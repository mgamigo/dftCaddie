"""
dftCaddie | dftcaddie.commands.config
=====================================

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
    check_parser = commands.add_parser(
        "check", help="Validate active configuration and resources"
    )
    check_parser.add_argument(
        "--pseudos",
        action="store_true",
        help="Also inspect configured UPF and POTCAR files and metadata.",
    )
    check_parser.add_argument(
        "-w",
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
        return apply_check(workflows=args.workflows, pseudos=args.pseudos)
    raise ValueError(f"Unknown configuration action: {args.config_action}")


def apply_check(workflows: bool = False, pseudos: bool = False) -> int:
    """
    Validate the active YAML file and resources without changing them.

    Parameters
    ----------
    workflows : bool, optional
        Exercise calculation preparation with synthetic potentials.
    pseudos : bool, optional
        Inspect actual pseudopotential libraries after configuration validation.

    Returns
    -------
    int
        Zero if no errors were found, otherwise one. Warnings are nonfatal.
    """
    import yaml
    from dftcaddie.checks.config import validate_config
    from dftcaddie.config import _config_paths

    path, source = _config_paths()
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
    if pseudos:
        if errors:
            print("Pseudopotential inspection skipped: fix configuration errors first.")
        else:
            from dftcaddie.checks.pseudos import check_pseudos

            reports = check_pseudos(data, source)
            pseudo_errors = 0
            for report in reports:
                print(f"{report['format']}: {report['name']}: {report['path']}")
                print(
                    f"  {report['files']} file(s), "
                    f"{len(report['species'])} species"
                )
                for field, values in report["metadata"].items():
                    if values:
                        print(f"  {field}: {', '.join(map(str, values))}")
                for issue in report["issues"]:
                    print(f"  ERROR: {issue}")
                pseudo_errors += len(report["issues"])
            print(
                f"Pseudopotential inspection: {len(reports)} libraries, "
                f"{pseudo_errors} issue(s)."
            )
            errors += pseudo_errors
    if workflows:
        from dftcaddie.checks.workflows import check_workflows

        def print_workflow_result(result):
            label = "OK" if result.success else "ERROR"
            print(f"• {label}: {result.case}: {result.stage}: {result.message}")

        print("\nWorkflow checks use silicon and synthetic pseudos; no DFT jobs are run:")
        results = check_workflows(data, source, progress=print_workflow_result)
        errors += sum(not result.success for result in results)
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
    kpaths_src = resources / "kpaths"
    config_src = resources / "config.yaml"

    config_dst = user_root / "config.yaml"
    templates_dst = user_root / "templates"
    headers_dst = user_root / "sbatch_headers"
    kpaths_dst = user_root / "kpaths"

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
    copytree(kpaths_src, kpaths_dst)

    print(f"\nUser configuration initialized at {user_root}")
    return 0
