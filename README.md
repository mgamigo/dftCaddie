# dftCaddie
<div align="center">
<pre>
   '\                   .  .                        |>>
     \              .         ' .                   |  
    O>>         .                 'o                |  
     \       .                                      |  
     /\    .                                        |  
    / /  .'                  Don’t shoot the caddie |  
^^^^^^^`^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  
</pre>
</div>

<p align="center">
  Prepare DFT calculations from the terminal, using your own templates and conventions.
  <br />
  <a href="#installation">Installation</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="https://github.com/mgamigo/dftCaddie/issues">Report an Issue</a>
</p>

## About the Project

dftCaddie is a Python command-line tool for preparing DFT calculation folders.
Its installed command is `caddie`. It brings together the repeated steps of
copying input templates, inserting a crystal structure, setting k-points,
selecting pseudopotentials, and configuring job scripts.

The starting point is **your way of preparing calculations**. Most input
defaults live in editable templates. Configuration defines which templates
belong to a calculation and exposes choices such as the code, calculation
flavor, and spin-orbit coupling. Caddie applies the corresponding edits.

It runs entirely in the terminal, including over SSH on a cluster. Use typed
prompts when working interactively, or explicit arguments when preparing
calculations from scripts and agents.

### What It Does

- Copies the input files and scripts for a selected calculation.
- Reads structures such as CIF, POSCAR, and supported Quantum ESPRESSO inputs.
- Writes lattice vectors and atomic positions into supported templates.
- Generates automatic k-point grids and inserts stored high-symmetry paths.
- Resolves Quantum ESPRESSO pseudopotentials and assembles VASP POTCAR files.
- Sets energy cutoffs from pseudopotential recommendations when requested.
- Applies spin-orbit and cell-relaxation choices.
- Configures MPI launch commands and the scheduler header in `master.sh`.
- Checks configuration, referenced resources, and preparation workflows.
- Completes commands, flags, paths, and configured choices in the shell.

Caddie **prepares files**. It does not execute DFT calculations or submit jobs.
Review and run the resulting scripts using your normal local or cluster workflow.

### How It Works

```text
Calculation choice + your configuration + your templates
                            |
                 Copy and configure inputs
                            |
              Structure, k-points, pseudopotentials
                            |
                  Prepared calculation folder
```

Three parts define a preparation:

| Part | Role |
| --- | --- |
| Templates | Input parameters, shell scripts, and your preferred calculation defaults. |
| Configuration | Calculation kinds, flavors, template mappings, cluster presets, and selected numerical defaults. |
| Request | The choices and structure supplied through CLI arguments or interactive prompts. |

A **kind** identifies a workflow, such as `bands` or `relax`. A **flavor**
selects a variation of that workflow, such as fixed-cell or variable-cell
relaxation. A **code** selects the backend and its templates.

Caddie aims to make these preparation steps explicit and repeatable. To
reproduce an older preparation, retain the templates, configuration, structure,
and pseudopotential library used for it; repeating the command alone does not
freeze those resources.

## Installation

Python **3.10 or newer** is required. Clone the repository before installing
with either uv or pip:

```bash
git clone https://github.com/mgamigo/dftCaddie.git
cd dftCaddie
```

### uv

Install `caddie` as an isolated command without manually managing a virtual
environment:

```bash
uv tool install .
caddie --help
```

For development, use an editable installation instead so source changes take
effect immediately:

```bash
uv tool install --editable .
```

### pip

Create and activate a virtual environment, then install the package:

```bash
python -m venv ~/.venvs/dftcaddie
source ~/.venvs/dftcaddie/bin/activate
python -m pip install .
caddie --help
```

With pip 25.1 or newer, an editable development installation including the
`dev` dependency group can be installed with:

```bash
python -m pip install --editable . --group dev
```

The Python installation includes YAIV, Questionary, and argcomplete.
DFT executables, MPI, Slurm, and pseudopotential libraries are configured
separately; caddie does not install them.

## Quick Start

### Prepare Your First Folder

After cloning the repository, try the bundled silicon fixture. This example
does not require a pseudopotential library:

```bash
mkdir -p ~/caddie-example
cp tests/data/Si.cif ~/caddie-example/Si.cif
cd ~/caddie-example

