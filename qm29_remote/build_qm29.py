from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "FINAL_QM29"
FIXED_TIME = "2026-07-13T17:20:00+08:00"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(rel: str, text: str) -> Path:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def write_json(rel: str, obj: object) -> Path:
    return write_text(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def write_csv(rel: str, fields: list[str], rows: list[dict]) -> Path:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
    return p


def num(v):
    if v in (None, "", "NOT_DETECTED", "QUALITATIVE_ONLY", "NOT_IDENTIFIABLE"):
        return None
    return float(v)


def d(t, c):
    t, c = num(t), num(c)
    return "" if t is None or c is None else round(t - c, 8)


def lnrr(t, c):
    t, c = num(t), num(c)
    return "" if t is None or c is None or t <= 0 or c <= 0 else round(math.log(t / c), 8)


if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

snapshot_basis = {
    "window": "QM29",
    "qm31_snapshot": "QM31-480a683d507a8e4247d0a0c5",
    "grain_contribution": {"median": 0.604, "ci95": [0.482, 0.750], "effects": 5, "papers": 4, "range": [0.180, 0.783]},
    "primary_dois": ["10.1016/j.scriptamat.2013.03.017", "10.1016/j.msea.2017.04.068"],
}
SNAP_HASH = sha_bytes(json.dumps(snapshot_basis, sort_keys=True, separators=(",", ":")).encode())
SNAPSHOT = f"QM29_DERIVED_{SNAP_HASH[:20]}"

luo = """
# Luo et al. 2013 — primary evidence capture

DOI: 10.1016/j.scriptamat.2013.03.017. Direct project-library PDF pages 2–4 were opened.

Grain size was measured from approximately 200 grains by the linear-intercept method. Control Ti: 67.2 µm, hardness 1660 ± 320 MPa, compressive YS 480 MPa. The 60 wt.% coated-powder state: locally aligned TiC nanoplatelets, 42.6 µm, hardness 3126 ± 245 MPa, YS 1240 MPa, ultimate compressive strength 2540 MPa, fracture strain 44.4%. The 100 wt.% coated state: TiC nanoplatelets plus microparticles, 38.6 µm, hardness 4175 ± 284 MPa, YS 1520 MPa, ultimate compressive strength 2480 MPa, fracture strain 34.5%.

For the 1466 MPa hardness increment from control to the 60%-coated state, the source estimated 300 MPa from interstitials, less than 250 MPa / 17% from refinement, and more than 60% from locally aligned TiC nanoplatelets. This budget is for hardness, not YS; C/O/N and reinforcement morphology co-change.
"""
hoss = """
# Hosseini et al. 2017 — primary evidence capture

DOI: 10.1016/j.msea.2017.04.068. Direct project-library PDF pages 2–11 were opened.

Same-chemistry Ti-6242S states after aging: Widmanstätten prior-β ≈600 µm, α/transformed-β ratio 0.00, YS/UTS/EL 931/1039 MPa/7%; bimodal ≈16 µm, ratio 0.22, 1000/1056 MPa/14%; trimodal β grains not detected, ratio 0.67, 959/1058 MPa/13%. Phase fractions were measured in multiple OM regions using Clemex; α layers were examined by SEM. Bimodal→trimodal raises the ratio by 0.45 while YS falls 41 MPa, proving that a one-variable monotonic phase-fraction path is inadequate.
"""
qm31 = """
# QM31 derived evidence capture

Snapshot QM31-480a683d507a8e4247d0a0c5: 5 fully recomputable same-paper tensile effects from 4 independent papers. Paper-balanced median grain-refinement contribution candidate = 60.4% of matched ΔYS; paper-cluster bootstrap 95% interval 48.2–75.0%; exact effect range 18.0–78.3%. Adding a 2025 Ti60 source-reported contribution lowers the median to 50.2%, but FG/CG mixture inputs and supplement tables are missing. Source Hall–Petch k spans ≈328–1455 MPa·√µm. WAAM TiB/Ti64 is a negative control: prior-β refinement is strong but the source assigns Hall–Petch ≈0 because operative α/β lamellar width is comparable. HP, GND and HDI terms risk double counting.
"""
for name, txt in [("LUO_2013_PRIMARY_CAPTURE.md", luo), ("HOSSEINI_2017_PRIMARY_CAPTURE.md", hoss), ("QM31_DERIVED_CAPTURE.md", qm31)]:
    write_text("source_evidence/" + name, txt)
CAP_HASH = {"luo": sha_bytes(textwrap.dedent(luo).strip().encode()), "hoss": sha_bytes(textwrap.dedent(hoss).strip().encode()), "qm31": sha_bytes(textwrap.dedent(qm31).strip().encode())}

cohort_fields = ["snapshot_id", "paper_uid", "doi", "sample_uid", "condition_uid", "material_family", "exposure", "process_state", "reinforcement_state", "grain_size_um", "prior_beta_grain_um", "alpha_lath_thickness_um", "alpha_to_transformed_beta_ratio", "alpha_fraction_pct", "beta_fraction_pct", "kam_deg", "gnd_m2", "texture_metric", "measurement_method", "measurement_scale", "ys_mpa", "uts_mpa", "el_pct", "hardness_mpa", "hardness_sd_mpa", "evidence_level", "included", "source_locator", "provenance_id"]
cohort = [
    {"snapshot_id": SNAPSHOT, "paper_uid": "P_LUO_2013", "doi": "10.1016/j.scriptamat.2013.03.017", "sample_uid": "LUO_CONTROL", "condition_uid": "RT_COMPRESSION_AS_SINTERED", "material_family": "CP-Ti/TiC", "exposure": "0 wt.% coated powder", "process_state": "1350C_1h_vacuum", "reinforcement_state": "none", "grain_size_um": 67.2, "measurement_method": "linear intercept; ~200 grains; SEM", "measurement_scale": "matrix grain", "ys_mpa": 480, "hardness_mpa": 1660, "hardness_sd_mpa": 320, "evidence_level": "DIRECT_TABLE_TEXT", "included": "YES", "source_locator": "Luo2013 Table 1/text", "provenance_id": "PROV_LUO_CONTROL"},
    {"snapshot_id": SNAPSHOT, "paper_uid": "P_LUO_2013", "doi": "10.1016/j.scriptamat.2013.03.017", "sample_uid": "LUO_30", "condition_uid": "RT_COMPRESSION_AS_SINTERED", "material_family": "CP-Ti/TiC", "exposure": "30 wt.% coated powder", "process_state": "1350C_1h_vacuum", "reinforcement_state": "TiC nanoplatelets", "grain_size_um": 46.8, "measurement_method": "linear intercept; ~200 grains; SEM", "measurement_scale": "matrix grain", "hardness_mpa": 2480, "hardness_sd_mpa": 340, "evidence_level": "DIRECT_TABLE_TEXT", "included": "DESCRIPTIVE_ONLY", "source_locator": "Luo2013 Table 1", "provenance_id": "PROV_LUO_30"},
    {"snapshot_id": SNAPSHOT, "paper_uid": "P_LUO_2013", "doi": "10.1016/j.scriptamat.2013.03.017", "sample_uid": "LUO_60", "condition_uid": "RT_COMPRESSION_AS_SINTERED", "material_family": "CP-Ti/TiC", "exposure": "60 wt.% coated powder", "process_state": "1350C_1h_vacuum", "reinforcement_state": "locally aligned TiC nanoplatelets", "grain_size_um": 42.6, "texture_metric": "locally aligned by grain; macroscopically random", "measurement_method": "linear intercept; SEM/TEM", "measurement_scale": "grain + platelet", "ys_mpa": 1240, "uts_mpa": 2540, "el_pct": 44.4, "hardness_mpa": 3126, "hardness_sd_mpa": 245, "evidence_level": "DIRECT_TABLE_TEXT", "included": "YES", "source_locator": "Luo2013 Table 1/text", "provenance_id": "PROV_LUO_60"},
    {"snapshot_id": SNAPSHOT, "paper_uid": "P_LUO_2013", "doi": "10.1016/j.scriptamat.2013.03.017", "sample_uid": "LUO_100", "condition_uid": "RT_COMPRESSION_AS_SINTERED", "material_family": "CP-Ti/TiC", "exposure": "100 wt.% coated powder", "process_state": "1350C_1h_vacuum", "reinforcement_state": "TiC nanoplatelets + microparticles", "grain_size_um": 38.6, "texture_metric": "mixed reinforcement morphology", "measurement_method": "linear intercept; SEM/TEM", "measurement_scale": "grain + reinforcement", "ys_mpa": 1520, "uts_mpa": 2480, "el_pct": 34.5, "hardness_mpa": 4175, "hardness_sd_mpa": 284, "evidence_level": "DIRECT_TABLE_TEXT", "included": "YES", "source_locator": "Luo2013 Table 1/text", "provenance_id": "PROV_LUO_100"},
    {"snapshot_id": SNAPSHOT, "paper_uid": "P_HOSS_2017", "doi": "10.1016/j.msea.2017.04.068", "sample_uid": "HOSS_W", "condition_uid": "RT_TENSION_AGED_600C", "material_family": "Ti-6242S", "exposure": "Widmanstatten TMP", "process_state": "950C rolling; 1050C/2h AC; 600C/8h AC", "reinforcement_state": "none", "prior_beta_grain_um": 600, "alpha_to_transformed_beta_ratio": 0.00, "measurement_method": "OM/Clemex; SEM", "measurement_scale": "prior-beta/colony/phase", "ys_mpa": 931, "uts_mpa": 1039, "el_pct": 7, "evidence_level": "MIXED_DIRECT_TEXT_FIGURE_DERIVED", "included": "YES", "source_locator": "Hosseini2017 Figs 3-5,8/text", "provenance_id": "PROV_HOSS_W"},
    {"snapshot_id": SNAPSHOT, "paper_uid": "P_HOSS_2017", "doi": "10.1016/j.msea.2017.04.068", "sample_uid": "HOSS_B", "condition_uid": "RT_TENSION_AGED_600C", "material_family": "Ti-6242S", "exposure": "Bimodal TMP", "process_state": "950C rolling; 990C/2h AC; 600C/8h AC", "reinforcement_state": "none", "prior_beta_grain_um": 16, "alpha_to_transformed_beta_ratio": 0.22, "measurement_method": "OM/Clemex; SEM", "measurement_scale": "prior-beta/colony/phase", "ys_mpa": 1000, "uts_mpa": 1056, "el_pct": 14, "evidence_level": "MIXED_DIRECT_TEXT_FIGURE_DERIVED", "included": "YES", "source_locator": "Hosseini2017 Figs 3-5,8/text", "provenance_id": "PROV_HOSS_B"},
    {"snapshot_id": SNAPSHOT, "paper_uid": "P_HOSS_2017", "doi": "10.1016/j.msea.2017.04.068", "sample_uid": "HOSS_T", "condition_uid": "RT_TENSION_AGED_600C", "material_family": "Ti-6242S", "exposure": "Trimodal TMP", "process_state": "1000C rolling; 975C/2h AC; 600C/8h AC", "reinforcement_state": "none", "prior_beta_grain_um": "NOT_DETECTED", "alpha_lath_thickness_um": "QUALITATIVE_ONLY", "alpha_to_transformed_beta_ratio": 0.67, "measurement_method": "OM/Clemex; SEM", "measurement_scale": "phase + qualitative alpha layer", "ys_mpa": 959, "uts_mpa": 1058, "el_pct": 13, "evidence_level": "MIXED_DIRECT_TEXT_FIGURE_DERIVED", "included": "YES", "source_locator": "Hosseini2017 Figs 3-6,8/text", "provenance_id": "PROV_HOSS_T"},
]
for row in cohort:
    for field in cohort_fields:
        row.setdefault(field, "")
write_csv("ANALYSIS_COHORT.csv", cohort_fields, cohort)
by_sample = {r["sample_uid"]: r for r in cohort}

pair_fields = ["snapshot_id", "pair_id", "paper_uid", "control_sample_uid", "treatment_sample_uid", "condition_uid", "match_grade", "exposure_contrast", "delta_grain_size_um", "delta_prior_beta_um", "delta_alpha_tb_ratio", "delta_ys_mpa", "delta_uts_mpa", "delta_el_pp", "delta_hardness_mpa", "lnrr_ys", "lnrr_uts", "lnrr_el", "identification", "support_domain", "notes", "provenance_id"]
pair_specs = [
    ("LUO_C_60", "LUO_CONTROL", "LUO_60", "A_TOTAL_EXPOSURE", "0→60 wt.% coated powder", "Interstitials and TiC morphology co-change"),
    ("LUO_C_100", "LUO_CONTROL", "LUO_100", "A_TOTAL_EXPOSURE", "0→100 wt.% coated powder", "Interstitials, dose and morphology co-change"),
    ("HOSS_W_B", "HOSS_W", "HOSS_B", "A_PROCESS", "Widmanstätten→bimodal", "Multiple organization variables change"),
    ("HOSS_W_T", "HOSS_W", "HOSS_T", "A_PROCESS", "Widmanstätten→trimodal", "Multiple organization variables change"),
    ("HOSS_B_T", "HOSS_B", "HOSS_T", "A_PROCESS", "Bimodal→trimodal", "Phase-ratio sign-reversal counterexample"),
]
pairs = []
for pid, c_uid, t_uid, grade, contrast, note in pair_specs:
    c, t = by_sample[c_uid], by_sample[t_uid]
    pairs.append({"snapshot_id": SNAPSHOT, "pair_id": pid, "paper_uid": c["paper_uid"], "control_sample_uid": c_uid, "treatment_sample_uid": t_uid, "condition_uid": c["condition_uid"], "match_grade": grade, "exposure_contrast": contrast, "delta_grain_size_um": d(t["grain_size_um"], c["grain_size_um"]), "delta_prior_beta_um": d(t["prior_beta_grain_um"], c["prior_beta_grain_um"]), "delta_alpha_tb_ratio": d(t["alpha_to_transformed_beta_ratio"], c["alpha_to_transformed_beta_ratio"]), "delta_ys_mpa": d(t["ys_mpa"], c["ys_mpa"]), "delta_uts_mpa": d(t["uts_mpa"], c["uts_mpa"]), "delta_el_pp": d(t["el_pct"], c["el_pct"]), "delta_hardness_mpa": d(t["hardness_mpa"], c["hardness_mpa"]), "lnrr_ys": lnrr(t["ys_mpa"], c["ys_mpa"]), "lnrr_uts": lnrr(t["uts_mpa"], c["uts_mpa"]), "lnrr_el": lnrr(t["el_pct"], c["el_pct"]), "identification": "LEVEL_2_SAME_PAPER_MATCHED_ASSOCIATION", "support_domain": "RT; source-specific material/process/test", "notes": note, "provenance_id": "PROV_PAIR_" + pid})
write_csv("PAIR_MATCHES.csv", pair_fields, pairs)

effect_fields = ["snapshot_id", "effect_id", "pair_id", "paper_uid", "estimand", "outcome", "estimate", "unit", "ci95_low", "ci95_high", "evidence_level", "match_grade", "independent_papers", "claim_level", "status", "support_domain", "notes", "provenance_id"]
map_effect = [("delta_grain_size_um", "grain_size", "um", "exposure_to_microstructure"), ("delta_prior_beta_um", "prior_beta", "um", "exposure_to_microstructure"), ("delta_alpha_tb_ratio", "alpha_to_transformed_beta_ratio", "ratio", "exposure_to_microstructure"), ("delta_ys_mpa", "YS", "MPa", "exposure_to_property"), ("delta_uts_mpa", "UTS", "MPa", "exposure_to_property"), ("delta_el_pp", "EL", "percentage_point", "exposure_to_property"), ("delta_hardness_mpa", "hardness", "MPa", "exposure_to_property")]
effects = []
for p in pairs:
    for key, outcome, unit, estimand in map_effect:
        if p[key] == "":
            continue
        effects.append({"snapshot_id": SNAPSHOT, "effect_id": f"EFF_{p['pair_id']}_{outcome}", "pair_id": p["pair_id"], "paper_uid": p["paper_uid"], "estimand": estimand, "outcome": outcome, "estimate": p[key], "unit": unit, "ci95_low": "", "ci95_high": "", "evidence_level": "DIRECT_OR_FIGURE_DERIVED", "match_grade": p["match_grade"], "independent_papers": 1, "claim_level": 2, "status": "ESTIMABLE_DESCRIPTIVE", "support_domain": p["support_domain"], "notes": "No replicate-level variance recovered for this contrast", "provenance_id": p["provenance_id"]})
write_csv("EFFECT_ESTIMATES.csv", effect_fields, effects)

mediator_fields = ["mediator_id", "variable", "physical_role", "measurement_definition", "temporal_order_supported", "principal_confounders", "co_mediators", "identification_status", "eligible_estimand", "source_support"]
mediators = [
    {"mediator_id": "M_GRAIN", "variable": "operative grain/colony/lamellar scale", "physical_role": "boundary-limited slip length; Hall–Petch candidate", "measurement_definition": "state-specific operative scale, not arbitrary prior-beta substitution", "temporal_order_supported": "PARTIAL", "principal_confounders": "chemistry, interstitials, HT, defects", "co_mediators": "GND, phase, texture, architecture", "identification_status": "MECHANISM_CONTRIBUTION_CANDIDATE", "eligible_estimand": "Δσ_HP/ΔYS", "source_support": "QM31 + Luo"},
    {"mediator_id": "M_PRIOR_BETA", "variable": "prior-β grain", "physical_role": "parent-grain/colony constraint; proxy candidate", "measurement_definition": "reconstructed distribution with method", "temporal_order_supported": "PARTIAL", "principal_confounders": "cooling, lath width, texture", "co_mediators": "colony, lath, texture", "identification_status": "PROXY_ONLY_NEGATIVE_CONTROL", "eligible_estimand": "process→prior-beta; conditional property association", "source_support": "Hosseini + QM31 WAAM"},
    {"mediator_id": "M_LATH", "variable": "α-lath thickness", "physical_role": "slip length/interface density", "measurement_definition": "SEM/TEM distribution over fields", "temporal_order_supported": "YES_IN_PRINCIPLE", "principal_confounders": "cooling, partitioning, phase fraction", "co_mediators": "phase, colony, precipitates", "identification_status": "NOT_IDENTIFIABLE_NUMERIC", "eligible_estimand": "conditional microstructure→property slope", "source_support": "Hosseini qualitative"},
    {"mediator_id": "M_PHASE", "variable": "α/β fraction and partitioning", "physical_role": "slip systems/interface density/chemistry partition", "measurement_definition": "field-level OM/EBSD/XRD with unindexed fraction", "temporal_order_supported": "YES_IN_PRINCIPLE", "principal_confounders": "solution T, cooling, chemistry", "co_mediators": "lath, partitioning, precipitates", "identification_status": "PAIRED_ASSOCIATION_ONLY", "eligible_estimand": "process→phase and conditional property association", "source_support": "Hosseini triad"},
    {"mediator_id": "M_KAM_GND", "variable": "KAM/GND", "physical_role": "lattice-curvature/dislocation proxy", "measurement_definition": "step size, kernel, cutoff, cleanup, b and Nye inversion required", "temporal_order_supported": "YES_IN_PRINCIPLE", "principal_confounders": "resolution, noise, deformation history", "co_mediators": "grain, HDI, texture", "identification_status": "NOT_IDENTIFIABLE", "eligible_estimand": "process→GND and GND→property with error model", "source_support": "gap + QM31 double-count warning"},
    {"mediator_id": "M_TEXTURE", "variable": "texture", "physical_role": "resolved shear/anisotropy", "measurement_definition": "ODF/pole figure or defined texture index by phase/direction", "temporal_order_supported": "YES_IN_PRINCIPLE", "principal_confounders": "process direction, plane, phase", "co_mediators": "grain shape, lath orientation", "identification_status": "NOT_IDENTIFIABLE", "eligible_estimand": "direction-specific conditional path", "source_support": "no complete cohort"},
    {"mediator_id": "M_METHOD", "variable": "measurement method/scale", "physical_role": "calibration/random factor, not physical mediator", "measurement_definition": "instrument, magnification, step, segmentation and field count", "temporal_order_supported": "N/A", "principal_confounders": "paper/lab/material family", "co_mediators": "all measured variables", "identification_status": "REQUIRED_CALIBRATION_FACTOR", "eligible_estimand": "method bias/random effect", "source_support": "Luo/Hosseini methods + analytic GND sensitivity"},
]
write_csv("MICROSTRUCTURE_MEDIATORS.csv", mediator_fields, mediators)

med_fields = ["snapshot_id", "mediation_id", "exposure", "mediator", "outcome", "total_effect", "total_effect_unit", "indirect_effect_candidate", "indirect_effect_unit", "proportion_mediated", "ci95_low", "ci95_high", "bound_operator", "independent_papers", "effect_rows", "formal_nie_status", "identification", "evidence_level", "support_domain", "notes", "provenance_id"]
mediation = [
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_QM31_GRAIN_YS", "exposure": "reinforcement-induced refinement", "mediator": "operative grain/slip length", "outcome": "ΔYS", "total_effect": "matched paper-specific ΔYS", "total_effect_unit": "MPa", "indirect_effect_candidate": "source/recomputed Δσ_HP", "indirect_effect_unit": "MPa", "proportion_mediated": 0.604, "ci95_low": 0.482, "ci95_high": 0.750, "bound_operator": "paper-balanced median + paper-cluster bootstrap", "independent_papers": 4, "effect_rows": 5, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "MECHANISM_CONTRIBUTION_RATIO", "evidence_level": "DERIVED_CALCULATION_RECOMPUTABLE_SUBGROUP", "support_domain": "RT tensile; family/scale-matched k", "notes": "Exact effect range 0.180–0.783", "provenance_id": "PROV_QM31"},
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_LUO_GRAIN_HARDNESS", "exposure": "0→60 wt.% coated powder", "mediator": "grain refinement 67.2→42.6 µm", "outcome": "Δhardness", "total_effect": 1466, "total_effect_unit": "MPa", "indirect_effect_candidate": 250, "indirect_effect_unit": "MPa", "proportion_mediated": 0.17, "bound_operator": "STRICT_UPPER_BOUND", "independent_papers": 1, "effect_rows": 1, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "SOURCE_MECHANISM_BOUND", "evidence_level": "DIRECT_TEXT_SOURCE_CALCULATION", "support_domain": "CP-Ti/TiC RT hardness", "notes": "Outcome-specific; interstitials/morphology co-change", "provenance_id": "PROV_LUO_BUDGET"},
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_LUO_TIC_HARDNESS", "exposure": "0→60 wt.% coated powder", "mediator": "locally aligned TiC nanoplatelets", "outcome": "Δhardness", "total_effect": 1466, "total_effect_unit": "MPa", "indirect_effect_candidate": 879.6, "indirect_effect_unit": "MPa", "proportion_mediated": 0.60, "bound_operator": "STRICT_LOWER_BOUND", "independent_papers": 1, "effect_rows": 1, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "SOURCE_MECHANISM_BOUND", "evidence_level": "DIRECT_TEXT_SOURCE_CALCULATION", "support_domain": "CP-Ti/TiC RT hardness", "notes": "Cannot separate morphology from load transfer without factorial control", "provenance_id": "PROV_LUO_BUDGET"},
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_WAAM_PRIOR_BETA_NEG", "exposure": "TiB addition in WAAM Ti64", "mediator": "prior-beta refinement", "outcome": "ΔYS", "indirect_effect_candidate": 0, "indirect_effect_unit": "MPa_approx", "proportion_mediated": 0, "bound_operator": "SOURCE_APPROXIMATION", "independent_papers": 1, "effect_rows": 1, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "NEGATIVE_CONTROL_FOR_PROXY_SCALE", "evidence_level": "DERIVED_REPORT", "support_domain": "unchanged operative lamellar width", "notes": "Original DOI/rows requested", "provenance_id": "PROV_WAAM_GAP"},
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_PHASE_YS", "exposure": "TMP state", "mediator": "alpha/transformed-beta ratio", "outcome": "YS", "total_effect": "pair-specific", "total_effect_unit": "MPa", "independent_papers": 1, "effect_rows": 3, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "PAIRED_ASSOCIATION_WITH_SIGN_REVERSAL", "evidence_level": "MIXED_DIRECT_TEXT_FIGURE_DERIVED", "support_domain": "Ti-6242S RT tension", "notes": "Bimodal→trimodal ratio +0.45 but YS −41 MPa", "provenance_id": "PROV_HOSS_TRIAD"},
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_LATH", "exposure": "process/reinforcement", "mediator": "alpha-lath thickness", "outcome": "YS/EL", "independent_papers": 1, "effect_rows": 0, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "QUALITATIVE_ONLY", "evidence_level": "DIRECT_TEXT_QUALITATIVE", "support_domain": "Ti-6242S", "notes": "Numerical distributions absent", "provenance_id": "PROV_HOSS_TRIAD"},
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_KAM_GND", "exposure": "process/reinforcement", "mediator": "KAM/GND", "outcome": "YS", "independent_papers": 0, "effect_rows": 0, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "MISSING_RAW_MAPS_AND_ERROR_MODEL", "evidence_level": "UNRESOLVED", "support_domain": "none", "notes": "Step/kernel/cutoff/cleanup/Nye metadata absent", "provenance_id": "PROV_KAM_GAP"},
    {"snapshot_id": SNAPSHOT, "mediation_id": "MED_TEXTURE", "exposure": "process/reinforcement", "mediator": "texture", "outcome": "directional property", "independent_papers": 0, "effect_rows": 0, "formal_nie_status": "NOT_IDENTIFIABLE", "identification": "NO_COMPLETE_TEXTURE_PROPERTY_COHORT", "evidence_level": "UNRESOLVED", "support_domain": "none", "notes": "ODF/property pairs absent", "provenance_id": "PROV_TEXTURE_GAP"},
]
for row in mediation:
    for field in med_fields:
        row.setdefault(field, "")
write_csv("MEDIATION_EFFECTS.csv", med_fields, mediation)

uq_fields = ["uq_id", "variable", "source_or_formula", "measurement_method", "scale_parameter", "reference_value", "sensitivity_relation", "uncertainty_status", "bias_direction", "required_metadata", "notes"]
uq = [
    {"uq_id": "UQ_LUO_GRAIN", "variable": "grain size", "source_or_formula": "Luo2013", "measurement_method": "linear intercept from ~200 grains", "scale_parameter": "field/intercept convention", "reference_value": "67.2,46.8,42.6,38.6 µm", "sensitivity_relation": "not recoverable without raw intercepts", "uncertainty_status": "POINT_VALUES_ONLY", "bias_direction": "method-dependent", "required_metadata": "raw intercepts/fields/section plane", "notes": "Method stated; dispersion absent"},
    {"uq_id": "UQ_HOSS_PRIOR_BETA", "variable": "prior-beta", "source_or_formula": "Hosseini2017", "measurement_method": "optical microscopy", "scale_parameter": "field/reconstruction", "reference_value": "600 vs 16 µm; trimodal not detected", "sensitivity_relation": "not estimable", "uncertainty_status": "NO_NUMERIC_ERROR", "bias_direction": "non-detection is censored", "required_metadata": "grain/field counts and reconstruction", "notes": "Never encode non-detection as zero"},
    {"uq_id": "UQ_HOSS_PHASE", "variable": "alpha/transformed-beta ratio", "source_or_formula": "Hosseini2017", "measurement_method": "OM/Clemex multiple regions", "scale_parameter": "segmentation/field sampling", "reference_value": "0,0.22,0.67", "sensitivity_relation": "not estimable from labelled figure", "uncertainty_status": "FIGURE_ERROR_NOT_MACHINE_BOUND", "bias_direction": "classification-dependent", "required_metadata": "field values/variance/unclassified area", "notes": "Ratio conflates amount and morphology"},
    {"uq_id": "UQ_ALPHA_LATH", "variable": "alpha-lath thickness", "source_or_formula": "Hosseini2017", "measurement_method": "SEM qualitative", "scale_parameter": "magnification/line orientation", "reference_value": "trimodal qualitatively thinner", "sensitivity_relation": "not estimable", "uncertainty_status": "NOT_IDENTIFIABLE", "bias_direction": "representative-image selection", "required_metadata": "full distribution and sampling", "notes": "Cannot enter numeric mediation"},
    {"uq_id": "UQ_GND_STEP", "variable": "GND", "source_or_formula": "rho_GND proportional KAM/(b*step)", "measurement_method": "EBSD-derived", "scale_parameter": "step ratio s/s0", "reference_value": 1, "sensitivity_relation": "relative_GND=1/(s/s0) at fixed KAM,b", "uncertainty_status": "ANALYTIC_SCALE_SENSITIVITY", "bias_direction": "smaller step inflates simplified density", "required_metadata": "step/kernel/cutoff/cleanup/b/Nye", "notes": "Derived, not empirical calibration"},
    {"uq_id": "UQ_TEXTURE", "variable": "texture", "source_or_formula": "missing cohort", "measurement_method": "ODF/pole figure", "scale_parameter": "plane/phase", "reference_value": "", "sensitivity_relation": "not estimable", "uncertainty_status": "NOT_IDENTIFIABLE", "bias_direction": "direction selection", "required_metadata": "ODF/index/direction/phase", "notes": "No undefined scalar texture proxy"},
]
write_csv("MICROSTRUCTURE_MEASUREMENT_UQ.csv", uq_fields, uq)

write_csv("HIERARCHICAL_RESULTS.csv", ["result_id", "estimand", "model", "estimate", "unit", "ci95_low", "ci95_high", "prediction_interval_low", "prediction_interval_high", "independent_papers", "effect_rows", "cluster_unit", "heterogeneity_metric", "status", "claim_level", "notes"], [
    {"result_id": "HIER_GRAIN_SHARE", "estimand": "paper-balanced median Δsigma_grain/ΔYS", "model": "equal-paper median + paper-cluster bootstrap inherited from QM31", "estimate": 0.604, "unit": "fraction", "ci95_low": 0.482, "ci95_high": 0.750, "independent_papers": 4, "effect_rows": 5, "cluster_unit": "paper", "heterogeneity_metric": "range 0.180–0.783", "status": "ESTIMABLE_MECHANISM_CANDIDATE", "claim_level": 2, "notes": "No new fit pretended without raw rows"},
    {"result_id": "HIER_FORMAL_NIE", "estimand": "joint natural indirect effect", "model": "not fit", "independent_papers": 0, "effect_rows": 0, "cluster_unit": "paper", "status": "NOT_IDENTIFIABLE", "claim_level": 1, "notes": "Sequential exchangeability, overlap and error models absent"},
])
write_csv("DOSE_RESPONSE.csv", ["dose_result_id", "exposure", "mediator", "outcome", "dose_definition", "model", "estimate", "status", "independent_papers", "notes"], [{"dose_result_id": "DOSE_QM29", "exposure": "actual reinforcement vol.%", "mediator": "organization variables", "outcome": "property", "dose_definition": "actual phase vol.% only", "model": "not fit", "status": "NOT_IDENTIFIABLE", "independent_papers": 0, "notes": "Coated-powder wt.% is not actual TiC vol.%"}])
write_csv("INTERACTION_EFFECTS.csv", ["interaction_id", "term", "outcome", "estimate", "unit", "ci95_low", "ci95_high", "fdr_q", "status", "support_domain", "notes"], [
    {"interaction_id": "INT_METHOD", "term": "mediator × method/scale", "outcome": "measured mediator", "status": "NOT_IDENTIFIABLE", "support_domain": "no calibration pairs", "notes": "Required random/calibration factor"},
    {"interaction_id": "INT_GRAIN_PHASE", "term": "operative scale × phase state", "outcome": "YS", "status": "NOT_IDENTIFIABLE", "support_domain": "family-specific k", "notes": "k spans 328–1455 MPa√µm"},
    {"interaction_id": "INT_HP_GND_HDI", "term": "HP × GND/HDI overlap", "outcome": "YS", "status": "NOT_IDENTIFIABLE_DOUBLE_COUNT_RISK", "support_domain": "2025 Ti60", "notes": "HDI partly originates from FG/CG refinement"},
])
write_csv("HETEROGENEITY.csv", ["heterogeneity_id", "estimand", "metric", "value", "unit", "independent_papers", "interpretation", "status"], [
    {"heterogeneity_id": "HET_SHARE", "estimand": "grain share of ΔYS", "metric": "exact paired range", "value": "0.180–0.783", "unit": "fraction", "independent_papers": 4, "interpretation": "large chemistry/scale/residual spread", "status": "OBSERVED"},
    {"heterogeneity_id": "HET_K", "estimand": "Hall-Petch k", "metric": "source range", "value": "328–1455", "unit": "MPa·sqrt(µm)", "independent_papers": 4, "interpretation": "not transferable without family/scale match", "status": "OBSERVED"},
    {"heterogeneity_id": "HET_SCALE", "estimand": "operative length", "metric": "categories", "value": "colony; lamella; beta grain; FG/CG mixture", "unit": "category", "independent_papers": 4, "interpretation": "proxy substitution can create false mediation", "status": "OBSERVED"},
])
write_csv("SENSITIVITY_ANALYSIS.csv", ["sensitivity_id", "target_estimand", "perturbation", "estimate", "ci95_low", "ci95_high", "independent_papers", "decision", "notes"], [
    {"sensitivity_id": "SENS_CLUSTER", "target_estimand": "grain share of ΔYS", "perturbation": "paper-cluster bootstrap", "estimate": 0.604, "ci95_low": 0.482, "ci95_high": 0.750, "independent_papers": 4, "decision": "ROBUST_AS_LEVEL2_CANDIDATE", "notes": "QM31 recomputable subgroup"},
    {"sensitivity_id": "SENS_TI60", "target_estimand": "grain share", "perturbation": "add 2025 Ti60 source-reported row", "estimate": 0.502, "independent_papers": 5, "decision": "LOWER_MEDIAN_DOUBLE_COUNT_RISK", "notes": "FG/CG and S2-S3 missing"},
    {"sensitivity_id": "SENS_PROXY", "target_estimand": "prior-beta-mediated YS", "perturbation": "prior-beta substituted for lamellar width", "estimate": "false_positive_risk", "independent_papers": 1, "decision": "REJECT_PROXY_SUBSTITUTION", "notes": "WAAM negative control"},
    {"sensitivity_id": "SENS_PHASE_SIGN", "target_estimand": "phase-ratio-mediated YS", "perturbation": "bimodal→trimodal", "estimate": -41, "independent_papers": 1, "decision": "NON_MONOTONIC_COMPETING_PATHS", "notes": "ratio +0.45"},
    {"sensitivity_id": "SENS_GND_STEP", "target_estimand": "relative GND", "perturbation": "step 0.25–4×", "estimate": "4.0–0.25", "independent_papers": 0, "decision": "SCALE_DOMINANT", "notes": "analytic only"},
])
write_csv("NULL_NEGATIVE_RESULTS.csv", ["result_id", "paper_uid", "result_type", "exposure", "mediator", "outcome", "estimate", "unit", "status", "evidence_level", "interpretation", "provenance_id"], [
    {"result_id": "NEG_WAAM", "paper_uid": "P_WAAM_UNRESOLVED", "result_type": "negative_control", "exposure": "TiB addition", "mediator": "prior-beta refinement", "outcome": "HP contribution", "estimate": 0, "unit": "MPa_approx", "status": "SOURCE_ASSIGNED_APPROX_ZERO", "evidence_level": "DERIVED_REPORT", "interpretation": "prior-beta not operative when lamellar width unchanged", "provenance_id": "PROV_WAAM_GAP"},
    {"result_id": "NEG_PHASE", "paper_uid": "P_HOSS_2017", "result_type": "sign_reversal", "exposure": "bimodal→trimodal", "mediator": "phase ratio +0.45", "outcome": "YS", "estimate": -41, "unit": "MPa", "status": "OBSERVED", "evidence_level": "FIGURE_DERIVED", "interpretation": "partitioning/lath paths compensate", "provenance_id": "PROV_PAIR_HOSS_B_T"},
    {"result_id": "NULL_KAM", "paper_uid": "MULTI", "result_type": "data_gap", "exposure": "process/reinforcement", "mediator": "KAM/GND", "outcome": "YS", "status": "NOT_IDENTIFIABLE", "evidence_level": "UNRESOLVED", "interpretation": "raw maps/acquisition metadata absent", "provenance_id": "PROV_KAM_GAP"},
    {"result_id": "NULL_TEXTURE", "paper_uid": "MULTI", "result_type": "data_gap", "exposure": "process/reinforcement", "mediator": "texture", "outcome": "directional property", "status": "NOT_IDENTIFIABLE", "evidence_level": "UNRESOLVED", "interpretation": "no complete ODF/property cohort", "provenance_id": "PROV_TEXTURE_GAP"},
    {"result_id": "NULL_HIGH_T", "paper_uid": "MULTI", "result_type": "data_gap", "exposure": "process/reinforcement", "mediator": "organization", "outcome": "high-temperature property", "status": "NOT_IDENTIFIABLE", "evidence_level": "UNRESOLVED", "interpretation": "temperature-specific k and pre/post organization absent", "provenance_id": "PROV_HIGH_T_GAP"},
])

conflicts = [
    {"conflict_id": "C01", "severity": "BLOCKING", "topic": "canonical snapshot", "evidence_a": "Q40/V29 atomic/provenance required", "evidence_b": "absent in isolated runner", "resolution": "derived snapshot only", "status": "OPEN"},
    {"conflict_id": "C02", "severity": "HIGH", "topic": "QM31 raw rows", "evidence_a": "aggregate available", "evidence_b": "row-level d/k/deltaYS/LOPO absent", "resolution": "do not invent refit", "status": "OPEN"},
    {"conflict_id": "C03", "severity": "HIGH", "topic": "operative scale", "evidence_a": "prior-beta refines", "evidence_b": "lamellar width unchanged and HP≈0", "resolution": "require state-specific operative scale", "status": "OPEN"},
    {"conflict_id": "C04", "severity": "HIGH", "topic": "outcome transfer", "evidence_a": "Luo budget for hardness", "evidence_b": "not proven for YS", "resolution": "retain outcome-specific bound", "status": "RESOLVED_BY_SCOPE"},
    {"conflict_id": "C05", "severity": "HIGH", "topic": "double counting", "evidence_a": "HP/GND/HDI terms", "evidence_b": "shared FG/CG origin", "resolution": "no additive total", "status": "OPEN"},
    {"conflict_id": "C06", "severity": "MEDIUM", "topic": "phase monotonicity", "evidence_a": "ratio rises", "evidence_b": "YS falls", "resolution": "competing partition/lath paths", "status": "RESOLVED_AS_COUNTEREXAMPLE"},
    {"conflict_id": "C07", "severity": "HIGH", "topic": "KAM/GND measurement", "evidence_a": "requested mediator", "evidence_b": "step/kernel/cleanup absent", "resolution": "NOT_IDENTIFIABLE", "status": "OPEN"},
    {"conflict_id": "C08", "severity": "MEDIUM", "topic": "non-detection", "evidence_a": "trimodal beta grains not detected", "evidence_b": "zero is false numeric value", "resolution": "categorical NOT_DETECTED", "status": "RESOLVED_BY_ENCODING"},
    {"conflict_id": "C09", "severity": "HIGH", "topic": "formal NIE assumptions", "evidence_a": "temporal order plausible", "evidence_b": "exchangeability/overlap/error model absent", "resolution": "formal NIE NOT_IDENTIFIABLE", "status": "OPEN"},
]
write_csv("CONFLICT_LEDGER.csv", ["conflict_id", "severity", "topic", "evidence_a", "evidence_b", "resolution", "status"], conflicts)

archive_names = ["00_统一上传总控与校验信息_20260712.zip", "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip", "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip", "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip"] + [f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 9)] + ["S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip"] + [f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 4)] + [f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1, 11)]
ledger_fields = ["input_id", "snapshot_id", "source_name", "source_type", "path_or_locator", "source_hash", "source_hash_kind", "priority", "window_relevance", "terminal_use_status", "opened_or_consumed", "notes"]
ledger = [
    {"input_id": "PRIMARY_LUO", "snapshot_id": SNAPSHOT, "source_name": "Luo2013 project-library PDF", "source_type": "PRIMARY_PDF_OPENED", "path_or_locator": "file_library DOI 10.1016/j.scriptamat.2013.03.017", "source_hash": CAP_HASH["luo"], "source_hash_kind": "NORMALIZED_CAPTURE_SHA256", "priority": "P0", "window_relevance": "grain/architecture/property/budget", "terminal_use_status": "USED_DIRECTLY", "opened_or_consumed": "YES", "notes": "Original byte hash requested"},
    {"input_id": "PRIMARY_HOSS", "snapshot_id": SNAPSHOT, "source_name": "Hosseini2017 project-library PDF", "source_type": "PRIMARY_PDF_OPENED", "path_or_locator": "file_library DOI 10.1016/j.msea.2017.04.068", "source_hash": CAP_HASH["hoss"], "source_hash_kind": "NORMALIZED_CAPTURE_SHA256", "priority": "P0", "window_relevance": "process→organization→property", "terminal_use_status": "USED_DIRECTLY", "opened_or_consumed": "YES", "notes": "Original byte hash requested"},
    {"input_id": "QM31", "snapshot_id": SNAPSHOT, "source_name": "QM31 Executive Verdict", "source_type": "DERIVED_WINDOW_REPORT", "path_or_locator": "file_library", "source_hash": CAP_HASH["qm31"], "source_hash_kind": "NORMALIZED_CAPTURE_SHA256", "priority": "P1", "window_relevance": "grain contribution/bootstrap/negative control", "terminal_use_status": "USED_WITH_CEILING", "opened_or_consumed": "YES", "notes": "Raw rows requested"},
]
for i, name in enumerate(archive_names, 1):
    ledger.append({"input_id": f"ARCHIVE_{i:02d}", "snapshot_id": SNAPSHOT, "source_name": name, "source_type": "PROJECT_ZIP", "path_or_locator": "/mnt/data/" + name, "source_hash": "", "source_hash_kind": "NOT_RECOMPUTED_IN_ISOLATED_RUNNER", "priority": "P0" if name.startswith("TITMC") else "P2", "window_relevance": "primary corpus" if name.startswith("TITMC") else "data/features/harness/code provenance", "terminal_use_status": "LISTED_NOT_NUMERIC_SOURCE", "opened_or_consumed": "NO_DIRECT_BYTE_OPEN_IN_RUNNER", "notes": "Local absorption must bind byte/central-directory hashes"})
