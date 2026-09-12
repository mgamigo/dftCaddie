"""Shell completion through the installed CLI without command execution."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


@pytest.fixture
def complete(tmp_path, bundled_config):
    """Invoke argcomplete's shell protocol with isolated user configuration."""
    config = tmp_path / ".config/dftcaddie/config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(yaml.safe_dump(bundled_config, sort_keys=False))
    output = tmp_path / "completions"
    working = tmp_path / "calculation"
    working.mkdir()

    def run(line):
        """Collect completion candidates and verify no preparation occurred."""
        output.write_text("")
        env = {
            **os.environ,
            "HOME": str(tmp_path),
            "_ARGCOMPLETE": "1",
            "_ARGCOMPLETE_IFS": "\n",
            "_ARGCOMPLETE_SUPPRESS_SPACE": "1",
            "_ARGCOMPLETE_STDOUT_FILENAME": str(output),
            "COMP_LINE": line,
            "COMP_POINT": str(len(line)),
            "COMP_TYPE": "63",
        }
        before = {p.name: p.read_bytes() for p in working.iterdir()}
        result = subprocess.run(
            [str(Path(sys.executable).parent / "caddie")],
            cwd=working,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert not result.stdout
        assert {p.name: p.read_bytes() for p in working.iterdir()} == before
        return output.read_text().splitlines()

    return run, config, working


@pytest.mark.parametrize(
    "line,expected",
    [
        ("caddie ", {"calc", "set", "config"}),
        ("caddie set ", {"system", "pseudo", "header"}),
        ("caddie calc -", {"-s", "--kind", "--flavor", "--code"}),
        ("caddie calc --", {"--kind", "--flavor", "--code"}),
        ("caddie config ", {"init", "check"}),
        ("caddie calc --kind ", {"bands", "relax", "phonons"}),
        ("caddie calc --kind relax --flavor ", {"fixed_cell", "variable_cell"}),
        ("caddie calc --kind phonons --code ", {"quantum_espresso"}),
        (
            "caddie set header --cluster cluster2 --header ",
            {"default", "long", "small"},
        ),
        ("caddie set header --cluster ", {"local", "cluster1", "cluster2"}),
    ],
)
def test_shell_candidates(complete, line, expected):
    run, _, _ = complete
    candidates = set(run(line))
    assert expected <= candidates
    if line.endswith("--code "):
        assert "vasp" not in candidates


@pytest.mark.parametrize("line", ["caddie ", "caddie calc ", "caddie set system "])
def test_flags_require_dash_prefix(complete, line):
    run, _, _ = complete
    assert not any(candidate.startswith("-") for candidate in run(line))


def test_prefix_and_paths(complete):
    run, _, working = complete
    assert run("caddie calc --kind ph") == ["phonons"]
    (working / "Si.cif").write_text("structure fixture")
    assert "Si.cif" in run("caddie set system Si")
    assert "Si.cif" in run("caddie calc --structure Si")


def test_configuration_changes_are_seen_on_next_completion(complete):
    run, path, _ = complete
    assert "new_kind" not in run("caddie calc --kind ")
    data = yaml.safe_load(path.read_text())
    data["calculations"]["new_kind"] = {
        "name": "New kind",
        "files": {"new_code": ["input"]},
    }
    path.write_text(yaml.safe_dump(data))
    assert "new_kind" in run("caddie calc --kind ")
    assert run("caddie calc --kind new_kind --code ") == ["new_code"]


def test_commands_and_flags_follow_parser(monkeypatch):
    from argcomplete import CompletionFinder
    from dftcaddie.cli import _build_parser

    parser = _build_parser()
    parser.add_argument("--new-option", action="store_true")
    finder = CompletionFinder(parser, always_complete_options=False)
    assert finder.rl_complete("caddie --new", 0).strip() == "caddie --new-option"
