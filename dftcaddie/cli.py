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

Private Utilities
-----------------
_configure_logging():
    Configure root logging level for the CLI.
"""

import sys
import argparse
import logging

from dftcaddie import calc_client, setup_client, pseudo_client

_all__ = [
    "main",
]


def _configure_logging(verbose: int, quiet: bool) -> None:
    """Configure root logging level for the CLI."""
    if quiet:
        level = logging.ERROR
    elif verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(level=level, format="%(message)s")


def main(argv: list[str] | None = None) -> int:
    """
    Run the dftCaddie command-line interface.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments (excluding the program name). If ``None``,
        arguments are taken from ``sys.argv[1:]``.
    """
    # print("dftCaddie 🏌️\n============")
    _heading()

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="caddie",
        description="DFT Caddie - Your assistant for DFT calculations.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv).",
    )
    subparsers = parser.add_subparsers(title="Commands", dest="command")

    # --- calc subcommand ---
    calc_parser = subparsers.add_parser(
        "calc",
        help="Create or prepare a new DFT calculation",
    )
    calc_client.add_arguments(calc_parser)
    # --- setup subcommand ---
    setup_parser = subparsers.add_parser(
        "setup",
        help="Configure the calculation for a given system.",
    )
    setup_client.add_arguments(setup_parser)
    # --- calc subcommand ---
    pseudo_parser = subparsers.add_parser(
        "pseudo",
        help="Configure the pseudopotential for a given system.",
    )
    pseudo_client.add_arguments(pseudo_parser)

    # ---
    args = parser.parse_args(argv)
    _configure_logging(args.verbose, quiet=False)

    # Dispatch
    if args.command == "calc":
        calc_client.run(args)
    elif args.command == "setup":
        setup_client.run(args)
    elif args.command == "pseudo":
        pseudo_client.run(args)
    else:
        parser.print_help()
        return 0
    print(f"\nFinished! ⛳")
    return 0


def _heading():
    print(
        r"""
   '\                   .  .                        |>>
     \              .         ' .                   |
    O>>         .                 'o                |
     \       .                                      |
     /\    .                                        |
    / /  .'               DFT, but with a caddie 🏌️ |
^^^^^^^`^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"""
    )
