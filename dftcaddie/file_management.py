"""
dftCaddie | dftcaddie.file_management
=====================================

File and template management utilities for dftCaddie.

This module provides the low-level routines used to prepare and modify
calculation input files in the working directory. It includes utilities to:

- copy template input files for a selected calculation/code,
- edit template files in-place (insert/remove/replace line blocks),
- configure cluster and script settings (SBATCH preambles, MPI command),
- apply calculation options (SOC, cell relaxation),
- write structure-dependent data (lattice, positions),
- set k-point grids and high-symmetry paths,
- resolve and apply pseudopotentials and cutoffs.

Functions
---------
copy_input_files()
    Copy template input files for a given calculation into the working directory.
populate_master_script()
    Insert sub-script execution lines into ``master.sh``.
set_master_preamble()
    Prepend a cluster-specific SBATCH header to ``master.sh``.
change_mpi_command()
    Replace MPI prefixes in scripts with the cluster-specific MPI command.
set_spin_orbit_coupling()
    Enable or disable spin-orbit coupling settings in input scripts.
set_cell_relaxation()
    Configure ionic vs variable-cell relaxation.
configure_input_files()
    Apply calculation-option-dependent edits to input scripts.
set_crystal_structure()
    Write lattice and fractional atomic positions.
set_auto_kgrid()
    Compute and write an automatic k-point grid.
set_high_symmetry_path()
    Insert a high-symmetry k-path.
get_qe_pseudo_paths()
    Resolve pseudopotential path.
write_pseudos_to_system_info()
    Write ATOMIC_SPECIES and EXCHANGE into ``SYSTEM.INFO`` (QE).
configure_qe_cutoffs_from_pseudos()
    Read suggested cutoffs from pseudo headers and update ``SYSTEM.INFO`` (QE).

Private Utilities
-----------------
_replace_setting()
    Replace a single setting line in a file while preserving indentation.
_insert_lines()
    Insert a block of lines after a matching line in a file.
_remove_lines()
    Remove a block of lines between two matching markers.
"""

import logging
from types import SimpleNamespace
from typing import Iterable
import os

from dftcaddie.config import (
    calculations,
    clusters,
    mpi_executables,
    suggested_qe_pseudos,
)

log = logging.getLogger(__name__)

__all__ = [
    # File copying / orchestration
    "copy_input_files",
    "populate_master_script",
    "set_master_preamble",
    "change_mpi_command",
    # Calculation options
    "set_spin_orbit_coupling",
    "set_cell_relaxation",
    "configure_input_files",
    # Structure & setup
    "set_crystal_structure",
    "set_auto_kgrid",
    "set_high_symmetry_path",
    # Pseudopotentials (QE)
    "get_qe_pseudo_paths",
    "write_pseudos_to_system_info",
    "configure_qe_cutoffs_from_pseudos",
]


def _replace_setting(file_path: str, partial_match: str, new_line: str) -> None:
    """
    Replace the first line starting with a specific substring, ignoring
    leading spaces, with a new line preserving the original line's
    indentation.

    Parameters
    ----------
    file_path : str
        Path to the file to be modified.
    partial_match : str
        The substring to match at the start of lines. Only lines starting
        with this substring will be replaced.
    new_line : str
        The new line content to use as a replacement, including preserved
        indentation.
    """

    # Read the file's contents
    with open(file_path, "r") as file:
        lines = file.readlines()

    # Replace the desired line with a partial match
    replaced = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith(partial_match):
            leading_spaces = len(line) - len(line.lstrip(" "))
            lines[i] = (" " * leading_spaces) + new_line + "\n"
            replaced = True
            log.debug(
                "Replaced line starting with '%s' in '%s'",
                partial_match,
                file_path,
            )
            break

    if not replaced:
        log.debug(
            "No line starting with '%s' found in '%s'",
            partial_match,
            file_path,
        )

    # Write the modified contents back to the file
    with open(file_path, "w") as file:
        file.writelines(lines)


