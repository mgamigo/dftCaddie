"""
dftCaddie | dftcaddie.config
============================

This module defines configuration variables used throughout the dftCaddie
application, providing flexible support for different calculation types,
DFT codes, and necessary input files.
"""

from pathlib import Path
from functools import lru_cache
import yaml
import logging

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_config() -> dict:
    CONFIG_FILE = Path.home() / ".config" / "dftcaddie" / "config.yaml"
    SOURCE_DIR = Path.home() / ".config" / "dftcaddie"
    if not CONFIG_FILE.exists():
        CONFIG_FILE = Path(__file__).parent / "resources" / "config.yaml"
        SOURCE_DIR = Path(__file__).parent / "resources"
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f) or {}, SOURCE_DIR


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
    root = CONFIG.get("qe_pslibrary")

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
    root = CONFIG.get("vasp_pseudopotentials")

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


CONFIG, SOURCE_DIR = _load_config()

default_kppra = CONFIG["default_kppra"]
nscf_kppra_ratio = CONFIG["nscf_kppra_ratio"]
default_cutoff_ratio = CONFIG["default_cutoff_ratio"]

suggested_qe_pseudos = CONFIG["suggested_qe_pseudos"]
mpi_executables = CONFIG["mpi_executables"]
clusters = CONFIG["clusters"]
calculations = CONFIG["calculations"]
