"""
dftCaddie | dftcaddie.commands.sbatch
=====================================

CLI handler for the ``caddie sbatch`` command.

This module provides an interactive workflow to select a target cluster and an
SBATCH header preset, then apply it to the current working directory's
``master.sh`` script. Existing SBATCH preambles are removed and replaced, while
preserving the current ``#SBATCH --job-name`` value.

Functions
---------
add_arguments(parser)
    Register command-line arguments for the ``sbatch`` subcommand.
run(args=None)
    Dispatch the ``sbatch`` workflow (resolve cluster/header and apply it).
apply_header(cluster, header)
    Replace the SBATCH header in ``master.sh`` with the selected preset.
"""

import logging

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
    "apply_header",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``sbatch`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``sbatch`` arguments are added.
    """
    parser.add_argument(
        "-c",
        "--cluster",
        metavar="CLUSTER",
        required=False,
        help="Cluster name used to generate an SBATCH header.",
    )
    parser.add_argument(
        "-H",
        "--header",
        metavar="HEADER",
        required=False,
        help="Desired SBATCH header.",
    )


def run(args=None):
    """
    Dispatch the ``caddie sbatch`` workflow.

    This function selects a cluster (from CLI or inferred via hostname) and an
    SBATCH header preset (from CLI or an interactive numbered menu), then updates
    ``master.sh`` by removing

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``sbatch`` subcommand.
    """
    from dftcaddie import utils as ut
    from dftcaddie.config import load_config

    clusters = load_config()[0]["clusters"]

    if args.cluster is None:
        args.cluster = ut.resolve_cluster(clusters)
        log.info("Resolved cluster: %s", args.cluster)
    options = list(clusters.keys())
    ut.check_option_exists(args.cluster, options, "Clusters")

    headers = clusters[args.cluster]["headers"]
    options = [item["name"] for item in headers]
    if args.header is None:
        print(f"\nAvailable sbatch headers for Cluster={args.cluster}:")
        print(ut.format_options(options, numbers=True))
        user_input = input("Choose a sbatch header: ").strip().lower()
        args.header = ut.resolve_user_input(user_input, options)
    ut.check_option_exists(args.header, options, "Headings")
    log.info("Sbatch header is: %s", args.header)

    print(f"\nSummary\n-------")
    keys = list(args.__dict__.keys())
    for key, value in args.__dict__.items():
        print(f"{key.title()}: {value}")
    print(f"-------")

    apply_header(
        cluster=args.cluster,
        header=options.index(args.header),
    )


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