def _insert_lines(
    file_path: str, lines_to_insert: list[str], match_string: str
) -> None:
    """
    Inserts the specified lines into the file right after a line
    containing the specified match_string.

    Parameters
    ----------
    file_path : str
        Path to the file in which lines are to be inserted.
    lines_to_insert : list[str]
        List of strings representing lines to insert.
    match_string : str
        String to match in the file to determine the insertion point.
    """
    log.debug(
        "Inserting lines into '%s' after match '%s'",
        file_path,
        match_string,
    )

    with open(file_path, "r") as file:
        lines = file.readlines()

    # Initialize index to insert after
    insert_index = None
    for index, line in enumerate(lines):
        if match_string in line:
            insert_index = index + 1
            break

    # Check if the match_string was found
    if insert_index is None:
        log.error(
            "No line containing '%s' found in '%s'",
            match_string,
            file_path,
        )
        return

    # Insert specified lines into the list
    updated_lines = lines[:insert_index] + lines_to_insert + lines[insert_index:]

    # Write the updated lines back into the file
    with open(file_path, "w") as file:
        file.writelines(updated_lines)

    log.debug(
        "Inserted %d lines into '%s'",
        len(lines_to_insert),
        file_path,
    )


def _remove_lines(
    file_path: str,
    starting_partial_match: str,
    finishing_partial_match: str,
) -> None:
    """
    Remove lines between those containing the start and finish partial matches, excluded.

    Parameters
    ----------
    file_path : str
        Path to the file to be modified.
    starting_partial_match : str
        The substring indicating the start of lines to be removed.
    finishing_partial_match : str
        The substring indicating the end of lines to be removed.
    """
    log.debug(
        "Removing lines in '%s' between '%s' and '%s'",
        file_path,
        starting_partial_match,
        finishing_partial_match,
    )

    with open(file_path, "r") as file:
        lines = file.readlines()

    # Find indices for start and end of removal
    start_index = None
    end_index = None

    for i, line in enumerate(lines):
        if starting_partial_match in line:
            start_index = i
        elif finishing_partial_match in line and start_index is not None:
            end_index = i
            break

    if start_index is None or end_index is None:
        log.error(
            "Could not find start '%s' or finish '%s' in '%s'",
            starting_partial_match,
            finishing_partial_match,
            file_path,
        )
        return

    del lines[start_index + 1 : end_index]

    with open(file_path, "w") as file:
        file.writelines(lines)

    log.debug(
        "Removed lines between '%s' and '%s' in '%s'",
        starting_partial_match,
        finishing_partial_match,
        file_path,
    )


def copy_input_files(calculation: SimpleNamespace) -> list[str]:
    """
    Copies specified input files for a given DFT code into the current
    working directory. Prompts users to confirm overwriting if files
    already exist at the destination.

    Parameters
    ----------
    calculation : SimpleNamespace
        A Namespace with all the relevant details.

    Returns
    -------
    files : list[str]
        List of files that relevant for the calculation.

    Notes
    -----
    - User confirmation is required if files exist at the destination.
    """
    import shutil

    # Resolve needed files.
    log.info("\nWriting input files:")
    files_to_copy = calculations[calculation.kind]["files"][calculation.code]
    if not os.path.exists("SYSTEM.INFO") and calculation.code == "quantum_espresso":
        files_to_copy.append("SYSTEM.INFO")
    files_to_copy.append("master.sh")

    # Copy the files
    source_dir = os.path.join(os.path.dirname(__file__), "data", calculation.code)
    copied = []
    for file_name in files_to_copy:
        source_path = os.path.join(source_dir, file_name)
        destination_path = os.path.join(os.getcwd(), file_name)

        if not os.path.exists(source_path):
            log.error(
                "Input file '%s' does not exist in the library: %s",
                file_name,
                source_path,
            )
            continue

        if os.path.exists(destination_path) and not calculation.overwrite:
            confirmation = input(
                f"The file '{file_name}' already exists. Do you want to overwrite it? (yes/no): "
            )
            if confirmation.strip().lower() not in ("yes", "y"):
                log.info("Skipped overwriting '%s'", file_name)
                continue

        shutil.copy(source_path, destination_path)
        copied.append(file_name)
        log.info("Copied '%s'", file_name)

    return files_to_copy


