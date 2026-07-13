from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WINDOW_ID = "QM21"
SNAPSHOT_ID = "MISSING_Q40_INPUT_SNAPSHOT"
STATUS = "CONTINUE_DATA_GAP"
CLAIM_LEVEL_MAX = 2
HERE = Path(__file__).resolve().parent
BUILD = HERE / "generated"
ROOT = BUILD / "FINAL_QM21"
FIGDATA = ROOT / "figure_data"
FIGS = ROOT / "figures"
PLOTS = ROOT / "plot_code"
TESTS = ROOT / "tests"

if BUILD.exists():
    shutil.rmtree(BUILD)
for p in (ROOT, FIGDATA, FIGS, PLOTS, TESTS):
    p.mkdir(parents=True, exist_ok=True)


def uid(prefix: str, *parts: object) -> str:
    s = "|".join(str(x) for x in parts)
    return f"{prefix}_{hashlib.sha256(s.encode()).hexdigest()[:16]}"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write_csv(name: str | Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path = ROOT / name if isinstance(name, str) else name
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: "" if r.get(k) is None else r.get(k) for k in fields})


def write_json(name: str | Path, obj) -> None:
    path = ROOT / name if isinstance(name, str) else name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


papers = {
    "LI2016": ("10.1016/j.matdes.2016.01.092", "Strengthening behavior of in situ-synthesized (TiC-TiB)/Ti composites by powder metallurgy and hot extrusion", 2016, "journal_primary", "Project Library original PDF; source turn25file0"),
    "KOO2012": ("10.1016/j.scriptamat.2011.12.024", "Effect of the aspect ratio of TiB whiskers on the mechanical properties of TiB/Ti-6Al-4V composites", 2012, "journal_primary", "Project Library original PDF; approximate figure digitization"),
    "MA2020": ("10.1016/j.msea.2019.138749", "Effect of trace boron addition on microstructure and mechanical properties of a near-alpha titanium alloy", 2020, "journal_primary", "Project Library original PDF; source turn23file0"),
    "SUN2021": ("SUN-SHICHEN-THESIS-2021", "TiB reinforced near-alpha high-temperature titanium matrix composites during hot deformation", 2021, "thesis_primary", "Project Library thesis PDF; source turn25file1"),
    "RIELLI2020": ("10.1016/j.matchar.2020.110286", "Single step heat treatment of beta titanium composites with in-situ TiB and TiC", 2020, "journal_primary", "Project Library original PDF; source turn23file1"),
    "XIONG2024": ("10.1007/s10853-024-09461-3", "Hot compression deformation characteristics of TiBw/Ti65 composites for high-temperature application", 2024, "journal_primary_missing_supplement", "Project Library original PDF; source turn23file2; Table S1/Fig. S1 absent"),
    "WANG2018": ("WANG-2018-NEARALPHA-TIBW", "Heat-treatment-dependent 600 C tensile properties of 5.1 vol.% TiBw near-alpha composite", 2018, "journal_primary", "Project Library paper; no matrix control"),
    "WU2019": ("WU-2019-CPTI-TIBW", "Temperature-dependent tensile behavior of 5 vol.% TiBw/cp-Ti composite", 2019, "journal_primary", "Project Library paper; no matrix control"),
}
P = {}
for key, (doi, title, year, stype, locator) in papers.items():
    P[key] = {"paper_uid": uid("paper", doi), "doi": doi if doi.startswith("10.") else "", "title": title, "year": year, "source_type": stype, "source_locator": locator}


effects: list[dict] = []

def add_effect(paper_key: str, pair: str, family: str, grade: str, reinforcement: str,
               dose, dose_unit: str, temp, mode: str, prop: str,
               control=None, treatment=None, control_sd=None, treatment_sd=None,
               pct=None, aspect=None, evidence="DIRECT_TABLE_TEXT", match="A", notes="") -> None:
    p = P[paper_key]
    pair_id = uid("pair", paper_key, pair, temp, mode)
    lnrr = None
    delta = None
    se_delta = None
    se_lnrr = None
    lo = None
    hi = None
    if control is not None and treatment is not None:
        control = float(control); treatment = float(treatment)
        delta = treatment - control
        if control > 0 and treatment > 0:
            lnrr = math.log(treatment / control)
            pct = 100 * (math.exp(lnrr) - 1)
        if control_sd is not None and treatment_sd is not None:
            se_delta = math.sqrt(float(control_sd) ** 2 + float(treatment_sd) ** 2)
            if control > 0 and treatment > 0:
                se_lnrr = math.sqrt((float(control_sd) / control) ** 2 + (float(treatment_sd) / treatment) ** 2)
                lo = 100 * (math.exp(lnrr - 1.96 * se_lnrr) - 1)
                hi = 100 * (math.exp(lnrr + 1.96 * se_lnrr) - 1)
    elif pct is not None:
        pct = float(pct)
        lnrr = math.log1p(pct / 100)
    effects.append({
        "effect_uid": uid("effect", paper_key, pair, prop, temp, aspect),
        "paper_key": paper_key,
        "paper_uid": p["paper_uid"],
        "pair_id": pair_id,
        "control_sample_uid": uid("sample", paper_key, pair, "control"),
        "treatment_sample_uid": uid("sample", paper_key, pair, "tmc"),
        "condition_uid": uid("condition", temp, mode, prop),
        "uid_status": "PROVISIONAL_WEB_UID_NOT_V29_OFFICIAL",
        "matrix_family": family,
        "grade": grade,
        "reinforcement": reinforcement,
        "dose_value": dose,
        "dose_unit": dose_unit,
        "aspect_ratio": aspect,
        "temperature_c": temp,
        "test_mode": mode,
        "property": prop,
        "control_value": control,
        "treatment_value": treatment,
        "delta": delta,
        "lnRR": lnrr,
        "percent_change": pct,
        "control_sd": control_sd,
        "treatment_sd": treatment_sd,
        "se_delta_conservative": se_delta,
        "se_lnRR_conservative": se_lnrr,
        "ci95_percent_low_conservative": lo,
        "ci95_percent_high_conservative": hi,
        "match_grade": match,
        "evidence_level": evidence,
        "claim_level": 2 if match in {"A", "B"} else 1,
        "support_domain": "WITHIN_PAPER_MATCHED" if match in {"A", "B"} else "DESCRIPTIVE_ONLY",
        "estimand": "paired absolute effect; ln response ratio",
        "estimand_status": "IDENTIFIED_WITHIN_PAIR" if match in {"A", "B"} else "DESCRIPTIVE_ONLY",
        "source_locator": p["source_locator"],
        "notes": notes,
    })

# cp-Ti: actual hybrid fraction 2.76 vol.% TiC + 10.80 vol.% TiB.
add_effect("LI2016", "Ti5B4C", "cp-Ti", "CP-450", "TiC+TiB", 13.56, "actual_total_vol_pct", 25, "tension", "YS_MPa", 484, 916, 8, 44, notes="n=3; hybrid, not pure TiB")
add_effect("LI2016", "Ti5B4C", "cp-Ti", "CP-450", "TiC+TiB", 13.56, "actual_total_vol_pct", 25, "tension", "UTS_MPa", 654, 1138, 7, 17, notes="n=3; hybrid, not pure TiB")
add_effect("LI2016", "Ti5B4C", "cp-Ti", "CP-450", "TiC+TiB", 13.56, "actual_total_vol_pct", 25, "tension", "EL_pct", 29, 2.6, 2, 1.8, notes="Table control=29%; body text=32.4%; conflict retained")

