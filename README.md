# dftCaddie

**Your calculations. Your templates. Your terminal.**

dftCaddie prepares DFT calculation folders using your preferred input files,
numerical defaults, and cluster scripts. Type your choices interactively over
SSH, then use the same preparation commands in scripts and agent workflows.
The package is `dftcaddie`; the command is **`caddie`**.

[Interactive Use](#start-interactively) · [Installation](#installation) ·
[Scripts and Agents](#scripts-and-agents) · [Configuration](#make-it-yours) ·
[Shell Completion](#shell-completion)

## Start Interactively

Inside a fresh calculation folder:

```bash
caddie calc
```

Choose the calculation and code by typing a name or a unique prefix. For
example, `ban` selects `Bands`, and `quantum` selects `quantum_espresso`.
Matching ignores case; Tab completes names. No arrow-key navigation is needed.

To choose settings such as spin-orbit coupling as well, and insert a structure:

```bash
caddie calc --details --structure Si.cif
```

![Actual interactive preparation: choose Bands, Quantum ESPRESSO, and SOC, then insert a silicon structure](/../assets/docs/assets/interactive.gif?raw=true)

This recording uses the bundled configuration. Your own calculation names,
flavors, and options appear when you customize it. Without `--details`, caddie
uses the configured defaults for settings that have them.

### Try It with Silicon

After [installing from the checkout](#installation), run:

```bash
mkdir -p ~/calculations/Si-demo
cp tests/data/Si.cif ~/calculations/Si-demo/
cd ~/calculations/Si-demo

caddie calc --details --structure Si.cif
caddie set system Si.cif --autokgrid --kpath
```

Select **Bands** and **quantum_espresso**. These commands copy the templates,
insert the structure, and set a k-grid and stored high-symmetry path. They need
no pseudopotential library for this demonstration. Before running DFT, configure
your [pseudopotentials](#pseudopotential-libraries) and inspect the inputs.

## What You Can Prepare

| Task | Caddie handles |
| --- | --- |
| Start a calculation | Copy the templates for its kind, flavor, and code |
| Adapt it to a material | Insert lattice vectors, atomic positions, and atom counts |
| Set reciprocal-space sampling | Generate automatic k-grids and insert stored k-paths |
| Select pseudopotentials | Resolve QE files or assemble a VASP POTCAR |
| Configure input settings | Apply SOC, cell relaxation, and recommended cutoffs |
| Prepare cluster scripts | Apply MPI commands and a scheduler header in `master.sh` |
| Check your recipes | Validate configuration and exercise preparation workflows |

Bundled recipes include **bands**, **fixed/variable-cell relaxation** for QE
and VASP, and **phonons** for QE. Your configuration can add more recipes and
reuse the existing editing operations.

Caddie prepares files; it does not run DFT, submit jobs, or track calculation
status. Review the results and launch them through your usual workflow.

## Installation

Requires Python **3.10+**. Clone the repository:

```bash
git clone https://github.com/mgamigo/dftCaddie.git
cd dftCaddie
```

### With uv

Install an isolated command without creating an environment manually:

```bash
uv tool install .
caddie --version
```

For development, use `uv tool install --editable .` so edits to the checkout
immediately affect the installed command.

### With pip

```bash
python -m venv ~/.venvs/dftcaddie
source ~/.venvs/dftcaddie/bin/activate
python -m pip install .
caddie --help
```

Installation includes YAIV, Questionary, and argcomplete. Supply your own
pseudopotential libraries, DFT executables, and cluster environment.

## Everyday Workflows

### Prepare a Complete Folder

With a pseudopotential library configured, you can keep choosing interactively
while caddie applies the structure, k-grid, k-path, and pseudopotentials:

```bash
caddie calc --structure Si.cif --auto
```

`--auto` uses configured defaults and requests cutoff configuration too.
`--details` lets you choose configurable settings interactively. `--pseudo`
requests pseudopotentials without also requesting a k-grid or k-path.
Both `--auto` and `--pseudo` require `--structure FILE`.

### Adjust an Existing Calculation

The `set` commands infer the calculation from the files in its folder:

```bash
# Apply a structure and choose a denser k-grid.
caddie set system Si.cif --autokgrid --kppra 16000

# Insert a stored high-symmetry path.
caddie set system Si.cif --kpath

# Select relativistic QE potentials and set cutoffs with an explicit factor.
caddie set pseudo Si.cif --exchange pbe --kind paw \
    --relativistic --configure --ratio 2.0

# Choose a scheduler header interactively.
caddie set header
```

`--kppra` takes effect with `--autokgrid`; `--ratio` takes effect with
`--configure`. Without `--ratio`, cutoffs use `default_cutoff_ratio` from
configuration.

For `set pseudo`, `--kind` means the **pseudopotential type**. Exchange and kind
are passed to both QE and VASP library lookup. `--relativistic` enables SOC and
selects relativistic QE potentials; omitting it disables SOC when applying
pseudopotentials.

`set header` preserves the job body and current job name. It selects the
cluster by hostname, falling back to `local`; you can supply both choices:

```bash
caddie set header --cluster local --header default
```

Changing a header does not update MPI commands in the sub-scripts.

### Work from Another Directory

Put the global `-C` / `--directory` option before the subcommand:

```bash
caddie -C ~/calculations/Si-bands set system /work/structures/Si.cif --autokgrid
```

The target directory must exist. Relative input paths are interpreted **inside
that directory**, so absolute structure paths are convenient for automation.

## Scripts and Agents

Provide full configuration keys to resolve choices without interactive input:

```bash
mkdir -p /work/calculations/Si-bands
caddie -C /work/calculations/Si-bands calc \
    --kind bands --code quantum_espresso \
    --structure /work/structures/Si.cif --auto
```

For a VASP variable-cell relaxation, configure the grid and pseudos in stages:

```bash
mkdir -p /work/calculations/Si-relax
caddie -C /work/calculations/Si-relax calc \
    --kind relax --flavor variable_cell --code vasp \
    --structure /work/structures/Si.cif
caddie -C /work/calculations/Si-relax set system \
    /work/structures/Si.cif --autokgrid
caddie -C /work/calculations/Si-relax set pseudo \
    /work/structures/Si.cif --configure
```

Configured defaults govern the remaining choices. For example, bundled bands
enable SOC by default, while relaxation and phonons disable it.

Use a separate, fresh folder for each calculation. When templates already
exist, caddie asks about each overwrite. Declining preserves that file for the
whole `calc` invocation. `--overwrite` replaces existing templates; explicit
`set` commands edit existing inputs.

When a structure is supplied, all structure-dependent edits use that structure.
Preserved files remain untouched; caddie does not substitute an existing POSCAR
for the supplied structure.

If a required answer cannot be collected without a terminal, caddie returns
status **1** with a hint. Cancelling a prompt returns **130**. Preparation is
not transactional: a later failure can leave partially configured files.

Repeatability depends on keeping the same request, configuration, templates,
structure, and pseudopotential library. Caddie does not freeze these resources
or establish scientific convergence for you.

## Make It Yours

```bash
caddie config init
```

This creates your editable resource tree:

```text
~/.config/dftcaddie/
    config.yaml
    templates/
    sbatch_headers/
    kpaths/
```

**Templates hold your input defaults.** `config.yaml` maps calculation kinds,
flavors, and codes to those templates and defines the choices exposed by the
client. A kind is a workflow such as `relax`; a flavor is a variation such as
`fixed_cell`; a code selects its backend.

When a user `config.yaml` exists, caddie uses that resource tree instead of the
bundled one. Template paths are relative to `templates/`; header paths are
relative to `sbatch_headers/`. Repeating `config init` preserves existing files.
`config init --force` replaces your configuration and resources.

### Pseudopotential Libraries

Set the paths in your configuration:

```yaml
qe_pslibrary: /path/to/pslibrary
vasp_pseudopotentials: /path/to/vasp/potentials
```

QE uses `$PSLIBRARY` first, if set, and expects PSLibrary folders such as
`pbe/PSEUDOPOTENTIALS/` or `rel-pbe/PSEUDOPOTENTIALS/`. The
`suggested_qe_pseudos` mapping supplies element-specific patterns.

VASP expects library subfolders matching the requested exchange and kind,
for example `potpaw_PBE/Si/POTCAR`. Potentials must already be installed.

### Defaults and Cluster Presets

```yaml
default_kppra: 12000
nscf_kppra_ratio: 4
default_cutoff_ratio: 1.5
```

These control generated k-grids and cutoff multipliers. Other numerical
parameters live in the input templates.

Cluster entries define a hostname match, MPI launch command, and named header
presets. During `calc`, caddie applies the detected cluster's MPI command and
first header preset. Edit the bundled placeholder entries for your machines.

### Add a Recipe

1. Start from a similar entry in the [bundled config](dftcaddie/resources/config.yaml).
2. Add your input files under your user `templates/` directory.
3. Define the calculation's name, settings, flavors if needed, and template mapping.
4. Preserve the markers used by the editing helpers and run the workflow checks.

New recipes can reuse QE, VASP, and supported Wannier editing operations.
New backend behavior or a new type of edit may require Python code as well as
configuration.

## Shell Completion

For a uv installation:

```bash
mkdir -p ~/.local/share/bash-completion/completions
uvx --from argcomplete register-python-argcomplete caddie \
    > ~/.local/share/bash-completion/completions/caddie
```

For pip, generate the same file with the environment activated:

```bash
mkdir -p ~/.local/share/bash-completion/completions
register-python-argcomplete caddie \
    > ~/.local/share/bash-completion/completions/caddie
```

Open a new terminal. If your cluster does not automatically load per-user Bash
completions, add this to `~/.bashrc`; it also enables completion immediately
when run in the current shell:

```bash
source ~/.local/share/bash-completion/completions/caddie
```

| Type, then press Tab twice | Suggestions |
| --- | --- |
| `caddie ` | Commands |
| `caddie set ` | `system`, `pseudo`, `header` |
| `caddie calc -` | Flags |
| `caddie calc --kind ` | Your configured kinds |
| `caddie calc --kind relax --flavor ` | Relaxation flavors |
| `caddie calc --kind bands --code ` | Available backend codes |
| `caddie -C ` | Directories |

Flags appear only after `-`. Commands and flags follow the parser; configured
choices are read on every completion request, so adding recipes does not
require regenerating the completion script.

## Checks and Development

```bash
caddie config check
caddie config check --workflows
```

Configuration checks inspect the schema and resources. Workflow checks prepare
calculations in temporary folders using silicon and synthetic potentials;
they do not launch DFT. They test preparation behavior, not convergence or
the contents of your real pseudopotential library.

From a checkout:

```bash
uv tool install --editable .
uv run pytest -q
```

`uv run` creates/synchronizes the project's development environment, including
pytest. With pip 25.1+, use `python -m pip install --editable . --group dev`.

See `caddie --help` and each subcommand's `--help` for the complete interface.
The GIF and [demo recorder](https://github.com/mgamigo/dftCaddie/blob/assets/docs/record_demo.py)
live on the separate `assets` branch. They are excluded from the normal source
checkout and source archive. A full Git clone can still fetch that branch;
use `git clone --single-branch` to fetch only the selected branch.

To regenerate the GIF, check out `assets` separately and run its recorder from
your development checkout, using the real CLI with isolated bundled resources:

```bash
uv run --with pexpect --with pyte --with pillow \
    python /path/to/assets/docs/record_demo.py "$PWD"
```

[License](LICENSE) · [Issues](https://github.com/mgamigo/dftCaddie/issues)
