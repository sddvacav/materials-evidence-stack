from __future__ import annotations

import shutil
from pathlib import Path

import build_qm21 as b


def fixed_contract_checks() -> list[str]:
    checks: list[str] = []
    for name in b.REQUIRED_FILES[:-2]:
        p = b.OUT / name
        if not p.exists() or p.stat().st_size == 0:
            raise AssertionError(f"missing required output: {name}")
        checks.append(f"PASS required:{name}")
    for stem in ["matrix_cate_caterpillar", "baseline_strength_gain", "transfer_error_matrix", "overlap_ad_map"]:
        for ext in ["svg", "pdf", "png"]:
            p = b.FIGURES / f"{stem}.{ext}"
            if not p.exists() or p.stat().st_size == 0:
                raise AssertionError(f"missing figure {p}")
            checks.append(f"PASS figure:{stem}.{ext}")
    verdict = (b.OUT / "00_EXECUTIVE_VERDICT.md").read_text(encoding="utf-8")
    if "STATUS: VALIDATED" in verdict or "production_model_registered=true" in verdict.lower():
        raise AssertionError("premature validation or production registration claim")
    checks.append("PASS no_premature_promotion")
    return checks


_original_copy = b.copy_code_and_write_requirements


def self_contained_copy() -> None:
    _original_copy()
    data_out = b.OUT / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    for name in ["source_pairs.csv", "input_ledger_seed.csv"]:
        shutil.copy2(b.DATA / name, data_out / name)
    shutil.copy2(Path(__file__), b.OUT / "code" / "run_build.py")
    reproduce = '''from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "code" / "build_qm21.py"
spec = importlib.util.spec_from_file_location("qm21_builder", MODULE_PATH)
b = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(b)

b.BASE = ROOT
b.DATA = ROOT / "data"
b.BUILD = ROOT / "build"
b.OUT = b.BUILD / "FINAL_QM21"
b.FIG_DATA = b.OUT / "figure_data"
b.PLOT_CODE = b.OUT / "plot_code"
b.FIGURES = b.OUT / "figures"

def fixed_contract_checks():
    checks=[]
    for name in b.REQUIRED_FILES[:-2]:
        p=b.OUT/name
        if not p.exists() or p.stat().st_size==0: raise AssertionError(f"missing {name}")
        checks.append(f"PASS required:{name}")
    for stem in ["matrix_cate_caterpillar","baseline_strength_gain","transfer_error_matrix","overlap_ad_map"]:
        for ext in ["svg","pdf","png"]:
            p=b.FIGURES/f"{stem}.{ext}"
            if not p.exists() or p.stat().st_size==0: raise AssertionError(f"missing {p}")
            checks.append(f"PASS figure:{stem}.{ext}")
    return checks
b.internal_contract_checks = fixed_contract_checks
b.main()
'''
    (b.OUT / "reproduce.py").write_text(reproduce, encoding="utf-8")
    acceptance = '''# Acceptance commands

```bash
python -m pip install -r requirements.lock
python reproduce.py
python -m unittest discover -s tests -v
sha256sum -c CHECKSUMS.sha256
```

`reproduce.py` rebuilds the recovery analysis under `build/FINAL_QM21`. Replace `data/*.csv` with canonical V29/Q40 inputs only after preserving their schema and hashes. The recovery package must not be promoted to Gold or a production registry.
'''
    (b.OUT / "acceptance_commands.md").write_text(acceptance, encoding="utf-8")


b.internal_contract_checks = fixed_contract_checks
b.copy_code_and_write_requirements = self_contained_copy
b.main()
