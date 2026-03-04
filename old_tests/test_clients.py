from types import SimpleNamespace
import pytest
import builtins

import dftcaddie.calc_client as calc_client
import dftcaddie.setup_client as setup_client
import dftcaddie.pseudo_client as pseudo_client
import dftcaddie.sbatch_client as sbatch_client


def _make_calc_args(**overrides):
    # Provide everything calc_client.run() expects to exist on args
    base = dict(
        kind="bands",
        code="quantum_espresso",
        overwrite=True,
        details=False,
        structure="Si.cif",
        pseudo=False,
        init=False,
        cluster="local",
        # plus any config options your calculations["bands"]["config"] might add later
        soc=False,
        cell_relaxation=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_setup_args(
    structure="Si.cif",
    autokgrid=False,
    kppra=9000,
    kpath=False,
    pseudo=False,
):
    return SimpleNamespace(
        structure=structure,
        autokgrid=autokgrid,
        kppra=kppra,
        kpath=kpath,
        pseudo=pseudo,
    )


def _make_pseudo_args(
    structure="Si.cif",
    exchange="pbe",
    kind="kjpaw",
    relativistic=False,
    configure=False,
):
    return SimpleNamespace(
        structure=structure,
        exchange=exchange,
        kind=kind,
        relativistic=relativistic,
        configure=configure,
    )


def _make_sbatch_args(cluster=None, header=None):
    return SimpleNamespace(cluster=cluster, header=header)


def test_calc_client_calls_apply_setup_when_structure_provided(monkeypatch):
    # Patch get_structure so we don't rely on YAIV/spglib
    fake_structure = SimpleNamespace(
        symbols=["Si"], formula="Si", lattice=[], positions=[], space_group="225"
    )
    monkeypatch.setattr("dftcaddie.utils.get_structure", lambda path: fake_structure)

    # Patch filesystem-touching parts in file_management
    monkeypatch.setattr(
        "dftcaddie.file_management.copy_input_files",
        lambda calculation: ["bands.sh", "master.sh"],
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.populate_master_script",
        lambda master, files: ["bands.sh"],
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.set_master_preamble", lambda master, cluster: None
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.change_mpi_command", lambda scripts, cluster: None
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.configure_input_files", lambda calculation: None
    )

    # Capture apply_setup call
    called = {}

    def fake_apply_setup(**kwargs):
        called.update(kwargs)
        return None

    monkeypatch.setattr("dftcaddie.setup_client.apply_setup", fake_apply_setup)

    # Run
    args = _make_calc_args(structure="Si.cif", pseudo=False, init=False)
    calc_client.run(args)

    # Assert
    assert called, "apply_setup was not called"
    assert called["kind"] == "bands"
    assert called["code"] == "quantum_espresso"
    assert called["structure"] is fake_structure
    assert called["autokgrid"] is False
    assert called["kpath"] is False


def test_calc_client_calls_apply_pseudos_when_pseudo_true(monkeypatch):
    # Patch get_structure
    fake_structure = SimpleNamespace(
        symbols=["Si"], formula="Si", lattice=[], positions=[], space_group="225"
    )
    monkeypatch.setattr("dftcaddie.utils.get_structure", lambda path: fake_structure)

    # Patch file_management
    monkeypatch.setattr(
        "dftcaddie.file_management.copy_input_files",
        lambda calculation: ["bands.sh", "master.sh"],
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.populate_master_script",
        lambda master, files: ["bands.sh"],
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.set_master_preamble", lambda master, cluster: None
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.change_mpi_command", lambda scripts, cluster: None
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.configure_input_files", lambda calculation: None
    )

    # Patch apply_setup (still called if structure provided)
    monkeypatch.setattr("dftcaddie.setup_client.apply_setup", lambda **kwargs: None)

    # Capture apply_pseudos call
    called = {}

    def fake_apply_pseudos(**kwargs):
        called.update(kwargs)
        return None

    monkeypatch.setattr("dftcaddie.pseudo_client.apply_pseudos", fake_apply_pseudos)

    # Run
    args = _make_calc_args(structure="Si.cif", pseudo=True, init=False, soc=True)
    calc_client.run(args)

    # Assert
    assert called, "apply_pseudos was not called"
    assert called["kind_calc"] == "bands"
    assert called["code"] == "quantum_espresso"
    assert called["symbols"] == ["Si"]
    assert called["relativistic"] is True
    assert called["configure"] is True


def test_calc_client_no_structure_skips_apply_setup_and_apply_pseudos(monkeypatch):
    # Patch file_management to avoid filesystem
    monkeypatch.setattr(
        "dftcaddie.file_management.copy_input_files",
        lambda calculation: ["bands.sh", "master.sh"],
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.populate_master_script",
        lambda master, files: ["bands.sh"],
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.set_master_preamble", lambda master, cluster: None
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.change_mpi_command", lambda scripts, cluster: None
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.configure_input_files", lambda calculation: None
    )

    # Make them fail if called
    monkeypatch.setattr(
        "dftcaddie.setup_client.apply_setup",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("apply_setup called")),
    )
    monkeypatch.setattr(
        "dftcaddie.pseudo_client.apply_pseudos",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("apply_pseudos called")),
    )
    monkeypatch.setattr(
        "dftcaddie.utils.get_structure",
        lambda path: (_ for _ in ()).throw(AssertionError("get_structure called")),
    )

    # Run: structure is None
    args = _make_calc_args(structure=None, pseudo=True, init=True)
    calc_client.run(args)


