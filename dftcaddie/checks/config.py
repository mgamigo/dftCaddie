"""
dftCaddie | dftcaddie.checks.config
====================================

Reusable validation of configuration data and referenced resources.

This module does not import the active configuration, so it can inspect invalid
user files and can also be called by tests with bundled or temporary resources.

Classes
-------
ConfigIssue
    Validation error or warning with a severity, location, and message.

Functions
---------
validate_config()
    Check configuration structure, resources, and calculation distinguishability.

Private functions
-----------------
_validate_defaults(), _validate_clusters()
    Check global defaults, executable names, and scheduler resources.
_validate_calculations(), _validate_recipe_settings()
    Check recipe questions, template files, and calculation distinguishability.
_validate_kpaths()
    Check k-path resources for the backends referenced by recipes.
_validate_libraries(), _validate_library_defaults(), _validate_suggestions()
    Check per-code defaults, named libraries, and grouped suggestion patterns.
_validate_library()
    Check each library's directory and selection settings.
_validate_library_pattern(), _validate_library_overrides(), _validate_library_cutoffs()
    Check filename rules, exact files, and optional UPF cutoff defaults.
_check_pseudo_filename(), _error(), _check_mapping(), _check_string()
_check_string_list(), _check_file()
    Collect issues and perform shared value and file checks.
"""

from dataclasses import dataclass
import math
from pathlib import Path
from string import Formatter

from ase.data import atomic_numbers


@dataclass(frozen=True)
class ConfigIssue:
    """A validation error or warning at a named configuration location."""

    level: str
    location: str
    message: str


def validate_config(data, source_dir: Path) -> list[ConfigIssue]:
    """
    Check configuration structure, resources, and calculation distinguishability.

    Parameters
    ----------
    data : object
        Parsed YAML content. Invalid types are reported as errors.
    source_dir : pathlib.Path
        Root for templates, SBATCH headers, and k-path resources.

    Returns
    -------
    list of ConfigIssue
        All detected errors and warnings, including invalid configured locations.

    Notes
    -----
    No files are modified and no external programs are executed. Checks cover
    configuration consistency, not scientific input correctness.
    """
    # Collect independent problems in one pass; guard nested sections before
    # reading them because the YAML itself may be malformed.
    issues = []
    # Resource paths belong to this YAML, which may be a user copy.
    source_dir = Path(source_dir)
    if not _check_mapping(issues, data, "config"):
        return issues

    _validate_defaults(data, issues)
    _validate_clusters(data, source_dir, issues)
    codes_used = _validate_calculations(data, source_dir, issues)
    _validate_kpaths(codes_used, source_dir, issues)
    _validate_libraries(data, source_dir, issues)
    return issues


def _validate_defaults(data, issues):
    """Check numeric defaults and executable names."""
    # Scalar defaults -------------------------------------------------------
    # Exact numeric types exclude bool, which Python treats as an integer.
    for key in ("default_kppra", "nscf_kppra_ratio", "default_cutoff_ratio"):
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            _error(issues, key, "Expected a finite positive number.")

    # Global executables ---------------------------------------------------
    _check_string_list(issues, data.get("mpi_executables"), "mpi_executables")


def _validate_clusters(data, source_dir, issues):
    """Check cluster settings and referenced SBATCH headers."""
    # Cluster definitions and SBATCH headers --------------------------------
    clusters = data.get("clusters")
    if _check_mapping(issues, clusters, "clusters"):
        if "local" not in clusters:
            _error(issues, "clusters", "Missing fallback cluster 'local'.")
        # Visit each cluster and then its selectable scheduler-header presets.
        for name, cluster in clusters.items():
            location = f"clusters.{name}"
            if not _check_mapping(issues, cluster, location):
                continue
            hostname = cluster.get("hostname")
            if not isinstance(hostname, str) or (name != "local" and not hostname):
                _error(
                    issues,
                    location + ".hostname",
                    "Expected a hostname (empty only for local).",
                )
            _check_string(issues, cluster.get("mpi_command"), location + ".mpi_command")
            headers = cluster.get("headers")
            if not isinstance(headers, list) or not headers:
                _error(issues, location + ".headers", "Expected a nonempty list.")
                continue
            # Header names must be unique within this cluster, not globally.
            names = set()
            for i, header in enumerate(headers):
                entry = f"{location}.headers[{i}]"
                if not _check_mapping(issues, header, entry):
                    continue
                name = header.get("name")
                if _check_string(issues, name, entry + ".name"):
                    if name in names:
                        _error(issues, entry, f"Duplicate header name: {name}")
                    names.add(name)
                filename = header.get("file")
                if _check_string(issues, filename, entry + ".file"):
                    _check_file(issues, source_dir / "sbatch_headers" / filename, entry)


