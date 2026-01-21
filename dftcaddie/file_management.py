"""
dftCaddie | dftcaddie.file_management
=====================================
"""

import os
import shutil


def copy_input_files(code, files_to_copy):
    """
    Copy necessary input files for the specified calculation type and code.

    :param code: DFT code (e.g., "vasp", "quantum espresso")
    :param files_to_copy: List of filenames to copy
    :param selections: Additional options selected by the user
    """
    source_dir = os.path.join(os.path.dirname(__file__), "data", code.replace(" ", ""))

    for file_name in files_to_copy:
        source_path = os.path.join(source_dir, file_name)
        destination_path = os.path.join(os.getcwd(), file_name)

        if os.path.exists(source_path):
            if os.path.exists(destination_path):
                # Prompt for overwrite confirmation
                overwrite = input(
                    f"The file '{file_name}' already exists. Do you want to overwrite it? (yes/no): "
                )
                if overwrite.strip().lower() not in ["yes", "y"]:
                    print(f"Skipped overwriting '{file_name}'.")
                    continue
            shutil.copy(source_path, destination_path)
            print(f"Copied '{file_name}'.")
        else:
            print(
                f"Error: The input file '{file_name}' does not exist in the library:\n{source_path}."
            )
