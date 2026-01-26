"""
dftCaddie | dftcaddie.config
============================

This module defines configuration variables used throughout the dftCaddie
application, providing flexible support for different calculation types,
DFT codes, and necessary input files.
"""


# Kinds of calculations
# Files located in data/code
def _config_soc(default: bool = None):
    config = {
        "name": "soc",
        "question": "Spin orbit coupling:",
        "options": [True, False],
    }
    if isinstance(default, bool):
        config["default"] = default
    return config


calculations = {
    "bands": {
        "name": "[B]ands",
        "config": [
            {
                "name": "code",
                "question": "Available codes:",
                "options": ["quantum_espresso", "vasp"],
            },
            _config_soc(True),
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
            _config_soc(False),
        ],
        "files": {
            "quantum_espresso": ["relax.sh"],
            "vasp": ["INCAR.RELAX", "KPOINTS.SCC"],
        },
    },
    "phonons": {
        "name": "[P]honons",
        "config": [
            {
                "name": "code",
                "question": "Available codes:",
                "options": ["quantum_espresso"],
            },
            _config_soc(False),
        ],
        "files": {
            "quantum_espresso": ["scf.sh", "ph.sh", "matdyn.sh"],
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
    "triton": {"hostname": "triton", "heading": "triton", "mpi_command": "srun"},
    "puhti": {"hostname": "puhti", "heading": "puhti_mahti", "mpi_command": "srun"},
    "mahti": {"hostname": "mahti", "heading": "puhti_mahti", "mpi_command": "srun"},
    "planck": {
        "hostname": "login",
        "heading": "planck",
        "mpi_command": "srun --mpi=pmi2",
    },
}

# Executables over which mpi_command should be added
mpi_executables = ["pw.x", "projwfc.x", "ph.x"]

# Pseudopotentials (first one being the default one).
pseudopotentials = ["pbe", "pbesol", "pz"]
# The ones given in the pslibrary repository
suggested_qe_pseudos = {
    "H": "H.$fct-*_psl.1.0.0",
    "He": "He.$fct-*_psl.1.0.0",
    "Li": "Li.$fct-sl-*_psl.1.0.0",
    "Be": "Be.$fct-sl-*_psl.1.0.0",
    "B": "B.$fct-n-*_psl.1.0.0",
    "C": "C.$fct-n-*_psl.1.0.0",
    "N": "N.$fct-n-*_psl.1.0.0",
    "O": "O.$fct-n-*_psl.1.0.0",
    "F": "F.$fct-n-*_psl.1.0.0",
    "Ne": "Ne.$fct-n-*_psl.1.0.0",
    "Na": "Na.$fct-spnl-*_psl.1.0.0",
    "Mg": "Mg.$fct-spnl-*_psl.1.0.0",
    "Al": "Al.$fct-nl-*_psl.1.0.0",
    "Si": "Si.$fct-nl-*_psl.1.0.0",
    "P": "P.$fct-nl-*_psl.1.0.0",
    "S": "S.$fct-nl-*_psl.1.0.0",
    "Cl": "Cl.$fct-nl-*_psl.1.0.0",
    "Ar": "Ar.$fct-nl-*_psl.1.0.0",
    "K": "K.$fct-spn-*_psl.1.0.0",
    "Ca": "Ca.$fct-spn-*_psl.1.0.0",
    "Sc": "Sc.$fct-spn-*_psl.1.0.0",
    "Ti": "Ti.$fct-spn-*_psl.1.0.0",
    "V": "V.$fct-spnl-*_psl.1.0.0",
    "Cr": "Cr.$fct-spn-*_psl.1.0.0",
    "Mn": "Mn.$fct-spn-*_psl.0.3.1",
    "Fe": "Fe.$fct-n-*_psl.1.0.0",
    "Co": "Co.$fct-n-*_psl.0.3.1",
    "Ni": "Ni.$fct-n-*_psl.1.0.0",
    "Cu": "Cu.$fct-dn-*_psl.1.0.0",
    "Zn": "Zn.$fct-dn-*_psl.1.0.0",
    "Ga": "Ga.$fct-dnl-*_psl.1.0.0",
    "Ge": "Ge.$fct-n-*_psl.1.0.0",
    "As": "As.$fct-n-*_psl.1.0.0",
    "Se": "Se.$fct-n-*_psl.1.0.0",
    "Br": "Br.$fct-n-*_psl.1.0.0",
    "Kr": "Kr.$fct-dn-*_psl.1.0.0",
    "Rb": "Rb.$fct-spn-*_psl.1.0.0",
    "Sr": "Sr.$fct-spn-*_psl.1.0.0",
    "Y": "Y.$fct-spn-*_psl.1.0.0",
    "Zr": "Zr.$fct-spn-*_psl.1.0.0",
    "Nb": "Nb.$fct-spn-*_psl.1.0.0",
    "Mo": "Mo.$fct-spn-*_psl.1.0.0",
    "Tc": "Tc.$fct-spn-*_psl.0.3.0",
    "Ru": "Ru.$fct-spn-*_psl.1.0.0",
    "Rh": "Rh.$fct-spn-*_psl.1.0.0",
    "Pd": "Pd.$fct-n-*_psl.1.0.0",
    "Ag": "Ag.$fct-n-*_psl.1.0.0",
    "Cd": "Cd.$fct-n-*_psl.1.0.0",
    "In": "In.$fct-dn-*_psl.1.0.0",
    "Sn": "Sn.$fct-dn-*_psl.1.0.0",
    "Sb": "Sb.$fct-n-*_psl.1.0.0",
    "Te": "Te.$fct-n-*_psl.1.0.0",
    "I": "I.$fct-n-*_psl.1.0.0",
    "Xe": "Xe.$fct-dn-*_psl.1.0.0",
    "Cs": "Cs.$fct-spnl-*_psl.1.0.0",
    "Ba": "Ba.$fct-spn-*_psl.1.0.0",
    "La": "La.$fct-spfn-*_psl.1.0.0",
    "Ce": "Ce.$fct-spdn-*_psl.1.0.0",
    "Pr": "Pr.$fct-spdn-*_psl.1.0.0",
    "Nd": "Nd.$fct-spdn-*_psl.1.0.0",
    "Pm": "Pm.$fct-spdn-*_psl.1.0.0",
    "Sm": "Sm.$fct-spdn-*_psl.1.0.0",
    "Eu": "Eu.$fct-spn-*_psl.1.0.0",
    "Gd": "Gd.$fct-spdn-*_psl.1.0.0",
    "Tb": "Tb.$fct-spdn-*_psl.1.0.0",
    "Dy": "Dy.$fct-spdn-*_psl.1.0.0",
    "Ho": "Ho.$fct-spdn-*_psl.1.0.0",
    "Er": "Er.$fct-spdn-*_psl.1.0.0",
    "Tm": "Tm.$fct-spdn-*_psl.1.0.0",
    "Yb": "Yb.$fct-spn-*_psl.1.0.0",
    "Lu": "Lu.$fct-spdn-*_psl.1.0.0",
    "Hf": "Hf.$fct-spn-*_psl.1.0.0",
    "Ta": "Ta.$fct-spn-*_psl.1.0.0",
    "W": "W.$fct-spn-*_psl.1.0.1",
    "Re": "Re.$fct-spn-*_psl.1.0.0",
    "Os": "Os.$fct-spn-*_psl.1.0.0",
    "Ir": "Ir.$fct-n-*_psl.0.2.3",
    "Pt": "Pt.$fct-n-*_psl.1.0.0",
    "Au": "Au.$fct-n-*_psl.1.0.1",
    "Hg": "Hg.$fct-n-*_psl.1.0.0",
    "Tl": "Tl.$fct-dn-*_psl.1.0.0",
    "Pb": "Pb.$fct-dn-*_psl.1.0.0",
    "Bi": "Bi.$fct-dn-*_psl.1.0.0",
    "Po": "Po.$fct-dn-*_psl.1.0.0",
    "At": "At.$fct-dn-*_psl.1.0.0",
    "Rn": "Rn.$fct-dn-*_psl.1.0.0",
    "Fr": "Fr.$fct-spdn-*_psl.1.0.0",
    "Ra": "Ra.$fct-spdn-*_psl.1.0.0",
    "Ac": "Ac.$fct-spfn-*_psl.1.0.0",
    "Th": "Th.$fct-spfn-*_psl.1.0.0",
    "Pa": "Pa.$fct-spfn-*_psl.1.0.0",
    "U": "U.$fct-spfn-*_psl.1.0.0",
    "Np": "Np.$fct-spfn-*_psl.1.0.0",
    "Pu": "Pu.$fct-spfn-*_psl.1.0.0",
}