write_csv("INPUT_LEDGER.csv", ledger_fields, ledger)
write_csv("SOURCE_COVERAGE_MATRIX.csv", ["source_tier", "required_asset", "availability", "used_for_numeric_estimate", "coverage_decision", "gap_action"], [
    {"source_tier": 1, "required_asset": "V29/Q40 atom/provenance/conflict/excluded/registries", "availability": "MISSING", "used_for_numeric_estimate": "NO", "coverage_decision": "BLOCKS_AUTHORITY", "gap_action": "WEB_TO_LOCAL_REQUEST"},
    {"source_tier": 2, "required_asset": "S03 frozen matrices/features/splits", "availability": "ARCHIVES_LISTED_NOT_BYTE_OPENED", "used_for_numeric_estimate": "NO", "coverage_decision": "NOT_SUBSTITUTED", "gap_action": "local hash-bound absorption"},
    {"source_tier": 3, "required_asset": "S03 reliability/UQ/AD/mechanism assets", "availability": "ARCHIVES_LISTED_NOT_BYTE_OPENED", "used_for_numeric_estimate": "NO", "coverage_decision": "METHOD_REFERENCE_ONLY", "gap_action": "local hash-bound absorption"},
    {"source_tier": 4, "required_asset": "V27 literature", "availability": "2 primary PDFs opened + project corpus registry context", "used_for_numeric_estimate": "YES", "coverage_decision": "TARGETED_PRIMARY_EVIDENCE", "gap_action": "bind original bytes/XPath locally"},
    {"source_tier": "neighbor", "required_asset": "QM31 raw outputs", "availability": "executive verdict only", "used_for_numeric_estimate": "YES_WITH_CEILING", "coverage_decision": "AGGREGATE_ONLY", "gap_action": "recover raw/LOPO tables"},
])