caddie calc --kind bands --code quantum_espresso --structure Si.cif
caddie set system Si.cif --autokgrid --kpath
```

The first command copies the band-structure templates and inserts the structure.
The second configures the k-grid and high-symmetry path. Pseudopotentials still
need to be configured before running the calculation.

**Preparation commands write into the current working directory.** Use a
separate directory for each calculation. Paths such as `../Si.cif` are also
accepted when the structure is stored elsewhere.

### Use Interactive Choices

```bash
caddie calc
caddie calc --details
```

Type a full name or a unique prefix, ignoring case, and press Enter. For
example, `ban` selects `bands` when it is unambiguous. Tab completes names;
ambiguous input stays in the prompt until you refine it.

Configured defaults are normally applied automatically. `--details` asks
about configurable choices instead. Boolean settings use yes/no confirmations.
CLI arguments themselves should use the full configuration keys, such as
`--code quantum_espresso`.

### Prepare Automatically

Once the required pseudopotential library is configured:

```bash
caddie calc --kind bands --code quantum_espresso --structure Si.cif --auto
```

`--auto` requests system configuration, an automatic k-grid, a high-symmetry path,
and pseudopotential configuration with cutoffs. It still asks for unresolved
calculation choices when necessary.

Both `calc --auto` and `calc --pseudo` require `--structure FILE`.
The latter adds pseudopotentials without automatically requesting k-grid and
k-path configuration.

## Commands

| Command | Purpose |
| --- | --- |
| `caddie calc` | Create and configure a calculation from templates. |
| `caddie set system FILE` | Adapt an existing calculation to a structure and optionally set its k-points. |
| `caddie set pseudo FILE` | Select pseudopotentials and optionally configure cutoffs. |
| `caddie set header` | Replace the scheduler header in `master.sh`. |
| `caddie config init` | Copy editable default configuration and resources into your home directory. |
| `caddie config check` | Validate configuration and resources. |

Every command supports `--help`. For additional logging, put the global
verbosity flag before the subcommand:

```bash
caddie calc --help
caddie set --help
caddie set system --help
caddie set pseudo --help
caddie set header --help
caddie -v calc --kind bands --code vasp
caddie -vv config check
```

### Bundled Calculations

The bundled configuration provides:

| Kind | Flavors | Codes |
| --- | --- | --- |
| `bands` | None | `quantum_espresso`, `vasp` |
| `relax` | `fixed_cell`, `variable_cell` | `quantum_espresso`, `vasp` |
| `phonons` | None | `quantum_espresso` |

Your user configuration may provide a different selection. Bundled bands
default to SOC enabled; relaxation and phonons default to SOC disabled.
Use `--details` to choose interactively, or edit the configured defaults.

## Examples

Run each new calculation example in its own folder, with the structure path
adjusted as needed.

### Fixed-Cell Relaxation with Quantum ESPRESSO

```bash
caddie calc --kind relax --flavor fixed_cell --code quantum_espresso
caddie set system ../Si.cif --autokgrid
caddie set pseudo ../Si.cif --configure
```

### Variable-Cell Relaxation with VASP

This requires a configured VASP pseudopotential library:

```bash
caddie calc --kind relax --flavor variable_cell --code vasp --structure ../Si.cif
caddie set system ../Si.cif --autokgrid --kppra 12000
caddie set pseudo ../Si.cif --configure
```

### Change the K-Point Density

Inside an existing calculation folder:

```bash
caddie set system ../Si.cif --autokgrid --kppra 16000
```

`--kppra` sets the target k-point density used by `--autokgrid`. It does not
request grid generation on its own.

### Select Quantum ESPRESSO Pseudopotentials

```bash
caddie set pseudo ../Si.cif --exchange pbe --kind paw --relativistic --configure
```

Here `--kind` means the pseudopotential type, not the calculation kind.
`--relativistic` selects relativistic QE potentials and enables SOC;
omitting it disables SOC when applying pseudopotentials.
`--configure` also updates cutoffs using the configured multiplier.

The exchange and pseudopotential-kind selectors currently apply to QE.
The VASP command path uses the library's PBE PAW selection.

### Change a Scheduler Header

```bash
caddie set header --cluster local --header default
```

For a configured cluster, use its key and header name. Omit `--header` for
an interactive choice. If `--cluster` is omitted, caddie matches the hostname
against the configured clusters and falls back to `local`.

This command replaces the header while preserving the job body and current
job name. It does not submit the job or rewrite MPI commands in sub-scripts.

## Configuration

Caddie uses bundled resources until a user configuration exists. Initialize
your editable copy with:

```bash
caddie config init
```

```text
~/.config/dftcaddie/
    config.yaml
    templates/
    sbatch_headers/
    kpaths/
