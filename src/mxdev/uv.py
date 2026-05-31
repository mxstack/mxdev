from mxdev.config import to_bool
from mxdev.hooks import Hook
from mxdev.state import State
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

import logging
import os
import tempfile


if TYPE_CHECKING:
    import tomlkit


logger = logging.getLogger("mxdev")

# Trailing comment used to tag the [tool.uv.sources] entries mxdev writes, so
# stale ones can be pruned without touching user-defined sources.
_UV_SOURCE_MARKER = "managed by mxdev"


def _is_mxdev_managed_source(value: Any) -> bool:
    """Return True if a [tool.uv.sources] value carries the mxdev marker comment."""
    trivia = getattr(value, "trivia", None)
    comment = getattr(trivia, "comment", "") or ""
    return _UV_SOURCE_MARKER in comment


def _constraints_to_uv(constraints: list[str]) -> list[tuple[str, str]]:
    """Turn resolved constraint lines into ordered uv array items.

    Mirrors ``constraints-mxdev.txt`` into TOML-array form: specifier lines
    become ``("entry", specifier)`` and comment lines become
    ``("comment", text)``, preserving source order. Decorative ``####`` rules,
    blank lines, and non-PEP-508 lines (e.g. ``--hash``) are dropped.
    """
    from packaging.requirements import Requirement

    items: list[tuple[str, str]] = []
    for raw in constraints:
        stripped = raw.strip()
        if not stripped:
            continue
        # Decorative full-width rule (line consisting only of '#').
        if set(stripped) == {"#"}:
            continue
        if stripped.startswith("#"):
            items.append(("comment", stripped.lstrip("#").strip()))
            continue
        try:
            Requirement(stripped)
        except Exception:
            logger.debug("[uv] Skipping non-PEP-508 constraint line: %s", stripped)
            continue
        items.append(("entry", stripped))
    return items


