"""
dftCaddie | dftcaddie.cofig_client
==================================

CLI handler for the `caddie cofig` command.

This module registers calculation-preparation options and implements the
interactive flow that resolves missing parameters, then writes DFT input
files to a folder via ``dftcaddie.file_management``.

Functions
---------
add_arguments
    Register command-line arguments for the `cofig` subcommand.
run
    Resolve calculation options and prepare DFT input files.
"""

import logging
import os
from types import SimpleNamespace

from dftcaddie import utils as ut
from dftcaddie import file_management as files
from dftcaddie.config import calculations

log = logging.getLogger(__name__)

_all__ = [
    "add_arguments",
    "run",
]


def add_arguments(parser):
    """
    Add command-line arguments for the `config` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the `config` arguments are added.
    """
    parser.add_argument(
        "-f",
        "--file",
        metavar="FILE",
        required=True,
        help="File from which to get the crystal structure.",
    )
    parser.add_argument(
        "-e",
        "--exchange",
        metavar="EX",
        default="pbe",
        help="Kind of exchange (pbe, pbesol, pz, ...).",
    )
    parser.add_argument(
        "-k",
        "--kind",
        metavar="KIND",
        default="kjpaw",
        help="Kind of pseudopotential (kjpaw, us, ...).",
    )
    parser.add_argument(
        "-r",
        "--relativistic",
        action="store_true",
        help="Set relativistic pseudopotential",
    )
    parser.add_argument(
        "-c",
        "--configure",
        action="store_true",
        help="Configure cutoffs according to the pseudopotentials",
    )


def run(args=None):
    """
    Resolve calculation options and prepare DFT input files.

    This function implements the `caddie calc` workflow. It resolves
    missing options interactively when needed, validates user selections,
    copies template input files, and applies code- and cluster-specific
    configuration edits.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the `calc` subcommand.
    """
    kind, code = ut.resolve_calc_current_dir()
    structure = ut.get_structure(args.file)
    apply_pseudos(
        kind_calc=kind,
        code=code,
        symbols=structure.symbols,
        exchange=args.exchange,
        kind_pseudo=args.kind,
        relativistic=args.relativistic,
        configure=args.configure,
    )


def apply_pseudos(
    kind_calc: str,
    code: str,
    symbols: list[str],
    relativistic: bool,
    exchange: str = "pbe",
    kind_pseudo: str = "kjpaw",
    configure: bool = False,
    system_info_path: str = "SYSTEM.INFO",
    ratio: float = 1.5,
) -> int:
    """
    Resolve and apply pseudopotentials for a structure and update input templates.

    For Quantum ESPRESSO calculations, this function selects one pseudopotential
    per element from the PSLibrary tree and updates ``SYSTEM.INFO`` accordingly.
    Optionally, it reads suggested cutoffs from the pseudopotential headers and
    writes CUTOFF/ECUTRHO into ``SYSTEM.INFO``.

    Parameters
    ----------
    kind_calc : str
        Calculation kind (e.g., ``"relax"``, ``"bands"``). Used to apply
        kind-dependent edits (e.g., SOC-related settings).
    code : str
        DFT code identifier. Currently only ``"quantum_espresso"`` is supported.
    symbols : list[str]
        Chemical symbols present in the structure (e.g., ``["Si", "O"]``).
    exchange : str
        Exchange/correlation label used to locate pseudopotentials (e.g., ``"pbe"``).
    kind_pseudo : str
        Pseudopotential kind/wildcard used to resolve files (e.g., ``"kjpaw"``, ``"us"``).
    relativistic : bool
        If True, use the relativistic exchange folder variant (prefix ``"rel-"``).
    configure : bool
        If True, read suggested cutoff values from pseudo headers and update
        CUTOFF/ECUTRHO in ``SYSTEM.INFO``.
    system_info_path : str, optional
        Path to the ``SYSTEM.INFO`` file to edit, by default "SYSTEM.INFO".
    ratio : float, optional
        Safety factor applied to suggested cutoff values, by default 1.5.

    Returns
    -------
    int
        Exit code (0 on success).

    Raises
    ------
    NotImplementedError
        If ``code`` is not supported.
    """
    if code != "quantum_espresso":
        raise NotImplementedError("Only quantum_espresso supported for now.")

    pseudos = files.get_qe_pseudo_paths(
        symbols=symbols,
        exchange=exchange,
        kind=kind_pseudo,
        relativistic=relativistic,
    )
    files.write_pseudos_to_system_info(system_info_path, pseudos)
    files.set_spin_orbit_coupling(kind_calc, code, relativistic)

    if configure:
        files.configure_qe_cutoffs_from_pseudos(system_info_path, pseudos, ratio=ratio)

    return 0
