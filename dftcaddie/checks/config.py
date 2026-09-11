"""Reusable validation of configuration data and referenced resources.

This module does not import the active configuration, so it can inspect invalid
user files and can also be called by tests with bundled or temporary resources.
"""

from dataclasses import dataclass
import math
import os
from pathlib import Path


@dataclass(frozen=True)
class ConfigIssue:
    """A validation error or warning at a named configuration location."""

    level: str
    location: str
    message: str


def validate_config(data, source_dir: Path, *, environ=None) -> list[ConfigIssue]:
    """
    Check configuration structure, resources, and calculation distinguishability.

    Parameters
    ----------
    data : object
        Parsed YAML content. Invalid types are reported as errors.
    source_dir : pathlib.Path
        Root for templates and SBATCH headers, matching the configuration loader.
    environ : mapping, optional
        Environment used to resolve PSLIBRARY. Defaults to os.environ.

    Returns
    -------
    list of ConfigIssue
        All detected errors and warnings. Missing optional pseudo libraries are
        warnings; invalid configured locations are errors.

    Notes
    -----
    No files are modified and no external programs are executed. K-paths are
    checked in the package directory because setup currently reads them there.
    Checks cover configuration consistency, not scientific input correctness.
    """
    issues = []
    source_dir = Path(source_dir)
    environ = os.environ if environ is None else environ

    def error(location, message):
        issues.append(ConfigIssue("error", location, message))

    def mapping(value, location):
        if not isinstance(value, dict) or not value:
            error(location, "Expected a nonempty mapping.")
            return False
        if not all(isinstance(key, str) and key for key in value):
            error(location, "Keys must be nonempty strings.")
            return False
        return True

    def string(value, location):
        if not isinstance(value, str) or not value.strip():
            error(location, "Expected a nonempty string.")
            return False
        return True

    def strings(value, location):
        if not isinstance(value, list) or not value:
            error(location, "Expected a nonempty list of strings.")
            return False
        return all([string(item, f"{location}[{i}]") for i, item in enumerate(value)])

    def file(path, location, *, nonempty=False):
        try:
            if not path.is_file():
                error(location, f"Missing file: {path}")
            elif nonempty and path.stat().st_size == 0:
                error(location, f"Empty file: {path}")
        except (OSError, ValueError) as exc:
            error(location, f"Cannot inspect {path}: {exc}")

    if not mapping(data, "config"):
        return issues

    for key in ("default_kppra", "nscf_kppra_ratio", "default_cutoff_ratio"):
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            error(key, "Expected a finite positive number.")

    strings(data.get("mpi_executables"), "mpi_executables")
    pseudos = data.get("suggested_qe_pseudos")
    if mapping(pseudos, "suggested_qe_pseudos"):
        for symbol, pattern in pseudos.items():
            string(pattern, f"suggested_qe_pseudos.{symbol}")

    clusters = data.get("clusters")
    if mapping(clusters, "clusters"):
        if "local" not in clusters:
            error("clusters", "Missing fallback cluster 'local'.")
        for name, cluster in clusters.items():
            location = f"clusters.{name}"
            if not mapping(cluster, location):
                continue
            hostname = cluster.get("hostname")
            if not isinstance(hostname, str) or (name != "local" and not hostname):
                error(
                    location + ".hostname",
                    "Expected a hostname (empty only for local).",
                )
            string(cluster.get("mpi_command"), location + ".mpi_command")
            headers = cluster.get("headers")
            if not isinstance(headers, list) or not headers:
                error(location + ".headers", "Expected a nonempty list.")
                continue
            names = set()
            for i, header in enumerate(headers):
                entry = f"{location}.headers[{i}]"
                if not mapping(header, entry):
                    continue
                name = header.get("name")
                if string(name, entry + ".name"):
                    if name in names:
                        error(entry, f"Duplicate header name: {name}")
                    names.add(name)
                filename = header.get("file")
                if string(filename, entry + ".file"):
                    file(source_dir / "sbatch_headers" / filename, entry)

    calculations = data.get("calculations")
    signatures = {}
    codes_used = set()
    if mapping(calculations, "calculations"):
        for kind, definition in calculations.items():
            location = f"calculations.{kind}"
            if not mapping(definition, location):
                continue
            string(definition.get("name"), location + ".name")
            variants = definition.get("flavors", {None: definition})
            if "flavors" in definition and not mapping(variants, location + ".flavors"):
                continue
            first_names = None
            for flavor, variant in variants.items():
                entry = location if flavor is None else f"{location}.flavors.{flavor}"
                if not mapping(variant, entry):
                    continue
                string(variant.get("name"), entry + ".name")
                settings = variant.get("config")
                names = set()
                codes = None
                if not isinstance(settings, list) or not settings:
                    error(entry + ".config", "Expected a nonempty list.")
                else:
                    for i, setting in enumerate(settings):
                        setting_path = f"{entry}.config[{i}]"
                        if not mapping(setting, setting_path):
                            continue
                        name = setting.get("name")
                        if not string(name, setting_path + ".name"):
                            continue
                        if name in names:
                            error(setting_path, f"Duplicate setting name: {name}")
                        names.add(name)
                        string(setting.get("prompt"), setting_path + ".prompt")
                        options = setting.get("options")
                        if not isinstance(options, list) or not options:
                            error(
                                setting_path + ".options", "Expected a nonempty list."
                            )
                            continue
                        if not (
                            all(
                                isinstance(option, str) and option for option in options
                            )
                            or all(type(option) is bool for option in options)
                        ):
                            error(
                                setting_path + ".options",
                                "Use strings or booleans consistently.",
                            )
                        if "default" in setting and setting["default"] not in options:
                            error(
                                setting_path + ".default",
                                "Default is not one of the options.",
                            )
                        if name == "code" and strings(
                            options, setting_path + ".options"
                        ):
                            codes = set(options)
                if codes is None:
                    error(entry, "Missing valid 'code' setting.")
                if first_names is None:
                    first_names = names
                elif not names <= first_names:
                    error(
                        entry,
                        "Settings cannot be retrieved without a flavor: "
                        + ", ".join(sorted(names - first_names)),
                    )
                files = variant.get("files")
                if not mapping(files, entry + ".files"):
                    continue
                if codes is not None and codes != set(files):
                    error(entry, "Code options and template mappings differ.")
                for code, filenames in files.items():
                    codes_used.add(code)
                    files_path = f"{entry}.files.{code}"
                    if not strings(filenames, files_path):
                        continue
                    for filename in filenames:
                        file(source_dir / "templates" / filename, files_path)
                    signature = frozenset(Path(filename).name for filename in filenames)
                    if len(signature) != len(filenames):
                        error(files_path, "Template basenames must be unique.")
                    # Complete template sets tie in the resolver only when equal.
                    previous = signatures.setdefault(
                        signature, (kind, code, files_path)
                    )
                    if previous[:2] != (kind, code):
                        error(
                            files_path,
                            f"Ambiguous calculation files: same as {previous[2]}.",
                        )

    kpaths = Path(__file__).resolve().parents[1] / "resources" / "kpaths"
    for code in sorted(codes_used):
        if code in ("quantum_espresso", "vasp", "wannier90"):
            for group in range(1, 231):
                file(
                    kpaths / code / f"SG{group}",
                    f"kpaths.{code}.SG{group}",
                    nonempty=True,
                )

    for key, environment_key in (
        ("qe_pslibrary", "PSLIBRARY"),
        ("vasp_pseudopotentials", None),
    ):
        root = environ.get(environment_key) if environment_key else None
        location = f"${environment_key}" if root else key
        root = root or data.get(key)
        if not root:
            issues.append(
                ConfigIssue(
                    "warning", key, "Optional pseudopotential library not configured."
                )
            )
        elif string(root, location):
            try:
                path = Path(root).expanduser()
                if not path.is_dir():
                    error(location, f"Pseudopotential directory does not exist: {path}")
            except (OSError, ValueError, RuntimeError) as exc:
                error(location, f"Cannot inspect pseudopotential directory: {exc}")
    return issues
