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


@lru_cache(maxsize=1)
def resolve_pslibrary() -> Path:
    """
    Resolve the root path of the pseudopotential library.

    Priority:
    1. Environment variable PSLIBRARY
    2. User configuration (YAML)
    """
    import os

    # 1. From environment
    env = os.environ.get("PSLIBRARY")
    if env:
        log.info("Using PSLIBRARY from environment")
        return Path(env).expanduser()

    # 2. From YAML (optional)
    pseudo_cfg = CONFIG.get("pseudopotentials")
    if isinstance(pseudo_cfg, dict):
        root = pseudo_cfg.get("root")
        if root:
            log.info("Using PSLIBRARY from config file")
            return Path(root).expanduser()

    # 3. Hard error
    raise RuntimeError(
        "Pseudopotential library not found. "
        "Define 'pseudopotentials.root' in config.yaml "
        "or set the PSLIBRARY environment variable."
    )


CONFIG = _load_config()

calculations = CONFIG["calculations"]
clusters = CONFIG["clusters"]
mpi_executables = CONFIG["mpi_executables"]
suggested_qe_pseudos = CONFIG["suggested_qe_pseudos"]
