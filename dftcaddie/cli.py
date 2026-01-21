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
_format_options(options)
    Formats a list of strings into a comma-separated string.

_resolve_user_input(user_input, options)
    Resolve user input to find its index in a list of options.
"""

import sys
import argparse
import socket
from types import SimpleNamespace

from dftcaddie import file_management as files
from dftcaddie.config import cases

_all__ = [
    "main",
]

affirmation2bool = {"yes": True, "no": False}
bool2affirmation = {True: "yes", False: "no"}


def _format_options(options: list[str] | list[bool], brackets: bool = False) -> str:
    """
    Formats a list of strings into a comma-separated string, with optional
    bracket notation for the first character of each string.

    Parameters
    ----------
    options : list[str]
        A list of strings representing options to be formatted.

    brackets : bool, optional
        If True, encloses the first character of each option in brackets
        (default is False).

    Returns
    -------
    str
        A formatted, comma-separated string of options.
    """
    if isinstance(options[0], bool):
        options = [bool2affirmation[key] for key in options]
    if brackets:
        options = [f"[{x[0].upper()}]{x[1:]}" for x in options]
    return ", ".join(options)


def _resolve_user_input(user_input: str, options: list[str] | list[bool]) -> int:
    """
    Resolve user input to find its index in a list of options first by
    full match, then by partial match.

    Parameters
    ----------
    user_input : str
        The user's input string to match against the list of options.

    options : list[str]
        A list of strings representing possible options to match.

    Returns
    -------
    int
        Index of the matched option.

    Notes
    -----
    If no match is found, an error message is printed and execution is
    terminated.
    """
    # Change if options are booleans.
    if isinstance(options[0], bool):
        options = [bool2affirmation[key] for key in options]

    # Try full match first
    if user_input in options:
        return options.index(user_input)

    # Try partial match (based on starting characters)
    partial_matches = [
        index for index, option in enumerate(options) if option.startswith(user_input)
    ]

    if partial_matches:
        return partial_matches[0]  # Return the index of the first partial match

    # Print error and terminate process if no match is found
    print(f"Error: No match found for input: '{user_input}'. Exiting the process.")
    sys.exit(1)  # Exit with a status code indicating an error


def main(args=None):
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
        "--hostname",
        required=False,
        metavar="HOST",
        help="Hostname for automatic SBATCH heading.",
    )

    parsed_args = parser.parse_args(args if isinstance(args, list) else None)
    calculation = SimpleNamespace(**vars(parsed_args))

    if calculation.hostname is None:
        calculation.hostname = socket.gethostname()

    # Select calculation type
    if calculation.kind is None:
        options = list(cases.keys())
        option_strings = [cases[key]["name"] for key in options]
        print(f"Available Calculation Types:\n{_format_options(option_strings)}")
        user_input = input("Choose a calculation type: ").strip().lower()
        calculation.kind = options[_resolve_user_input(user_input, options)]

    # Select code
    if calculation.code is None:
        options = cases[calculation.kind]["codes"]
        if len(options) > 1:
            print(f"\nAvailable Codes for {calculation.kind.title()}:")
            print(_format_options(options, brackets=True))
            user_input = input("Choose a code: ").strip().lower()
            calculation.code = options[_resolve_user_input(user_input, options)]
        else:
            calculation.code = options[1]

    # Additional options
    if "additional" in cases[calculation.kind].keys():
        settings = cases[calculation.kind]["additional"]
        for x in settings:
            print(f"\n{x['question']}")
            options = x["options"]
            print(_format_options(options, brackets=True))
            user_input = input("Select: ").strip().lower()
            answer = options[_resolve_user_input(user_input, options)]
            calculation.__setattr__(x["name"], answer)

    # Proceed with the operation using the user's selected options
    print(f"\nSummary\n=======")
    print(f"Calculation Type: {calculation.kind.title()}")
    print(f"Code: {calculation.code.title()}")
    keys = list(calculation.__dict__.keys())
    for x in ["code", "kind"]:
        keys.remove(x)
    for key in keys:
        print(f"{key}: {calculation.__getattribute__(key)}")
    print(f"-------\n")

    # Utilize the mapping to get the list of files
    copied_files = files.copy_input_files(calculation)
    files.populate_master_script("master.sh", copied_files)
    files.set_master_preamble("master.sh", hostname=calculation.hostname)

    print(f"\nFinished! ⛳")
