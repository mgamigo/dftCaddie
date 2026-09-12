"""
dftCaddie | dftcaddie.utils
===========================

Utility functions for dftCaddie.

This module collects small helpers used across the CLI clients and file
management routines, including:

- resolving the target cluster from the hostname,
- validating explicit option selections,
- inferring the current calculation kind/code from a working directory,
- reading basic structure data from a structure file,
- retrieving calculation configuration entries.

Functions
---------
resolve_cluster()
    Identify the cluster key based on the machine hostname.
check_option_exists()
    Validate that a value is contained in a list of allowed options.
resolve_calc_current_dir()
    Infer calculation kind and code from files in the current directory.
get_structure()
    Read a structure file and return basic structural information.
get_config()
    Retrieve a config entry by name for a given calculation kind.
"""

import logging
import sys
import os
from types import SimpleNamespace

from dftcaddie import config

log = logging.getLogger(__name__)

__all__ = [
    "resolve_cluster",
    "check_option_exists",
    "resolve_calc_current_dir",
    "get_structure",
    "get_config",
]


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


def check_option_exists(
    value: str | bool, options: list[str] | list[bool], name: str = None
) -> int:
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

    Returns
    -------
    int
        Exit code (0 on successful completion).
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
    return 0


def resolve_calc_current_dir() -> tuple[str, str, str]:
    """
    Infer calculation kind, flavor and code from files in the current directory.

    Returns
    -------
    tuple[str, str, str]
        (kind, flavor, code)

    Raises
    ------
    RuntimeError
        If no matching calculation definition is found or if the match is ambiguous.
    """
    present_files = set(f for f in os.listdir(".") if os.path.isfile(f))
    calculations = config.load_config()[0]["calculations"]

    matches = []

    def append_matches(matches, files):
        for code, expected_files in files.items():
            expected = set([os.path.basename(f) for f in expected_files])
            overlap = expected & present_files

            if overlap:
                matches.append(
                    {
                        "kind": kind,
                        "flavor": flavor,
                        "code": code,
                        "score": len(overlap),
                        "expected": len(expected),
                    }
                )

    for kind, kind_data in calculations.items():
        flavors = kind_data.get("flavors", None)
        if flavors is not None:
            for flavor, flavor_data in flavors.items():
                append_matches(matches, flavor_data["files"])
        else:
            flavor = None
            append_matches(matches, kind_data["files"])
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
        kinds = list(set([m["kind"] for m in equally_good]))
        codes = list(set([m["code"] for m in equally_good]))
        if len(kinds) == 1 and len(codes) == 1:
            log.debug(
                "Not possible to resolve between different flavors for kind/code =  %s/%s.",
                kinds[0],
                codes[0],
            )
            best["flavor"] = None
        else:
            raise RuntimeError(
                f"Ambiguous calculation definition detected: {equally_good}"
            )

    if best["flavor"] is None:
        log.info("Resolved calcualtion kind/code as %s/%s", best["kind"], best["code"])
    else:
        log.info(
            "Resolved calcualtion kind/flavor/code as %s/%s/%s",
            best["kind"],
            best["flavor"],
            best["code"],
        )

    return best["kind"], best["flavor"], best["code"]


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
        - ``atoms`` : ase.Atoms
            ase.Atoms object
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
        atoms=C.atoms,
    )
    return data


def get_config(kind: str, config_name: str, flavor: str = None) -> dict:
    """
    Retrieve a configuration entry by name for a given calculation kind.

    Parameters
    ----------
    kind : str
        Calculation kind (e.g., "relax", "bands").
    config_name : str
        Name of the configuration entry to retrieve.
    flavor : str, optional
        Calculation flavor (e.g., "fixed_cell", "variable_cell").

    Returns
    -------
    dict
        Configuration dictionary matching ``config_name``.

    Notes
    -----
    - If more than one flavor are present, but flavor is not provided. It
      retrieves the setting from the first flavor.

    Raises
    ------
    KeyError
        If the calculation kind or configuration name is not found.
    """
    calculations = config.load_config()[0]["calculations"]
    if flavor is not None:
        try:
            configs = calculations[kind]["flavors"][flavor]["config"]
        except KeyError as exc:
            raise KeyError(
                f"No config for calculation kind/flavor: '{kind}/{flavor}'"
            ) from exc
    else:
        try:
            possible_flavors = calculations[kind].get("flavors", None)
        except KeyError as exc:
            raise KeyError(f"No calculation kind: {kind!r}") from exc
        # No possible flavors
        if possible_flavors is None:
            try:
                configs = calculations[kind]["config"]
            except KeyError as exc:
                raise KeyError(f"No config for calculation kind: {kind!r}") from exc
        # More than one possible flavor (retrieve setting for first flavor)
        else:
            for flavor, flavor_data in possible_flavors.items():
                try:
                    configs = flavor_data["config"]
                    break
                except KeyError as exc:
                    raise KeyError(
                        f"No config for calculation kind/flavor: '{kind}/{flavor}'"
                    ) from exc

    for cfg in configs:
        if cfg.get("name") == config_name:
            return cfg

    raise KeyError(
        f"Configuration {config_name!r} not found for calculation kind {kind!r}"
    )
