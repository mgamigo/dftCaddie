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

DEFAULT_CONFIG_PATH = Path(__file__).parent / "data" / "config.default.yaml"
USER_PATHS = [
    Path.cwd() / "dftcaddie.yaml",
    Path.home() / ".config" / "dftcaddie" / "config.yaml",
]


@lru_cache(maxsize=1)
def _load_config() -> dict:
    for path in USER_PATHS:
        if path.exists():
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}

    with open(DEFAULT_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}

CONFIG = _load_config()

calculations = CONFIG["calculations"]
clusters = CONFIG["clusters"]
mpi_executables = CONFIG["mpi_executables"]
pseudopotentials = CONFIG["pseudopotentials"]
suggested_qe_pseudos = CONFIG["suggested_qe_pseudos"]
