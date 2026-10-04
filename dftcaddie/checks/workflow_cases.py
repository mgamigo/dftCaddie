"""
Preparation scenarios and output assertions for workflow checks.

The isolated worker calls _run_case() with an empty case directory and shared
fixtures. These checks invoke the Python CLI, inspect generated files, and
compare repeated preparation; they never launch calculation executables.

Private functions and classes
-----------------------------
_require()
    Fail a case with an explanatory assertion message.
_snapshot()
    Capture current-directory file bytes for comparison.
_has_code_family()
    Recognize backend families, including combined code names.
_has_managed_workflow()
    Identify backends with structure and pseudopotential checks.
_CommandRunner
    Track the command or assertion stage for failure reporting.
_run_case()
    Execute one preparation scenario and return its result.
_check_automatic()
    Compare automatic preparation with equivalent staged commands.
_check_calc_output()
    Check templates, calculation detection, and master-script wiring.
_check_system_output()
    Check generated geometry, grids, and k-paths.
_check_pseudo_output()
    Check potential selection, cutoff values, and SOC settings.
_check_headers()
    Check header replacement preserves the job body.
_check_reconfiguration()
    Check changed settings, preserved notes, and repeatability.
"""

from math import ceil
import os
from pathlib import Path
from shlex import quote

from dftcaddie.checks.workflows import WorkflowResult


def _require(condition, message):
    """
    Raise an error when a workflow condition is not satisfied.

    Parameters
    ----------
    condition : bool
        Condition expected to be true.
    message : str
        Error message used when the condition is false.

    Raises
    ------
    ValueError
        If condition is false.
    """
    if not condition:
        raise ValueError(message)


def _snapshot():
    """
    Capture the file contents in the current working directory.

    Returns
    -------
    dict
        Mapping from filename to raw file bytes for regular files in cwd.
    """
    return {p.name: p.read_bytes() for p in Path.cwd().iterdir() if p.is_file()}


def _has_code_family(code, family):
    """
    Return whether a code name includes a backend family.

    Parameters
    ----------
    code : str
        Calculation backend from the configuration.
    family : str
        Backend family to search for.

    Returns
    -------
    bool
        True when the backend family name is contained in code.
    """
    return family in code


def _has_managed_workflow(code):
    """
    Return whether system and pseudo checks are implemented for any code family.

    Parameters
    ----------
    code : str
        Calculation backend from the configuration.

    Returns
    -------
    bool
        True for codes containing a backend family with structure, pseudo, and
        reconfiguration assertions.
    """
    return any(
        _has_code_family(code, family) for family in ("quantum_espresso", "vasp")
    )


class _CommandRunner:
    """Run preparation commands while tracking the current failure stage."""

    def __init__(self):
        self.stage = "fixtures"

    def __call__(self, *args):
        """Invoke caddie and raise on a nonzero exit status."""
        from dftcaddie import cli

        # Keep the command name available if dispatch raises before an assertion.
        self.stage = args[0]
        _require(cli.main(list(args)) == 0, f"Command failed: {args[0]}")


def _run_case(payload, root, fixtures):
    """
    Dispatch one scenario in a fresh directory and report its outcome.

    Parameters
    ----------
    payload : dict
        Selected case, scenario, label, and configuration.
    root : pathlib.Path
        Directory reserved for this case.
    fixtures : tuple
        Shared structure path, pseudo filenames, and POTCAR contents.

    Returns
    -------
    WorkflowResult
        Outcome including the command or assertion stage on failure.
    """
    run = _CommandRunner()
    scenario = payload["scenario"]
    try:
        from dftcaddie.calculation import get_calculation_definition

        data = payload["data"]
        kind, flavor, code = payload["case"]
        structure, _, _ = fixtures
        working = root / "calculation"
        working.mkdir(parents=True)
        os.chdir(working)

        # Explicit selectors avoid interactive recipe selection in the worker.
        flags = ["--kind", kind, "--code", code]
        if flavor is not None:
            flags += ["--flavor", flavor]
        definition = get_calculation_definition(data, kind, flavor)

        # Other backends support generic template/header checks, but we do not
        # know their structure or pseudopotential editing formats.
        if not _has_managed_workflow(code) and scenario != "staged":
            return WorkflowResult(
                payload["label"],
                True,
                scenario,
                f"Skipped code-specific workflow checks for {code}.",
                scenario,
            )

        if scenario in ("automatic", "auto"):
            _check_automatic(run, flags, structure, root, scenario)
        else:
            # Generic checks: every configured backend should copy templates,
            # resolve the calculation, wire scripts, and accept scheduler headers.
            run("calc", *flags)
            master = _check_calc_output(definition, kind, code)
            _check_headers(run, data, master)

            if not _has_managed_workflow(code):
                return WorkflowResult(
                    payload["label"],
                    True,
                    scenario,
                    "Generic preparation completed; code-specific checks skipped.",
                    scenario,
                )

            # Managed backend checks: these commands edit known input formats.
            run(
                "set",
                "system",
                str(structure),
                "--autokgrid",
                "--kppra",
                "64",
                "--kpath",
            )
            run.stage = "system output"
            _check_system_output(code, structure)

            run(
                "set",
                "pseudo",
                str(structure),
                "--configure",
                "--soc",
            )
            run.stage = "pseudo output"
            _check_pseudo_output(code, data, fixtures)

            # Start with the prepared SOC calculation, then change settings and
            # check that repeating the changes leaves the files unchanged.
            if scenario == "reconfiguration":
                _check_reconfiguration(run, code, data, fixtures)

        return WorkflowResult(
            payload["label"], True, scenario, "Preparation completed.", scenario
        )
    # Return a failed case rather than aborting the rest of the worker batch.
    except (Exception, SystemExit) as exc:
        return WorkflowResult(
            payload["label"], False, run.stage, f"{type(exc).__name__}: {exc}", scenario
        )


