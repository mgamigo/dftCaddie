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
        help="Set up default pseudopotentials",
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
    from types import SimpleNamespace
    from dftcaddie.config import load_config
    from dftcaddie.commands.setup import apply_setup
    from dftcaddie.commands.pseudo import apply_pseudos
    from dftcaddie import utils as ut
    from dftcaddie import file_management as fm

    settings, _ = load_config()
    calculations, clusters = settings["calculations"], settings["clusters"]
    calculation = SimpleNamespace(**vars(args))
    details = calculation.details
    del calculation.details
    if calculation.auto:
        calculation.pseudo = True

    calculation.cluster = ut.resolve_cluster(clusters)
    log.debug("Resolved cluster: %s", calculation.cluster)

    # Select calculation type
    options = list(calculations.keys())
    if calculation.kind is None:
        option_strings = [calculations[key]["name"] for key in options]
        print(f"\nAvailable Calculation Types:\n{ut.format_options(option_strings)}")
        user_input = input("Choose a calculation type: ").strip().lower()
        calculation.kind = ut.resolve_user_input(user_input, options)
    ut.check_option_exists(calculation.kind, options)
    log.debug("Calculation kind: %s", calculation.kind)

    # Solve flavor if present
    if "flavors" in calculations[calculation.kind].keys():
        options = list(calculations[calculation.kind]["flavors"].keys())
        if calculation.flavor is None:
            if len(options) == 1:
                calculation.flavor = options[0]
                log.debug("Using only available flavor: %s", options[0])
            else:
                option_strings = [
                    calculations[calculation.kind]["flavors"][key]["name"]
                    for key in options
                ]
                print(
                    f"\nAvailable flavors:\n{ut.format_options(option_strings,brackets=True)}"
                )
                user_input = input("Choose flavor: ").strip().lower()
                calculation.flavor = ut.resolve_user_input(user_input, options)
        ut.check_option_exists(calculation.flavor, options)
        log.info("Calculation flavor: %s", calculation.flavor)

    # Additional configuration
    if calculation.flavor is None:
        config = calculations[calculation.kind]["config"]
        del calculation.flavor
    else:
        index = options.index(calculation.flavor)
        config = calculations[calculation.kind]["flavors"][calculation.flavor]["config"]
    for setting in config:
        options = setting["options"]
        value = getattr(calculation, setting["name"], None)
        log.debug("Resolving setting: %s", setting["name"])
        if value is None:
            if "default" in setting and not details:
                value = setting["default"]
                log.debug("Using default value: %s", value)
            elif len(options) == 1:
                value = options[0]
                log.debug("Single option available: %s", value)
            else:
                print(f"\n{setting['prompt']}")
                print(ut.format_options(options, brackets=True))
                user_input = input("Select: ").strip().lower()
                value = ut.resolve_user_input(user_input, options)
            setattr(calculation, setting["name"], value)
        ut.check_option_exists(value, options, setting["name"])
        log.debug("Setting %s : %s", setting["name"], value)

    # Proceed with the operation using the user's selected options
    print(f"\nSummary\n-------")
    keys = list(calculation.__dict__.keys())
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
        structure = ut.get_structure(args.structure)
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
                relativistic=calculation.soc,
                configure=True,
            )
