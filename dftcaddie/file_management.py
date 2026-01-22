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
from types import SimpleNamespace

from dftcaddie.config import cases, clusters, executables

_all__ = [
    "copy_input_files",
]


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


def copy_input_files(calculation: SimpleNamespace) -> list[str]:
    """
    [TODO:summary]

    [TODO:description]

    Parameters
    ----------
    calculation : SimpleNamespace
        [TODO:description]

    Returns
    -------
    list[str]
        [TODO:description]
    """
    """
    Copies specified input files for a given DFT code into the current
    working directory. Prompts users to confirm overwriting if files
    already exist at the destination.

    Parameters
    ----------
    calculation : SimpleNamespace
        A Namespace with all the relevant details.

    Returns
    -------j
    files : list[str]
        List of files that were copied for the calculation.

    Notes
    -----
    - User confirmation is required if files exist at the destination.
    """
    # Resolve needed files.
    files_to_copy = cases[calculation.kind]["files"][calculation.code]
    if calculation.scratch and code == "quantum_espresso":
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


def populate_master_script(master_script_path: str, sub_scripts: list[str]):
    """
    Integrates sub-scripts into the master.sh script, modifying its content
    to include references or execution commands for the specified scripts.

    Parameters
    ----------
    sub_scripts : list[str]
        A list of filenames representing sub-scripts to integrate.

    master_script_path : str
        Path to the master.sh script to be modified or populated.

    Notes
    -----
    - It will ignore all files that are not `.sh` files.
    """
    # Remove non-valid scripts
    sub_scripts.remove(os.path.basename(master_script_path))
    sub_scripts = [script for script in sub_scripts if script.endswith(".sh")]

    # Prepare lines to append
    script_lines = [f"bash {script}\n" for script in sub_scripts]

    # Insert lines
    _insert_lines(master_script_path, script_lines, "#Actual JOBS")

    print(f"Successfully populated '{master_script_path}' with sub-scripts.")
    return sub_scripts


def set_master_preamble(master_script_path: str, cluster: str):
    """
    DOCU
    """
    source_dir = os.path.join(os.path.dirname(__file__), "data/sbatch_headings")

    file_path = os.path.join(source_dir, clusters[cluster]["heading"])
    with open(file_path, "r") as file:
        preamble = file.readlines()
    with open(master_script_path, "r") as file:
        master = file.readlines()

    updated_lines = preamble + master

    # Write the updated lines back into the file
    with open(master_script_path, "w") as file:
        file.writelines(updated_lines)

    print(f"Successfully added the '{cluster}' heading for '{master_script_path}'.")


def set_mpi_command(file_path: str, cluster: str):
    mpi_command = clusters[cluster]["mpi_command"]
    commands = [clusters[key]["mpi_command"] for key in clusters.keys()]
    commands = sorted(list(set(commands)), key=len, reverse=True)

    with open(file_path, "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        for exe in executables:
            if exe in line:
                for c in commands:
                    line.replace(c, "")
                lines[i] = f"{mpi_command} {line}"

    with open(file_path, "w") as file:
        file.writelines(lines)
