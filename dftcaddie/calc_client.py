"""
dftCaddie | dftcaddie.calc_client
=================================

TODO

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
_resolve_cluster(clusters)
    Identifies the cluster key based on the machine's hostname.

_format_options(options)
    Formats a list of strings into a comma-separated string.

_resolve_user_input(user_input, options)
    Resolve user input to find its index in a list of options.

_check_option_exists(value, options)
    Checks if a value exists within a list of options.
"""

import sys
import argparse
import socket
from types import SimpleNamespace

from dftcaddie import file_management as files
from dftcaddie.config import cases, clusters


def (args=None):
    """
    Command-line client for dftCaddie that facilitates the setup of DFT
    calculations. It allows users to select calculation types and codes,
    offers additional configuration options, and prepares necessary input
    files for execution.

    Parameters
    ----------
    args : list, optional
        A list of command-line arguments. Defaults to None, in which case
        system-provided command-line arguments are used.
    """
    if args is None:
        args = sys.argv[1:]  # Default to command-line arguments
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Test caddie client description.",
        epilog="Example: caddie use example",
    )
    parser.add_argument(
        "-s", "--scratch", action="store_true", help="Start calculation from scratch"
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite existing files if necessary",
    )
    parser.add_argument(
        "-st",
        "--structure",
        required=False,
        metavar="file",
        help="File from which to read the crystal structure",
    )
    parser.add_argument(
        "-d",
        "--details",
        action="store_true",
        help="Ask for details instead of going for default values",
    )
    parser.add_argument(
        "--kind",
        required=False,
        metavar="CALC",
        help="Calculation kind (e.g., bands, relax)",
    )
    parser.add_argument(
        "--code",
        required=False,
        metavar="CODE",
        help="DFT code to use (e.g., vasp, quantum espresso)",
    )
    parser.add_argument(
        "--cluster",
        required=False,
        metavar="CLUSTER",
        help="Cluster for automatic SBATCH heading.",
    )

    parsed_args = parser.parse_args(args if isinstance(args, list) else None)
    calculation = SimpleNamespace(**vars(parsed_args))
    details = parsed_args.details
    calculation.__delattr__("details")

    if calculation.cluster is None:
        # calculation.hostname = socket.gethostname()
        calculation.cluster = _resolve_cluster(clusters)
    print(f"dftCaddie 🏌️\n" f"============\n")

    # Select calculation type
    if calculation.kind is None:
        options = list(cases.keys())
        option_strings = [cases[key]["name"] for key in options]
        print(f"Available Calculation Types:\n{_format_options(option_strings)}")
        user_input = input("Choose a calculation type: ").strip().lower()
        calculation.kind = _resolve_user_input(user_input, options)
    _check_option_exists(calculation.kind, cases.keys())

    # Additional configuration
    if "config" in cases[calculation.kind].keys():
        settings = cases[calculation.kind]["config"]
        for x in settings:
            options = x["options"]
            try:
                value = calculation.__getattribute__(x["name"])
            except AttributeError:
                value = None
            if value is None:
                if "default" in x.keys() and not details:
                    value = x["default"]
                elif len(options) == 1:
                    value = options[0]
                else:
                    print(f"\n{x['question']}")
                    print(_format_options(options, brackets=True))
                    user_input = input("Select: ").strip().lower()
                    value = _resolve_user_input(user_input, options)
                calculation.__setattr__(x["name"], value)
            _check_option_exists(value, options, x["name"])

    # Proceed with the operation using the user's selected options
    print(f"\nSummary\n-------")
    print(f"Calculation Type: {calculation.kind.title()}")
    print(f"Code: {calculation.code.title()}")
    keys = list(calculation.__dict__.keys())
    for x in ["code", "kind"]:
        keys.remove(x)
    for key in keys:
        print(f"{key.title()}: {calculation.__getattribute__(key)}")
    print(f"-------\n")

    files.prepare_calculation(calculation)

    print(f"\nFinished! ⛳")
