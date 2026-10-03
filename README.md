<a name="readme-top"></a>

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

<p><strong>Prepare DFT workflows your way, with your templates, defaults and cluster settings.</strong></p>

<p>
  <a href="#features">Features</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#shell-completion">Shell Completion</a> ·
  <a href="#make-it-yours">Configuration</a> ·
  <a href="#examples">Examples</a>
</p>

<img src="/../assets/docs/assets/interactive.gif?raw=true" alt="Live terminal demo: choose Bands, Quantum ESPRESSO, and SOC, then prepare inputs from a silicon structure." width="928" />

<p><em>Choose a workflow. Supply a structure. Prepare your calculation.</em></p>

</div>

## Features

Start with an empty calculation folder and let caddie ask for the missing choices:

```bash
mkdir Si-bands
cd Si-bands
caddie calc
```

Choose a calculation, code, and any required workflow variant by typing a name
or a matching part of it. Settings with defaults are applied automatically;
add `--details` to choose them interactively too.

- `caddie calc`: Choose interactively.
- `caddie calc --structure Si.cif`: Include your structure.
- `caddie calc --details --structure Si.cif`: Choose every setting.
- `caddie calc --kind bands --code quantum_espresso`: Supply known choices.
- `caddie calc --structure Si.cif --auto`: Also set k-points, pseudopotentials, and cutoffs.
- `caddie -C /work/Si-bands calc`: Work in another directory.

**Update an existing calculation**

- `caddie set system Si.cif --autokgrid --kpath`: Set the structure, k-grid, and k-path.
- `caddie set pseudo Si.cif --configure`: Set pseudopotentials and cutoffs.
- `caddie set cluster`: Configure the cluster header and MPI commands.

The bundled recipes cover **bands, relaxation, and phonons**, using Quantum
ESPRESSO or VASP where configured. All interaction stays in the terminal,
including on a cluster without a graphical session.

### From Templates to a Job

<p align="center">
  <img src="/../assets/docs/assets/workflow.svg?raw=true" alt="Templates, configuration and cluster settings, and an optional structure feed caddie calc. It prepares a calculation folder with input files and master.sh, which calls the workflow scripts in order." width="928" />
</p>

**`master.sh` orchestrates the workflow.** Caddie adds the selected scheduler
header and calls the calculation scripts in their configured order. Submit
it through your usual cluster workflow; caddie prepares the files but does
not submit or execute the calculation.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Installation

Requires **Python 3.10 or newer**. The package is `dftcaddie`; the terminal
command is `caddie`.

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
caddie --version
```

## Shell Completion

For **uv**, generate the Bash completion file once:

```bash
mkdir -p ~/.local/share/bash-completion/completions
uvx --from argcomplete register-python-argcomplete caddie \
    > ~/.local/share/bash-completion/completions/caddie
```

For **pip**, activate the installation environment and use:

```bash
mkdir -p ~/.local/share/bash-completion/completions
register-python-argcomplete caddie \
    > ~/.local/share/bash-completion/completions/caddie
```

Open a new terminal. If your shell does not load per-user Bash completions,
add the following to `~/.bashrc`. Run it in the current shell to enable
completion immediately:

```bash
source ~/.local/share/bash-completion/completions/caddie
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Make It Yours

**Your templates hold your input defaults.** `config.yaml` defines the available
workflows, connects them to templates, and describes your execution environment.
The bundled resources are a starting point for your own conventions.

<p align="center">
  <img src="/../assets/docs/assets/recipe.gif?raw=true" alt="Recipe walkthrough: Bands settings in config.yaml, the QE template mapping, and the generated master.sh loading SYSTEM.INFO before calling SCF, bands, and projection scripts in order." width="928" />
</p>

<p align="center"><em>From a configured recipe to an ordered workflow. Shown with bundled resources and a generated master.sh.</em></p>

<details>
<summary>View the recipe without animation</summary>

![Bands settings and defaults](/../assets/docs/assets/recipe-defaults.png?raw=true)
![Quantum ESPRESSO template mapping](/../assets/docs/assets/recipe-files.png?raw=true)
![Generated master script](/../assets/docs/assets/recipe-result.png?raw=true)

</details>