```

When `~/.config/dftcaddie/config.yaml` exists, it selects that resource tree.
Template paths in the YAML are relative to its `templates/` directory, and
header filenames refer to `sbatch_headers/`. The user configuration is used
instead of merging it with the bundled configuration.

Repeated initialization preserves existing files and directories.
`caddie config init --force` replaces them with bundled defaults, including
customized templates, headers, and k-paths.

### Pseudopotential Libraries

Edit these entries in your user `config.yaml` to point to existing libraries:

```yaml
qe_pslibrary: /path/to/pslibrary
vasp_pseudopotentials: /path/to/vasp/potentials
```

For QE, the environment variable takes precedence over the YAML entry:

```bash
export PSLIBRARY=/path/to/pslibrary
```

QE expects PSLibrary-style folders such as
`pbe/PSEUDOPOTENTIALS/` and `rel-pbe/PSEUDOPOTENTIALS/`.
The `suggested_qe_pseudos` mapping supplies element-specific selection patterns.

VASP expects a library root containing a PBE PAW directory, with files such as
`potpaw_PBE/Si/POTCAR`. Potentials must already be available in your library.

### Templates and Numerical Defaults

Edit the templates to change the input parameters and scripts you normally
use. Selected settings are subsequently overwritten by the corresponding
`set` operations.

The bundled numerical configuration includes:

```yaml
default_kppra: 12000
nscf_kppra_ratio: 4
default_cutoff_ratio: 1.5
```

These control generated k-grids and cutoffs. A generated cutoff is the
pseudopotential recommendation multiplied by `default_cutoff_ratio`;
these defaults do not establish convergence for a particular system.

### Clusters and Job Scripts

Each cluster entry defines a hostname substring, an MPI launch command, and
named scheduler headers. The bundled files contain Slurm SBATCH directives.
Adapt the placeholder clusters to your machines.

During `calc`, caddie detects the cluster, applies its first header preset,
and configures MPI calls in the generated scripts. The `mpi_executables`
list identifies executables that receive that launch command.
Use `caddie set header` afterwards to select a different header preset.

### Add Calculations or Flavors

Start from a similar entry in the
[bundled configuration](dftcaddie/resources/config.yaml):

1. Place the required templates under your user `templates/` directory.
2. Add a calculation or flavor with its display name, configurable choices,
   and code-to-template mapping.
3. Include the appropriate `master.sh` and preserve the template structure
   expected by the editing helpers.
4. Run `caddie config check --workflows`.

New recipes can reuse the existing QE and VASP operations. A new backend or
a new kind of input edit may also need Python implementation; adding a YAML
setting alone does not implement its effect.

## Shell Completion

Package installation does not modify shell configuration. Register completion
once by generating a file in Bash's standard per-user completion directory.

For a uv tool installation:

```bash
mkdir -p ~/.local/share/bash-completion/completions
uvx --from argcomplete register-python-argcomplete caddie \
    > ~/.local/share/bash-completion/completions/caddie
```

For a pip installation, run the generator while the caddie environment is
active:

```bash
mkdir -p ~/.local/share/bash-completion/completions
register-python-argcomplete caddie \
    > ~/.local/share/bash-completion/completions/caddie