# Ti-6Al-4V: approximate figure-derived YS values, not inferentially pooled.
for pair, dose, ar, ys in [("1vol_AR18", 1.0, 18, 900), ("1vol_AR38", 1.0, 38, 1040), ("1vol_AR58", 1.0, 58, 1080), ("5vol_AR13", 5.0, 13, 1050)]:
    add_effect("KOO2012", pair, "Ti-6Al-4V", "Ti-6Al-4V", "TiBw", dose, "vol_pct", 25, "tension", "YS_MPa", 800, ys, aspect=ar, evidence="FIGURE_DERIVED", match="B", notes="Approximate digitization; broad uncertainty; no Gold promotion")

# near-alpha TA6.5, nominal 0.2 wt.% B; actual TiB vol.% unavailable.
for temp, vals in {
    25: {"UTS_MPa": (1077, 1146), "YS_MPa": (972, 1062), "EL_pct": (15.1, 8.5), "E_GPa": (110, 125)},
    650: {"UTS_MPa": (673, 712), "YS_MPa": (539, 596), "EL_pct": (22.9, 16.9), "E_GPa": (67, 77)},
}.items():
    for prop, (c, t) in vals.items():
        add_effect("MA2020", f"TA6.5_0.2B_{temp}", "near-alpha", "TA6.5", "TiB", 0.2, "nominal_B_wt_pct", temp, "tension", prop, c, t, notes="Same paper/process; actual TiB vol.% unavailable")

# near-alpha high-temperature alloy thesis.
near_grade = "Ti-6Al-4Sn-10Zr-1Mo-1Nb-1W-0.35Si"
add_effect("SUN2021", "3volTiB_as_cast", "near-alpha", near_grade, "TiB", 3.0, "vol_pct", 25, "compression", "CYS_MPa", 1099, 1310, notes="As-cast matched matrix/composite")
add_effect("SUN2021", "3volTiB_as_cast", "near-alpha", near_grade, "TiB", 3.0, "vol_pct", 25, "nanoindentation", "Hardness_GPa", 5.40, 6.18, notes="Matrix micro-region; scale-specific")

# beta Beta21S; B4C precursor creates TiB+TiC.
for name, dose, cys, ucs, deform in [("FC0.5", 0.5, 1055, 1521, 14.6), ("FC1.5", 1.5, 1281, 1680, 13.2), ("FC3", 3.0, 1205, 1636, 20.5)]:
    add_effect("RIELLI2020", name, "beta", "Beta 21S", "TiB+TiC", dose, "B4C_wt_pct", 25, "compression", "CYS_MPa", 801, cys, notes="Actual phase fractions unavailable")
    add_effect("RIELLI2020", name, "beta", "Beta 21S", "TiB+TiC", dose, "B4C_wt_pct", 25, "compression", "UCS_MPa", 1116, ucs, notes="Actual phase fractions unavailable")
    add_effect("RIELLI2020", name, "beta", "Beta 21S", "TiB+TiC", dose, "B4C_wt_pct", 25, "compression", "max_deformation_pct", 23.8, deform, notes="Compression maximum deformation")

# Ti65 main paper only; supplement is missing.
add_effect("XIONG2024", "3.4volTiBw_600", "Ti65", "Ti65", "TiBw", 3.4, "designed_vol_pct", 600, "tension", "UTS_MPa", pct=17.0, evidence="SAME_WORK_SUPPLEMENT_REFERENCED", match="B", notes="Absolute values and uncertainty require Table S1/Fig. S1")
add_effect("XIONG2024", "3.4volTiBw_700", "Ti65", "Ti65", "TiBw", 3.4, "designed_vol_pct", 700, "tension", "UTS_MPa", pct=16.0, evidence="SAME_WORK_SUPPLEMENT_REFERENCED", match="B", notes="Absolute values and uncertainty require Table S1/Fig. S1")

effects.sort(key=lambda r: (r["matrix_family"], r["paper_key"], float(r["temperature_c"]), r["pair_id"], r["property"]))
write_csv("EFFECT_ESTIMATES.csv", effects)

# Atomic records only for absolute values.
atomic = []
for e in effects:
    for arm, skey, val, sdv in [
        ("control", "control_sample_uid", e["control_value"], e["control_sd"]),
        ("treatment", "treatment_sample_uid", e["treatment_value"], e["treatment_sd"]),
    ]:
        if val is None:
            continue
        atomic.append({
            "snapshot_id": SNAPSHOT_ID,
            "paper_uid": e["paper_uid"],
            "sample_uid": e[skey],
            "condition_uid": e["condition_uid"],
            "pair_id": e["pair_id"],
            "arm": arm,
            "matrix_family": e["matrix_family"],
            "grade": e["grade"],
            "reinforcement": "none" if arm == "control" else e["reinforcement"],
            "dose_value": 0 if arm == "control" else e["dose_value"],
            "dose_unit": e["dose_unit"],
            "temperature_c": e["temperature_c"],
            "test_mode": e["test_mode"],
            "property": e["property"],
            "value": val,
            "sd": sdv,
            "evidence_level": e["evidence_level"],
            "source_locator": e["source_locator"],
            "uid_status": e["uid_status"],
        })
write_csv("ATOMIC_RECORDS_USED.csv", atomic)

# Cohort and matched pairs.
groups = defaultdict(list)
for e in effects:
    groups[e["pair_id"]].append(e)
cohort, pairs = [], []
for pair_id, rows in sorted(groups.items()):
    e = rows[0]
    props = ";".join(sorted({x["property"] for x in rows}))
    cohort.append({
        "snapshot_id": SNAPSHOT_ID, "paper_uid": e["paper_uid"], "pair_id": pair_id,
        "matrix_family": e["matrix_family"], "grade": e["grade"], "reinforcement": e["reinforcement"],
        "dose_value": e["dose_value"], "dose_unit": e["dose_unit"], "temperature_c": e["temperature_c"],
        "test_mode": e["test_mode"], "properties": props, "control_sample_uid": e["control_sample_uid"],
        "treatment_sample_uid": e["treatment_sample_uid"], "include": True,
        "evidence_level": e["evidence_level"], "support_domain": e["support_domain"],
        "uid_status": e["uid_status"],
    })
    pairs.append({
        "pair_id": pair_id, "paper_uid": e["paper_uid"], "control_sample_uid": e["control_sample_uid"],
        "treatment_sample_uid": e["treatment_sample_uid"], "condition_uid": e["condition_uid"],
        "match_grade": e["match_grade"], "matrix_exact": True, "process_exact": True,
        "heat_treatment_exact": True, "test_mode_exact": True, "temperature_exact": True,
        "orientation_exact_or_unreported": True, "properties": props,
        "extrapolation_flag": "NO" if e["match_grade"] == "A" else "EVIDENCE_LIMITED",
        "notes": e["notes"],
    })
write_csv("ANALYSIS_COHORT.csv", cohort)
write_csv("PAIR_MATCHES.csv", pairs)

