"""Bundled workflows and regression checks for the shared workflow checker."""

from copy import deepcopy
from pathlib import Path
import shutil

import pytest

from dftcaddie.checks import workflows as checker
from dftcaddie.checks.workflows import check_workflows
from dftcaddie.config import load_config

SCENARIOS = ("staged", "automatic", "auto", "reconfiguration")


@pytest.fixture(scope="module")
def workflow_requests():
    """Select the calculation/scenario combinations covered by this module."""
    cases = list(checker.calculation_cases(load_config(default_config=True)[0]))
    return [(case, "staged") for case in cases] + [
        (("bands", None, code), scenario)
        for scenario in SCENARIOS[1:]
        for code in ("quantum_espresso", "vasp")
    ]


@pytest.fixture(scope="module")
def workflow_batch(bundled_resources, workflow_requests):
    """Run all bundled scenarios in one worker, as a single shared batch."""
    workers = []
    seen = []
    popen = checker.subprocess.Popen

    def start_worker(*args, **kwargs):
        process = popen(*args, **kwargs)
        workers.append(process)
        return process

    def record(result):
        seen.append((result, workers[0].poll()))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(checker.subprocess, "Popen", start_worker)
        results = check_workflows(
            load_config(default_config=True)[0],
            bundled_resources,
            checks=workflow_requests,
            structure_path=Path(__file__).resolve().parent / "data/Si.cif",
            progress=record,
        )
    return results, seen, workers


@pytest.fixture
def workflow_check(workflow_batch):
    def check(case, scenario="staged"):
        results, _, _ = workflow_batch
        label = "/".join(value or "default" for value in case)
        return [
            result
            for result in results
            if result.case == label and result.scenario == scenario
        ]

    return check


def test_staged_calculation(workflow_check, calculation_case):
    results = workflow_check(calculation_case)
    assert len(results) == 1
    assert results[0].success, results[0]


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
@pytest.mark.parametrize("scenario", ["automatic", "auto"])
def test_automatic_matches_staged(workflow_check, code, scenario):
    results = workflow_check(("bands", None, code), scenario)
    assert len(results) == 1
    assert results[0].success, results[0]


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_reconfigure_and_repeat(workflow_check, code):
    results = workflow_check(("bands", None, code), "reconfiguration")
    assert len(results) == 1
    assert results[0].success, results[0]


def test_custom_resources_and_defaults_are_used(
    tmp_path, monkeypatch, bundled_config, bundled_resources
):
    source = tmp_path / "resources"
    shutil.copytree(bundled_resources / "templates", source / "templates")
    shutil.copytree(bundled_resources / "sbatch_headers", source / "sbatch_headers")
    shutil.copytree(bundled_resources / "kpaths", source / "kpaths")
    data = bundled_config
    data["default_cutoff_ratio"] = 2.3
    original = deepcopy(data)
    monkeypatch.setenv("PSLIBRARY", "/not-the-selected-library")
    # Poison the caller's config: workers must load the explicit input.
    user_config = tmp_path / ".config" / "dftcaddie"
    user_config.mkdir(parents=True)
    invalid = user_config / "config.yaml"
    invalid.write_text("invalid: [")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    before = Path.cwd()
    result = checker.check_workflows(
        data, source, case=("bands", None, "quantum_espresso")
    )
    assert len(result) == 1 and result[0].success, result
    template = source / "templates/quantum_espresso/SYSTEM.INFO"
    template.write_text(
        template.read_text().replace("ATM_NUM=Num", "# missing atom count")
    )
    contents = template.read_bytes()
    results = checker.check_workflows(data, source)
    qe_result = next(r for r in results if r.case == "bands/default/quantum_espresso")
    assert not qe_result.success
    assert qe_result.stage == "system output"
    assert "ATM_NUM" in qe_result.message
    assert all(r.success for r in results if r.case.endswith("/vasp"))
    assert data == original
    assert Path.cwd() == before
    assert template.read_bytes() == contents
    assert invalid.read_text() == "invalid: ["


def test_timeout_is_reported(bundled_config, bundled_resources, workflow_requests):
    results = checker.check_workflows(
        bundled_config, bundled_resources, checks=workflow_requests, timeout=0.001
    )
    assert [result.scenario for result in results] == [
        scenario for _, scenario in workflow_requests
    ]
    assert all(
        not result.success and "Timed out" in result.message for result in results
    )


def test_batch_reuses_worker_and_reports_progress(workflow_batch, workflow_requests):
    results, seen, workers = workflow_batch
    assert [result for result, _ in seen] == results
    assert seen[0][1] is None
    assert len(workers) == 1
    assert [(result.scenario, result.case) for result in results] == [
        (scenario, "/".join(value or "default" for value in case))
        for case, scenario in workflow_requests
    ]
    assert all(result.success for result in results), results
    assert workers[0].poll() is not None


def test_invalid_schema_is_reported_without_running(monkeypatch, bundled_resources):
    def unexpected_run(*args, **kwargs):
        raise AssertionError("Invalid configuration should not start a worker")

    monkeypatch.setattr(checker.subprocess, "Popen", unexpected_run)
    results = checker.check_workflows([], bundled_resources)
    assert results and all(not result.success for result in results)


def test_packaged_cif_matches_test_fixture():
    fixture = Path(__file__).resolve().parent / "data/Si.cif"
    assert (
        Path(checker.__file__).parent / "data/Si.cif"
    ).read_bytes() == fixture.read_bytes()
