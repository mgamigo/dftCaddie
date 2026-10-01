# QE pseudopotential implementation roadmap

Use this file to track and revise the implementation plan. Mark a step
`[x] Completed` only after its work is finished. All steps below are pending.
Function names for new helpers are proposals.

## Design decisions

- Replace the existing QE pseudopotential configuration without backward
  compatibility or legacy fallbacks.
- Identify each configured library by name. Different providers, versions,
  semicore choices, or other preferences may share the same kind, exchange,
  and relativistic treatment.
- Each library defines its path, exchange, kind, relativity, filename pattern,
  optional element overrides, and optional cutoff defaults.
- Keep original library layouts and filenames; do not require users to copy
  or rename their pseudopotentials.
- Resolve files using the selected library and atomic species. Do not choose
  silently between multiple matches or fall back to another library.
- Put read-only resolution and parsing in `utils.py`; keep file editing in
  `file_management.py` and configuration resolution in `config.py`.
- Defer test creation and updates until the final step.

## Implementation steps

### 1. Library configuration and resolution

- [ ] Replace `resolve_pslibrary()` with `resolve_qe_library(name)` in
  `config.py`, returning a validated library definition.
- [ ] Define `qe_pseudopotentials` with a default library name and a mapping of
  named libraries. Document required fields and optional settings.
- [ ] Use explicit relativity values: `scalar`, `full`, and `nonrelativistic`.
- [ ] Define path expansion, filename placeholders, element overrides, and
  cutoff-default units and semantics.
- [ ] Remove `qe_pslibrary`, QE `$PSLIBRARY` resolution, and global
  `suggested_qe_pseudos`; move element preferences into individual libraries.
- [ ] Update `clear_config_cache()` for the new resolver.

### 2. UPF metadata parsing

- [ ] Add `read_qe_pseudo_metadata(path)` in `utils.py`.
- [ ] Read element, pseudopotential kind, functional, relativistic information,
  and recommended wavefunction/charge-density cutoffs when available.
- [ ] Inspect representative PSLibrary and ONCVPSP files under `../PSEUDOS`
  before settling the supported parsing formats.
- [ ] Distinguish absent metadata from malformed values and normalize supported
  representations and units without guessing unsupported information.

### 3. Library-based file selection

- [ ] Move and rework `get_qe_pseudo_paths(library, symbols)` in `utils.py`.
- [ ] Accept a resolved library definition and atomic species; remove the
  independent exchange, kind, and relativistic selection arguments.
- [ ] Return an element-to-`Path` mapping in first-occurrence species order.
- [ ] Apply explicit element overrides before the library filename pattern.
- [ ] Require exactly one file per species; report missing files and ambiguous
  candidates with actionable context.
- [ ] Validate available UPF metadata against the species and library settings.
- [ ] Initially require selected files within a library to share a directory.

### 4. Cutoff resolution

- [ ] Add `get_qe_cutoffs(pseudos, *, defaults, ratio)` in `utils.py`.
- [ ] Resolve each cutoff for each species from a valid recommendation, using
  an explicitly configured library default when the recommendation is absent.
- [ ] Report the missing species/value if neither recommendation nor default
  is available; do not introduce universal hardcoded cutoffs.
- [ ] Normalize supported units to Ry, take the maximum across species, apply
  the safety factor, and round upward.
- [ ] Validate positive cutoff values and safety factors, and report when
  defaults were used. Document defaults as convergence-test starting points.

### 5. SYSTEM.INFO and QE directory handling

- [ ] Adapt `write_pseudos_to_system_info()` with minimal structural changes to
  consume the species-to-path mapping and explicit library metadata.
- [ ] Obtain element symbols and masses from mapping keys, and exchange from
  library metadata, rather than filenames or directory depth.
- [ ] Write the selected `PSEUDO_DIR` and ensure generated QE inputs use it.
- [ ] Update QE `SYSTEM.INFO` and `master.sh` templates to remove their
  `$PSLIBRARY` directory assumption and preserve the resolved directory.

### 6. Cutoff writing

- [ ] Simplify `configure_qe_cutoffs_from_pseudos()` into a wrapper around
  `get_qe_cutoffs()` that writes `CUTOFF` and `ECUTRHO`.
- [ ] Finish cutoff resolution and validation before editing the output file.

### 7. Library inspection, configuration checks, and documentation

- [ ] Add a read-only `inspect_qe_library()` helper for path availability,
  matching files, ambiguities, and metadata problems.
- [ ] Update production configuration validation for the new schema and remove
  old QE settings from its checks.
- [ ] Update the synthetic fixtures and command invocations used by the
  production workflow checker to exercise the new configuration.
- [ ] Document named library selection, filename patterns, element overrides,
  cutoff defaults, and examples for PSLibrary and ONCVPSP.

### 8. Shared workflow and automatic callers

- [ ] Update `apply_pseudos()` to resolve the library and species, validate
  selections and requested cutoffs, then perform file edits.
- [ ] Update `calc.run()` and `set.system.run()` to use the configured default
  QE library for automatic pseudopotential preparation.
- [ ] Review `set_spin_orbit_coupling()` integration: selecting a fully
  relativistic library and requesting SOC are distinct decisions.
- [ ] Preserve appropriate VASP behavior while changing shared interfaces.

### 9. Command interface: caddie set pseudo

- [ ] Update `add_arguments()` and `run()` last among the implementation steps.
- [ ] Add named library selection through `--library`.
- [ ] Add `--list` showing configured library names, physical metadata, and
  directory availability.
- [ ] Expose library inspection through `--check`.
- [ ] Allow listing/checking without a structure file or calculation directory.
- [ ] Replace independent QE exchange/kind/relativity selectors with library
  selection; retain appropriate VASP options and explicit SOC behavior.
- [ ] Update affected command completion, help text, and usage documentation.

### 10. Tests and final verification — deferred until implementation is complete

- [ ] Create/update utility tests using representative small UPF fixtures for
  metadata, file matching, overrides, missing/ambiguous files, and cutoffs.
- [ ] Update configuration tests for named libraries and removed legacy settings.
- [ ] Update file-editing tests to assert exact SYSTEM.INFO contents and verify
  generated scripts use the selected pseudopotential directory.
- [ ] Update command, automatic-workflow, resource, and completion tests for the
  new interfaces, including structure-free listing/checking and VASP coverage.
- [ ] Run the full pytest suite in the project environment and check CLI help
  and relevant command behavior. Resolve failures before marking this step done.

## Progress notes

- Roadmap created; implementation steps are pending.
- `../PSEUDOS` was not visible in the sandbox when this roadmap was prepared.
  Recheck its availability before implementing provider-specific parsing.
