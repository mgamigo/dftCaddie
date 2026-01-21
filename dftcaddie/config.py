"""
dftCaddie | dftcaddie.config
============================

This module defines configuration variables used throughout the dftCaddie
application, providing flexible support for different calculation types,
DFT codes, and necessary input files.
"""

#Files located in data/code
cases = {
    "bands": {
        "name": "[B]ands",
        "codes": ["quantum_espresso", "vasp"],
        "files": {
            "quantum_espresso": ["scf.sh", "bands.sh", "project_bands.sh"],
            "vasp": ["INCAR.SCC", "INCAR.BS", "KPOINTS.SCC"],
        },
    },
    "relax": {
        "name": "[R]elax",
        "codes": ["quantum_espresso", "vasp"],
        "additional": [
            {
                "name": "cell_relaxation",
                "question": "Do you want also a cell relaxation?",
                "options": [True, False],
            }
        ],
        "files": {
            "quantum_espresso": ["relax.sh"],
            "vasp": ["INCAR.RELAX", "KPOINTS.SCC"],
        },
    },
}

#Headings located in data/sbatch_headings
sbatch_headings = {
    "ekhi": "ekhi",
    "login": "planck",
    "triton": "triton",
    "puthi": "puhti_mahti",
    "mahti": "puhti_mahti",
}
