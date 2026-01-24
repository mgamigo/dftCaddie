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
    if code == "quantum_espresso":
        pseudos = files.get_qe_pseudo_paths(
            structure.symbols, args.exchange, args.kind, args.relativistic
        )
        files.write_pseudos_to_system_info("SYSTEM.INFO", pseudos)
        # SET SOC
        files.set_spin_orbit_coupling(kind, code, args.relativistic)
        if args.configure:
            files.configure_qe_cutoffs_from_pseudos("SYSTEM.INFO", pseudos, ratio=1.5)
