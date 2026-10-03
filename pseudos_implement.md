# Pseudopotential implementation roadmap

Use this file to track and revise the implementation plan. Mark a step
`[x] Completed` only after its work is finished. Completion status is tracked below.
Function names for new helpers are proposals.

## Design decisions

- Replace the existing QE pseudopotential configuration without backward
  compatibility or legacy fallbacks.
- Identify each configured library by name. Different providers, versions,
  semicore choices, or other preferences may share the same kind, exchange,
  and relativistic treatment.
- Each library defines its path and filename pattern, with optional element
  overrides and cutoff defaults. Exchange, kind, and relativity are not required
  configuration fields: read physical metadata from UPF files when needed.
- Library names are arbitrary identifiers, including descriptive names such as
  `pbesol-us-sr`. Never infer physical properties by parsing the name.
- Configure two defaults, `scalar` and `soc`. An explicit `--library` wins;
  otherwise choose the default according to whether SOC is requested. Both
  defaults may refer to the same fully relativistic library.
- Keep original library layouts and filenames; do not require users to copy
  or rename their pseudopotentials.
- Resolve files using the selected library and atomic species. Do not choose
  silently between multiple matches or fall back to another library.
- Keep the configuration resolver simple: lookup and path expansion only.
  Schema and directory validation belong to `caddie config check`.
- Keep optional `suggested_upf_pseudos` as preferences within the selected
  library. Missing suggestions do not prevent using that library.
- Put read-only resolution and parsing in `utils.py`; keep file editing in
  `file_management.py` and configuration resolution in `config.py`.
- Defer test creation and updates until the final step.

## Accepted configuration schema

