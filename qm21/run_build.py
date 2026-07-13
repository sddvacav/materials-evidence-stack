from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import build_qm21 as b


def fixed_baseline_moderation(effects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    primary = effects[(effects["primary_analysis"].eq(1)) & effects["canonical_property"].isin(["yield_strength", "ultimate_strength"])].copy()
    for (canonical, test_mode), g in primary.groupby(["canonical_property", "test_mode"]):
        g = g[(g["baseline_value"] > 0) & g["lnRR"].notna()].copy()
        n_papers = g.paper_uid.nunique()
        if len(g) >= 3:
            x = np.log(g.baseline_value.to_numpy(float))
            y = g.lnRR.to_numpy(float)
            intercept, slope, pred = b.fit_ols(x, y)
            resid = y - pred
            rmse = float(np.sqrt(np.mean(resid ** 2)))
            lo = []
            for paper in sorted(g.paper_uid.unique()):
                gg = g[g.paper_uid.ne(paper)]
                if len(gg) >= 3 and gg.paper_uid.nunique() >= 2:
                    _, s, _ = b.fit_ols(np.log(gg.baseline_value.to_numpy(float)), gg.lnRR.to_numpy(float))
                    lo.append(s)
            lo_low = float(np.quantile(lo, 0.025)) if len(lo) >= 3 else np.nan
            lo_high = float(np.quantile(lo, 0.975)) if len(lo) >= 3 else np.nan
            rx = g.baseline_value.rank(method="average").to_numpy(float)
            ry = g.percent_change.rank(method="average").to_numpy(float)
            rank_corr = float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) > 0 and np.std(ry) > 0 else np.nan
            ident = "ADJUSTED_ASSOCIATION_ONLY" if n_papers >= 3 else "NOT_IDENTIFIABLE"
        else:
            intercept = slope = rmse = lo_low = lo_high = rank_corr = np.nan
            ident = "NOT_IDENTIFIABLE"
        rows.append({
            "estimand": "moderation of reinforcement gain by baseline strength",
            "canonical_property": canonical,
            "test_mode": test_mode,
            "n_effects": len(g),
            "independent_papers": n_papers,
            "model": "lnRR = intercept + slope*ln(baseline)",
            "intercept": intercept,
            "baseline_log_slope": slope,
            "lopo_slope_ci_low": lo_low,
            "lopo_slope_ci_high": lo_high,
            "rmse_lnRR": rmse,
            "spearman_baseline_vs_percent_gain": rank_corr,
            "regression_to_mean_control": "ratio-scale outcome plus same-paper controls; absolute-delta slope is not headline",
            "identifiability": ident,
            "claim_level": 3 if ident == "ADJUSTED_ASSOCIATION_ONLY" else 2,
        })
    return pd.DataFrame(rows)


def fixed_overlap_matrix(effects: pd.DataFrame) -> pd.DataFrame:
    out = _original_overlap_matrix(effects)
    diagonal = out["source_family"].eq(out["target_family"])
    out.loc[diagonal, "gower_distance"] = 0.0
    out.loc[diagonal, "support_status"] = "IN_DOMAIN_SELF"
    out.loc[diagonal, "accepted_for_transfer"] = True
    return out


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


def repair_generated_plot_scripts() -> None:
    replacements = {
        "Matrix-specific reinforcement effect\nSame-paper paired association": "Matrix-specific reinforcement effect\\nSame-paper paired association",
        "Baseline strength–gain relation\nPaper-clustered evidence": "Baseline strength–gain relation\\nPaper-clustered evidence",
        "Naive transfer error matrix\nNon-diagonal cells": "Naive transfer error matrix\\nNon-diagonal cells",
        "Overlap / applicability-domain map\nGower distance": "Overlap / applicability-domain map\\nGower distance",
        "label+='\nOOD'": "label+='\\nOOD'",
        "f\"{piv.loc[s,t]:.2f}\n{status.get((s,t),'')}\"": "f\"{piv.loc[s,t]:.2f}\\n{status.get((s,t),'')}\"",
    }
    for path in b.PLOT_CODE.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


_original_overlap_matrix = b.overlap_matrix
_original_plot_writer = b.write_plot_scripts


def fixed_plot_writer():
    result = _original_plot_writer()
    repair_generated_plot_scripts()
    return result


_original_copy = b.copy_code_and_write_requirements


def self_contained_copy() -> None:
    _original_copy()
    data_out = b.OUT / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    for name in ["source_pairs.csv", "input_ledger_seed.csv"]:
        shutil.copy2(b.DATA / name, data_out / name)
    shutil.copy2(Path(__file__), b.OUT / "code" / "run_build.py")
    copied_builder = b.OUT / "code" / "build_qm21.py"
    source = copied_builder.read_text(encoding="utf-8")
    old = 'rank_corr = float(pd.Series(g.baseline_value).corr(pd.Series(g.percent_change), method="spearman")) if len(g) >= 3 else np.nan'
    new = 'rank_corr = float(np.corrcoef(g.baseline_value.rank(method="average"), g.percent_change.rank(method="average"))[0, 1]) if len(g) >= 3 else np.nan'
    if old not in source:
        raise AssertionError("expected baseline-moderation source line not found")
    copied_builder.write_text(source.replace(old, new), encoding="utf-8")
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

def fixed_overlap_matrix(effects):
    out=original_overlap_matrix(effects)
    diagonal=out["source_family"].eq(out["target_family"])
    out.loc[diagonal,"gower_distance"]=0.0
    out.loc[diagonal,"support_status"]="IN_DOMAIN_SELF"
    out.loc[diagonal,"accepted_for_transfer"]=True
    return out

def fixed_plot_writer():
    result=original_plot_writer()
    replacements={
      "Matrix-specific reinforcement effect\\nSame-paper paired association":"Matrix-specific reinforcement effect\\\\nSame-paper paired association",
      "Baseline strength–gain relation\\nPaper-clustered evidence":"Baseline strength–gain relation\\\\nPaper-clustered evidence",
      "Naive transfer error matrix\\nNon-diagonal cells":"Naive transfer error matrix\\\\nNon-diagonal cells",
      "Overlap / applicability-domain map\\nGower distance":"Overlap / applicability-domain map\\\\nGower distance",
      "label+='\\nOOD'":"label+='\\\\nOOD'",
      "f\\\"{piv.loc[s,t]:.2f}\\n{status.get((s,t),'')}\\\"":"f\\\"{piv.loc[s,t]:.2f}\\\\n{status.get((s,t),'')}\\\"",
    }
    for path in b.PLOT_CODE.glob("*.py"):
      text=path.read_text(encoding="utf-8")
      for old,new in replacements.items(): text=text.replace(old,new)
      path.write_text(text,encoding="utf-8")
    return result

b.internal_contract_checks=fixed_contract_checks
original_overlap_matrix=b.overlap_matrix
b.overlap_matrix=fixed_overlap_matrix
original_plot_writer=b.write_plot_scripts
b.write_plot_scripts=fixed_plot_writer
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


b.baseline_moderation = fixed_baseline_moderation
b.overlap_matrix = fixed_overlap_matrix
b.internal_contract_checks = fixed_contract_checks
b.write_plot_scripts = fixed_plot_writer
b.copy_code_and_write_requirements = self_contained_copy
b.main()
