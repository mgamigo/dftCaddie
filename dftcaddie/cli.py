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

from dftcaddie import file_management as files
from dftcaddie.config import cases

_all__ = [
    "main",
]


def _format_options(options: list[str], brackets: bool = False) -> str:
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
    if brackets:
        options = [f"[{x[0].upper()}]{x[1:]}" for x in options]
    return ", ".join(options)


def _resolve_user_input(user_input: str, options: list[str]) -> int:
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
    args = parser.parse_args(args if isinstance(args, list) else None)

    # Select calculation type
    options = list(cases.keys())
    option_strings = [cases[key]["name"] for key in options]
    print(f"Available Calculation Types:\n{_format_options(option_strings)}")
    user_input = input("Choose a calculation type: ").strip().lower()
    calc_type = options[_resolve_user_input(user_input, options)]

    # Select code
    options = cases[calc_type]["codes"]
    if len(options) > 1:
        print(f"\nAvailable Codes for {calc_type.title()}:")
        print(_format_options(options, brackets=True))
        user_input = input("Choose a code: ").strip().lower()
        code = options[_resolve_user_input(user_input, options)]
    else:
        code = options[1]

    # Additional options
    selections = []
    if "additional" in cases[calc_type].keys():
        additional = cases[calc_type]["additional"]
        for a in additional:
            print(f"\n{a['question']}")
            options = a["options"]
            print(_format_options(options, brackets=True))
            user_input = input("Select: ").strip().lower()
            selections.append(options[_resolve_user_input(user_input, options)])

    # Proceed with the operation using the user's selected options
    print(f"\nSummary\n=======")
    print(f"Selected Calculation Type: {calc_type.title()}")
    print(f"Selected Code: {code.title()}")
    if len(selections) != 0:
        for i in range(len(additional)):
            print(f'{additional[i]["name"].title()}: {selections[i].title()}')
    print(f"-------\n")

    # Utilize the mapping to get the list of files
    files_to_copy = cases[calc_type]["files"][code]
    if args.scratch and code == "quantum espresso":
        files_to_copy.append("SYSTEM.INFO")
    files_to_copy.append("master.sh")
    files.copy_input_files(code, files_to_copy, overwrite=args.overwrite)
    files.populate_master_script("master.sh", files_to_copy)

    print(f"\nFinished! ⛳")
