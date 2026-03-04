import sys


def test_importing_dftcaddie_does_not_eagerly_import_heavy_deps():
    """
    Guardrail: importing dftcaddie CLI/client code should not automatically
    pull heavy scientific stacks unless needed.

    Adjust the module list depending on what you consider "heavy".
    """
    heavy = {
        "numpy",
        "scipy",
        "matplotlib",
        "spglib",
        "ase",
        "yaiv",
    }

    # Ensure a clean-ish baseline for this test
    already = set(sys.modules)

    import dftcaddie  # noqa: F401

    loaded_now = set(sys.modules) - already

    # Any heavy modules loaded as a consequence of importing dftcaddie?
    offenders = sorted(m for m in loaded_now if m.split(".", 1)[0] in heavy)

    assert not offenders, (
        "Heavy deps imported at dftcaddie import time:\n"
        + "\n".join(f"- {m}" for m in offenders)
    )
