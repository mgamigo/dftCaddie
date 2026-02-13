# CODE IDEA

- Make so that **all** config files can be stored in .config/dftcaddie.
- Rewrite the current yaml.config as a placeholder without personal info.
- Put instructions in current yalm.config file.
- Complete the vasp functionalities.
- Make SYSTEM.INFO clearer and more understandable.

```
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
```
