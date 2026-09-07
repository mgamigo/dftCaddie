"""
dftCaddie | dftcaddie.commands.init
===================================

CLI handler for the ``caddie init`` command.

This module initializes a user configuration directory under
``~/.config/dftcaddie`` by copying editable resources.

Functions
---------
add_arguments(parser)
    Register command-line arguments for the ``config`` subcommand.
run(args=None)
    Dispatch the ``init`` workflow.
apply_init(force=False)
    Create and populate the user configuration directory.
"""

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
    "apply_init",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``init`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``init`` arguments are added.
    """
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing user configuration.",
    )


def run(args=None):
    """
    Dispatch the ``caddie init`` workflow.

    This function initializes a user configuration directory under
    ``~/.config/dftcaddie`` by copying editable resources.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``init`` subcommand.

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    return apply_init(force=args.force)


def apply_init(force: bool = False) -> int:
    """
    Create and populate the user configuration directory.

    Parameters
    ----------
    force : bool, optional
        If True, overwrite existing files and directories, by default False.

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    pkg_root = Path(__file__).resolve().parents[1]
    resources = pkg_root / "resources"

    user_root = Path.home() / ".config" / "dftcaddie"
    templates_src = resources / "templates"
    headers_src = resources / "sbatch_headers"
    config_src = resources / "config.yaml"

    config_dst = user_root / "config.yaml"
    templates_dst = user_root / "templates"
    headers_dst = user_root / "sbatch_headers"

    user_root.mkdir(parents=True, exist_ok=True)

    def copytree(src: Path, dst: Path):
        if dst.exists():
            if not force:
                log.warning("Directory %s already exists. Skipping.", dst)
                return
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    def copyfile(src: Path, dst: Path):
        if dst.exists() and not force:
            log.warning("File %s already exists. Skipping.", dst)
            return
        shutil.copy2(src, dst)

    copyfile(config_src, config_dst)
    copytree(templates_src, templates_dst)
    copytree(headers_src, headers_dst)

    print(f"\nUser configuration initialized at {user_root}")
    return 0
