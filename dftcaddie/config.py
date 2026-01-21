"""
dftCaddie | dftcaddie.config
============================

This module defines configuration variables used throughout the dftCaddie
application, providing flexible support for different calculation types,
DFT codes, and necessary input files.
"""

cases = {
    "bands": {
        "name": "[B]ands",
        "codes": ["quantum espresso", "vasp"],
        "files": {
            "quantum espresso": ["scf.sh", "bands.sh", "project_bands.sh"],
            "vasp": ["INCAR.SCC", "INCAR.BS", "KPOINTS.SCC"],
        },
    },
    "relax": {
        "name": "[R]elax",
        "codes": ["quantum espresso", "vasp"],
        "additional": [
            {
                "name": "cell relaxation",
                "question": "Do you want also a cell relaxation?",
                "options": ["yes", "no"],
            }
        ],
        "files": {
            "quantum espresso": ["relax.sh"],
            "vasp": ["INCAR.RELAX", "KPOINTS.SCC"],
        },
    },
}