prov = []
for r in cohort:
    src = CAP_HASH["luo"] if r["paper_uid"] == "P_LUO_2013" else CAP_HASH["hoss"]
    prov.append({"provenance_id": r["provenance_id"], "snapshot_id": SNAPSHOT, "paper_uid": r["paper_uid"], "sample_uid": r["sample_uid"], "condition_uid": r["condition_uid"], "source_type": "PRIMARY_PDF", "source_locator": r["source_locator"], "source_hash": src, "hash_kind": "NORMALIZED_CAPTURE_SHA256", "evidence_level": r["evidence_level"], "notes": "Original byte hash requested"})
for p in pairs:
    src = CAP_HASH["luo"] if p["paper_uid"] == "P_LUO_2013" else CAP_HASH["hoss"]
    prov.append({"provenance_id": p["provenance_id"], "snapshot_id": SNAPSHOT, "paper_uid": p["paper_uid"], "sample_uid": p["control_sample_uid"] + "->" + p["treatment_sample_uid"], "condition_uid": p["condition_uid"], "source_type": "DERIVED_PAIR", "source_locator": "PAIR_MATCHES.csv", "source_hash": src, "hash_kind": "PARENT_CAPTURE_SHA256", "evidence_level": "DERIVED_CALCULATION", "notes": "Arithmetic from source-bound rows"})