Illustrative paths and patterns (verify against actual files before use):

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
```

Multiple libraries may share a directory and distinguish their files through
patterns or element overrides. Optional cutoff defaults and overrides will be
documented during implementation.

The `scalar` default means calculation without SOC, not a requirement to use a
strictly nonrelativistic pseudopotential. Fully relativistic potentials can
generally also be used without SOC. For ordinary collinear QE calculations,
`noncolin=.false.` and `lspinorb=.false.`; SOC requires both `.true.`.
Noncollinearity without SOC is also possible, so these remain distinct concepts.
Disabling SOC does not guarantee identical results to a separately generated
scalar-relativistic potential. Validate SOC support in the selected UPF files
whenever SOC is requested, including with an explicit library selection.

## Implementation steps

### 1. Library configuration and resolution — Completed

- [x] Completed: Replace `resolve_pslibrary()` with `resolve_upf_library(name)` in
  `config.py`, returning library settings, its name, and an absolute path
  without checking directory existence or validating the schema.
- [x] Completed: Define `upf_pseudopotentials` with `defaults.scalar`, `defaults.soc`, and
  `libraries` as shown above. Default validation is deferred to step 7.
- [x] Completed: Require only path and pattern per library; do not parse library names or
  require exchange/kind/relativity fields.
- [x] Completed: Define path expansion, filename placeholders, element overrides, and
  cutoff-default units and semantics.
- [x] Completed: Remove `qe_pslibrary` and QE `$PSLIBRARY` resolution. Retain
  `suggested_upf_pseudos` as optional filename-glob preferences, with library
  overrides for explicit choices.
- [x] Completed: Update `clear_config_cache()` for the new resolver.

### 2. UPF metadata parsing — Completed

- [x] Completed: Add `read_upf_pseudo_metadata(path)` in `utils.py`.
- [x] Completed: Read element, pseudopotential kind, functional, relativistic information,
  and recommended wavefunction/charge-density cutoffs when available.
- [x] Completed: Inspect representative PSLibrary and ONCVPSP files under `devtools/PSEUDOS`
  before settling the supported parsing formats.
- [x] Completed: Distinguish absent metadata from malformed values and normalize supported
  representations and units without guessing unsupported information.

### 3. Library-based file selection — Completed

- [x] Completed: Move `get_upf_pseudo_paths(library, symbols)` to `utils.py`;
  remove the old PSLibrary-specific helper from `file_management.py`.
- [x] Completed: Accept a resolved library definition and atomic species,
  without exchange/kind/relativistic arguments.
- [x] Completed: Return an element-to-Path mapping in first-occurrence order.
- [x] Completed: Apply exact element overrides first. Otherwise prefer the
  optional suggested-pseudo glob within the library-pattern matches, preserving
  version suffixes. Missing suggestions leave the original matches intact.
- [x] Completed: Raise FileNotFoundError for missing files. For ambiguity, issue
  UserWarning and select the first filename alphabetically, as requested.
- [x] Completed: Omit UPF metadata and physical-compatibility validation, as
  requested; selection is based on configured filenames only.
- [x] Completed: Select only files directly in the library directory.

### 4. Cutoff resolution — Completed

- [x] Completed: Add `get_qe_cutoffs(pseudos, *, defaults=None, ratio=1.5)`
  in `utils.py`, consuming the species-to-path mapping.
- [x] Completed: Read UPF cutoff recommendations as declared; optionally use
  caller-supplied ecutwfc/ecutrho defaults only when recommendations are missing.
  No cutoff defaults were added to config.yaml.
- [x] Completed: Report the missing species/value when no recommendation or
  default is available; do not introduce universal hardcoded cutoffs.
- [x] Completed: Use `yaiv.defaults.config.ureg` for units. Numeric defaults
  mean Ry; unit-bearing strings and ureg quantities are accepted. Take the
  maximum for each cutoff, apply the safety factor, and round upward.
- [x] Completed: Require positive finite values and safety factors. Warn when
  defaults are used; document defaults as convergence-test starting points.

### 5. SYSTEM.INFO and QE directory handling — Completed

- [x] Completed: Adapt `write_pseudos_to_system_info()` to consume the
  species-to-path mapping; obtain element symbols and masses from mapping keys.
- [x] Completed: Remove EXCHANGE from the QE template and its exports; exchange
  metadata is no longer needed for writing SYSTEM.INFO.
- [x] Completed: Write a shell-quoted absolute PSEUDO_DIR shared by the selected
  files, and export it through SYSTEM.INFO for the calculation scripts.
- [x] Completed: Remove the PSLIBRARY-based PSEUDO_DIR assignment in master.sh
  so it preserves the directory sourced from SYSTEM.INFO.

### 6. Cutoff writing — Completed

- [x] Completed: Make `configure_qe_cutoffs_from_pseudos()` a thin wrapper around
  `get_qe_cutoffs()`, writing the resolved CUTOFF and ECUTRHO values in Ry.
- [x] Completed: Resolve and validate both cutoffs before editing SYSTEM.INFO.

### 7. Library inspection, configuration checks, and documentation — Completed

- [x] Completed: Add a read-only `inspect_upf_library()` helper for path availability,
  matching files, ambiguities, and metadata problems.
- [x] Completed: Update production configuration validation for the new schema and remove
  obsolete QE settings from its checks. Validate library mappings, scalar/SOC
  default references, paths and directory existence, patterns, overrides,
  suggested-pseudo preferences, and cutoff defaults here rather than in the
  resolver.
- [x] Completed: Update the synthetic fixtures and command invocations used by the
  production workflow checker to exercise the new configuration.
- [x] Completed: Document named library selection, filename patterns, element overrides,
  cutoff defaults, scalar/SOC defaults, and examples for PSLibrary and ONCVPSP.

### 8. Shared workflow and automatic callers — Completed

- [x] Completed: Update `apply_pseudos()` to resolve the library and species, validate
  requested SOC support and cutoffs, then perform file edits. General physical
  compatibility remains the user’s responsibility.
- [x] Completed: Update `calc.run()` and `set.system.run()` to select `defaults.scalar` or
  `defaults.soc` according to the requested SOC mode for automatic preparation.
- [x] Completed: Review `set_spin_orbit_coupling()` integration: selecting a fully
  relativistic library and requesting SOC are distinct decisions.
- [x] Completed: Validate SOC support for every selected species when SOC is requested;
  allow the same fully relativistic library to serve both defaults.
- [x] Completed: Preserve appropriate VASP behavior while changing shared interfaces.

### 9. Command interface: caddie set pseudo — Completed

- [x] Completed: Update `add_arguments()` and `run()` last among the implementation steps.
- [x] Completed: Add named library selection through `--library`, taking precedence over
  the scalar/SOC defaults without implicitly changing the requested SOC mode.
- [x] Completed: Add `--list` showing configured library names, default roles, and directory
  availability; physical metadata is shown by `config check --pseudos`.
- [x] Completed: Expose library inspection through `caddie config check --pseudos`.
- [x] Completed: Allow listing/checking without a structure file or calculation directory.
- [x] Completed: Replace independent QE exchange/kind/relativity selectors with library
  selection for both QE and VASP; keep explicit SOC behavior.
- [x] Completed: Update affected command completion, help text, and usage documentation.

### 10. Tests and final verification — deferred until implementation is complete

- [ ] Create/update utility tests using representative small UPF fixtures for
  metadata, file matching, overrides, missing/ambiguous files, and cutoffs.
- [ ] Update configuration tests for named libraries and removed legacy settings.
- [ ] Cover scalar/SOC default selection, explicit library precedence, both
  defaults sharing one library, and validation of SOC support.
- [ ] Update file-editing tests to assert exact SYSTEM.INFO contents and verify
  generated scripts use the selected pseudopotential directory.
- [ ] Update command, automatic-workflow, resource, and completion tests for the
  new interfaces, including structure-free listing/checking and VASP coverage.
- [ ] Run the full pytest suite in the project environment and check CLI help
  and relevant command behavior. Resolve failures before marking this step done.

## Progress notes

- Step 1 revised: simple library lookup and path expansion, new bundled schema,
  optional suggested pseudos restored, and cache handling. Validation is deferred
  to `caddie config check` in step 7.
- Resolver smoke checks cover relative paths, preservation of filename patterns,
  independent returned settings, and resolution of paths that do not exist.
  No test files were created or updated.
- Full pytest currently stops during collection because `tests/test_config.py`
  references removed `resolve_pslibrary`. Existing QE workflow and configuration
  checker callers still need the later planned migration; step 1 is not an
  end-to-end working QE workflow.
- Step 2 completed with `read_upf_pseudo_metadata()` for attribute-based UPF 2
  headers only; provider-specific free text is not parsed. UPF 1 is explicitly unsupported.
  Missing data returns None; malformed booleans/cutoffs raise ValueError.
- Provider samples are now available in `devtools/PSEUDOS`. All 1,870 PSLibrary
  and 144 ONCVPSP files were parsed. The returned `type` preserves the UPF
  `pseudo_type` label (including USPP). Cutoff attributes are read as declared
  in Ry, without generator/version exceptions or physical validation. Missing
  or zero cutoffs remain None; no defaults have been added.
- Existing utility tests: 11 passed. Full pytest still stops at the pre-existing
  reference to removed resolve_pslibrary. No test files were created or updated.

- Step 3 completed. Real-library checks selected Si/O from scalar and fully
  relativistic PSLibrary and from ONCVPSP. Smoke checks covered ordering,
  duplicate species, suggestion preference/fallback, override precedence,
  missing overrides, and warning plus alphabetical selection for ambiguity.
- Corrected bundled PSLibrary example patterns to match rrkjus_psl filenames.
  Existing utility tests: 11 passed; no test files added or changed. Command
  callers and old tests still need migration in their scheduled steps.

- Steps 4–6 completed. Smoke checks covered real Si/O PSLibrary cutoffs,
  hartree/Ry fallback conversion, warning behavior, missing-cutoff failure
  without file modification, arbitrary pseudo filenames, and shell-quoted
  PSEUDO_DIR paths. Utility/resource tests: 28 passed. Full pytest remains
  blocked at collection by the old resolve_pslibrary test reference. No test
  files were added or changed; command integration remains in later steps.

- Steps 7–9 completed: `inspect_upf_library`, named-library configuration
  validation, migrated synthetic production workflows, automatic scalar/SOC
  defaults, explicit `--library`, `--soc`, `set pseudo --list` and `config check --pseudos`, library
  completion, CLI status propagation, and README documentation. VASP now uses
  named POTCAR libraries too; exchange/kind and `--relativistic` are removed.
- All 28 production workflow combinations passed across runs, including QE,
  VASP, automatic setup, and reconfiguration. Fixed checker assertions that
  assumed bands-specific filenames in relaxation calculations. Manual smoke
  checks confirmed real ONCVPSP inspection, missing-directory exit status,
  completion, library precedence, SOC support, and no edits on SOC rejection.
- Step 10 remains pending. No test files were created or modified, and the full
  pytest suite was not run during steps 7–9.

- Named libraries extended to POTCARs: `potcar_pseudopotentials` uses scalar/SOC
  defaults, paths, relative patterns such as `{element}/POTCAR`, and exact
  relative-path overrides. `resolve_potcar_library(name)` mirrors the simple,
  cached `resolve_upf_library(name)` (renamed from the QE-specific resolver).
- `get_potcar_paths(library, symbols)` moved to utils.py and preserves POSCAR
  species-group order, including separated repeats. No automatic bare/pv/sv
  preference: configure patterns and overrides explicitly. Inspection,
  configuration validation, completion, synthetic workflows, and documentation
  cover both formats. `set pseudo --library` replaces VASP exchange/kind flags.
- Step 10 remains deferred; no test files changed for this extension.
- POTCAR extension verified against `devtools/VASP_pseudos/PAW_PBE`: exact
  Ti_pv override, repeated species order, concatenated bytes, SOC settings,
  cache reuse, CLI inspection, config validation, and completion passed.
  All 28 production workflows also passed with named POTCAR libraries.

- Library inspection moved to `checks/pseudos.py` and is invoked through
  `caddie config check --pseudos`. Ordinary config checks stay lightweight;
  inspection uses the freshly validated YAML, not cached selection settings.
  `set pseudo --check` was removed; `--list` remains available there.

- Added optional `suggested_potcar_pseudos` (initial preference: Cs_sv/POTCAR).
  Priority: exact library override, existing suggested relative path/glob,
  library pattern. Unlike UPF preference filtering, POTCAR suggestions may
  select variants outside the pattern but remain inside the library root.
  Missing suggestions fall back; missing overrides fail. Configuration
  validation and library inspection follow the same preferences.