def test_setup_client_run_calls_apply_setup(monkeypatch):
    # Arrange: patch utils resolution + structure reading
    fake_structure = SimpleNamespace(
        symbols=["Si"],
        formula="Si",
        lattice=[],
        positions=[],
        space_group="225",
    )

    monkeypatch.setattr(
        "dftcaddie.utils.resolve_calc_current_dir",
        lambda: ("bands", "quantum_espresso"),
    )
    monkeypatch.setattr(
        "dftcaddie.utils.get_structure",
        lambda path: fake_structure,
    )

    # Capture apply_setup call
    called = {}

    def fake_apply_setup(**kwargs):
        called.update(kwargs)
        return 0

    monkeypatch.setattr("dftcaddie.setup_client.apply_setup", fake_apply_setup)

    # Act
    args = _make_setup_args(autokgrid=True, kppra=1234, kpath=True, pseudo=False)
    setup_client.run(args)

    # Assert
    assert called, "apply_setup was not called"
    assert called["kind"] == "bands"
    assert called["code"] == "quantum_espresso"
    assert called["structure"] is fake_structure
    assert called["autokgrid"] is True
    assert called["kppra"] == 1234
    assert called["kpath"] is True


def test_setup_client_run_calls_apply_pseudos_with_relativistic_default(monkeypatch):
    # Arrange
    fake_structure = SimpleNamespace(
        symbols=["Si"],
        formula="Si",
        lattice=[],
        positions=[],
        space_group="225",
    )

    monkeypatch.setattr(
        "dftcaddie.utils.resolve_calc_current_dir",
        lambda: ("relax", "quantum_espresso"),
    )
    monkeypatch.setattr(
        "dftcaddie.utils.get_structure",
        lambda path: fake_structure,
    )

    # Ensure get_config returns default SOC/relativistic value
    monkeypatch.setattr(
        "dftcaddie.utils.get_config",
        lambda kind, config_name: {"name": config_name, "default": True},
    )

    # Patch apply_setup (so we don't touch filesystem in this test)
    monkeypatch.setattr("dftcaddie.setup_client.apply_setup", lambda **kwargs: 0)

    # Capture apply_pseudos call
    pseudos_called = {}

    def fake_apply_pseudos(**kwargs):
        pseudos_called.update(kwargs)
        return 0

    monkeypatch.setattr("dftcaddie.pseudo_client.apply_pseudos", fake_apply_pseudos)

    # Act
    args = _make_setup_args(pseudo=True)
    setup_client.run(args)

    # Assert
    assert pseudos_called, "apply_pseudos was not called"
    assert pseudos_called["kind_calc"] == "relax"
    assert pseudos_called["code"] == "quantum_espresso"
    assert pseudos_called["symbols"] == ["Si"]
    assert pseudos_called["relativistic"] is True
    assert pseudos_called["configure"] is True