def _validate_calculations(data, source_dir, issues):
    """Check recipe settings and templates, returning referenced backends."""
    # Calculation menus, template mappings, and resolver ambiguity ----------
    calculations = data.get("calculations")
    # Runtime detection uses generated basenames. Remember who first declared
    # each file set so indistinguishable calculations can be reported.
    signatures = {}
    # Only backends referenced by a recipe need their k-path resources checked.
    codes_used = set()
    if _check_mapping(issues, calculations, "calculations"):
        for kind, definition in calculations.items():
            location = f"calculations.{kind}"
            if not _check_mapping(issues, definition, location):
                continue
            _check_string(issues, definition.get("name"), location + ".name")
            # Treat an unflavored recipe as one variant; None denotes that
            # there is no explicit flavor layer in the YAML.
            variants = definition.get("flavors", {None: definition})
            if "flavors" in definition and not _check_mapping(
                issues, variants, location + ".flavors"
            ):
                continue
            first_names = None
            for flavor, variant in variants.items():
                entry = location if flavor is None else f"{location}.flavors.{flavor}"
                if not _check_mapping(issues, variant, entry):
                    continue
                _check_string(issues, variant.get("name"), entry + ".name")
                names, codes = _validate_recipe_settings(
                    variant.get("config"), entry, issues
                )
                if codes is None:
                    _error(issues, entry, "Missing valid 'code' setting.")
                # Without a flavor, get_config() reads settings from the first
                # flavor. Later flavors must not introduce unreachable names.
                if first_names is None:
                    first_names = names
                elif not names <= first_names:
                    _error(
                        issues,
                        entry,
                        "Settings cannot be retrieved without a flavor: "
                        + ", ".join(sorted(names - first_names)),
                    )
                files = variant.get("files")
                if not _check_mapping(issues, files, entry + ".files"):
                    continue
                if codes is not None and codes != set(files):
                    _error(issues, entry, "Code options and template mappings differ.")
                # Each backend has its own template list. Files are copied into
                # a flat directory, so their basenames must not collide.
                for code, filenames in files.items():
                    codes_used.add(code)
                    files_path = f"{entry}.files.{code}"
                    if not _check_string_list(issues, filenames, files_path):
                        continue
                    for filename in filenames:
                        _check_file(
                            issues, source_dir / "templates" / filename, files_path
                        )
                    signature = frozenset(Path(filename).name for filename in filenames)
                    if len(signature) != len(filenames):
                        _error(issues, files_path, "Template basenames must be unique.")
                    # Complete template sets tie in the resolver only when equal.
                    previous = signatures.setdefault(
                        signature, (kind, code, files_path)
                    )
                    if previous[:2] != (kind, code):
                        _error(
                            issues,
                            files_path,
                            f"Ambiguous calculation files: same as {previous[2]}.",
                        )
    return codes_used


def _validate_recipe_settings(settings, entry, issues):
    """Check recipe questions, returning their names and selectable backends."""
    names = set()
    codes = None
    if not isinstance(settings, list) or not settings:
        _error(issues, entry + ".config", "Expected a nonempty list.")
    else:
        # These are the recipe's questions. Defaults must be selectable;
        # the code question determines which template backends are valid.
        for i, setting in enumerate(settings):
            setting_path = f"{entry}.config[{i}]"
            if not _check_mapping(issues, setting, setting_path):
                continue
            name = setting.get("name")
            if not _check_string(issues, name, setting_path + ".name"):
                continue
            if name in names:
                _error(issues, setting_path, f"Duplicate setting name: {name}")
            names.add(name)
            _check_string(issues, setting.get("prompt"), setting_path + ".prompt")
            options = setting.get("options")
            if not isinstance(options, list) or not options:
                _error(issues, setting_path + ".options", "Expected a nonempty list.")
                continue
            if not (
                all(isinstance(option, str) and option for option in options)
                or all(type(option) is bool for option in options)
            ):
                _error(
                    issues,
                    setting_path + ".options",
                    "Use strings or booleans consistently.",
                )
            if "default" in setting and setting["default"] not in options:
                _error(
                    issues,
                    setting_path + ".default",
                    "Default is not one of the options.",
                )
            if name == "code" and _check_string_list(
                issues, options, setting_path + ".options"
            ):
                codes = set(options)
    return names, codes


