"""
dftCaddie | dftcaddie.commands.config
===================================

CLI handler for the ``caddie config`` command.

This module initializes editable user resources under ``~/.config/dftcaddie``
and checks the active configuration without modifying it.

Functions
---------
add_arguments(parser)
    Register command-line arguments for the ``config`` subcommand.
run(args=None)
    Dispatch configuration initialization or validation.
apply_init(force=False)
    Create and populate the user configuration directory.
apply_check()
    Report configuration and resource validation issues.
"""

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

__all__ = [
    "add_arguments",
    "run",
    "apply_init",
    "apply_check",
]


def add_arguments(parser):
    """
    Add initialization and validation subcommands.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser instance to which the ``init`` arguments are added.
    """
    commands = parser.add_subparsers(dest="config_action", required=True)
    init_parser = commands.add_parser("init", help="Copy editable default resources")
    init_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing user configuration.",
    )
    check = commands.add_parser(
        "check", help="Validate active configuration and resources"
    )
    check.add_argument(
        "--workflows",
        action="store_true",
        help="Also prepare every calculation in temporary directories using synthetic pseudos.",
    )


def run(args=None):
    """
    Dispatch the ``caddie config`` workflow.

    Initialize editable resources or report validation issues for the active
    configuration.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments for the ``init`` subcommand.

    Returns
    -------
    int
        Exit code (0 on successful completion).
    """
    if args.config_action == "init":
        return apply_init(force=args.force)
    if args.config_action == "check":
        return apply_check(workflows=args.workflows)
    raise ValueError(f"Unknown configuration action: {args.config_action}")


def apply_check(workflows: bool = False) -> int:
    """
    Validate the active YAML file and resources without changing them.

    Returns
    -------
    int
        Zero if no errors were found, otherwise one. Warnings are nonfatal.
    """
    import yaml
    from dftcaddie.checks.config import validate_config
    from dftcaddie.config import config_paths

    path, source = config_paths()
    print(f"Configuration: {path}")
    try:
        with path.open() as stream:
            data = yaml.safe_load(stream)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        print(f"ERROR: Cannot read configuration: {exc}")
        return 1

    issues = validate_config(data, source)
    for issue in issues:
        print(f"{issue.level.upper()}: {issue.location}: {issue.message}")
    errors = sum(issue.level == "error" for issue in issues)
    warnings = sum(issue.level == "warning" for issue in issues)
    print(f"Configuration check: {errors} error(s), {warnings} warning(s).")
    if workflows:
        from dftcaddie.checks.workflows import check_workflows

        print("Workflow checks use silicon and synthetic pseudos; no DFT jobs are run.")
        for result in check_workflows(data, source):
            label = "OK" if result.success else "ERROR"
            print(f"{label}: {result.case}: {result.stage}: {result.message}")
            errors += not result.success
    return 1 if errors else 0


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
