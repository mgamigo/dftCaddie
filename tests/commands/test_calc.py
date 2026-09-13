from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dftcaddie import utils
from dftcaddie.commands import calc
from dftcaddie.commands.set import pseudo, system


@pytest.mark.parametrize("flag", ["--pseudo", "--auto"])
def test_supplied_structure_controls_generated_vasp_inputs(parse_args, monkeypatch, flag):
    from ase.build import bulk
    from ase.io import write
    from dftcaddie import file_management as fm

    write("POSCAR", bulk("Si"), format="vasp")
    write("Ge.cif", bulk("Ge"))
    original = Path("POSCAR").read_bytes()
    potential = Path("Ge.POTCAR")
    potential.write_text("Germanium potential\n ENMAX = 200;\n")
    finder = Mock(return_value=[str(potential)])
    grid = Mock(wraps=fm.set_auto_kgrid)
    monkeypatch.setattr(fm, "get_potcar_paths", finder)
    monkeypatch.setattr(fm, "set_auto_kgrid", grid)

    calc.run(
        parse_args(
            "calc",
            "--kind",
            "bands",
            "--code",
            "vasp",
            "--structure",
            "Ge.cif",
            flag,
        )
    )

    assert Path("POSCAR").read_bytes() == original
    finder.assert_called_once_with(symbols=["Ge", "Ge"], exchange="pbe", kind="paw")
    assert Path("POTCAR").read_bytes() == potential.read_bytes()
    if flag == "--auto":
        assert grid.call_args.args[0].symbols == ["Ge", "Ge"]
    else:
        grid.assert_not_called()


@pytest.mark.parametrize("flag", ["-a", "--auto", "-p", "--pseudo"])
def test_calc_requires_structure_before_prompting_or_writing(
    parse_args, monkeypatch, flag, caplog
):
    def unexpected_prompt(prompt):
        pytest.fail("Invalid requests must not prompt")

    monkeypatch.setattr("builtins.input", unexpected_prompt)
    Path("notes.txt").write_text("Keep these notes.\n")
    before = {p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()}
    with pytest.raises(SystemExit) as error:
        calc.run(parse_args("calc", flag))
    assert error.value.code == 1
    assert "require --structure FILE" in caplog.text
    assert {
        p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()
    } == before


@pytest.mark.parametrize(
    "flavor,expected", [("fixed_cell", "relax"), ("variable_cell", "vc-relax")]
)
def test_calc_relax_flavor(parse_args, flavor, expected):
    calc.run(
        parse_args(
            "calc",
            "--kind",
            "relax",
            "--flavor",
            flavor,
            "--code",
            "quantum_espresso",
        )
    )
    assert f"calculation='{expected}'" in Path("relax.sh").read_text()


def test_calc_interactive_details(parse_args, monkeypatch):
    answers = iter(["bands", "quantum_espresso", False])
    monkeypatch.setattr(
        "dftcaddie.prompts.select", lambda *args, **kwargs: next(answers)
    )
    calc.run(parse_args("calc", "--details"))
    assert "noncolin=.false." in Path("scf.sh").read_text()
    assert "lspinorb=.false." in Path("scf.sh").read_text()


def test_calc_overwrite(parse_args):
    args = parse_args(
        "calc", "--kind", "bands", "--code", "quantum_espresso", "--overwrite"
    )
    calc.run(args)
    Path("bands.sh").write_text("old contents\n")
    calc.run(args)
    assert "old contents" not in Path("bands.sh").read_text()
    assert Path("master.sh").read_text().count("bash bands.sh\n") == 1


@pytest.mark.parametrize(
    "flags",
    [
        ("--kind", "unknown"),
        ("--kind", "bands", "--code", "unknown"),
        ("--kind", "relax", "--flavor", "unknown"),
    ],
)
def test_calc_rejects_invalid_selection(parse_args, flags):
    with pytest.raises(SystemExit) as error:
        calc.run(parse_args("calc", *flags))
    assert error.value.code == 1
    assert not Path("master.sh").exists()


def test_calc_structure_without_pseudo(parse_args, monkeypatch):
    structure = SimpleNamespace(symbols=["Si"])
    setup_step, pseudo_step = Mock(), Mock()
    monkeypatch.setattr(utils, "get_structure", lambda path: structure)
    monkeypatch.setattr(system, "apply_system", setup_step)
    monkeypatch.setattr(pseudo, "apply_pseudos", pseudo_step)
    calc.run(
        parse_args(
            "calc",
            "--kind",
            "bands",
            "--code",
            "quantum_espresso",
            "-s",
            "Si.cif",
        )
    )
    setup_step.assert_called_once_with(
        kind="bands",
        code="quantum_espresso",
        structure=structure,
        autokgrid=False,
        kpath=False,
        files={"scf.sh", "bands.sh", "project_bands.sh", "SYSTEM.INFO", "master.sh"},
    )
    pseudo_step.assert_not_called()


@pytest.mark.parametrize("flag", ["-a", "--auto"])
def test_calc_auto_runs_full_setup(parse_args, monkeypatch, flag):
    structure = SimpleNamespace(symbols=["Si"])
    setup_step, pseudo_step = Mock(), Mock()
    monkeypatch.setattr(utils, "get_structure", lambda path: structure)
    monkeypatch.setattr(system, "apply_system", setup_step)
    monkeypatch.setattr(pseudo, "apply_pseudos", pseudo_step)

    calc.run(
        parse_args(
            "calc",
            "--kind",
            "bands",
            "--code",
            "quantum_espresso",
            "--structure",
            "Si.cif",
            flag,
        )
    )

    setup_step.assert_called_once_with(
        kind="bands",
        code="quantum_espresso",
        structure=structure,
        autokgrid=True,
        kpath=True,
        files={"scf.sh", "bands.sh", "project_bands.sh", "SYSTEM.INFO", "master.sh"},
    )
    pseudo_step.assert_called_once_with(
        kind_calc="bands",
        code="quantum_espresso",
        symbols=structure.symbols,
        relativistic=True,
        configure=True,
        files={"scf.sh", "bands.sh", "project_bands.sh", "SYSTEM.INFO", "master.sh"},
    )