# Scope-specific matrix-conditional rows; explicitly not family CATE.
write_csv("MATRIX_CATE.csv", [{
    "matrix_family": e["matrix_family"], "grade": e["grade"], "paper_uid": e["paper_uid"],
    "effect_uid": e["effect_uid"], "property": e["property"], "temperature_c": e["temperature_c"],
    "test_mode": e["test_mode"], "reinforcement": e["reinforcement"], "dose_value": e["dose_value"],
    "dose_unit": e["dose_unit"], "paired_delta": e["delta"], "lnRR": e["lnRR"],
    "percent_change": e["percent_change"], "n_independent_papers": 1,
    "evidence_level": e["evidence_level"], "support_domain": e["support_domain"],
    "estimand_requested": "reinforcement CATE by matrix_family",
    "estimand_delivered": "within-paper matrix-conditional paired effect",
    "estimand_status": "DESCRIPTIVE_PAIRED_ONLY_NOT_FAMILY_CATE", "claim_level": e["claim_level"],
} for e in effects])

hier = [
    {"model_id": "H1_RANDOM_SLOPE_MATRIX_FAMILY", "formula": "lnRR ~ reinforcement + dose + baseline_strength + beta_fraction + alpha_scale + temperature + interactions + (1+reinforcement|paper/matrix_family)", "estimand": "matrix-family CATE and between-grade variance", "status": "NOT_IDENTIFIABLE", "estimate": "", "uncertainty": "", "reason": "Matrix family is aliased with paper, process, property mode, dose basis and reinforcement identity; most families have one paper.", "claim_level": 1},
    {"model_id": "H2_BASELINE_MODERATION", "formula": "percent_gain ~ baseline_strength + mode + temperature + reinforcement + (1|paper)", "estimand": "baseline-strength moderation", "status": "NOT_IDENTIFIABLE", "estimate": "", "uncertainty": "", "reason": "Mathematical coupling/regression-to-mean plus sparse independent papers; plot is observation-level only.", "claim_level": 1},
    {"model_id": "H3_GRADE_TRANSFER", "formula": "leave-grade/family-out transfer error", "estimand": "source-grade to target-grade error", "status": "NOT_IDENTIFIABLE_OOD", "estimate": "", "uncertainty": "", "reason": "No common feature-complete frozen matrix, authoritative split manifest or target labels; off-diagonal errors remain blank.", "claim_level": 1},
    {"model_id": "H4_BETA_DOSE_WITHIN_PAPER", "formula": "strength ~ B4C dose + dose^2", "estimand": "within-paper dose shape", "status": "DESCRIPTIVE_NONMONOTONIC", "estimate": "peak at 1.5 wt.% B4C", "uncertainty": "not reported", "reason": "Strength falls at 3 wt.% despite higher precursor dose; actual TiB/TiC fractions unavailable.", "claim_level": 2},
]
write_csv("HIERARCHICAL_RESULTS.csv", hier)

# Dose response table and same-paper Beta21S piecewise slopes.
dose_rows = [{
    "paper_uid": e["paper_uid"], "matrix_family": e["matrix_family"], "grade": e["grade"],
    "property": e["property"], "temperature_c": e["temperature_c"], "dose_value": e["dose_value"],
    "dose_unit": e["dose_unit"], "aspect_ratio": e["aspect_ratio"], "delta": e["delta"],
    "percent_change": e["percent_change"], "dose_response_status": "OBSERVED_POINT_ONLY",
    "identifiability": "NOT_GENERALIZABLE",
} for e in effects]
for prop in ("CYS_MPa", "UCS_MPa"):
    pts = sorted([e for e in effects if e["paper_key"] == "RIELLI2020" and e["property"] == prop], key=lambda r: float(r["dose_value"]))
    pdose, pdelta = 0.0, 0.0
    for e in pts:
        slope = (float(e["delta"]) - pdelta) / (float(e["dose_value"]) - pdose)
        dose_rows.append({
            "paper_uid": e["paper_uid"], "matrix_family": "beta", "grade": "Beta 21S", "property": prop,
            "temperature_c": 25, "dose_value": f"{pdose}->{e['dose_value']}", "dose_unit": "B4C_wt_pct_interval",
            "aspect_ratio": "", "delta": slope, "percent_change": "",
            "dose_response_status": "PIECEWISE_SLOPE_MPa_PER_WT_PCT_DESCRIPTIVE", "identifiability": "WITHIN_ONE_PAPER_ONLY",
        })
        pdose, pdelta = float(e["dose_value"]), float(e["delta"])
write_csv("DOSE_RESPONSE.csv", dose_rows)


def find_effect(key: str, temp, prop: str) -> dict:
    return next(e for e in effects if e["paper_key"] == key and float(e["temperature_c"]) == float(temp) and e["property"] == prop)

interactions = []
for prop in ("UTS_MPa", "YS_MPa", "EL_pct", "E_GPa"):
    rt, ht = find_effect("MA2020", 25, prop), find_effect("MA2020", 650, prop)
    interactions.append({
        "interaction": "reinforcement_x_temperature", "matrix_family": "near-alpha", "grade": "TA6.5",
        "property": prop, "contrast": "650C minus 25C relative effect", "estimate": float(ht["percent_change"]) - float(rt["percent_change"]),
        "unit": "percentage_points", "status": "WITHIN_PAPER_DESCRIPTIVE", "claim_level": 2,
        "interpretation": "Temperature moderation cannot be generalized beyond this paper.",
    })
interactions += [
    {"interaction": "reinforcement_x_temperature", "matrix_family": "Ti65", "grade": "Ti65", "property": "UTS_MPa", "contrast": "700C minus 600C relative effect", "estimate": -1.0, "unit": "percentage_points", "status": "SUPPLEMENT_REFERENCED_DESCRIPTIVE", "claim_level": 1, "interpretation": "Relative benefit is similar; absolute values and uncertainty are missing."},
    {"interaction": "dose_x_phase_fraction", "matrix_family": "beta", "grade": "Beta 21S", "property": "CYS/UCS", "contrast": "3.0 minus 1.5 wt.% B4C", "estimate": "negative strength increment", "unit": "qualitative", "status": "WITHIN_PAPER_DESCRIPTIVE", "claim_level": 2, "interpretation": "Reinforcement/grain refinement competes with alpha-fraction loss and beta-matrix softening."},
    {"interaction": "aspect_ratio_x_reinforcement", "matrix_family": "Ti-6Al-4V", "grade": "Ti-6Al-4V", "property": "YS_MPa", "contrast": "AR58 minus AR18 at 1 vol.%", "estimate": 180.0, "unit": "MPa_approximate", "status": "FIGURE_DERIVED_DESCRIPTIVE", "claim_level": 1, "interpretation": "Whisker morphology can dominate nominal dose; digitization uncertainty unresolved."},
]
write_csv("INTERACTION_EFFECTS.csv", interactions)

strength_props = {"YS_MPa", "UTS_MPa", "CYS_MPa", "UCS_MPa"}
hetero = []
for fam in sorted({e["matrix_family"] for e in effects}):
    rows = [e for e in effects if e["matrix_family"] == fam and e["property"] in strength_props]
    vals = [float(e["percent_change"]) for e in rows if e["percent_change"] is not None]
    hetero.append({
        "matrix_family": fam, "n_independent_papers": len({e["paper_uid"] for e in rows}), "n_strength_effects": len(vals),
        "observed_percent_change_min": min(vals) if vals else "", "observed_percent_change_max": max(vals) if vals else "",
        "tau2": "", "I2": "", "between_grade_variance_status": "NOT_IDENTIFIABLE",
        "reason": "Insufficient independent papers and non-exchangeable process/test/reinforcement conditions.",
    })