def test_apply_setup_calls_file_management_conditionally(monkeypatch):
    # Arrange
    calls = {"crystal": 0, "kgrid": 0, "kpath": 0}

    def fake_set_crystal_structure(structure, code):
        calls["crystal"] += 1

    def fake_set_auto_kgrid(structure, code, kppra):
        calls["kgrid"] += 1
        # Verify kppra is passed through
        assert kppra == 777

    def fake_set_high_symmetry_path(structure, code):
        calls["kpath"] += 1

    monkeypatch.setattr(
        "dftcaddie.file_management.set_crystal_structure", fake_set_crystal_structure
    )
    monkeypatch.setattr("dftcaddie.file_management.set_auto_kgrid", fake_set_auto_kgrid)
    monkeypatch.setattr(
        "dftcaddie.file_management.set_high_symmetry_path", fake_set_high_symmetry_path
    )

    structure = SimpleNamespace(
        symbols=["Si"], lattice=[], positions=[], space_group="225"
    )

    # Act 1: nothing optional
    rc = setup_client.apply_setup(
        kind="bands",
        code="quantum_espresso",
        structure=structure,
        autokgrid=False,
        kppra=777,
        kpath=False,
    )
    assert rc == 0
    assert calls == {"crystal": 1, "kgrid": 0, "kpath": 0}

    # Act 2: enable both optional steps
    rc = setup_client.apply_setup(
        kind="bands",
        code="quantum_espresso",
        structure=structure,
        autokgrid=True,
        kppra=777,
        kpath=True,
    )
    assert rc == 0
    assert calls == {"crystal": 2, "kgrid": 1, "kpath": 1}


def test_pseudo_client_run_calls_apply_pseudos(monkeypatch):
    # Arrange: patch utils resolution + structure reading
    fake_structure = SimpleNamespace(symbols=["Si", "O"])

    monkeypatch.setattr(
        "dftcaddie.utils.resolve_calc_current_dir",
        lambda: ("relax", "quantum_espresso"),
    )
    monkeypatch.setattr(
        "dftcaddie.utils.get_structure",
        lambda path: fake_structure,
    )

    called = {}

    def fake_apply_pseudos(**kwargs):
        called.update(kwargs)
        return 0

    monkeypatch.setattr("dftcaddie.pseudo_client.apply_pseudos", fake_apply_pseudos)

    # Act
    args = _make_pseudo_args(
        structure="SiO2.cif",
        exchange="pbesol",
        kind="us",
        relativistic=True,
        configure=True,
    )
    pseudo_client.run(args)

    # Assert
    assert called, "apply_pseudos was not called"
    assert called["kind_calc"] == "relax"
    assert called["code"] == "quantum_espresso"
    assert called["symbols"] == ["Si", "O"]
    assert called["exchange"] == "pbesol"
    assert called["kind_pseudo"] == "us"
    assert called["relativistic"] is True
    assert called["configure"] is True


