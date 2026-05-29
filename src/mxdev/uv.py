from mxdev.hooks import Hook
from mxdev.state import State
from pathlib import Path
from typing import TYPE_CHECKING

import logging
import os
import tempfile


if TYPE_CHECKING:
    import tomlkit


logger = logging.getLogger("mxdev")


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

        if not packages and not overrides:
            return

        if "tool" not in doc:
            doc.add("tool", tomlkit.table())
        if "uv" not in doc["tool"]:
            doc["tool"]["uv"] = tomlkit.table()

        # 1. Update [tool.uv.sources]
        if packages:
            if "sources" not in doc["tool"]["uv"]:
                doc["tool"]["uv"]["sources"] = tomlkit.table()

            uv_sources = doc["tool"]["uv"]["sources"]

            for pkg_name, pkg_data in packages.items():
                install_mode = pkg_data.get("install-mode", "editable")

                if install_mode == "skip":
                    continue

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

        # 2. Update [tool.uv] override-dependencies from version-overrides
        if overrides:
            override_array = tomlkit.array()
            override_array.extend(overrides.values())
            override_array.multiline(True)
            doc["tool"]["uv"]["override-dependencies"] = override_array
