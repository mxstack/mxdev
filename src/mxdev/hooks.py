from .state import State
from pkg_resources import iter_entry_points

import typing


class Hook:
    """Entry point for hooking into mxdev."""

    namespace: str
    """The namespace for this hook."""

    def read(self, state: State) -> None:
        """Gets executed after mxdev read operation."""

    def write(self, state: State) -> None:
        """Gets executed after mxdev write operation."""


def load_hooks() -> list:
    return [ep.load()() for ep in iter_entry_points("mxdev") if ep.name == "hook"]


def read_hooks(state: State, hooks: typing.List[Hook]) -> None:
    for hook in hooks:
        hook.read(state)


def write_hooks(state: State, hooks: typing.List[Hook]) -> None:
    for hook in hooks:
        hook.write(state)