def test_apply_pseudos_calls_file_management_in_order(monkeypatch):
    # Arrange
    calls = []

    def fake_get_qe_pseudo_paths(**kwargs):
        calls.append(("get_qe_pseudo_paths", kwargs))
        return ["/pslib/Si.pbe.kjpaw.UPF", "/pslib/O.pbe.kjpaw.UPF"]

    def fake_write_pseudos_to_system_info(path, pseudos):
        calls.append(("write_pseudos_to_system_info", path, list(pseudos)))

    def fake_set_spin_orbit_coupling(kind_calc, code, relativistic):
        calls.append(("set_spin_orbit_coupling", kind_calc, code, relativistic))

    def fake_configure_qe_cutoffs_from_pseudos(path, pseudos, ratio=1.5):
        calls.append(("configure_qe_cutoffs_from_pseudos", path, list(pseudos), ratio))
        return (60, 600)

    monkeypatch.setattr(
        "dftcaddie.file_management.get_qe_pseudo_paths", fake_get_qe_pseudo_paths
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.write_pseudos_to_system_info",
        fake_write_pseudos_to_system_info,
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.set_spin_orbit_coupling",
        fake_set_spin_orbit_coupling,
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.configure_qe_cutoffs_from_pseudos",
        fake_configure_qe_cutoffs_from_pseudos,
    )

    # Act
    rc = pseudo_client.apply_pseudos(
        kind_calc="bands",
        code="quantum_espresso",
        symbols=["Si", "O"],
        exchange="pbe",
        kind_pseudo="kjpaw",
        relativistic=True,
        configure=True,
        system_info_path="SYSTEM.INFO",
        ratio=2.0,
    )

    # Assert
    assert rc == 0

    # Check key sequencing + arguments
    assert calls[0][0] == "get_qe_pseudo_paths"
    assert calls[0][1]["symbols"] == ["Si", "O"]
    assert calls[0][1]["exchange"] == "pbe"
    assert calls[0][1]["kind"] == "kjpaw"
    assert calls[0][1]["relativistic"] is True

    assert calls[1][0] == "write_pseudos_to_system_info"
    assert calls[1][1] == "SYSTEM.INFO"
    assert calls[2] == ("set_spin_orbit_coupling", "bands", "quantum_espresso", True)

    # configure=True => cutoffs must be configured
    assert calls[3][0] == "configure_qe_cutoffs_from_pseudos"
    assert calls[3][1] == "SYSTEM.INFO"
    assert calls[3][3] == 2.0  # ratio passed through


def test_apply_pseudos_does_not_configure_cutoffs_when_configure_false(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        "dftcaddie.file_management.get_qe_pseudo_paths",
        lambda **kwargs: ["/pslib/Si.pbe.kjpaw.UPF"],
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.write_pseudos_to_system_info",
        lambda path, pseudos: None,
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.set_spin_orbit_coupling",
        lambda kind_calc, code, relativistic: None,
    )

    # If this gets called, we want the test to fail loudly
    def _boom(*args, **kwargs):
        raise AssertionError("configure_qe_cutoffs_from_pseudos should not be called")

    monkeypatch.setattr(
        "dftcaddie.file_management.configure_qe_cutoffs_from_pseudos", _boom
    )

    # Act
    rc = pseudo_client.apply_pseudos(
        kind_calc="relax",
        code="quantum_espresso",
        symbols=["Si"],
        exchange="pbe",
        kind_pseudo="kjpaw",
        relativistic=False,
        configure=False,
    )

    # Assert
    assert rc == 0


def test_apply_pseudos_raises_for_unsupported_code():
    with pytest.warns(UserWarning, match="Pseudo client skipped"):
        pseudo_client.apply_pseudos(
            kind_calc="relax",
            code="UNKNOWN_CODE",
            symbols=["Si"],
            exchange="pbe",
            kind_pseudo="kjpaw",
            relativistic=False,
            configure=False,
        )

def test_sbatch_run_resolves_cluster_and_applies_header_when_header_provided(
    monkeypatch,
):
    # Provide a minimal clusters config for the client
    monkeypatch.setattr(
        "dftcaddie.config.clusters",
        {
            "local": {
                "headers": [
                    {"name": "short"},
                    {"name": "long"},
                ]
            }
        },
    )

    # If args.cluster is None, it should use resolve_cluster()
    monkeypatch.setattr("dftcaddie.utils.resolve_cluster", lambda clusters: "local")

    # Avoid sys.exit in check_option_exists
    monkeypatch.setattr("dftcaddie.utils.check_option_exists", lambda *a, **k: None)

    called = {}

    def fake_apply_header(cluster, header):
        called["cluster"] = cluster
        called["header"] = header
        return 0

    monkeypatch.setattr(sbatch_client, "apply_header", fake_apply_header)

    args = _make_sbatch_args(cluster=None, header="long")
    sbatch_client.run(args)

    assert called["cluster"] == "local"
    assert called["header"] == 1  # "long" is index 1


