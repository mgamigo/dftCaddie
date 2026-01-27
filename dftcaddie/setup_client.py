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
    Add command-line arguments for the `config` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the `config` arguments are added.
    """
    parser.add_argument(
        "-s",
        "--structure",
        metavar="FILE",
        required=False,
        help="Structure file used to initialize the calculation (e.g. CIF, POSCAR).",
    )
    parser.add_argument(
        "-i",
        "--init",
        action="store_true",
        help="Initialize setup from templates before applying options.",
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
    apply_setup(
        kind=kind,
        code=code,
        structure_file=args.structure,
        autokgrid=args.autokgrid,
        kppra=args.kppra,
        init=args.init,
        path=args.path,
    )
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
    structure_file: str = None,
    autokgrid: bool = False,
    kppra: int = 9000,
    path: bool = False,
    pseudo: bool = False,
    relativistic: bool = None,
    init: bool = False,
    system_info_path: str = "SYSTEM.INFO",
) -> int:
    """
    Apply structure- and system-dependent setup steps to a calculation.

    This function implements the ``caddie setup`` workflow. Depending on the
    selected options, it initializes template input files, reads a structure
    file, and applies structure-specific configuration such as lattice and
    atomic positions, automatic k-point grids, high-symmetry k-paths, and
    pseudopotential setup.

    Parameters
    ----------
    kind : str
        Calculation kind (e.g., ``"relax"``, ``"bands"``), used to select
        kind-dependent configuration options.
    code : str
        DFT code identifier (e.g., ``"quantum_espresso"``).
    structure_file : str or None, optional
        Path to a structure file readable by ``get_structure``. If ``None``,
        no structure-dependent setup is applied.
    autokgrid : bool, optional
        If True, compute and write an automatic k-point grid based on the
        structure, by default False.
    kppra : int, optional
        Target number of k-points per reciprocal atom used for automatic
        k-grid generation, by default 9000.
    path : bool, optional
        If True, insert a high-symmetry k-path based on the structure space
        group, by default False.
    pseudo : bool, optional
        If True, apply pseudopotential configuration during setup. When used
        together with ``init``, pseudopotentials are initialized from
        defaults, by default False.
    relativistic : bool
        If True, use the relativistic exchange folder variant (prefix ``"rel-"``).
    init : bool, optional
        If True, initialize ``SYSTEM.INFO`` from the template library before
        applying all possible modifications, by default False.
    system_info_path : str, optional
        Path to the ``SYSTEM.INFO`` file to create or modify, by default
        "SYSTEM.INFO".

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    if code == "quantum_espresso":
        if init or not os.path.exists(system_info_path):
            source_dir = os.path.join(os.path.dirname(__file__), "data", code)
            source_path = os.path.join(source_dir, system_info_path)
            destination_path = os.path.join(os.getcwd(), system_info_path)
            shutil.copy(source_path, destination_path)
    if structure_file is not None:
        structure = ut.get_structure(structure_file)
        files.set_crystal_structure(structure, code)
        if autokgrid or init:
            files.set_auto_kgrid(structure, code, kppra)
        if path or init:
            files.set_high_symmetry_path(structure, code)
        if pseudo or init:
            setting = ut.get_config(kind=kind, config_name="soc")
            if relativistic is None:
                relativistic = setting.get("default", False)
            apply_pseudos(
                kind_calc=kind,
                code=code,
                symbols=structure.symbols,
                relativistic=relativistic,
                configure=True,
            )
    return 0
