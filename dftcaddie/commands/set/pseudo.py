"""
dftCaddie | dftcaddie.commands.set.pseudo
=========================================

CLI handler for the ``caddie set pseudo`` command.

This module implements the workflow used to select and apply
pseudopotentials for a calculation. It resolves the current calculation
kind and code, selects appropriate pseudopotentials for the given
structure, updates ``SYSTEM.INFO`` accordingly, and optionally configures
energy cutoffs based on pseudopotential recommendations.

Functions
---------
add_arguments()
    Register arguments for the ``caddie set pseudo`` subcommand.
run()
    Dispatch the ``pseudo`` workflow using parsed CLI arguments.
apply_pseudos()
    Resolve and apply pseudopotentials and related settings to input files.
"""

import logging
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
    "apply_pseudos",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``set pseudo`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``pseudo`` arguments are added.
    """
    from dftcaddie.completion import complete_pseudo_library

    parser.add_argument(
        "structure", metavar="FILE", nargs="?",
        help="Structure file; required when applying potentials.",
    )
    library = parser.add_argument(
        "-l", "--library", help="Named pseudopotential library for the calculation code."
    )
    library.completer = complete_pseudo_library
    parser.add_argument(
        "--list", action="store_true", help="List configured UPF and POTCAR libraries."
    )
    parser.add_argument(
        "--soc", action="store_true",
        help="Enable spin-orbit coupling; otherwise use collinear settings.",
    )
    parser.add_argument(
        "-c", "--configure", action="store_true",
        help="Configure cutoffs from recommendations or library defaults.",
    )
    parser.add_argument(
        "--ratio", type=float,
        help="Cutoff safety factor (default: config.yaml).",
    )


def run(args=None):
    """
    List configured libraries or apply pseudopotentials to a calculation.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments. Listing needs no structure or calculation directory.

    Returns
    -------
    int
        Zero on success, one on a listing or application error.
    """
    from dftcaddie import utils as ut
    from dftcaddie.config import load_config, resolve_upf_library, resolve_potcar_library

    try:
        if args.list:
            settings = load_config()[0]
            formats = (
                ("UPF", "upf_pseudopotentials", resolve_upf_library),
                ("POTCAR", "potcar_pseudopotentials", resolve_potcar_library),
            )
            found = False
            for label, key, resolve in formats:
                section = settings.get(key, {})
                libraries = section.get("libraries", {})
                names = [args.library] if args.library in libraries else libraries
                if args.library is not None and args.library not in libraries:
                    continue
                for name in names:
                    found = True
                    library = resolve(name)
                    roles = [
                        role for role, value in section["defaults"].items()
                        if value == name
                    ]
                    state = "available" if library["path"].is_dir() else "missing"
                    role_label = ", ".join(roles) or "no default role"
                    print(f"{label}: {name} [{role_label}] {state}: {library['path']}")
            if args.library is not None and not found:
                raise ValueError(f"Unknown pseudopotential library: {args.library}")
            return 0
        if args.structure is None:
            raise ValueError("Supply a structure FILE, or use --list.")
        kind, _, code = ut.resolve_calculation_directory(Path.cwd())
        structure = ut.get_structure(args.structure)
        return apply_pseudos(
            kind_calc=kind,
            code=code,
            symbols=structure.symbols,
            soc=args.soc,
            library=args.library,
            configure=args.configure,
            ratio=args.ratio,
        )
    except (KeyError, ValueError, OSError, RuntimeError) as exc:
        log.error("%s", exc)
        return 1


def apply_pseudos(
    kind_calc: str,
    code: str,
    symbols: list[str],
    soc: bool,
    configure: bool = False,
    system_info_path: str = "SYSTEM.INFO",
    ratio: float | None = None,
    files: Iterable[str] | None = None,
    library: str | None = None,
) -> int:
    """
    Resolve and apply pseudopotentials for a structure and update input templates.

    For Quantum ESPRESSO calculations, this function selects one pseudopotential
    per element from a named UPF library and updates ``SYSTEM.INFO`` accordingly.
    Optionally, it reads suggested cutoffs from the pseudopotential headers and
    writes CUTOFF/ECUTRHO into ``SYSTEM.INFO``.

    Parameters
    ----------
    kind_calc : str
        Calculation kind (e.g., ``"relax"``, ``"bands"``). Used to apply
        kind-dependent edits (e.g., SOC-related settings).
    code : str
        DFT code identifier: Quantum ESPRESSO or VASP.
    symbols : list[str]
        Chemical symbols present in the structure (e.g., ``["Si", "O"]``).
    soc : bool
        Enable SOC independently of the selected library. QE SOC requires
        has_so=True in every selected UPF header.
    configure : bool
        If True, read suggested cutoff values from pseudo headers and update
        cutoffs.
    system_info_path : str, optional
        Path to the ``SYSTEM.INFO`` file to edit, by default "SYSTEM.INFO".
    ratio : float, optional
        Safety factor applied to suggested cutoff values. ``None`` uses
        ``default_cutoff_ratio`` from the active configuration.
    files : iterable of str, optional
        Basenames or paths that may be changed. ``None`` permits all edits,
        as used by ``caddie set pseudo``.
    library : str, optional
        Explicit library name for the code. Otherwise use its scalar or soc default.

    Returns
    -------
    int
        Exit code (0 on success).

    Raises
    ------
    ValueError
        Selected UPF files do not support requested SOC.
    RuntimeError
        Requested cutoff recommendations/defaults are unavailable.
    """

    from dftcaddie import file_management as fm
    from dftcaddie.config import load_config, resolve_upf_library, resolve_potcar_library
    from dftcaddie import utils as ut
    import warnings

    editable = None if files is None else {Path(file).name for file in files}
    system_info_name = Path(system_info_path).name
    if configure and ratio is None:
        ratio = load_config()[0]["default_cutoff_ratio"]
    if "quantum_espresso" in code:
        settings = load_config()[0]
        name = library
        if name is None:
            mode = "soc" if soc else "scalar"
            name = settings["upf_pseudopotentials"]["defaults"][mode]
        selected_library = resolve_upf_library(name)
        pseudos = ut.get_upf_pseudo_paths(selected_library, symbols)
        if soc:
            for symbol, path in pseudos.items():
                if ut.read_upf_pseudo_metadata(path)["has_so"] is not True:
                    raise ValueError(f"SOC requires has_so=True for {symbol}: {path}")
        if editable is None or system_info_name in editable:
            if configure:
                fm.configure_qe_cutoffs_from_pseudos(
                    system_info_path,
                    pseudos,
                    ratio=ratio,
                    defaults=selected_library.get("cutoff_defaults"),
                )
            fm.write_pseudos_to_system_info(system_info_path, pseudos)
        fm.set_spin_orbit_coupling(soc, code, files=editable)
    elif "vasp" in code:
        name = library
        if name is None:
            mode = "soc" if soc else "scalar"
            name = load_config()[0]["potcar_pseudopotentials"]["defaults"][mode]
        selected_library = resolve_potcar_library(name)
        pseudos = ut.get_potcar_paths(selected_library, symbols)
        if editable is None or "POTCAR" in editable:
            fm.write_potcar(pseudos)
        fm.set_spin_orbit_coupling(soc, code, files=editable)

        editable_incars = (
            editable is None or any(name.startswith("INCAR") for name in editable)
        )
        if configure and (editable is None or "POTCAR" in editable) and editable_incars:
            fm.configure_vasp_cutoffs_from_potcar(
                "POTCAR", ratio=ratio, files=editable
            )
    else:
        warnings.warn(
            f"Pseudo client skipped (not implemented for code={code})", UserWarning
        )
    return 0