def test_sbatch_run_interactive_header_selection(monkeypatch):
    monkeypatch.setattr(
        "dftcaddie.config.clusters",
        {
            "local": {
                "headers": [
                    {"name": "short"},
                    {"name": "long"},
                    {"name": "debug"},
                ]
            }
        },
    )

    # cluster already provided -> no need to resolve hostname
    monkeypatch.setattr("dftcaddie.utils.check_option_exists", lambda *a, **k: None)

    # The interactive path prints numbered options + uses input + resolve_user_input
    monkeypatch.setattr(
        "dftcaddie.utils.format_options",
        lambda opts, numbers=False, **k: "1) short, 2) long, 3) debug",
    )
    monkeypatch.setattr(builtins, "input", lambda prompt="": "2")  # user types "2"
    monkeypatch.setattr(
        "dftcaddie.utils.resolve_user_input", lambda user_input, options: "long"
    )

    called = {}

    monkeypatch.setattr(
        sbatch_client,
        "apply_header",
        lambda cluster, header: called.update({"cluster": cluster, "header": header})
        or 0,
    )

    args = _make_sbatch_args(cluster="local", header=None)
    sbatch_client.run(args)

    assert called["cluster"] == "local"
    assert called["header"] == 1  # "long" is index 1


def test_apply_header_preserves_existing_job_name_and_calls_file_management(
    monkeypatch, tmp_path
):
    # Work in a temp dir because apply_header opens "master.sh"
    monkeypatch.chdir(tmp_path)

    master = tmp_path / "master.sh"
    master.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                '#SBATCH --job-name="MYJOB"',
                "#SBATCH --time=01:00:00",
                "# === DFTCADDIE SBATCH HEADER END ===",
                "echo hi",
                "",
            ]
        ),
        encoding="utf-8",
    )

    calls = []

    monkeypatch.setattr(
        "dftcaddie.file_management.remove_master_preamble",
        lambda path: calls.append(("remove_master_preamble", path)),
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.set_master_preamble",
        lambda path, cluster, header: calls.append(
            ("set_master_preamble", path, cluster, header)
        ),
    )
    monkeypatch.setattr(
        "dftcaddie.file_management._replace_setting",
        lambda path, match, new_line: calls.append(
            ("replace_setting", path, match, new_line)
        ),
    )

    rc = sbatch_client.apply_header(cluster="local", header=0)

    assert rc == 0
    assert calls[0] == ("remove_master_preamble", "master.sh")
    assert calls[1] == ("set_master_preamble", "master.sh", "local", 0)
    assert calls[2] == (
        "replace_setting",
        "master.sh",
        "#SBATCH --job-name",
        '#SBATCH --job-name="MYJOB"',
    )


def test_apply_header_defaults_job_name_when_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master.sh").write_text(
        "\n".join(
            [
                "#!/bin/bash",
                "#SBATCH --time=01:00:00",
                "# === DFTCADDIE SBATCH HEADER END ===",
                "echo hi",
                "",
            ]
        ),
        encoding="utf-8",
    )

    calls = []
    monkeypatch.setattr(
        "dftcaddie.file_management.remove_master_preamble",
        lambda path: None,
    )
    monkeypatch.setattr(
        "dftcaddie.file_management.set_master_preamble",
        lambda path, cluster, header: None,
    )
    monkeypatch.setattr(
        "dftcaddie.file_management._replace_setting",
        lambda path, match, new_line: calls.append((match, new_line)),
    )

    rc = sbatch_client.apply_header(cluster="local", header=0)

    assert rc == 0
    assert calls == [
        ("#SBATCH --job-name", '#SBATCH --job-name="NONAME"'),
    ]