write_csv("HETEROGENEITY.csv", hetero)

baseline = [{
    "effect_uid": e["effect_uid"], "paper_uid": e["paper_uid"], "matrix_family": e["matrix_family"], "grade": e["grade"],
    "property": e["property"], "temperature_c": e["temperature_c"], "test_mode": e["test_mode"],
    "baseline_strength": e["control_value"], "absolute_gain": e["delta"], "percent_gain": e["percent_change"],
    "evidence_level": e["evidence_level"], "overlap_flag": "BASELINE_MISSING" if e["control_value"] is None else "OBSERVED_POINT",
    "regression_slope": "", "model_status": "NOT_IDENTIFIABLE_OBSERVATION_ONLY",
} for e in effects if e["property"] in strength_props]
write_csv("BASELINE_MODERATION.csv", baseline)

# Transparent, rule-based applicability diagnostics.
grades = [
    {"grade": "CP-450", "family": "cp-Ti", "modes": {"tension"}, "temps": {25}, "reinforcement": {"TiB+TiC"}, "dose": {"vol"}, "process": {"PM_extrusion"}},
    {"grade": "Ti-6Al-4V", "family": "Ti-6Al-4V", "modes": {"tension"}, "temps": {25}, "reinforcement": {"TiB"}, "dose": {"vol"}, "process": {"SPS"}},
    {"grade": "TA6.5", "family": "near-alpha", "modes": {"tension"}, "temps": {25, 650}, "reinforcement": {"TiB"}, "dose": {"wtB"}, "process": {"melt_forge"}},
    {"grade": near_grade, "family": "near-alpha", "modes": {"compression", "nanoindentation"}, "temps": {25}, "reinforcement": {"TiB"}, "dose": {"vol"}, "process": {"casting"}},
    {"grade": "Ti65", "family": "Ti65", "modes": {"tension"}, "temps": {600, 700}, "reinforcement": {"TiB"}, "dose": {"vol"}, "process": {"PM_hot_press"}},
    {"grade": "Beta 21S", "family": "beta", "modes": {"compression"}, "temps": {25}, "reinforcement": {"TiB+TiC"}, "dose": {"wtB4C"}, "process": {"VAR_heat_treat"}},
]
overlap, transfer = [], []
for s in grades:
    for t in grades:
        if s["grade"] == t["grade"]:
            score, support = 1.0, "IN_DOMAIN_SELF_ONLY"
        else:
            dims = [s["family"] == t["family"], bool(s["modes"] & t["modes"]), bool(s["temps"] & t["temps"]), bool(s["reinforcement"] & t["reinforcement"]), bool(s["dose"] & t["dose"]), bool(s["process"] & t["process"])]
            score = sum(dims) / 6
            support = "PARTIAL_OVERLAP_HYPOTHESIS_ONLY" if score >= 0.5 else "OOD_NO_TRANSFER_CLAIM"
        overlap.append({
            "source_grade": s["grade"], "source_family": s["family"], "target_grade": t["grade"], "target_family": t["family"],
            "overlap_score_descriptive": round(score, 4), "feature_dimensions": "family;test_mode;temperature;reinforcement;dose_basis;process",
            "support_status": support, "extrapolation_flag": "NO" if s["grade"] == t["grade"] else "YES",
            "claim_ceiling": "within_grade_observation" if s["grade"] == t["grade"] else "hypothesis_only",
        })
        transfer.append({
            "source_grade": s["grade"], "source_family": s["family"], "target_grade": t["grade"], "target_family": t["family"],
            "transfer_error": "", "error_metric": "", "overlap_score_descriptive": round(score, 4),
            "support_status": "SELF_REFERENCE_NO_CV_ERROR" if s["grade"] == t["grade"] else "NOT_IDENTIFIABLE_OOD",
            "leave_grade_out_status": "NOT_A_TRANSFER_TEST" if s["grade"] == t["grade"] else "FAILED_SUPPORT",
            "reason": "No common feature-complete frozen matrix or target labels; numeric error intentionally not fabricated.",
        })
write_csv("MATRIX_OVERLAP.csv", overlap)
write_csv("GRADE_TRANSFER_MATRIX.csv", transfer)

sensitivity = [
    {"analysis": "Li2016 elongation conflict", "variant": "table control EL=29%", "result": "delta=-26.4 percentage points", "impact": "headline table uses this value", "status": "ROBUST_DIRECTION"},
    {"analysis": "Li2016 elongation conflict", "variant": "body control EL=32.4%", "result": "delta=-29.8 percentage points", "impact": "magnitude changes; severe loss remains", "status": "ROBUST_DIRECTION"},
    {"analysis": "Evidence level", "variant": "exclude FIGURE_DERIVED Ti64", "result": "Ti64 numeric effect removed", "impact": "cross-family CATE remains unidentified", "status": "DATA_GAP"},
    {"analysis": "Reinforcement identity", "variant": "exclude hybrid TiB+TiC", "result": "cp-Ti and beta anchors disappear", "impact": "pure-TiB family comparison collapses", "status": "NOT_IDENTIFIABLE"},
    {"analysis": "Test mode", "variant": "tension only", "result": "beta and thesis compression anchors removed", "impact": "no beta comparison", "status": "FAILED_SUPPORT"},
    {"analysis": "LOPO", "variant": "leave one independent paper out", "result": "most families retain zero paper", "impact": "family slopes fail support", "status": "FAILED_SUPPORT"},
    {"analysis": "Leave-family-out", "variant": "predict omitted family", "result": "off-diagonal error unavailable", "impact": "OOD hypothesis only", "status": "NOT_IDENTIFIABLE_OOD"},
    {"analysis": "Ti65 supplement", "variant": "main-paper relative gains only", "result": "+17% at 600C; +16% at 700C", "impact": "no absolute gain/uncertainty", "status": "CONTINUE_DATA_GAP"},
]
write_csv("SENSITIVITY_ANALYSIS.csv", sensitivity)

nulls = [
    {"result_id": "N1", "scope": "beta/Beta21S", "finding": "Strength is non-monotonic with B4C precursor dose; 3 wt.% is weaker than 1.5 wt.%.", "interpretation": "Reinforcement/grain refinement competes with reduced alpha fraction and softer beta matrix.", "evidence": "DIRECT_TABLE_TEXT", "claim_level": 2},
    {"result_id": "N2", "scope": "near-alpha/TA6.5", "finding": "Trace-B strengthening costs about 6 percentage points elongation at 25C and 650C.", "interpretation": "Refinement/DRX and load transfer coexist with TiB/interface damage.", "evidence": "DIRECT_TABLE_TEXT", "claim_level": 2},
    {"result_id": "N3", "scope": "cp-Ti hybrid", "finding": "Large strength gains coexist with severe elongation collapse.", "interpretation": "High hybrid fraction raises load bearing but brittle reinforcement damage controls failure.", "evidence": "DIRECT_TABLE_TEXT", "claim_level": 2},
    {"result_id": "N4", "scope": "cross-grade transfer", "finding": "No defensible numeric off-diagonal transfer error can be computed.", "interpretation": "Support domains do not sufficiently overlap and frozen feature/UID snapshot is absent.", "evidence": "ANALYSIS_CONSTRAINT", "claim_level": 1},
    {"result_id": "N5", "scope": "baseline moderation", "finding": "A baseline-strength/gain trend cannot be separated from confounding and regression-to-mean.", "interpretation": "The scatter trend is not causal or general.", "evidence": "ANALYSIS_CONSTRAINT", "claim_level": 1},
]
write_csv("NULL_NEGATIVE_RESULTS.csv", nulls)

