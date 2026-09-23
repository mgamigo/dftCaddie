"""
dftCaddie | dftcaddie.commands.set.cluster
=========================================

CLI handler for the ``caddie set cluster`` command.

This module provides an interactive workflow to select a target cluster and an
SBATCH header preset, then apply it to the current working directory's
``master.sh`` script and configure MPI launch commands in the inferred
calculation scripts. Header replacement preserves the current job name.

Functions
---------
add_arguments(parser)
    Register arguments for the ``caddie set cluster`` subcommand.
run(args=None)
    Resolve and apply cluster settings, with optional header or MPI opt-outs.
apply_cluster(cluster, header, mpi)
    Configure the header and the inferred calculation's MPI commands.
apply_header(cluster, header)
    Replace the SBATCH header in ``master.sh`` with the selected preset.
"""

import logging
from pathlib import Path
from types import SimpleNamespace

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
    "apply_header",
    "apply_cluster",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``set cluster`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``cluster`` arguments are added.
    """
    from dftcaddie.completion import complete_header

    parser.add_argument(
        "-c",
        "--cluster",
        metavar="CLUSTER",
        required=False,
        help="Target cluster for the scheduler header and MPI commands.",
    ).completer = complete_header
    parser.add_argument(
        "-H",
        "--header",
        metavar="HEADER",
        required=False,
        help="Desired SBATCH header.",
    ).completer = complete_header
    parser.add_argument(
        "--no-header", action="store_true", help="Keep the existing scheduler header."
    )
    parser.add_argument(
        "--no-mpi", action="store_true", help="Keep existing MPI launch commands."
    )


def run(args=None):
    """
    Dispatch the ``caddie set cluster`` workflow.

    This function selects a cluster (from CLI or inferred via hostname) and an
    SBATCH header preset (from CLI or an interactive selection menu), then updates
    the header in ``master.sh`` and the calculation's MPI launch commands.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``set cluster`` subcommand.
    """
    from dftcaddie import utils as ut
    from dftcaddie.config import load_config
    from dftcaddie import prompts

    clusters = load_config()[0]["clusters"]

    if args.no_header and (args.no_mpi or args.header is not None):
        raise ValueError("--no-header cannot be combined with --no-mpi or --header.")

    if args.cluster is None:
        args.cluster = ut.resolve_cluster(clusters)
        log.info("Resolved cluster: %s", args.cluster)
    options = list(clusters.keys())
    ut.check_option_exists(args.cluster, options, "Clusters")

    if args.no_header:
        return apply_cluster(args.cluster, header=None, mpi=True)

    headers = clusters[args.cluster]["headers"]
    options = [item["name"] for item in headers]
    if args.header is None:
        args.header = prompts.select(
            f"Choose a scheduler header for {args.cluster}:",
            options,
            hint=f"Supply --header with one of: {', '.join(options)}.",
        )
    ut.check_option_exists(args.header, options, "Headings")
    log.info("Scheduler header is: %s", args.header)

    print(f"\nSummary\n-------")
    for key, value in args.__dict__.items():
        print(f"{key.title()}: {value}")
    print(f"-------")

    return apply_cluster(
        cluster=args.cluster,
        header=options.index(args.header),
        mpi=not args.no_mpi,
    )


def apply_cluster(cluster: str, header: int | None = 0, mpi: bool = True) -> int:
    """Apply cluster settings to the inferred calculation.

    Parameters
    ----------
    cluster : str
        Target cluster key.
    header : int or None
        Scheduler preset index, or ``None`` to preserve the header.
    mpi : bool
        Whether to update the calculation's MPI launch commands.
    """
    from dftcaddie import file_management as fm, utils

    scripts = []
    if mpi:
        kind, flavor, code = utils.resolve_calculation_directory(Path.cwd())
        files = fm.resolve_files(
            SimpleNamespace(kind=kind, flavor=flavor, code=code)
        )
        scripts = [
            Path(file).name
            for file in files
            if Path(file).suffix == ".sh" and Path(file).name != "master.sh"
        ]
    if header is not None:
        apply_header(cluster, header)
    if mpi:
        fm.change_mpi_command(scripts, cluster)
    return 0


def apply_header(cluster: str, header: int) -> int:
    """
    Replace the SBATCH header in ``master.sh`` with a preset for a given cluster.

    This function:
    1) Extracts the current job name from ``#SBATCH --job-name="..."`` in
       ``master.sh`` (if present),
    2) removes the existing SBATCH preamble,
    3) inserts the selected cluster/header preset,
    4) re-applies the original job name to the new header.

    Parameters
    ----------
    cluster : str
        Cluster key used to select the SBATCH header presets (from
        the active configuration).
    header : int
        Index of the selected header preset for the given cluster (0-based).

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """

    from dftcaddie import file_management as fm

    master_script_path = "master.sh"

    # Extract Job-name
    with open(master_script_path, "r") as file:
        lines = file.readlines()
    name = "NONAME"
    for line in lines:
        if "--job-name" in line:
            name = line.split('"')[1]
    # Remove current Header
    fm.remove_master_preamble(master_script_path)
    # Set new Header
    fm.set_master_preamble(master_script_path, cluster=cluster, header=header)
    # Reapply name
    fm._replace_setting(
        master_script_path,
        "#SBATCH --job-name",
        f'#SBATCH --job-name="{name}"',
        keep_comment=False,
    )
    return 0
