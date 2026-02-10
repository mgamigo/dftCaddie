# CODE IDEA

- Create the sbatch client for changing partitions and configurations easily.

dftCaddie/
├── __init__.py
├── cli.py                 # Command-line interface for user interaction
├── mode_client.py         # Clients for the different modes
├── data/                  # Contains template input files
│   ├── config.default.yalm   # Default configuration
│   ├── vasp/
│   │   ├── INCAR.relaxation
│   │   └── INCAR.bandstructure
│   └── quantum_espresso/
│   │   ├── pw.scf.in
│   │   └── pw.bands.in
│   └── sbatch_headings/
│       ├── clusterX_headingY
│       └── clusterX_headingZ
├── file_management.py     # Functions to copy and modify input files
├── utils.py               # Utility functions for string formatting, option resolution, etc.
├── config.py              # Loads configuration (user of default)
└── examples/              # Example workflows and demos
    └── example_workflow.py
