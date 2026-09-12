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
    parser.add_argument(
        "structure",
        metavar="FILE",
        help="Structure file (e.g. CIF, POSCAR, .pwi).",
    )
    parser.add_argument(
        "-e",
        "--exchange",
        metavar="XC",
        default="pbe",
        help="Exchange-correlation functional (e.g., pbe, pbesol, pz).",
    )
    parser.add_argument(
        "-k",
        "--kind",
        metavar="KIND",
        default="paw",
        help="Kind of pseudopotential (paw, us, ...).",
    )
    parser.add_argument(
        "-r",
        "--relativistic",
        action="store_true",
        help="Set relativistic pseudopotential",
    )
    parser.add_argument(
        "-c",
        "--configure",
        action="store_true",
        help="Configure cutoffs according to the pseudopotentials",
    )
    parser.add_argument(
        "--ratio",
        metavar="FLOAT",
        type=float,
        default=None,
        help="Cutoff safety factor (default: config.yaml).",
    )


def run(args=None):
    """
    Dispatch the ``caddie set pseudo`` workflow.

    This function resolves the current calculation kind and code from the
    working directory, reads the provided structure file, and applies
    pseudopotential configuration to the existing input templates. Depending
    on the selected options, it may also configure energy cutoffs based on
    pseudopotential recommendations.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``set pseudo`` subcommand.
    """

    from dftcaddie import utils as ut

    kind, flavor, code = ut.resolve_calculation_directory(Path.cwd())

    print(f"\nSummary\n-------")
    keys = list(args.__dict__.keys())
    for key, value in args.__dict__.items():
        print(f"{key.title()}: {value}")
    print(f"-------")

    structure = ut.get_structure(args.structure)

    apply_pseudos(
        kind_calc=kind,
        code=code,
        symbols=structure.symbols,
        exchange=args.exchange,
        kind_pseudo=args.kind,
        relativistic=args.relativistic,
        configure=args.configure,
        ratio=args.ratio,
    )


def apply_pseudos(
    kind_calc: str,
    code: str,
    symbols: list[str],
    relativistic: bool,
    exchange: str = "pbe",
    kind_pseudo: str = "paw",
    configure: bool = False,
    system_info_path: str = "SYSTEM.INFO",
    ratio: float | None = None,
    files: Iterable[str] | None = None,
) -> int:
    """
    Resolve and apply pseudopotentials for a structure and update input templates.

    For Quantum ESPRESSO calculations, this function selects one pseudopotential
    per element from the PSLibrary tree and updates ``SYSTEM.INFO`` accordingly.
    Optionally, it reads suggested cutoffs from the pseudopotential headers and
    writes CUTOFF/ECUTRHO into ``SYSTEM.INFO``.

    Parameters
    ----------
    kind_calc : str
        Calculation kind (e.g., ``"relax"``, ``"bands"``). Used to apply
        kind-dependent edits (e.g., SOC-related settings).
    code : str
        DFT code identifier. Currently only ``"quantum_espresso"`` is supported.
    symbols : list[str]
        Chemical symbols present in the structure (e.g., ``["Si", "O"]``).
    exchange : str
        Exchange/correlation label used to locate pseudopotentials (e.g., ``"pbe"``).
    kind_pseudo : str
        Pseudopotential kind/wildcard used to resolve files (e.g., ``"paw"``, ``"us"``).
    relativistic : bool
        If True, use the relativistic exchange folder variant (prefix ``"rel-"``).
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

    Returns
    -------
    int
        Exit code (0 on success).

    Raises
    ------
    NotImplementedError
        If ``code`` is not supported.
    """

    from dftcaddie import file_management as fm
    from dftcaddie.config import load_config
    import warnings

    editable = None if files is None else {Path(file).name for file in files}
    system_info_name = Path(system_info_path).name
    if configure and ratio is None:
        ratio = load_config()[0]["default_cutoff_ratio"]
    if "quantum_espresso" in code:
        pseudos = fm.get_qe_pseudo_paths(
            symbols=symbols,
            exchange=exchange,
            kind=kind_pseudo,
            relativistic=relativistic,
        )
        if editable is None or system_info_name in editable:
            fm.write_pseudos_to_system_info(system_info_path, pseudos)
        fm.set_spin_orbit_coupling(relativistic, code, files=editable)

        if configure and (editable is None or system_info_name in editable):
            fm.configure_qe_cutoffs_from_pseudos(
                system_info_path, pseudos, ratio=ratio
            )
    elif "vasp" in code:
        pseudos = fm.get_potcar_paths(
            symbols=symbols, exchange=exchange, kind=kind_pseudo
        )
        if editable is None or "POTCAR" in editable:
            fm.write_potcar(pseudos)
        fm.set_spin_orbit_coupling(relativistic, code, files=editable)

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
