from pathlib import Path
from types import SimpleNamespace

import pytest

import dftcaddie.file_management as fm


# -------------------------
# Helpers: private utilities
# -------------------------


def test_replace_setting_preserves_indentation(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("  noncolin=.false.\nother=1\n", encoding="utf-8")

    fm._replace_setting(str(f), "noncolin=", "noncolin=.true.")
    text = f.read_text(encoding="utf-8").splitlines()

    assert text[0] == "  noncolin=.true."
    assert text[1] == "other=1"


def test_insert_lines_inserts_after_match(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("start\nMARK\nend\n", encoding="utf-8")

    fm._insert_lines(str(f), ["L1\n", "L2\n"], "MARK")
    text = f.read_text(encoding="utf-8")

    assert text == "start\nMARK\nL1\nL2\nend\n"


def test_insert_lines_no_match_leaves_file_unchanged(tmp_path: Path):
    f = tmp_path / "a.txt"
    original = "start\nend\n"
    f.write_text(original, encoding="utf-8")

    fm._insert_lines(str(f), ["L1\n"], "MISSING_MARK")
    assert f.read_text(encoding="utf-8") == original


def test_remove_lines_between_markers_exclusive(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text(
        "A\nSTART\n1\n2\n3\nEND\nB\n",
        encoding="utf-8",
    )

    fm._remove_lines(str(f), "START", "END")
    assert f.read_text(encoding="utf-8") == "A\nSTART\nEND\nB\n"


def test_remove_lines_missing_markers_leaves_file_unchanged(tmp_path: Path):
    f = tmp_path / "a.txt"
    original = "A\nB\n"
    f.write_text(original, encoding="utf-8")

    fm._remove_lines(str(f), "START", "END")
    assert f.read_text(encoding="utf-8") == original


# -------------------------
# populate_master_script
# -------------------------


def test_populate_master_script_adds_only_sh_and_not_self(tmp_path: Path):
    master = tmp_path / "master.sh"
    master.write_text("#!/bin/bash\n#Actual JOBS\n", encoding="utf-8")

    subs = ["a.sh", "b.sh", "notes.txt", "master.sh"]
    added = fm.populate_master_script(str(master), subs)

    # Only .sh and not master.sh
    assert added == ["a.sh", "b.sh"]

    text = master.read_text(encoding="utf-8")
    assert "bash a.sh\n" in text
    assert "bash b.sh\n" in text
    assert "notes.txt" not in text


# -------------------------
# set_master_preamble
# -------------------------


def test_set_master_preamble_prepends_header(tmp_path: Path, monkeypatch):
    # Create fake "package data" dir structure next to file_management.py
    # We monkeypatch fm.__file__ so its dirname points to our tmp tree.
    pkg_root = tmp_path / "pkg"
    (pkg_root / "data" / "sbatch_headers").mkdir(parents=True)

    header_file = pkg_root / "data" / "sbatch_headers" / "header.txt"
    header_file.write_text("#SBATCH -A TEST\n", encoding="utf-8")

    master = tmp_path / "master.sh"
    master.write_text("#!/bin/bash\necho hi\n", encoding="utf-8")

    monkeypatch.setattr(fm, "__file__", str(pkg_root / "file_management.py"))
    monkeypatch.setattr(
        fm,
        "clusters",
        {"mycluster": {"headers": [{"name": "default", "file": "header.txt"}]}},
    )
    print(master)

    fm.set_master_preamble(str(master), "mycluster")

    text = master.read_text(encoding="utf-8").splitlines()
    for line in text:
        print(line)

    assert text[0] == "#!/bin/bash"
    assert text[1] == "#SBATCH -A TEST"
    assert text[2] == "echo hi"


# -------------------------
# change_mpi_command
# -------------------------


def test_change_mpi_command_replaces_existing_prefix(tmp_path: Path, monkeypatch):
    script = tmp_path / "run.sh"
    script.write_text(
        "srun pw.x -in in.pwi\n" "mpirun -np 4 pw.x -in in2.pwi\n" "echo done\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(fm, "mpi_executables", ["pw.x"])
    monkeypatch.setattr(
        fm,
        "clusters",
        {
            "c1": {"mpi_command": "srun"},
            "c2": {"mpi_command": "mpirun -np 4"},
            "target": {"mpi_command": "srun -n 8"},
        },
    )

    fm.change_mpi_command(str(script), "target")

    lines = script.read_text(encoding="utf-8").splitlines()

    # Both lines containing pw.x must start with target mpi command
    assert lines[0].startswith("srun -n 8 ")
    assert lines[1].startswith("srun -n 8 ")
    # Non-mpi line unchanged
    assert lines[2] == "echo done"


def test_change_mpi_command_no_matching_executable_no_change(
    tmp_path: Path, monkeypatch
):
    script = tmp_path / "run.sh"
    script.write_text("echo hello\n", encoding="utf-8")

    monkeypatch.setattr(fm, "mpi_executables", ["pw.x"])
    monkeypatch.setattr(fm, "clusters", {"target": {"mpi_command": "srun -n 8"}})

    fm.change_mpi_command(str(script), "target")
    assert script.read_text(encoding="utf-8") == "echo hello\n"


# -------------------------
# set_cell_relaxation
# -------------------------


def test_set_cell_relaxation_edits_relax_sh(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relax = tmp_path / "relax.sh"
    relax.write_text("calculation='relax'\n", encoding="utf-8")

    fm.set_cell_relaxation(code="quantum_espresso", cell_relaxation=True)
    assert "calculation='vc-relax'" in relax.read_text(encoding="utf-8")

    fm.set_cell_relaxation(code="quantum_espresso", cell_relaxation=False)
    assert "calculation='relax'" in relax.read_text(encoding="utf-8")


# -------------------------
# set_spin_orbit_coupling
# -------------------------


def test_set_spin_orbit_coupling_edits_all_sh_scripts(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Create two scripts
    (tmp_path / "a.sh").write_text(
        "noncolin=.false.\nlspinorb=.false.\n", encoding="utf-8"
    )
    (tmp_path / "b.sh").write_text(
        "  noncolin=.false.\n  lspinorb=.false.\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        fm,
        "calculations",
        {"bands": {"files": {"quantum_espresso": ["a.sh", "b.sh", "SYSTEM.INFO"]}}},
    )

    fm.set_spin_orbit_coupling(kind="bands", code="quantum_espresso", soc=True)

    assert "noncolin=.true." in (tmp_path / "a.sh").read_text(encoding="utf-8")
    assert "lspinorb=.true." in (tmp_path / "a.sh").read_text(encoding="utf-8")

    # indentation preserved in b.sh
    assert (
        (tmp_path / "b.sh")
        .read_text(encoding="utf-8")
        .splitlines()[0]
        .startswith("  noncolin=.true.")
    )


# -------------------------
# set_crystal_structure
# -------------------------


def test_set_crystal_structure_updates_system_info(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    system = tmp_path / "SYSTEM.INFO"
    system.write_text(
        "NAME='NoName'\n"
        "ATM_NUM=\n"
        "ATM_TYPES=\n"
        "ATOMIC_CRYST_POSITIONS=\n"
        "old\n"
        "EOL\n"
        "LATTICE=\n"
        "old\n"
        "EOL\n",
        encoding="utf-8",
    )

    structure = SimpleNamespace(
        formula="Si2",
        lattice=[
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        positions=[
            [0.0, 0.0, 0.0],
            [0.25, 0.25, 0.25],
        ],
        symbols=["Si", "Si"],
    )

    fm.set_crystal_structure(structure, code="quantum_espresso")
    text = system.read_text(encoding="utf-8")

    assert "NAME='Si2'" in text
    assert "ATM_NUM=2" in text
    assert "ATM_TYPES=1" in text
    assert "Si" in text  # species label appears in position lines
    assert "0.250000000" in text  # formatted fraction


# -------------------------
# configure_qe_cutoffs_from_pseudos
# -------------------------


def test_configure_qe_cutoffs_from_pseudos_reads_headers_and_sets_values(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    system = tmp_path / "SYSTEM.INFO"
    system.write_text("CUTOFF=\nECUTRHO=\n", encoding="utf-8")

    p1 = tmp_path / "Si.pbe.UPF"
    p2 = tmp_path / "O.pbe.UPF"
    p1.write_text(
        "Suggested minimum cutoff for wavefunctions: 50 Ry\n"
        "Suggested minimum cutoff for charge density: 400 Ry\n",
        encoding="utf-8",
    )
    p2.write_text(
        "Suggested minimum cutoff for wavefunctions: 60 Ry\n"
        "Suggested minimum cutoff for charge density: 500 Ry\n",
        encoding="utf-8",
    )

    cutoff, ecutrho = fm.configure_qe_cutoffs_from_pseudos(
        str(system),
        [str(p1), str(p2)],
        ratio=1.5,
    )

    # max(50,60)*1.5 = 90
    assert cutoff == 90
    # max(400,500)*1.5 = 750
    assert ecutrho == 750

    txt = system.read_text(encoding="utf-8")
    assert "CUTOFF=90" in txt
    assert "ECUTRHO=750" in txt


def test_configure_qe_cutoffs_from_pseudos_raises_if_missing_values(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    system = tmp_path / "SYSTEM.INFO"
    system.write_text("CUTOFF=\nECUTRHO=\n", encoding="utf-8")

    p1 = tmp_path / "Si.pbe.UPF"
    p1.write_text(
        "Suggested minimum cutoff for wavefunctions: 50 Ry\n", encoding="utf-8"
    )

    with pytest.raises(RuntimeError):
        fm.configure_qe_cutoffs_from_pseudos(str(system), [str(p1)], ratio=1.0)


# -------------------------
# get_qe_pseudo_paths (mocked)
# -------------------------


def test_get_qe_pseudo_paths_uses_resolve_pslibrary_and_glob(
    tmp_path: Path, monkeypatch
):
    root = tmp_path / "pslib"
    pseudo_dir = root / "pbe" / "PSEUDOPOTENTIALS"
    pseudo_dir.mkdir(parents=True)

    # Make the template realistic (no "XXXXXX" hacks)
    monkeypatch.setattr(
        fm,
        "suggested_qe_pseudos",
        {"Si": "Si.$fct-*.UPF"},
    )

    monkeypatch.setattr(
        "dftcaddie.config.resolve_pslibrary",
        lambda: str(root),
    )

    match = pseudo_dir / "Si.pbe-kjpaw.UPF"
    match.write_text("pseudo", encoding="utf-8")

    paths = fm.get_qe_pseudo_paths(
        symbols=["Si"], exchange="pbe", kind="kjpaw", relativistic=False
    )

    assert paths == [str(match)]
