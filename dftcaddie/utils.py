"""
dftCaddie | dftcaddie.utils
===========================

Utility functions for dftCaddie.

This module collects small helpers used across the CLI clients and file
management routines, including:

- resolving the target cluster from the hostname,
- validating explicit option selections,
- inferring calculation kind/code from a directory,
- reading basic structure data from a structure file,
- retrieving calculation configuration entries.

Functions
---------
resolve_cluster()
    Identify the cluster key based on the machine hostname.
check_option_exists()
    Validate that a value is contained in a list of allowed options.
resolve_calculation_directory()
    Infer calculation kind and code from files in a directory.
get_structure()
    Read a structure file and return basic structural information.
get_config()
    Retrieve a config entry by name for a given calculation kind.
read_upf_pseudo_metadata()
    Read physical metadata and available cutoff recommendations from UPF 2.
get_upf_pseudo_paths()
    Select QE pseudopotential files from a configured library.
get_qe_cutoffs()
    Resolve wavefunction and charge-density cutoffs in Ry.
get_potcar_paths()
    Select POTCAR files from a configured library in POSCAR group order.

Private functions
-----------------
_potcar_candidates()
    Find matching POTCAR files using overrides, suggestions, and library patterns.
"""

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

from dftcaddie import config

log = logging.getLogger(__name__)

