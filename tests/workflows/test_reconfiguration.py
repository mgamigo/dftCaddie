"""Ensure repeated configuration preserves files and replaces selected values."""

from pathlib import Path

import pytest


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
def test_reconfigure_and_repeat(workflow, code):
    workflow.run("calc", "-k", "bands", "-c", code)
    workflow.run("setup", workflow.structure, "--autokgrid", "--kppra", "64")
    workflow.run("pseudo", workflow.structure, "--configure", "--relativistic")
    workflow.run("sbatch", "--cluster", "cluster2", "--header", "long")
    grid_file = Path("SYSTEM.INFO" if code == "quantum_espresso" else "KPOINTS.SCC")
    old_grid = grid_file.read_bytes()
    Path("notes.txt").write_text("Keep my calculation notes.\n")

    def reconfigure():
        workflow.run("setup", workflow.structure, "--autokgrid", "--kppra", "4096")
        workflow.run("pseudo", workflow.structure, "--configure")
        workflow.run("sbatch", "--cluster", "cluster1", "--header", "default")

    reconfigure()
    assert grid_file.read_bytes() != old_grid
    assert Path("notes.txt").read_text() == "Keep my calculation notes.\n"
    assert "#SBATCH --partition=long" not in Path("master.sh").read_text()
    if code == "quantum_espresso":
        result = Path("SYSTEM.INFO").read_text()
        assert "Si.pbe-nl-kjpaw_psl.1.0.0.UPF" in result
        assert "Si.rel-pbe" not in result
        assert "noncolin=.false." in Path("scf.sh").read_text()
    else:
        assert Path("POTCAR").read_text() == workflow.potcar
        assert "LSORBIT = FALSE" in Path("INCAR.SCC").read_text()
    before = {p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()}
    reconfigure()
    assert {
        p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()
    } == before
