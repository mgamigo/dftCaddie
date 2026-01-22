"""
dftCaddie | dftcaddie.config
============================

This module defines configuration variables used throughout the dftCaddie
application, providing flexible support for different calculation types,
DFT codes, and necessary input files.
"""

# Files located in data/code
cases = {
    "bands": {
        "name": "[B]ands",
        "config": [
            {
                "name": "code",
                "question": "Available codes:",
                "options": ["quantum_espresso", "vasp"],
            },
        ],
        "files": {
            "quantum_espresso": ["scf.sh", "bands.sh", "project_bands.sh"],
            "vasp": ["INCAR.SCC", "INCAR.BS", "KPOINTS.SCC"],
        },
    },
    "relax": {
        "name": "[R]elax",
        "config": [
            {
                "name": "code",
                "question": "Available codes:",
                "options": ["quantum_espresso", "vasp"],
            },
            {
                "name": "cell_relaxation",
                "question": "Do you want also a cell relaxation?",
                "options": [True, False],
            },
        ],
        "files": {
            "quantum_espresso": ["relax.sh"],
            "vasp": ["INCAR.RELAX", "KPOINTS.SCC"],
        },
    },
}

# Cluster configuartion
clusters = {
    None: {
        "hostname": None,
        "heading": "default",
        "mpi_command": "mpiexec -np 2",
    },
    "ekhi": {
        "hostname": "ekhi",
        "heading": "ekhi",
        "mpi_command": "mpiexec -np $NPROCS",
    },
    "planck": {
        "hostname": "login",
        "heading": "planck",
        "mpi_command": "srun --mpi=pmi2",
    },
    "triton": {"hostname": "triton", "heading": "trion", "mpi_command": "srun"},
    "puhti": {"hostname": "puhti", "heading": "puhti_mahti", "mpi_command": "srun"},
    "mahti": {"hostname": "mahti", "heading": "puhti_mahti", "mpi_command": "srun"},
}

# Executables over which mpi_command should be added
executables = ["pw.x", "projwfc.x", "ph.x"]