__all__ = [
    "resolve_cluster",
    "check_option_exists",
    "resolve_calculation_directory",
    "get_structure",
    "get_config",
    "read_upf_pseudo_metadata",
    "get_upf_pseudo_paths",
    "get_qe_cutoffs",
    "get_potcar_paths",
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


def resolve_calculation_directory(directory: str | Path) -> tuple[str, str, str]:
    """
    Infer calculation kind, flavor and code from files in a directory.

    Parameters
    ----------
    directory : str or pathlib.Path
        Calculation directory whose regular files are used for detection.

    Returns
    -------
    tuple[str, str, str]
        (kind, flavor, code)

    Raises
    ------
    RuntimeError
        If no matching calculation definition is found or if the match is ambiguous.
    """
    directory = Path(directory)
    present_files = {path.name for path in directory.iterdir() if path.is_file()}
    from dftcaddie.calculation import iter_calculation_definitions

    settings = config.load_config()[0]

    matches = []

    def append_matches(matches, files):
        for code, expected_files in files.items():
            expected = {Path(file).name for file in expected_files}
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

    for kind, flavor, definition in iter_calculation_definitions(settings):
        append_matches(matches, definition["files"])
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
    from dftcaddie.calculation import (
        get_calculation_definition,
        iter_calculation_definitions,
    )

    settings = config.load_config()[0]
    if flavor is not None:
        try:
            configs = get_calculation_definition(settings, kind, flavor)["config"]
        except (KeyError, ValueError) as exc:
            raise KeyError(
                f"No config for calculation kind/flavor: '{kind}/{flavor}'"
            ) from exc
    else:
        variants = [
            definition
            for variant_kind, _, definition in iter_calculation_definitions(settings)
            if variant_kind == kind
        ]
        if not variants:
            raise KeyError(f"No calculation kind: {kind!r}")
        configs = variants[0]["config"]

    for cfg in configs:
        if cfg.get("name") == config_name:
            return cfg

    raise KeyError(
        f"Configuration {config_name!r} not found for calculation kind {kind!r}"
    )


def read_upf_pseudo_metadata(path: str | Path) -> dict:
    """
    Read UPF 2 metadata.

    Parameters
    ----------
    path : str or pathlib.Path
        Pseudopotential file containing an attribute-based PP_HEADER.

    Returns
    -------
    dict
        Element, type (the UPF pseudo_type label), exchange, relativity, has_so,
        ecutwfc, and ecutrho. Cutoffs are in Ry as declared by the UPF header.
        Absent fields are None; exchange and relativity are lowercased. A false
        has_so does not distinguish scalar from nonrelativistic treatment.

    Raises
    ------
    ValueError
        The header is absent, uses the unsupported UPF 1 format, or contains
        malformed boolean or cutoff data.
        File access and decoding errors propagate.

    Notes
    -----
    Only PP_HEADER is parsed as XML, since other sections may contain non-XML
    generator text. Read wfc_cutoff/rho_cutoff as declared; zero values mean
    unavailable recommendations. Fortran D exponents are supported. Free-text
    recommendations and provider-specific interpretations are not parsed.
    """
    import math
    import re
    from xml.etree import ElementTree

    path = Path(path)
    text = path.read_text()
    header = re.search(r"<PP_HEADER\b[^>]*>", text)
    if header is None:
        raise ValueError(f"No PP_HEADER found in {path}.")
    tag = header.group().rstrip(">").rstrip().rstrip("/") + "/>"
    try:
        attrs = ElementTree.fromstring(tag).attrib
    except ElementTree.ParseError as exc:
        raise ValueError(f"Malformed PP_HEADER in {path}: {exc}") from exc
    if not attrs:
        raise ValueError(f"Expected an attribute-based UPF 2 PP_HEADER in {path}.")

    has_so = attrs.get("has_so")
    if has_so is not None:
        boolean = has_so.strip().lower().strip(".")
        if boolean not in {"t", "true", "f", "false"}:
            raise ValueError(f"Invalid has_so value {has_so!r} in {path}.")
        has_so = boolean in {"t", "true"}

    def cutoff(attribute):
        """Read a cutoff attribute in Ry, with zero meaning unavailable."""
        raw = attrs.get(attribute)
        if raw is None:
            return None
        try:
            value = float(raw.replace("D", "E").replace("d", "e"))
        except ValueError as exc:
            raise ValueError(f"Invalid {attribute} {raw!r} in {path}.") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Invalid {attribute} {raw!r} in {path}.")
        return value or None

    return {
        "element": attrs.get("element", "").strip().capitalize() or None,
        "type": attrs.get("pseudo_type", "").strip() or None,
        "exchange": attrs.get("functional", "").strip().lower() or None,
        "relativity": attrs.get("relativistic", "").strip().lower() or None,
        "has_so": has_so,
        "ecutwfc": cutoff("wfc_cutoff"),
        "ecutrho": cutoff("rho_cutoff"),
    }


def get_upf_pseudo_paths(library: dict, symbols: Iterable[str]) -> dict[str, Path]:
    """
    Select one pseudopotential per species from a resolved QE library.

    Parameters
    ----------
    library : dict
        Settings returned by resolve_upf_library(), including path, pattern,
        and optional overrides mapping elements to exact filenames.
    symbols : iterable of str
        Atomic species in structure order. Repeated elements are selected once.

    Returns
    -------
    dict[str, Path]
        Species-to-path mapping in first-occurrence order. All selected files
        are direct children of the library directory.

    Raises
    ------
    FileNotFoundError
        The library directory or a species' matching file is missing.

    Warns
    -----
    UserWarning
        Multiple candidates remain; the first filename alphabetically is used.

    Notes
    -----
    Exact library overrides take precedence. Otherwise, format the library
    glob with the element and prefer matches of its optional global
    suggested_upf_pseudos glob. An absent suggestion leaves the original matches
    intact. Matching is case-sensitive and preserves version suffixes. This
    function does not read UPF metadata or validate physical compatibility.
    """
    from fnmatch import fnmatchcase
    import warnings

    directory = Path(library["path"]).absolute()
    files = sorted(path for path in directory.iterdir() if path.is_file())
    suggestions = config.load_config()[0].get("suggested_upf_pseudos", {})
    overrides = library.get("overrides", {})
    pseudos = {}
    for symbol in dict.fromkeys(symbols):
        if symbol in overrides:
            target = overrides[symbol]
            matches = [path for path in files if path.name == target]
        else:
            target = library["pattern"].format(element=symbol)
            matches = [path for path in files if fnmatchcase(path.name, target)]
            suggestion = suggestions.get(symbol)
            if suggestion:
                preferred = [
                    path for path in matches if fnmatchcase(path.name, suggestion)
                ]
                matches = preferred or matches
        if not matches:
            raise FileNotFoundError(
                f"No pseudopotential for {symbol} in {directory} "
                f"matching {target!r}. Check the library pattern or override."
            )
        if len(matches) > 1:
            warnings.warn(
                f"Multiple pseudopotentials for {symbol} in {directory}: "
                f"{', '.join(path.name for path in matches)}. "
                f"Using {matches[0].name} (first alphabetically). "
                "Set an element override to choose explicitly.",
                UserWarning,
                stacklevel=2,
            )
        pseudos[symbol] = matches[0]
    return pseudos


def get_qe_cutoffs(
    pseudos: dict[str, Path], *, defaults: dict | None = None, ratio: float = 1.5
) -> tuple[int, int]:
    """
    Resolve QE cutoffs from UPF recommendations and optional defaults.

    Parameters
    ----------
    pseudos : dict[str, Path]
        Species-to-path mapping returned by get_upf_pseudo_paths().
    defaults : dict, optional
        Fallback ecutwfc and/or ecutrho for missing recommendations. Numbers
        mean Ry; unit-bearing strings (e.g. "30 hartree") and quantities from
        yaiv.defaults.config.ureg are also accepted. Defaults are starting
        values for convergence tests, before applying the safety factor.
    ratio : float, optional
        Positive finite multiplier applied to both maxima, by default 1.5.

    Returns
    -------
    tuple[int, int]
        Wavefunction and charge-density cutoffs in Ry, rounded upward after
        taking each maximum across species and applying the safety factor.

    Raises
    ------
    ValueError
        No species were supplied, or a cutoff or ratio is not finite/positive.
    RuntimeError
        A species has neither a recommendation nor a default for a cutoff.
        UPF parsing errors and incompatible-unit errors propagate.

    Warns
    -----
    UserWarning
        A default was used in place of a missing UPF recommendation.
    """
    import math
    import warnings
    from yaiv.defaults.config import ureg

    if not pseudos:
        raise ValueError("Supply at least one pseudopotential to resolve cutoffs.")
    if isinstance(ratio, bool) or not math.isfinite(ratio) or ratio <= 0:
        raise ValueError("Cutoff safety factor must be finite and positive.")
    defaults = defaults or {}
    maxima = {"ecutwfc": 0.0, "ecutrho": 0.0}
    for symbol, path in pseudos.items():
        metadata = read_upf_pseudo_metadata(path)
        for key in maxima:
            value = metadata[key]
            fallback = value is None
            if fallback:
                value = defaults.get(key)
            if value is None:
                raise RuntimeError(
                    f"No {key} recommendation for {symbol} in {path}; "
                    f"supply a {key} default."
                )
            if isinstance(value, (str, ureg.Quantity)):
                value = ureg.Quantity(value).to("Ry").magnitude
            else:
                if isinstance(value, bool):
                    raise ValueError(f"Invalid {key} for {symbol}: {value!r}.")
                value = ureg.Quantity(value, "Ry").to("Ry").magnitude
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} for {symbol} must be finite and positive.")
            if fallback:
                warnings.warn(
                    f"No {key} recommendation for {symbol}; using default "
                    f"{value:g} Ry before the safety factor.",
                    UserWarning,
                    stacklevel=2,
                )
            maxima[key] = max(maxima[key], value)
    return tuple(math.ceil(value * ratio) for value in maxima.values())


