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
    Resolve the root path of the QE pslibrary.

    The path is read from the user configuration key
    ``qe_pseudopotentials``. The directory must exist.

    Returns
    -------
    Path
        Absolute path to the pslibrary.

    Raises
    ------
    RuntimeError
        If the path is not defined or does not exist.
    """
    root = CONFIG.get("qe_pslibrary")

    if not root:
        raise RuntimeError(
            "QE PSLIBRARY not defined. " "Set 'qe_pslibrary' in config.yaml."
        )

    path = Path(root).expanduser()

    if not path.exists():
        raise RuntimeError(
            f"QE PSLIBRARY not found at '{path}'. "
            "Check 'qe_pslibrary' in config.yaml."
        )

    log.info("Using QE pseudopotentials from %s", path)
    return path


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

calculations = CONFIG["calculations"]
clusters = CONFIG["clusters"]
mpi_executables = CONFIG["mpi_executables"]
suggested_qe_pseudos = CONFIG["suggested_qe_pseudos"]
