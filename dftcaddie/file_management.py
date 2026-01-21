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

_all__ = [
    "copy_input_files",
]


def copy_input_files(code: str, files_to_copy: list[str], overwrite: bool = False):
    """
    Copies specified input files for a given DFT code into the current
    working directory. Prompts users to confirm overwriting if files
    already exist at the destination.

    Parameters
    ----------
    code : str
        The DFT code identifier (e.g., "vasp", "quantum espresso").
    files_to_copy : list[str]
        Filenames to copy from the code-specific directory in the library's
        `data` directory.
    overwrite : bool, optional
        Overwrite existing files if necessary. Default is False.

    Notes
    -----
    - User confirmation is required if files exist at the destination.
    """
    source_dir = os.path.join(os.path.dirname(__file__), "data", code.replace(" ", "_"))

    for file_name in files_to_copy:
        source_path = os.path.join(source_dir, file_name)
        destination_path = os.path.join(os.getcwd(), file_name)

        if os.path.exists(source_path):
            if os.path.exists(destination_path) and not overwrite:
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
    sub_scripts = [script for script in sub_scripts if script.endswith('.sh')]

    # Read the current content of master.sh
    with open(master_script_path, "r") as file:
        lines = file.readlines()

    # Prepare lines to append
    script_lines = [f"bash {script}\n" for script in sub_scripts]

    # Find the index where "#Actual JOBS" occurs
    try:
        actual_jobs_index = lines.index("#Actual JOBS\n") + 1
    except ValueError:
        print("Error: '#Actual JOBS' not found in the master.sh script.")
        return

    # Insert sub_script sources after "#Actual JOBS"
    updated_lines = lines[:actual_jobs_index] + script_lines + lines[actual_jobs_index:]

    # Write the updated lines back to master.sh
    with open(master_script_path, "w") as file:
        file.writelines(updated_lines)

    print(f"Successfully populated '{master_script_path}' with sub-scripts.")