Create your editable copy:

```bash
caddie config init
```

This creates your editable resource tree:

```text
~/.config/dftcaddie/
    config.yaml         Recipes, choices, and shared settings
    templates/          Input files and calculation scripts
    sbatch_headers/     Scheduler header presets
    kpaths/             Stored high-symmetry paths
```

When your user `config.yaml` exists, caddie uses this resource tree instead of
the bundled one. Check your changes with:

```bash
caddie config check --workflows
```

### Define a Recipe

A **kind** identifies a workflow, such as `bands` or `relax`. A **flavor** is
a variant with its own configuration and files, such as `fixed_cell` or
`variable_cell`. The **code** selects the template set.

For example, this entry under `calculations` defines a minimal QE SCF recipe:

```yaml
calculations:
  scf:
    name: "Self-consistent"
    config:
      - name: code
        prompt: "Select code:"
        options:
          - quantum_espresso
    files:
      quantum_espresso:
        - quantum_espresso/scf.sh
        - quantum_espresso/SYSTEM.INFO
        - quantum_espresso/master.sh
```

Template paths are relative to `templates/`. Include `master.sh` and list the
other shell scripts in execution order. Start from the
[bundled configuration](dftcaddie/resources/config.yaml) for examples of
defaults, settings, and flavors.

New recipes can reuse the existing QE, VASP, and supported Wannier editing
operations. You can also configure templates for another code: caddie can
copy them and assemble the workflow, while code-specific edits require
Python support.

### Pseudopotential Libraries

Configure named UPF and POTCAR libraries without renaming or moving their files:

```yaml
upf_pseudopotentials:
  defaults:
    scalar: pbesol-us-sr
    soc: pbesol-us-fr
  libraries:
    pbesol-us-sr:
      path: ~/Software/PSEUDOS/pslibrary/pbesol/PSEUDOPOTENTIALS
      pattern: "{element}.pbesol-*rrkjus_psl.*.UPF"
    pbesol-us-fr:
      path: ~/Software/PSEUDOS/pslibrary/rel-pbesol/PSEUDOPOTENTIALS
      pattern: "{element}.rel-pbesol-*rrkjus_psl.*.UPF"
    oncv-pbe:
      path: ~/Software/PSEUDOS/ONCVPSP/nc-sr-pbe
      pattern: "{element}.upf"
      # Optional exact filename preferences:
      # overrides:
      #   Si: Si.upf
      # Optional fallbacks when UPF recommendations are missing:
      # cutoff_defaults:
      #   ecutwfc: "30 hartree"
      #   ecutrho: 240  # Bare numbers mean Ry.

suggested_potcar_pseudos:
  Cs: Cs_sv/POTCAR

potcar_pseudopotentials:
  defaults:
    scalar: paw-pbe
    soc: paw-pbe
  libraries:
    paw-pbe:
      path: ~/Software/VASP_pseudos/PAW_PBE
      pattern: "{element}/POTCAR"
      # Choose variants explicitly when needed:
      # overrides:
      #   Ti: Ti_pv/POTCAR
```

Library names are arbitrary labels. Paths expand `~`; relative paths are
resolved against the configuration directory. Patterns are case-sensitive
globs with `{element}` as the only placeholder. UPF patterns match filenames;
POTCAR patterns match relative paths such as `{element}/POTCAR`. Libraries can
share a directory and use different patterns. Potentials must already be installed.

Exact per-element `overrides` take priority. Otherwise, the optional global
`suggested_upf_pseudos` mapping prefers matching UPF filenames within the library's
matches, including version suffixes. If a suggestion is absent, ordinary
library matching applies. Multiple remaining matches issue a warning and use
the first filename alphabetically. Missing files produce an error.

`--library` selects a library in the format required by the calculation: UPF
for QE or POTCAR for VASP. Otherwise, each format uses its `scalar` default
without SOC or its `soc` default with SOC. Both defaults may name the same
library; a VASP library can serve both modes. Names do not control SOC: `--soc`
enables it and requires `has_so=True` for every selected UPF. Without it, the
command sets collinear, non-SOC inputs. Automatic `calc --pseudo/--auto` and
`set system --pseudo` use the calculation's SOC setting and corresponding
default library.