class UvPyprojectUpdater(Hook):
    """An mxdev hook that updates pyproject.toml during the write phase for uv-managed projects."""

    namespace = "uv"

    def read(self, state: State) -> None:
        pass

    def write(self, state: State) -> None:
        pyproject_path = Path(state.configuration.settings.get("directory", ".")) / "pyproject.toml"
        if not pyproject_path.exists():
            logger.debug("[%s] pyproject.toml not found, skipping.", self.namespace)
            return

        try:
            content = pyproject_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.error("[%s] Failed to read pyproject.toml: %s", self.namespace, e)
            return

        # Attempt to parse using standard library (Python 3.11+)
        try:
            import tomllib

            parsed = tomllib.loads(content)
            if parsed.get("tool", {}).get("uv", {}).get("managed") is not True:
                logger.debug(
                    "[%s] Project not explicitly managed by uv ([tool.uv] managed=true missing), skipping.",
                    self.namespace,
                )
                return
        except ImportError:
            # Fallback for Python 3.10: fast string check to avoid tomlkit overhead
            if "[tool.uv]" not in content:
                logger.debug(
                    "[%s] Project not explicitly managed by uv ([tool.uv] managed=true missing), skipping.",
                    self.namespace,
                )
                return
        except Exception:
            # If the parser fails (e.g., malformed TOML), just skip.
            return

        # Now we are confident it's a uv project, require our heavy dependency
        try:
            from typing import TYPE_CHECKING

            if not TYPE_CHECKING:
                import tomlkit
        except ImportError:
            raise RuntimeError("tomlkit is required for the uv hook. Install it with: pip install mxdev[uv]")

        doc = tomlkit.loads(content)

        # Check for the UV managed signal
        tool_uv = doc.get("tool", {}).get("uv", {})
        if tool_uv.get("managed") is not True:
            logger.debug(
                "[%s] Project not explicitly managed by uv ([tool.uv] managed=true missing), skipping.", self.namespace
            )
            return

        logger.info("[%s] Updating pyproject.toml...", self.namespace)
        self._update_pyproject(doc, state)

        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=pyproject_path.parent, suffix=".tmp", delete=False, encoding="utf-8"
            ) as f:
                tomlkit.dump(doc, f)
                tmp = f.name
            os.replace(tmp, str(pyproject_path))
            tmp = None  # success, don't clean up
            logger.info("[%s] Successfully updated pyproject.toml", self.namespace)
        except OSError as e:
            logger.error("[%s] Failed to write pyproject.toml: %s", self.namespace, e)
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)

    def _update_pyproject(self, doc: "tomlkit.TOMLDocument", state: State) -> None:
        """Modify the pyproject.toml document based on mxdev state."""
        import tomlkit

        packages = state.configuration.packages
        overrides = state.configuration.overrides
        settings = state.configuration.settings

        write_constraints = to_bool(settings.get("uv-constraint-dependencies", "true"))
        constraint_items = _constraints_to_uv(state.constraints) if write_constraints else []

        # Packages mxdev manages as path sources. A package in "skip" install-mode
        # gets no source entry (and an existing one is pruned below).
        managed_sources = {name: data for name, data in packages.items() if data.get("install-mode") != "skip"}

        if "tool" not in doc:
            doc.add("tool", tomlkit.table())
        if "uv" not in doc["tool"]:
            doc["tool"]["uv"] = tomlkit.table()
        uv = doc["tool"]["uv"]

        # 1. Reconcile [tool.uv.sources]: write the current managed sources and
        #    prune mxdev-managed entries whose package was removed from mx.ini.
        #    Foreign (user-defined) sources without the mxdev marker are never
        #    touched.
        existing_sources = uv.get("sources")
        if managed_sources or existing_sources is not None:
            if existing_sources is None:
                uv["sources"] = tomlkit.table()
            uv_sources = uv["sources"]

            # Prune stale mxdev-managed entries.
            for key in list(uv_sources.keys()):
                if _is_mxdev_managed_source(uv_sources[key]) and key not in managed_sources:
                    del uv_sources[key]

            # Write / refresh current managed entries, each tagged with the marker.
            for pkg_name, pkg_data in managed_sources.items():
                install_mode = pkg_data.get("install-mode", "editable")

                target_dir = Path(pkg_data.get("target", "sources"))
                package_path = target_dir / pkg_name
                subdirectory = pkg_data.get("subdirectory", "")
                if subdirectory:
                    package_path = package_path / subdirectory

                try:
                    if package_path.is_absolute():
                        rel_path = package_path.relative_to(Path.cwd()).as_posix()
                    else:
                        rel_path = package_path.as_posix()
                except ValueError:
                    rel_path = package_path.as_posix()

                source_table = tomlkit.inline_table()
                source_table.append("path", rel_path)

                if install_mode == "editable":
                    source_table.append("editable", True)
                elif install_mode == "fixed":
                    source_table.append("editable", False)

                uv_sources[pkg_name] = source_table
                uv_sources[pkg_name].trivia.comment_ws = "  "
                uv_sources[pkg_name].trivia.comment = f"# {_UV_SOURCE_MARKER}"

            # Drop the table entirely if reconciliation emptied it.
            if len(uv_sources) == 0:
                del uv["sources"]

        # 2. Update [tool.uv] override-dependencies from version-overrides
        if overrides:
            override_array = tomlkit.array()
            override_array.extend(overrides.values())
            override_array.multiline(True)
            uv["override-dependencies"] = override_array

        # 3. Update [tool.uv] constraint-dependencies from resolved constraints
        if write_constraints:
            if constraint_items:
                constraint_array = tomlkit.array()
                constraint_array.multiline(True)
                constraint_array.add_line(comment="managed by mxdev - do not edit")
                for kind, text in constraint_items:
                    if kind == "comment":
                        constraint_array.add_line(comment=text)
                    else:
                        constraint_array.add_line(text)
                uv["constraint-dependencies"] = constraint_array
            elif "constraint-dependencies" in uv:
                # Resolved set is empty: drop a stale mxdev-managed array.
                del uv["constraint-dependencies"]
