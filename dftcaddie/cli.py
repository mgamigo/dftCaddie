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
_caddie_heading()
    Heading for the client.
_show_heading()
    Return whether the welcome heading should be printed.
_build_parser()
    Build the caddie parser.
"""

import sys
import argparse
import logging

from dftcaddie.commands import calc, config, pseudo, sbatch, setup

__all__ = [
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

    #    logging.basicConfig(level=level, format="%(message)s")
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def _caddie_heading():
    print(r"""
   '\                   .  .                        |>>
     \              .         ' .                   |
    O>>         .                 'o                |
     \       .                                      |
     /\    .                                        |
    / /  .'                  Don’t shoot the caddie |
^^^^^^^`^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^""")


def _show_heading(args) -> bool:
    """Return whether the welcome heading should be printed."""
    return args.command in (None, "calc")


def _build_parser() -> argparse.ArgumentParser:
    """
    Build caddie parser

    Returns
    -------
    argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="caddie",
        description="DFT Caddie - Your assistant for DFT calculations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv).",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only show errors.",
    )
    subparsers = parser.add_subparsers(title="Commands", dest="command")

    # --- calc subcommand ---
    calc_parser = subparsers.add_parser(
        "calc",
        help="Start a new DFT calculation",
        description="Start a new DFT calculation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    calc.add_arguments(calc_parser)
    # --- setup subcommand ---
    setup_parser = subparsers.add_parser(
        "setup",
        help="Configure the calculation for a given system",
        description="Configure the calculation for a given system",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    setup.add_arguments(setup_parser)
    # --- pseudo subcommand ---
    pseudo_parser = subparsers.add_parser(
        "pseudo",
        help="Set the desired pseudopotentials",
        description="Set the desired pseudopotentials",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    pseudo.add_arguments(pseudo_parser)
    # --- sbatch subcommand ---
    sbatch_parser = subparsers.add_parser(
        "sbatch",
        help="Set the desired sbatch header",
        description="Set the desired sbatch header",
    )
    sbatch.add_arguments(sbatch_parser)
    # --- config subcommand ---
    config_parser = subparsers.add_parser(
        "config",
        help="Initialize or check configuration",
        description="Manage dftCaddie configuration and resources",
    )
    config.add_arguments(config_parser)
    # ---
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Run the dftCaddie command-line interface.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments (excluding the program name). If ``None``,
        arguments are taken from ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose, quiet=args.quiet)

    try:
        if _show_heading(args):
            _caddie_heading()
        # Dispatch
        if args.command == "calc":
            calc.run(args)
        elif args.command == "setup":
            setup.run(args)
        elif args.command == "pseudo":
            pseudo.run(args)
        elif args.command == "sbatch":
            sbatch.run(args)
        elif args.command == "config":
            status = config.run(args)
            if status:
                return status
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\n👋 Caddie has left the course.", file=sys.stderr)
        return 130
    print("\n⛳ Setup complete. May your jobs converge.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
