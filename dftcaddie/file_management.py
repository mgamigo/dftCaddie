"""
dftCaddie | dftcaddie.file_management
=====================================

This module provides functionality for managing and copying input files
necessary for DFT calculations. It includes utilities to handle various
file operations, ensuring users can prepare their calculation directories
efficiently.

Functions
---------
copy_input_files(...)
    Copy necessary input files for specified DFT codes to the current
    working directory, with options for overwriting existing files.
"""

import os
import shutil
import glob
from types import SimpleNamespace

import numpy as np
import spglib as spg
from ase.data import atomic_numbers, atomic_masses
from yaiv.cell import Cell
from yaiv.utils import auto_kgrid

from dftcaddie.config import (
    cases,
    clusters,
    executables,
    pseudopotentials,
    suggested_qe_pseudos,
)

_all__ = [
    "copy_input_files",
]


def _replace_setting(file_path: str, partial_match: str, new_line: str):
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
    for i, line in enumerate(lines):
        if line.lstrip().startswith(partial_match):
            leading_spaces = len(line) - len(line.lstrip(" "))
            lines[i] = (" " * leading_spaces) + new_line + "\n"  # Preserve indentation
            break  # Stop after the replacement

    # Write the modified contents back to the file
    with open(file_path, "w") as file:
        file.writelines(lines)


def _insert_lines(file_path: str, lines_to_insert: list[str], match_string: str):
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
    with open(file_path, "r") as file:
        lines = file.readlines()

    # Initialize index to insert after
    insert_index = None

    # Find the first line that contains the match_string
    for index, line in enumerate(lines):
        if match_string in line:
            insert_index = index + 1
            break

    # Check if the match_string was found
    if insert_index is None:
        print(f"Error: No line containing '{match_string}' was found in {file_path}.")
        return

    # Insert specified lines into the list
    updated_lines = lines[:insert_index] + lines_to_insert + lines[insert_index:]

    # Write the updated lines back into the file
    with open(file_path, "w") as file:
        file.writelines(updated_lines)