```

Open a new terminal after generating the file. To enable it immediately, or on
a cluster that does not automatically load per-user completions, source it from
the current shell or `~/.bashrc`:

```bash
source ~/.local/share/bash-completion/completions/caddie
```

| Type, then press Tab | Suggestions |
| --- | --- |
| `caddie ` | Subcommands |
| `caddie calc -` | Short and long flags |
| `caddie calc --kind ` | Configured calculation kinds |
| `caddie calc --kind relax --flavor ` | Relaxation flavors |
| `caddie calc --kind bands --code ` | Codes available for bands |
| `caddie set ` | `system`, `pseudo`, and `header` |
| `caddie set header --cluster ` | Configured clusters |
| `caddie set header --cluster local --header ` | Headers for that cluster |
| `caddie set system ` | Filesystem paths |

Flags appear only after typing `-`. Press Tab twice to list multiple matches,
according to your shell's completion settings.

Commands and flags follow the parser automatically. Configuration choices are
read on each completion request, so edits do not require regenerating a script.
New options with custom dynamic values need a completion callback.

## Scripts and Agents

Supply full calculation keys and use configured defaults for unattended work:

```bash
caddie calc --kind bands --code quantum_espresso --structure ../Si.cif --auto
```

An empty destination directory avoids overwrite questions. Use `--overwrite`
only when you intend to replace existing calculation templates.

If a required choice or overwrite confirmation cannot be collected because
stdin or stdout is not a terminal, caddie exits with status 1 and a hint.
Cancelling a prompt or declining an overwrite stops preparation with status
130. All overwrite decisions are collected before copying templates.

The `set system` and `set pseudo` commands infer the calculation from files in the
current directory. Keep different calculations in separate directories.
Preparation is not transactional: failures during later setting steps can leave
partially configured files.

## Validation and Development

Check the active configuration:

```bash
caddie config check
caddie config check --workflows
```

The first checks configuration structure, referenced resources, calculation
ambiguity, k-path files, and configured pseudopotential directories. Optional
libraries that are not configured produce warnings; errors return status 1.

The workflow check prepares configured calculations in temporary directories,
using silicon and synthetic pseudopotentials. No DFT scripts are executed.
It checks preparation behavior, not scientific convergence or the contents
of your real pseudopotential libraries. Unimplemented backend-specific checks
are skipped.

From a development checkout:

```bash
uv sync
uv run pytest -q
```

Tests include command workflows, staged versus automatic preparation, repeated
configuration, interactive input, and shell completion. Workflow cases run in
fresh directories within a shared subprocess, with timeout handling.

### Code Organization

| Module | Responsibility |
| --- | --- |
| `cli.py`, `commands/set/__init__.py` | Top-level parsing and `set` command dispatch |
| `commands/set/system.py` | Structure, automatic k-grid, and k-path workflow |
| `commands/set/pseudo.py` | Pseudopotential selection and cutoff workflow |
| `commands/set/header.py` | Scheduler-header selection and replacement |
| `calculation.py` | Resolve preparation choices into a `CalculationSpec` |
| `prompts.py` | Typed selections, confirmations, and terminal checks |
| `completion.py` | Configuration-dependent shell completion |
| `file_management.py` | Template copying and input editing |
| `utils.py` | Detection, parsing, and other non-editing helpers |
| `config.py` | Lazy configuration loading and library resolution |
| `checks/` | Configuration and preparation validation |
| `resources/` | Bundled defaults, templates, headers, and k-paths |

Configuration is cached within a Python process. When editing it during a
long-running Python session, call `clear_config_cache()` before loading again:

```python
from dftcaddie.config import clear_config_cache, load_config

clear_config_cache()
settings, source_dir = load_config()
```

Functions use NumPy-style docstrings. See [LICENSE](LICENSE) for licensing
and [GitHub Issues](https://github.com/mgamigo/dftCaddie/issues) for bug reports
and feature requests.