def _validate_kpaths(codes_used, source_dir, issues):
    """Check k-path resources for each referenced backend."""
    # High-symmetry k-path resources ----------------------------------------
    kpaths = source_dir / "kpaths"
    for code in sorted(codes_used):
        if code in ("quantum_espresso", "vasp", "wannier90"):
            # Structure-based lookup may request any space group from 1 to 230.
            for group in range(1, 231):
                _check_file(
                    issues,
                    kpaths / code / f"SG{group}",
                    f"kpaths.{code}.SG{group}",
                    nonempty=True,
                )


def _validate_libraries(data, source_dir, issues):
    """Check named libraries, per-code defaults, and grouped suggestions."""
    # Header inspection stays separate and only runs with config check --pseudos.
    settings = data.get("pseudopotentials")
    if not _check_mapping(issues, settings, "pseudopotentials"):
        return
    libraries = settings.get("libraries")
    if not _check_mapping(issues, libraries, "pseudopotentials.libraries"):
        return
    _validate_library_defaults(settings.get("defaults"), libraries, issues)
    # Validate libraries independently; sharing their root is allowed.
    for name, library in libraries.items():
        location = f"pseudopotentials.libraries.{name}"
        if not _check_mapping(issues, library, location):
            continue
        pseudo_format = library.get("format")
        if pseudo_format not in ("upf", "potcar"):
            _error(issues, location + ".format", "Expected upf or potcar.")
        codes = library.get("supported_codes")
        if _check_string_list(issues, codes, location + ".supported_codes"):
            for code in codes:
                # Match the backend families used by the command, including
                # combined codes such as quantum_espresso/wannier90.
                expected = None
                if "quantum_espresso" in code:
                    expected = "upf"
                elif "vasp" in code:
                    expected = "potcar"
                if expected is not None and pseudo_format != expected:
                    _error(issues, location + ".format", f"{code} requires {expected}.")
        _validate_library(library, pseudo_format, location, source_dir, issues)
    _validate_suggestions(data.get("suggested_pseudos", []), libraries, issues)


def _validate_library_defaults(defaults, libraries, issues):
    """Check scalar and SOC defaults for each configured calculation code."""
    if not _check_mapping(issues, defaults, "pseudopotentials.defaults"):
        return
    for code, roles in defaults.items():
        location = f"pseudopotentials.defaults.{code}"
        if not _check_mapping(issues, roles, location):
            continue
        # Both roles must resolve; they may deliberately share one library.
        for mode in ("scalar", "soc"):
            entry = f"{location}.{mode}"
            name = roles.get(mode)
            if not _check_string(issues, name, entry):
                continue
            if name not in libraries:
                _error(issues, entry, f"Unknown library: {name}")
                continue
            library = libraries[name]
            if isinstance(library, dict):
                supported = library.get("supported_codes")
                if isinstance(supported, list) and code not in supported:
                    _error(issues, entry, f"Library {name} does not support {code}.")


