from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import textwrap
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
BUILD = BASE / "build"
OUT = BUILD / "FINAL_QM21"
FIG_DATA = OUT / "figure_data"
PLOT_CODE = OUT / "plot_code"
FIGURES = OUT / "figures"
SNAPSHOT_PREFIX = "QM21_RECOVERY"

REQUIRED_FILES = [
    "00_EXECUTIVE_VERDICT.md", "INPUT_LEDGER.csv", "ANALYSIS_COHORT.csv",
    "PAIR_MATCHES.csv", "EFFECT_ESTIMATES.csv", "HIERARCHICAL_RESULTS.csv",
    "DOSE_RESPONSE.csv", "INTERACTION_EFFECTS.csv", "HETEROGENEITY.csv",
    "SENSITIVITY_ANALYSIS.csv", "NULL_NEGATIVE_RESULTS.csv", "CONFLICT_LEDGER.csv",
    "PROVENANCE.jsonl", "METHODS.md", "LIMITATIONS.md", "PLOT_SPECS.json",
    "WEB_TO_LOCAL_REQUEST.json", "LOCAL_ABSORPTION_PROMPT.md", "WINDOW_STATUS.json",
    "MATRIX_CATE.csv", "GRADE_TRANSFER_MATRIX.csv", "BASELINE_MODERATION.csv",
    "MATRIX_OVERLAP.csv", "MANIFEST.json", "CHECKSUMS.sha256",
]

NUMERIC_COLS = [
    "temperature_c", "strain_rate_s1", "dose_value", "beta_fraction_pct",
    "baseline_grain_um", "treated_grain_um", "baseline_value", "treated_value",
    "baseline_uncertainty", "treated_uncertainty", "primary_analysis",
]

STRENGTH_CANONICAL = {
    "YS": "yield_strength", "CYS": "yield_strength",
    "UTS": "ultimate_strength", "UCS": "ultimate_strength",
}

FAMILY_ORDER = ["cp-Ti", "Ti64", "near-alpha", "Ti65", "beta"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if pd.isna(x) else str(x) for x in parts).encode("utf-8")
    return f"{prefix}_{sha256_bytes(payload)[:20]}"


def ensure_clean() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    if BUILD.exists():
        for p in BUILD.iterdir():
            if p.name != "FINAL_QM21":
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
    for p in [OUT, FIG_DATA, PLOT_CODE, FIGURES, OUT / "code", OUT / "tests"]:
        p.mkdir(parents=True, exist_ok=True)


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    pairs_path = DATA / "source_pairs.csv"
    ledger_path = DATA / "input_ledger_seed.csv"
    if not pairs_path.exists() or not ledger_path.exists():
        raise FileNotFoundError("QM21 source cohort or input-ledger seed is missing")
    snapshot_material = pairs_path.read_bytes() + b"\n--LEDGER--\n" + ledger_path.read_bytes()
    snapshot_id = f"{SNAPSHOT_PREFIX}_{sha256_bytes(snapshot_material)[:16]}"
    pairs = pd.read_csv(pairs_path, keep_default_na=True)
    ledger = pd.read_csv(ledger_path, keep_default_na=True)
    for col in NUMERIC_COLS:
        if col in pairs.columns:
            pairs[col] = pd.to_numeric(pairs[col], errors="coerce")
    for col in pairs.columns:
        if col not in NUMERIC_COLS:
            pairs[col] = pairs[col].fillna("").astype(str)
    pairs["snapshot_id"] = snapshot_id
    pairs["sample_uid_control"] = [stable_id("sample", p, g, s, "control") for p, g, s in zip(pairs.paper_uid, pairs.grade, pairs.material_state)]
    pairs["sample_uid_treated"] = [stable_id("sample", p, g, s, r, d) for p, g, s, r, d in zip(pairs.paper_uid, pairs.grade, pairs.material_state, pairs.reinforcement_class, pairs.dose_value)]
    pairs["condition_uid"] = [stable_id("cond", p, s, t, m, r) for p, s, t, m, r in zip(pairs.paper_uid, pairs.material_state, pairs.temperature_c, pairs.test_mode, pairs.strain_rate_s1)]
    pairs["effect_uid"] = [stable_id("effect", x) for x in pairs.pair_id]
    pairs["source_hash"] = pairs["source_file_sha256"]
    missing_hash = pairs["source_hash"].eq("")
    pairs.loc[missing_hash, "source_hash"] = [
        sha256_bytes(f"{d}|{t}|{l}".encode("utf-8"))
        for d, t, l in zip(pairs.loc[missing_hash, "doi"], pairs.loc[missing_hash, "title"], pairs.loc[missing_hash, "source_locator"])
    ]
    pairs["source_hash_kind"] = np.where(missing_hash, "LOCATOR_METADATA_SHA256", "ORIGINAL_FILE_SHA256")
    ledger.insert(0, "snapshot_id", snapshot_id)
    return pairs, ledger, snapshot_id


