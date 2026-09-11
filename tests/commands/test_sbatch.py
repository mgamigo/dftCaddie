from pathlib import Path
from unittest.mock import Mock

import pytest

from dftcaddie import utils
from dftcaddie.commands import sbatch


def test_explicit_cluster_and_header(parse_args, monkeypatch):
    operation = Mock()
    detection = Mock(side_effect=AssertionError("Unexpected hostname detection"))
    monkeypatch.setattr(sbatch, "apply_header", operation)
    monkeypatch.setattr(utils, "resolve_cluster", detection)
    sbatch.run(parse_args("sbatch", "--cluster", "cluster2", "--header", "long"))
    operation.assert_called_once_with(cluster="cluster2", header=1)


def test_detected_cluster_and_interactive_header(parse_args, monkeypatch):
    operation = Mock()
    monkeypatch.setattr(utils, "resolve_cluster", lambda clusters: "cluster2")
    monkeypatch.setattr("dftcaddie.prompts.select", lambda *args, **kwargs: "small")
    monkeypatch.setattr(sbatch, "apply_header", operation)
    sbatch.run(parse_args("sbatch"))
    operation.assert_called_once_with(cluster="cluster2", header=2)


@pytest.mark.parametrize(
    "flags", [("--cluster", "missing"), ("--cluster", "local", "--header", "missing")]
)
def test_invalid_selection_does_not_edit(parse_args, flags):
    Path("master.sh").write_text("unchanged\n")
    with pytest.raises(SystemExit) as error:
        sbatch.run(parse_args("sbatch", *flags))
    assert error.value.code == 1
    assert Path("master.sh").read_text() == "unchanged\n"


def test_header_replacement_preserves_custom_job_name(parse_args):
    old = '#!/bin/bash\n#SBATCH --job-name="silicon"\n#SBATCH --partition=obsolete\n# === DFTCADDIE SBATCH HEADER END ===\n'
    body = "#Actual JOBS\nbash scf.sh\n"
    Path("master.sh").write_text(old + body)
    args = parse_args("sbatch", "--cluster", "cluster2", "--header", "long")
    sbatch.run(args)
    result = Path("master.sh").read_text()
    assert '#SBATCH --job-name="silicon"' in result


def test_missing_master(parse_args):
    with pytest.raises(FileNotFoundError):
        sbatch.run(parse_args("sbatch", "--cluster", "local", "--header", "default"))