`--configure` reads UPF header cutoff recommendations. Missing recommendations
require explicit library `cutoff_defaults`; numeric defaults mean Ry, and
unit-bearing strings use the shared `ureg`. Defaults are used only for missing
values, with a warning. Each cutoff takes its maximum across species, applies
`--ratio` (or `default_cutoff_ratio`), and rounds upward in Ry. Recommendations
and defaults still require convergence testing; header values are read as
provided, without provider-specific corrections. `SYSTEM.INFO` records the
selected `PSEUDO_DIR`, species, and cutoffs; it no longer uses `EXCHANGE`.

```bash
# These work outside a calculation directory, without a structure:
caddie set pseudo --list
caddie config check --pseudos
caddie config check
```

`set pseudo --list` shows format, names, default roles, and path availability.
`config check` validates the schema and paths without reading potential headers.
Add `--pseudos` to inspect all configured UPF and POTCAR libraries, reporting
file counts, metadata, missing overrides, ambiguities, and parsing problems.
Inspection runs after configuration validation succeeds and returns a nonzero
status if issues are found. None of these commands edits pseudopotentials.
The optional `--workflows` check remains separate and uses synthetic potentials.

POTCAR library paths point directly to a family directory, such as `PAW_PBE`.
Patterns and exact relative-path overrides select variants; no automatic
`_pv`/`_sv` fallback is applied. The optional `suggested_potcar_pseudos` mapping
provides preferred relative paths or globs, such as `Cs: Cs_sv/POTCAR`.
Selection priority is an exact library override, then an existing suggestion,
then the library pattern. POTCAR suggestions can choose a variant outside the
normal pattern (`Cs_sv/POTCAR` instead of `Cs/POTCAR`), but always within the
selected library root. A missing suggestion falls back; a missing override
fails. The concatenated POTCAR follows POSCAR's
consecutive species groups, including repeated groups. VASP cutoff configuration
continues to use ENMAX in eV and the safety factor; UPF cutoff defaults do not
apply to POTCAR libraries. Both formats now use `--library`; `--exchange` and
`--kind` are removed from `set pseudo`.

Standalone listing spans both formats. If a name is shared by both,
`--library NAME --list` lists both; applying it uses the calculation's code.
Library inspection lives under `config check --pseudos`, not `set pseudo`.

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

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Examples

### Prepare a Complete Folder

With your pseudopotential library configured, keep choosing interactively
while caddie prepares the structure, k-grid, k-path, pseudopotentials, and
cutoffs:

```bash
caddie calc --structure Si.cif --auto
```

`--auto` uses configured defaults and requests cutoff configuration too.
`--details` lets you choose configurable settings interactively. `--pseudo`
requests pseudopotentials without also requesting a k-grid or k-path.
Both `--auto` and `--pseudo` require `--structure FILE`.

### Adjust an Existing Calculation

The `set` commands infer the calculation from the files in the target folder.

```bash
# Apply a structure and choose a denser k-grid.
caddie set system Si.cif --autokgrid --kppra 16000

# Insert a stored high-symmetry path.
caddie set system Si.cif --kpath

# Select a QE library, enable SOC, and configure cutoffs.
caddie set pseudo Si.cif --library pbesol-us-fr \
    --soc --configure --ratio 2.0

# Configure the cluster and choose a scheduler header interactively.
caddie set cluster
```

`--kppra` takes effect with `--autokgrid`; `--ratio` takes effect with
`--configure`. Without `--ratio`, cutoffs use `default_cutoff_ratio` from
configuration.

For VASP, select a POTCAR family with `--library paw-pbe`. For QE, select a
named UPF library with `--library`. `--soc` controls spin-orbit coupling
independently of library selection for both codes.

`set cluster` updates the scheduler header and MPI launch commands by default,
inferring the calculation kind and code to select its scripts. Header replacement
preserves the job body and current job name. Use `--no-header` to update only MPI
commands, or `--no-mpi` to update only the header. `--header` selects a named preset.

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

Use a fresh directory to avoid overwrite questions. `--overwrite` allows
replacement of existing templates. Without an interactive terminal, supply
all required choices and omit `--details` to use configured defaults.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