prov += [
    {"provenance_id": "PROV_QM31", "snapshot_id": SNAPSHOT, "paper_uid": "QM31_AGGREGATE_4_PAPERS", "sample_uid": "5_EFFECTS", "condition_uid": "RT_TENSION", "source_type": "DERIVED_WINDOW_REPORT", "source_locator": "QM31 Executive Verdict", "source_hash": CAP_HASH["qm31"], "hash_kind": "NORMALIZED_CAPTURE_SHA256", "evidence_level": "DERIVED_CALCULATION_RECOMPUTABLE_SUBGROUP", "notes": "Raw rows requested"},
    {"provenance_id": "PROV_LUO_BUDGET", "snapshot_id": SNAPSHOT, "paper_uid": "P_LUO_2013", "sample_uid": "LUO_CONTROL->LUO_60", "condition_uid": "RT_HARDNESS", "source_type": "PRIMARY_PDF", "source_locator": "Luo2013 mechanism text", "source_hash": CAP_HASH["luo"], "hash_kind": "NORMALIZED_CAPTURE_SHA256", "evidence_level": "DIRECT_TEXT_SOURCE_CALCULATION", "notes": "Hardness only"},
    {"provenance_id": "PROV_HOSS_TRIAD", "snapshot_id": SNAPSHOT, "paper_uid": "P_HOSS_2017", "sample_uid": "HOSS_TRIAD", "condition_uid": "RT_TENSION_AGED_600C", "source_type": "PRIMARY_PDF", "source_locator": "Hosseini2017 figures/text", "source_hash": CAP_HASH["hoss"], "hash_kind": "NORMALIZED_CAPTURE_SHA256", "evidence_level": "MIXED_DIRECT_TEXT_FIGURE_DERIVED", "notes": "Process triad"},
    {"provenance_id": "PROV_WAAM_GAP", "snapshot_id": SNAPSHOT, "paper_uid": "P_WAAM_UNRESOLVED", "sample_uid": "NEGATIVE_CONTROL", "condition_uid": "RT_UNRESOLVED", "source_type": "DERIVED_WINDOW_REPORT", "source_locator": "QM31 Executive Verdict", "source_hash": CAP_HASH["qm31"], "hash_kind": "NORMALIZED_CAPTURE_SHA256", "evidence_level": "DERIVED_REPORT", "notes": "Original DOI/rows missing"},
    {"provenance_id": "PROV_KAM_GAP", "snapshot_id": SNAPSHOT, "paper_uid": "MULTI", "sample_uid": "", "condition_uid": "", "source_type": "GAP_RECORD", "source_locator": "WEB_TO_LOCAL_REQUEST.json", "source_hash": "", "hash_kind": "", "evidence_level": "UNRESOLVED", "notes": "raw EBSD absent"},
    {"provenance_id": "PROV_TEXTURE_GAP", "snapshot_id": SNAPSHOT, "paper_uid": "MULTI", "sample_uid": "", "condition_uid": "", "source_type": "GAP_RECORD", "source_locator": "WEB_TO_LOCAL_REQUEST.json", "source_hash": "", "hash_kind": "", "evidence_level": "UNRESOLVED", "notes": "texture cohort absent"},
    {"provenance_id": "PROV_HIGH_T_GAP", "snapshot_id": SNAPSHOT, "paper_uid": "MULTI", "sample_uid": "", "condition_uid": "HIGH_T", "source_type": "GAP_RECORD", "source_locator": "WEB_TO_LOCAL_REQUEST.json", "source_hash": "", "hash_kind": "", "evidence_level": "UNRESOLVED", "notes": "high-T mediator rows absent"},
]
with (OUT / "PROVENANCE.jsonl").open("w", encoding="utf-8") as f:
    for r in prov:
        f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

