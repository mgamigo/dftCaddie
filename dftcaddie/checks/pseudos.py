"""
Read-only inspection of configured pseudopotential libraries.

Functions
---------
check_pseudos()
    Inspect all UPF and POTCAR libraries in a validated configuration.
inspect_upf_library()
    Report UPF candidates, metadata, and selection problems.
inspect_potcar_library()
    Report POTCAR candidates, headers, and selection problems.
"""

from pathlib import Path

from dftcaddie.utils import _potcar_candidates, read_upf_pseudo_metadata

__all__ = ["check_pseudos", "inspect_upf_library", "inspect_potcar_library"]


def check_pseudos(data: dict, source_dir: Path) -> list[dict]:
    """
    Inspect libraries from the configuration being checked, without caching.

    Parameters
    ----------
    data : dict
        Validated configuration, including optional suggested_upf_pseudos.
    source_dir : pathlib.Path
        Active configuration directory used to resolve relative library paths.

    Returns
    -------
    list of dict
        Inspection reports with library name and format (UPF or POTCAR).
    """
    reports = []
    for label, key in (
        ("UPF", "upf_pseudopotentials"),
        ("POTCAR", "potcar_pseudopotentials"),
    ):
        for name, settings in data.get(key, {}).get("libraries", {}).items():
            path = Path(settings["path"]).expanduser()
            if not path.is_absolute():
                path = Path(source_dir) / path
            library = dict(settings, path=path.absolute())
            if label == "UPF":
                report = inspect_upf_library(
                    library, suggestions=data.get("suggested_upf_pseudos", {})
                )
            else:
                report = inspect_potcar_library(
                    library, suggestions=data.get("suggested_potcar_pseudos", {})
                )
            reports.append(dict(report, name=name, format=label))
    return reports


def inspect_upf_library(library: dict, *, suggestions: dict | None = None) -> dict:
    """
    Inspect a resolved UPF library without changing its configuration or files.

    Parameters
    ----------
    library : dict
        Resolved library with path, filename pattern, and optional overrides.
        Schema validation belongs to the configuration checker.
    suggestions : dict, optional
        Element-to-filename preferences from the configuration being checked.

    Returns
    -------
    dict
        Absolute path, directory availability, matching file count, species
        mapped to candidate filenames, observed metadata values, and issues.
        Metadata summarizes non-missing type, exchange, relativity, and has_so.
        Issues include missing files, ambiguous selections, unreadable headers,
        and disagreement between the requested species and the UPF element.

    Notes
    -----
    Only pattern matches and overrides are inspected, allowing libraries to
    share directories. Suggestions and overrides resolve selection ambiguities
    as in get_upf_pseudo_paths(); all candidates remain visible in the report.
    Missing cutoff recommendations are allowed and values are read as declared.
    """
    from fnmatch import fnmatchcase
    from ase.data import chemical_symbols

    directory = Path(library["path"]).absolute()
    report = {
        "path": directory,
        "available": directory.is_dir(),
        "files": 0,
        "species": {},
        "metadata": {key: [] for key in ("type", "exchange", "relativity", "has_so")},
        "issues": [],
    }
    issues = report["issues"]
    if not report["available"]:
        issues.append(f"Library directory does not exist: {directory}")
        return report
    try:
        files = sorted(path for path in directory.iterdir() if path.is_file())
    except OSError as exc:
        issues.append(f"Cannot read library directory: {exc}")
        return report

    overrides = library.get("overrides", {})
    suggestions = suggestions or {}
    selected_files = {}
    for symbol in dict.fromkeys([*chemical_symbols[1:], *overrides]):
        pattern = library["pattern"].format(element=symbol)
        matches = [path for path in files if fnmatchcase(path.name, pattern)]
        if symbol in overrides:
            override = overrides[symbol]
            preferred = [path for path in files if path.name == override]
            if not preferred:
                issues.append(f"Missing override for {symbol}: {override!r}")
            matches = sorted(set(matches + preferred))
        else:
            suggestion = suggestions.get(symbol)
            preferred = (
                [path for path in matches if fnmatchcase(path.name, suggestion)]
                if suggestion
                else []
            ) or matches
        if not matches:
            continue
        report["species"][symbol] = [path.name for path in matches]
        for path in matches:
            selected_files.setdefault(path, []).append(symbol)
        if len(preferred) > 1:
            issues.append(
                f"Ambiguous selection for {symbol}: "
                + ", ".join(path.name for path in preferred)
            )

    report["files"] = len(selected_files)
    if not selected_files:
        issues.append("No files match the library pattern or overrides.")
    for path, symbols in sorted(selected_files.items()):
        try:
            metadata = read_upf_pseudo_metadata(path)
        except (OSError, UnicodeError, ValueError) as exc:
            issues.append(f"Cannot read {path.name}: {exc}")
            continue
        for symbol in symbols:
            if metadata["element"] != symbol:
                issues.append(
                    f"{path.name}: expected element {symbol}, "
                    f"UPF header declares {metadata['element']!r}."
                )
        for key, observed in report["metadata"].items():
            value = metadata[key]
            if value is not None and value not in observed:
                observed.append(value)
    for observed in report["metadata"].values():
        observed.sort()
    return report


