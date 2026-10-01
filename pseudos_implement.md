# QE pseudopotential implementation roadmap

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
- Keep optional `suggested_qe_pseudos` as preferences within the selected
  library. Missing suggestions do not prevent using that library.
- Put read-only resolution and parsing in `utils.py`; keep file editing in
  `file_management.py` and configuration resolution in `config.py`.
- Defer test creation and updates until the final step.

## Accepted configuration schema

Illustrative paths and patterns (verify against actual files before use):

```yaml
qe_pseudopotentials:
  defaults:
    scalar: pbesol-us-sr
    soc: pbesol-us-fr

  libraries:
    pbesol-us-sr:
      path: ~/Software/PSEUDOS/pslibrary/pbesol/PSEUDOPOTENTIALS
      pattern: "{element}.pbesol-*_us_psl.*.UPF"

    pbesol-us-fr:
      path: ~/Software/PSEUDOS/pslibrary/rel-pbesol/PSEUDOPOTENTIALS
      pattern: "{element}.rel-pbesol-*_us_psl.*.UPF"
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

- [x] Completed: Replace `resolve_pslibrary()` with `resolve_qe_library(name)` in
  `config.py`, returning library settings, its name, and an absolute path
  without checking directory existence or validating the schema.
- [x] Completed: Define `qe_pseudopotentials` with `defaults.scalar`, `defaults.soc`, and
  `libraries` as shown above. Default validation is deferred to step 7.
- [x] Completed: Require only path and pattern per library; do not parse library names or
  require exchange/kind/relativity fields.
- [x] Completed: Define path expansion, filename placeholders, element overrides, and
  cutoff-default units and semantics.
- [x] Completed: Remove `qe_pslibrary` and QE `$PSLIBRARY` resolution. Retain
  `suggested_qe_pseudos` as optional filename-glob preferences, with library
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

### 3. Library-based file selection

- [ ] Move and rework `get_qe_pseudo_paths(library, symbols)` in `utils.py`.
- [ ] Accept a resolved library definition and atomic species; remove the
  independent exchange, kind, and relativistic selection arguments.
- [ ] Return an element-to-`Path` mapping in first-occurrence species order.
- [ ] Apply explicit element overrides first. Otherwise find library-pattern
  matches, then prefer those matching the element's `suggested_qe_pseudos` glob
  if any exist. If none do, keep the original library matches. Preserve version
  suffixes; suggestions must never select a file outside the library matches.
- [ ] Require exactly one file per species; report missing files and ambiguous
  candidates with actionable context.
- [ ] Validate available UPF metadata against the requested species and check
  consistency across selected files; never infer metadata from library names.
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
  consume the species-to-path mapping and parsed UPF metadata as needed.
- [ ] Obtain element symbols and masses from mapping keys, and exchange from
  UPF metadata if still needed, rather than filenames or directory depth.
  Review whether `EXCHANGE` is still necessary once `PSEUDO_DIR` is explicit;
  remove it if it only served to construct the old directory path.
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
  removed QE settings from its checks. Validate library mappings, scalar/SOC
  default references, paths and directory existence, patterns, overrides,
  suggested-pseudo preferences, and cutoff defaults here rather than in the
  resolver.
- [ ] Update the synthetic fixtures and command invocations used by the
  production workflow checker to exercise the new configuration.
- [ ] Document named library selection, filename patterns, element overrides,
  cutoff defaults, scalar/SOC defaults, and examples for PSLibrary and ONCVPSP.

### 8. Shared workflow and automatic callers

- [ ] Update `apply_pseudos()` to resolve the library and species, validate
  selections and requested cutoffs, then perform file edits.
- [ ] Update `calc.run()` and `set.system.run()` to select `defaults.scalar` or
  `defaults.soc` according to the requested SOC mode for automatic preparation.
- [ ] Review `set_spin_orbit_coupling()` integration: selecting a fully
  relativistic library and requesting SOC are distinct decisions.
- [ ] Validate SOC support for every selected species when SOC is requested;
  allow the same fully relativistic library to serve both defaults.
- [ ] Preserve appropriate VASP behavior while changing shared interfaces.

### 9. Command interface: caddie set pseudo

- [ ] Update `add_arguments()` and `run()` last among the implementation steps.
- [ ] Add named library selection through `--library`, taking precedence over
  the scalar/SOC defaults without implicitly changing the requested SOC mode.
- [ ] Add `--list` showing configured library names, default roles, and directory
  availability; show physical metadata when available from UPF inspection.
- [ ] Expose library inspection through `--check`.
- [ ] Allow listing/checking without a structure file or calculation directory.
- [ ] Replace independent QE exchange/kind/relativity selectors with library
  selection; retain appropriate VASP options and explicit SOC behavior.
- [ ] Update affected command completion, help text, and usage documentation.

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
