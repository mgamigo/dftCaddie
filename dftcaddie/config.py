"""
dftCaddie | dftcaddie.config
============================

Select configuration paths, load settings on demand, and resolve libraries.
Importing this module does not read YAML or access configuration values.

Functions
---------
load_config()
    Read the active or bundled configuration on first use and cache it.
resolve_pslibrary()
    Resolve and validate the Quantum ESPRESSO pseudopotential library.
resolve_potcar_library()
    Resolve and validate the VASP POTCAR library.
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
def resolve_pslibrary() -> Path:
    """
    Resolve the root path of the Quantum ESPRESSO PSLibrary.

    The location is resolved in the following priority order:

    1. Environment variable ``$PSLIBRARY``.
    2. User configuration key ``qe_pslibrary`` in ``config.yaml``.

    The resolved directory must exist.

    Returns
    -------
    Path
        Absolute path to the QE PSLibrary.

    Raises
    ------
    RuntimeError
        If no path is defined or if the resolved directory does not exist.
    """
    import os

    # ------------------------------------------------------------
    # 1. Environment variable
    # ------------------------------------------------------------
    env_path = os.environ.get("PSLIBRARY")
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            log.info("Using QE PSLibrary from $PSLIBRARY: %s", path)
            return path
        else:
            raise RuntimeError(
                f"$PSLIBRARY is set but directory does not exist: '{path}'"
            )

    # ------------------------------------------------------------
    # 2. Config file
    # ------------------------------------------------------------
    root = load_config()[0].get("qe_pslibrary")

    if root:
        path = Path(root).expanduser()
        if path.exists():
            log.info("Using QE PSLibrary from config.yaml: %s", path)
            return path
        else:
            raise RuntimeError(
                f"QE PSLibrary not found at '{path}'. "
                "Check 'qe_pslibrary' in config.yaml."
            )

    # ------------------------------------------------------------
    # 3. Hard error
    # ------------------------------------------------------------
    raise RuntimeError(
        "QE PSLibrary not defined. "
        "Set the $PSLIBRARY environment variable or define "
        "'qe_pslibrary' in config.yaml."
    )


@lru_cache(maxsize=1)
def resolve_potcar_library() -> Path:
    """
    Resolve the root path of the VASP POTCAR library.

    The path is read from the user configuration key
    ``vasp_pseudopotentials``. The directory must exist.

    Returns
    -------
    Path
        Absolute path to the POTCAR library.

    Raises
    ------
    RuntimeError
        If the path is not defined or does not exist.
    """
    root = load_config()[0].get("vasp_pseudopotentials")

    if not root:
        raise RuntimeError(
            "VASP POTCAR library not defined. "
            "Set 'vasp_pseudopotentials' in config.yaml."
        )

    path = Path(root).expanduser()

    if not path.exists():
        raise RuntimeError(
            f"VASP POTCAR library not found at '{path}'. "
            "Check 'vasp_pseudopotentials' in config.yaml."
        )

    log.info("Using VASP POTCARs from %s", path)
    return path


def clear_config_cache() -> None:
    """
    Clear cached settings and resolved pseudopotential paths.

    This is mainly useful in long-running Python sessions, such as IPython, when
    ``~/.config/dftcaddie/config.yaml`` or ``$PSLIBRARY`` has changed after the
    first configuration lookup.

    Returns
    -------
    None
        The cache is cleared in-place.
    """
    load_config.cache_clear()
    resolve_pslibrary.cache_clear()
    resolve_potcar_library.cache_clear()