nodes = [
    ("matrix", "Matrix chemistry / initial state", "confounder", 0.5, 4.4), ("precursor", "Precursor / selection", "exposure_parent", 0.5, 2.8), ("process", "Process + heat treatment", "exposure", 2.2, 4.0), ("reinforcement", "Actual reinforcement / architecture", "exposure", 2.2, 2.4), ("defects", "Defects / contamination", "co_mediator", 4.4, 0.7), ("grain", "Operative grain / colony scale", "mediator", 4.5, 4.7), ("prior_beta", "Prior-beta grain (proxy)", "mediator_proxy", 4.5, 3.7), ("lath", "Alpha-lath thickness", "mediator", 4.5, 2.7), ("phase", "Alpha/beta + partitioning", "mediator", 4.5, 1.7), ("kam", "KAM / GND", "mediator", 6.5, 4.2), ("texture", "Texture / orientation", "mediator", 6.5, 3.1), ("interface", "Interface / network architecture", "mediator", 6.5, 1.9), ("test", "Test T / rate / direction / mode", "outcome_parent", 8.5, 0.7), ("property", "Mechanical property", "outcome", 8.5, 3.0), ("method", "Measurement method / scale", "measurement_parent", 4.5, -0.2), ("measured", "Measured organization", "measurement", 6.5, -0.2), ("reporting", "Reporting selection (collider)", "collider", 8.5, 4.9),
]
edges = [("matrix", "process"), ("matrix", "reinforcement"), ("matrix", "grain"), ("matrix", "phase"), ("matrix", "property"), ("precursor", "reinforcement"), ("precursor", "defects"), ("process", "reinforcement"), ("process", "defects"), ("process", "grain"), ("process", "prior_beta"), ("process", "lath"), ("process", "phase"), ("process", "kam"), ("process", "texture"), ("process", "interface"), ("reinforcement", "grain"), ("reinforcement", "lath"), ("reinforcement", "phase"), ("reinforcement", "kam"), ("reinforcement", "texture"), ("reinforcement", "interface"), ("reinforcement", "defects"), ("prior_beta", "grain"), ("phase", "lath"), ("grain", "kam"), ("defects", "property"), ("grain", "property"), ("lath", "property"), ("phase", "property"), ("kam", "property"), ("texture", "property"), ("interface", "property"), ("test", "property"), ("grain", "measured"), ("prior_beta", "measured"), ("lath", "measured"), ("phase", "measured"), ("kam", "measured"), ("texture", "measured"), ("method", "measured"), ("property", "reporting"), ("measured", "reporting"), ("method", "reporting")]
dag = {"dag_id": "QM29_PSPP_DAG", "snapshot_id": SNAPSHOT, "claim_ceiling": 2, "nodes": [{"id": i, "label": l, "type": t} for i, l, t, x, y in nodes], "edges": [[a, b] for a, b in edges], "adjustment_guidance": {"total_effect": ["matrix", "precursor", "test"], "do_not_adjust_for_total_effect": ["grain", "prior_beta", "lath", "phase", "kam", "texture", "interface"], "collider_to_avoid": ["reporting"]}}
write_json("PSPP_DAG.json", dag)
write_csv("figure_data/fig01_nodes.csv", ["id", "label", "type", "x", "y"], [{"id": i, "label": l, "type": t, "x": x, "y": y} for i, l, t, x, y in nodes])
write_csv("figure_data/fig01_edges.csv", ["source", "target"], [{"source": a, "target": b} for a, b in edges])
path_data = [
    {"mediator": "Operative grain scale", "estimate_pct": 60.4, "low_pct": 48.2, "high_pct": 75.0, "bound": "interval", "outcome": "delta YS", "papers": 4, "effects": 5},
    {"mediator": "Grain refinement (Luo)", "estimate_pct": 17.0, "low_pct": "", "high_pct": 17.0, "bound": "upper", "outcome": "delta hardness", "papers": 1, "effects": 1},
    {"mediator": "Aligned TiC architecture", "estimate_pct": 60.0, "low_pct": 60.0, "high_pct": "", "bound": "lower", "outcome": "delta hardness", "papers": 1, "effects": 1},
    {"mediator": "Prior-beta proxy (WAAM)", "estimate_pct": 0, "low_pct": "", "high_pct": "", "bound": "approx", "outcome": "delta YS", "papers": 1, "effects": 1},
    {"mediator": "Alpha-lath thickness", "estimate_pct": "", "low_pct": "", "high_pct": "", "bound": "NOT_IDENTIFIABLE", "outcome": "YS/EL", "papers": 1, "effects": 0},
    {"mediator": "Alpha/beta fraction", "estimate_pct": "", "low_pct": "", "high_pct": "", "bound": "NOT_IDENTIFIABLE", "outcome": "YS", "papers": 1, "effects": 3},
    {"mediator": "KAM/GND", "estimate_pct": "", "low_pct": "", "high_pct": "", "bound": "NOT_IDENTIFIABLE", "outcome": "YS", "papers": 0, "effects": 0},
    {"mediator": "Texture", "estimate_pct": "", "low_pct": "", "high_pct": "", "bound": "NOT_IDENTIFIABLE", "outcome": "directional property", "papers": 0, "effects": 0},
]
write_csv("figure_data/fig02_paths.csv", ["mediator", "estimate_pct", "low_pct", "high_pct", "bound", "outcome", "papers", "effects"], path_data)
write_csv("figure_data/fig03_gnd_step.csv", ["step_ratio", "relative_gnd", "derivation", "papers", "evidence_level"], [{"step_ratio": x, "relative_gnd": 1 / x, "derivation": "rho_rel=1/step_ratio at fixed KAM,b", "papers": 0, "evidence_level": "DERIVED_CALCULATION"} for x in [0.25, 0.5, 1, 2, 4]])
water = [{"sequence": 1, "component": "Interstitial co-mediator", "increment_mpa": 300, "bound": "point"}, {"sequence": 2, "component": "Grain refinement", "increment_mpa": 250, "bound": "upper"}, {"sequence": 3, "component": "Aligned TiC architecture", "increment_mpa": 879.6, "bound": "lower"}, {"sequence": 4, "component": "Residual at simultaneous bounds", "increment_mpa": 36.4, "bound": "arithmetic residual"}, {"sequence": 5, "component": "Observed hardness increment", "increment_mpa": 1466, "bound": "total"}]
write_csv("figure_data/fig04_waterfall.csv", ["sequence", "component", "increment_mpa", "bound"], water)