def _validate_suggestions(groups, libraries, issues):
    """Check suggestion globs assigned to nonoverlapping library groups."""
    if not isinstance(groups, list):
        _error(issues, "suggested_pseudos", "Expected a list of suggestion groups.")
        return
    assigned = set()
    for i, group in enumerate(groups):
        location = f"suggested_pseudos[{i}]"
        if not _check_mapping(issues, group, location):
            continue
        names = group.get("libraries")
        formats = set()
        if _check_string_list(issues, names, location + ".libraries"):
            for name in names:
                if name not in libraries:
                    _error(issues, location + ".libraries", f"Unknown library: {name}")
                elif isinstance(libraries[name], dict):
                    pseudo_format = libraries[name].get("format")
                    if isinstance(pseudo_format, str):
                        formats.add(pseudo_format)
                if name in assigned:
                    _error(issues, location + ".libraries", f"Repeated library: {name}")
                assigned.add(name)
        elements = group.get("elements")
        if not _check_mapping(issues, elements, location + ".elements"):
            continue
        for symbol, pattern in elements.items():
            entry = f"{location}.elements.{symbol}"
            if symbol not in atomic_numbers or symbol == "X":
                _error(issues, entry, "Expected an element symbol.")
            # Missing matches are allowed: selection falls back to the library pattern.
            pseudo_format = "upf" if "upf" in formats else "potcar"
            _check_pseudo_filename(
                issues, pattern, pseudo_format, entry, allow_glob=True
            )


def _validate_library(library, pseudo_format, location, source_dir, issues):
    """Check one library's root, selection rules, and cutoff defaults."""
    # An unusable root must not be reused when checking overrides.
    path = None
    root = library.get("path")
    if _check_string(issues, root, location + ".path"):
        try:
            path = Path(root).expanduser()
            if not path.is_absolute():
                path = source_dir / path
            if not path.is_dir():
                _error(issues, location + ".path", f"Missing directory: {path}")
        except (OSError, ValueError, RuntimeError) as exc:
            _error(issues, location + ".path", f"Cannot inspect directory: {exc}")
            path = None
    _validate_library_pattern(library.get("pattern"), pseudo_format, location, issues)
    _validate_library_overrides(library, pseudo_format, location, path, issues)
    _validate_library_cutoffs(library, pseudo_format, location, issues)


