"""
dftCaddie | dftcaddie.utils
===========================

Utility functions for dftCaddie.

This module collects small helpers used across the CLI clients and file
management routines, including:

- resolving the target cluster from the hostname,
- formatting and validating interactive option selections,
- inferring the current calculation kind/code from a working directory,
- reading basic structure data from a structure file,
- retrieving calculation configuration entries.

Functions
---------
resolve_cluster()
    Identify the cluster key based on the machine hostname.
format_options()
    Format a list of options for CLI display.
resolve_user_input()
    Resolve a user selection against a list of allowed options.
check_option_exists()
    Validate that a value is contained in a list of allowed options.
resolve_calc_current_dir()
    Infer calculation kind and code from files in the current directory.
get_structure()
    Read a structure file and return basic structural information.
get_config()
    Retrieve a config entry by name for a given calculation kind.
"""

import sys
import os
from types import SimpleNamespace

from dftcaddie.config import calculations

__all__ = [
    "resolve_cluster",
    "format_options",
    "resolve_user_input",
    "check_option_exists",
    "resolve_calc_current_dir",
    "get_structure",
    "get_config",
    "affirmation2bool",
    "bool2affirmation",
]

affirmation2bool = {"yes": True, "no": False}
bool2affirmation = {True: "yes", False: "no"}


def resolve_cluster(clusters: dict) -> str:
    """
    Identifies the cluster key based on the machine's hostname.

    Parameters
    ----------
    clusters : dict
        A mapping of cluster keys to configurations containing a "hostname" entry.

    Returns
    -------
    str
        The cluster key that matches the current hostname, or None if no match is found.
    """
    import socket

    hostname = socket.gethostname()
    # Solve the appropiate heading:
    keys = list(clusters.keys())
    keys.remove("local")
    for k in keys:
        if clusters[k]["hostname"] in hostname:
            return k
    return "local"


def format_options(
    options: list[str] | list[bool], brackets: bool = False, numbers: bool = False
) -> str:
    """
    Formats a list of strings into a comma-separated string, with optional
    bracket or numbered notation.

    Parameters
    ----------
    options : list[str]
        A list of strings representing options to be formatted.
    brackets : bool, optional
        If True, encloses the first character of each option in brackets
        (default is False).
    numbers : bool, optional
        If True, each options are numbered. Preferred for many options.

    Returns
    -------
    str
        A formatted, comma-separated string of options.

    Notes
    -----
    - If options are booleans, they are written as "Yes/No"
    """
    if isinstance(options[0], bool):
        options = [bool2affirmation[key] for key in options]
    if brackets:
        options = [f"[{x[0].upper()}]{x[1:]}" for x in options]
    elif numbers:
        options = [
            f"[{i}] {x[0].upper()}{x[1:]}" for i, x in enumerate(options, start=1)
        ]
    return ", ".join(options)


def resolve_user_input(user_input: str, options: list[str] | list[bool]) -> str | bool:
    """
    Resolve user input to find its matched value in a list of options first by
    full match, then by partial match.

    Parameters
    ----------
    user_input : str
        The user's input string to match against the list of options.
    options : list[str]
        A list of strings representing possible options to match.

    Returns
    -------
    str | bool
        The matched option itself.

    Notes
    -----
    - If no match is found, an error message is printed and execution is
    terminated.
    - If options are booleans, yes/no user input is read as True/False.
    """
    # Handle numbered input.
    try:
        user_input = int(user_input)
    except ValueError:
        pass
    if isinstance(user_input, int):
        return options[user_input - 1]

    # Handle boolean options
    boolean = False
    if isinstance(options[0], bool):
        boolean = True
        options = [bool2affirmation[key] for key in options]

    # Try full match first
    if user_input in options:
        matched_option = user_input
    else:
        # Try partial match (based on starting characters)
        partial_matches = [
            option for option in options if option.startswith(user_input)
        ]

        if len(partial_matches) >= 1:
            matched_option = partial_matches[0]  # Return the first partial match
        else:
            # Print error and terminate process if no match is found
            print(
                f"Error: No match found for input: '{user_input}'. Exiting the process."
            )
            sys.exit(1)  # Exit with a status code indicating an error
    if boolean:
        return affirmation2bool[matched_option]
    else:
        return matched_option