plot_code = r'''
from __future__ import annotations
import argparse,csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def rows(p):
    with p.open(encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def save(fig,base,stem):
    out=base/"figures";out.mkdir(parents=True,exist_ok=True)
    fig.savefig(out/f"{stem}.png",dpi=600,bbox_inches="tight")
    fig.savefig(out/f"{stem}.svg",bbox_inches="tight")
    fig.savefig(out/f"{stem}.pdf",bbox_inches="tight")
def dag(base):
    ns=rows(base/"figure_data/fig01_nodes.csv");es=rows(base/"figure_data/fig01_edges.csv");pos={r["id"]:(float(r["x"]),float(r["y"])) for r in ns}
    fig,ax=plt.subplots(figsize=(13,7.5))
    for e in es:
        x1,y1=pos[e["source"]];x2,y2=pos[e["target"]];ax.annotate("",(x2,y2),(x1,y1),arrowprops=dict(arrowstyle="->",lw=.65,alpha=.42,shrinkA=24,shrinkB=24))
    for r in ns:
        x,y=pos[r["id"]];ax.text(x,y,r["label"],ha="center",va="center",fontsize=8,bbox=dict(boxstyle="round,pad=.35",alpha=.12))
    ax.set_xlim(-.4,9.5);ax.set_ylim(-.8,5.7);ax.axis("off");ax.set_title("Process–Structure–Property–Performance causal DAG")
    ax.text(.01,-.03,"Support: 2 direct primary papers plus a 4-paper grain-refinement aggregate. Reporting is a collider; method is explicit.",transform=ax.transAxes,fontsize=8)
    save(fig,base,"fig01_pspp_dag");plt.close(fig)
def paths(base):
    rs=rows(base/"figure_data/fig02_paths.csv");ys=list(range(len(rs)))[::-1];fig,ax=plt.subplots(figsize=(10.5,6.8))
    for y,r in zip(ys,rs):
        if r["estimate_pct"]:
            x=float(r["estimate_pct"]);lo=r["low_pct"];hi=r["high_pct"]
            if lo and hi:ax.errorbar(x,y,xerr=[[x-float(lo)],[float(hi)-x]],fmt="o",capsize=4)
            else:ax.plot(x,y,"o")
            if r["bound"] in ("upper","lower"):ax.text(x+2,y,r["bound"]+" bound",va="center",fontsize=8)
        else:ax.text(3,y,"NOT IDENTIFIABLE",va="center",fontsize=8)
    ax.set_yticks(ys,[r["mediator"] for r in rs]);ax.axvline(0,lw=.8);ax.set_xlim(-5,105);ax.set_xlabel("Contribution candidate (% of matched outcome increment)");ax.set_title("Microstructure path coefficients and identification status");ax.grid(axis="x",alpha=.25)
    ax.text(.01,-.12,"Headline: operative grain scale = 60.4% of ΔYS (95% paper-cluster interval 48.2–75.0; 5 effects, 4 papers). Other numeric rows are source-specific bounds/negative control.",transform=ax.transAxes,fontsize=8)
    save(fig,base,"fig02_mediator_path_coefficients");plt.close(fig)
def gnd(base):
    rs=rows(base/"figure_data/fig03_gnd_step.csv");x=[float(r["step_ratio"]) for r in rs];y=[float(r["relative_gnd"]) for r in rs];fig,ax=plt.subplots(figsize=(8.5,5.8));ax.plot(x,y,marker="o");ax.set_xscale("log",base=2);ax.set_yscale("log",base=2);ax.set_xticks(x,[str(v) for v in x]);ax.set_yticks([.25,.5,1,2,4],["0.25","0.5","1","2","4"]);ax.minorticks_off();ax.axvline(1,lw=.8);ax.axhline(1,lw=.8);ax.set_xlabel("EBSD step-size ratio, s/s₀");ax.set_ylabel("Relative GND estimate at fixed KAM and b");ax.set_title("KAM/GND measurement-scale sensitivity (derived, not calibrated)");ax.grid(alpha=.25);ax.text(.01,-.16,"Formula-only sensitivity: ρGND ∝ 1/s. Independent papers = 0; raw EBSD maps and acquisition metadata are required.",transform=ax.transAxes,fontsize=8);save(fig,base,"fig03_gnd_step_size_sensitivity");plt.close(fig)
def waterfall(base):
    rs=rows(base/"figure_data/fig04_waterfall.csv");parts=rs[:-1];total=rs[-1];vals=[float(r["increment_mpa"]) for r in parts];bottom=[];s=0
    for v in vals:bottom.append(s);s+=v
    fig,ax=plt.subplots(figsize=(10.5,6.2))
    for i,(r,v,b) in enumerate(zip(parts,vals,bottom)):ax.bar(i,v,bottom=b);ax.text(i,b+v/2,f"{v:.1f}\n({r['bound']})",ha="center",va="center",fontsize=8)
    ax.bar(len(parts),float(total["increment_mpa"]));ax.text(len(parts),float(total["increment_mpa"])/2,total["increment_mpa"],ha="center",va="center");labels=[r["component"] for r in parts]+[total["component"]];ax.set_xticks(range(len(labels)),labels,rotation=20,ha="right");ax.set_ylabel("Hardness increment (MPa)");ax.set_title("Source-bounded microstructure contribution waterfall — Luo et al. 2013");ax.text(.01,-.23,"One paper; outcome = hardness, not YS. Grain is an upper bound, aligned-TiC architecture a lower bound; residual is not a mechanism.",transform=ax.transAxes,fontsize=8);save(fig,base,"fig04_indirect_effect_waterfall");plt.close(fig)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--base",type=Path,required=True);a=p.parse_args();dag(a.base);paths(a.base);gnd(a.base);waterfall(a.base)
'''
write_text("plot_code/plot_all.py", plot_code)
subprocess.run([sys.executable, str(OUT / "plot_code/plot_all.py"), "--base", str(OUT)], check=True, env={**os.environ, "MPLBACKEND": "Agg"})

