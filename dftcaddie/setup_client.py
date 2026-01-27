"""
dftCaddie | dftcaddie.setup_client
==================================

CLI handler for the ``caddie setup`` command.

This module defines the workflow used to adapt a prepared calculation to a
specific system. It can initialize template files (e.g. ``SYSTEM.INFO`` for
Quantum ESPRESSO), read a structure file, and apply structure-dependent edits
such as lattice vectors, fractional atomic positions, automatic k-point grids,
high-symmetry k-paths, and pseudopotential configuration.

Functions
---------
add_arguments
    Register command-line arguments for the ``setup`` subcommand.
run
    Dispatch the ``setup`` workflow using parsed CLI arguments.
apply_setup
    Apply setup steps (structure, k-grid, k-path, pseudos) to the working directory.
"""

import logging
import os
import shutil
from types import SimpleNamespace

from dftcaddie import utils as ut
from dftcaddie import file_management as files
from dftcaddie.pseudo_client import apply_pseudos

log = logging.getLogger(__name__)

_all__ = [
    "add_arguments",
    "run",
    "apply_setup",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``setup`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``setup`` arguments are added.
    """
    parser.add_argument(
        "-s",
        "--structure",
        metavar="FILE",
        required=True,
        help="Structure file used to initialize the calculation (e.g. CIF, POSCAR).",
    )
    parser.add_argument(
        "-ak",
        "--autokgrid",
        action="store_true",
        help="Set up an automatic k-point grid.",
    )
    parser.add_argument(
        "--kppra",
        metavar="INT",
        type=int,
        default=9000,
        help="Target number of k-points per atom (used with --autokgrid).",
    )
    parser.add_argument(
        "-kp",
        "--path",
        action="store_true",
        help="Set up a high-symmetry k-path in reciprocal space.",
    )
    parser.add_argument(
        "-p",
        "--pseudo",
        action="store_true",
        help="Set up default pseudopotentials",
    )


def run(args=None):
    """
    Dispatch the ``caddie setup`` workflow.

    This function resolves the current calculation kind and code from the
    working directory and applies system- and structure-dependent setup
    steps such as lattice and atomic positions, automatic k-point grids,
    high-symmetry k-paths, and pseudopotential configuration.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``setup`` subcommand.
    """
    kind, code = ut.resolve_calc_current_dir()
    structure = ut.get_structure(args.structure)

    apply_setup(
        kind=kind,
        code=code,
        structure=structure,
        autokgrid=args.autokgrid,
        kppra=args.kppra,
        path=args.path,
    )
    if args.pseudo:
        # Get default relativistic value for this calculation kind
        setting = ut.get_config(kind=kind, config_name="soc")
        relativistic = setting.get("default", False)
        apply_pseudos(
            kind_calc=kind,
            code=code,
            symbols=structure.symbols,
            relativistic=relativistic,
            configure=True,
        )


def apply_setup(
    kind: str,
    code: str,
    structure: SimpleNamespace,
    autokgrid: bool = False,
    kppra: int = 9000,
    path: bool = False,
) -> int:
    """
    Apply structure-dependent setup steps to a calculation.

    This function updates input templates using structural information
    (lattice vectors and atomic positions) and optionally configures an
    automatic k-point grid and a high-symmetry k-path.

    Parameters
    ----------
    kind : str
        Calculation kind (e.g., ``"relax"``, ``"bands"``). Included for
        interface consistency, but not used directly in this function.
    code : str
        DFT code identifier (e.g., ``"quantum_espresso"``).
    structure : SimpleNamespace
        Structure container providing lattice vectors, fractional atomic
        positions, chemical symbols, and space-group information.
    autokgrid : bool, optional
        If True, compute and write an automatic k-point grid based on the
        structure, by default False.
    kppra : int, optional
        Target number of k-points per reciprocal atom used for automatic
        k-grid generation, by default 9000.
    path : bool, optional
        If True, insert a high-symmetry k-path based on the structure space
        group, by default False.

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    files.set_crystal_structure(structure, code)
    if autokgrid:
        files.set_auto_kgrid(structure, code, kppra)
    if path:
        files.set_high_symmetry_path(structure, code)
    return 0