def populate_master_script(
    master_script_path: str, sub_scripts: list[str]
) -> list[str]:
    """
    Integrates sub-scripts into the master.sh script, modifying its content
    to include references or execution commands for the specified scripts.

    Parameters
    ----------
    sub_scripts : list[str]
        A list of filenames representing sub-scripts to integrate.
    master_script_path : str
        Path to the master.sh script to be modified or populated.

    Returns
    -------
    list[str]
        List of scripts added to the master.sh script.

    Notes
    -----
    - It will ignore all files that are not `.sh` files.
    """
    log.debug("Populating master script: %s", master_script_path)

    # Remove master script itself and non-.sh files
    master_name = os.path.basename(master_script_path)
    if master_name in sub_scripts:
        sub_scripts.remove(master_name)

    # Remove non-valid scripts
    sub_scripts = [script for script in sub_scripts if script.endswith(".sh")]

    log.debug("Sub-scripts to add: %s", sub_scripts)

    # Prepare lines to append
    if len(sub_scripts) > 0:
        script_lines = [f"bash {script}\n" for script in sub_scripts]
        _insert_lines(master_script_path, script_lines, "#Actual JOBS")
        log.info(
            "Added %d sub-scripts to '%s'",
            len(sub_scripts),
            master_script_path,
        )
    else:
        log.info("No sub-scripts to add to '%s'", master_script_path)

    return sub_scripts


def remove_master_preamble(master_script_path: str) -> None:
    """
    Removes cluster-specific preamble from a master script file.

    Parameters
    ----------
    master_script_path : str
        Path to the master script file to be updated.
    """
    log.info(
        "Removing cluster preamble from '%s'",
        master_script_path,
    )
    _remove_lines(
        master_script_path, "bin/bash", "# === DFTCADDIE SBATCH HEADER END ==="
    )


def set_master_preamble(master_script_path: str, cluster: str, header: int = 0) -> None:
    """
    Prepends cluster-specific preamble to a master script file.

    This function reads a cluster-specific header from a file and inserts
    it at the beginning of a master script, updating the script to reflect
    the target cluster’s setup requirements.

    Parameters
    ----------
    master_script_path : str
        Path to the master script file to be updated.
    cluster : str
        The name of the cluster whose preamble should be added to the master
        script.
    header : int
        Index of the header to be used for the particular cluster.
    """
    header_name = clusters[cluster]["headers"][header]["name"]
    log.info(
        "Adding cluster preamble for '%s/%s' to '%s'",
        cluster,
        header_name,
        master_script_path,
    )

    source_dir = os.path.join(os.path.dirname(__file__), "data", "sbatch_headers")
    header_file = clusters[cluster]["headers"][header]["file"]
    file_path = os.path.join(source_dir, header_file)

    log.debug("Using preamble file: %s", file_path)

    with open(file_path, "r") as file:
        preamble = file.readlines()

    _insert_lines(master_script_path, preamble, match_string="bin/bash")

    log.info(
        "Successfully added header '%s/%s' to '%s'",
        cluster,
        header_name,
        master_script_path,
    )


def change_mpi_command(file_path: str | list, cluster: str) -> None:
    """
    Modifies a script by replacing existing MPI commands with a cluster-specific command.

    This function scans through the specified file, identifies lines containing MPI executables,
    removes existing MPI commands, and prepends the cluster-specific MPI command. If modifications
    are made, the file is updated accordingly.

    Parameters
    ----------
    file_path : str | list
        Path (or list of paths) to the script file that requires MPI command modification.
    cluster : str
        The name of the cluster whose MPI command should be used in the script.
    """
    log.info("\nChanging mpi commands:")
    mpi_command = clusters[cluster]["mpi_command"]
    commands = {clusters[key]["mpi_command"] for key in clusters}
    commands = sorted(commands, key=len, reverse=True)

    if not isinstance(file_path, list):
        file_path = [file_path]

    for file in file_path:
        with open(file, "r") as f:
            lines = f.readlines()

        changes = False

        for i, line in enumerate(lines):
            for exe in mpi_executables:
                if exe in line:
                    changes = True
                    for c in commands:
                        if c in line:
                            line = line.replace(c, "")
                            log.debug("Removed existing MPI command '%s'", c)

                    lines[i] = f"{mpi_command} {line}"

        if not changes:
            log.info("No MPI commands found in '%s'", file)
            return

        with open(file, "w") as f:
            f.writelines(lines)

        log.info(
            "Applied MPI command '%s' to '%s'",
            mpi_command,
            file,
        )


