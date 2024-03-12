from .entry_points import load_eps_by_group
from .state import State

import typing


try:
    # do we have Python 3.12+
    from importlib.metadata import EntryPoints  # type: ignore # noqa: F401

    HAS_IMPORTLIB_ENTRYPOINTS = True
except ImportError:
    HAS_IMPORTLIB_ENTRYPOINTS = False


class Hook:
    """Entry point for hooking into mxdev."""

    namespace: str
    """The namespace for this hook."""

    def read(self, state: State) -> None:
        """Gets executed after mxdev read operation."""

    def write(self, state: State) -> None:
        """Gets executed after mxdev write operation."""


def load_hooks() -> list:
    return [ep.load()() for ep in load_eps_by_group("mxdev") if ep.name == "hook"]


def read_hooks(state: State, hooks: typing.List[Hook]) -> None:
    for hook in hooks:
        hook.read(state)


def write_hooks(state: State, hooks: typing.List[Hook]) -> None:
    for hook in hooks:
        hook.write(state)
