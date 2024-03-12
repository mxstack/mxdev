# this is a helper to load entrypoints with importlib, since pkg_resources
# is deprecated. In Python 3.12 an API incompatible change was introduced,
# so this code is that ugly now.
from importlib.metadata import entry_points


try:
    # do we have Python 3.12+?
    from importlib.metadata import EntryPoints  # type: ignore # noqa: F401

    HAS_IMPORTLIB_ENTRYPOINTS = True
except ImportError:
    HAS_IMPORTLIB_ENTRYPOINTS = False


def load_eps_by_group(group: str) -> list:
    if HAS_IMPORTLIB_ENTRYPOINTS:
        eps = entry_points(group=group)  # type: ignore
    else:
        eps_base = entry_points()
        if group not in eps_base:
            return []
        eps = eps_base[group]  # type: ignore
    # XXX: for some reasons entry points are loaded twice. not sure if this
    #      is a glitch when installing with uv or something related to
    #      importlib.metadata.entry_points
    return list(set(eps))  # type: ignore
