from pathlib import Path
from unittest.mock import Mock

import pytest

from dftcaddie import utils
from dftcaddie.commands.set import cluster as header


@pytest.mark.parametrize("code", ["quantum_espresso", "vasp"])
@pytest.mark.parametrize("mode", [(), ("--no-header",), ("--no-mpi",)])
def test_cluster_updates_inferred_scripts(parse_args, bundled_config, code, mode):
    from dftcaddie.commands import calc

    calc.run(parse_args("calc", "--kind", "bands", "--code", code))
    Path("unrelated.sh").write_text("$QE_PATH/pw.x\n")
    master_before = Path("master.sh").read_bytes()
    scripts = [p for p in Path.cwd().glob("*.sh") if p.name not in ("master.sh", "unrelated.sh")]
    before = {p: p.read_bytes() for p in scripts}
    flags = () if "--no-header" in mode else ("--header", "long")
    args = parse_args("set", "cluster", "--cluster", "cluster2", *flags, *mode)
    header.run(args)
    if "--no-header" in mode:
        assert Path("master.sh").read_bytes() == master_before
    else:
        assert Path("master.sh").read_bytes() != master_before
    if "--no-mpi" in mode:
        assert {p: p.read_bytes() for p in scripts} == before
    else:
        command = bundled_config["clusters"]["cluster2"]["mpi_command"]
        assert command in Path("scf.sh").read_text()
    assert Path("unrelated.sh").read_text() == "$QE_PATH/pw.x\n"
    snapshot = {p: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()}
    header.run(args)
    assert {p: p.read_bytes() for p in snapshot} == snapshot


@pytest.mark.parametrize("flags", [("--no-header", "--no-mpi"), ("--no-header", "--header", "long")])
def test_conflicting_flags_do_not_write(parse_args, flags):
    Path("master.sh").write_text("unchanged\n")
    with pytest.raises(ValueError):
        header.run(parse_args("set", "cluster", "--cluster", "cluster2", *flags))
    assert Path("master.sh").read_text() == "unchanged\n"


def test_explicit_cluster_and_header(parse_args, monkeypatch):
    operation = Mock()
    detection = Mock(side_effect=AssertionError("Unexpected hostname detection"))
    monkeypatch.setattr(header, "apply_cluster", operation)
    monkeypatch.setattr(utils, "resolve_cluster", detection)
    header.run(parse_args("set", "cluster", "--cluster", "cluster2", "--header", "long"))
    operation.assert_called_once_with(cluster="cluster2", header=1, mpi=True)


def test_detected_cluster_and_interactive_header(parse_args, monkeypatch):
    operation = Mock()
    monkeypatch.setattr(utils, "resolve_cluster", lambda clusters: "cluster2")
    monkeypatch.setattr("dftcaddie.prompts.select", lambda *args, **kwargs: "small")
    monkeypatch.setattr(header, "apply_cluster", operation)
    header.run(parse_args("set", "cluster"))
    operation.assert_called_once_with(cluster="cluster2", header=2, mpi=True)


@pytest.mark.parametrize(
    "flags", [("--cluster", "missing"), ("--cluster", "local", "--header", "missing")]
)
def test_invalid_selection_does_not_edit(parse_args, flags):
    Path("master.sh").write_text("unchanged\n")
    with pytest.raises(SystemExit) as error:
        header.run(parse_args("set", "cluster", *flags))
    assert error.value.code == 1
    assert Path("master.sh").read_text() == "unchanged\n"


def test_header_replacement_preserves_custom_job_name(parse_args):
    old = '#!/bin/bash\n#SBATCH --job-name="silicon"\n#SBATCH --partition=obsolete\n# === DFTCADDIE SBATCH HEADER END ===\n'
    body = "#Actual JOBS\nbash scf.sh\n"
    Path("master.sh").write_text(old + body)
    args = parse_args("set", "cluster", "--cluster", "cluster2", "--header", "long", "--no-mpi")
    header.run(args)
    result = Path("master.sh").read_text()
    assert '#SBATCH --job-name="silicon"' in result


def test_missing_master(parse_args):
    with pytest.raises(FileNotFoundError):
        header.run(
            parse_args("set", "cluster", "--cluster", "local", "--header", "default", "--no-mpi")
        )