def _check_automatic(run, flags, structure, root, scenario):
    """
    Compare automatic preparation with the equivalent staged commands.

    Parameters
    ----------
    run : _CommandRunner
        Command executor and current failure stage.
    flags : list of str
        Calculation selection arguments.
    structure : pathlib.Path
        Shared silicon CIF.
    root : pathlib.Path
        Parent for the separate comparison directory.
    scenario : str
        automatic (pseudo configuration) or auto (full automatic preparation).
    """
    option = "--auto" if scenario == "auto" else "--pseudo"
    run("calc", *flags, "--structure", str(structure), option)
    # Compare all generated bytes against the equivalent sequence of set commands.
    automatic = _snapshot()
    (root / "staged").mkdir()
    os.chdir(root / "staged")
    run("calc", *flags)
    # --auto also configures grids and k-paths; --pseudo does not.
    extra = ["--autokgrid", "--kpath"] if scenario == "auto" else []
    run("set", "system", str(structure), "--pseudo", *extra)
    run.stage = "compare"
    _require(
        _snapshot() == automatic,
        "Automatic and staged preparation produced different files.",
    )


def _check_calc_output(definition, kind, code):
    """
    Check generated templates, calculation detection, and master script wiring.

    Parameters
    ----------
    definition : dict
        Selected calculation definition.
    kind, code : str
        Expected calculation kind and backend.

    Returns
    -------
    str
        Original master script for later job-body comparisons.
    """
    from dftcaddie import utils

    # Templates may live in subdirectories; their copies use basenames in cwd.
    for filename in definition["files"][code]:
        _require(
            Path(Path(filename).name).is_file(),
            f"Missing generated template: {filename}",
        )
    resolved_kind, _, resolved_code = utils.resolve_calculation_directory(Path.cwd())
    _require(
        (resolved_kind, resolved_code) == (kind, code),
        "Generated files resolve to a different calculation.",
    )
    master = Path("master.sh").read_text()
    _require("bash master.sh" not in master, "Master script invokes itself.")
    # Each child script is invoked once; master must never invoke itself.
    for filename in definition["files"][code]:
        name = Path(filename).name
        if name.endswith(".sh") and name != "master.sh":
            _require(
                master.count(f"bash {name}\n") == 1,
                f"Missing or duplicate script: {name}",
            )
    return master


def _check_system_output(code, structure):
    """
    Check the generated structure, k-grid, and high-symmetry k-path.

    Parameters
    ----------
    code : str
        Calculation backend.
    structure : pathlib.Path
        Reference silicon CIF.
    """
    if _has_code_family(code, "quantum_espresso"):
        text = Path("SYSTEM.INFO").read_text()
        # These values follow from the bundled eight-atom silicon fixture and
        # the small kppra=64 requested by the staged scenario.
        for expected in (
            "NAME='Si8'",
            "ATM_NUM=8\n",
            "ATM_TYPES=1\n",
            "KGRID='2 2 2'",
        ):
            _require(expected in text, f"Missing structure/grid setting: {expected}")
        path = Path.home() / ".config/dftcaddie/kpaths/quantum_espresso/SG227"
        _require(path.read_text().strip() in text, "Incorrect QE k-path.")
    if _has_code_family(code, "vasp"):
        import numpy as np
        from ase.io import read

        # Compare parsed geometry so harmless POSCAR formatting differences do not fail.
        actual, expected = read("POSCAR"), read(structure)
        _require(
            actual.get_chemical_symbols() == expected.get_chemical_symbols(),
            "POSCAR species differ.",
        )
        _require(np.allclose(actual.cell, expected.cell), "POSCAR lattice differs.")
        _require(
            np.allclose(actual.get_scaled_positions(), expected.get_scaled_positions()),
            "POSCAR positions differ.",
        )
        _require("2 2 2" in Path("KPOINTS.SCC").read_text(), "Incorrect VASP grid.")
        path = Path.home() / ".config/dftcaddie/kpaths/vasp/SG227"
        _require(
            Path("KPOINTS.BS").read_bytes() == path.read_bytes(),
            "Incorrect VASP k-path.",
        )


