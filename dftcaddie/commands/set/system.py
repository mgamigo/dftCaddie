"""
dftCaddie | dftcaddie.commands.set.system
=========================================

CLI handler for the ``caddie set system`` command.

This module defines the workflow used to adapt a prepared calculation to a
specific system. It can initialize template files (e.g. ``SYSTEM.INFO`` for
Quantum ESPRESSO), read a structure file, and apply structure-dependent edits
such as lattice vectors, fractional atomic positions, automatic k-point grids,
high-symmetry k-paths, and pseudopotential configuration.

Functions
---------
add_arguments()
    Register arguments for the ``caddie set system`` command.
run()
    Adapt the current calculation to a structure using parsed arguments.
apply_system()
    Apply structure, k-grid, and k-path edits to the working directory.
"""

import logging
from types import SimpleNamespace

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
    "apply_system",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``set system`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``system`` arguments are added.
    """
    parser.add_argument(
        "structure",
        metavar="FILE",
        help="Structure file (e.g. CIF, POSCAR, .pwi).",
    )
    parser.add_argument(
        "-ak",
        "--autokgrid",
        action="store_true",
        help="Set up an automatic k-point grid.",
    )
    parser.add_argument(
        "--kppra",
        metavar="INT",
        type=int,
        default=None,
        help="Target number of k-points per atom (default: config.yaml).",
    )
    parser.add_argument(
        "-kp",
        "--kpath",
        action="store_true",
        help="Set up a high-symmetry k-path in reciprocal space.",
    )
    parser.add_argument(
        "-p",
        "--pseudo",
        action="store_true",
        help="Set up default pseudopotentials",
    )


def run(args=None):
    """
    Dispatch the ``caddie set system`` workflow.

    This function resolves the current calculation kind and code from the
    working directory and applies system- and structure-dependent changes
    steps such as lattice and atomic positions, automatic k-point grids,
    high-symmetry k-paths, and pseudopotential configuration.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``set system`` subcommand.
    """
    from dftcaddie import utils as ut
    from dftcaddie.commands.set.pseudo import apply_pseudos

    kind, flavor, code = ut.resolve_calc_current_dir()

    print(f"\nSummary\n-------")
    keys = list(args.__dict__.keys())
    for key, value in args.__dict__.items():
        print(f"{key.title()}: {value}")
    print(f"-------")

    structure = ut.get_structure(args.structure)

    apply_system(
        kind=kind,
        code=code,
        structure=structure,
        autokgrid=args.autokgrid,
        kppra=args.kppra,
        kpath=args.kpath,
    )
    if args.pseudo:
        # Get default relativistic value for this calculation kind
        setting = ut.get_config(kind=kind, flavor=flavor, config_name="soc")
        relativistic = setting.get("default", False)
        apply_pseudos(
            kind_calc=kind,
            code=code,
            symbols=structure.symbols,
            relativistic=relativistic,
            configure=True,
        )


def apply_system(
    kind: str,
    code: str,
    structure: SimpleNamespace,
    autokgrid: bool = False,
    kppra: int | None = None,
    kpath: bool = False,
) -> int:
    """
    Adapt a calculation to a crystal structure.

    This function updates input templates using structural information
    (lattice vectors and atomic positions) and optionally configures an
    automatic k-point grid and a high-symmetry k-path.

    Parameters
    ----------
    kind : str
        Calculation kind (e.g., ``"relax"``, ``"bands"``). Included for
        interface consistency, but not used directly in this function.
    code : str
        DFT code identifier (e.g., ``"quantum_espresso"``).
    structure : SimpleNamespace
        Structure container providing lattice vectors, fractional atomic
        positions, chemical symbols, and space-group information.
    autokgrid : bool, optional
        If True, compute and write an automatic k-point grid based on the
        structure, by default False.
    kppra : int, optional
        Target number of k-points per reciprocal atom used for automatic
        k-grid generation. Default in ``~/.config/dftcaddie/config.yaml``.
    kpath : bool, optional
        If True, insert a high-symmetry k-path based on the structure space
        group, by default False.

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    from dftcaddie import file_management as fm

    if kppra is None:
        from dftcaddie.config import load_config

        kppra = load_config()[0]["default_kppra"]
    fm.set_crystal_structure(structure, code)
    if autokgrid:
        fm.set_auto_kgrid(structure, code, kppra)
    if kpath:
        fm.set_high_symmetry_path(structure, code)
    return 0
