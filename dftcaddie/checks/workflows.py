"""
dftCaddie | dftcaddie.checks.workflows
=======================================

Shared workflow checks for pytest and the configuration CLI.

Only Python preparation commands run. A shared worker process uses synthetic
potentials and a real Si CIF, with a fresh working directory for each case.

Classes
-------
WorkflowResult
    Outcome of one checked calculation workflow.

Functions
---------
calculation_cases()
    Yield every declared calculation kind/flavor/code combination.
check_workflows()
    Run one or more calculation workflows in isolated temporary directories.

Private Utilities
-----------------
_require()
    Raise a ValueError when a workflow assertion fails.
_snapshot()
    Capture current-directory file contents for later comparison.
_worker()
    Prepare shared fixtures and stream results from an isolated worker.
_prepare_fixtures()
    Install the temporary configuration, structure, and synthetic libraries.
_run_case()
    Execute one calculation in its own temporary working directory.
"""

from copy import deepcopy
from contextlib import redirect_stdout
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
from queue import Empty, Queue
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread

import yaml

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
    for kind, definition in data["calculations"].items():
        for flavor, variant in definition.get("flavors", {None: definition}).items():
            for code in variant["files"]:
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
        Unsupported backends and unexpected interactive prompts fail explicitly.
        Results follow request order and identify their scenario independently
        of the success or failure stage.
    """
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
    clean = deepcopy(data)
    if isinstance(clean, dict):
        for key in ("qe_pslibrary", "vasp_pseudopotentials"):
            clean.pop(key, None)
    issues = validate_config(clean, source, environ={})
    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        for issue in errors:
            record(
                WorkflowResult("configuration", False, issue.location, issue.message)
            )
        return results
    cases = list(calculation_cases(clean))
    if checks is None:
        checks = (
            [(tuple(case), scenario)]
            if case is not None
            else [(selected_case, scenario) for selected_case in cases]
        )
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
    # One process and resource installation for the entire batch.
    with TemporaryDirectory(prefix="dftcaddie-check-") as root:
        root = Path(root)
        request = root / "request.yaml"
        request.write_text(
            yaml.safe_dump(
                {
                    "data": clean,
                    "source": str(source),
                    "cases": [selected_case for selected_case, _ in checks],
                    "checks": checks,
                    "structure": str(structure),
                }
            )
        )
        env = dict(os.environ)
        env.pop("PSLIBRARY", None)
        env["HOME"] = str(root / "home")
        # Also support source checkouts not installed into this interpreter.
        env["PYTHONPATH"] = os.pathsep.join(
            [str(Path(__file__).resolve().parents[2]), env.get("PYTHONPATH", "")]
        )
        jobs = [
            (f"{kind}/{flavor or 'default'}/{code}", selected)
            for (kind, flavor, code), selected in checks
        ]
        messages = Queue()

        def read_results(stream):
            for line in stream:
                messages.put(line)
            messages.put(None)

        try:
            with (
                (root / "worker.log").open("w+") as log,
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "dftcaddie.checks.workflows",
                        str(request),
                    ],
                    cwd=root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=log,
                    text=True,
                ) as process,
            ):
                reader = Thread(
                    target=read_results, args=(process.stdout,), daemon=True
                )
                reader.start()
                failure = None
                try:
                    for label, selected in jobs:
                        if failure is None:
                            try:
                                line = messages.get(timeout=timeout)
                                if line is None:
                                    log.seek(0)
                                    failure = (
                                        log.read()[-2000:]
                                        or "Worker exited without a result."
                                    )
                                else:
                                    result = WorkflowResult(**json.loads(line))
                            except Empty:
                                failure = f"Timed out after {timeout}s; worker stopped."
                            except (ValueError, TypeError) as exc:
                                failure = f"Invalid worker result: {exc}"
                            if failure is None:
                                record(result)
                                continue
                        record(
                            WorkflowResult(label, False, "worker", failure, selected)
                        )
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    reader.join()
        except OSError as exc:
            for label, selected in jobs[len(results) :]:
                record(WorkflowResult(label, False, "worker", str(exc), selected))
    return results


def _require(condition, message):
    """
    Raise an error when a workflow condition is not satisfied.

    Parameters
    ----------
    condition : bool
        Condition expected to be true.
    message : str
        Error message used when the condition is false.

    Raises
    ------
    ValueError
        If condition is false.
    """
    if not condition:
        raise ValueError(message)


def _snapshot():
    """
    Capture the file contents in the current working directory.

    Returns
    -------
    dict
        Mapping from filename to raw file bytes for regular files in cwd.
    """
    return {p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()}


def _prepare_fixtures(payload, root):
    """
    Create the shared structure, synthetic libraries, and user configuration.

    Parameters
    ----------
    payload : dict
        Batch request containing configuration, resources, and structure paths.
    root : pathlib.Path
        Temporary worker directory.

    Returns
    -------
    tuple
        Structure path, QE pseudo filenames, and synthetic POTCAR contents.
    """
    data = payload["data"]
    structure = root / "Si.cif"
    structure.write_bytes(Path(payload["structure"]).read_bytes())
    qe = root / "qe"
    names = {}
    if any(case[2] == "quantum_espresso" for case in payload["cases"]):
        pattern = data["suggested_qe_pseudos"]["Si"]
        for exchange in ("pbe", "rel-pbe"):
            name = pattern.replace("$fct", exchange).replace("*", "kjpaw") + ".UPF"
            _require(Path(name).name == name, "Si pseudo pattern must be a filename.")
            directory = qe / exchange / "PSEUDOPOTENTIALS"
            directory.mkdir(parents=True)
            (directory / name).write_text(
                "Suggested minimum cutoff for wavefunctions: 40 Ry\n"
                "Suggested minimum cutoff for charge density: 160 Ry\n"
            )
            names[exchange] = name
    vasp = root / "vasp/PAW_PBE/Si"
    vasp.mkdir(parents=True)
    potcar = "Synthetic Si potential for testing only\n ENMAX = 200.0; ENMIN = 150.0\n"
    (vasp / "POTCAR").write_text(potcar)
    data["qe_pslibrary"] = str(qe)
    data["vasp_pseudopotentials"] = str(root / "vasp")

    # Install editable resources once for the active worker configuration.
    user_config = Path.home() / ".config" / "dftcaddie"
    user_config.mkdir(parents=True)
    for directory in ("templates", "sbatch_headers", "kpaths"):
        shutil.copytree(Path(payload["source"]) / directory, user_config / directory)
    (user_config / "config.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    return structure, names, potcar


def _run_case(payload, root, fixtures):
    """
    Run one workflow using shared fixtures and a fresh calculation directory.

    Parameters
    ----------
    payload : dict
        Selected case, scenario, label, and configuration.
    root : pathlib.Path
        Directory reserved for this case.
    fixtures : tuple
        Shared structure path, pseudo filenames, and POTCAR contents.

    Returns
    -------
    WorkflowResult
        Outcome with the failing command or assertion stage when applicable.
    """
    from dftcaddie import cli, utils

    stage = "fixtures"
    try:
        data = payload["data"]
        kind, flavor, code = payload["case"]
        structure, names, potcar = fixtures
        _require(
            code in ("quantum_espresso", "vasp"),
            f"No workflow checks implemented for {code}.",
        )
        working = root / "calculation"
        working.mkdir(parents=True)
        os.chdir(working)

        def run(*args):
            """
            Run one caddie subcommand and fail on nonzero status.
            """
            nonlocal stage
            stage = " ".join(args[:1])
            _require(cli.main(list(args)) == 0, f"Command failed: {args[0]}")

        flags = ["--kind", kind, "--code", code]
        if flavor is not None:
            flags += ["--flavor", flavor]
        definition = data["calculations"][kind]
        if flavor is not None:
            definition = definition["flavors"][flavor]

        scenario = payload["scenario"]
        if scenario in ("automatic", "auto"):
            # Automatic one-shot preparation must match the staged commands.
            option = "--auto" if scenario == "auto" else "--pseudo"
            run("calc", *flags, "--structure", str(structure), option)
            automatic = _snapshot()
            (root / "staged").mkdir()
            os.chdir(root / "staged")
            run("calc", *flags)
            extra = ["--autokgrid", "--kpath"] if scenario == "auto" else []
            run("setup", str(structure), "--pseudo", *extra)
            stage = "compare"
            _require(
                _snapshot() == automatic,
                "Automatic and staged preparation produced different files.",
            )
        else:
            # caddie calc: templates, script wiring, and calculation detection.
            run("calc", *flags)
            for filename in definition["files"][code]:
                _require(
                    Path(Path(filename).name).is_file(),
                    f"Missing generated template: {filename}",
                )
            resolved_kind, _, resolved_code = utils.resolve_calc_current_dir()
            _require(
                (resolved_kind, resolved_code) == (kind, code),
                "Generated files resolve to a different calculation.",
            )
            master = Path("master.sh").read_text()
            _require("bash master.sh" not in master, "Master script invokes itself.")
            for filename in definition["files"][code]:
                name = Path(filename).name
                if name.endswith(".sh") and name != "master.sh":
                    _require(
                        master.count(f"bash {name}\n") == 1,
                        f"Missing or duplicate script: {name}",
                    )

            # caddie setup: structure, k-grid, and high-symmetry k-path edits.
            run("setup", str(structure), "--autokgrid", "--kppra", "64", "--kpath")
            stage = "setup output"
            if code == "quantum_espresso":
                text = Path("SYSTEM.INFO").read_text()
                for expected in (
                    "NAME='Si8'",
                    "ATM_NUM=8\n",
                    "ATM_TYPES=1\n",
                    "KGRID='2 2 2'",
                ):
                    _require(
                        expected in text, f"Missing structure/grid setting: {expected}"
                    )
                path = Path.home() / ".config/dftcaddie/kpaths/quantum_espresso/SG227"
                _require(path.read_text().strip() in text, "Incorrect QE k-path.")
            else:
                import numpy as np
                from ase.io import read

                actual, expected = read("POSCAR"), read(structure)
                _require(
                    actual.get_chemical_symbols() == expected.get_chemical_symbols(),
                    "POSCAR species differ.",
                )
                _require(
                    np.allclose(actual.cell, expected.cell), "POSCAR lattice differs."
                )
                _require(
                    np.allclose(
                        actual.get_scaled_positions(), expected.get_scaled_positions()
                    ),
                    "POSCAR positions differ.",
                )
                _require(
                    "2 2 2" in Path("KPOINTS.SCC").read_text(), "Incorrect VASP grid."
                )
                path = Path.home() / ".config/dftcaddie/kpaths/vasp/SG227"
                _require(
                    Path("KPOINTS.BS").read_bytes() == path.read_bytes(),
                    "Incorrect VASP k-path.",
                )

            # caddie pseudo: pseudo selection, cutoffs, and SOC settings.
            run("pseudo", str(structure), "--configure", "--relativistic")
            stage = "pseudo output"
            ratio = data["default_cutoff_ratio"]
            if code == "quantum_espresso":
                text = Path("SYSTEM.INFO").read_text()
                _require(text.count(names["rel-pbe"]) == 1, "Incorrect QE species.")
                _require(
                    f"CUTOFF={int(40 * ratio)}\n" in text
                    and f"ECUTRHO={int(160 * ratio)}\n" in text,
                    "Incorrect QE cutoffs.",
                )
            else:
                _require(Path("POTCAR").read_text() == potcar, "Incorrect POTCAR.")
                incars = list(Path.cwd().glob("INCAR*"))
                _require(incars, "No INCAR generated.")
                for incar in incars:
                    text = incar.read_text()
                    _require(
                        f"ENCUT = {int(200 * ratio)}" in text
                        and "LSORBIT = TRUE" in text,
                        f"Incorrect cutoff/SOC in {incar.name}.",
                    )

            # caddie sbatch: every configured header preserves the job body.
            body = master[master.index("#Actual JOBS") :]
            for cluster, entry in data["clusters"].items():
                for header in entry["headers"]:
                    run("sbatch", "--cluster", cluster, "--header", header["name"])
                    result = Path("master.sh").read_text()
                    _require(
                        result.endswith(body),
                        "Header replacement changed the job body.",
                    )
                    _require(
                        result.count("# === DFTCADDIE SBATCH HEADER END ===") == 1,
                        "Duplicate SBATCH header boundary.",
                    )

            if scenario == "reconfiguration":
                # Repeated configuration should update owned settings only.
                grid = Path(
                    "SYSTEM.INFO" if code == "quantum_espresso" else "KPOINTS.SCC"
                )
                old_grid = grid.read_bytes()
                Path("notes.txt").write_text("Keep my calculation notes.\n")

                def reconfigure():
                    """
                    Apply the second-pass setup, pseudo, and sbatch commands.
                    """
                    run("setup", str(structure), "--autokgrid", "--kppra", "4096")
                    run("pseudo", str(structure), "--configure")
                    run(
                        "sbatch",
                        "--cluster",
                        "local",
                        "--header",
                        data["clusters"]["local"]["headers"][0]["name"],
                    )

                reconfigure()
                stage = "reconfiguration output"
                _require(grid.read_bytes() != old_grid, "Grid did not change.")
                _require(
                    Path("notes.txt").read_text() == "Keep my calculation notes.\n",
                    "Unrelated notes changed.",
                )
                if code == "quantum_espresso":
                    text = Path("SYSTEM.INFO").read_text()
                    _require(
                        names["pbe"] in text and names["rel-pbe"] not in text,
                        "Pseudo selection was not replaced.",
                    )
                    _require(
                        "noncolin=.false." in Path("scf.sh").read_text(),
                        "SOC was not disabled.",
                    )
                else:
                    _require(
                        Path("POTCAR").read_text() == potcar,
                        "POTCAR changed unexpectedly.",
                    )
                    _require(
                        "LSORBIT = FALSE" in Path("INCAR.SCC").read_text(),
                        "SOC was not disabled.",
                    )
                before = _snapshot()
                reconfigure()
                stage = "repeat"
                _require(
                    _snapshot() == before, "Repeating configuration changed files."
                )
        result = WorkflowResult(
            payload["label"],
            True,
            scenario,
            "Preparation completed.",
            payload["scenario"],
        )
    except (Exception, SystemExit) as exc:
        result = WorkflowResult(
            payload["label"],
            False,
            stage,
            f"{type(exc).__name__}: {exc}",
            payload["scenario"],
        )
    return result


def _worker(request):
    """
    Prepare one isolated worker and stream a JSON result for each case.

    Parameters
    ----------
    request : path-like
        YAML batch request written by ``check_workflows``.
    """
    import builtins
    import socket

    payload = yaml.safe_load(Path(request).read_text())
    root = Path.cwd()

    def unexpected_input(prompt):
        """Fail on an unexpected interactive prompt."""
        raise ValueError(f"Interactive choice required: {prompt}")

    builtins.input = unexpected_input
    socket.gethostname = lambda: ""
    # Reserve stdout for results; command output goes to the worker log.
    with redirect_stdout(sys.stderr):
        fixtures = _prepare_fixtures(payload, root)
    for index, ((kind, flavor, code), selected) in enumerate(payload["checks"]):
        payload["scenario"] = selected
        payload["case"] = (kind, flavor, code)
        payload["label"] = f"{kind}/{flavor or 'default'}/{code}"
        try:
            with redirect_stdout(sys.stderr):
                result = _run_case(payload, root / f"case-{index}", fixtures)
        finally:
            os.chdir(root)
        print(json.dumps(asdict(result)), flush=True)


if __name__ == "__main__":
    _worker(*sys.argv[1:])
