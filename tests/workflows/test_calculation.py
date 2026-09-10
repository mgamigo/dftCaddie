"""Exercise every bundled calculation through the staged CLI workflow."""

from pathlib import Path

import numpy as np
from ase.io import read

from dftcaddie import utils


def test_staged_calculation(workflow, calculation_case):
    case = calculation_case
    flags = ["--flavor", case.flavor] if case.flavor else []
    workflow.run("calc", "--kind", case.kind, "--code", case.code, *flags)
    assert all(Path(Path(file).name).is_file() for file in case.files)
    kind, _, code = utils.resolve_calc_current_dir()
    assert (kind, code) == (case.kind, case.code)

    master = Path("master.sh").read_text()
    for file in case.files:
        name = Path(file).name
        if name.endswith(".sh") and name != "master.sh":
            assert master.count(f"bash {name}\n") == 1
    assert "bash master.sh" not in master

    workflow.run("setup", workflow.structure, "--autokgrid", "--kppra", "64", "--kpath")
    if case.code == "quantum_espresso":
        result = Path("SYSTEM.INFO").read_text()
        assert "NAME='Si8'" in result
        assert "ATM_NUM=8\n" in result
        assert "ATM_TYPES=1\n" in result
        assert "KGRID='2 2 2'" in result
        expected_path = (
            workflow.resources / "kpaths/quantum_espresso/SG227"
        ).read_text()
        assert expected_path.strip() in result
    else:
        assert case.code == "vasp", f"Add workflow assertions for {case.code}"
        expected = read(workflow.structure)
        actual = read("POSCAR")
        assert actual.get_chemical_symbols() == expected.get_chemical_symbols()
        np.testing.assert_allclose(actual.cell, expected.cell)
        np.testing.assert_allclose(
            actual.get_scaled_positions(), expected.get_scaled_positions()
        )
        assert "2 2 2" in Path("KPOINTS.SCC").read_text()
        assert (
            Path("KPOINTS.BS").read_bytes()
            == (workflow.resources / "kpaths/vasp/SG227").read_bytes()
        )

    workflow.run("pseudo", workflow.structure, "--configure", "--relativistic")
    ratio = workflow.config["default_cutoff_ratio"]
    if case.code == "quantum_espresso":
        result = Path("SYSTEM.INFO").read_text()
        assert result.count("Si.rel-pbe-nl-kjpaw_psl.1.0.0.UPF") == 1
        assert f"CUTOFF={int(40 * ratio)}\n" in result
        assert f"ECUTRHO={int(160 * ratio)}\n" in result
    else:
        assert Path("POTCAR").read_text() == workflow.potcar
        for incar in Path.cwd().glob("INCAR*"):
            result = incar.read_text()
            assert f"ENCUT = {int(200 * ratio)}" in result
            assert "LSORBIT = TRUE" in result

    body = master[master.index("#Actual JOBS") :]
    workflow.run("sbatch", "--cluster", "cluster2", "--header", "long")
    result = Path("master.sh").read_text()
    assert "#SBATCH --partition=long" in result
    assert result.endswith(body)
    assert result.count("# === DFTCADDIE SBATCH HEADER END ===") == 1