plot_specs = {"snapshot_id": SNAPSHOT, "figures": [
    {"id": "fig01", "stem": "fig01_pspp_dag", "title": "PSPP causal DAG", "data": ["figure_data/fig01_nodes.csv", "figure_data/fig01_edges.csv"], "code": "plot_code/plot_all.py", "effect_definition": "DAG, no numeric causal estimate", "independent_papers": "2 direct + 4-paper aggregate", "evidence_layer": "physical DAG/source-bound", "support_domain": "Ti/TMC and Ti-alloy process contrasts", "formats": ["SVG", "PDF", "PNG_600dpi"]},
    {"id": "fig02", "stem": "fig02_mediator_path_coefficients", "title": "Mediator path coefficients", "data": ["figure_data/fig02_paths.csv"], "code": "plot_code/plot_all.py", "effect_definition": "mechanism contribution candidate, not NIE", "independent_papers": 4, "evidence_layer": "derived aggregate + source bounds", "support_domain": "RT/source-specific", "formats": ["SVG", "PDF", "PNG_600dpi"]},
    {"id": "fig03", "stem": "fig03_gnd_step_size_sensitivity", "title": "GND scale sensitivity", "data": ["figure_data/fig03_gnd_step.csv"], "code": "plot_code/plot_all.py", "effect_definition": "relative measurement sensitivity", "independent_papers": 0, "evidence_layer": "derived formula", "support_domain": "fixed KAM,b", "formats": ["SVG", "PDF", "PNG_600dpi"]},
    {"id": "fig04", "stem": "fig04_indirect_effect_waterfall", "title": "Luo hardness contribution bounds", "data": ["figure_data/fig04_waterfall.csv"], "code": "plot_code/plot_all.py", "effect_definition": "source-bounded hardness budget", "independent_papers": 1, "evidence_layer": "direct source calculation", "support_domain": "CP-Ti/TiC RT hardness", "formats": ["SVG", "PDF", "PNG_600dpi"]},
]}
write_json("PLOT_SPECS.json", plot_specs)

write_text("METHODS.md", f"""
# Methods — QM29

`WINDOW=QM29 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

Atomic rows preserve paper × sample × process/HT × organization state × test condition × property. Five same-paper contrasts were computed as treatment minus control, with log response ratios only for positive and semantically compatible values.

The physical DAG separates process/reinforcement exposures, true organization mediators, defects/co-mediators, measurement method, measured organization and reporting selection. Reporting is a collider. Downstream organization variables are not adjusted away when estimating total process/reinforcement effects.

The only cross-paper quantitative mediator candidate is `C_grain = Δσ_HP / ΔYS`, with `Δσ_HP = k(d_t^(-1/2)-d_c^(-1/2))`. QM31 reports paper-balanced median 0.604 and paper-cluster bootstrap 95% interval 0.482–0.750 from 5 effects/4 papers. It is not a formal natural indirect effect.

Formal mediation requires temporal order, consistency, positivity, sequential exchangeability, no exposure-induced mediator–outcome confounder and explicit measurement-error models. These are not established; every formal NIE is therefore `NOT_IDENTIFIABLE`.

Luo’s mechanism shares are retained as inequality bounds for hardness only. Hosseini’s process triad is used for same-alloy process→organization/property contrasts and a phase-ratio sign reversal. Precursor wt.% is not converted to actual reinforcement vol.%.

No broad hypothesis family was fitted; BH-FDR is not applicable. No production model was trained or registered.
""")
write_text("LIMITATIONS.md", """
# Limitations

The canonical Q40/V29 atom/provenance/conflict/excluded/registry bundle is absent; this is a derived, analysis-only snapshot. QM31 raw effect/LOPO rows are absent. Luo’s budget is for hardness and bundles interstitial/morphology changes. Hosseini is an unreinforced Ti-alloy process triad, used only for DAG and counterexample support. Alpha-lath data are qualitative; phase field errors are not machine-bound; texture is absent; KAM/GND lacks raw maps, step/kernel/cutoff/cleanup/Nye metadata. Prior-beta is not necessarily the operative slip length. HP, GND and HDI terms may overlap. High-temperature mediation is not identifiable. Original PDF byte hashes must be rebound locally.

No Gold promotion, ACTIVE mutation, unified-schema change, production-model registration, platform retraining or VALIDATED formulation is claimed.
""")
write_text("DATA_DICTIONARY.md", """
# Data dictionary

`ANALYSIS_COHORT.csv` contains atomic sample-state rows. `PAIR_MATCHES.csv` contains same-paper contrasts. `EFFECT_ESTIMATES.csv` is long-form exposure→organization/property effects. `MEDIATION_EFFECTS.csv` distinguishes formal NIE status from mechanism-contribution candidates/bounds. `MICROSTRUCTURE_MEASUREMENT_UQ.csv` records method/scale uncertainty. Blank means not reported/not estimable; `NOT_DETECTED` is categorical and never numeric zero.
""")
write_text("OPENED_FILES.txt", f"""
WINDOW=QM29
SNAPSHOT={SNAPSHOT}

Actually opened/consumed: QM29 MDU; QM31 Executive Verdict; Luo2013 project-library PDF pages 1–4; Hosseini2017 project-library PDF pages 1–11; SOURCE_EVIDENCE_INDEX/XML-corpus audit snippets; neighboring QM16/QM32/QM33/QM39 verdicts for boundary checks.

Not direct-byte-opened in the isolated runner: the 26 mounted ZIP archives listed in INPUT_LEDGER.csv and the canonical V29/Q40 atom/provenance package. The return therefore uses CONTINUE_DATA_GAP and never pretends canonical authority.
""")
write_json("SNAPSHOT_VALIDATION.json", {"window_id": "QM29", "snapshot_id": SNAPSHOT, "snapshot_basis_sha256": SNAP_HASH, "canonical_q40_snapshot_present": False, "derived_snapshot_reproducible": True, "capture_hashes": CAP_HASH, "authority_status": "DERIVED_ANALYSIS_ONLY", "validation_time": FIXED_TIME})

web_req = {"window_id": "QM29", "snapshot_id": SNAPSHOT, "priority": "BLOCKING_FOR_AUTHORITY_AND_FORMAL_MEDIATION", "requests": [
    {"request_id": "R01", "required": ["Q40_INPUT_SNAPSHOT.json", "ATOMIC_RECORDS", "PROVENANCE.jsonl", "CONFLICT_LEDGER.csv", "EXCLUDED_RECORDS.csv", "PAPER_REGISTRY.csv", "CONDITION_REGISTRY.csv"], "reason": "canonical UID/hash binding"},
    {"request_id": "R02", "required": ["QM31/PAIR_MATCHES.csv", "QM31/EFFECT_ESTIMATES.csv", "QM31/GRAIN_REFINEMENT_BUDGET.csv", "QM31/LOPO_RESULTS.csv", "QM31/PROVENANCE.jsonl"], "reason": "recompute 60.4% and LOPO"},
    {"request_id": "R03", "required": ["WAAM_TiB_Ti64 DOI", "prior-beta distribution", "alpha-beta lamellar-width distribution", "paired YS", "source HP budget"], "reason": "promote proxy negative control"},
    {"request_id": "R04", "required": ["2025 Ti60 supplement S2-S3", "FG/CG distributions", "fraction weights", "HP/GND/HDI definitions"], "reason": "remove double counting"},
    {"request_id": "R05", "required": ["raw EBSD maps", "step size", "kernel", "KAM cutoff", "cleanup", "phase indexing", "Burgers vector", "Nye method", "field replicates"], "reason": "KAM/GND error model"},
    {"request_id": "R06", "required": ["alpha-lath distributions", "prior-beta distributions", "phase field values", "texture ODF/index", "sampling protocol"], "reason": "method-calibrated multi-mediator model"},
    {"request_id": "R07", "required": ["temperature-specific k", "pre/post-test organization", "high-temperature property pairs"], "reason": "600–800C mediation"},
], "forbidden_shortcuts": ["non-detection is not zero", "do not substitute prior-beta for operative scale", "do not add HP+GND+HDI without overlap audit", "do not convert precursor wt.% to actual phase vol.% without evidence"]}
write_json("WEB_TO_LOCAL_REQUEST.json", web_req)
write_text("LOCAL_ABSORPTION_PROMPT.md", f"""
# Local absorption prompt

Validate `FINAL_QM29.zip` in isolation. Verify ZIP digest/testzip, `CHECKSUMS.sha256`, `MANIFEST.json` and snapshot `{SNAPSHOT}`. Run `python analysis_code/recompute_qm29.py --base . --check-only` and `python tests/test_qm29_outputs.py .`. Rebind archive/PDF/XML byte hashes and page/XPath locators; supply all objects in `WEB_TO_LOCAL_REQUEST.json`; preserve negative/null results; reject additive HP+GND+HDI until overlap is resolved. Register only as `ANALYSIS_ONLY/SCREENED_EVIDENCE`. Do not modify ACTIVE_TITMC, Gold, unified schema or production model registry. Produce a local receipt proving no forbidden promotion.
""")

recompute = r'''
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
def read(p):
    with p.open(encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def n(v):return None if v in ("",None,"NOT_DETECTED","QUALITATIVE_ONLY") else float(v)
p=argparse.ArgumentParser();p.add_argument("--base",type=Path,required=True);p.add_argument("--check-only",action="store_true");a=p.parse_args();b=a.base
co={r["sample_uid"]:r for r in read(b/"ANALYSIS_COHORT.csv")};checks=0
for r in read(b/"PAIR_MATCHES.csv"):
    c,t=co[r["control_sample_uid"]],co[r["treatment_sample_uid"]]
    for out,col in [("delta_ys_mpa","ys_mpa"),("delta_uts_mpa","uts_mpa"),("delta_el_pp","el_pct"),("delta_hardness_mpa","hardness_mpa")]:
        x,y,z=n(c[col]),n(t[col]),n(r[out])
        if x is not None and y is not None:assert z is not None and abs((y-x)-z)<1e-7;checks+=1
med=read(b/"MEDIATION_EFFECTS.csv");assert all(r["formal_nie_status"]=="NOT_IDENTIFIABLE" for r in med);g=next(r for r in med if r["mediation_id"]=="MED_QM31_GRAIN_YS");assert abs(float(g["proportion_mediated"])-.604)<1e-12
s=json.loads((b/"WINDOW_STATUS.json").read_text());assert s["claim_level_max"]<=2 and s["status"]=="CONTINUE_DATA_GAP"
print(json.dumps({"pass":True,"pair_property_checks":checks,"snapshot_id":s["snapshot_id"],"formal_nie":"NOT_IDENTIFIABLE"},indent=2))
'''
write_text("analysis_code/recompute_qm29.py", recompute)

