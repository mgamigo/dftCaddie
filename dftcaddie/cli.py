"""
dftCaddie | dftcaddie.cli
=========================

This module provides a command-line client interface for ...

Functions
---------
main(...)
    Command-line client for ...
"""

import sys
import argparse

from dftcaddie import file_management as files

__all__ = [
    "main",
]

cases = {
    "bands": {
        "name": "[B]ands",
        "codes": ["quantum espresso", "vasp"],
        "files": {
            "quantum espresso": ["scf.sh", "bands.sh", "project_bands.sh"],
            "vasp": ["INCAR.SCC", "INCAR.BS", "KPOINTS.SCC"],
        },
    },
    "relax": {
        "name": "[R]elax",
        "codes": ["quantum espresso", "vasp"],
        "additional": [
            {
                "name": "cell relaxation",
                "question": "Do you want also a cell relaxation?",
                "options": ["yes", "no"],
            }
        ],
        "files": {
            "quantum espresso": ["relax.sh"],
            "vasp": ["INCAR.RELAX", "KPOINTS.SCC"],
        },
    },
}


def _format_options(options, brackets=False):
    """
    Format a list of options into a comma-separated string.

    :param options: List of options to format
    :return: A formatted string
    """
    if brackets:
        options = [f"[{x[0].upper()}]{x[1:]}" for x in options]
    return ", ".join(options)


def _resolve_user_input(user_input, options):
    """
    Resolve user input to find its index in a list of options first by full match, then by partial match.

    :param user_input: The user's input (string)
    :param options: List of options to match against
    :return: Index of matched option or None if no match is found
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

    # If no match is found, return None or a specific value (-1)
    return None


def main(args=None):
    """
    Command-line client for dftCaddie.

    Longer description
    """
    if args is None:
        args = sys.argv[1:]  # Default to command-line arguments
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Test caddie client description.",
        epilog="Example: caddie use example",
    )
    parser.add_argument(
        "-s",
        "--scratch",
        action='store_true',
        help="Start calculation from scratch"
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
        files_to_copy.append('SYSTEM.INFO')
    files_to_copy.append('master.sh')
    files.copy_input_files(code, files_to_copy)

    print(f"\nFinished!")