def _potcar_candidates(
    library: dict, symbol: str, *, suggestions: dict | None = None
) -> list[Path]:
    """
    Find POTCAR candidates for one element using configured preferences.

    Parameters
    ----------
    library : dict
        Resolved library path, relative filename pattern, and optional exact
        relative-path overrides per element.
    symbol : str
        Chemical element symbol used to format the library pattern.
    suggestions : dict, optional
        Element-to-relative-path globs from suggested_potcar_pseudos.

    Returns
    -------
    list[pathlib.Path]
        Absolute matching file paths in alphabetical order, or an empty list
        when no file matches. Ambiguity is left for the caller to handle.

    Raises
    ------
    ValueError
        A selection path is absolute or contains a parent-directory component.

    Notes
    -----
    An explicit override is mandatory and prevents fallback. Otherwise, an
    existing suggestion takes precedence over the library pattern. Used by
    both POTCAR selection and library inspection to keep their rules aligned.
    """
    directory = Path(library["path"]).absolute()
    overrides = library.get("overrides", {})
    if symbol in overrides:
        targets = [overrides[symbol]]
    else:
        targets = []
        if suggestions and symbol in suggestions:
            targets.append(suggestions[symbol])
        targets.append(library["pattern"].format(element=symbol))
    for target in targets:
        relative = Path(target)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"POTCAR selection must stay inside {directory}.")
        candidates = (
            [directory / relative] if symbol in overrides else directory.glob(target)
        )
        matches = sorted(path for path in candidates if path.is_file())
        if matches:
            return matches
    return []


def get_potcar_paths(library: dict, symbols: Iterable[str]) -> list[Path]:
    """
    Select POTCARs from a named library in consecutive species-group order.

    Parameters
    ----------
    library : dict
        Resolved path, relative glob pattern such as ``{element}/POTCAR``,
        and optional exact relative-path overrides per element.
    symbols : iterable of str
        Chemical symbols in atom order, matching the unsorted POSCAR.

    Returns
    -------
    list[pathlib.Path]
        One absolute path per consecutive species group. Nonconsecutive
        repetitions are retained to match ASE's unsorted POSCAR output.

    Raises
    ------
    FileNotFoundError
        The directory or a requested species' POTCAR is missing.
    ValueError
        A configured pattern or override leaves the library directory.

    Warns
    -----
    UserWarning
        Multiple files match; the first path alphabetically is selected.

    Notes
    -----
    Overrides take precedence over suggested_potcar_pseudos relative-path
    preferences. If no suggested file exists, use the library pattern.
    No implicit bare, pv, or sv preference is used.
    Selection does not inspect the physical metadata in POTCAR files.
    """
    from itertools import groupby
    import warnings

    directory = Path(library["path"]).absolute()
    if not directory.is_dir():
        raise FileNotFoundError(f"POTCAR library directory does not exist: {directory}")
    suggestions = config.load_config()[0].get("suggested_potcar_pseudos", {})
    selected = {}
    pseudos = []
    for symbol, _ in groupby(symbols):
        if symbol not in selected:
            matches = _potcar_candidates(library, symbol, suggestions=suggestions)
            if not matches:
                raise FileNotFoundError(
                    f"No POTCAR for {symbol} in {directory}. "
                    "Check the library pattern or override."
                )
            if len(matches) > 1:
                warnings.warn(
                    f"Multiple POTCARs for {symbol} in {directory}: "
                    + ", ".join(str(path.relative_to(directory)) for path in matches)
                    + f". Using {matches[0].relative_to(directory)} "
                    "(first alphabetically). Set an element override to choose explicitly.",
                    UserWarning,
                    stacklevel=2,
                )
            selected[symbol] = matches[0]
        pseudos.append(selected[symbol])
    return pseudos
