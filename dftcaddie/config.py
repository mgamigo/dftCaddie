"""
dftCaddie | dftcaddie.config
============================

Select configuration paths, load settings on demand, and resolve libraries.
Importing this module does not read YAML or access configuration values.

Functions
---------
load_config()
    Read the active or bundled configuration on first use and cache it.
resolve_pseudo_library(name)
    Look up a named library, resolve its path, and attach its suggestions.
clear_config_cache()
    Clear cached configuration and pseudopotential library paths.

Private Utilities
-----------------
_config_paths()
    Return the selected YAML path and the matching resource directory.
"""

from pathlib import Path
from functools import lru_cache
import logging

log = logging.getLogger(__name__)


def _config_paths(default_config: bool = False) -> tuple[Path, Path]:
    """
    Return the selected YAML path and resource root.

    Parameters
    ----------
    default_config : bool, optional
        If True, ignore the user configuration and return bundled resources.

    Returns
    -------
    tuple[Path, Path]
        The active YAML path and the directory used to resolve relative
        template, SBATCH header, and k-path resources.
    """
    resources = Path(__file__).parent / "resources"
    path = resources / "config.yaml"
    if not default_config:
        user_path = Path.home() / ".config" / "dftcaddie" / "config.yaml"
        if user_path.exists():
            path = user_path
    return path, path.parent


@lru_cache(maxsize=2)
def load_config(default_config: bool = False) -> tuple[dict, Path]:
    """
    Read the selected configuration on first use and cache it for this process.

    Parameters
    ----------
    default_config : bool, optional
        If True, load the bundled configuration even when a user
        ``~/.config/dftcaddie/config.yaml`` exists.

    Returns
    -------
    tuple of dict and pathlib.Path
        Parsed settings and the resource root.

    Raises
    ------
    ValueError
        If the YAML root is not a mapping. Syntax and file errors propagate.

    Notes
    -----
    Call clear_config_cache() after changing configuration paths or files in
    a long-running interactive session.
    """
    import yaml

    path, source = _config_paths(default_config=default_config)
    with path.open() as stream:
        data = yaml.safe_load(stream)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {path}")
    return data, source


@lru_cache(maxsize=1)
def resolve_pseudo_library(name: str) -> dict:
    """
    Resolve a named pseudopotential library and its suggestion patterns.

    Parameters
    ----------
    name : str
        Globally unique key in ``pseudopotentials.libraries``.

    Returns
    -------
    dict
        Library settings with name, absolute Path, and a suggestions mapping
        from element to relative glob patterns. Relative library paths use
        the active configuration directory; ``~`` expands to the user's home.

    Notes
    -----
    Configuration checks validate formats, supported codes, and suggestion
    groups. This function only looks up settings and expands paths. The most
    recent library is cached; treat returned settings as read-only and call
    clear_config_cache() after changing configuration.
    """
    from copy import deepcopy

    data, source = load_config()
    library = deepcopy(data["pseudopotentials"]["libraries"][name])
    path = Path(library["path"]).expanduser()
    if not path.is_absolute():
        path = source / path
    suggestions = next(
        (
            group["elements"]
            for group in data.get("suggested_pseudos", [])
            if name in group["libraries"]
        ),
        {},
    )
    library.update(name=name, path=path.absolute(), suggestions=deepcopy(suggestions))
    return library


def clear_config_cache() -> None:
    """
    Clear cached settings and resolved pseudopotential paths.

    This is mainly useful in long-running Python sessions, such as IPython, when
    ``~/.config/dftcaddie/config.yaml`` has changed after the
    first configuration lookup.

    Returns
    -------
    None
        The cache is cleared in-place.
    """
    load_config.cache_clear()
    resolve_pseudo_library.cache_clear()
