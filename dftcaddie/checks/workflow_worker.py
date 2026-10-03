"""
Process isolation and shared fixtures for workflow checks.

The parent writes a request into a temporary directory and receives one JSON
result per case. The child installs synthetic potentials and copied resources
under its own HOME, then delegates each scenario to workflow_cases.

Private functions
-----------------
_run_worker()
    Start the subprocess, collect results, enforce timeouts, and clean up.
_worker()
    Run the child process and stream case results back to the parent.
_prepare_fixtures()
    Install the structure, synthetic libraries, and editable resources once.
"""

from contextlib import redirect_stdout
from dataclasses import asdict
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

from dftcaddie.checks.workflows import WorkflowResult
from dftcaddie.checks.workflow_cases import _has_code_family, _run_case


def _run_worker(payload, timeout, progress):
    """
    Run a batch in one isolated process and forward results as they arrive.

    Parameters
    ----------
    payload : dict
        Validated configuration, resource paths, and requested checks.
    timeout : float
        Maximum wait for each result.
    progress : callable or None
        Callback receiving each result immediately.

    Returns
    -------
    list of WorkflowResult
        Ordered outcomes, including failures if the worker stops early.
    """
    results = []

    def record(result):
        results.append(result)
        if progress is not None:
            progress(result)

    # One process and resource installation for the entire batch.
    with TemporaryDirectory(prefix="dftcaddie-check-") as root:
        root = Path(root)
        request = root / "request.yaml"
        request.write_text(yaml.safe_dump(payload))
        env = dict(os.environ)
        # Only the child gets this HOME. Its CLI calls must not load or overwrite
        # the real user's configuration and editable resources.
        env["HOME"] = str(root / "home")
        # Also support source checkouts not installed into this interpreter.
        env["PYTHONPATH"] = os.pathsep.join(
            [str(Path(__file__).resolve().parents[2]), env.get("PYTHONPATH", "")]
        )
        # Labels mirror output order, including jobs left unfinished after failure.
        jobs = [
            (f"{kind}/{flavor or 'default'}/{code}", selected)
            for (kind, flavor, code), selected in payload["checks"]
        ]
        # Read on a thread so the parent can time out instead of blocking forever
        # in readline() if a command hangs.
        messages = Queue()

        def read_results(stream):
            for line in stream:
                messages.put(line)
            # EOF is distinct from an empty queue: no further results can arrive.
            messages.put(None)

        try:
            with (
                (root / "worker.log").open("w+") as log,
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "dftcaddie.checks.workflow_worker",
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
                # Once the worker fails, mark remaining jobs with that failure.
                failure = None
                try:
                    for label, selected in jobs:
                        if failure is None:
                            try:
                                # This deadline is per result, not for the whole batch.
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
                # Reap the process on success, timeout, or malformed output.
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    reader.join()
        except OSError as exc:
            for label, selected in jobs[len(results) :]:
                record(WorkflowResult(label, False, "worker", str(exc), selected))
    return results


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

    # Checks must be unattended and portable: reject prompts and force the
    # local-cluster fallback rather than using the machine's hostname.
    builtins.input = unexpected_input
    socket.gethostname = lambda: ""
    # Reserve stdout for results; command output goes to the worker log.
    with redirect_stdout(sys.stderr):
        fixtures = _prepare_fixtures(payload, root)
    # Share fixtures but isolate generated files in one directory per case/scenario.
    for index, ((kind, flavor, code), selected) in enumerate(payload["checks"]):
        payload["scenario"] = selected
        payload["case"] = (kind, flavor, code)
        payload["label"] = f"{kind}/{flavor or 'default'}/{code}"
        try:
            with redirect_stdout(sys.stderr):
                result = _run_case(payload, root / f"case-{index}", fixtures)
        finally:
            # Commands use cwd heavily; restore it even when a case fails.
            os.chdir(root)
        print(json.dumps(asdict(result)), flush=True)


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
    # Filenames are kept for assertions; library definitions go into worker YAML.
    names = {}
    libraries = {}
    if any(
        _has_code_family(case[2], "quantum_espresso") for case, _ in payload["checks"]
    ):
        # Distinct scalar/SOC headers exercise selection and cutoff extraction.
        # They are preparation fixtures, not usable inputs for a DFT calculation.
        for selection, relativity in (("scalar", "scalar"), ("soc", "full")):
            name = f"Si.{selection}.UPF"
            directory = qe / selection
            directory.mkdir(parents=True)
            has_so = "T" if selection == "soc" else "F"
            (directory / name).write_text(
                '<UPF version="2.0.1">\n'
                f'<PP_HEADER element="Si" pseudo_type="NC" '
                f'relativistic="{relativity}" has_so="{has_so}" '
                'functional="PBE" wfc_cutoff="40" rho_cutoff="160"/>\n'
                '</UPF>\n'
            )
            names[selection] = name
            libraries[selection] = {
                "path": str(directory),
                "pattern": "{element}.*.UPF",
            }
        data["upf_pseudopotentials"] = {
            "defaults": {"scalar": "scalar", "soc": "soc"},
            "libraries": libraries,
        }
    # Real potential preferences must not affect these synthetic selections.
    data["suggested_upf_pseudos"] = {}
    data["suggested_potcar_pseudos"] = {}
    vasp = root / "vasp/PAW_PBE/Si"
    vasp.mkdir(parents=True)
    # VASP checks need only an ENMAX value and known bytes to concatenate.
    potcar = "Synthetic Si potential for testing only\n ENMAX = 200.0; ENMIN = 150.0\n"
    (vasp / "POTCAR").write_text(potcar)
    data["potcar_pseudopotentials"] = {
        "defaults": {"scalar": "pbe", "soc": "pbe"},
        "libraries": {
            "pbe": {"path": str(vasp.parent), "pattern": "{element}/POTCAR"}
        },
    }

    # Install editable resources once for the active worker configuration.
    user_config = Path.home() / ".config" / "dftcaddie"
    user_config.mkdir(parents=True)
    # Reproduce config init's directory layout within the temporary HOME.
    for directory in ("templates", "sbatch_headers", "kpaths"):
        shutil.copytree(Path(payload["source"]) / directory, user_config / directory)
    (user_config / "config.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    return structure, names, potcar


if __name__ == "__main__":
    _worker(*sys.argv[1:])