def set_spin_orbit_coupling(kind: str, code: str, soc: bool) -> None:
    """
    Enable or disable spin-orbit coupling settings in input scripts.

    For Quantum ESPRESSO calculations, this updates the ``noncolin`` and
    ``lspinorb`` flags in the relevant ``.sh`` scripts associated with the
    selected calculation kind.

    Parameters
    ----------
    kind : str
        Calculation kind key (e.g., ``"bands"``, ``"relax"``) used to select
        which template scripts are modified.
    code : str
        DFT code identifier. Currently only ``"quantum_espresso"`` is supported.
    soc : bool
        If True, enable SOC (set ``noncolin=.true.`` and ``lspinorb=.true.``).
        If False, disable SOC.
    """
    files = calculations[kind]["files"][code]

    if code == "quantum_espresso":

        scripts = [file for file in files if file.endswith(".sh")]
        log.info("\nConfiguring for SOC : %s", soc)

        for script in scripts:
            if soc:
                _replace_setting(script, "noncolin=", "noncolin=.true.")
                _replace_setting(script, "lspinorb=", "lspinorb=.true.")
            else:
                _replace_setting(script, "noncolin=", "noncolin=.false.")
                _replace_setting(script, "lspinorb=", "lspinorb=.false.")


def set_cell_relaxation(code: str, cell_relaxation: bool) -> None:
    """
    Configure ionic vs variable-cell relaxation for Quantum ESPRESSO.

    This edits ``relax.sh`` to use either ``calculation='vc-relax'`` (variable
    cell) or ``calculation='relax'`` (ions only).

    Parameters
    ----------
    code : str
        DFT code identifier. Currently only ``"quantum_espresso"`` is supported.
    cell_relaxation : bool
        If True, set variable-cell relaxation (``vc-relax``). If False, set
        ionic relaxation only (``relax``).
    """
    log.info("\nConfiguring for cell_relaxation : %s", cell_relaxation)
    if code == "quantum_espresso":
        if cell_relaxation:
            _replace_setting("relax.sh", "calculation=", "calculation='vc-relax'")
        else:
            _replace_setting("relax.sh", "calculation=", "calculation='relax'")


def configure_input_files(calculation: SimpleNamespace) -> None:
    """
    Apply calculation-dependent configuration edits to input files.

    Parameters
    ----------
    calculation : SimpleNamespace
        Calculation options container.
    """
    options = set(calculation.__dict__.keys())
    log.info("\nConfiguring scripts according to options:")

    # Spin-orbit coupling
    if "soc" in options:
        set_spin_orbit_coupling(
            kind=calculation.kind, code=calculation.code, soc=calculation.soc
        )

    # Cell relaxation
    if calculation.kind == "relax":
        set_cell_relaxation(
            code=calculation.code, cell_relaxation=calculation.cell_relaxation
        )

    log.info("\nFile configuration completed")


def set_crystal_structure(structure: SimpleNamespace, code: str) -> None:
    """
    Write structure-dependent quantities into input templates.

    For Quantum ESPRESSO, this function updates ``SYSTEM.INFO`` with the
    system name, number of atoms, number of atomic types, fractional atomic
    positions, and lattice vectors.

    Parameters
    ----------
    structure : SimpleNamespace
        Structure container with at least the attributes ``formula``,
        ``lattice`` (3x3), ``positions`` (Nx3 fractional), and ``symbols`` (N).
    code : str
        DFT code identifier.
    """
    if code != "quantum_espresso":
        log.debug("set_crystal_structure skipped (code=%s)", code)
        return

    formula = structure.formula
    lattice = structure.lattice
    positions = structure.positions
    symbols = structure.symbols

    nat = len(positions)
    ntyp = len(set(symbols))

    log.info(
        "\nUpdating crystal structure in SYSTEM.INFO (NAME=%s, NAT=%d, NTYP=%d)",
        formula,
        nat,
        ntyp,
    )

    _replace_setting("SYSTEM.INFO", "NAME='NoName'", f"NAME='{formula}'")
    _replace_setting("SYSTEM.INFO", "ATM_NUM=", f"ATM_NUM={nat}")
    _replace_setting("SYSTEM.INFO", "ATM_TYPES=", f"ATM_TYPES={ntyp}")

    # Atomic positions (fractional)
    log.debug("Writing %d atomic positions", nat)
    _remove_lines("SYSTEM.INFO", "ATOMIC_CRYST_POSITIONS=", "EOL")
    pos_lines = [
        f"{s:<2} {x:14.9f} {y:14.9f} {z:14.9f}\n"
        for s, (x, y, z) in zip(symbols, positions)
    ]
    _insert_lines("SYSTEM.INFO", pos_lines, "ATOMIC_CRYST_POSITIONS=")

    # Lattice vectors
    log.debug("Writing lattice vectors")
    _remove_lines("SYSTEM.INFO", "LATTICE=", "EOL")
    lat_lines = [f"{x:14.9f} {y:14.9f} {z:14.9f}\n" for x, y, z in lattice]
    _insert_lines("SYSTEM.INFO", lat_lines, "LATTICE=")