conflicts = [
    {"conflict_id": "C1", "paper_uid": P["LI2016"]["paper_uid"], "field": "control_EL_pct", "value_a": 29, "source_a": "Fig.3 table", "value_b": 32.4, "source_b": "body/conclusion", "resolution": "Use table 29%; retain 32.4 sensitivity", "status": "OPEN_SOURCE_INTERNAL_CONFLICT"},
    {"conflict_id": "C2", "paper_uid": P["XIONG2024"]["paper_uid"], "field": "absolute_600_700C_tensile", "value_a": "relative +17/+16%", "source_a": "main paper", "value_b": "Table S1/Fig.S1 unavailable", "source_b": "supplement", "resolution": "Relative effects only; request supplement", "status": "OPEN_MISSING_SUPPLEMENT"},
    {"conflict_id": "C3", "paper_uid": P["KOO2012"]["paper_uid"], "field": "YS_values", "value_a": "approximate figure digitization", "source_a": "figure", "value_b": "raw table absent", "source_b": "project source", "resolution": "FIGURE_DERIVED; exclude inferential pooling", "status": "OPEN_DIGITIZATION_UNCERTAINTY"},
    {"conflict_id": "C4", "paper_uid": "", "field": "snapshot_and_uids", "value_a": SNAPSHOT_ID, "source_a": "web return", "value_b": "V29 official IDs absent", "source_b": "contract", "resolution": "Provisional UIDs; no Gold/production registration", "status": "OPEN_GOVERNANCE_BLOCK"},
    {"conflict_id": "C5", "paper_uid": P["MA2020"]["paper_uid"], "field": "actual_TiB_vol_pct", "value_a": "0.2 wt.% nominal B", "source_a": "methods", "value_b": "not reported", "source_b": "paper", "resolution": "No unit-content efficiency", "status": "OPEN_CONVERSION_GAP"},
    {"conflict_id": "C6", "paper_uid": P["RIELLI2020"]["paper_uid"], "field": "actual_TiB_TiC_phase_fractions", "value_a": "0.5/1.5/3 wt.% B4C", "source_a": "methods", "value_b": "not reported", "source_b": "paper", "resolution": "Precursor-dose descriptive only", "status": "OPEN_CONVERSION_GAP"},
]
write_csv("CONFLICT_LEDGER.csv", conflicts)
write_csv("EXCLUDED_RECORDS.csv", [
    {"paper_uid": P["WANG2018"]["paper_uid"], "reason": "No unreinforced matrix control; heat-treatment series only", "disposition": "MECHANISM_REFERENCE_ONLY"},
    {"paper_uid": P["WU2019"]["paper_uid"], "reason": "No unreinforced matrix control", "disposition": "DESCRIPTIVE_TEMPERATURE_REFERENCE_ONLY"},
])

# Input ledger: terminal disposition for every top-level project package named in the dispatch context.
archives = [
    "00_统一上传总控与校验信息_20260712.zip",
    "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip", "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
] + [f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 9)] + [
    "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
] + [f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 4)] + [f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1, 11)]
ledger = []
for name in archives:
    if name.startswith("TITMC"):
        role, disposition = "original_literature_corpus", "USED_VIA_PROJECT_LIBRARY_PRIMARY_PAPERS; MEMBER_HASH_REQUIRES_LOCAL_ABSORPTION"
    elif name.startswith("S03_CODEX_ML_DATA"):
        role, disposition = "frozen_data_features_expected", "NOT_BINDABLE_WITHOUT_Q40_INPUT_SNAPSHOT_AND_MEMBER_HASH"
    elif name.startswith("S03_CODEX_ML_HARNESS"):
        role, disposition = "harness_evidence_expected", "METHOD_CONTRACT_REFERENCE; OFFICIAL_UID_ASSETS_NOT_LOCATED"
    elif name.startswith("S02"):
        role, disposition = "plot_and_web_return_code", "PLOT_CONTRACT_REFERENCE"
    elif name.startswith("S04"):
        role, disposition = "github_staging_or_history", "NOT_SCIENTIFIC_INPUT_TO_THIS_WINDOW"
    else:
        role, disposition = "control_and_validation", "GOVERNANCE_REFERENCE; AUTHORITATIVE_SNAPSHOT_HASH_MISSING"
    ledger.append({"input_name": name, "snapshot_id": SNAPSHOT_ID, "source_hash": "MISSING_LOCAL_FILE_HASH", "hash_scope": "top_level_archive", "open_status": "PROJECT_PATH_VISIBLE; CONTENT/HASH_NOT_AUTHORITY_BOUND", "role": role, "terminal_disposition": disposition, "blocking_gap": "Q40_INPUT_SNAPSHOT/V29_UID_BINDINGS" if name.startswith(("00_", "S03")) else ""})
ledger.append({"input_name": "QM21_基体族对增强效应的异质性与跨牌号迁移.md", "snapshot_id": SNAPSHOT_ID, "source_hash": "MISSING_LOCAL_FILE_HASH", "hash_scope": "dispatch_unit", "open_status": "FULL_TEXT_READ", "role": "analysis_contract", "terminal_disposition": "USED_DIRECTLY", "blocking_gap": ""})
write_csv("INPUT_LEDGER.csv", ledger)
write_csv("SOURCE_UTILIZATION_LEDGER.csv", ledger)

source_register = []
for key, p in P.items():
    included = key in {e["paper_key"] for e in effects}
    source_register.append({"paper_key": key, **p, "included_in_effect_estimation": included, "terminal_disposition": "DIRECT_EFFECT_SOURCE" if included else "REFERENCE_ONLY_NO_MATCHED_CONTROL"})
write_csv("RELEVANT_SOURCE_REGISTER.csv", source_register)