def inspect_potcar_library(library: dict, *, suggestions: dict | None = None) -> dict:
    """
    Inspect a POTCAR library without modifying files or displaying their contents.

    Parameters
    ----------
    library : dict
        Resolved library path, relative pattern, and optional element overrides.
    suggestions : dict, optional
        Element-to-relative-path preferences from the configuration being checked.

    Returns
    -------
    dict
        Path, directory availability, file count, species-to-relative-path lists,
        observed type/exchange/relativity/has_so metadata, and issues. Type,
        exchange, and element are read from TITEL when available; relativity
        and SOC support are not inferred. Missing overrides, ambiguous matches,
        unreadable headers, and element mismatches are reported as issues.
    """
    import re
    from ase.data import chemical_symbols

    directory = Path(library["path"]).absolute()
    report = {
        "path": directory,
        "available": directory.is_dir(),
        "files": 0,
        "species": {},
        "metadata": {key: [] for key in ("type", "exchange", "relativity", "has_so")},
        "issues": [],
    }
    issues = report["issues"]
    if not report["available"]:
        issues.append(f"Library directory does not exist: {directory}")
        return report
    selected_files = {}
    overrides = library.get("overrides", {})
    for symbol in dict.fromkeys([*chemical_symbols[1:], *overrides]):
        try:
            matches = _potcar_candidates(library, symbol, suggestions=suggestions)
        except (OSError, ValueError) as exc:
            issues.append(f"Cannot inspect {symbol}: {exc}")
            continue
        if not matches:
            if symbol in overrides:
                issues.append(f"Missing override for {symbol}: {overrides[symbol]!r}")
            continue
        report["species"][symbol] = [
            str(path.relative_to(directory)) for path in matches
        ]
        if len(matches) > 1:
            issues.append(
                f"Ambiguous selection for {symbol}: "
                + ", ".join(report["species"][symbol])
            )
        for path in matches:
            selected_files.setdefault(path, []).append(symbol)
    report["files"] = len(selected_files)
    if not selected_files:
        issues.append("No files match the library pattern or overrides.")
    for path, symbols in sorted(selected_files.items()):
        name = str(path.relative_to(directory))
        try:
            with path.open() as source:
                title = next(
                    (
                        line.split("=", 1)[1].split()
                        for line in source
                        if re.match(r"\s*TITEL\s*=", line)
                    ),
                    [],
                )
        except (OSError, UnicodeError) as exc:
            issues.append(f"Cannot read {name}: {exc}")
            continue
        if len(title) < 2:
            issues.append(f"Missing or malformed TITEL in {name}.")
            continue
        element = title[1].split("_", 1)[0]
        for symbol in symbols:
            if element != symbol:
                issues.append(
                    f"{name}: expected element {symbol}, TITEL declares {element!r}."
                )
        pseudo_type, _, exchange = title[0].partition("_")
        for key, value in (("type", pseudo_type), ("exchange", exchange.lower())):
            observed = report["metadata"][key]
            if value and value not in observed:
                observed.append(value)
    for observed in report["metadata"].values():
        observed.sort()
    return report
