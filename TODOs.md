# CODE IDEA

dftCaddie/
├── __init__.py
├── cli.py                 # Command-line interface for user interaction
├── data/                  # Contains template input files
│   ├── vasp/
│   │   ├── INCAR.relaxation
│   │   └── INCAR.bandstructure
│   └── quantum_espresso/
│       ├── pw.scf.in
│       └── pw.bands.in
├── file_management.py     # Functions to copy and modify input files
├── script_generation.py   # Generate sbatch or other setup scripts (without submission logic)
├── utils.py               # Utility functions for string formatting, option resolution, etc.
└── examples/              # Example workflows and demos
    └── example_workflow.py
