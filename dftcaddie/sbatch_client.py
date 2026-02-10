"""
dftCaddie | dftcaddie.sbatch_client
===================================

CLI handler for the ``caddie sbatch`` command.

(Create similar definition to this)
This module defines the workflow used to adapt a prepared calculation to a
specific system. It can initialize template files (e.g. ``SYSTEM.INFO`` for
Quantum ESPRESSO), read a structure file, and apply structure-dependent edits
such as lattice vectors, fractional atomic positions, automatic k-point grids,
high-symmetry k-paths, and pseudopotential configuration.

Functions
---------
add_arguments
    Register command-line arguments for the ``setup`` subcommand.
run
    Dispatch the ``setup`` workflow using parsed CLI arguments.
"""

import logging
from types import SimpleNamespace

log = logging.getLogger(__name__)

_all__ = [
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
    Dispatch the ``caddie setup`` workflow.

    This function resolves the current calculation kind and code from the
    working directory and applies system- and structure-dependent setup
    steps such as lattice and atomic positions, automatic k-point grids,
    high-symmetry k-paths, and pseudopotential configuration.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``setup`` subcommand.
    """
    from dftcaddie import utils as ut
    from dftcaddie.config import clusters

    if args.cluster is None:
        args.cluster = ut.resolve_cluster(clusters)
        log.info("Resolved cluster: %s", args.cluster)
    options = list(clusters.keys())
    ut.check_option_exists(args.cluster, options, "Clusters")

    options = clusters[args.cluster]["headings"]
    option_strings = [item["name"] for item in options]
    if args.header is None:
        print(f"\nAvailable sbatch headers:")
        print(ut.format_options(option_strings, numbers=True))
        user_input = input("Choose a sbatch header: ").strip().lower()
        args.header = ut.resolve_user_input(user_input, option_strings)
    ut.check_option_exists(args.header, option_strings, "Headings")
    log.info("Sbatch header is: %s", args.header)

    print(f"\nSummary\n-------")
    keys = list(args.__dict__.keys())
    for key, value in args.__dict__.items():
        print(f"{key.title()}: {value}")
    print(f"-------")

    apply_header(
        cluster=args.cluster,
        header=args.header,
    )


def apply_header(cluster: str, header: str) -> int:
    """
    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    return 0
