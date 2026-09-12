"""
dftCaddie | dftcaddie.commands.calc
===================================

CLI handler for the ``caddie calc`` command.

This module registers calculation-preparation options and implements the
interactive flow that resolves missing parameters, then writes DFT input
files to a folder via ``dftcaddie.file_management``.

Functions
---------
add_arguments()
    Register command-line arguments for the ``calc`` subcommand.
run()
    Resolve calculation options and prepare DFT input files.

Private Utilities
-----------------
run.prompt()
    Collect a missing choice through the shared Questionary interface.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``calc`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``calc`` arguments are added.
    """
    from dftcaddie.completion import complete_calculation

    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite existing files if necessary",
    )
    parser.add_argument(
        "-d",
        "--details",
        action="store_true",
        help="Ask for details instead of going for defaults",
    )
    parser.add_argument(
        "-s",
        "--structure",
        metavar="FILE",
        required=False,
        help="Structure file (e.g. CIF, POSCAR, .pwi).",
    )
    parser.add_argument(
        "-p",
        "--pseudo",
        action="store_true",
        help="Set up default pseudopotentials (requires --structure FILE)",
    )
    parser.add_argument(
        "-a",
        "--auto",
        action="store_true",
        help="Run full automatic preparation (requires --structure FILE).",
    )
    parser.add_argument(
        "--kind",
        metavar="KIND",
        required=False,
        help="Calculation kind (e.g., bands, relax, phonons)",
    ).completer = complete_calculation
    parser.add_argument(
        "--flavor",
        metavar="KIND",
        required=False,
        help="Calculation flavor (e.g., default, single_point)",
    ).completer = complete_calculation
    parser.add_argument(
        "--code",
        metavar="CODE",
        required=False,
        help="DFT code to use (e.g., vasp, quantum espresso)",
    ).completer = complete_calculation


def run(args=None):
    """
    Resolve calculation options and prepare DFT input files.

    This function implements the ``caddie calc`` workflow. It resolves
    missing options interactively when needed, validates user selections,
    copies template input files, and applies code- and cluster-specific
    configuration edits.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``calc`` subcommand.
    """
    from dftcaddie.calculation import resolve_calculation
    from dftcaddie.config import load_config
    from dftcaddie.commands.set.system import apply_system
    from dftcaddie.commands.set.pseudo import apply_pseudos
    from dftcaddie import utils as ut
    from dftcaddie import file_management as fm
    from dftcaddie import prompts

    settings, _ = load_config()

    def prompt(label, options, labels):
        """
        Collect a missing calculation choice with a noninteractive error hint.

        Parameters
        ----------
        label : str
            Question describing the missing setting.
        options : list of str or list of bool
            Available configuration values.
        labels : list of str or None
            Optional display names corresponding to options.

        Returns
        -------
        str or bool
            The selected configuration value.

        Raises
        ------
        InputRequired
            The choice is required without an interactive terminal.
        KeyboardInterrupt
            The user cancels or input ends.
        """
        return prompts.select(
            label,
            options,
            labels,
            hint="Supply --kind, --flavor and --code as needed; omit --details to use configured defaults.",
        )

    try:
        spec = resolve_calculation(
            vars(args),
            settings,
            cluster=ut.resolve_cluster(settings["clusters"]),
            prompt=prompt,
            details=args.details,
        )
    except ValueError as exc:
        log.error("%s", exc)
        raise SystemExit(1) from exc
    calculation = spec.as_namespace()

    # Proceed with the operation using the user's selected options
    print(f"\nSummary\n-------")
    for key, value in calculation.__dict__.items():
        print(f"{key.title()}: {value}")
    print(f"-------")
    files = fm.resolve_files(calculation)
    copied_files = fm.copy_input_files(files, calculation.overwrite)
    copied_names = {Path(file).name for file in copied_files}

    if "master.sh" in copied_names:
        log.info("Editing master.sh ...")
        fm.populate_master_script("master.sh", files)
        fm.set_master_preamble("master.sh", calculation.cluster)

    copied_scripts = [
        Path(file).name
        for file in copied_files
        if file.endswith(".sh") and Path(file).name != "master.sh"
    ]
    fm.change_mpi_command(copied_scripts, calculation.cluster)
    fm.configure_input_files(calculation, files=copied_names)
    if calculation.structure is not None:
        structure = ut.get_structure(spec.structure)
        editable_files = set(copied_names)
        if calculation.code == "vasp" and not Path("POSCAR").exists():
            editable_files.add("POSCAR")
        if calculation.auto and calculation.code == "vasp" and not Path(
            "KPOINTS.BS"
        ).exists():
            editable_files.add("KPOINTS.BS")
        apply_system(
            kind=calculation.kind,
            code=calculation.code,
            structure=structure,
            autokgrid=calculation.auto,
            kpath=calculation.auto,
            files=editable_files,
        )
        if calculation.pseudo:
            if calculation.code == "vasp" and not Path("POTCAR").exists():
                editable_files.add("POTCAR")
            apply_pseudos(
                kind_calc=calculation.kind,
                code=calculation.code,
                symbols=structure.symbols,
                relativistic=spec.soc,
                configure=True,
                files=editable_files,
            )
