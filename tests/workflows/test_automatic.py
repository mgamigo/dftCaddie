"""Compare combined command options with explicit preparation steps."""

from pathlib import Path

import pytest


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_calc_structure_and_pseudo_matches_staged(workflow, monkeypatch, code):
    workflow.run(
        "calc", "-k", "bands", "-c", code, "-s", workflow.structure, "--pseudo"
    )
    automatic = {p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()}
    staged = workflow.directory.parent / "staged"
    staged.mkdir()
    monkeypatch.chdir(staged)
    workflow.run("calc", "-k", "bands", "-c", code)
    workflow.run("setup", workflow.structure, "--pseudo")
    assert {
        p.name: p.read_bytes() for p in staged.iterdir() if p.is_file()
    } == automatic


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_calc_init_matches_staged(workflow, monkeypatch, code):
    workflow.run("calc", "-k", "bands", "-c", code, "-s", workflow.structure, "--init")
    automatic = {p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()}
    staged = workflow.directory.parent / "staged"
    staged.mkdir()
    monkeypatch.chdir(staged)
    workflow.run("calc", "-k", "bands", "-c", code)
    workflow.run("setup", workflow.structure, "--autokgrid", "--kpath", "--pseudo")
    assert {
        p.name: p.read_bytes() for p in staged.iterdir() if p.is_file()
    } == automatic