def get_qe_pseudo_paths(
    symbols: Iterable[str],
    exchange: str = "pbe",
    kind: str = "kjpaw",
    relativistic: bool = False,
) -> list[str]:
    """
    Resolve Quantum ESPRESSO pseudopotential file paths from PSLibrary.

    Parameters
    ----------
    symbols : Iterable[str]
        Chemical symbols present in the structure (e.g., ``["Si", "O"]``).
    exchange : str, optional
        Exchange/correlation label used to locate pseudos (e.g., ``"pbe"``),
        by default "pbe".
    kind : str, optional
        Pseudopotential kind/wildcard (e.g., ``"kjpaw"``, ``"us"``),
        by default "kjpaw".
    relativistic : bool, optional
        If True, use the relativistic exchange folder (prefix ``"rel-"``),
        by default False.

    Returns
    -------
    pseudos : list[str]
        Absolute pseudo paths.

    Raises
    ------
    EnvironmentError
        If ``PSLIBRARY`` is not set.
    FileNotFoundError
        If no pseudopotential is found for a symbol.
    RuntimeError
        If multiple candidates are found for a symbol.
    """
    from glob import glob
    from dftcaddie.config import resolve_pslibrary
    from pathlib import Path

    symbols = set(symbols)

    ps_library = resolve_pslibrary()

    exchange_folder = f"rel-{exchange}" if relativistic else exchange
    source_path = os.path.join(ps_library, exchange_folder, "PSEUDOPOTENTIALS")

    log.info(
        "\nResolving QE pseudos (exchange=%s, kind=%s, relativistic=%s) from %s",
        exchange,
        kind,
        relativistic,
        source_path,
    )

    pseudos = []
    for sym in symbols:
        target = suggested_qe_pseudos[sym]
        target = target.replace("$fct", exchange_folder).replace("*", kind)
        target = ".".join(target.split(".")[:2])
        matches = glob(f"{source_path}/{target}*")

        if len(matches) == 1:
            pseudos.append(matches[0])
            log.debug("Selected pseudo for %s: %s", sym, os.path.basename(matches[0]))
        elif len(matches) == 0:
            raise FileNotFoundError(
                f"No pseudopotential found for {sym!r} under {source_path!r} with pattern {target!r}."
            )
        else:
            raise RuntimeError(
                f"Multiple pseudopotentials found for {sym!r}: {matches}. "
                "Please refine your pattern or choose manually."
            )

    return pseudos


def write_pseudos_to_system_info(
    system_info_path: str,
    pseudos: list[str],
) -> None:
    """
    Update ``SYSTEM.INFO`` with ATOMIC_SPECIES and EXCHANGE for Quantum ESPRESSO.

    Parameters
    ----------
    system_info_path : str
        Path to the ``SYSTEM.INFO`` file to edit.
    pseudos : list[str]
        Pseudopotential paths aligned with ``symbols`` inferred from filenames.
    """
    from ase.data import atomic_numbers, atomic_masses

    symbols = [os.path.basename(p).split(".")[0] for p in pseudos]
    masses = [atomic_masses[atomic_numbers[sym]] for sym in symbols]
    exchange_folder = pseudos[0]

    lines = [
        f"{s:<2} {m:11.6f}   {os.path.basename(p)}\n"
        for s, m, p in zip(symbols, masses, pseudos)
    ]

    log.info("\nUpdating %s: ATOMIC_SPECIES and EXCHANGE", system_info_path)

    _remove_lines(system_info_path, "ATOMIC_SPECIES=", "EOL")
    _insert_lines(system_info_path, lines, "ATOMIC_SPECIES=")
    _replace_setting(
        system_info_path, "EXCHANGE=", f"EXCHANGE='{exchange_folder.split('/')[-3]}'"
    )