def _remove_lines(
    file_path: str, starting_partial_match: str, finishing_partial_match: str
):
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
    # Read the file's contents
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
            break  # Stop after finding the first finish match following the start match

    # Ensure both start and end indices are found
    if start_index is not None and end_index is not None:
        # Remove lines between start_index and end_index inclusive
        del lines[start_index + 1 : end_index]
    else:
        # Print error message if matches are not found correctly
        print(
            f"Error: Could not find "
            f"start '{starting_partial_match}' or finish '{finishing_partial_match}' in '{file_path}'."
        )

    # Write the modified contents back to the file
    with open(file_path, "w") as file:
        file.writelines(lines)


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
        List of files that were copied for the calculation.

    Notes
    -----
    - User confirmation is required if files exist at the destination.
    """
    # Resolve needed files.
    files_to_copy = cases[calculation.kind]["files"][calculation.code]
    if calculation.scratch and calculation.code == "quantum_espresso":
        files_to_copy.append("SYSTEM.INFO")
    files_to_copy.append("master.sh")

    # Copy the files
    source_dir = os.path.join(os.path.dirname(__file__), "data", calculation.code)
    for file_name in files_to_copy:
        source_path = os.path.join(source_dir, file_name)
        destination_path = os.path.join(os.getcwd(), file_name)

        if os.path.exists(source_path):
            if os.path.exists(destination_path) and not calculation.overwrite:
                # Prompt for overwrite confirmation
                confirmation = input(
                    f"The file '{file_name}' already exists. Do you want to overwrite it? (yes/no): "
                )
                if confirmation.strip().lower() not in ["yes", "y"]:
                    print(f"Skipped overwriting '{file_name}'.")
                    continue
            shutil.copy(source_path, destination_path)
            print(f"Copied '{file_name}'.")
        else:
            print(
                f"Error: The input file '{file_name}' does not exist in the library:\n{source_path}."
            )
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
    # Remove non-valid scripts
    sub_scripts.remove(os.path.basename(master_script_path))
    sub_scripts = [script for script in sub_scripts if script.endswith(".sh")]

    # Prepare lines to append
    if len(sub_scripts) > 1:
        script_lines = [f"bash {script}\n" for script in sub_scripts]
        # Insert lines
        _insert_lines(master_script_path, script_lines, "#Actual JOBS")

    print(f"Successfully populated '{master_script_path}' with sub-scripts.")
    return sub_scripts


def set_master_preamble(master_script_path: str, cluster: str):
    """
    Prepends cluster-specific preamble to a master script file.

    This function reads a cluster-specific heading from a file and inserts
    it at the beginning of a master script, updating the script to reflect
    the target cluster’s setup requirements.

    Parameters
    ----------
    master_script_path : str
        Path to the master script file to be updated.
    cluster : str
        The name of the cluster whose preamble should be added to the master
        script.
    """
    source_dir = os.path.join(os.path.dirname(__file__), "data/sbatch_headings")

    heading = clusters[cluster]["heading"]
    file_path = os.path.join(source_dir, heading)
    with open(file_path, "r") as file:
        preamble = file.readlines()
    with open(master_script_path, "r") as file:
        master = file.readlines()

    updated_lines = preamble + ["\n"] + master

    # Write the updated lines back into the file
    with open(master_script_path, "w") as file:
        file.writelines(updated_lines)

    print(f"Successfully added the '{heading}' heading for '{master_script_path}'.")


def change_mpi_command(file_path: str, cluster: str):
    """
    Modifies a script by replacing existing MPI commands with a cluster-specific command.

    This function scans through the specified file, identifies lines containing MPI executables,
    removes existing MPI commands, and prepends the cluster-specific MPI command. If modifications
    are made, the file is updated accordingly.

    Parameters
    ----------
    file_path : str
        Path to the script file that requires MPI command modification.
    cluster : str
        The name of the cluster whose MPI command should be used in the script.
    """
    changes = False
    mpi_command = clusters[cluster]["mpi_command"]
    commands = [clusters[key]["mpi_command"] for key in clusters.keys()]
    commands = sorted(list(set(commands)), key=len, reverse=True)

    with open(file_path, "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        for exe in executables:
            if exe in line:
                changes = True
                for c in commands:
                    line.replace(c, "")
                lines[i] = f"{mpi_command} {line}"

    if not changes:
        return

    with open(file_path, "w") as file:
        file.writelines(lines)

    print(f"Successfully added the '{mpi_command}' prefix in '{file_path}'.")


def set_spin_orbit_coupling(calculation):
    files = cases[calculation.kind]["files"][calculation.code]
    if calculation.code == "quantum_espresso":
        scripts = [file for file in files if file.endswith(".sh")]
        for script in scripts:
            if calculation.soc:
                _replace_setting(script, "noncolin=", "noncolin=.true.")
                _replace_setting(script, "lspinorb=", "lspinorb=.true.")
            else:
                _replace_setting(script, "noncolin=", "noncolin=.false.")
                _replace_setting(script, "lspinorb=", "lspinorb=.false.")


def set_cell_relaxation(calculation):
    if calculation.code == "quantum_espresso":
        if not calculation.cell_relaxation:
            _replace_setting("relax.sh", "calculation=", "calculation='relax'")


def configure_files(calculation):
    options = list(calculation.__dict__.keys())
    # Spin-orbit coupling
    if "soc" in options:
        set_spin_orbit_coupling(calculation)
    # Cell relaxation
    if calculation.kind == "relax":
        set_cell_relaxation(calculation)


def set_crystal_structure(calculation):
    if calculation.structure is None:
        return
    C = Cell.from_file(calculation.structure)

    formula = C.atoms.get_chemical_formula()
    cell = np.asarray(C.atoms.get_cell())
    positions = np.asarray(C.atoms.get_scaled_positions())
    symbols = C.atoms.get_chemical_symbols()

    if calculation.code == "quantum_espresso":
        _replace_setting("SYSTEM.INFO", "NAME='NoName'", f"NAME='{formula}'")
        _replace_setting("SYSTEM.INFO", "ATM_NUM=", f"ATM_NUM={len(positions)}")
        _replace_setting("SYSTEM.INFO", "ATM_TYPES=", f"ATM_TYPES={len(set(symbols))}")
        # Atomic positions
        _remove_lines("SYSTEM.INFO", "ATOMIC_CRYST_POSITIONS=", "EOL")
        lines = []
        for s, (x, y, z) in zip(symbols, positions):
            lines.append(f"{s:<2} {x:14.9f} {y:14.9f} {z:14.9f}\n")
        _insert_lines("SYSTEM.INFO", lines, "ATOMIC_CRYST_POSITIONS=")
        # Lattice
        _remove_lines("SYSTEM.INFO", "LATTICE=", "EOL")
        lines = []
        for x, y, z in cell:
            lines.append(f"{x:14.9f} {y:14.9f} {z:14.9f}\n")
        _insert_lines("SYSTEM.INFO", lines, "LATTICE=")
        if calculation.scratch:
            # More changes beyond just crystal structure
            pass


def get_pseudo(
    calculation, exchange: str = None, kind: str = None, relativistic: bool = False
):
    if calculation.structure is None:
        return

    C = Cell.from_file(calculation.structure)
    symbols = set(C.atoms.get_chemical_symbols())

    # Get pseudos
    ps_library = os.environ.get("PSLIBRARY")
    if exchange is None:
        exchange = pseudopotentials[0]
    if kind is None:
        kind = "kjpaw"
    if relativistic:
        exchange = "rel-" + exchange
    source_path = os.path.join(ps_library, exchange, "PSEUDOPOTENTIALS")
    pseudos = []
    for sym in symbols:
        target = suggested_qe_pseudos[sym]
        target = target.replace("$fct", exchange).replace("*", kind)[:-6]
        search = glob.glob(f"{source_path}/{target}*")
        if len(search) == 1:
            pseudo = search[0]
        elif len(search) > 1:
            print(
                "Error: More than one option.. etc, requiere manual intervention.. etc (complete this)"
            )
        elif len(search) == 0:
            print("Error: No pseudos found... etc (complete this)")
        pseudos.append(pseudo)

    # Get masses
    masses = []
    for sym in symbols:
        atomic_mass = atomic_masses[atomic_numbers[sym]]
        masses.append(atomic_mass)

    # Prepare lines
    lines = []
    for s, m, p in zip(symbols, masses, pseudos):
        lines.append(f"{s:<2} {m:11.6f}   {os.path.basename(p)}\n")

    # Put the pseudo
    _remove_lines("SYSTEM.INFO", "ATOMIC_SPECIES=", "EOL")
    _insert_lines("SYSTEM.INFO", lines, "ATOMIC_SPECIES=")
    _replace_setting("SYSTEM.INFO", "EXCHANGE=", f"EXCHANGE='{exchange}'")

    # Get appropaite cutoff and ecutrho
    cutoff, ecutrho = [], []
    for pseudo in pseudos:
        with open(pseudo, "r") as file:
            lines = file.readlines()
        for line in lines:
            if "Suggested minimum cutoff for wavefunctions" in line:
                cutoff.append(float(line.split()[-2]))
            elif "Suggested minimum cutoff for charge density:" in line:
                ecutrho.append(float(line.split()[-2]))
    if len(cutoff) != len(pseudos) or len(ecutrho) != len(pseudos):
        print(
            "Error: Either the minimum suggested values for cutoff and ecutrho could not be read."
        )
    ratio = 1.5
    cutoff = int(np.max(cutoff) * ratio)
    ecutrho = int(np.max(ecutrho) * ratio)
    _replace_setting("SYSTEM.INFO", "CUTOFF=", f"CUTOFF={cutoff}")
    _replace_setting("SYSTEM.INFO", "ECUTRHO=", f"ECUTRHO={ecutrho}")

    # Get appropaite KGRID
    kgrid = auto_kgrid(C[0], n_atoms=len(C[1]), kppra=9000)
    kgrid_str = " ".join(map(str, kgrid))
    _replace_setting("SYSTEM.INFO", "KGRID=", f"KGRID='{kgrid_str}'")

    # Change High-symmetry-path
    space_group = spg.get_spacegroup(C).split("(")[1].split(")")[0]
    source_dir = os.path.join(
        os.path.dirname(__file__), "data", "kpaths", "quantum_espresso"
    )
    with open(f"{source_dir}/SG{space_group}") as file:
        lines = file.readlines()
    _remove_lines("SYSTEM.INFO", "QE_CRYST_PATH=", "EOL")
    _insert_lines("SYSTEM.INFO", lines, "QE_CRYST_PATH=")


def prepare_calculation(calculation: SimpleNamespace):
    # Copy files
    copied_files = copy_input_files(calculation)
    # Create default master.sh
    scripts = populate_master_script("master.sh", copied_files)
    set_master_preamble("master.sh", cluster=calculation.cluster)
    # Change mpi prefix
    for file in scripts:
        change_mpi_command(file, calculation.cluster)
    # Change scripts depending on calculation
    configure_files(calculation)
    # Modify SYSTEM.INFO
    set_crystal_structure(calculation)
    # Set pseudopotentials
    get_pseudo(calculation)
