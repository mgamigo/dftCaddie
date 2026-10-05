"""Read-only inspection of pseudopotential libraries."""

from copy import deepcopy
from pathlib import Path

from dftcaddie.checks.pseudos import check_pseudos


def test_inspection_does_not_modify_inputs(settings, bundled_resources, monkeypatch):
    from dftcaddie import config

    monkeypatch.setattr(
        config,
        "load_config",
        lambda: (_ for _ in ()).throw(AssertionError("cached settings used")),
    )
    original = deepcopy(settings)
    root = Path(settings["pseudopotentials"]["libraries"]["scalar"]["path"])
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    reports = check_pseudos(settings, bundled_resources)
    assert [report["files"] for report in reports] == [1, 1, 2]
    assert not any(report["issues"] for report in reports)
    assert reports[0]["metadata"]["type"] == ["USPP"]
    assert settings == original
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_inspection_reports_mismatched_element_and_ambiguity(
    settings, bundled_resources
):
    library = settings["pseudopotentials"]["libraries"]["scalar"]
    library["pattern"] = "{element}.scalar*"
    root = Path(library["path"])
    (root / "Si.scalar-extra.UPF").write_text('<PP_HEADER element="O"/>')
    report = check_pseudos(settings, bundled_resources)[0]
    assert any("Ambiguous" in issue for issue in report["issues"])
    assert any("expected element Si" in issue for issue in report["issues"])


def test_suggestions_can_be_shared_and_missing_matches_are_optional(
    settings, bundled_resources
):
    settings["suggested_pseudos"].append(
        {
            "libraries": ["scalar", "soc"],
            "elements": {"Si": "missing*"},
        }
    )
    assert not any(r["issues"] for r in check_pseudos(settings, bundled_resources))
