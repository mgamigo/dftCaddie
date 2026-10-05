"""Selection and metadata contracts independent of provider and calculation code."""

from pathlib import Path

import pytest

from dftcaddie.utils import get_pseudo_paths, get_upf_cutoffs, read_upf_pseudo_metadata


@pytest.fixture
def upf(tmp_path):
    def write(name="sample.UPF", **attrs):
        path = tmp_path / name
        attributes = {"element": "Si", **attrs}
        path.write_text(
            "<PP_HEADER " + " ".join(f'{k}="{v}"' for k, v in attributes.items()) + "/>"
        )
        return path

    return write


def test_metadata_preserves_standard_header_values(upf):
    path = upf(
        pseudo_type="USPP",
        functional="PBESOL",
        relativistic="full",
        has_so=".TRUE.",
        wfc_cutoff="4.1D+1",
        rho_cutoff="0.012",
    )
    assert read_upf_pseudo_metadata(path) == {
        "element": "Si",
        "type": "USPP",
        "exchange": "pbesol",
        "relativity": "full",
        "has_so": True,
        "ecutwfc": 41.0,
        "ecutrho": 0.012,
    }


def test_metadata_ignores_generator_text_and_missing_fields(upf):
    path = upf(wfc_cutoff="0")
    path.write_text(
        "<UPF><PP_INFO>unescaped & generator notes</PP_INFO>"
        + path.read_text()
        + "</UPF>"
    )
    metadata = read_upf_pseudo_metadata(path)
    assert metadata["element"] == "Si"
    assert all(value is None for key, value in metadata.items() if key != "element")


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("has_so", "maybe"),
        ("wfc_cutoff", "nan"),
        ("rho_cutoff", "-1"),
    ],
)
def test_bad_header_values_are_reported(upf, attribute, value):
    with pytest.raises(ValueError, match=attribute):
        read_upf_pseudo_metadata(upf(**{attribute: value}))


@pytest.mark.parametrize("text", ["no header", "<PP_HEADER>legacy header</PP_HEADER>"])
def test_unsupported_header_is_reported(tmp_path, text):
    path = tmp_path / "pseudo.UPF"
    path.write_text(text)
    with pytest.raises(ValueError, match="PP_HEADER"):
        read_upf_pseudo_metadata(path)


def test_selection_priorities_and_upf_type_filtering(tmp_path):
    names = [
        "Si.pbe-nl-rrkjus_psl.1.UPF",
        "Si.pbe-n-rrkjus_psl.1.UPF",
        "Si.pbe-nl-kjpaw_psl.1.UPF",
        "custom.UPF",
    ]
    for name in names:
        (tmp_path / name).touch()
    library = {
        "path": tmp_path,
        "format": "upf",
        "pattern": "{element}.*rrkjus*",
        "suggestions": {"Si": "Si.*-nl-*_psl.1.UPF"},
    }
    assert get_pseudo_paths(library, ["Si", "Si"]) == {"Si": tmp_path / names[0]}
    library["overrides"] = {"Si": "custom.UPF"}
    assert get_pseudo_paths(library, ["Si"])["Si"].name == "custom.UPF"
    library["overrides"]["Si"] = "absent.UPF"
    with pytest.raises(FileNotFoundError):
        get_pseudo_paths(library, ["Si"])
    library.pop("overrides")
    library["suggestions"]["Si"] = "missing*"
    with pytest.warns(UserWarning, match="first alphabetically"):
        assert get_pseudo_paths(library, ["Si"])["Si"].name == names[1]


def test_potcar_suggestions_and_separated_species_groups(tmp_path):
    for variant in ["Cs_sv", "Si"]:
        (tmp_path / variant).mkdir()
        (tmp_path / variant / "POTCAR").touch()
    library = {
        "path": tmp_path,
        "format": "potcar",
        "pattern": "{element}/POTCAR",
        "suggestions": {"Cs": "Cs_*/POTCAR"},
    }
    result = get_pseudo_paths(library, iter(["Cs", "Cs", "Si", "Cs"]))
    assert result == [
        tmp_path / variant / "POTCAR" for variant in ["Cs_sv", "Si", "Cs_sv"]
    ]


def test_upf_mapping_preserves_first_species_occurrence(tmp_path):
    for symbol in ["Si", "O"]:
        (tmp_path / f"{symbol}.UPF").touch()
    library = {"path": tmp_path, "format": "upf", "pattern": "{element}.UPF"}
    assert list(get_pseudo_paths(library, iter(["O", "Si", "O"]))) == ["O", "Si"]


def test_cutoffs_take_each_maximum_then_round_up(upf):
    paths = {
        "Si": upf("Si.UPF", wfc_cutoff="40.1", rho_cutoff="320"),
        "O": upf("O.UPF", wfc_cutoff="35", rho_cutoff="400.1"),
    }
    assert get_upf_cutoffs(paths, ratio=1.5) == (61, 601)


def test_cutoff_fallbacks_convert_units_without_becoming_thresholds(upf):
    from yaiv.defaults.config import ureg

    paths = {"Si": upf(wfc_cutoff="10", rho_cutoff="0")}
    with pytest.warns(UserWarning, match="ecutrho"):
        assert get_upf_cutoffs(
            paths,
            ratio=1,
            defaults={
                "ecutwfc": "80 Ry",
                "ecutrho": 20 * ureg.hartree,
            },
        ) == (10, 40)
    with pytest.warns(UserWarning, match="ecutrho"):
        assert get_upf_cutoffs(paths, ratio=1, defaults={"ecutrho": "20 hartree"}) == (
            10,
            40,
        )


def test_missing_cutoff_requires_explicit_fallback(upf):
    with pytest.raises(RuntimeError, match="ecutrho"):
        get_upf_cutoffs({"Si": upf(wfc_cutoff="40")})


@pytest.mark.parametrize("ratio", [0, -1, float("inf"), float("nan"), True])
def test_invalid_safety_factor(upf, ratio):
    with pytest.raises(ValueError, match="safety factor"):
        get_upf_cutoffs({"Si": upf()}, ratio=ratio)
