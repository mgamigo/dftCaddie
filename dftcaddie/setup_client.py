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
        help="File from which to get the crystal structure.",
    )
    parser.add_argument(
        "-s",
        "--scratch",
        action="store_true",
        help="Start setup from scratch",
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
    if code == "quantum_espresso":
        if args.scratch:
            source_dir = os.path.join(os.path.dirname(__file__), "data", code)
            source_path = os.path.join(source_dir, "SYSTEM.INFO")
            destination_path = os.path.join(os.getcwd(), "SYSTEM.INFO")
            shutil.copy(source_path, destination_path)
    if args.file is not None:
        structure = ut.get_structure(args.file)
        files.set_crystal_structure(structure, code)
    if args.autokgrid or args.file and args.scratch:
        files.set_auto_kgrid(structure, code, args.kppra)
    if args.path or args.file and args.scratch:
        files.set_high_symmetry_path(structure, code)
    if args.pseudo or args.file and args.scratch:
        files.set_high_symmetry_path(structure, code)