with (ROOT / "PROVENANCE.jsonl").open("w", encoding="utf-8") as f:
    for e in effects:
        p = P[e["paper_key"]]
        rec = {
            "snapshot_id": SNAPSHOT_ID, "paper_uid": e["paper_uid"], "sample_uid_control": e["control_sample_uid"],
            "sample_uid_treatment": e["treatment_sample_uid"], "condition_uid": e["condition_uid"], "effect_uid": e["effect_uid"],
            "uid_status": e["uid_status"], "title": p["title"], "doi": p["doi"], "source_locator": e["source_locator"],
            "evidence_level": e["evidence_level"], "match_grade": e["match_grade"],
            "extracted_fields": {k: e[k] for k in ("matrix_family", "grade", "reinforcement", "dose_value", "dose_unit", "temperature_c", "test_mode", "property", "control_value", "treatment_value", "lnRR")},
            "gold_promotion_allowed": False, "production_model_registration_allowed": False,
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Figure data.
cat = [{
    "label": f"{e['grade']} | {e['property'].replace('_MPa','')} | {e['temperature_c']}C | {e['paper_key']}",
    "matrix_family": e["matrix_family"], "paper_uid": e["paper_uid"], "property": e["property"],
    "temperature_c": e["temperature_c"], "percent_change": e["percent_change"],
    "ci95_low": e["ci95_percent_low_conservative"], "ci95_high": e["ci95_percent_high_conservative"],
    "evidence_level": e["evidence_level"], "support_domain": e["support_domain"],
} for e in effects if e["property"] in strength_props]
write_csv(FIGDATA / "F1_matrix_specific_effect_caterpillar.csv", cat)
write_csv(FIGDATA / "F2_baseline_strength_gain.csv", baseline)
write_csv(FIGDATA / "F3_grade_transfer_error_matrix.csv", transfer)
write_csv(FIGDATA / "F4_overlap_ad_map.csv", overlap)

plot_code = r'''from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"figure_data"; OUT=ROOT/"figures"; OUT.mkdir(exist_ok=True)
def read(name):
    with (DATA/name).open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
def save(fig, stem):
    fig.savefig(OUT/f"{stem}.svg", bbox_inches="tight")
    fig.savefig(OUT/f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT/f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
def f1():
    d=sorted(read("F1_matrix_specific_effect_caterpillar.csv"), key=lambda r: float(r["percent_change"]))
    y=np.arange(len(d)); v=[float(r["percent_change"]) for r in d]
    fig,ax=plt.subplots(figsize=(11,max(7,0.39*len(d))))
    for i,r in enumerate(d):
        if r["ci95_low"] and r["ci95_high"]:
            ax.errorbar(v[i],y[i],xerr=[[v[i]-float(r["ci95_low"])],[float(r["ci95_high"])-v[i]]],fmt="o",capsize=3)
        else: ax.plot(v[i],y[i],"o")
    ax.axvline(0,lw=1); ax.set_yticks(y,[r["label"] for r in d]); ax.set_xlabel("Paired strength change (%)")
    ax.set_title("Matrix-specific reinforcement effects | 6 independent papers | Claim ceiling 2\nConservative CI only where both-arm SDs were reported")
    ax.grid(axis="x",alpha=.25); save(fig,"F1_matrix_specific_reinforcement_effect_caterpillar")
def f2():
    d=[r for r in read("F2_baseline_strength_gain.csv") if r["baseline_strength"] and r["percent_gain"]]
    fig,ax=plt.subplots(figsize=(10,7))
    for r in d:
        x=float(r["baseline_strength"]); y=float(r["percent_gain"]); ax.scatter([x],[y])
        ax.annotate(f"{r['grade']} {r['property'].replace('_MPa','')} {r['temperature_c']}C",(x,y),xytext=(4,4),textcoords="offset points",fontsize=7)
    ax.set_xlabel("Baseline matrix strength (MPa)"); ax.set_ylabel("Paired strength gain (%)")
    ax.set_title("Baseline strength versus reinforcement gain | Observation-level only\nNo moderation slope: confounding and regression-to-mean risk")
    ax.grid(alpha=.25); save(fig,"F2_baseline_strength_gain_relation")
def matrix_data(name, value):
    d=read(name); grades=[]
    for r in d:
        if r["source_grade"] not in grades: grades.append(r["source_grade"])
    idx={g:i for i,g in enumerate(grades)}; m=np.zeros((len(grades),len(grades)))
    for r in d: m[idx[r["source_grade"]],idx[r["target_grade"]]]=value(r)
    return d,grades,m
def f3():
    d,g,m=matrix_data("F3_grade_transfer_error_matrix.csv",lambda r:1.0 if r["source_grade"]==r["target_grade"] else 0.0)
    fig,ax=plt.subplots(figsize=(12,10)); ax.imshow(m)
    for i in range(len(g)):
        for j in range(len(g)): ax.text(j,i,"SELF" if i==j else "OOD",ha="center",va="center",fontsize=8)
    ax.set_xticks(range(len(g)),g,rotation=35,ha="right"); ax.set_yticks(range(len(g)),g)
    ax.set_xlabel("Target grade"); ax.set_ylabel("Source grade")
    ax.set_title("Grade-transfer error matrix | Numeric errors NOT IDENTIFIABLE\nOff-diagonal cells are support failures, not predictions")
    save(fig,"F3_grade_transfer_error_matrix")
def f4():
    d,g,m=matrix_data("F4_overlap_ad_map.csv",lambda r:float(r["overlap_score_descriptive"]))
    fig,ax=plt.subplots(figsize=(12,10)); im=ax.imshow(m,vmin=0,vmax=1)
    for i in range(len(g)):
        for j in range(len(g)): ax.text(j,i,f"{m[i,j]:.2f}",ha="center",va="center",fontsize=8)
    ax.set_xticks(range(len(g)),g,rotation=35,ha="right"); ax.set_yticks(range(len(g)),g)
    ax.set_xlabel("Target grade"); ax.set_ylabel("Source grade")
    ax.set_title("Overlap / applicability-domain map | Transparent six-dimension match score\nFamily, mode, temperature, reinforcement, dose basis and process")
    fig.colorbar(im,ax=ax,label="Descriptive overlap score"); save(fig,"F4_overlap_applicability_domain_map")
def main(): f1(); f2(); f3(); f4()
if __name__=="__main__": main()
'''
(PLOTS / "plot_all.py").write_text(plot_code, encoding="utf-8")
for name, fn in [("plot_F1_caterpillar.py", "f1"), ("plot_F2_baseline_gain.py", "f2"), ("plot_F3_transfer_matrix.py", "f3"), ("plot_F4_overlap_ad.py", "f4")]:
    (PLOTS / name).write_text(f"from plot_all import {fn}\nif __name__ == '__main__': {fn}()\n", encoding="utf-8")
subprocess.run([sys.executable, str(PLOTS / "plot_all.py")], cwd=PLOTS, check=True)

write_json("PLOT_SPECS.json", {
    "window_id": WINDOW_ID, "language": "English", "formats": ["SVG", "PDF", "PNG_600dpi"],
    "figures": [
        {"id": "F1", "title": "Matrix-specific reinforcement effect caterpillar", "effect_definition": "paired percent change converted from lnRR", "data": "figure_data/F1_matrix_specific_effect_caterpillar.csv", "code": "plot_code/plot_F1_caterpillar.py", "support_note": "Independent papers and evidence levels shown; conservative CI only where SDs permit."},
        {"id": "F2", "title": "Baseline strength-gain relation", "effect_definition": "baseline matrix strength versus paired percent gain", "data": "figure_data/F2_baseline_strength_gain.csv", "code": "plot_code/plot_F2_baseline_gain.py", "support_note": "Observation-level; no moderation coefficient."},
        {"id": "F3", "title": "Grade transfer error matrix", "effect_definition": "numeric transfer error requested; support status delivered", "data": "figure_data/F3_grade_transfer_error_matrix.csv", "code": "plot_code/plot_F3_transfer_matrix.py", "support_note": "Off-diagonal errors intentionally blank."},
        {"id": "F4", "title": "Overlap/applicability-domain map", "effect_definition": "transparent six-dimension overlap score", "data": "figure_data/F4_overlap_ad_map.csv", "code": "plot_code/plot_F4_overlap_ad.py", "support_note": "Rule-based audit diagnostic, not learned AD probability."},
    ],
})

(ROOT / "00_EXECUTIVE_VERDICT.md").write_text("""# QM21 执行裁决：基体族异质性与跨牌号迁移

## 一句话结论
同一种名义增强相不存在可跨牌号直接搬运的“固有强化系数”。现有证据支持同论文成对效应（Claim Level 2），不支持把 cp-Ti、Ti-6Al-4V、near-alpha、Ti65 与 beta 合金拼成可外推的 family CATE。

## 可复算锚点
- cp-Ti / 13.56 vol.% TiC+TiB：室温 YS +89.3%，UTS +74.0%；EL 由表中 29% 降至 2.6%（正文另报 32.4%，已记冲突）。这是低基线、高混杂增强体积分数、挤压取向和强界面的极端锚点，不是纯 TiB 系数。
- Ti-6Al-4V / TiBw：图读数显示 1 vol.% TiBw 的 YS 增益随长径比约 18→58 显著增加；形貌/取向可压过名义剂量。图读数未进入推断性合并。
- near-alpha TA6.5 / 0.2 wt.% B：25 C 下 UTS +6.41%、YS +9.26%、EL -6.6 个百分点；650 C 下 UTS +5.79%、YS +10.58%、EL -6.0 个百分点。
- near-alpha 高温合金 / 3 vol.% TiB：室温压缩屈服 +19.2%，微区硬度 +14.4%；alpha 层片约 3→1.5 um、长度约 35→20 um，细晶与局部载荷阻滞是核心贡献。
- Ti65 / 3.4 vol.% TiBw：主文只允许保留 600 C UTS +17%、700 C +16%。Table S1/Fig. S1 缺失，绝对增益、方差和预测区间不得编造。
- Beta 21S / TiB+TiC：压缩强度随 B4C 前驱体剂量先升后降，1.5 wt.% 达峰、3 wt.% 回落，否定“剂量越高越强”。

## 第一性机制
`Delta sigma = Delta sigma_grain + Delta sigma_load-transfer + Delta sigma_dislocation/CTE + Delta sigma_phase/precipitation - Delta sigma_damage`

基体流动应力、alpha/beta 相分数、晶粒/层片尺度、TiB 长径比与取向、网络结构、界面质量、剂量、工艺和温度共同决定净收益。

## 迁移裁决
- family random slope、跨牌号效应方差、baseline moderation slope：NOT_IDENTIFIABLE。
- LOPO/leave-family-out：多数折删除后该家族没有剩余独立论文，FAILED_SUPPORT。
- 源牌号→目标牌号非对角迁移误差：全部留空；图中只显示 OOD，不伪造数字。
- 当前包不得晋升 Gold、不得注册生产模型、不得生成 VALIDATED 配方。
""", encoding="utf-8")

(ROOT / "METHODS.md").write_text("""# METHODS

## Estimands
1. `DeltaY = Y_TMC - Y_matrix`.
2. `lnRR = ln(Y_TMC/Y_matrix)` for positive quantities.
3. `100*(exp(lnRR)-1)`.
4. Requested but not identified: family CATE, between-grade variance, baseline moderation slope and source-to-target transfer error.

## Atomicity and matching
One row is paper × sample × actual composition × precursor/actual phase × process × heat treatment × microstructure state × test mode × temperature × property. Tensile/compression, temperature, process and heat-treatment states were never merged. Grade A is same-paper/same-condition control; Grade B is evidence-limited matched contrast.

## Uncertainty
Where both arms reported SDs, conservative independent-arm approximations were used: `SE(Delta)=sqrt(SD_TMC^2+SD_matrix^2)` and `SE(lnRR)=sqrt((SD_TMC/Y_TMC)^2+(SD_matrix/Y_matrix)^2)`. Paired covariance is unavailable. SD was never reverse-engineered.

## Hierarchical model gate
The preregistered skeleton was retained but not fitted: `g(E[Y]) = beta0 + beta_r*reinforcement + f(dose) + beta_m*matrix + beta_p*process + beta_t*condition + interactions + u_paper + u_matrix + epsilon`. Matrix family is effectively aliased with paper, route, property mode, reinforcement identity and dose basis. Fitting would manufacture precision.

## Baseline moderation
The panel is observation-level only. Baseline appears in both denominator and contrast, creating mathematical coupling/regression-to-mean risk; paper/process/property mode remain confounded.

## Transfer and AD
Leave-grade/family-out needs a common frozen feature matrix, labels, official split manifest and target observations. Missing inputs make off-diagonal errors non-identifiable. The overlap map is a transparent six-dimension diagnostic, not a learned probability.

## Reproducibility
Every quantitative figure has CSV data and Python code. `plot_code/plot_all.py` regenerates SVG/PDF/600 dpi PNG. Tests enforce schemas, provenance, claim ceiling and blank off-diagonal transfer errors.
""", encoding="utf-8")

(ROOT / "LIMITATIONS.md").write_text("""# LIMITATIONS
1. Authoritative Q40 snapshot and official V29 UIDs were absent; all UIDs are deterministic provisional web UIDs.
2. Matrix family, paper, process, property mode, reinforcement identity and dose basis are strongly confounded.
3. Ti65 Table S1/Fig. S1 is missing; only relative +17/+16% is retained.
4. Ti-6Al-4V values are figure-derived approximations, not Gold-grade numeric evidence.
5. Actual TiB vol.% is unavailable for TA6.5 0.2 wt.% B; actual TiB/TiC fractions are unavailable for Beta21S B4C additions.
6. Tensile and compression effects are not pooled; nanoindentation is not bulk strength.
7. Replicate-level data and paired covariance are mostly absent; prediction intervals cannot be estimated honestly.
8. The overlap score is an audit diagnostic, not a probabilistic AD model.
9. Nothing in this package is production-model evidence, Gold promotion or a validated recipe.
""", encoding="utf-8")

request = {
    "window_id": WINDOW_ID, "status": STATUS,
    "required_inputs": [
        {"item": "Q40_INPUT_SNAPSHOT.json", "purpose": "authoritative snapshot hash/member map", "priority": "P0"},
        {"item": "V29 ATOMIC_RECORDS.*, PROVENANCE.jsonl, CONFLICT_LEDGER.csv, EXCLUDED_RECORDS.csv, paper/source registry", "purpose": "official cohort/provenance binding", "priority": "P0"},
        {"item": "official paper_uid/sample_uid/condition_uid maps", "purpose": "replace provisional UIDs", "priority": "P0"},
        {"item": "Xiong 2024 Table S1 and Fig. S1", "purpose": "Ti65 absolute UTS/YS/EL and uncertainty at 600/700 C", "priority": "P0"},
        {"item": "Koo 2012 raw numeric tensile table or validated digitization", "purpose": "replace approximate Ti64 values", "priority": "P1"},
        {"item": "replicate-level or SD/SE data for Ma 2020, Rielli 2020 and Sun 2021", "purpose": "cluster uncertainty/prediction intervals", "priority": "P1"},
        {"item": "actual TiB vol.% for 0.2 wt.% B TA6.5", "purpose": "unit-content efficiency", "priority": "P1"},
        {"item": "actual TiB/TiC fractions for Beta21S B4C series", "purpose": "phase-resolved dose response", "priority": "P1"},
        {"item": "top-level archive SHA-256 and member hashes", "purpose": "bind INPUT_LEDGER", "priority": "P0"},
    ],
    "acceptance": "After absorption, rerun matched effects, random-slope partial pooling, paper-cluster bootstrap, LOPO and leave-family/grade-out; production registration remains forbidden.",
}
write_json("WEB_TO_LOCAL_REQUEST.json", request)

(ROOT / "LOCAL_ABSORPTION_PROMPT.md").write_text("""# LOCAL ABSORPTION PROMPT — QM21
1. Verify FINAL_QM21.zip SHA-256 and extract into exclusive q40/QM21 staging. Do not modify ACTIVE/Gold/production registries.
2. Replace every provisional UID only through authoritative V29 maps; emit one-to-one crosswalk and reject ambiguity.
3. Bind every input to Q40_INPUT_SNAPSHOT.json, archive SHA-256 and member hash; no PENDING disposition.
4. Supply Xiong Table S1/Fig. S1, validated Koo numeric data, replicate uncertainty and actual phase fractions in WEB_TO_LOCAL_REQUEST.json.
5. Fit the declared mixed model only after support gates pass; execute paper-cluster bootstrap, LOPO and leave-family/grade-out. OOD grades remain hypotheses.
6. Run `python -m unittest discover -s tests -v`, regenerate figures, validate MANIFEST/CHECKSUMS and issue a new immutable package.
7. Never promote this web return to Gold or register a production SUP/SSL model from it.
""", encoding="utf-8")

status = {
    "window_id": WINDOW_ID, "snapshot_id": SNAPSHOT_ID, "papers_seen": 8, "papers_included": 6,
    "independent_papers": 6, "atomic_rows": len(atomic), "matched_pairs": len(pairs), "effect_estimates": len(effects),
    "plots_generated": 4, "open_conflicts": len(conflicts), "claim_level_max": CLAIM_LEVEL_MAX,
    "status": STATUS, "next_action": "LOCAL_ABSORB_AND_RE-RUN_HIERARCHICAL_TRANSFER",
    "production_model_registration": "FORBIDDEN", "gold_promotion": "FORBIDDEN",
}
write_json("WINDOW_STATUS.json", status)

(ROOT / "README.md").write_text("""# FINAL_QM21
Quantitative return for matrix-family heterogeneity and cross-grade transfer of TiB/TiBw-containing titanium matrix composites.

Run:
```bash
python plot_code/plot_all.py
python -m unittest discover -s tests -v
```

Boundary: within-paper effects and OOD diagnostics only. No identified family CATE, numeric off-diagonal transfer error, production model, Gold promotion or validated recipe.
""", encoding="utf-8")
(ROOT / "requirements.txt").write_text("matplotlib==3.10.3\nnumpy==2.2.6\n", encoding="utf-8")
(ROOT / "acceptance_commands.md").write_text("""# Acceptance commands
```bash
python plot_code/plot_all.py
python -m unittest discover -s tests -v
python - <<'PY'
from pathlib import Path
import hashlib
root=Path('.')
for line in (root/'CHECKSUMS.sha256').read_text().splitlines():
    digest, rel=line.split('  ',1)
    assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest, rel
print('CHECKSUMS_OK')
PY
```
""", encoding="utf-8")

# Seven contract tests.
test_code = r'''import csv, hashlib, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Contract(unittest.TestCase):
    def test_required_files(self):
        req=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MATRIX_CATE.csv","GRADE_TRANSFER_MATRIX.csv","BASELINE_MODERATION.csv","MATRIX_OVERLAP.csv","MANIFEST.json","CHECKSUMS.sha256"]
        self.assertEqual([x for x in req if not (ROOT/x).exists()],[])
    def test_effect_provenance(self):
        rows=list(csv.DictReader((ROOT/"EFFECT_ESTIMATES.csv").open(encoding="utf-8-sig")))
        self.assertEqual(len(rows),28)
        for r in rows:
            for k in ["paper_uid","control_sample_uid","treatment_sample_uid","condition_uid","source_locator"]: self.assertTrue(r[k])
    def test_transfer_errors_blank(self):
        rows=list(csv.DictReader((ROOT/"GRADE_TRANSFER_MATRIX.csv").open(encoding="utf-8-sig")))
        for r in rows:
            if r["source_grade"]!=r["target_grade"]:
                self.assertEqual(r["transfer_error"],""); self.assertIn("OOD",r["support_status"])
    def test_claim_locks(self):
        s=json.loads((ROOT/"WINDOW_STATUS.json").read_text())
        self.assertLessEqual(s["claim_level_max"],2); self.assertEqual(s["production_model_registration"],"FORBIDDEN"); self.assertEqual(s["gold_promotion"],"FORBIDDEN")
    def test_figures(self):
        stems=["F1_matrix_specific_reinforcement_effect_caterpillar","F2_baseline_strength_gain_relation","F3_grade_transfer_error_matrix","F4_overlap_applicability_domain_map"]
        for stem in stems:
            for ext in ["svg","pdf","png"]: self.assertGreater((ROOT/"figures"/f"{stem}.{ext}").stat().st_size,0)
    def test_checksums(self):
        for line in (ROOT/"CHECKSUMS.sha256").read_text().splitlines():
            d,r=line.split("  ",1); self.assertEqual(hashlib.sha256((ROOT/r).read_bytes()).hexdigest(),d,r)
    def test_status_data_gap(self):
        s=json.loads((ROOT/"WINDOW_STATUS.json").read_text()); self.assertEqual(s["status"],"CONTINUE_DATA_GAP"); self.assertEqual(s["snapshot_id"],"MISSING_Q40_INPUT_SNAPSHOT")
if __name__=="__main__": unittest.main()
'''
(TESTS / "test_contract.py").write_text(test_code, encoding="utf-8")

# Run tests before final hashes; checksum test is skipped until hashes exist.
pre = subprocess.run([sys.executable, "-m", "unittest", "tests.test_contract.Contract.test_effect_provenance", "tests.test_contract.Contract.test_transfer_errors_blank", "tests.test_contract.Contract.test_claim_locks", "tests.test_contract.Contract.test_figures", "tests.test_contract.Contract.test_status_data_gap", "-v"], cwd=ROOT, capture_output=True, text=True)
(ROOT / "self_test_output.txt").write_text(pre.stdout + "\n" + pre.stderr + f"\nreturncode={pre.returncode}\n", encoding="utf-8")
if pre.returncode:
    raise SystemExit(pre.returncode)

# Final manifest and checksums; exclude the two circular files from manifest entries.
files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"})
manifest = {
    "window_id": WINDOW_ID, "snapshot_id": SNAPSHOT_ID, "status": STATUS, "claim_level_max": CLAIM_LEVEL_MAX,
    "file_count_excluding_manifest_and_checksums": len(files),
    "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    "notes": "MANIFEST.json and CHECKSUMS.sha256 are excluded from manifest entries to avoid circular self-hashing; CHECKSUMS includes MANIFEST.json.",
}
write_json("MANIFEST.json", manifest)
checksum_files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
(ROOT / "CHECKSUMS.sha256").write_text("\n".join(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}" for p in checksum_files) + "\n", encoding="utf-8")

# Full validation now does not modify package.
full = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, capture_output=True, text=True)
if full.returncode:
    print(full.stdout); print(full.stderr, file=sys.stderr); raise SystemExit(full.returncode)

zip_path = BUILD / "FINAL_QM21.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_file(): z.write(p, (Path("FINAL_QM21") / p.relative_to(ROOT)).as_posix())
zip_sha = sha(zip_path)
(BUILD / "FINAL_QM21.sha256").write_text(f"{zip_sha}  FINAL_QM21.zip\n", encoding="utf-8")
summary = {"window_id": WINDOW_ID, "zip": str(zip_path), "zip_sha256": zip_sha, "zip_bytes": zip_path.stat().st_size, "status": STATUS, "papers_seen": 8, "papers_included": 6, "effects": len(effects), "matched_pairs": len(pairs), "atomic_rows": len(atomic), "plots": 4, "tests": 7}
(BUILD / "build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
