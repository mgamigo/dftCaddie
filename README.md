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

## Configuration

Interactive selections use Questionary typed prompts with vertical option lists
and single-column Tab completion, including over SSH. Enter an exact name or a
unique prefix, ignoring case; ambiguous prefixes require more characters.
Existing shortcut labels such as `[B]ands` are displayed as `Bands`;
configuration keys are also accepted. Boolean settings and overwrites use
yes/no confirmations.

For scripts and agents, supply calculation choices explicitly, for example:

```bash
caddie calc --kind bands --code quantum_espresso --auto --structure Si.cif
caddie sbatch --cluster local --header default
```

Configured defaults still apply. If a choice or overwrite confirmation is
needed without an interactive terminal, the command exits with status 1 and
instructions. Use `--overwrite` to explicitly allow replacement of calculation
templates. All overwrite confirmations happen before copying; declining one
or cancelling a prompt stops preparation with status 130. `--auto` and
`--pseudo` require `--structure FILE`.

`caddie config init` copies editable defaults to `~/.config/dftcaddie`.
Use `caddie config init --force` to replace existing config, templates, and headers.

`caddie config check` validates the user configuration when present, otherwise
the bundled defaults. It checks configuration structure, referenced templates
and headers, calculation ambiguity, bundled k-paths, and pseudopotential
directories. It reports the selected configuration path and returns status 1
for errors. Unconfigured optional pseudopotential libraries produce warnings.
It does not modify files or run calculations.

`caddie config check --workflows` additionally prepares every configured
calculation through calc, setup, pseudo, and each SBATCH preset. These runs use
temporary folders, a packaged copy of the silicon CIF fixture, and synthetic
pseudopotentials; no calculation scripts are executed. Real library paths are
still checked separately. Failed cases report their stage and make the command
return status 1.

Pytest calls the same `check_workflows(data, source_dir)` implementation with
bundled resources. Optional scenarios compare automatic preparation with staged
commands and check repeated configuration. Each case runs in a fresh process,
with a 60-second timeout, so configuration caches and cwd cannot leak between runs.
The configuration loader accepts `DFTCADDIE_CONFIG` and `DFTCADDIE_SOURCE_DIR`
overrides; workers set both to select their configuration snapshot and resource root.

Configuration selection and loading live in `dftcaddie.config`. Importing it
does not read YAML. Use `settings, source_dir = load_config()` to retrieve the
cached configuration, and `clear_config_cache()` to reload settings and library
paths after edits in a long-running Python session.

The standalone `caddie init` command has been replaced by `caddie config init`.