def _validate_library_pattern(pattern, pseudo_format, location, issues):
    """Check the element placeholder and paths allowed for this pseudo format."""
    if _check_string(issues, pattern, location + ".pattern"):
        try:
            # Only literal {element} is supported, without conversions
            # or format specifications such as {element!r}.
            fields = [
                (field, spec, conversion)
                for _, field, spec, conversion in Formatter().parse(pattern)
                if field is not None
            ]
            if not fields or any(field != ("element", "", None) for field in fields):
                raise ValueError("Use {element} as the filename placeholder.")
            # Si probes the resulting path syntax; no Si file is required.
            filename = pattern.format(element="Si")
            relative = Path(filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Pattern must stay within the library directory.")
            if pseudo_format == "upf" and relative.name != filename:
                raise ValueError("UPF patterns must match filenames, not paths.")
        except (ValueError, KeyError, IndexError) as exc:
            _error(issues, location + ".pattern", str(exc))


def _validate_library_overrides(library, pseudo_format, location, path, issues):
    """Check exact per-element filenames and the referenced files."""
    # Overrides promise an exact file, unlike optional suggestions.
    # Check that file as well as the path convention for this format.
    overrides = library.get("overrides", {})
    if overrides != {} and _check_mapping(issues, overrides, location + ".overrides"):
        for symbol, filename in overrides.items():
            entry = f"{location}.overrides.{symbol}"
            if symbol not in atomic_numbers or symbol == "X":
                _error(issues, entry, "Expected an element symbol.")
            if _check_pseudo_filename(issues, filename, pseudo_format, entry):
                if path is not None:
                    _check_file(issues, path / filename, entry)


def _validate_library_cutoffs(library, pseudo_format, location, issues):
    """Check optional UPF fallback energies; POTCAR recommendations use ENMAX."""
    if pseudo_format == "potcar":
        if "cutoff_defaults" in library:
            _error(issues, location + ".cutoff_defaults", "POTCAR cutoffs use ENMAX.")
        return
    # UPF defaults accept bare Ry numbers or explicit energy units.
    # Unit conversion checks dimensions, not scientific convergence.
    cutoffs = library.get("cutoff_defaults", {})
    if cutoffs != {} and _check_mapping(issues, cutoffs, location + ".cutoff_defaults"):
        from pint.errors import PintError
        from yaiv.defaults.config import ureg

        for cutoff_key, value in cutoffs.items():
            entry = f"{location}.cutoff_defaults.{cutoff_key}"
            if cutoff_key not in ("ecutwfc", "ecutrho"):
                _error(issues, entry, "Expected ecutwfc or ecutrho.")
                continue
            try:
                if type(value) in (int, float):
                    quantity = ureg.Quantity(value, "Ry")
                elif isinstance(value, str):
                    quantity = ureg.Quantity(value)
                else:
                    raise ValueError(
                        "Expected a number in Ry or a unit-bearing string."
                    )
                cutoff = quantity.to("Ry").magnitude
                if not math.isfinite(cutoff) or cutoff <= 0:
                    raise ValueError("Expected a finite positive energy.")
            except (PintError, ValueError, TypeError) as exc:
                _error(issues, entry, f"Invalid cutoff: {exc}")


def _check_pseudo_filename(
    issues, filename, pseudo_format, location, *, allow_glob=False
):
    """Check a relative file or suggestion glob; UPF stays in one directory."""
    if not _check_string(issues, filename, location):
        return False
    relative = Path(filename)
    invalid = relative.is_absolute() or ".." in relative.parts
    if pseudo_format == "upf":
        invalid |= relative.name != filename
    forbidden = "{}" if allow_glob else "*?[]{}"
    if invalid or any(c in filename for c in forbidden):
        kind = "glob" if allow_glob else "exact file"
        _error(
            issues,
            location,
            f"Expected a relative {kind} within the library directory.",
        )
        return False
    return True


def _error(issues, location, message):
    """
    Append a validation error to the current issue list.

    Parameters
    ----------
    issues : list of ConfigIssue
        Collected issues, extended in-place.
    location : str
        Dotted configuration path where the problem was found.
    message : str
        Human-readable explanation of the problem.
    """
    issues.append(ConfigIssue("error", location, message))


def _check_mapping(issues, value, location):
    """
    Check that a value is a nonempty mapping with string keys.

    Parameters
    ----------
    issues : list of ConfigIssue
        Collected issues, extended in-place.
    value : object
        Candidate mapping value.
    location : str
        Dotted configuration path for error reporting.

    Returns
    -------
    bool
        True when the value is valid.
    """
    if not isinstance(value, dict) or not value:
        _error(issues, location, "Expected a nonempty mapping.")
        return False
    if not all(isinstance(key, str) and key for key in value):
        _error(issues, location, "Keys must be nonempty strings.")
        return False
    return True


def _check_string(issues, value, location):
    """
    Check that a value is a nonempty string.

    Parameters
    ----------
    issues : list of ConfigIssue
        Collected issues, extended in-place.
    value : object
        Candidate string value.
    location : str
        Dotted configuration path for error reporting.

    Returns
    -------
    bool
        True when the value is valid.
    """
    if not isinstance(value, str) or not value.strip():
        _error(issues, location, "Expected a nonempty string.")
        return False
    return True


def _check_string_list(issues, value, location):
    """
    Check that a value is a nonempty list of nonempty strings.

    Parameters
    ----------
    issues : list of ConfigIssue
        Collected issues, extended in-place.
    value : object
        Candidate list value.
    location : str
        Dotted configuration path for error reporting.

    Returns
    -------
    bool
        True when every item is valid.
    """
    if not isinstance(value, list) or not value:
        _error(issues, location, "Expected a nonempty list of strings.")
        return False
    # Evaluate every entry first so a bad item does not hide later errors.
    return all(
        [
            _check_string(issues, item, f"{location}[{i}]")
            for i, item in enumerate(value)
        ]
    )


def _check_file(issues, path, location, *, nonempty=False):
    """
    Check that a referenced file exists and optionally has content.

    Parameters
    ----------
    issues : list of ConfigIssue
        Collected issues, extended in-place.
    path : pathlib.Path
        File path to inspect.
    location : str
        Dotted configuration path for error reporting.
    nonempty : bool, optional
        If True, empty files are reported as errors.
    """
    try:
        if not path.is_file():
            _error(issues, location, f"Missing file: {path}")
        elif nonempty and path.stat().st_size == 0:
            _error(issues, location, f"Empty file: {path}")
    except (OSError, ValueError) as exc:
        _error(issues, location, f"Cannot inspect {path}: {exc}")