def configure_qe_cutoffs_from_pseudos(
    system_info_path: str,
    pseudos: list[str],
    ratio: float = 1.5,
) -> tuple[int, int]:
    """
    Read suggested cutoffs from QE pseudopotential headers and update ``SYSTEM.INFO``.

    Parameters
    ----------
    system_info_path : str
        Path to the ``SYSTEM.INFO`` file to edit.
    pseudos : list[str]
        Pseudopotential file paths to read.
    ratio : float, optional
        Safety factor applied to the maximum suggested values, by default 1.5.

    Returns
    -------
    cutoff : int
        Wavefunction cutoff used (after applying ``ratio``).
    ecutrho : int
        Charge density cutoff used (after applying ``ratio``).

    Raises
    ------
    RuntimeError
        If suggested values cannot be read for all pseudos.
    """
    import numpy as np

    log.info("\nConfiguring cutoffs from pseudo headers (ratio=%s)", ratio)

    cutoff_vals: list[float] = []
    ecutrho_vals: list[float] = []

    for pseudo in pseudos:
        with open(pseudo, "r") as f:
            for line in f:
                if "Suggested minimum cutoff for wavefunctions" in line:
                    cutoff_vals.append(float(line.split()[-2]))
                elif "Suggested minimum cutoff for charge density:" in line:
                    ecutrho_vals.append(float(line.split()[-2]))

    if len(cutoff_vals) != len(pseudos) or len(ecutrho_vals) != len(pseudos):
        raise RuntimeError(
            "Could not read suggested cutoff/ecutrho values for all pseudos."
        )

    cutoff = int(np.max(cutoff_vals) * ratio)
    ecutrho = int(np.max(ecutrho_vals) * ratio)

    log.info(
        "Setting CUTOFF=%d and ECUTRHO=%d in %s", cutoff, ecutrho, system_info_path
    )

    _replace_setting(system_info_path, "CUTOFF=", f"CUTOFF={cutoff}")
    _replace_setting(system_info_path, "ECUTRHO=", f"ECUTRHO={ecutrho}")

    return cutoff, ecutrho


def set_auto_kgrid(structure: SimpleNamespace, code: str, kppra: int = 9000) -> None:
    """
    Set an automatic k-point grid in ``SYSTEM.INFO``.

    This computes a Monkhorst-Pack-like k-grid from the structure and writes it
    to the ``KGRID=`` entry in ``SYSTEM.INFO``.

    Parameters
    ----------
    structure : SimpleNamespace
        Structure container. Must provide lattice/cell information and the
        number of atoms. The exact required fields depend on ``auto_kgrid``.
    code : str
        DFT code identifier. Currently only ``"quantum_espresso"`` is supported.
    kppra : int, optional
        Target number of k-points per reciprocal atom, by default 9000.
    """
    from yaiv.utils import auto_kgrid

    lattice = structure.lattice
    n_atoms = len(structure.positions)

    log.info("\nComputing automatic k-grid (kppra=%d, n_atoms=%d)", kppra, n_atoms)

    if code != "quantum_espresso":
        log.debug("set_auto_kgrid skipped (code=%s)", code)
        return

    kgrid = auto_kgrid(lattice, n_atoms=n_atoms, kppra=kppra)
    kgrid_str = " ".join(map(str, kgrid))

    log.info("Setting KGRID='%s' in SYSTEM.INFO", kgrid_str)
    _replace_setting("SYSTEM.INFO", "KGRID=", f"KGRID='{kgrid_str}'")


def set_high_symmetry_path(structure: SimpleNamespace, code: str) -> None:
    """
    Set the high-symmetry k-path in ``SYSTEM.INFO`` based on space group.

    For Quantum ESPRESSO, this reads a template k-path file from the library
    (keyed by the structure space group) and inserts it under ``QE_CRYST_PATH=``.

    Parameters
    ----------
    structure : SimpleNamespace
        Structure container. Must define ``space_group`` (int).
    code : str
        DFT code identifier. Currently only ``"quantum_espresso"`` is supported.

    Raises
    ------
    FileNotFoundError
        If the k-path template for the given space group is not found.
    """
    log.info(
        "\nSetting high-symmetry path for space group %s in SYSTEM.INFO",
        structure.space_group,
    )

    if code != "quantum_espresso":
        log.debug("set_high_symmetry_path skipped (code=%s)", code)
        return

    source_dir = os.path.join(os.path.dirname(__file__), "data", "kpaths", code)
    path_file = os.path.join(source_dir, f"SG{structure.space_group}")

    log.debug("Reading k-path template: %s", path_file)
    with open(path_file, "r") as file:
        lines = file.readlines()
    _remove_lines("SYSTEM.INFO", "QE_CRYST_PATH=", "EOL")
    _insert_lines("SYSTEM.INFO", lines, "QE_CRYST_PATH=")
