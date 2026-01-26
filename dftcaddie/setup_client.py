"""
dftCaddie | dftcaddie.setup_client
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
import shutil
from types import SimpleNamespace

from dftcaddie import utils as ut
from dftcaddie.config import calculations, clusters
from dftcaddie import file_management as files
from dftcaddie.pseudo_client import apply_pseudos

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
        required=False,
        help="File from which to get/update the crystal structure.",
    )
    parser.add_argument(
        "-i",
        "--init",
        action="store_true",
        help="Start setup from scratch.",
    )
    parser.add_argument(
        "-ak",
        "--autokgrid",
        action="store_true",
        help="Setup an automatic kgrid",
    )
    parser.add_argument(
        "--kppra",
        metavar="INT",
        default=9000,
        help="Target number of k-points per atom",
    )
    parser.add_argument(
        "-kp",
        "--path",
        action="store_true",
        help="Setup a high-symmetry path in reciprocal space",
    )
    parser.add_argument(
        "-p",
        "--pseudo",
        action="store_true",
        help="Setup the pseudopotential",
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
    apply_setup(
        kind=kind,
        code=code,
        structure_file=args.file,
        autokgrid=args.autokgrid,
        kppra=args.kppra,
        init=args.init,
        path=args.path,
        pseudo=args.pseudo,
    )


def apply_setup(
    kind: str,
    code: str,
    structure_file: str = None,
    autokgrid: bool = False,
    kppra: int = 9000,
    path: bool = False,
    pseudo: bool = False,
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
            relativistic = setting.get("default", False)
            apply_pseudos(
                kind_calc=kind,
                code=code,
                symbols=structure.symbols,
                relativistic=relativistic,
            )
    return 0
