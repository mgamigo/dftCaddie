"""
dftCaddie | dftcaddie.cli
=========================

This module provides a command-line client interface for dftCaddie, a tool
to assist in the preparation of DFT calculations. It allows users to choose
calculation types and corresponding codes, configure calculation options,
and prepare the necessary input files.

Functions
---------
main(...)
    Command-line client for dftCaddie that facilitates the setup of DFT calculations.
"""

import sys
import argparse


def main(argv=None):
    """
    Command-line client for dftCaddie that facilitates the setup of DFT
    calculations.

    Parameters
    ----------
    argv : list, optional
        A list of command-line arguments. Defaults to None, in which case
        system-provided command-line arguments are used.
    """

    print(f"dftCaddie 🏌️\n" f"============\n")

    if argv is None:
        argv = sys.argv[1:]
        if len(argv) == 0:
            argv = ["-h"]

    parser = argparse.ArgumentParser(
        prog="caddie",
        description="DFT Caddie - Your assistant for DFT calculations.",
    )
    subparsers = parser.add_subparsers(title="Commands", dest="command")

    # calc subcommand
    calc_parser = subparsers.add_parser("calc", help="Create a new DFT calculation.")
    calc_parser.add_argument(
        "-s", "--scratch", action="store_true", help="Start calculation from scratch"
    )
    calc_parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite existing files if necessary",
    )
    calc_parser.add_argument(
        "-st",
        "--structure",
        required=False,
        metavar="file",
        help="File from which to read the crystal structure",
    )
    calc_parser.add_argument(
        "-d",
        "--details",
        action="store_true",
        help="Ask for details instead of going for default values",
    )
    calc_parser.add_argument(
        "--kind",
        required=False,
        metavar="CALC",
        help="Calculation kind (e.g., bands, relax)",
    )
    calc_parser.add_argument(
        "--code",
        required=False,
        metavar="CODE",
        help="DFT code to use (e.g., vasp, quantum espresso)",
    )
    calc_parser.add_argument(
        "--cluster",
        required=False,
        metavar="CLUSTER",
        help="Cluster for automatic SBATCH heading.",
    )

    # pseudo subcommand
    pseudo_parser = subparsers.add_parser("pseudo", help="Change pseudopotentials.")
    pseudo_parser.add_argument(
        "--option2",
        help="Option for changing pseudopotentials.",
    )

    args = parser.parse_args(argv)

    # Dispatch
    if args.command == "calc":
        print("Running calc with option")
        print(args)
        # create_calculation(args)
    elif args.command == "pseudo":
        print("Running pseudo")
        print(args)
        # change_pseudopotentials(args)