def build_atomic_records(pairs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, r in pairs.iterrows():
        common = {
            "snapshot_id": r.snapshot_id,
            "paper_uid": r.paper_uid,
            "doi": r.doi,
            "source_hash": r.source_hash,
            "source_hash_kind": r.source_hash_kind,
            "matrix_family": r.matrix_family,
            "grade": r.grade,
            "material_state": r.material_state,
            "process_route": r.process_route,
            "condition_uid": r.condition_uid,
            "temperature_c": r.temperature_c,
            "test_mode": r.test_mode,
            "strain_rate_s1": r.strain_rate_s1,
            "property": r.property,
            "unit": r.unit,
            "evidence_grade": r.evidence_grade,
            "source_locator": r.source_locator,
        }
        control = dict(common)
        control.update({
            "record_uid": stable_id("record", r.effect_uid, "control"),
            "sample_uid": r.sample_uid_control,
            "arm": "matrix_control",
            "reinforcement_class": "none",
            "dose_value": 0.0,
            "dose_unit": r.dose_unit,
            "value": r.baseline_value,
            "uncertainty": r.baseline_uncertainty,
        })
        treated = dict(common)
        treated.update({
            "record_uid": stable_id("record", r.effect_uid, "treated"),
            "sample_uid": r.sample_uid_treated,
            "arm": "reinforced",
            "reinforcement_class": r.reinforcement_class,
            "dose_value": r.dose_value,
            "dose_unit": r.dose_unit,
            "value": r.treated_value,
            "uncertainty": r.treated_uncertainty,
        })
        rows.extend([control, treated])
    return pd.DataFrame(rows)


def compute_effects(pairs: pd.DataFrame) -> pd.DataFrame:
    e = pairs.copy()
    e["delta"] = e["treated_value"] - e["baseline_value"]
    valid_ratio = (e["baseline_value"] > 0) & (e["treated_value"] > 0)
    e["lnRR"] = np.where(valid_ratio, np.log(e["treated_value"] / e["baseline_value"]), np.nan)
    e["percent_change"] = np.where(valid_ratio, 100.0 * (np.exp(e["lnRR"]) - 1.0), np.nan)
    credible_vol = e["dose_unit"].eq("vol%") & e["dose_actuality"].isin(["MEASURED_TOTAL", "NOMINAL_PHASE_FRACTION"])
    e["unit_content_efficiency"] = np.where(credible_vol & (e["dose_value"] > 0), e["delta"] / e["dose_value"], np.nan)
    e["efficiency_eligibility"] = np.where(credible_vol, "ELIGIBLE_CONDITIONALLY", "INELIGIBLE_OR_SENSITIVITY")
    have_u = e["baseline_uncertainty"].notna() & e["treated_uncertainty"].notna()
    e["se_delta"] = np.where(have_u, np.sqrt(e["baseline_uncertainty"] ** 2 + e["treated_uncertainty"] ** 2), np.nan)
    e["delta_ci_low"] = e["delta"] - 1.96 * e["se_delta"]
    e["delta_ci_high"] = e["delta"] + 1.96 * e["se_delta"]
    e["claim_level"] = np.where(e["control_class"].eq("A"), 2, 1)
    e["causal_label"] = "same-paper paired association"
    e["canonical_property"] = e["property"].map(STRENGTH_CANONICAL).fillna(e["property"])
    return e


def aggregate_matrix_cate(effects: pd.DataFrame) -> pd.DataFrame:
    primary = effects[effects["primary_analysis"].eq(1)].copy()
    rows: list[dict[str, Any]] = []
    for (prop, test), global_g in primary.groupby(["canonical_property", "test_mode"], dropna=False):
        global_mean = global_g["lnRR"].dropna().mean()
        for family, g in global_g.groupby("matrix_family"):
            vals = g["lnRR"].dropna()
            n = len(vals)
            weight = n / (n + 2.0)
            fam_mean = vals.mean() if n else np.nan
            shrunk = weight * fam_mean + (1.0 - weight) * global_mean if n else np.nan
            n_papers = g["paper_uid"].nunique()
            rows.append({
                "estimand": "reinforcement CATE by matrix_family",
                "canonical_property": prop,
                "test_mode": test,
                "matrix_family": family,
                "n_effects": len(g),
                "independent_papers": n_papers,
                "median_delta": g["delta"].median(),
                "median_lnRR": vals.median() if n else np.nan,
                "median_percent_change": g["percent_change"].median(),
                "observed_min_percent": g["percent_change"].min(),
                "observed_max_percent": g["percent_change"].max(),
                "partial_pooling_weight": weight,
                "shrunk_lnRR": shrunk,
                "shrunk_percent_change": 100.0 * (math.exp(shrunk) - 1.0) if pd.notna(shrunk) else np.nan,
                "ci_low": np.nan,
                "ci_high": np.nan,
                "identifiability": "NOT_IDENTIFIABLE_AS_FAMILY_CATE" if n_papers < 2 else "DESCRIPTIVE_PARTIAL_POOLING",
                "confounding": "matrix_family is aliased with paper/process/dose in current cohort",
                "claim_level": 2,
            })
    return pd.DataFrame(rows)


def fit_ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float, np.ndarray]:
    X = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    return float(coef[0]), float(coef[1]), pred


