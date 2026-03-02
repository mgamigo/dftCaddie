from importlib.resources import files as rfiles
import numpy
from collections import Counter
from dftcaddie.config import calculations


def test_templates_declared_in_config_exist():
    data_root = rfiles("dftcaddie") / "resources"
    missing: list[str] = []
    for kind, kind_cfg in calculations.items():
        files_by_code = kind_cfg.get("files")
        for code, template_files in files_by_code.items():
            code_dir = data_root / code

            if not code_dir.is_dir():
                missing.append(
                    f"- kind={kind!r}, code={code!r}: missing directory {str(code_dir)!r}"
                )
                continue

            for fname in template_files:
                path = code_dir / fname
                if not path.is_file():
                    missing.append(
                        f"- kind={kind!r}, code={code!r}: missing file {fname!r} at {str(path)!r}"
                    )
    assert not missing, "Missing packaged templates:\n" + "\n".join(missing)


def test_no_duplicate_template_names_per_kind_code():
    duplicates = []

    for kind, kind_cfg in calculations.items():
        for code, template_files in kind_cfg.get("files", {}).items():
            counts = Counter(template_files)
            dups = [name for name, n in counts.items() if n > 1]
            if dups:
                duplicates.append(f"- kind={kind!r}, code={code!r}: {dups}")

    assert not duplicates, "Duplicate template entries found:\n" + "\n".join(duplicates)


def test_qe_system_info_has_required_markers():
    sysinfo = rfiles("dftcaddie") / "resources" / "quantum_espresso" / "SYSTEM.INFO"
    text = sysinfo.read_text(encoding="utf-8")

    required = ["ATOMIC_SPECIES=", "ATOMIC_CRYST_POSITIONS=", "LATTICE=", "EOL"]
    missing = [x for x in required if x not in text]
    assert not missing, f"SYSTEM.INFO missing markers: {missing}"
