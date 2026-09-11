"""
dftCaddie | dftcaddie.config
============================

Select configuration paths, load settings on demand, and resolve libraries.
Importing this module does not read YAML or access configuration values.
"""

from pathlib import Path
from functools import lru_cache
import logging

log = logging.getLogger(__name__)


def config_paths() -> tuple[Path, Path]:
    """
    Return the selected YAML path and template/header root.

    Returns
    -------
    tuple of pathlib.Path
        The active YAML path and the directory used to resolve relative
        template/header paths.
    """
    path = Path.home() / ".config" / "dftcaddie" / "config.yaml"
    if not path.exists():
        path = Path(__file__).parent / "resources" / "config.yaml"
    return path, path.parent


@lru_cache(maxsize=1)
def load_config() -> tuple[dict, Path]:
    """
    Read the selected configuration on first use and cache it for this process.

    Returns
    -------
    tuple of dict and pathlib.Path
        Parsed settings and the template/header root.

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

    path, source = config_paths()
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
    """Clear cached settings and resolved pseudopotential paths."""
    load_config.cache_clear()
    resolve_pslibrary.cache_clear()
    resolve_potcar_library.cache_clear()
