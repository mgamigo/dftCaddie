# dftCaddie

<div align="center">
<pre>
   '\                   .  .                        |>>
     \              .         ' .                   |
    O>>         .                 'o                |
     \       .                                      |
     /\    .                                        |
    / /  .'                  Don't shoot the caddie |
^^^^^^^`^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
</pre>

<p><strong>Prepare DFT calculation workflows from the terminal using your templates, defaults, and scripts.</strong></p>

<p>
  <a href="#features">Features</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#make-it-yours">Configuration</a> ·
  <a href="#shell-completion">Shell Completion</a> ·
  <a href="#examples">Examples</a>
</p>

<img src="/../assets/docs/assets/interactive.gif?raw=true" alt="Interactive dftCaddie preparation" width="928" />

</div>

## Features

For a full interactive run in a new folder:

```bash
mkdir new_calc
cd new_calc
caddie calc
```

The most useful command forms are:

- `caddie calc`: Fully interactive calculation setup.
  - `caddie calc --structure Si.cif`: Also writes the supplied structure.
  - `caddie calc --details --structure Si.cif`: Also asks about every setting.
  - `caddie calc --kind bands --code quantum_espresso`: Sets known choices.
  - `caddie calc --structure Si.cif --auto`: Also sets structure, k-points,
    pseudopotentials, and cutoffs.
  - `caddie -C /work/Si-bands calc ...`: Runs in another calculation directory.
- `caddie set`: Modifies an existing calculation.
  - `caddie set system Si.cif --autokgrid --kpath`: Sets the structure, k-grid,
    and k-path.
  - `caddie set pseudo Si.cif --configure`: Sets pseudopotentials and cutoffs.
  - `caddie set header`: Sets the scheduler header in `master.sh`.
- `caddie config`: Manages configuration and resources.
  - `caddie config init`: Creates an editable user configuration.
  - `caddie config check --workflows`: Checks configuration and workflows.

Caddie organizes the calculation workflow into `master.sh`, the top-level job
script intended for submission. It adds the selected scheduler header and calls
the calculation scripts in their configured order, for example an SCF step
followed by a bands or phonon step. Submit `master.sh` through your usual
cluster workflow; caddie prepares the job but does not submit or run it.

## Installation

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

### With pip

```bash
python -m venv ~/.venvs/dftcaddie
source ~/.venvs/dftcaddie/bin/activate
python -m pip install .
caddie --help
```

## Make It Yours

`caddie` comes with a bundled `config.yaml` and a set of resources: templates,
k-paths, and scheduler headers. The important part is that these are meant to
be edited and extended to represent your own calculation conventions.

You can add a code that caddie does not yet edit directly. In that case,
`caddie calc` can still copy and orchestrate its configured templates,
but actions behind `caddie set` require editing rules in Python.

To initialize your user configuration, run:

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
relative to `sbatch_headers/`.

Check that the configuration and its resources are installed correctly:

```bash
caddie config check --workflows
```

### Add a Recipe

1. Start from a similar entry in the [bundled config](dftcaddie/resources/config.yaml).
2. Add your input files under your user `templates/` directory.
3. Define the calculation's name, settings, flavors if needed, and template mapping.
4. Check the result with `caddie config check --workflows`.

Each calculation definition has a display name, a list of configurable
settings, and a mapping from code to template files. For example, a calculation
may be displayed as `Relax`, while its configuration key is `relax`.

The `code` setting is mandatory because it selects a backend and its template
set. The `files` mapping lists the templates copied into the calculation folder.
One of them is normally `master.sh`, the top-level script that caddie uses to
orchestrate the calculation scripts in order. It receives the scheduler header and
contains the calls to each individual script. `master.sh` itself is not added as a
sub-script, so it never invokes itself.

A calculation may also have **flavors**. A flavor is a named variation of a
workflow with its own defaults, configuration, and template mapping; it is not
just one more input setting. For example, `relax` has `fixed_cell` and
`variable_cell` flavors. Both are relaxation calculations, but the first uses
ionic relaxation while the second permits cell relaxation, so they can carry
different scripts and VASP/QE settings.

New recipes will reuse QE, VASP, and supported Wannier editing operations.

### Pseudopotential Libraries

Set the paths in your configuration:

```yaml
qe_pslibrary: /path/to/pslibrary
vasp_pseudopotentials: /path/to/vasp/potentials
```

QE uses `$PSLIBRARY` first, if set, and expects PSLibrary folders such as
`pbe/PSEUDOPOTENTIALS/` or `rel-pbe/PSEUDOPOTENTIALS/`. The
`suggested_qe_pseudos` mapping supplies preferred element-specific patterns.

VASP expects library subfolders matching the requested exchange and kind,
for example `potpaw_PBE/Si/POTCAR`. Potentials must already be installed.

### Numerical Defaults and Cluster Presets

```yaml
default_kppra: 12000
nscf_kppra_ratio: 4
default_cutoff_ratio: 1.5
```

These control the density of generated automatic k-grids and default cutoff
multipliers. Other numerical parameters live in the input templates.

Cluster entries define a hostname match, MPI launch command, and named header
presets. During `calc`, caddie applies the detected cluster's MPI command and
first header preset. Edit the bundled placeholder entries for your machines.


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

Open a new terminal. If your shell does not automatically load per-user Bash
completions, add this to `~/.bashrc`; it also enables completion immediately
when run in the current shell:

```bash
source ~/.local/share/bash-completion/completions/caddie
```

## Examples

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

### Scripts and Agents

Supply the full configuration keys to prepare a calculation without prompts.
The `-C` option makes the destination explicit, which is useful for scripts,
agents, and jobs launched from another directory:

```bash
mkdir -p /work/calculations/Si-bands
caddie -C /work/calculations/Si-bands calc \
    --kind bands \
    --code quantum_espresso \
    --structure /work/structures/Si.cif \
    --auto
```

Use a fresh directory for each calculation. If a template already exists,
caddie asks before replacing it; `--overwrite` accepts replacement for all
templates. When no interactive terminal is available, provide all required
choices explicitly. `--auto` and `--pseudo` always require `--structure FILE`.

The same command remains reproducible only while its templates, configuration,
structure file, and pseudopotential library remain the same. Caddie prepares
the input folder but does not establish scientific convergence or execute it.
