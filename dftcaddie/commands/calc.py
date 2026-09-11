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
        help="Run the full automatic setup from scratch (structure must be provided).",
    )
    parser.add_argument(
        "--kind",
        metavar="KIND",
        required=False,
        help="Calculation kind (e.g., bands, relax, phonons)",
    )
    parser.add_argument(
        "--flavor",
        metavar="KIND",
        required=False,
        help="Calculation flavor (e.g., default, single_point)",
    )
    parser.add_argument(
        "--code",
        metavar="CODE",
        required=False,
        help="DFT code to use (e.g., vasp, quantum espresso)",
    )


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
    from dftcaddie.commands.setup import apply_setup
    from dftcaddie.commands.pseudo import apply_pseudos
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
    fm.copy_input_files(files, calculation.overwrite)

    log.info("Editing master.sh ...")
    scripts = fm.populate_master_script("master.sh", files)
    fm.set_master_preamble("master.sh", calculation.cluster)

    fm.change_mpi_command(scripts, calculation.cluster)
    fm.configure_input_files(calculation)
    if calculation.structure is not None:
        structure = ut.get_structure(spec.structure)
        apply_setup(
            kind=calculation.kind,
            code=calculation.code,
            structure=structure,
            autokgrid=calculation.auto,
            kpath=calculation.auto,
        )
        if calculation.pseudo:
            apply_pseudos(
                kind_calc=calculation.kind,
                code=calculation.code,
                symbols=structure.symbols,
                relativistic=spec.soc,
                configure=True,
            )