def baseline_moderation(effects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    primary = effects[(effects["primary_analysis"].eq(1)) & effects["canonical_property"].isin(["yield_strength", "ultimate_strength"])].copy()
    for (canonical, test_mode), g in primary.groupby(["canonical_property", "test_mode"]):
        g = g[(g["baseline_value"] > 0) & g["lnRR"].notna()].copy()
        n_papers = g.paper_uid.nunique()
        if len(g) >= 3:
            x = np.log(g.baseline_value.to_numpy(float))
            y = g.lnRR.to_numpy(float)
            intercept, slope, pred = fit_ols(x, y)
            resid = y - pred
            rmse = float(np.sqrt(np.mean(resid ** 2)))
            lo = []
            for paper in sorted(g.paper_uid.unique()):
                gg = g[g.paper_uid.ne(paper)]
                if len(gg) >= 3 and gg.paper_uid.nunique() >= 2:
                    _, s, _ = fit_ols(np.log(gg.baseline_value.to_numpy(float)), gg.lnRR.to_numpy(float))
                    lo.append(s)
            lo_low = float(np.quantile(lo, 0.025)) if len(lo) >= 3 else np.nan
            lo_high = float(np.quantile(lo, 0.975)) if len(lo) >= 3 else np.nan
            rank_corr = float(pd.Series(g.baseline_value).corr(pd.Series(g.percent_change), method="spearman")) if len(g) >= 3 else np.nan
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


def gower_distance(a: pd.Series, b: pd.Series, numeric_ranges: dict[str, float], numeric_cols: list[str], categorical_cols: list[str]) -> tuple[float, int]:
    terms: list[float] = []
    shared = 0
    for col in numeric_cols:
        av, bv = a.get(col, np.nan), b.get(col, np.nan)
        if pd.isna(av) or pd.isna(bv):
            terms.append(0.5)
        else:
            rng = numeric_ranges.get(col, 0.0)
            terms.append(abs(float(av) - float(bv)) / rng if rng > 0 else 0.0)
            shared += 1
    for col in categorical_cols:
        av, bv = str(a.get(col, "")), str(b.get(col, ""))
        if not av or not bv:
            terms.append(0.5)
        else:
            terms.append(0.0 if av == bv else 1.0)
            shared += 1
    return float(np.mean(terms)) if terms else np.nan, shared


def overlap_matrix(effects: pd.DataFrame) -> pd.DataFrame:
    p = effects[(effects.primary_analysis.eq(1)) & effects.canonical_property.isin(["yield_strength", "ultimate_strength"])].copy()
    p["family"] = pd.Categorical(p.matrix_family, FAMILY_ORDER, ordered=True)
    centroid_rows = []
    for fam, g in p.groupby("matrix_family"):
        centroid_rows.append({
            "matrix_family": fam,
            "baseline_strength": g.baseline_value.median(),
            "temperature_c": g.temperature_c.median(),
            "dose_value": g.dose_value.median(),
            "beta_fraction_pct": g.beta_fraction_pct.median(),
            "baseline_grain_um": g.baseline_grain_um.median(),
            "test_mode": g.test_mode.mode().iloc[0] if not g.test_mode.mode().empty else "",
            "reinforcement_class": g.reinforcement_class.mode().iloc[0] if not g.reinforcement_class.mode().empty else "",
            "process_route": g.process_route.mode().iloc[0] if not g.process_route.mode().empty else "",
            "n_effects": len(g),
            "independent_papers": g.paper_uid.nunique(),
        })
    centroids = pd.DataFrame(centroid_rows).set_index("matrix_family")
    num = ["baseline_strength", "temperature_c", "dose_value", "beta_fraction_pct", "baseline_grain_um"]
    cat = ["test_mode", "reinforcement_class", "process_route"]
    ranges = {c: float(centroids[c].max() - centroids[c].min()) if centroids[c].notna().any() else 0.0 for c in num}
    rows = []
    for sf in FAMILY_ORDER:
        if sf not in centroids.index:
            continue
        for tf in FAMILY_ORDER:
            if tf not in centroids.index:
                continue
            dist, shared = gower_distance(centroids.loc[sf], centroids.loc[tf], ranges, num, cat)
            if sf == tf:
                status = "IN_DOMAIN_SELF"
            elif dist <= 0.35 and shared >= 5:
                status = "LIMITED_OVERLAP"
            elif dist <= 0.55:
                status = "LOW_OVERLAP"
            else:
                status = "OOD"
            rows.append({
                "source_family": sf,
                "target_family": tf,
                "gower_distance": dist,
                "shared_observed_features": shared,
                "support_status": status,
                "accepted_for_transfer": sf == tf,
                "missing_feature_penalty": 0.5,
                "features": ";".join(num + cat),
                "claim": "non-diagonal transfer is hypothesis-only unless overlap is independently established",
            })
    return pd.DataFrame(rows)


def transfer_matrix(effects: pd.DataFrame, overlap: pd.DataFrame) -> pd.DataFrame:
    p = effects[(effects.primary_analysis.eq(1)) & effects.canonical_property.isin(["yield_strength", "ultimate_strength"])].copy()
    family_effect = p.groupby(["matrix_family", "canonical_property"], as_index=False).agg(
        median_lnRR=("lnRR", "median"), source_effects=("effect_uid", "count"), source_papers=("paper_uid", "nunique")
    )
    target = p.groupby(["matrix_family", "canonical_property"], as_index=False).agg(
        target_baseline=("baseline_value", "median"), target_observed=("treated_value", "median"), target_effects=("effect_uid", "count"), target_papers=("paper_uid", "nunique")
    )
    support_lookup = overlap.set_index(["source_family", "target_family"])["support_status"].to_dict()
    rows = []
    for _, s in family_effect.iterrows():
        for _, t in target[target.canonical_property.eq(s.canonical_property)].iterrows():
            pred = float(t.target_baseline * math.exp(s.median_lnRR))
            abs_err = abs(pred - float(t.target_observed))
            rel_err = 100.0 * abs_err / float(t.target_observed) if t.target_observed else np.nan
            support = support_lookup.get((s.matrix_family, t.matrix_family), "OOD")
            self_transfer = s.matrix_family == t.matrix_family
            rows.append({
                "estimand": "source-grade to target-grade transfer error",
                "canonical_property": s.canonical_property,
                "source_family": s.matrix_family,
                "target_family": t.matrix_family,
                "source_median_lnRR": s.median_lnRR,
                "target_baseline": t.target_baseline,
                "predicted_target_treated": pred,
                "observed_target_treated": t.target_observed,
                "absolute_error": abs_err,
                "relative_error_pct": rel_err,
                "support_status": support,
                "accepted_transfer": bool(self_transfer),
                "validation_status": "SELF_RECONSTRUCTION" if self_transfer else "EXTRAPOLATION_ONLY",
                "independent_source_papers": int(s.source_papers),
                "independent_target_papers": int(t.target_papers),
                "claim_level": 1 if not self_transfer else 2,
            })
    return pd.DataFrame(rows)


def dose_response(effects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (paper, prop, state), g in effects[(effects.dose_value.notna()) & effects.primary_analysis.eq(1)].groupby(["paper_uid", "property", "material_state"]):
        g = g.sort_values("dose_value")
        if len(g) >= 2:
            slope = np.polyfit(g.dose_value, g.delta, 1)[0]
        else:
            slope = np.nan
        quadratic = np.nan
        turning = np.nan
        if len(g) >= 3 and g.dose_value.nunique() >= 3:
            co = np.polyfit(g.dose_value, g.delta, 2)
            quadratic = co[0]
            turning = -co[1] / (2 * co[0]) if co[0] != 0 else np.nan
        rows.append({
            "paper_uid": paper,
            "matrix_family": g.matrix_family.iloc[0],
            "grade": g.grade.iloc[0],
            "property": prop,
            "material_state": state,
            "dose_unit": g.dose_unit.iloc[0],
            "n_doses": g.dose_value.nunique(),
            "dose_min": g.dose_value.min(),
            "dose_max": g.dose_value.max(),
            "linear_delta_slope_per_dose": slope,
            "quadratic_coefficient": quadratic,
            "estimated_turning_dose": turning,
            "nonmonotonic_observed": bool((g.delta.diff().dropna() < 0).any()),
            "identifiability": "WITHIN_PAPER_DESCRIPTIVE_ONLY",
            "claim_level": 2,
        })
    return pd.DataFrame(rows)


def interactions(effects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    ti55 = effects[(effects.paper_uid == "LI2026_JMST") & effects.primary_analysis.eq(1)]
    for (dose, prop), g in ti55.groupby(["dose_value", "property"]):
        if set(g.material_state) >= {"as-received", "hot-forged"}:
            ar = float(g.loc[g.material_state.eq("as-received"), "delta"].iloc[0])
            hf = float(g.loc[g.material_state.eq("hot-forged"), "delta"].iloc[0])
            rows.append({
                "interaction": "hot_forging_x_TiBw",
                "paper_uid": "LI2026_JMST",
                "matrix_family": "near-alpha",
                "property": prop,
                "dose": dose,
                "contrast": hf - ar,
                "contrast_unit": g.unit.iloc[0],
                "interpretation": "difference-in-differences within one paper; matrix and composite both forged",
                "identifiability": "SAME_PAPER_QUASI_FACTORIAL",
                "claim_level": 2,
            })
    beta = effects[(effects.paper_uid == "RIELLI2020_MATCHAR") & effects.property.isin(["CYS", "UCS"])]
    for prop, g in beta.groupby("property"):
        g = g.sort_values("dose_value")
        peak = g.loc[g.treated_value.idxmax()]
        rows.append({
            "interaction": "beta_matrix_phase_partition_x_precursor_dose",
            "paper_uid": "RIELLI2020_MATCHAR",
            "matrix_family": "beta",
            "property": prop,
            "dose": peak.dose_value,
            "contrast": peak.treated_value - g.loc[g.dose_value.idxmax(), "treated_value"],
            "contrast_unit": "MPa",
            "interpretation": "intermediate dose outperforms highest dose; alpha reduction and beta softening compete with grain refinement",
            "identifiability": "WITHIN_PAPER_NONMONOTONIC",
            "claim_level": 2,
        })
    ti65 = effects[(effects.paper_uid == "TI65_INTERNAL_2026") & effects.property.isin(["UTS", "YS", "EL"])]
    for prop, g in ti65.groupby("property"):
        if g.temperature_c.nunique() >= 2:
            lo = g.sort_values("temperature_c").iloc[0]
            hi = g.sort_values("temperature_c").iloc[-1]
            rows.append({
                "interaction": "temperature_x_TiB2_derived_sensitivity",
                "paper_uid": "TI65_INTERNAL_2026",
                "matrix_family": "Ti65",
                "property": prop,
                "dose": hi.dose_value,
                "contrast": hi.delta - lo.delta,
                "contrast_unit": hi.unit,
                "interpretation": "sensitivity only; high-temperature absolute values reconstructed from rounded contrasts",
                "identifiability": "NOT_IDENTIFIABLE_PRIMARY",
                "claim_level": 1,
            })
    return pd.DataFrame(rows)


def heterogeneity(effects: pd.DataFrame, cate: pd.DataFrame) -> pd.DataFrame:
    rows = []
    p = effects[effects.primary_analysis.eq(1)]
    for (canon, test), g in p.groupby(["canonical_property", "test_mode"]):
        family_means = g.groupby("matrix_family").lnRR.mean().dropna()
        rows.append({
            "estimand": "cross-grade effect variance",
            "canonical_property": canon,
            "test_mode": test,
            "n_effects": len(g),
            "independent_papers": g.paper_uid.nunique(),
            "matrix_families": g.matrix_family.nunique(),
            "observed_between_family_variance_lnRR": family_means.var(ddof=1) if len(family_means) > 1 else np.nan,
            "observed_effect_range_lnRR": g.lnRR.max() - g.lnRR.min(),
            "random_slope_variance": np.nan,
            "random_slope_status": "NOT_IDENTIFIABLE_PAPER_FAMILY_ALIASING",
            "interpretation": "observed variance combines matrix family paper process dose morphology and test protocol",
            "claim_level": 2,
        })
    return pd.DataFrame(rows)


def hierarchical_results(cate: pd.DataFrame, effects: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (canon, test), g in cate.groupby(["canonical_property", "test_mode"]):
        rows.append({
            "model_id": stable_id("hier", canon, test),
            "formula": "lnRR ~ 1 + matrix_family + partial_pooling(matrix_family) + paper_intercept",
            "canonical_property": canon,
            "test_mode": test,
            "n_effects": int(g.n_effects.sum()),
            "independent_papers": int(g.independent_papers.sum()),
            "matrix_families": g.matrix_family.nunique(),
            "fit_status": "DESCRIPTIVE_EMPIRICAL_BAYES_ONLY",
            "random_intercept_variance": np.nan,
            "random_slope_variance": np.nan,
            "reason_not_identifiable": "one dominant independent paper per family; paper and matrix slope cannot be separated",
            "prediction_interval_status": "NOT_ESTIMABLE",
            "claim_level": 2,
        })
    return pd.DataFrame(rows)


def sensitivity_table(effects: pd.DataFrame, moderation: pd.DataFrame) -> pd.DataFrame:
    cp_el = effects[effects.pair_id.eq("LI2016_CP_HYB_EL")].iloc[0]
    rows = [
        {
            "analysis_id": "SENS_CP_EL_BASELINE_DEFINITION",
            "change": "replace Fig.6 control EL=29% with text EL=32.4%",
            "primary_result": cp_el.delta,
            "sensitivity_result": cp_el.treated_value - 32.4,
            "metric": "delta_EL_percentage_points",
            "decision": "direction and severe ductility penalty unchanged",
        },
        {
            "analysis_id": "SENS_Ti65_DERIVED_EXCLUSION",
            "change": "exclude reconstructed 650-700C Ti65 rows",
            "primary_result": int(effects.primary_analysis.sum()),
            "sensitivity_result": len(effects),
            "metric": "effect_rows_primary_vs_all",
            "decision": "headline family estimates use primary rows only",
        },
        {
            "analysis_id": "SENS_DOSE_CREDIBILITY",
            "change": "restrict unit-content efficiency to measured or nominal actual vol%",
            "primary_result": int(effects.efficiency_eligibility.eq("ELIGIBLE_CONDITIONALLY").sum()),
            "sensitivity_result": int(effects.dose_value.notna().sum()),
            "metric": "eligible_vs_dose_reported_rows",
            "decision": "precursor-dose and unresolved Ti64 hybrids barred from MPa/vol% headline",
        },
        {
            "analysis_id": "SENS_FAMILY_PAPER_ALIAS",
            "change": "require at least two independent papers per matrix family",
            "primary_result": 0,
            "sensitivity_result": effects.matrix_family.nunique(),
            "metric": "families_identifiable_vs_observed",
            "decision": "true matrix-family CATE remains NOT_IDENTIFIABLE",
        },
    ]
    for _, r in moderation.iterrows():
        rows.append({
            "analysis_id": f"LOPO_{r.canonical_property}_{r.test_mode}",
            "change": "leave-one-paper-out baseline moderation",
            "primary_result": r.baseline_log_slope,
            "sensitivity_result": f"[{r.lopo_slope_ci_low},{r.lopo_slope_ci_high}]",
            "metric": "lnRR_vs_log_baseline_slope",
            "decision": r.identifiability,
        })
    return pd.DataFrame(rows)


def conflict_ledger() -> pd.DataFrame:
    return pd.DataFrame([
        {"conflict_id": "C001", "object": "LI2016 cp-Ti control elongation", "source_a": "Fig.6: 29±2%", "source_b": "text: 32.4%", "resolution": "primary uses figure value; text alternative retained in sensitivity", "status": "OPEN_NONCRITICAL"},
        {"conflict_id": "C002", "object": "Bhat Ti64 actual phase fraction", "source_a": "nominal alloy chemistry", "source_b": "partial TiB estimate; coarse-primary contribution unresolved", "resolution": "bar hybrids and partial TiB from universal unit-content coefficient", "status": "OPEN_HIGH_IMPACT"},
        {"conflict_id": "C003", "object": "Ti65 650-700C absolute values", "source_a": "rounded delta and percent change", "source_b": "authoritative atomic rows absent", "resolution": "reconstructed values retained as sensitivity only", "status": "OPEN_HIGH_IMPACT"},
        {"conflict_id": "C004", "object": "matrix family versus paper identity", "source_a": "five families", "source_b": "one dominant paper/source per family", "resolution": "do not estimate causal family random slope", "status": "STRUCTURAL_NONIDENTIFIABILITY"},
        {"conflict_id": "C005", "object": "Beta21S dose monotonicity", "source_a": "grain size refines continuously", "source_b": "strength peaks at 1.5 wt% B4C then falls", "resolution": "retain nonmonotonic response and mechanism competition", "status": "RESOLVED_AS_REAL_HETEROGENEITY"},
    ])


def null_negative_results() -> pd.DataFrame:
    return pd.DataFrame([
        {"result_id": "N001", "question": "universal matrix-family CATE", "result": "NOT_IDENTIFIABLE", "reason": "paper-family aliasing and no replicated family across independent papers", "implication": "do not rank families causally"},
        {"result_id": "N002", "question": "universal cross-grade transfer model", "result": "REJECTED", "reason": "non-diagonal overlap is low or OOD", "implication": "transfer outputs are hypotheses only"},
        {"result_id": "N003", "question": "monotonic reinforcement dose response", "result": "FALSIFIED_IN_BETA21S", "reason": "1.5 wt% B4C exceeds 3 wt% for CYS and UCS", "implication": "phase partition and matrix softening must be modeled"},
        {"result_id": "N004", "question": "strength gain without plasticity cost", "result": "GENERALLY_NOT_SUPPORTED", "reason": "large EL losses in cp-Ti Ti64 near-alpha and Ti65 RT", "implication": "architecture and matrix deformation reserve are first-order"},
        {"result_id": "N005", "question": "Ti65 high-temperature EL reversal proves toughening", "result": "NOT_SUPPORTED", "reason": "derived rows lack authoritative absolute records and matrix softening is a competing explanation", "implication": "retain as sensitivity only"},
    ])


def write_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, float_format="%.10g")


def write_plot_scripts() -> dict[str, dict[str, str]]:
    common = """import argparse\nfrom pathlib import Path\nimport matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\nimport numpy as np\nimport pandas as pd\n\ndef save(fig, prefix):\n    p=Path(prefix); p.parent.mkdir(parents=True, exist_ok=True)\n    fig.savefig(str(p)+'.svg', bbox_inches='tight')\n    fig.savefig(str(p)+'.pdf', bbox_inches='tight')\n    fig.savefig(str(p)+'.png', dpi=600, bbox_inches='tight')\n"""
    scripts: dict[str, str] = {}
    scripts["plot_matrix_cate.py"] = common + """
p=argparse.ArgumentParser(); p.add_argument('--data',required=True); p.add_argument('--out-prefix',required=True); a=p.parse_args()
d=pd.read_csv(a.data)
d=d.sort_values('order')
fig,ax=plt.subplots(figsize=(8.2,4.8))
y=np.arange(len(d))
x=d['median_percent_change'].to_numpy(float)
lo=x-d['observed_min_percent'].to_numpy(float); hi=d['observed_max_percent'].to_numpy(float)-x
ax.errorbar(x,y,xerr=np.vstack([lo,hi]),fmt='o',capsize=4)
ax.axvline(0,linewidth=1)
ax.set_yticks(y,d['matrix_family'])
ax.set_xlabel('Median change in ultimate strength (%)')
ax.set_title('Matrix-specific reinforcement effect\nSame-paper paired association; range is observed support, not a causal CI')
for yi,row in d.reset_index(drop=True).iterrows(): ax.text(row['observed_max_percent']+1,yi,f"{int(row['independent_papers'])} paper, {int(row['n_effects'])} effects",va='center',fontsize=8)
ax.grid(axis='x',alpha=.25); fig.tight_layout(); save(fig,a.out_prefix)
"""
    scripts["plot_baseline_strength_gain.py"] = common + """
p=argparse.ArgumentParser(); p.add_argument('--data',required=True); p.add_argument('--out-prefix',required=True); a=p.parse_args()
d=pd.read_csv(a.data)
fig,ax=plt.subplots(figsize=(8.2,5.2))
for fam,g in d.groupby('matrix_family'):
    ax.scatter(g['baseline_value'],g['percent_change'],label=fam,s=42)
if len(d)>=3:
    x=np.log(d['baseline_value'].to_numpy(float)); y=d['lnRR'].to_numpy(float); c=np.polyfit(x,y,1)
    xx=np.linspace(d['baseline_value'].min(),d['baseline_value'].max(),200); yy=100*(np.exp(c[0]*np.log(xx)+c[1])-1)
    ax.plot(xx,yy,linewidth=1.5,label='pooled adjusted association')
ax.axhline(0,linewidth=1); ax.set_xlabel('Matrix baseline strength (MPa)'); ax.set_ylabel('Reinforcement gain (%)')
ax.set_title('Baseline strength–gain relation\nPaper-clustered evidence; slope is not causal')
ax.legend(fontsize=8,ncol=2); ax.grid(alpha=.25); fig.tight_layout(); save(fig,a.out_prefix)
"""
    scripts["plot_transfer_error_matrix.py"] = common + """
p=argparse.ArgumentParser(); p.add_argument('--data',required=True); p.add_argument('--out-prefix',required=True); a=p.parse_args()
d=pd.read_csv(a.data); families=list(dict.fromkeys(d['source_family'].tolist()))
piv=d.pivot(index='source_family',columns='target_family',values='relative_error_pct').reindex(index=families,columns=families)
fig,ax=plt.subplots(figsize=(7,6)); im=ax.imshow(piv.to_numpy(float))
ax.set_xticks(range(len(families)),families,rotation=45,ha='right'); ax.set_yticks(range(len(families)),families)
ax.set_xlabel('Target matrix family'); ax.set_ylabel('Source matrix family'); ax.set_title('Naive transfer error matrix\nNon-diagonal cells are extrapolation-only')
status=d.set_index(['source_family','target_family'])['validation_status'].to_dict()
for i,s in enumerate(families):
  for j,t in enumerate(families):
    v=piv.loc[s,t]
    label=f"{v:.1f}%" if np.isfinite(v) else 'NA'
    if status.get((s,t))!='SELF_RECONSTRUCTION': label+='\nOOD'
    ax.text(j,i,label,ha='center',va='center',fontsize=7)
fig.colorbar(im,ax=ax,label='Relative prediction error (%)'); fig.tight_layout(); save(fig,a.out_prefix)
"""
    scripts["plot_overlap_ad_map.py"] = common + """
p=argparse.ArgumentParser(); p.add_argument('--data',required=True); p.add_argument('--out-prefix',required=True); a=p.parse_args()
d=pd.read_csv(a.data); families=list(dict.fromkeys(d['source_family'].tolist()))
piv=d.pivot(index='source_family',columns='target_family',values='gower_distance').reindex(index=families,columns=families)
fig,ax=plt.subplots(figsize=(7,6)); im=ax.imshow(piv.to_numpy(float),vmin=0,vmax=1)
ax.set_xticks(range(len(families)),families,rotation=45,ha='right'); ax.set_yticks(range(len(families)),families)
ax.set_xlabel('Target matrix family'); ax.set_ylabel('Source matrix family'); ax.set_title('Overlap / applicability-domain map\nGower distance with explicit missing-feature penalty')
status=d.set_index(['source_family','target_family'])['support_status'].to_dict()
for i,s in enumerate(families):
  for j,t in enumerate(families): ax.text(j,i,f"{piv.loc[s,t]:.2f}\n{status.get((s,t),'')}",ha='center',va='center',fontsize=6.5)
fig.colorbar(im,ax=ax,label='Distance (0=in-domain, 1=far)'); fig.tight_layout(); save(fig,a.out_prefix)
"""
    for name, content in scripts.items():
        (PLOT_CODE / name).write_text(content, encoding="utf-8")
    return {name: {"path": f"plot_code/{name}"} for name in scripts}


def make_figure_data(effects: pd.DataFrame, cate: pd.DataFrame, transfer: pd.DataFrame, overlap: pd.DataFrame) -> None:
    ultimate = cate[(cate.canonical_property == "ultimate_strength")].copy()
    ultimate["order"] = ultimate.matrix_family.map({x: i for i, x in enumerate(FAMILY_ORDER)})
    ultimate.sort_values("order").to_csv(FIG_DATA / "matrix_cate_caterpillar.csv", index=False)
    baseline = effects[(effects.primary_analysis.eq(1)) & effects.canonical_property.isin(["yield_strength", "ultimate_strength"])].copy()
    baseline[["effect_uid", "paper_uid", "matrix_family", "grade", "canonical_property", "test_mode", "baseline_value", "treated_value", "lnRR", "percent_change", "evidence_grade"]].to_csv(FIG_DATA / "baseline_strength_gain.csv", index=False)
    t = transfer[transfer.canonical_property.eq("ultimate_strength")].copy()
    t["source_family"] = pd.Categorical(t.source_family, FAMILY_ORDER, ordered=True)
    t["target_family"] = pd.Categorical(t.target_family, FAMILY_ORDER, ordered=True)
    t.sort_values(["source_family", "target_family"]).to_csv(FIG_DATA / "transfer_error_matrix.csv", index=False)
    o = overlap.copy()
    o["source_family"] = pd.Categorical(o.source_family, FAMILY_ORDER, ordered=True)
    o["target_family"] = pd.Categorical(o.target_family, FAMILY_ORDER, ordered=True)
    o.sort_values(["source_family", "target_family"]).to_csv(FIG_DATA / "overlap_ad_map.csv", index=False)


def execute_plots() -> None:
    jobs = [
        ("plot_matrix_cate.py", "matrix_cate_caterpillar.csv", "matrix_cate_caterpillar"),
        ("plot_baseline_strength_gain.py", "baseline_strength_gain.csv", "baseline_strength_gain"),
        ("plot_transfer_error_matrix.py", "transfer_error_matrix.csv", "transfer_error_matrix"),
        ("plot_overlap_ad_map.py", "overlap_ad_map.csv", "overlap_ad_map"),
    ]
    for script, data, prefix in jobs:
        subprocess.run([
            sys.executable, str(PLOT_CODE / script), "--data", str(FIG_DATA / data),
            "--out-prefix", str(FIGURES / prefix),
        ], check=True)


def write_reports(snapshot_id: str, effects: pd.DataFrame, cate: pd.DataFrame, transfer: pd.DataFrame, overlap: pd.DataFrame, conflicts: pd.DataFrame) -> None:
    primary = effects[effects.primary_analysis.eq(1)]
    def eff(pid: str) -> pd.Series:
        return effects.loc[effects.pair_id.eq(pid)].iloc[0]
    cp_ys, cp_uts, cp_el = eff("LI2016_CP_HYB_YS"), eff("LI2016_CP_HYB_UTS"), eff("LI2016_CP_HYB_EL")
    t64_ys, t64_uts, t64_el = eff("BHAT2000_TIB_YS"), eff("BHAT2000_TIB_UTS"), eff("BHAT2000_TIB_EL")
    ti65_uts, ti65_el = eff("TI65_RT_UTS"), eff("TI65_RT_EL")
    verdict = f"""# QM21 Executive Verdict

`WINDOW=QM21 | SNAPSHOT={snapshot_id} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Quantitative verdict

The requested pure **matrix-family CATE is not identifiable** from the current frozen recovery cohort. Each of cp-Ti, Ti64, near-α/Ti55, Ti65 and β/Beta21S is dominated by a different paper or internal source, process route, reinforcement architecture, dose scale and in one case test mode. The partial-pooling table therefore reports descriptive shrinkage only; it does not estimate a causal family coefficient.

1. **cp-Ti, 13.66 vol.% TiC+TiB:** YS changes by {cp_ys.delta:.0f} MPa ({cp_ys.percent_change:.1f}%), UTS by {cp_uts.delta:.0f} MPa ({cp_uts.percent_change:.1f}%), while elongation changes by {cp_el.delta:.1f} percentage points using the figure baseline. This is a high-volume hybrid reinforcement, not a pure TiB slope.
2. **Ti-6Al-4V:** the figure-derived TiB comparison changes YS by {t64_ys.delta:.0f} MPa ({t64_ys.percent_change:.1f}%), UTS by {t64_uts.delta:.0f} MPa ({t64_uts.percent_change:.1f}%), and elongation by {t64_el.delta:.1f} percentage points. The actual total TiB fraction remains partially unresolved, so a universal MPa/vol.% value is prohibited.
3. **near-α Ti55:** 3.5–7.0 vol.% network TiBw raises room-temperature YS and UTS in both as-received and hot-forged states, but the plasticity cost depends strongly on dose and state. Hot forging creates bimodal α grains and high GND density in both matrix and composite; the source attributes only a minor 13.9–18.6 MPa increment to TiBw rotation, while grain refinement and dislocations dominate the forging increment.
4. **β Beta21S:** the response is non-monotonic. CYS/UCS peak at 1.5 wt.% B4C precursor and decline at 3 wt.% despite stronger grain refinement. Matrix phase partition and β softening therefore override a monotonic reinforcement-only narrative.
5. **Ti65 +3W background:** 1.8 wt.% TiB2 changes RT UTS by {ti65_uts.delta:.2f} MPa ({ti65_uts.percent_change:.2f}%) but elongation by {ti65_el.delta:.2f} percentage points. Reconstructed 650–700 °C rows are sensitivity-only because authoritative absolute records and condition UIDs are absent.

## Why the same reinforcement behaves differently

The controlling quantity is not reinforcement identity alone. Net gain is the balance of load transfer, grain/lamella refinement, dislocation storage and phase/precipitation strengthening against damage initiation, interface debonding, whisker fracture, matrix softening and loss of deformation reserve. Matrix baseline strength and α/β partition set the available deformation capacity; process route sets reinforcement morphology, network continuity, porosity and grain state; temperature changes matrix flow stress and recovery; test mode changes the failure constraint. These variables are aliased with family in the present cohort.

## Transfer and applicability-domain verdict

All non-diagonal source→target cells are reported as `EXTRAPOLATION_ONLY`. Their numerical errors are diagnostic stress tests, not validated transfer performance. Only diagonal reconstruction is accepted. Cross-grade transfer requires at least two independent source papers per family, a held-out target paper, compatible test/property definitions and overlap in baseline strength, phase fraction, grain scale, dose, process and temperature.

## Independent evidence accounting

- Top-level project sources terminally registered: 27; no `PENDING` state.
- Primary study/source identities in paired cohort: {primary.paper_uid.nunique()}.
- Paired property effects: {len(effects)} total, {len(primary)} primary and {len(effects)-len(primary)} sensitivity-only.
- Atomic sample-property records: {2*len(effects)}.
- Matrix families represented: {primary.matrix_family.nunique()}.
- Quantitative figures: 4, each with CSV, standalone Python, SVG, PDF and 600-dpi PNG.
- Open or structural conflicts: {len(conflicts)}.
- Maximum claim level: 2 for headline paired results; adjusted moderation is reported only as noncausal association.

## Claim ceiling

Allowed: same-paper paired effects, within-paper dose/state interactions, descriptive partial pooling, LOPO sensitivity and explicit OOD diagnostics. Forbidden: universal matrix-family causal coefficient, production transfer model, Gold promotion, production-model registration or `VALIDATED` formulation.

`STATUS: CONTINUE_DATA_GAP`
"""
    (OUT / "00_EXECUTIVE_VERDICT.md").write_text(verdict, encoding="utf-8")

    methods = """# Methods

## Estimands

The primary paired estimands are ΔY = Y_reinforced − Y_matrix, lnRR = ln(Y_reinforced/Y_matrix), and 100·(exp(lnRR)−1). Unit-content efficiency is computed only for measured or explicitly nominal actual vol.% reinforcement and is never pooled across precursor-dose scales.

## Atomicity and controls

Each pair retains paper, grade, material state, process, temperature, test mode, strain rate, reinforcement, dose, property, source locator and evidence grade. All headline pairs are class-A same-paper controls. Each pair is expanded into two atomic sample-property rows with deterministic sample, condition, record and effect UIDs.

## Partial pooling and heterogeneity

Family means on lnRR are shrunk toward the property/test-mode global mean using w=n/(n+2). This is a transparent descriptive empirical-Bayes analogue, not a fitted causal mixed model. Random-slope variance and prediction intervals are marked not identifiable because matrix family is aliased with paper and process.

## Baseline moderation

For each canonical property and test mode, lnRR is regressed on ln(baseline strength). Ratio-scale response plus same-paper controls reduces, but cannot eliminate, regression-to-the-mean bias. Slopes are stress-tested by leave-one-paper-out; they are interpreted as adjusted associations only.

## Transfer and applicability domain

Source-family median lnRR is applied to target-family median baseline strength. Relative error is compared with the observed target median. Gower distance uses baseline strength, temperature, dose, β fraction, grain size, test mode, reinforcement class and process route; missing numeric/categorical information receives a 0.5 penalty. Non-diagonal transfer is not accepted.

## Uncertainty

Reported control/treatment dispersions are propagated as independent standard-error-like quantities only when both are available. Figure-digitized values carry explicit tolerance rather than invented replicate variance. Family confidence and prediction intervals remain null when independent-paper replication is absent.

## Multiplicity and causal language

No family significance ranking is performed, so BH-FDR is not invoked. Claim level is capped at 2 for same-paper paired association; no randomization or exchangeability claim is made.
"""
    (OUT / "METHODS.md").write_text(methods, encoding="utf-8")

    limitations = """# Limitations

1. The authoritative Q40 input snapshot, V29 stable paper/sample/condition UIDs and conflict ledger were not exposed as a single consumable frozen table.
2. Each matrix family is dominated by one independent paper or internal source. Matrix-family and paper/process effects cannot be separated.
3. cp-Ti uses a high-volume TiC+TiB hybrid; Ti64 contains pure-TiB and hybrid variants; Ti55 uses network TiBw; Beta21S uses B4C precursor with TiB+TiC; Ti65 uses TiB2-derived reinforcement. Chemical identity is therefore not fully invariant across families.
4. Beta21S properties are compression metrics while most other families use tension. The transfer matrix exposes, rather than hides, this protocol mismatch.
5. Several values are figure-derived. Ti65 high-temperature absolute rows are reconstructed from rounded contrasts and excluded from headline family estimates.
6. Replicate-level raw data and covariance are usually absent. No universal confidence or prediction interval is fabricated.
7. Missing β fraction and grain-scale fields incur an explicit applicability-domain penalty; they are not imputed as known physics.
8. The recovery snapshot is not Gold and cannot register a production model or validate a composition.
"""
    (OUT / "LIMITATIONS.md").write_text(limitations, encoding="utf-8")


def write_requests(snapshot_id: str) -> None:
    request = {
        "window_id": "QM21",
        "snapshot_id": snapshot_id,
        "status": "CONTINUE_DATA_GAP",
        "required": [
            {"object": "Q40_INPUT_SNAPSHOT", "reason": "bind analysis to authoritative frozen atomic records"},
            {"object": "V29_UID_BINDINGS", "reason": "replace recovery UIDs with canonical paper/sample/condition IDs"},
            {"object": "ORIGINAL_SOURCE_BYTE_HASHES_AND_MEMBER_PATHS", "reason": "upgrade locator hashes to original-byte provenance"},
            {"object": "REPLICATE_LEVEL_VALUES_OR_SD_N", "reason": "estimate paper-cluster uncertainty and prediction intervals"},
            {"object": "SAME_REINFORCEMENT_REPLICATES_ACROSS_MATRIX_FAMILIES", "reason": "identify matrix-family random slopes and held-out transfer"},
            {"object": "TI65_ORIGINAL_650_700C_ATOMIC_ROWS", "reason": "replace rounded reconstructed sensitivity rows"},
        ],
        "acceptance": "all files hash-bound; no row-level key collisions; paper counts independently verified; source PDF/XML locators present",
    }
    (OUT / "WEB_TO_LOCAL_REQUEST.json").write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt = f"""# Local absorption prompt

1. Verify `FINAL_QM21.zip` by external SHA-256, `zip -T`/testzip, `CHECKSUMS.sha256`, manifest coverage and independent extraction.
2. Confirm snapshot `{snapshot_id}` is a recovery snapshot, not ACTIVE/Gold.
3. Map every recovery paper/sample/condition UID to the canonical V29 registry without fuzzy overwrite; unresolved mappings enter the conflict ledger.
4. Supply the six objects listed in `WEB_TO_LOCAL_REQUEST.json`, then rerun `code/build_qm21.py` on the canonical snapshot.
5. Recompute all paired effects, LOPO slopes, family support distances and four figures. Reject any non-diagonal transfer that lacks overlap and an independent held-out target paper.
6. Do not promote Gold, modify ACTIVE_TITMC or register a production model until the canonical rerun passes independent validation.
"""
    (OUT / "LOCAL_ABSORPTION_PROMPT.md").write_text(prompt, encoding="utf-8")


def write_plot_specs() -> None:
    specs = {
        "matrix_cate_caterpillar": {"estimand": "median paired percent change in ultimate strength by matrix family", "uncertainty": "observed effect range, not causal CI", "support": "primary same-paper pairs"},
        "baseline_strength_gain": {"estimand": "lnRR moderation by log baseline strength", "uncertainty": "LOPO sensitivity in BASELINE_MODERATION.csv", "support": "paper/source labels retained"},
        "transfer_error_matrix": {"estimand": "naive source-family median lnRR applied to target-family median baseline", "uncertainty": "no accepted non-diagonal transfer", "support": "OOD cells labeled"},
        "overlap_ad_map": {"estimand": "pairwise Gower distance among family centroids", "uncertainty": "missing fields penalized 0.5", "support": "feature list in MATRIX_OVERLAP.csv"},
        "formats": ["SVG", "PDF", "PNG_600_DPI"],
        "language": "English",
    }
    (OUT / "PLOT_SPECS.json").write_text(json.dumps(specs, indent=2), encoding="utf-8")


def write_provenance(effects: pd.DataFrame) -> None:
    with (OUT / "PROVENANCE.jsonl").open("w", encoding="utf-8") as f:
        for _, r in effects.iterrows():
            obj = {
                "snapshot_id": r.snapshot_id,
                "effect_uid": r.effect_uid,
                "paper_uid": r.paper_uid,
                "sample_uid_control": r.sample_uid_control,
                "sample_uid_treated": r.sample_uid_treated,
                "condition_uid": r.condition_uid,
                "source_hash": r.source_hash,
                "source_hash_kind": r.source_hash_kind,
                "doi": r.doi or None,
                "source_locator": r.source_locator,
                "evidence_grade": r.evidence_grade,
                "derivation": {"baseline": r.baseline_value, "treated": r.treated_value, "delta": r.delta, "lnRR": None if pd.isna(r.lnRR) else r.lnRR},
                "claim_level": int(r.claim_level),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_status(snapshot_id: str, pairs: pd.DataFrame, effects: pd.DataFrame, conflicts: pd.DataFrame) -> None:
    status = {
        "window_id": "QM21",
        "snapshot_id": snapshot_id,
        "papers_seen": 8,
        "papers_included": int(effects.paper_uid.nunique()),
        "independent_papers": int(effects.paper_uid.nunique()),
        "atomic_rows": int(2 * len(pairs)),
        "matched_pairs": int(len(pairs)),
        "effect_estimates": int(len(effects)),
        "plots_generated": 4,
        "open_conflicts": int(conflicts.status.str.contains("OPEN|NONIDENTIFIABILITY", regex=True).sum()),
        "claim_level_max": 2,
        "status": "CONTINUE_DATA_GAP",
        "next_action": "local absorb canonical Q40/V29 identities and rerun hierarchical transfer with replicated families",
        "production_model_registered": False,
        "gold_promoted": False,
    }
    (OUT / "WINDOW_STATUS.json").write_text(json.dumps(status, indent=2), encoding="utf-8")


def copy_code_and_write_requirements() -> None:
    shutil.copy2(Path(__file__), OUT / "code" / "build_qm21.py")
    test_src = BASE / "tests" / "test_contract.py"
    if test_src.exists():
        shutil.copy2(test_src, OUT / "tests" / "test_contract.py")
    req = "numpy==2.2.6\npandas==2.2.3\nmatplotlib==3.10.3\n"
    (OUT / "requirements.lock").write_text(req, encoding="utf-8")
    acceptance = """# Acceptance commands

```bash
python -m pip install -r requirements.lock
python code/build_qm21.py
python -m unittest discover -s tests -v
sha256sum -c CHECKSUMS.sha256
```

The repository workflow performs the canonical build and unit-test sequence. Local rerun requires replacing the recovery seed tables with canonical V29/Q40 inputs before any Gold or production use.
"""
    (OUT / "acceptance_commands.md").write_text(acceptance, encoding="utf-8")


def internal_contract_checks() -> list[str]:
    checks = []
    for f in REQUIRED_FILES[:-2]:
        p = OUT / f
        if not p.exists():
            raise AssertionError(f"missing required output: {f}")
        checks.append(f"PASS required:{f}")
    for stem in ["matrix_cate_caterpillar", "baseline_strength_gain", "transfer_error_matrix", "overlap_ad_map"]:
        for ext in ["svg", "pdf", "png"]:
            p = FIGURES / f"{stem}.{ext}"
            if not p.exists() or p.stat().st_size == 0:
                raise AssertionError(f"missing figure {p}")
            checks.append(f"PASS figure:{stem}.{ext}")
    if "VALIDATED" in (OUT / "00_EXECUTIVE_VERDICT.md").read_text(encoding="utf-8"):
        raise AssertionError("forbidden VALIDATED token in executive verdict")
    checks.append("PASS no_validated_claim")
    return checks


def manifest_and_checksums(snapshot_id: str) -> None:
    files = [p for p in OUT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"}]
    manifest = {
        "window_id": "QM21",
        "snapshot_id": snapshot_id,
        "status": "CONTINUE_DATA_GAP",
        "files": [{"path": p.relative_to(OUT).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in sorted(files)],
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files2 = [p for p in OUT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256"]
    lines = [f"{sha256_file(p)}  {p.relative_to(OUT).as_posix()}" for p in sorted(files2)]
    (OUT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_zip(snapshot_id: str) -> tuple[Path, str, int]:
    zip_path = BUILD / "FINAL_QM21.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(OUT).as_posix())
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"zip CRC failure: {bad}")
        entries = len(zf.infolist())
    digest = sha256_file(zip_path)
    (BUILD / "FINAL_QM21.sha256").write_text(f"{digest}  FINAL_QM21.zip\n", encoding="utf-8")
    receipt = {
        "window_id": "QM21", "snapshot_id": snapshot_id, "zip": zip_path.name,
        "zip_sha256": digest, "zip_bytes": zip_path.stat().st_size, "zip_entries": entries,
        "testzip": "PASS", "status": "CONTINUE_DATA_GAP", "output_dir": str(OUT), "figures": 4,
    }
    (BUILD / "QM21_DELIVERY_RECEIPT.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return zip_path, digest, entries


def main() -> None:
    ensure_clean()
    pairs, ledger, snapshot_id = read_inputs()
    atomic = build_atomic_records(pairs)
    effects = compute_effects(pairs)
    cate = aggregate_matrix_cate(effects)
    moderation = baseline_moderation(effects)
    overlap = overlap_matrix(effects)
    transfer = transfer_matrix(effects, overlap)
    dose = dose_response(effects)
    inter = interactions(effects)
    hetero = heterogeneity(effects, cate)
    hier = hierarchical_results(cate, effects)
    sens = sensitivity_table(effects, moderation)
    conflicts = conflict_ledger()
    nulls = null_negative_results()

    write_csv(ledger, "INPUT_LEDGER.csv")
    write_csv(atomic, "ATOMIC_RECORDS.csv")
    cohort_cols = [c for c in pairs.columns if c not in {"baseline_uncertainty", "treated_uncertainty"}]
    write_csv(pairs[cohort_cols], "ANALYSIS_COHORT.csv")
    pair_cols = ["snapshot_id", "pair_id", "effect_uid", "paper_uid", "sample_uid_control", "sample_uid_treated", "condition_uid", "matrix_family", "grade", "material_state", "temperature_c", "test_mode", "reinforcement_class", "dose_value", "dose_unit", "property", "control_class", "evidence_grade", "source_hash", "source_locator"]
    write_csv(pairs[pair_cols], "PAIR_MATCHES.csv")
    write_csv(effects, "EFFECT_ESTIMATES.csv")
    write_csv(hier, "HIERARCHICAL_RESULTS.csv")
    write_csv(dose, "DOSE_RESPONSE.csv")
    write_csv(inter, "INTERACTION_EFFECTS.csv")
    write_csv(hetero, "HETEROGENEITY.csv")
    write_csv(sens, "SENSITIVITY_ANALYSIS.csv")
    write_csv(nulls, "NULL_NEGATIVE_RESULTS.csv")
    write_csv(conflicts, "CONFLICT_LEDGER.csv")
    write_csv(cate, "MATRIX_CATE.csv")
    write_csv(transfer, "GRADE_TRANSFER_MATRIX.csv")
    write_csv(moderation, "BASELINE_MODERATION.csv")
    write_csv(overlap, "MATRIX_OVERLAP.csv")

    write_provenance(effects)
    write_reports(snapshot_id, effects, cate, transfer, overlap, conflicts)
    write_requests(snapshot_id)
    write_plot_specs()
    write_status(snapshot_id, pairs, effects, conflicts)
    write_plot_scripts()
    make_figure_data(effects, cate, transfer, overlap)
    execute_plots()
    copy_code_and_write_requirements()
    checks = internal_contract_checks()
    (OUT / "TEST_RECEIPT.md").write_text("# Internal contract checks\n\n" + "\n".join(f"- {x}" for x in checks) + "\n", encoding="utf-8")
    (OUT / "RUN_LOG.txt").write_text(f"snapshot={snapshot_id}\npaired_effects={len(effects)}\nprimary_effects={int(effects.primary_analysis.sum())}\nplots=4\nstatus=CONTINUE_DATA_GAP\n", encoding="utf-8")
    manifest_and_checksums(snapshot_id)
    zip_path, digest, entries = make_zip(snapshot_id)
    print(json.dumps({"snapshot_id": snapshot_id, "zip": str(zip_path), "sha256": digest, "entries": entries, "status": "CONTINUE_DATA_GAP"}, indent=2))


if __name__ == "__main__":
    main()
