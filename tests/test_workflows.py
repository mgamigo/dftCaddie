"""Bundled workflows and regression checks for the shared workflow checker."""

from copy import deepcopy
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from dftcaddie.checks import workflows as checker
from dftcaddie.checks.workflows import calculation_cases, check_workflows

RESOURCES = Path(__file__).resolve().parents[1] / "dftcaddie/resources"
with (RESOURCES / "config.yaml").open() as stream:
    BUNDLED = yaml.safe_load(stream)


@pytest.fixture(
    params=list(calculation_cases(BUNDLED)),
    ids=lambda case: "/".join(x or "default" for x in case),
)
def calculation_case(request):
    return request.param


@pytest.fixture
def workflow_check():
    def check(case, scenario="staged"):
        return check_workflows(
            BUNDLED,
            RESOURCES,
            case=case,
            scenario=scenario,
            structure_path=Path(__file__).resolve().parent / "data/Si.cif",
        )

    return check


def test_staged_calculation(workflow_check, calculation_case):
    results = workflow_check(calculation_case)
    assert len(results) == 1
    assert results[0].success, results[0]


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
@pytest.mark.parametrize("scenario", ["automatic", "init"])
def test_automatic_matches_staged(workflow_check, code, scenario):
    results = workflow_check(("bands", None, code), scenario)
    assert len(results) == 1
    assert results[0].success, results[0]


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_reconfigure_and_repeat(workflow_check, code):
    results = workflow_check(("bands", None, code), "reconfiguration")
    assert len(results) == 1
    assert results[0].success, results[0]


def bundled_data():
    return deepcopy(BUNDLED)


def test_custom_resources_and_defaults_are_used(tmp_path, monkeypatch):
    source = tmp_path / "resources"
    shutil.copytree(RESOURCES / "templates", source / "templates")
    shutil.copytree(RESOURCES / "sbatch_headers", source / "sbatch_headers")
    data = bundled_data()
    data["default_cutoff_ratio"] = 2.3
    original = deepcopy(data)
    monkeypatch.setenv("PSLIBRARY", "/not-the-selected-library")
    # Poison the caller's selection: workers must load the explicit input.
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("invalid: [")
    monkeypatch.setenv("DFTCADDIE_CONFIG", str(invalid))
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
    result = checker.check_workflows(
        data, source, case=("bands", None, "quantum_espresso")
    )
    assert len(result) == 1 and not result[0].success
    assert result[0].stage == "setup output"
    assert "ATM_NUM" in result[0].message
    assert data == original
    assert Path.cwd() == before
    assert template.read_bytes() == contents
    assert invalid.read_text() == "invalid: ["


def test_timeout_is_reported(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(checker.subprocess, "run", timeout)
    results = checker.check_workflows(
        bundled_data(), RESOURCES, case=("bands", None, "vasp"), timeout=0.1
    )
    assert not results[0].success
    assert "Timed out" in results[0].message


def test_invalid_schema_is_reported_without_running(monkeypatch):
    def unexpected_run(*args, **kwargs):
        raise AssertionError("Invalid configuration should not start a worker")

    monkeypatch.setattr(checker.subprocess, "run", unexpected_run)
    results = checker.check_workflows([], RESOURCES)
    assert results and all(not result.success for result in results)


def test_packaged_cif_matches_test_fixture():
    fixture = Path(__file__).resolve().parent / "data/Si.cif"
    assert (
        Path(checker.__file__).parent / "data/Si.cif"
    ).read_bytes() == fixture.read_bytes()
