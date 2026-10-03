"""
Select and validate workflow checks, then dispatch an isolated worker.

This is the public entry point used by the configuration CLI. Process setup
and temporary fixtures live in workflow_worker; preparation scenarios and
output assertions live in workflow_cases. No DFT programs are executed.

Classes
-------
WorkflowResult
    Outcome of one checked calculation workflow.

Functions
---------
calculation_cases()
    Yield every declared calculation kind/flavor/code combination.
check_workflows()
    Validate requested scenarios and run them in an isolated worker.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from dftcaddie.checks.config import validate_config


@dataclass(frozen=True)
class WorkflowResult:
    """Outcome of one calculation workflow."""

    case: str
    success: bool
    stage: str
    message: str
    scenario: str = "staged"


def calculation_cases(data):
    """
    Yield every declared calculation kind, flavor, and code combination.

    Parameters
    ----------
    data : dict
        Parsed configuration data containing the ``calculations`` section.

    Yields
    ------
    tuple
        ``(kind, flavor, code)`` for each configured template set. ``flavor`` is
        None for calculations without a flavor layer.
    """
    from dftcaddie.calculation import iter_calculation_definitions

    # Expand each recipe/flavor into one case per supported backend.
    for kind, flavor, definition in iter_calculation_definitions(data):
        for code in definition["files"]:
            yield kind, flavor, code


def check_workflows(
    data,
    source_dir,
    *,
    case=None,
    scenario="staged",
    checks=None,
    structure_path=None,
    timeout=60,
    progress=None,
) -> list[WorkflowResult]:
    """
    Exercise preparation against explicitly supplied configuration and resources.

    Parameters
    ----------
    data : dict
        Parsed configuration. Never modified. Actual pseudo paths are checked
        separately by validate_config; these runs use synthetic libraries.
    source_dir : path-like
        Template and SBATCH header root belonging to data.
    case : tuple, optional
        One (kind, flavor, code) to check; otherwise check every calculation.
    scenario : str, optional
        staged, automatic, auto, or reconfiguration.
    checks : iterable of tuple, optional
        Explicit ``(case, scenario)`` pairs to run in one worker, each in a
        fresh directory. Cannot be combined with case or a nondefault scenario.
    structure_path : path-like, optional
        Silicon CIF fixture. Defaults to the packaged copy of tests/data/Si.cif.
    timeout : float, optional
        Maximum seconds waiting for each result, including worker startup for
        the first case. A timeout stops the worker and fails remaining cases.
    progress : callable, optional
        Function called with each ``WorkflowResult`` as soon as it is available.

    Returns
    -------
    list of WorkflowResult
        Failures include the stage and error message; remaining cases continue.
        Unexpected interactive prompts fail explicitly. Backends without
        implemented system/pseudo checks still run generic staged checks and
        skip code-specific scenarios successfully.
    """
    # Normalize requests to (case, scenario) pairs: the case selects a recipe,
    # while the scenario selects the route used to prepare it.
    if checks is not None:
        if case is not None or scenario != "staged":
            raise ValueError("checks cannot be combined with case or scenario.")
        checks = [
            (tuple(selected_case), selected) for selected_case, selected in checks
        ]
    for selected in ([scenario] if checks is None else [s for _, s in checks]):
        if selected not in ("staged", "automatic", "auto", "reconfiguration"):
            raise ValueError(f"Unknown workflow scenario: {selected}")

    results = []

    def record(result):
        results.append(result)
        if progress is not None:
            progress(result)

    # Preflight configuration without requiring real external pseudo libraries.
    source = Path(source_dir).resolve()
    # Preserve caller settings while substituting libraries for isolated checks.
    clean = deepcopy(data)
    if isinstance(clean, dict):
        # External libraries are replaced by generated fixtures in the worker.
        # These declarations only satisfy preflight checks. The worker replaces
        # them with real temporary paths containing synthetic potential files.
        for section, pattern in (
            ("upf_pseudopotentials", "{element}.UPF"),
            ("potcar_pseudopotentials", "{element}/POTCAR"),
        ):
            clean[section] = {
                "defaults": {"scalar": "synthetic", "soc": "synthetic"},
                "libraries": {
                    "synthetic": {"path": str(source), "pattern": pattern}
                },
            }
    issues = validate_config(clean, source)
    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        for issue in errors:
            record(
                WorkflowResult("configuration", False, issue.location, issue.message)
            )
        return results
    cases = list(calculation_cases(clean))
    # With no explicit batch, run one scenario for the chosen case or all cases.
    if checks is None:
        checks = (
            [(tuple(case), scenario)]
            if case is not None
            else [(selected_case, scenario) for selected_case in cases]
        )
    # Reject unknown recipes before launching a worker or creating calculations.
    for selected_case, selected in checks:
        if selected_case not in cases:
            record(
                WorkflowResult(
                    str(selected_case),
                    False,
                    "configuration",
                    "Unknown calculation case.",
                    selected,
                )
            )
            return results
    if not checks:
        return results

    # Choose the structure fixture shared by every case.
    structure = (
        Path(structure_path).resolve()
        if structure_path
        else (Path(__file__).parent / "data/Si.cif")
    )
    # Send data and paths; the child loads its own isolated configuration.
    from dftcaddie.checks.workflow_worker import _run_worker

    return _run_worker(
        {
            "data": clean,
            "source": str(source),
            "checks": checks,
            "structure": str(structure),
        },
        timeout,
        progress,
    )
