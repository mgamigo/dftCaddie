"""Schema, resource, and library configuration validation."""

import pytest

from dftcaddie.checks.config import validate_config


@pytest.mark.parametrize(
    "change,location",
    [
        (
            lambda s: s["pseudopotentials"]["libraries"]["scalar"].update(
                path="/nonexistent/dftcaddie"
            ),
            ".path",
        ),
        (
            lambda s: s["pseudopotentials"]["libraries"]["scalar"].update(
                format="potcar"
            ),
            ".format",
        ),
        (
            lambda s: s["pseudopotentials"]["defaults"]["quantum_espresso"].update(
                scalar="paw"
            ),
            ".scalar",
        ),
        (
            lambda s: s["pseudopotentials"]["libraries"]["scalar"].update(
                overrides={"Si": "missing.UPF"}
            ),
            ".overrides.Si",
        ),
        (
            lambda s: s["suggested_pseudos"].append(
                {"libraries": ["paw"], "elements": {"Cs": "Cs/POTCAR"}}
            ),
            "suggested_pseudos[1].libraries",
        ),
        (
            lambda s: s["suggested_pseudos"][0].update(libraries=["unknown"]),
            "suggested_pseudos[0].libraries",
        ),
        (
            lambda s: s["suggested_pseudos"][0].update(elements={"Cs": ["Cs/POTCAR"]}),
            ".elements.Cs",
        ),
        (
            lambda s: s["suggested_pseudos"][0].update(elements={"Cs": "../POTCAR"}),
            ".elements.Cs",
        ),
        (
            lambda s: s["pseudopotentials"]["libraries"]["scalar"].update(
                cutoff_defaults={"ecutwfc": "3 meters"}
            ),
            ".cutoff_defaults.ecutwfc",
        ),
    ],
)
def test_invalid_library_settings_are_reported(
    settings, bundled_resources, change, location
):
    change(settings)
    issues = validate_config(settings, bundled_resources)
    assert any(
        i.level == "error" and i.location.endswith(location) for i in issues
    ), issues


def test_arbitrary_code_names_are_allowed(settings, bundled_resources):
    settings["pseudopotentials"]["libraries"]["scalar"]["supported_codes"].append(
        "new_code"
    )
    settings["pseudopotentials"]["defaults"]["new_code"] = {
        "scalar": "scalar",
        "soc": "scalar",
    }
    assert not validate_config(settings, bundled_resources)


def test_combined_code_format_is_checked(settings, bundled_resources):
    library = settings["pseudopotentials"]["libraries"]["paw"]
    library["supported_codes"].append("quantum_espresso/wannier90")
    issues = validate_config(settings, bundled_resources)
    assert any(
        i.location == "pseudopotentials.libraries.paw.format"
        and "quantum_espresso/wannier90 requires upf" in i.message
        for i in issues
    )


def test_bundled_config_resources_are_valid(bundled_config, bundled_resources):
    # External roots are user-specific; check bundled resources without inspection.
    for library in bundled_config["pseudopotentials"]["libraries"].values():
        library["path"] = str(bundled_resources)
    issues = validate_config(bundled_config, bundled_resources)
    assert not issues


def test_suggestions_can_be_shared_and_missing_matches_are_optional(
    settings, bundled_resources
):
    settings["suggested_pseudos"].append(
        {
            "libraries": ["scalar", "soc"],
            "elements": {"Si": "missing*"},
        }
    )
    assert not validate_config(settings, bundled_resources)