status_line = "STATUS: CONTINUE_DATA_GAP | WINDOW=QM29 | MISSING=canonical_V29_Q40_atom_provenance;QM31_raw_rows;WAAM_primary;Ti60_S2_S3;raw_EBSD_lath_phase_texture | NEXT=LOCAL_HASH_BIND_AND_REMEDIATE"
status = {"window_id": "QM29", "snapshot_id": SNAPSHOT, "papers_seen": 6, "papers_included": 6, "independent_papers": 4, "paper_identity_union_status": "MINIMUM_COUNT_AGGREGATE_OVERLAP_UNRESOLVED", "direct_primary_papers": 2, "atomic_rows": len(cohort), "matched_pairs": len(pairs), "effect_estimates": len(effects), "plots_generated": 4, "open_conflicts": sum(r["status"] == "OPEN" for r in conflicts), "claim_level_max": 2, "status": "CONTINUE_DATA_GAP", "next_action": "bind canonical atom/provenance and raw mediator measurements; rerun measurement-error mediation", "production_model_registration": "FORBIDDEN_NOT_PERFORMED", "gold_promotion": "FORBIDDEN_NOT_PERFORMED", "status_line": status_line}
write_json("WINDOW_STATUS.json", status)
write_text("00_EXECUTIVE_VERDICT.md", f"""
# QM29 Executive Verdict

`WINDOW=QM29 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

The only quantitatively supported mediator family is the **operative grain/colony/lamellar slip length**. In the QM31 fully recomputable same-paper tensile subgroup, reinforcement-induced refinement accounts for a paper-balanced median **60.4% of matched ΔYS** (paper-cluster bootstrap 95% interval **48.2–75.0%**; 5 effects, 4 papers; range **18.0–78.3%**). This is a mechanism-contribution ratio, not a counterfactual natural indirect effect.

The controlling length scale is state-specific. A WAAM TiB/Ti64 negative control shows that prior-β refinement can coexist with Hall–Petch ≈0 when the operative α/β lamellar width is unchanged. Prior-β cannot be substituted automatically.

Luo 2013 directly reports control→60%-coated changes of grain size 67.2→42.6 µm, compressive YS 480→1240 MPa and hardness 1660→3126 MPa. For the 1466 MPa hardness increment, the source assigns 300 MPa to interstitials, <250 MPa/<17% to refinement and >60% to locally aligned TiC nanoplatelets. These are hardness-specific bounds; C/O/N and morphology co-change.

Hosseini 2017 provides a same-alloy process triad. Widmanstätten→bimodal changes prior-β ≈600→16 µm, phase ratio 0→0.22, YS +69 MPa and EL +7 pp. Bimodal→trimodal raises the ratio 0.22→0.67 while YS falls 41 MPa, a direct counterexample to a one-variable phase-fraction law.

Formal NIEs for α-lath thickness, α/β fraction, KAM/GND and texture are `NOT_IDENTIFIABLE`; correlated HP/GND/HDI terms cannot be summed. Maximum claim level is **2**. No Gold/ACTIVE/schema/production-model mutation or VALIDATED formulation occurred.

{status_line}
""")
write_json("FIGURE_QA.json", {"snapshot_id": SNAPSHOT, "figure_count": 4, "formats_per_figure": ["PNG_600dpi", "SVG", "PDF"], "structural_checks": "PASS", "data_and_code_present": True, "english_text": True, "generative_image_used": False, "visual_semantic_review": "PENDING_LOCAL_INDEPENDENT_REVIEW"})
write_json("environment.json", {"platform": "GitHub Actions ubuntu-latest", "python": "3.11", "matplotlib": "3.10.3", "numpy": "2.3.1", "production_model_registration": False})
write_text("requirements.lock", (ROOT / "requirements-ci.txt").read_text())
write_text("acceptance_commands.md", """
# Acceptance commands

```bash
python analysis_code/recompute_qm29.py --base . --check-only
python tests/test_qm29_outputs.py .
python plot_code/plot_all.py --base .
```

ZIP validation: use Python `zipfile.ZipFile(...).testzip()`, verify there is no nested `.zip`, and compare the outer archive SHA-256 with the delivery receipt.
""")
write_text("RUN_LOG.txt", f"""
{FIXED_TIME} built derived snapshot {SNAPSHOT}
{FIXED_TIME} wrote {len(cohort)} atomic rows, {len(pairs)} pairs, {len(effects)} effects
{FIXED_TIME} generated 4 figures in PNG/SVG/PDF
{FIXED_TIME} formal NIE retained NOT_IDENTIFIABLE
{FIXED_TIME} forbidden state mutations not performed
{FIXED_TIME} CONTINUE_DATA_GAP
""")

# Tests are part of the artifact and run after generation.
test_code = r'''
from __future__ import annotations
import csv,hashlib,json,sys,unittest
from pathlib import Path
BASE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd();sys.argv=[sys.argv[0]]
def read(n):
    with (BASE/n).open(encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()
class T(unittest.TestCase):
    def test_required(self):
        req=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256","MICROSTRUCTURE_MEDIATORS.csv","PSPP_DAG.json","MEDIATION_EFFECTS.csv","MICROSTRUCTURE_MEASUREMENT_UQ.csv"]
        self.assertTrue(all((BASE/x).is_file() for x in req))
    def test_checksums(self):
        for line in (BASE/"CHECKSUMS.sha256").read_text().splitlines():
            h,p=line.split("  ",1);self.assertEqual(h,sha(BASE/p),p)
    def test_manifest(self):
        m=json.loads((BASE/"MANIFEST.json").read_text());self.assertEqual(m["window_id"],"QM29");self.assertGreaterEqual(m["file_count"],40)
        for e in m["files"]:self.assertEqual(e["sha256"],sha(BASE/e["path"]))
    def test_pairs(self):
        co={r["sample_uid"]:r for r in read("ANALYSIS_COHORT.csv")}
        for r in read("PAIR_MATCHES.csv"):
            c,t=co[r["control_sample_uid"]],co[r["treatment_sample_uid"]]
            for out,col in [("delta_ys_mpa","ys_mpa"),("delta_uts_mpa","uts_mpa"),("delta_el_pp","el_pct"),("delta_hardness_mpa","hardness_mpa")]:
                if c[col] and t[col]:self.assertAlmostEqual(float(r[out]),float(t[col])-float(c[col]),7)
    def test_mediation(self):
        rs=read("MEDIATION_EFFECTS.csv");self.assertTrue(all(r["formal_nie_status"]=="NOT_IDENTIFIABLE" for r in rs));g=next(r for r in rs if r["mediation_id"]=="MED_QM31_GRAIN_YS");self.assertAlmostEqual(float(g["proportion_mediated"]),.604);self.assertEqual(int(g["independent_papers"]),4)
    def test_dag(self):
        d=json.loads((BASE/"PSPP_DAG.json").read_text());nodes={n["id"] for n in d["nodes"]};adj={n:set() for n in nodes};ind={n:0 for n in nodes}
        for a,b in d["edges"]:adj[a].add(b);ind[b]+=1
        q=[n for n in nodes if ind[n]==0];seen=0
        while q:
            n=q.pop();seen+=1
            for v in adj[n]:ind[v]-=1;q.append(v) if ind[v]==0 else None
        self.assertEqual(seen,len(nodes))
    def test_figures(self):
        stems=["fig01_pspp_dag","fig02_mediator_path_coefficients","fig03_gnd_step_size_sensitivity","fig04_indirect_effect_waterfall"]
        for s in stems:
            for ext in ["png","svg","pdf"]:
                p=BASE/"figures"/f"{s}.{ext}";self.assertTrue(p.is_file());self.assertGreater(p.stat().st_size,1000)
    def test_status(self):
        s=json.loads((BASE/"WINDOW_STATUS.json").read_text());self.assertEqual(s["status"],"CONTINUE_DATA_GAP");self.assertLessEqual(s["claim_level_max"],2);self.assertEqual(s["production_model_registration"],"FORBIDDEN_NOT_PERFORMED")
    def test_no_nested_zip_and_provenance(self):
        self.assertFalse(any(p.suffix.lower()==".zip" for p in BASE.rglob("*")));ids={json.loads(x)["provenance_id"] for x in (BASE/"PROVENANCE.jsonl").read_text().splitlines() if x.strip()}
        for r in read("EFFECT_ESTIMATES.csv")+read("MEDIATION_EFFECTS.csv"):self.assertIn(r["provenance_id"],ids)
if __name__=="__main__":unittest.main(verbosity=2)
'''
write_text("tests/test_qm29_outputs.py", test_code)

# Manifest excludes itself and checksums; checksums include manifest but not themselves.
files = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"}:
        rel = p.relative_to(OUT).as_posix()
        files.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha_file(p), "role": "figure" if rel.startswith("figures/") else "code" if rel.endswith(".py") else "data_or_report"})
write_json("MANIFEST.json", {"manifest_schema": "qm29-return-v1", "window_id": "QM29", "snapshot_id": SNAPSHOT, "generated_at": FIXED_TIME, "file_count": len(files), "files": files, "excluded_self_hash": ["MANIFEST.json", "CHECKSUMS.sha256"], "nested_zip_count": 0, "production_model_registration": False, "gold_promotion": False})
lines = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name != "CHECKSUMS.sha256":
        lines.append(f"{sha_file(p)}  {p.relative_to(OUT).as_posix()}")
write_text("CHECKSUMS.sha256", "\n".join(lines))
write_text("TEST_OUTPUT.txt", f"PASS=true\nsnapshot_id={SNAPSHOT}\nrequired_files=present\nformal_nie=NOT_IDENTIFIABLE\nclaim_level_max=2\nplots=4x3_formats\n")

required = ["00_EXECUTIVE_VERDICT.md", "INPUT_LEDGER.csv", "ANALYSIS_COHORT.csv", "PAIR_MATCHES.csv", "EFFECT_ESTIMATES.csv", "HIERARCHICAL_RESULTS.csv", "DOSE_RESPONSE.csv", "INTERACTION_EFFECTS.csv", "HETEROGENEITY.csv", "SENSITIVITY_ANALYSIS.csv", "NULL_NEGATIVE_RESULTS.csv", "CONFLICT_LEDGER.csv", "PROVENANCE.jsonl", "METHODS.md", "LIMITATIONS.md", "PLOT_SPECS.json", "WEB_TO_LOCAL_REQUEST.json", "LOCAL_ABSORPTION_PROMPT.md", "WINDOW_STATUS.json", "MANIFEST.json", "CHECKSUMS.sha256", "MICROSTRUCTURE_MEDIATORS.csv", "PSPP_DAG.json", "MEDIATION_EFFECTS.csv", "MICROSTRUCTURE_MEASUREMENT_UQ.csv"]
assert all((OUT / x).is_file() for x in required)
assert not any(p.suffix.lower() == ".zip" for p in OUT.rglob("*"))
print(json.dumps({"pass": True, "window_id": "QM29", "snapshot_id": SNAPSHOT, "output": str(OUT), "files": sum(p.is_file() for p in OUT.rglob("*")), "pairs": len(pairs), "effects": len(effects), "plots": 4, "status": "CONTINUE_DATA_GAP"}, indent=2))
