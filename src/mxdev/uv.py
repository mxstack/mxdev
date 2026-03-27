import logging
import re
from pathlib import Path
from typing import Any

import tomlkit
from mxdev.hooks import Hook
from mxdev.state import State

logger = logging.getLogger("mxdev")


def normalize_name(name: str) -> str:
    """PEP 503 normalization: lowercased, runs of -, _, . become single -"""
    return re.sub(r"[-_.]+", "-", name).lower()


class UvPyprojectUpdater(Hook):
    """
    An mxdev hook that updates pyproject.toml during the write phase for uv-managed projects.
    """

    namespace = "uv"

    def read(self, state: State) -> None:
        pass

    def write(self, state: State) -> None:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            logger.debug("[%s] pyproject.toml not found, skipping.", self.namespace)
            return

        try:
            with pyproject_path.open("r", encoding="utf-8") as f:
                doc = tomlkit.load(f)
        except Exception as e:
            logger.error("[%s] Failed to read pyproject.toml: %s", self.namespace, e)
            return

        # Check for the UV managed signal
        tool_uv = doc.get("tool", {}).get("uv", {})
        if tool_uv.get("managed") is not True:
            logger.debug(
                "[%s] Project not explicitly managed by uv ([tool.uv] managed=true missing), skipping.", self.namespace
            )
            return

        logger.info("[%s] Updating pyproject.toml...", self.namespace)
        self._update_pyproject(doc, state)

        try:
            with pyproject_path.open("w", encoding="utf-8") as f:
                tomlkit.dump(doc, f)
            logger.info("[%s] Successfully updated pyproject.toml", self.namespace)
        except Exception as e:
            logger.error("[%s] Failed to write pyproject.toml: %s", self.namespace, e)

    def _update_pyproject(self, doc: Any, state: State) -> None:
        """Modify the pyproject.toml document based on mxdev state."""
        if not state.configuration.packages:
            return

        # 1. Update [tool.uv.sources]
        if "tool" not in doc:
            doc.add("tool", tomlkit.table())
        if "uv" not in doc["tool"]:
            doc["tool"]["uv"] = tomlkit.table()
        if "sources" not in doc["tool"]["uv"]:
            doc["tool"]["uv"]["sources"] = tomlkit.table()

        uv_sources = doc["tool"]["uv"]["sources"]

        for pkg_name, pkg_data in state.configuration.packages.items():
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

            if install_mode in ("editable", "direct"):
                source_table.append("editable", True)
            elif install_mode == "fixed":
                source_table.append("editable", False)

            uv_sources[pkg_name] = source_table

        # 2. Add packages to project.dependencies if not present
        if "project" not in doc:
            doc.add("project", tomlkit.table())

        if "dependencies" not in doc["project"]:
            doc["project"]["dependencies"] = tomlkit.array()

        dependencies = doc["project"]["dependencies"]
        pkg_name_pattern = re.compile(r"^([a-zA-Z0-9_\-\.]+)")
        existing_pkg_names = set()

        for dep in dependencies:
            match = pkg_name_pattern.match(str(dep).strip())
            if match:
                existing_pkg_names.add(normalize_name(match.group(1)))

        for pkg_name, pkg_data in state.configuration.packages.items():
            install_mode = pkg_data.get("install-mode", "editable")
            if install_mode == "skip":
                continue

            normalized_name = normalize_name(pkg_name)
            if normalized_name not in existing_pkg_names:
                dependencies.append(pkg_name)