def check_option_exists(
    value: str | bool, options: list[str] | list[bool], name: str = None
) -> None:
    """
    Checks if a value exists within a list of options, printing an error
    and exiting if not.

    Parameters
    ----------
    value : str | bool
        The value to check against the list of options.
    options : list[str] | list[bool]
        The list of valid options.
    name : str, optional
        The name of the parameter being validated, included in the error
        message if provided.
    """
    if value not in options:
        if name is None:
            print(f"Error: No match found for '{value}'. Supported values are:")
        else:
            print(
                f"Error: No match found for '{name}' = '{value}'. Supported values are:"
            )
        print(f"{list(options)}")
        print(f"Exiting the process.")
        sys.exit(1)  # Exit with a status code indicating an error


def resolve_calc_current_dir():
    """
    Infer calculation kind and code from files in the current directory.

    Returns
    -------
    tuple[str, str]
        (kind, code)

    Raises
    ------
    RuntimeError
        If no matching calculation setup is found or if the match is ambiguous.
    """
    present_files = set(f for f in os.listdir(".") if os.path.isfile(f))

    matches = []

    for kind, kind_data in calculations.items():
        for code, expected_files in kind_data["files"].items():
            expected = set(expected_files)
            overlap = expected & present_files

            if overlap:
                matches.append(
                    {
                        "kind": kind,
                        "code": code,
                        "score": len(overlap),
                        "expected": len(expected),
                    }
                )

    if not matches:
        raise RuntimeError(
            "Could not infer calculation kind/code from directory contents."
        )

    # Prefer full matches, otherwise best overlap
    matches.sort(key=lambda x: (x["score"] == x["expected"], x["score"]), reverse=True)
    best = matches[0]

    # Ambiguity check
    equally_good = [
        m
        for m in matches
        if m["score"] == best["score"] and m["expected"] == best["expected"]
    ]
    if len(equally_good) > 1:
        raise RuntimeError(f"Ambiguous calculation setup detected: {equally_good}")

    return best["kind"], best["code"]


def get_structure(file: str) -> SimpleNamespace:
    """
    Read a crystal structure file and extract basic structural information.

    This function loads a structure from file, extracts lattice vectors,
    atomic symbols, fractional atomic positions, chemical formula, and
    space-group information, and returns them in a simple container.

    Parameters
    ----------
    file : str
        Path to a structure file readable by ``Cell.from_file`` (e.g. CIF,
        POSCAR, or other supported formats).

    Returns
    -------
    SimpleNamespace
        Container with the following attributes:

        - ``formula`` : str
            Chemical formula of the structure.
        - ``lattice`` : ndarray, shape (3, 3)
            Lattice vectors.
        - ``symbols`` : list[str]
            Chemical symbols for each atom.
        - ``positions`` : ndarray, shape (N, 3)
            Fractional atomic positions.
        - ``space_group`` : str
            Space-group number extracted from spglib.
    """
    import numpy as np
    import spglib as spg
    from yaiv.cell import Cell

    C = Cell.from_file(file)
    formula = C.atoms.get_chemical_formula()
    lattice = np.asarray(C.atoms.get_cell())
    symbols = C.atoms.get_chemical_symbols()
    positions = np.asarray(C.atoms.get_scaled_positions())
    space_group = spg.get_spacegroup(C).split("(")[1].split(")")[0]
    data = SimpleNamespace(
        formula=formula,
        lattice=lattice,
        symbols=symbols,
        positions=positions,
        space_group=space_group,
    )
    return data


def get_config(kind: str, config_name: str) -> dict:
    """
    Retrieve a configuration entry by name for a given calculation kind.

    Parameters
    ----------
    kind : str
        Calculation kind (e.g., "relax", "bands").
    config_name : str
        Name of the configuration entry to retrieve.

    Returns
    -------
    dict
        Configuration dictionary matching ``config_name``.

    Raises
    ------
    KeyError
        If the calculation kind or configuration name is not found.
    """
    try:
        configs = calculations[kind]["config"]
    except KeyError as exc:
        raise KeyError(f"Unknown calculation kind: {kind!r}") from exc

    for cfg in configs:
        if cfg.get("name") == config_name:
            return cfg

    raise KeyError(
        f"Configuration {config_name!r} not found for calculation kind {kind!r}"
    )
