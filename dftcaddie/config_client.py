"""
dftCaddie | dftcaddie.config_client
===================================

CLI handler for the ``caddie config`` command.

This module initializes a user configuration directory under
``~/.config/dftcaddie`` by copying editable resources.

Functions
---------
add_arguments(parser)
    Register command-line arguments for the ``config`` subcommand.
run(args=None)
    Dispatch the ``config`` workflow.
apply_config(force=False)
    Create and populate the user configuration directory.
"""

import logging

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
    "apply_config",
]


def add_arguments(parser):
    """
    Add command-line arguments for the ``config`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``config`` arguments are added.
    """
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize user configuration directory.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing user configuration.",
    )


def run(args=None):
    """
    Dispatch the ``caddie config`` workflow.

    This function initializes a user configuration directory under
    ``~/.config/dftcaddie`` by copying editable resources.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``config`` subcommand.
    """
    if args.init:
        return apply_config(force=args.force)

    print("\nNothing to do. Use --init to initialize configuration.")
    return 0


def apply_config(force: bool = False) -> int:
    """
    Initialize ~/.config/dftcaddie with editable resources.

    This function copies editable resources bundled with the package
    (configuration file, calculation templates, and SBATCH headers)
    into the user's configuration directory. Existing files and
    directories are preserved unless ``force`` is True.

    Parameters
    ----------
    force : bool
        If True, overwrite existing files and directories in the user
        configuration directory. If False, existing entries are kept
        and skipped with a warning.

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    from pathlib import Path
    import shutil

    pkg_root = Path(__file__).parent
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