def _check_pseudo_output(code, data, fixtures):
    """
    Check pseudo selection, cutoff values, and enabled spin-orbit coupling.

    Parameters
    ----------
    code : str
        Calculation backend.
    data : dict
        Configuration containing the cutoff ratio.
    fixtures : tuple
        Shared structure path, pseudo filenames, and POTCAR contents.
    """
    _, names, potcar = fixtures
    # Known fixture cutoffs (QE 40/160 Ry and VASP 200 eV) make it possible
    # to check that the configured safety factor was actually applied.
    ratio = data["default_cutoff_ratio"]
    if _has_code_family(code, "quantum_espresso"):
        text = Path("SYSTEM.INFO").read_text()
        _require(text.count(names["soc"]) == 1, "Incorrect QE species.")
        directory = data["pseudopotentials"]["libraries"]["soc"]["path"]
        _require(
            f"PSEUDO_DIR={quote(directory)}\n" in text,
            "Incorrect QE pseudo directory.",
        )
        _require(
            f"CUTOFF={ceil(40 * ratio)}\n" in text
            and f"ECUTRHO={ceil(160 * ratio)}\n" in text,
            "Incorrect QE cutoffs.",
        )
    if _has_code_family(code, "vasp"):
        _require(Path("POTCAR").read_text() == potcar, "Incorrect POTCAR.")
        incars = list(Path.cwd().glob("INCAR*"))
        _require(incars, "No INCAR generated.")
        # Every generated INCAR variant must receive the same cutoff and SOC setting.
        for incar in incars:
            text = incar.read_text()
            _require(
                f"ENCUT = {int(200 * ratio)}" in text and "LSORBIT = TRUE" in text,
                f"Incorrect cutoff/SOC in {incar.name}.",
            )


def _check_headers(run, data, master):
    """
    Check every configured scheduler header while preserving the job body.

    Parameters
    ----------
    run : _CommandRunner
        Command executor and current failure stage.
    data : dict
        Configuration containing clusters and headers.
    master : str
        Master script captured after calculation creation.
    """
    # Scheduler edits may replace the preamble, but must preserve the job body.
    body = master[master.index("#Actual JOBS") :]
    # Cycle through all cluster/header combinations on the same script. This
    # catches headers accumulating instead of replacing the previous header.
    for cluster, entry in data["clusters"].items():
        for header in entry["headers"]:
            run(
                "set",
                "cluster",
                "--cluster",
                cluster,
                "--header",
                header["name"],
            )
            result = Path("master.sh").read_text()
            _require(
                result.endswith(body),
                "Header replacement changed the job body.",
            )
            _require(
                result.count("# === DFTCADDIE SBATCH HEADER END ===") == 1,
                "Duplicate SBATCH header boundary.",
            )


def _check_reconfiguration(run, code, data, fixtures):
    """
    Check changed settings, preserved notes, and repeatable reconfiguration.

    Parameters
    ----------
    run : _CommandRunner
        Command executor and current failure stage.
    code : str
        Calculation backend.
    data : dict
        Configuration containing the local SBATCH header.
    fixtures : tuple
        Shared structure path, pseudo filenames, and POTCAR contents.
    """
    structure, names, potcar = fixtures
    grid = Path(
        "SYSTEM.INFO" if _has_code_family(code, "quantum_espresso") else "KPOINTS.SCC"
    )
    # Save the old grid and add a user-owned file to check the boundaries of edits.
    old_grid = grid.read_bytes()
    Path("notes.txt").write_text("Keep my calculation notes.\n")

    def reconfigure():
        """
        Apply the second-pass system, pseudo, and header commands.
        """
        run(
            "set",
            "system",
            str(structure),
            "--autokgrid",
            "--kppra",
            "4096",
        )
        # Omitting --soc must undo the first preparation's SOC setting.
        run("set", "pseudo", str(structure), "--configure")
        run(
            "set",
            "cluster",
            "--cluster",
            "local",
            "--header",
            data["clusters"]["local"]["headers"][0]["name"],
        )

    reconfigure()
    run.stage = "reconfiguration output"
    _require(grid.read_bytes() != old_grid, "Grid did not change.")
    _require(
        Path("notes.txt").read_text() == "Keep my calculation notes.\n",
        "Unrelated notes changed.",
    )
    if _has_code_family(code, "quantum_espresso"):
        text = Path("SYSTEM.INFO").read_text()
        _require(
            names["scalar"] in text and names["soc"] not in text,
            "Pseudo selection was not replaced.",
        )
        scripts = [
            path.read_text()
            for path in Path.cwd().glob("*.sh")
            if "noncolin=" in path.read_text()
        ]
        _require(
            scripts
            and all(
                "noncolin=.false." in text and "lspinorb=.false." in text
                for text in scripts
            ),
            "SOC was not disabled.",
        )
    if _has_code_family(code, "vasp"):
        _require(
            Path("POTCAR").read_text() == potcar,
            "POTCAR changed unexpectedly.",
        )
        incars = list(Path.cwd().glob("INCAR*"))
        _require(
            incars and all("LSORBIT = FALSE" in path.read_text() for path in incars),
            "SOC was not disabled.",
        )
    # A second identical pass must not change anything, including user notes.
    before = _snapshot()
    reconfigure()
    run.stage = "repeat"
    _require(_snapshot() == before, "Repeating configuration changed files.")
