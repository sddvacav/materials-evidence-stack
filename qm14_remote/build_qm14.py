#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import textwrap
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "FINAL_QM14_REBUILT"
ART = ROOT.parent / "artifacts"
SEED = 20260713
random.seed(SEED)
np.random.seed(SEED)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(rel: str, text: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(rel: str, obj) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(rel: str, rows: list[dict], columns: list[str] | None = None) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in columns})


def finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def sid(text: str, n: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
ART.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Source registry. Byte hashes are never fabricated. Identifier hashes are
# explicitly separated from unavailable original-file byte hashes.
# -----------------------------------------------------------------------------
sources = [
    {
        "paper_uid": "WANG2009_7715D",
        "paper_family_uid": "7715D_SJTU_PROGRAM",
        "citation": "P. Wang et al., Materials Transactions 50 (2009) 1411–1417",
        "doi": "10.2320/matertrans.MRA2008425",
        "source_kind": "PRIMARY_JOURNAL_FULLTEXT",
        "source_locator": "Table 1; Sections 3.2–3.4",
        "opened": True,
        "quantitative_use": "DIRECT_TABLE_TEXT",
        "notes": "Nine matrix/TMC steady-state creep-rate pairs; reported and threshold-corrected n/Q.",
    },
    {
        "paper_uid": "YE2025_TIC_TI5556",
        "paper_family_uid": "TI5556_XATU_PROGRAM",
        "citation": "叶沁, 原位TiC增强钛基复合材料高温拉伸及蠕变性能研究, 2025硕士论文",
        "doi": "",
        "source_kind": "PRIMARY_THESIS_FULLTEXT",
        "source_locator": "Tables 4.2 and 4.4; Chapter 4",
        "opened": True,
        "quantitative_use": "DIRECT_TABLE_TEXT",
        "notes": "Two matrix states, three stresses, matrix/TMC1/TMC2; Q conflict preserved.",
    },
    {
        "paper_uid": "FEREIDUNI2021_LPBF_TIB_TI64",
        "paper_family_uid": "LPBF_TIB_TI64",
        "citation": "E. Fereiduni et al., Journal of Manufacturing Processes (2021)",
        "doi": "10.1016/j.jmapro.2021.08.063",
        "source_kind": "PRIMARY_JOURNAL_FULLTEXT",
        "source_locator": "Table 2; 600 °C/200 MPa creep rupture",
        "opened": True,
        "quantitative_use": "DIRECT_TABLE_TEXT",
        "notes": "As-built and supertransus heat-treated matrix/TMC paired creep rate and life.",
    },
    {
        "paper_uid": "XU2023_TNBCY_CREEP",
        "paper_family_uid": "HIT_HYBRID_TMC_PROGRAM",
        "citation": "L. Xu et al., Transactions of Nonferrous Metals Society of China 33 (2023)",
        "doi": "10.1016/S1003-6326(22)66120-X",
        "source_kind": "PRIMARY_JOURNAL_FULLTEXT",
        "source_locator": "Table 1; 650 °C/120–160 MPa",
        "opened": True,
        "quantitative_use": "DIRECT_TABLE_TEXT",
        "notes": "Incremental 0.5 vol.% Y2O3 comparison; tests interrupted at 50 h.",
    },
    {
        "paper_uid": "GUO2020_TIAL_Y2O3",
        "paper_family_uid": "TIAL_Y2O3_PROGRAM",
        "citation": "Y. Guo et al., Journal of Alloys and Compounds 2020, 153852",
        "doi": "10.1016/j.jallcom.2020.153852",
        "source_kind": "PRIMARY_JOURNAL_FULLTEXT",
        "source_locator": "800 °C creep section; stress-exponent and 350 MPa rupture discussion",
        "opened": True,
        "quantitative_use": "DIRECT_TEXT_PLUS_DERIVED_CALCULATION",
        "notes": "Y2O3-bearing TiAl; TMC life 77 h, reported 62 h extension gives derived 15 h control.",
    },
    {
        "paper_uid": "LI2019_FRONTIERS_IMI834",
        "paper_family_uid": "LI_IMI834_PROGRAM",
        "citation": "J. Li et al., Frontiers in Materials 6 (2019) 276",
        "doi": "10.3389/fmats.2019.00276",
        "source_kind": "PRIMARY_JOURNAL_FULLTEXT",
        "source_locator": "Figures 7–10; creep section",
        "opened": True,
        "quantitative_use": "DIRECT_TEXT_PARAMETERS_FIGURE_RATE_ORDER",
        "notes": "HT1/HT2 matrix and TiB+La2O3 TMC; exact plotted rates not promoted to table-grade values.",
    },
    {
        "paper_uid": "ZHENG2021_Y2O3_NEARALPHA",
        "paper_family_uid": "HIT_HYBRID_TMC_PROGRAM",
        "citation": "Z. Zheng et al., Materials Characterization 178 (2021) 111249",
        "doi": "10.1016/j.matchar.2021.111249",
        "source_kind": "PRIMARY_JOURNAL_ABSTRACT_AND_PROJECT_INDEX",
        "source_locator": "Abstract and project literature index",
        "opened": True,
        "quantitative_use": "SUPPORTIVE_ONLY",
        "notes": "Rate decreased and life increased; approximate threefold life at 700 °C retained only in sensitivity ledger.",
    },
    {
        "paper_uid": "ZHENG2022_HYBRID_700C",
        "paper_family_uid": "HIT_HYBRID_TMC_PROGRAM",
        "citation": "Y. Zheng et al., Materials Characterization 190 (2022) 112067",
        "doi": "10.1016/j.matchar.2022.112067",
        "source_kind": "PRIMARY_JOURNAL_ABSTRACT_AND_PROJECT_INDEX",
        "source_locator": "Abstract; exact creep table pending authoritative extraction",
        "opened": True,
        "quantitative_use": "COHORT_METADATA_ONLY",
        "notes": "Matrix/TiB+TiC+Y2O3 at 700 °C; exact rate/life values not guessed.",
    },
    {
        "paper_uid": "ZHENG2022_TIBTIC_144279",
        "paper_family_uid": "HIT_HYBRID_TMC_PROGRAM",
        "citation": "Y. Zheng et al., Materials Science and Engineering A 860 (2022) 144279",
        "doi": "10.1016/j.msea.2022.144279",
        "source_kind": "PRIMARY_JOURNAL_ABSTRACT_AND_PROJECT_INDEX",
        "source_locator": "Abstract; exact creep table pending authoritative extraction",
        "opened": True,
        "quantitative_use": "COHORT_METADATA_ONLY",
        "notes": "2 and 4 vol.% TiB+TiC at 650/700 °C; exact values not inferred from figures.",
    },
    {
        "paper_uid": "XIAO2009_TIB_LA2O3_IMI834",
        "paper_family_uid": "LI_IMI834_PROGRAM",
        "citation": "L. Xiao et al., Materials Science and Engineering A 499 (2009) 500–506",
        "doi": "10.1016/j.msea.2008.09.002",
        "source_kind": "PRIMARY_JOURNAL_PROJECT_INDEX",
        "source_locator": "Project literature index; parameter context",
        "opened": True,
        "quantitative_use": "SUPPORTIVE_PARAMETER_CONTEXT",
        "notes": "Included for mechanism and program-family dependency control; no duplicated numeric effect.",
    },
]
for s in sources:
    ident = s["doi"] or s["citation"]
    s["identifier_sha256"] = sha256_bytes(ident.encode("utf-8"))
    s["original_file_sha256"] = "UNAVAILABLE_IN_WEB_RUNTIME"

snapshot_payload = json.dumps(
    [{k: s[k] for k in ("paper_uid", "doi", "source_locator", "quantitative_use")} for s in sources],
    ensure_ascii=False,
    sort_keys=True,
).encode("utf-8")
SNAPSHOT_ID = "QM14_REBUILT_DERIVED_" + sha256_bytes(snapshot_payload)[:16]

# -----------------------------------------------------------------------------
# Atomic creep-condition ledger.
# -----------------------------------------------------------------------------
curve_rows: list[dict] = []


def add_curve(
    paper_uid: str,
    family: str,
    sample: str,
    matrix_family: str,
    reinforcement: str,
    fraction,
    fraction_unit: str,
    process: str,
    heat_treatment: str,
    microstructure: str,
    temp: float,
    stress: float,
    rate,
    life,
    duration,
    censoring: str,
    evidence: str,
    locator: str,
    notes: str = "",
    original_rate=None,
    original_rate_unit: str = "",
):
    condition = f"{paper_uid}|{sample}|{heat_treatment}|{temp:g}C|{stress:g}MPa|tension"
    curve_rows.append(
        {
            "record_uid": "CR_" + sid(condition),
            "snapshot_id": SNAPSHOT_ID,
            "paper_uid": paper_uid,
            "paper_family_uid": family,
            "sample_uid": sample,
            "condition_uid": "COND_" + sid(condition),
            "matrix_family": matrix_family,
            "reinforcement": reinforcement,
            "reinforcement_fraction": fraction,
            "reinforcement_fraction_unit": fraction_unit,
            "process": process,
            "heat_treatment": heat_treatment,
            "microstructure_state": microstructure,
            "test_mode": "uniaxial_tensile_creep",
            "temperature_C": temp,
            "stress_MPa": stress,
            "environment": "air_or_not_reported",
            "duration_h": duration,
            "steady_creep_rate_s-1": rate,
            "reported_rate_original": original_rate,
            "reported_rate_unit": original_rate_unit,
            "rupture_life_h": life,
            "censoring": censoring,
            "evidence_grade": evidence,
            "source_locator": locator,
            "notes": notes,
        }
    )

# Wang 2009, Table 1.
wang = {
    600: [(200, 1.02e-8, 6.19e-9), (300, 5.41e-8, 3.27e-8), (350, 6.48e-8, 5.53e-8)],
    650: [(150, 5.93e-8, 3.82e-8), (200, 2.00e-7, 1.46e-7), (300, 7.20e-7, 5.82e-7)],
    700: [(100, 2.11e-7, 8.23e-8), (150, 6.45e-7, 5.48e-7), (200, 1.77e-6, 1.21e-6)],
}
for temp, vals in wang.items():
    for stress, m, t in vals:
        common = dict(
            paper_uid="WANG2009_7715D",
            family="7715D_SJTU_PROGRAM",
            matrix_family="7715D_near_alpha",
            process="consumable_vacuum_arc_remelt+hot_forge",
            heat_treatment="980C_2h_AC+570C_4h_AC",
            microstructure="Widmanstatten_alpha_beta",
            temp=temp,
            stress=stress,
            life="",
            duration="",
            censoring="steady_or_minimum_rate_as_defined_by_source",
            evidence="DIRECT_TABLE_TEXT",
            locator="Table 1",
        )
        add_curve(sample="WANG_M", reinforcement="none", fraction=0, fraction_unit="vol%", rate=m, **common)
        add_curve(sample="WANG_TMC", reinforcement="TiB+TiC", fraction=2.0, fraction_unit="vol% total", rate=t, **common)

# Ye 2025 thesis Tables 4.2 and 4.4.
ye_states = {
    "700C_2h_AC": {
        "micro": "alpha+beta",
        "rates": {
            "YE_M": [1.85e-8, 2.60e-8, 3.92e-8],
            "YE_TMC1": [1.77e-8, 2.54e-8, 3.79e-8],
            "YE_TMC2": [1.38e-8, 1.89e-8, 2.66e-8],
        },
        "locator": "Table 4.2",
    },
    "800C_2h_AC": {
        "micro": "beta_initial_then_secondary_alpha_during_creep",
        "rates": {
            "YE_M": [2.50e-8, 4.01e-8, 7.65e-8],
            "YE_TMC1": [1.74e-8, 2.93e-8, 6.37e-8],
            "YE_TMC2": [1.50e-8, 2.06e-8, 3.43e-8],
        },
        "locator": "Table 4.4",
    },
}
ye_reinf = {
    "YE_M": ("none", 0),
    "YE_TMC1": ("in_situ_TiC_from_Cr3C2_precursor", 3),
    "YE_TMC2": ("in_situ_TiC_from_Cr3C2_precursor", 6),
}
for ht, block in ye_states.items():
    for sample, rates in block["rates"].items():
        reinf, dose = ye_reinf[sample]
        for stress, rate in zip([300, 350, 400], rates):
            add_curve(
                paper_uid="YE2025_TIC_TI5556",
                family="TI5556_XATU_PROGRAM",
                sample=sample + "_" + ht,
                matrix_family="Ti-5Al-5Mo-5Zr-6Cr",
                reinforcement=reinf,
                fraction=dose,
                fraction_unit="wt% Cr3C2 precursor; actual TiC not reported",
                process="vacuum_consumable_arc_melting+forging",
                heat_treatment=ht,
                microstructure=block["micro"],
                temp=500,
                stress=stress,
                rate=rate,
                life="",
                duration=100,
                censoring="interrupted_100h_no_rupture",
                evidence="DIRECT_TABLE_TEXT",
                locator=block["locator"],
            )

# Xu 2023, Table 1; 50 h interrupted.
for stress, r1, r2, strain1, strain2 in [
    (120, 5.34e-8, 4.43e-8, 2.53, 2.47),
    (140, 9.29e-8, 6.17e-8, 3.57, 3.25),
    (160, 1.23e-7, 1.16e-7, 4.44, 4.29),
]:
    base = dict(
        paper_uid="XU2023_TNBCY_CREEP",
        family="HIT_HYBRID_TMC_PROGRAM",
        matrix_family="Ti-6Al-4Sn-8Zr-0.8Mo-1W-1Nb-0.25Si",
        process="induction_skull_melting",
        heat_treatment="as_cast",
        microstructure="basket_weave",
        temp=650,
        stress=stress,
        life="",
        duration=50,
        censoring="interrupted_50h",
        evidence="DIRECT_TABLE_TEXT",
        locator="Table 1",
    )
    add_curve(sample="XU_TMC1", reinforcement="TiB+TiC", fraction=2.5, fraction_unit="vol% total", rate=r1, notes=f"50h strain={strain1}%", **base)
    add_curve(sample="XU_TMC2", reinforcement="TiB+TiC+Y2O3", fraction=3.0, fraction_unit="vol% total", rate=r2, notes=f"50h strain={strain2}%", **base)

# Fereiduni 2021. Convert %/h to s^-1: (%/100)/3600.
for state, ht, mr, tr, ml, tl in [
    ("as_built", "none", 5.93, 4.48, 3.4, 2.9),
    ("heat_treated", "1050C_2h_furnace_cool", 2.16, 0.84, 0.6, 5.8),
]:
    for sample, reinf, rate_pct_h, life in [
        ("FER_M_" + state, "none", mr, ml),
        ("FER_TMC_" + state, "TiB_from_0.2wt%_B4C", tr, tl),
    ]:
        add_curve(
            paper_uid="FEREIDUNI2021_LPBF_TIB_TI64",
            family="LPBF_TIB_TI64",
            sample=sample,
            matrix_family="Ti-6Al-4V",
            reinforcement=reinf,
            fraction=0 if reinf == "none" else 0.2,
            fraction_unit="wt% B4C feedstock",
            process="laser_powder_bed_fusion",
            heat_treatment=ht,
            microstructure=state,
            temp=600,
            stress=200,
            rate=(rate_pct_h / 100.0) / 3600.0,
            life=life,
            duration=life,
            censoring="ruptured",
            evidence="DIRECT_TABLE_TEXT",
            locator="Table 2",
            original_rate=rate_pct_h,
            original_rate_unit="%/h",
        )

# Guo 2020/2021 TiAl-Y2O3 at 800 C / 350 MPa.
for sample, reinf, frac, life, grade, note in [
    ("GUO_TNV", "none", 0, 15.0, "DERIVED_CALCULATION", "Control life inferred as 77-62 h from source text."),
    ("GUO_TNV_Y", "Y2O3", 0.15, 77.0, "DIRECT_TEXT", "TNV-Y2O3 rupture life directly reported."),
]:
    add_curve(
        paper_uid="GUO2020_TIAL_Y2O3",
        family="TIAL_Y2O3_PROGRAM",
        sample=sample,
        matrix_family="Ti-45Al-6Nb-2.5V",
        reinforcement=reinf,
        fraction=frac,
        fraction_unit="at% Y2O3 addition",
        process="induction_skull_melting",
        heat_treatment="as_cast",
        microstructure="TiAl_lamellar",
        temp=800,
        stress=350,
        rate="",
        life=life,
        duration=life,
        censoring="ruptured",
        evidence=grade,
        locator="800 C creep section",
        notes=note,
    )

curve_df = pd.DataFrame(curve_rows)

# -----------------------------------------------------------------------------
# Cohort and explicit matched pairs.
# -----------------------------------------------------------------------------
cohort_rows = []
for s in sources:
    rows = curve_df[curve_df.paper_uid == s["paper_uid"]]
    cohort_rows.append(
        {
            "snapshot_id": SNAPSHOT_ID,
            "paper_uid": s["paper_uid"],
            "paper_family_uid": s["paper_family_uid"],
            "citation": s["citation"],
            "doi": s["doi"],
            "source_kind": s["source_kind"],
            "atomic_curve_rows": int(len(rows)),
            "quantitative_use": s["quantitative_use"],
            "included": "YES",
            "inclusion_role": "PRIMARY_EFFECT" if len(rows) else "PARAMETER_OR_SCOPE_SUPPORT",
            "source_locator": s["source_locator"],
            "exclusion_reason": "",
        }
    )

pair_rows: list[dict] = []


def pair(control_uid: str, treatment_uid: str, outcome_set: str, grade: str = "A", notes: str = ""):
    c = curve_df[curve_df.record_uid == control_uid].iloc[0]
    t = curve_df[curve_df.record_uid == treatment_uid].iloc[0]
    key = f"{c.paper_uid}|{c.condition_uid}|{c.sample_uid}|{t.sample_uid}|{outcome_set}"
    pair_rows.append(
        {
            "pair_uid": "PAIR_" + sid(key),
            "snapshot_id": SNAPSHOT_ID,
            "paper_uid": c.paper_uid,
            "paper_family_uid": c.paper_family_uid,
            "condition_uid_control": c.condition_uid,
            "condition_uid_treatment": t.condition_uid,
            "sample_uid_control": c.sample_uid,
            "sample_uid_treatment": t.sample_uid,
            "temperature_C": c.temperature_C,
            "stress_MPa": c.stress_MPa,
            "heat_treatment": c.heat_treatment,
            "outcome_set": outcome_set,
            "comparability_grade": grade,
            "claim_level": 2,
            "evidence_grade_control": c.evidence_grade,
            "evidence_grade_treatment": t.evidence_grade,
            "notes": notes,
        }
    )

# Wang condition pairs.
for temp in wang:
    for stress, _, _ in wang[temp]:
        sub = curve_df[(curve_df.paper_uid == "WANG2009_7715D") & (curve_df.temperature_C == temp) & (curve_df.stress_MPa == stress)]
        pair(sub[sub.sample_uid == "WANG_M"].record_uid.iloc[0], sub[sub.sample_uid == "WANG_TMC"].record_uid.iloc[0], "steady_creep_rate")
# Ye two dose contrasts per condition.
for ht in ye_states:
    for stress in [300, 350, 400]:
        sub = curve_df[(curve_df.paper_uid == "YE2025_TIC_TI5556") & (curve_df.heat_treatment == ht) & (curve_df.stress_MPa == stress)]
        c = sub[sub.sample_uid.str.startswith("YE_M_")].record_uid.iloc[0]
        pair(c, sub[sub.sample_uid.str.startswith("YE_TMC1_")].record_uid.iloc[0], "steady_creep_rate", notes="3 wt% Cr3C2 precursor arm")
        pair(c, sub[sub.sample_uid.str.startswith("YE_TMC2_")].record_uid.iloc[0], "steady_creep_rate", notes="6 wt% Cr3C2 precursor arm")
# Xu incremental Y2O3.
for stress in [120, 140, 160]:
    sub = curve_df[(curve_df.paper_uid == "XU2023_TNBCY_CREEP") & (curve_df.stress_MPa == stress)]
    pair(sub[sub.sample_uid == "XU_TMC1"].record_uid.iloc[0], sub[sub.sample_uid == "XU_TMC2"].record_uid.iloc[0], "steady_creep_rate", notes="Incremental 0.5 vol% Y2O3 on TiB+TiC background")
# Fereiduni both outcomes for each state.
for state in ["as_built", "heat_treated"]:
    sub = curve_df[curve_df.paper_uid == "FEREIDUNI2021_LPBF_TIB_TI64"]
    c = sub[sub.sample_uid == "FER_M_" + state].record_uid.iloc[0]
    t = sub[sub.sample_uid == "FER_TMC_" + state].record_uid.iloc[0]
    pair(c, t, "steady_creep_rate+rupture_life")
# Guo rupture.
sub = curve_df[curve_df.paper_uid == "GUO2020_TIAL_Y2O3"]
pair(sub[sub.sample_uid == "GUO_TNV"].record_uid.iloc[0], sub[sub.sample_uid == "GUO_TNV_Y"].record_uid.iloc[0], "rupture_life", notes="Control life is source-text-derived; sensitivity exclusion mandatory")

pair_df = pd.DataFrame(pair_rows)

# -----------------------------------------------------------------------------
# Effect estimates.
# -----------------------------------------------------------------------------
effects: list[dict] = []
for _, pr in pair_df.iterrows():
    c = curve_df[curve_df.record_uid == curve_df[curve_df.condition_uid == pr.condition_uid_control].record_uid.iloc[0]]
    # The condition UID is sample-specific; retrieve by sample UID instead.
    c = curve_df[(curve_df.paper_uid == pr.paper_uid) & (curve_df.sample_uid == pr.sample_uid_control) & (curve_df.temperature_C == pr.temperature_C) & (curve_df.stress_MPa == pr.stress_MPa) & (curve_df.heat_treatment == pr.heat_treatment)].iloc[0]
    t = curve_df[(curve_df.paper_uid == pr.paper_uid) & (curve_df.sample_uid == pr.sample_uid_treatment) & (curve_df.temperature_C == pr.temperature_C) & (curve_df.stress_MPa == pr.stress_MPa) & (curve_df.heat_treatment == pr.heat_treatment)].iloc[0]
    outcomes = []
    if finite(c.steady_creep_rate_s-1) and finite(t.steady_creep_rate_s-1):
        outcomes.append(("steady_creep_rate_s-1", float(c.steady_creep_rate_s-1), float(t.steady_creep_rate_s-1), "lower_is_better"))
    if finite(c.rupture_life_h) and finite(t.rupture_life_h):
        outcomes.append(("rupture_life_h", float(c.rupture_life_h), float(t.rupture_life_h), "higher_is_better"))
    for outcome, cv, tv, direction in outcomes:
        lnrr = math.log(tv / cv)
        effects.append(
            {
                "effect_uid": "EFF_" + sid(pr.pair_uid + outcome),
                "pair_uid": pr.pair_uid,
                "snapshot_id": SNAPSHOT_ID,
                "paper_uid": pr.paper_uid,
                "paper_family_uid": pr.paper_family_uid,
                "sample_uid_control": pr.sample_uid_control,
                "sample_uid_treatment": pr.sample_uid_treatment,
                "temperature_C": pr.temperature_C,
                "stress_MPa": pr.stress_MPa,
                "heat_treatment": pr.heat_treatment,
                "outcome": outcome,
                "control_value": cv,
                "treatment_value": tv,
                "absolute_effect": tv - cv,
                "lnRR": lnrr,
                "percent_change": 100.0 * (math.exp(lnrr) - 1.0),
                "benefit_direction": direction,
                "ci_low": "NOT_ESTIMABLE_NO_REPLICATE_VARIANCE",
                "ci_high": "NOT_ESTIMABLE_NO_REPLICATE_VARIANCE",
                "prediction_interval": "NOT_ESTIMABLE_AT_PAIR_LEVEL",
                "comparability_grade": pr.comparability_grade,
                "claim_level": 2,
                "evidence_grade": f"{pr.evidence_grade_control}|{pr.evidence_grade_treatment}",
                "source_locator": next(s["source_locator"] for s in sources if s["paper_uid"] == pr.paper_uid),
                "notes": pr.notes,
            }
        )
effect_df = pd.DataFrame(effects)

# -----------------------------------------------------------------------------
# Recomputed and reported creep parameters.
# -----------------------------------------------------------------------------
params: list[dict] = []


def add_param(paper, family, sample, temp, stress_range, ptype, value, unit, basis, mechanism, grade, locator, warning=""):
    params.append(
        {
            "parameter_uid": "PAR_" + sid(f"{paper}|{sample}|{temp}|{stress_range}|{ptype}|{value}|{basis}"),
            "snapshot_id": SNAPSHOT_ID,
            "paper_uid": paper,
            "paper_family_uid": family,
            "sample_uid": sample,
            "temperature_C": temp,
            "stress_range_MPa": stress_range,
            "parameter_type": ptype,
            "value": value,
            "unit": unit,
            "basis": basis,
            "mechanism_interpretation": mechanism,
            "evidence_grade": grade,
            "source_locator": locator,
            "comparability_warning": warning,
        }
    )

# Recompute n from direct tables for Wang and Ye.
for paper in ["WANG2009_7715D", "YE2025_TIC_TI5556"]:
    for keys, g in curve_df[(curve_df.paper_uid == paper) & curve_df.steady_creep_rate_s-1.apply(finite)].groupby(["paper_family_uid", "sample_uid", "temperature_C", "heat_treatment"]):
        family, sample, temp, ht = keys
        if len(g) >= 3 and g.stress_MPa.nunique() >= 3:
            slope = float(np.polyfit(np.log(g.stress_MPa.astype(float)), np.log(g["steady_creep_rate_s-1"].astype(float)), 1)[0])
            add_param(paper, family, sample, temp, f"{g.stress_MPa.min():g}-{g.stress_MPa.max():g}", "stress_exponent_n", round(slope, 4), "dimensionless", "RECOMPUTED_OLS_LOGLOG", "regime_interpretation_requires_source_context", "DERIVED_CALCULATION", "Direct table rows", "Three-point fit; no replicate uncertainty")
# Reported Wang parameters.
for temp, n in [(600, 3.47), (650, 3.57), (700, 3.05)]:
    add_param("WANG2009_7715D", "7715D_SJTU_PROGRAM", "WANG_M", temp, "source-specific", "stress_exponent_n", n, "dimensionless", "REPORTED_APPARENT", "Class I viscous dislocation glide", "DIRECT_TEXT", "Section 3.2")
    add_param("WANG2009_7715D", "7715D_SJTU_PROGRAM", "WANG_TMC", temp, "effective stress", "stress_exponent_n", 3.5, "dimensionless", "REPORTED_TRUE_THRESHOLD_CORRECTED", "Class I viscous dislocation glide", "DIRECT_TEXT", "Sections 3.3–3.4")
add_param("WANG2009_7715D", "7715D_SJTU_PROGRAM", "WANG_M", "600-700", "150-300", "activation_energy_Q", "347-365", "kJ/mol", "REPORTED_APPARENT_RANGE", "solute-drag/Class I context", "DIRECT_TEXT", "Section 3.2")
add_param("WANG2009_7715D", "7715D_SJTU_PROGRAM", "WANG_TMC", "600-700", "150-300", "activation_energy_Q", "374-398", "kJ/mol", "REPORTED_APPARENT_RANGE", "threshold-stress-affected", "DIRECT_TEXT", "Section 3.2")
add_param("WANG2009_7715D", "7715D_SJTU_PROGRAM", "WANG_M+TMC", "600-700", "effective stress", "activation_energy_Q", 343, "kJ/mol", "REPORTED_THRESHOLD_CORRECTED", "same mechanism after threshold compensation", "DIRECT_TEXT", "Section 3.3")
# Ye reported Q values.
for ht, micro, vals in [
    ("700C_2h_AC", "alpha+beta", {"YE_M":153.19,"YE_TMC1":104.64,"YE_TMC2":156.63}),
    ("800C_2h_AC", "beta", {"YE_M":78.26,"YE_TMC1":130.18,"YE_TMC2":225.94}),
]:
    for sample, q in vals.items():
        add_param("YE2025_TIC_TI5556", "TI5556_XATU_PROGRAM", sample+"_"+ht, 500, "300-400", "activation_energy_Q", q, "kJ/mol", "REPORTED_THESIS_CHINESE_CHAPTER", "phase-state-dependent; do not pool", "DIRECT_TEXT", "Chapter 4 Q discussion", "English abstract ordering conflict logged")
# Xu reported n.
add_param("XU2023_TNBCY_CREEP", "HIT_HYBRID_TMC_PROGRAM", "XU_TMC1", 650, "120-160", "stress_exponent_n", 2.92, "dimensionless", "REPORTED", "solute-drag creep", "DIRECT_TEXT", "Creep results")
add_param("XU2023_TNBCY_CREEP", "HIT_HYBRID_TMC_PROGRAM", "XU_TMC2", 650, "120-160", "stress_exponent_n", 3.32, "dimensionless", "REPORTED", "solute-drag creep", "DIRECT_TEXT", "Creep results")
# Frontiers 2019 parameters.
for sample, n, ht in [("LI_M_HT1",4.6,"HT1"),("LI_M_HT2",4.5,"HT2"),("LI_TMC_HT1",5.3,"HT1"),("LI_TMC_HT2",5.0,"HT2")]:
    add_param("LI2019_FRONTIERS_IMI834", "LI_IMI834_PROGRAM", sample, 650, "figure-specific", "stress_exponent_n", n, "dimensionless", "REPORTED_APPARENT", "dislocation-climb/threshold-stress context", "DIRECT_TEXT", "Figure 8 discussion")
for sample, q, stress, ht in [("LI_M_HT1",357,150,"HT1"),("LI_M_HT2",350,150,"HT2"),("LI_TMC_HT1",387,200,"HT1"),("LI_TMC_HT2",379,200,"HT2")]:
    add_param("LI2019_FRONTIERS_IMI834", "LI_IMI834_PROGRAM", sample, "600-700", str(stress), "activation_energy_Q", q, "kJ/mol", "REPORTED", "apparent activation energy", "DIRECT_TEXT", "Figure 9 discussion", "Matrix and TMC Q were evaluated at different constant stresses; no direct Q effect")
# Guo TiAl n.
add_param("GUO2020_TIAL_Y2O3", "TIAL_Y2O3_PROGRAM", "GUO_TNV", 800, "200-350", "stress_exponent_n", 4.03, "dimensionless", "REPORTED", "dislocation climb plus twinning", "DIRECT_TEXT", "800 C creep section")
add_param("GUO2020_TIAL_Y2O3", "TIAL_Y2O3_PROGRAM", "GUO_TNV_Y", 800, "200-350", "stress_exponent_n", 3.09, "dimensionless", "REPORTED", "dislocation climb plus twinning", "DIRECT_TEXT", "800 C creep section")
# Zheng 2021 hybrid parameter context.
add_param("ZHENG2021_Y2O3_NEARALPHA", "HIT_HYBRID_TMC_PROGRAM", "hybrid_TMC", 650, "source-specific", "stress_exponent_n", 4.5, "dimensionless", "REPORTED_ABSTRACT", "dislocation climb", "DIRECT_TEXT", "Abstract")
add_param("ZHENG2021_Y2O3_NEARALPHA", "HIT_HYBRID_TMC_PROGRAM", "hybrid_TMC", 700, "source-specific", "stress_exponent_n", 3.9, "dimensionless", "REPORTED_ABSTRACT", "dislocation climb", "DIRECT_TEXT", "Abstract")
param_df = pd.DataFrame(params)

# -----------------------------------------------------------------------------
# Dose response and interactions.
# -----------------------------------------------------------------------------
dose_rows = []
for ht in ye_states:
    for stress in [300, 350, 400]:
        g = curve_df[(curve_df.paper_uid == "YE2025_TIC_TI5556") & (curve_df.heat_treatment == ht) & (curve_df.stress_MPa == stress)].copy()
        x = g.reinforcement_fraction.astype(float).to_numpy()
        y = np.log(g["steady_creep_rate_s-1"].astype(float).to_numpy())
        slope = float(np.polyfit(x, y, 1)[0])
        dose_rows.append({
            "dose_result_uid":"DOSE_"+sid(f"YE|{ht}|{stress}"),
            "snapshot_id":SNAPSHOT_ID,
            "paper_uid":"YE2025_TIC_TI5556",
            "matrix_state":ye_states[ht]["micro"],
            "temperature_C":500,
            "stress_MPa":stress,
            "dose_definition":"wt% Cr3C2 precursor; not actual TiC vol%",
            "dose_levels":"0|3|6",
            "model":"linear ln(rate)~precursor_dose",
            "slope_per_dose_unit":slope,
            "endpoint_lnRR_6_vs_0":float(y[x.argmax()]-y[x.argmin()]),
            "status":"DESCRIPTIVE_3_POINT_NO_REPLICATE_DF",
            "claim_level":2,
        })
# two-point contrasts as non-fitted dose information.
for paper, dose_def, levels, note in [
    ("WANG2009_7715D","total TiB+TiC vol%","0|2","Only one non-zero dose"),
    ("XU2023_TNBCY_CREEP","incremental Y2O3 vol% on 2.5 vol% TiB+TiC background","0|0.5","Incremental formulation contrast"),
]:
    dose_rows.append({"dose_result_uid":"DOSE_"+sid(paper),"snapshot_id":SNAPSHOT_ID,"paper_uid":paper,"matrix_state":"source_specific","temperature_C":"source_specific","stress_MPa":"source_specific","dose_definition":dose_def,"dose_levels":levels,"model":"NOT_FIT_TWO_POINT_ONLY","slope_per_dose_unit":"NOT_IDENTIFIABLE","endpoint_lnRR_6_vs_0":"","status":note,"claim_level":2})

interaction_rows = []
# Fereiduni HT interaction in lnRR.
fer = effect_df[effect_df.paper_uid == "FEREIDUNI2021_LPBF_TIB_TI64"]
for outcome in ["steady_creep_rate_s-1", "rupture_life_h"]:
    a = float(fer[(fer.outcome == outcome) & (fer.heat_treatment == "none")].lnRR.iloc[0])
    h = float(fer[(fer.outcome == outcome) & (fer.heat_treatment == "1050C_2h_furnace_cool")].lnRR.iloc[0])
    interaction_rows.append({"interaction_uid":"INT_"+sid("FER"+outcome),"snapshot_id":SNAPSHOT_ID,"paper_uid":"FEREIDUNI2021_LPBF_TIB_TI64","interaction":"reinforcement_x_heat_treatment","outcome":outcome,"contrast_definition":"lnRR_HT-lnRR_as_built","estimate":h-a,"interpretation":"Heat treatment strongly modifies reinforcement effect","uncertainty":"NOT_ESTIMABLE_NO_REPLICATES","claim_level":2})
# Ye phase-state interaction per dose/stress.
for dose_name in ["TMC1", "TMC2"]:
    for stress in [300,350,400]:
        y = effect_df[(effect_df.paper_uid=="YE2025_TIC_TI5556") & (effect_df.stress_MPa==stress) & effect_df.sample_uid_treatment.str.contains(dose_name)]
        ab = float(y[y.heat_treatment=="700C_2h_AC"].lnRR.iloc[0])
        b = float(y[y.heat_treatment=="800C_2h_AC"].lnRR.iloc[0])
        interaction_rows.append({"interaction_uid":"INT_"+sid(f"YE|{dose_name}|{stress}"),"snapshot_id":SNAPSHOT_ID,"paper_uid":"YE2025_TIC_TI5556","interaction":"reinforcement_x_initial_matrix_state","outcome":"steady_creep_rate_s-1","contrast_definition":"lnRR_beta_state-lnRR_alpha+beta_state","estimate":b-ab,"interpretation":"Negative means larger rate reduction after 800C beta-state treatment","uncertainty":"NOT_ESTIMABLE_NO_REPLICATES","claim_level":2})

# -----------------------------------------------------------------------------
# Paper-cluster descriptive summaries and sensitivity.
# -----------------------------------------------------------------------------
def cluster_bootstrap(df: pd.DataFrame, nboot: int = 10000):
    paper_means = df.groupby("paper_uid").lnRR.mean().to_dict()
    papers = sorted(paper_means)
    vals = np.array([paper_means[p] for p in papers], dtype=float)
    obs = float(vals.mean())
    rng = np.random.default_rng(SEED)
    boots = np.array([rng.choice(vals, size=len(vals), replace=True).mean() for _ in range(nboot)]) if len(vals) else np.array([])
    ci = np.quantile(boots, [0.025, 0.975]).tolist() if len(boots) else [np.nan, np.nan]
    pi = [float(vals.min()), float(vals.max())] if len(vals) else [np.nan, np.nan]
    return papers, vals, obs, ci, pi

hier_rows=[]
for outcome, direction in [("steady_creep_rate_s-1","negative_beneficial"),("rupture_life_h","positive_beneficial")]:
    d=effect_df[effect_df.outcome==outcome]
    papers, vals, obs, ci, pi=cluster_bootstrap(d)
    hier_rows.append({"result_uid":"HIER_"+sid(outcome),"snapshot_id":SNAPSHOT_ID,"outcome":outcome,"model":"equal-paper-weight cluster bootstrap of paper mean lnRR","independent_papers":len(papers),"effect_estimates":len(d),"estimate_lnRR":obs,"cluster_bootstrap_95_low":ci[0],"cluster_bootstrap_95_high":ci[1],"observed_paper_mean_range_low":pi[0],"observed_paper_mean_range_high":pi[1],"status":"DESCRIPTIVE_HETEROGENEITY_SUMMARY_NOT_UNIVERSAL_EFFECT","claim_level":2,"warning":"Disconnected matrix/process/stress-temperature islands; not causal and not a production model."})
hier_rows.append({"result_uid":"HIER_"+sid("mixed_model"),"snapshot_id":SNAPSHOT_ID,"outcome":"all","model":"random_intercept/random_slope universal reinforcement model","independent_papers":len(set(effect_df.paper_uid)),"effect_estimates":len(effect_df),"estimate_lnRR":"NOT_IDENTIFIABLE","cluster_bootstrap_95_low":"","cluster_bootstrap_95_high":"","observed_paper_mean_range_low":"","observed_paper_mean_range_high":"","status":"NOT_IDENTIFIABLE_DISCONNECTED_SUPPORT_AND_NO_WITHIN_PAIR_VARIANCE","claim_level":2,"warning":"A pooled coefficient would average across mechanisms and violate the MDU claim ceiling."})

sensitivity=[]
lopo=[]
for outcome in ["steady_creep_rate_s-1","rupture_life_h"]:
    d=effect_df[effect_df.outcome==outcome]
    full=float(d.groupby("paper_uid").lnRR.mean().mean())
    for p in sorted(d.paper_uid.unique()):
        remain=d[d.paper_uid!=p]
        est=float(remain.groupby("paper_uid").lnRR.mean().mean()) if len(remain) else np.nan
        row={"analysis_uid":"LOPO_"+sid(outcome+p),"snapshot_id":SNAPSHOT_ID,"outcome":outcome,"left_out_paper":p,"full_equal_paper_mean_lnRR":full,"lopo_equal_paper_mean_lnRR":est,"sign_preserved":bool(np.sign(full)==np.sign(est)) if finite(est) else "NOT_IDENTIFIABLE","status":"LOPO_DESCRIPTIVE"}
        lopo.append(row)
        sensitivity.append({"sensitivity_uid":row["analysis_uid"],"snapshot_id":SNAPSHOT_ID,"analysis":"leave_one_paper_out","outcome":outcome,"exclusion":p,"estimate":est,"reference_estimate":full,"conclusion":"sign_preserved="+str(row["sign_preserved"]),"status":"COMPLETE"})
# Additional sensitivity definitions.
creep=effect_df[effect_df.outcome=="steady_creep_rate_s-1"]
for label, sub in [
    ("exclude_thesis",creep[creep.paper_uid!="YE2025_TIC_TI5556"]),
    ("median_pair_effect",creep),
]:
    est=float(sub.lnRR.median()) if label=="median_pair_effect" else float(sub.groupby("paper_uid").lnRR.mean().mean())
    sensitivity.append({"sensitivity_uid":"SENS_"+sid(label),"snapshot_id":SNAPSHOT_ID,"analysis":label,"outcome":"steady_creep_rate_s-1","exclusion":"YE2025" if label=="exclude_thesis" else "none","estimate":est,"reference_estimate":float(creep.groupby("paper_uid").lnRR.mean().mean()),"conclusion":"Direction retained; magnitude changes","status":"COMPLETE"})
# Guo derived control exclusion.
rup=effect_df[effect_df.outcome=="rupture_life_h"]
sub=rup[rup.paper_uid!="GUO2020_TIAL_Y2O3"]
sensitivity.append({"sensitivity_uid":"SENS_"+sid("exclude_derived_guo"),"snapshot_id":SNAPSHOT_ID,"analysis":"exclude_derived_control_life","outcome":"rupture_life_h","exclusion":"GUO2020_TIAL_Y2O3","estimate":float(sub.groupby("paper_uid").lnRR.mean().mean()),"reference_estimate":float(rup.groupby("paper_uid").lnRR.mean().mean()),"conclusion":"Rupture summary remains dominated by Fereiduni heat-treatment interaction; no universal life effect","status":"COMPLETE"})

hetero=[]
for outcome in ["steady_creep_rate_s-1","rupture_life_h"]:
    d=effect_df[effect_df.outcome==outcome]
    pm=d.groupby("paper_uid").lnRR.mean()
    hetero.append({"heterogeneity_uid":"HET_"+sid(outcome),"snapshot_id":SNAPSHOT_ID,"outcome":outcome,"independent_papers":len(pm),"paper_mean_lnRR_min":float(pm.min()),"paper_mean_lnRR_max":float(pm.max()),"paper_mean_lnRR_sd":float(pm.std(ddof=1)) if len(pm)>1 else "NOT_IDENTIFIABLE","pair_lnRR_min":float(d.lnRR.min()),"pair_lnRR_max":float(d.lnRR.max()),"I2":"NOT_IDENTIFIABLE_WITHOUT_PAIR_LEVEL_STANDARD_ERRORS","interpretation":"Materially heterogeneous; mechanism and processing strata must remain separate."})

# -----------------------------------------------------------------------------
# Rupture effects, mechanisms, conflicts, null results.
# -----------------------------------------------------------------------------
rupture_df=effect_df[effect_df.outcome=="rupture_life_h"].copy()
rupture_rows=rupture_df.to_dict("records")
mechanisms=[
    {"regime_uid":"REG_WANG","snapshot_id":SNAPSHOT_ID,"paper_uid":"WANG2009_7715D","matrix_family":"7715D","temperature_C":"600-700","stress_MPa":"100-350","n_range":"3.05-3.57 matrix; true 3.5 TMC","Q_kJ_mol":"343 corrected","mechanism":"Class I viscous dislocation glide with threshold-stress contribution","support":"DIRECT_TEXT+TABLE","boundary":"No transition identified inside tested range"},
    {"regime_uid":"REG_YE_AB","snapshot_id":SNAPSHOT_ID,"paper_uid":"YE2025_TIC_TI5556","matrix_family":"Ti-5556","temperature_C":500,"stress_MPa":"300-400","n_range":"recomputed per sample","Q_kJ_mol":"104.64-156.63","mechanism":"solid-solution-controlled viscous dislocation glide; alpha+beta initial state","support":"DIRECT_TABLE_TEXT","boundary":"100 h interrupted; no rupture"},
    {"regime_uid":"REG_YE_B","snapshot_id":SNAPSHOT_ID,"paper_uid":"YE2025_TIC_TI5556","matrix_family":"Ti-5556","temperature_C":500,"stress_MPa":"300-400","n_range":"recomputed per sample","Q_kJ_mol":"78.26-225.94","mechanism":"phase-state-dependent glide/viscous-glide interpretation","support":"DIRECT_TABLE_TEXT","boundary":"Secondary alpha evolves during creep"},
    {"regime_uid":"REG_XU","snapshot_id":SNAPSHOT_ID,"paper_uid":"XU2023_TNBCY_CREEP","matrix_family":"near-alpha hybrid TMC","temperature_C":650,"stress_MPa":"120-160","n_range":"2.92-3.32","Q_kJ_mol":"NR","mechanism":"solute-drag creep; interfaces/reinforcements/silicides pin dislocations","support":"DIRECT_TEXT+TABLE","boundary":"50 h interrupted"},
    {"regime_uid":"REG_FER","snapshot_id":SNAPSHOT_ID,"paper_uid":"FEREIDUNI2021_LPBF_TIB_TI64","matrix_family":"LPBF Ti64","temperature_C":600,"stress_MPa":200,"n_range":"NR","Q_kJ_mol":"NR","mechanism":"dislocation climb with TiB/interface and microstructure effects","support":"DIRECT_TEXT+TABLE","boundary":"Single stress-temperature point per state"},
    {"regime_uid":"REG_LI","snapshot_id":SNAPSHOT_ID,"paper_uid":"LI2019_FRONTIERS_IMI834","matrix_family":"IMI834","temperature_C":"600-700","stress_MPa":"source-specific","n_range":"4.5-5.3 at 650C","Q_kJ_mol":"350-387","mechanism":"dislocation climb plus TMC threshold stress/load transfer","support":"DIRECT_TEXT","boundary":"Matrix and TMC Q evaluated at different stresses"},
    {"regime_uid":"REG_GUO","snapshot_id":SNAPSHOT_ID,"paper_uid":"GUO2020_TIAL_Y2O3","matrix_family":"TiAl","temperature_C":800,"stress_MPa":"200-350","n_range":"4.03 matrix; 3.09 Y2O3","Q_kJ_mol":"NR","mechanism":"dislocation climb plus twinning; grain-boundary cavity/crack suppression","support":"DIRECT_TEXT","boundary":"TiAl-specific; not generic alpha-Ti service qualification"},
]

nulls=[
    {"result_uid":"NULL_001","paper_uid":"FEREIDUNI2021_LPBF_TIB_TI64","result":"As-built TiB lowered steady creep rate by about 24.5% but shortened rupture life from 3.4 to 2.9 h.","type":"COUNTEREXAMPLE","implication":"Lower steady-state rate is not sufficient for longer life."},
    {"result_uid":"NULL_002","paper_uid":"YE2025_TIC_TI5556","result":"TMC1 in the alpha+beta state changed rate by only about 2-4% across 300-400 MPa.","type":"SMALL_EFFECT","implication":"A reinforcement label does not guarantee a material rate reduction."},
    {"result_uid":"NULL_003","paper_uid":"XU2023_TNBCY_CREEP","result":"Incremental Y2O3 rate reduction shrank to about 5.7% at 160 MPa.","type":"STRESS_DEPENDENT_ATTENUATION","implication":"Benefit is stress dependent."},
    {"result_uid":"NULL_004","paper_uid":"LI2019_FRONTIERS_IMI834","result":"TRIPLEX heat treatment slightly increased creep rate relative to beta heat treatment while improving elongation.","type":"TRADEOFF","implication":"Creep resistance and ductility optimization are not identical objectives."},
    {"result_uid":"NULL_005","paper_uid":"WANG2009_7715D","result":"Threshold correction collapsed matrix and TMC activation energy to the same 343 kJ/mol.","type":"MECHANISM_NONSHIFT","implication":"Reinforcement can reduce rate without changing the controlling thermal activation process."},
]

conflicts=[
    {"conflict_uid":"CF_OLD_800C","severity":"CRITICAL","object":"superseded FINAL_QM14.zip verdict","claim_a":"No 800 C service claim is supported; quantitative support is 600-700 C","claim_b":"Project primary literature contains a direct 800 C TiAl/Y2O3 paired rupture study","resolution":"Old verdict invalidated. Correct ceiling: 800 C TiAl-specific evidence exists, but no generic 800 C qualification.","status":"RESOLVED_IN_REBUILD"},
    {"conflict_uid":"CF_OLD_OMISSION_YE","severity":"CRITICAL","object":"superseded FINAL_QM14.zip cohort","claim_a":"2025 TiC/Ti-5556 thesis absent","claim_b":"Thesis contains two matrix states and 18 direct creep-rate rows","resolution":"All table values incorporated; thesis retained as one independent study.","status":"RESOLVED_IN_REBUILD"},
    {"conflict_uid":"CF_YE_Q_ORDER","severity":"HIGH","object":"Ye 2025 activation energies","claim_a":"Chinese chapter assigns alpha+beta Q as M/TMC1/TMC2=153.19/104.64/156.63","claim_b":"English abstract appears to reorder labels","resolution":"Chinese chapter/table context used; abstract conflict preserved and values excluded from cross-study pooled Q.","status":"OPEN_SOURCE_CONFLICT"},
    {"conflict_uid":"CF_FER_LIFE","severity":"MEDIUM","object":"Fereiduni heat-treated TMC life","claim_a":"Table/main text 5.8 h","claim_b":"Abstract occurrence 5.9 h","resolution":"Table 2 value 5.8 h used; 5.9 h retained as alternate sensitivity value.","status":"RESOLVED_BY_TABLE_PRIORITY"},
    {"conflict_uid":"CF_LI_FRACTION","severity":"MEDIUM","object":"Li IMI834 TMC reinforcement fraction","claim_a":"Project thesis reports actual TiB 1.26 vol% and La2O3 0.582 vol%","claim_b":"Frontiers paper design reports 1.8 and 0.6 vol%","resolution":"Paper-specific nominal values retained; thesis actual values not merged across source identities.","status":"RESOLVED_BY_SOURCE_SCOPE"},
    {"conflict_uid":"CF_FRONT_Q_STRESS","severity":"HIGH","object":"Frontiers 2019 Q comparison","claim_a":"Matrix Q at 150 MPa","claim_b":"TMC Q at 200 MPa","resolution":"No direct reinforcement delta-Q estimated because constant-stress estimands differ.","status":"RESOLVED_NOT_COMPARABLE"},
    {"conflict_uid":"CF_MATCHAR112067","severity":"HIGH","object":"Materials Characterization 112067","claim_a":"Abstract supports improved 700 C creep behavior","claim_b":"Exact rate/life table unavailable in authoritative snapshot","resolution":"Cohort metadata only; no numeric effect fabricated.","status":"OPEN_DATA_GAP"},
    {"conflict_uid":"CF_MSEA144279","severity":"HIGH","object":"MSEA 144279","claim_a":"2 vs 4 vol% TiB+TiC dose series exists","claim_b":"Exact table/curve values not recovered into authoritative atomic rows","resolution":"No dose coefficient estimated from figures/abstract.","status":"OPEN_DATA_GAP"},
    {"conflict_uid":"CF_SNAPSHOT","severity":"CRITICAL","object":"Q40/V29 snapshot","claim_a":"MDU requires snapshot_id+source_hash binding","claim_b":"Authoritative V29 atomic/provenance snapshot not present in web return","resolution":"Derived snapshot created and explicitly barred from Gold/production promotion.","status":"OPEN_DATA_GAP"},
]

# -----------------------------------------------------------------------------
# Input ledger: distinguish actually opened primary sources from indexed project
# packages. The package inventory is terminally classified without pretending
# byte-level inspection.
# -----------------------------------------------------------------------------
project_packages = [
"00_统一上传总控与校验信息_20260712.zip","S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
"S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip","S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip","S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip","S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip","S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip","S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip","S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip","S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip",
"S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip","S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip","S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip","S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip",
] + [f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1,11)]
input_rows=[]
for name in project_packages:
    input_rows.append({"input_uid":"IN_"+sid(name),"snapshot_id":SNAPSHOT_ID,"input_name":name,"input_role":"PROJECT_PACKAGE_INDEX","actually_opened":"NO_BYTE_STREAM_IN_REBUILD_RUNTIME","source_hash":"UNAVAILABLE","hash_type":"NONE","terminal_status":"INDEX_REFERENCED; TARGETED_PRIMARY_SOURCES_RECOVERED_SEPARATELY","use_in_analysis":"DISCOVERY_AND_CROSSCHECK_ONLY","notes":"No claim of full member-byte inspection; prevents the false all-opened assertion in the superseded package."})
input_rows.append({"input_uid":"IN_MDU","snapshot_id":SNAPSHOT_ID,"input_name":"QM14_蠕变、持久寿命和应力—温度—时间耦合.md","input_role":"EXECUTION_CONTRACT","actually_opened":"YES","source_hash":"file_00000000c8ac720b9242ee0444eada42","hash_type":"CHATGPT_FILE_ID_NOT_BYTE_SHA","terminal_status":"CONSUMED","use_in_analysis":"METHOD_AND_ACCEPTANCE_CONTRACT","notes":"Byte SHA unavailable in web runtime."})
for s in sources:
    input_rows.append({"input_uid":"IN_"+sid(s["paper_uid"]),"snapshot_id":SNAPSHOT_ID,"input_name":s["citation"],"input_role":s["source_kind"],"actually_opened":"YES" if s["opened"] else "NO","source_hash":s["identifier_sha256"],"hash_type":"IDENTIFIER_SHA256_NOT_FILE_BYTE_HASH","terminal_status":"CONSUMED" if s["quantitative_use"]!="COHORT_METADATA_ONLY" else "COHORT_METADATA_ONLY","use_in_analysis":s["quantitative_use"],"notes":s["source_locator"]+"; "+s["notes"]})

excluded=[
    {"paper_uid":"HYDROGEN_TI_ALLOY_2022","reason":"No reinforcement TMC estimand; hydrogen-modified alloy only","terminal_status":"EXCLUDED_SCOPE"},
    {"paper_uid":"REVIEW_ONLY_ROWS","reason":"Review values cannot replace primary specimen-level evidence","terminal_status":"EXCLUDED_EVIDENCE_LEVEL"},
    {"paper_uid":"FIGURE_ONLY_UNDIGITIZED","reason":"Exact axes/curve coordinates not independently digitized and validated","terminal_status":"EXCLUDED_NUMERIC_EFFECT; RETAINED_FOR_REQUEST"},
]

# -----------------------------------------------------------------------------
# Write tabular outputs.
# -----------------------------------------------------------------------------
write_csv("INPUT_LEDGER.csv", input_rows)
write_csv("SOURCE_COVERAGE_MATRIX.csv", [{"paper_uid":s["paper_uid"],"fulltext_or_index":s["source_kind"],"rate_rows":int((curve_df.paper_uid==s["paper_uid"]).sum()),"exact_rate_effect":"YES" if s["paper_uid"] in set(effect_df[effect_df.outcome=="steady_creep_rate_s-1"].paper_uid) else "NO","exact_rupture_effect":"YES" if s["paper_uid"] in set(effect_df[effect_df.outcome=="rupture_life_h"].paper_uid) else "NO","n_available":"YES" if s["paper_uid"] in set(param_df[param_df.parameter_type=="stress_exponent_n"].paper_uid) else "NO","Q_available":"YES" if s["paper_uid"] in set(param_df[param_df.parameter_type=="activation_energy_Q"].paper_uid) else "NO","terminal_status":"USED"} for s in sources])
write_csv("ANALYSIS_COHORT.csv", cohort_rows)
write_csv("EXCLUDED_RECORDS.csv", excluded)
write_csv("PAIR_MATCHES.csv", pair_df.to_dict("records"))
write_csv("EFFECT_ESTIMATES.csv", effect_df.to_dict("records"))
write_csv("HIERARCHICAL_RESULTS.csv", hier_rows)
write_csv("DOSE_RESPONSE.csv", dose_rows)
write_csv("INTERACTION_EFFECTS.csv", interaction_rows)
write_csv("HETEROGENEITY.csv", hetero)
write_csv("SENSITIVITY_ANALYSIS.csv", sensitivity)
write_csv("LOPO_RESULTS.csv", lopo)
write_csv("LEAVE_FAMILY_OUT_RESULTS.csv", [{"analysis_uid":"LFO_"+sid(fam),"snapshot_id":SNAPSHOT_ID,"left_out_family":fam,"outcome":"steady_creep_rate_s-1","estimate_equal_paper_mean_lnRR":float(creep[creep.paper_family_uid!=fam].groupby("paper_uid").lnRR.mean().mean()) if len(creep[creep.paper_family_uid!=fam]) else "NOT_IDENTIFIABLE","status":"DESCRIPTIVE"} for fam in sorted(creep.paper_family_uid.unique())])
write_csv("NULL_NEGATIVE_RESULTS.csv", nulls)
write_csv("CONFLICT_LEDGER.csv", conflicts)
write_csv("CREEP_CURVE_LEDGER.csv", curve_df.to_dict("records"))
write_csv("CREEP_PARAMETERS.csv", param_df.to_dict("records"))
write_csv("RUPTURE_EFFECTS.csv", rupture_rows)
write_csv("CREEP_MECHANISM_REGIMES.csv", mechanisms)

# Provenance per source, atomic row, and effect.
prov=[]
for s in sources:
    prov.append({"object_type":"source","object_uid":s["paper_uid"],"snapshot_id":SNAPSHOT_ID,"paper_uid":s["paper_uid"],"sample_uid":"","condition_uid":"","source_identifier":s["doi"] or s["citation"],"identifier_sha256":s["identifier_sha256"],"original_file_sha256":"UNAVAILABLE_IN_WEB_RUNTIME","source_locator":s["source_locator"],"evidence_grade":s["quantitative_use"],"transform":"none"})
for r in curve_rows:
    prov.append({"object_type":"atomic_curve_row","object_uid":r["record_uid"],"snapshot_id":SNAPSHOT_ID,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"source_identifier":next((s["doi"] or s["citation"] for s in sources if s["paper_uid"]==r["paper_uid"]),""),"identifier_sha256":next((s["identifier_sha256"] for s in sources if s["paper_uid"]==r["paper_uid"]),""),"original_file_sha256":"UNAVAILABLE_IN_WEB_RUNTIME","source_locator":r["source_locator"],"evidence_grade":r["evidence_grade"],"transform":"unit conversion only" if r.get("reported_rate_original") not in (None,"") else "none"})
for r in effects:
    prov.append({"object_type":"effect_estimate","object_uid":r["effect_uid"],"snapshot_id":SNAPSHOT_ID,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid_treatment"],"condition_uid":r["pair_uid"],"source_identifier":next((s["doi"] or s["citation"] for s in sources if s["paper_uid"]==r["paper_uid"]),""),"identifier_sha256":next((s["identifier_sha256"] for s in sources if s["paper_uid"]==r["paper_uid"]),""),"original_file_sha256":"UNAVAILABLE_IN_WEB_RUNTIME","source_locator":r["source_locator"],"evidence_grade":r["evidence_grade"],"transform":"lnRR=ln(treatment/control); percent=100*(exp(lnRR)-1)"})
with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8") as f:
    for row in prov:
        f.write(json.dumps(row,ensure_ascii=False)+"\n")

# -----------------------------------------------------------------------------
# Figure data and reproducible plot scripts.
# -----------------------------------------------------------------------------
figdata=OUT/"figure_data"; plotcode=OUT/"plot_code"; figs=OUT/"figures"
figdata.mkdir(); plotcode.mkdir(); figs.mkdir()
curve_plot=curve_df[curve_df["steady_creep_rate_s-1"].apply(finite)].copy()
curve_plot.to_csv(figdata/"fig01_creep_rate_stress.csv",index=False)
param_df[param_df.parameter_type=="stress_exponent_n"].to_csv(figdata/"fig02_n_forest.csv",index=False)
param_df[param_df.parameter_type=="activation_energy_Q"].to_csv(figdata/"fig03_q_forest.csv",index=False)
curve_df[curve_df["rupture_life_h"].apply(finite)].to_csv(figdata/"fig04_rupture_support.csv",index=False)
pd.DataFrame(mechanisms).to_csv(figdata/"fig05_mechanism_regimes.csv",index=False)
effect_df[effect_df.outcome=="steady_creep_rate_s-1"].to_csv(figdata/"fig06_creep_effect_forest.csv",index=False)

common_py='''from pathlib import Path\nimport argparse\nimport matplotlib.pyplot as plt\nimport pandas as pd\n\ndef get_root():\n    ap=argparse.ArgumentParser()\n    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))\n    return Path(ap.parse_args().root).resolve()\n\ndef save3(fig, root, stem):\n    out=root/"figures"\n    out.mkdir(parents=True,exist_ok=True)\n    fig.savefig(out/(stem+".svg"),bbox_inches="tight")\n    fig.savefig(out/(stem+".pdf"),bbox_inches="tight")\n    fig.savefig(out/(stem+".png"),dpi=600,bbox_inches="tight")\n    plt.close(fig)\n'''
write_text("plot_code/_common.py",common_py)

plot01='''from _common import *\nimport numpy as np\nroot=get_root(); df=pd.read_csv(root/"figure_data/fig01_creep_rate_stress.csv")\nfig,ax=plt.subplots(figsize=(10,7))\nfor key,g in df.groupby(["paper_uid","sample_uid","temperature_C","heat_treatment"]):\n    if g["stress_MPa"].nunique()<2: continue\n    g=g.sort_values("stress_MPa")\n    label=f"{key[0]} | {key[1]} | {key[2]:g} C"\n    ax.plot(g["stress_MPa"],g["steady_creep_rate_s-1"],marker="o",label=label)\nax.set_xscale("log"); ax.set_yscale("log")\nax.set_xlabel("Applied stress (MPa)"); ax.set_ylabel("Steady-state creep rate (s$^{-1}$)")\nax.set_title("Creep rate–stress support by study and condition")\nax.grid(True,which="both",alpha=.25); ax.legend(fontsize=6,ncol=2)\nfig.text(.01,.01,"Exact table rows; no cross-mechanism averaging. Independent papers=3; support=500–700 °C, 100–400 MPa.",fontsize=8)\nsave3(fig,root,"fig01_creep_rate_stress_loglog")\n'''
plot02='''from _common import *\nroot=get_root(); df=pd.read_csv(root/"figure_data/fig02_n_forest.csv")\ndf=df[pd.to_numeric(df["value"],errors="coerce").notna()].copy(); df["v"]=pd.to_numeric(df["value"])\ndf["label"]=df["paper_uid"]+" | "+df["sample_uid"]+" | "+df["temperature_C"].astype(str)+" C | "+df["basis"]\ndf=df.sort_values("v"); fig,ax=plt.subplots(figsize=(10,max(6,.28*len(df))))\ny=range(len(df)); ax.scatter(df["v"],list(y)); ax.set_yticks(list(y),df["label"],fontsize=6)\nax.axvline(3.5,linewidth=1,linestyle="--"); ax.axvline(5,linewidth=1,linestyle=":")\nax.set_xlabel("Stress exponent, n"); ax.set_title("Reported and recomputed stress exponents")\nax.grid(True,axis="x",alpha=.25); fig.text(.01,.01,"No pooled n: apparent, true threshold-corrected, and recomputed values are distinct estimands.",fontsize=8)\nsave3(fig,root,"fig02_n_forest")\n'''
plot03='''from _common import *\nimport re\nroot=get_root(); df=pd.read_csv(root/"figure_data/fig03_q_forest.csv")\nrows=[]\nfor _,r in df.iterrows():\n    txt=str(r["value"]); nums=[float(x) for x in re.findall(r"[0-9]+(?:\\.[0-9]+)?",txt)]\n    if not nums: continue\n    lo=min(nums); hi=max(nums); mid=(lo+hi)/2\n    rows.append((r,lo,hi,mid))\nrows=sorted(rows,key=lambda z:z[3]); fig,ax=plt.subplots(figsize=(10,max(6,.36*len(rows))))\nfor i,(r,lo,hi,mid) in enumerate(rows):\n    ax.errorbar(mid,i,xerr=[[mid-lo],[hi-mid]],fmt="o")\nlabels=[f"{r['paper_uid']} | {r['sample_uid']} | {r['basis']}" for r,_,_,_ in rows]\nax.set_yticks(range(len(rows)),labels,fontsize=6); ax.set_xlabel("Activation energy, Q (kJ mol$^{-1}$)")\nax.set_title("Activation-energy evidence forest"); ax.grid(True,axis="x",alpha=.25)\nfig.text(.01,.01,"Ranges are source-reported. Different stress definitions and mechanism regimes are not pooled.",fontsize=8)\nsave3(fig,root,"fig03_q_forest")\n'''
plot04='''from _common import *\nimport numpy as np\nroot=get_root(); df=pd.read_csv(root/"figure_data/fig04_rupture_support.csv")\nfig,ax=plt.subplots(figsize=(9,6))\nfor _,r in df.iterrows():\n    life=float(r["rupture_life_h"]); ax.scatter(float(r["stress_MPa"]),float(r["temperature_C"]),s=30+45*np.log10(1+life))\n    ax.annotate(f"{r['paper_uid']}\\n{r['sample_uid']}: {life:g} h",(float(r["stress_MPa"]),float(r["temperature_C"])),xytext=(4,4),textcoords="offset points",fontsize=7)\nax.set_xlabel("Applied stress (MPa)"); ax.set_ylabel("Temperature (°C)"); ax.set_title("Rupture-life support map — no interpolation")\nax.grid(True,alpha=.25); fig.text(.01,.01,"Only observed/explicitly derived rupture points. A contour surface, LMP and Monkman–Grant law are NOT_IDENTIFIABLE.",fontsize=8)\nsave3(fig,root,"fig04_rupture_support_no_interpolation")\n'''
plot05='''from _common import *\nimport re\nroot=get_root(); df=pd.read_csv(root/"figure_data/fig05_mechanism_regimes.csv")\nfig,ax=plt.subplots(figsize=(10,7))\nfor i,r in df.iterrows():\n    t=str(r["temperature_C"]); s=str(r["stress_MPa"]); tn=[float(x) for x in re.findall(r"[0-9]+(?:\\.[0-9]+)?",t)]; sn=[float(x) for x in re.findall(r"[0-9]+(?:\\.[0-9]+)?",s)]\n    if not tn or not sn: continue\n    x=sum(sn)/len(sn); y=sum(tn)/len(tn); ax.scatter(x,y,s=70); ax.annotate(f"{r['paper_uid']}\\n{r['mechanism']}",(x,y),xytext=(5,5),textcoords="offset points",fontsize=6,wrap=True)\nax.set_xlabel("Stress support midpoint (MPa)"); ax.set_ylabel("Temperature support midpoint (°C)"); ax.set_title("Mechanism-regime support map")\nax.grid(True,alpha=.25); fig.text(.01,.01,"Points mark evidence islands, not fitted regime boundaries. Cross-island universal n/Q is physically invalid.",fontsize=8)\nsave3(fig,root,"fig05_mechanism_regime_map")\n'''
plot06='''from _common import *\nroot=get_root(); df=pd.read_csv(root/"figure_data/fig06_creep_effect_forest.csv").sort_values("lnRR")\ndf["label"]=df["paper_uid"]+" | "+df["sample_uid_treatment"]+" | "+df["temperature_C"].astype(str)+" C/"+df["stress_MPa"].astype(str)+" MPa"\nfig,ax=plt.subplots(figsize=(10,max(7,.26*len(df))))\ny=range(len(df)); ax.scatter(df["lnRR"],list(y)); ax.axvline(0,linewidth=1)\nax.set_yticks(list(y),df["label"],fontsize=6); ax.set_xlabel("ln response ratio, ln(rate$_{TMC}$/rate$_{control}$)")\nax.set_title("Condition-specific creep-rate effects"); ax.grid(True,axis="x",alpha=.25)\nfig.text(.01,.01,f"Exact same-paper effects; independent papers={df.paper_uid.nunique()}, pairs={len(df)}. Negative values indicate lower rate.",fontsize=8)\nsave3(fig,root,"fig06_creep_effect_forest")\n'''
for name,code in [("plot_fig01.py",plot01),("plot_fig02.py",plot02),("plot_fig03.py",plot03),("plot_fig04.py",plot04),("plot_fig05.py",plot05),("plot_fig06.py",plot06)]:
    write_text("plot_code/"+name,code)
write_text("plot_code/reproduce_all.py",'''from pathlib import Path\nimport subprocess,sys\nroot=Path(__file__).resolve().parents[1]\nfor i in range(1,7):\n    subprocess.run([sys.executable,str(root/"plot_code"/f"plot_fig{i:02d}.py"),"--root",str(root)],check=True)\nprint("plots_generated=6 formats=SVG/PDF/PNG")\n''')
subprocess.run([sys.executable,str(OUT/"plot_code"/"reproduce_all.py")],check=True)

plot_specs=[]
for i,(stem,data,estimand,support) in enumerate([
("fig01_creep_rate_stress_loglog","fig01_creep_rate_stress.csv","steady creep rate vs applied stress","500-700 C; 100-400 MPa; exact table data"),
("fig02_n_forest","fig02_n_forest.csv","reported/recomputed stress exponent n","500-800 C; mechanism-stratified"),
("fig03_q_forest","fig03_q_forest.csv","activation energy Q","source-specific stress definitions"),
("fig04_rupture_support_no_interpolation","fig04_rupture_support.csv","observed rupture life support","600 C/200 MPa and 800 C/350 MPa; no interpolation"),
("fig05_mechanism_regime_map","fig05_mechanism_regimes.csv","mechanism evidence islands","500-800 C; 100-400 MPa"),
("fig06_creep_effect_forest","fig06_creep_effect_forest.csv","ln(rate_TMC/rate_control)","exact same-paper pairs"),
],1):
    plot_specs.append({"figure_id":f"FIG{i:02d}","stem":stem,"figure_data":"figure_data/"+data,"plot_code":f"plot_code/plot_fig{i:02d}.py","formats":["svg","pdf","png_600dpi"],"estimand":estimand,"support_domain":support,"claim_level":2})
write_json("PLOT_SPECS.json",plot_specs)

# -----------------------------------------------------------------------------
# Narrative and methods.
# -----------------------------------------------------------------------------
creep_exact=effect_df[effect_df.outcome=="steady_creep_rate_s-1"]
min_pct=float(creep_exact.percent_change.min()); max_pct=float(creep_exact.percent_change.max())
all_negative=bool((creep_exact.lnRR<0).all())
fer_ab=effect_df[(effect_df.paper_uid=="FEREIDUNI2021_LPBF_TIB_TI64") & (effect_df.heat_treatment=="none")]
fer_ht=effect_df[(effect_df.paper_uid=="FEREIDUNI2021_LPBF_TIB_TI64") & (effect_df.heat_treatment=="1050C_2h_furnace_cool")]
guor=rupture_df[rupture_df.paper_uid=="GUO2020_TIAL_Y2O3"].iloc[0]
verdict=f'''# QM14 rebuilt executive verdict

`WINDOW=QM14 | SNAPSHOT={SNAPSHOT_ID} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Supersession decision

The earlier `/mnt/data/FINAL_QM14.zip` is invalidated and must not be absorbed. It omitted the 2025 TiC/Ti-5556 thesis, underused the 7715D primary paper/thesis evidence, and asserted that quantitative support stopped at 700 °C. Direct same-paper TiAl/Y2O3 evidence exists at 800 °C. This rebuild corrects the cohort and preserves the narrower claim ceiling: **800 °C TiAl-specific evidence is not generic 800 °C titanium-service qualification**.

## Quantitative answer

1. **Steady creep rate:** {len(creep_exact)} exact same-paper condition effects were recovered from {creep_exact.paper_uid.nunique()} independent papers. All exact contrasts are negative (`all_negative={all_negative}`), but the condition-specific change spans **{min_pct:.1f}% to {max_pct:.1f}%**. The spread is not noise to be averaged away: it tracks matrix family, reinforcement system, heat treatment, temperature and stress.
2. **Processing interaction:** in LPBF Ti-6Al-4V, TiB changed rate/life from {float(fer_ab[fer_ab.outcome=='steady_creep_rate_s-1'].percent_change.iloc[0]):.1f}% / {float(fer_ab[fer_ab.outcome=='rupture_life_h'].percent_change.iloc[0]):.1f}% in the as-built state to {float(fer_ht[fer_ht.outcome=='steady_creep_rate_s-1'].percent_change.iloc[0]):.1f}% / {float(fer_ht[fer_ht.outcome=='rupture_life_h'].percent_change.iloc[0]):.1f}% after supertransus treatment. Lower rate therefore does **not** guarantee longer life.
3. **Stress exponent:** reinforcement does not impose one directional shift. Wang's threshold-corrected matrix/TMC data share true `n=3.5`; Xu reports `2.92→3.32`; Frontiers reports higher apparent n in the TMC; Guo reports `4.03→3.09` at 800 °C. A universal n would mix different stress definitions and mechanisms.
4. **Activation energy:** Wang's threshold correction collapses matrix and TMC to `Q=343 kJ/mol`; Ye's Q changes strongly with initial phase state and dose; Frontiers' matrix and TMC Q were evaluated at different stresses. No universal reinforcement delta-Q is identifiable.
5. **Rupture life:** exact/derived paired evidence is sparse and interaction-dominated. At 800 °C/350 MPa, Y2O3-bearing TiAl increased life from a source-text-derived 15 h to 77 h (`lnRR={float(guor.lnRR):.3f}`, {float(guor.percent_change):.1f}%). This is a Level-2 same-paper estimate, not a design allowables claim.

## Claim ceiling

Maximum claim level is **2: same-paper, condition-specific paired association**. A pooled causal coefficient, universal n/Q, stress-temperature rupture contour, Larson–Miller parameter, Monkman–Grant law, Gold promotion, production-model registration and `VALIDATED` formulation are forbidden with the present support.

## Terminal state

The rebuilt analysis is complete for the recovered evidence, but authoritative closure is blocked by the absent V29/Q40 atomic snapshot, original byte-level source hashes, replicate variances, censoring metadata and exact tables for several identified studies.
'''
write_text("00_EXECUTIVE_VERDICT.md",verdict)

write_text("SUPERSESSION_NOTICE.md",'''# Supersession notice

- Superseded artifact: `FINAL_QM14.zip`
- Previously reported SHA-256: `35bcb0c2bbdbafde0dea1bf16afb89a3dac3b4ba49b5e729547dd764486a8d56`
- Disposition: **INVALID FOR ABSORPTION**
- Causes: omitted primary evidence; false upper-temperature support statement; incomplete provenance/hash claims.
- Replacement: `FINAL_QM14_REBUILT.zip`
- The replacement does not self-promote to Gold or production status.
''')

write_text("METHODS.md",f'''# Methods

## Estimands

For a same-paper matched control/treatment pair and positive outcome `Y`:

- absolute effect: `Y_TMC - Y_control`
- log response ratio: `lnRR = ln(Y_TMC/Y_control)`
- percent change: `100*(exp(lnRR)-1)`

Creep rate uses negative lnRR as beneficial; rupture life uses positive lnRR as beneficial. No effect is averaged across temperature, stress, matrix state or test mode before the condition-specific estimate is retained.

## Atomicity and matching

Atomic row = paper × sample × actual/declared reinforcement × process × heat treatment × microstructure × test mode × temperature × stress × outcome. All numerical effects in `EFFECT_ESTIMATES.csv` are grade-A same-paper matches. Figure/abstract-only studies remain cohort or mechanism support and are not silently converted into numeric rows.

## Parameter fitting

Recomputed stress exponent is the OLS slope of `ln(creep rate)` against `ln(stress)` only within one paper/sample/temperature/heat-treatment block with at least three stress points. Reported apparent, true threshold-corrected and recomputed n are stored as different `basis` values. Reported Q values are never pooled when constant-stress definitions differ.

## Uncertainty

The source tables generally lack replicate variance. Pair-level confidence intervals are therefore marked `NOT_ESTIMABLE`, not fabricated. A deterministic, equal-paper-weight paper-cluster bootstrap (`seed={SEED}`, 10,000 resamples) summarizes observed heterogeneity; it is explicitly descriptive. LOPO and leave-family-out analyses stress-test sign dependence.

## Composition and dose

Ye's dose response is defined on Cr3C2 precursor wt.%, because actual TiC volume fraction is not reported. This cannot be interpreted as TiC efficiency per vol.%. Two-point dose series are marked non-identifiable for curvature.

## Rupture surface

The support contains disconnected points rather than a connected temperature–stress grid. The delivered rupture figure is a no-interpolation support map. Larson–Miller and Monkman–Grant fits are not performed.

## Software

Python 3.11; numpy/pandas/matplotlib exact pins in `requirements.lock`. Plot outputs are generated from delivered CSV files by delivered scripts. No LLM is required for recomputation.
''')
write_text("LIMITATIONS.md",'''# Limitations

1. The authoritative V29/Q40 atomic snapshot and byte-level source hashes were not available in the web-return runtime; this package uses a derived snapshot and identifier hashes only.
2. Most source tables do not report replicate-level uncertainty, preventing valid pair-level confidence intervals and a defensible random-effects meta-analysis.
3. Several studies are figure/abstract-indexed but lack authoritative exact creep tables in the current input surface; they are not digitized or guessed.
4. Rupture evidence is too sparse for Larson–Miller, Monkman–Grant or a stress–temperature contour.
5. Matrix families span alpha/beta Ti, near-alpha Ti, Ti-6Al-4V and TiAl. Their mechanisms and homologous temperatures differ; pooled n/Q has no physical meaning.
6. The Guo matrix rupture life is derived from a reported 62 h life extension relative to the 77 h TMC value and is isolated in sensitivity analysis.
7. Ye's reinforcement dose is precursor wt.% rather than verified TiC vol.%; dose efficiency is therefore precursor-specific.
''')

write_json("WEB_TO_LOCAL_REQUEST.json",{
    "window_id":"QM14","snapshot_id":SNAPSHOT_ID,"priority":"BLOCKING_AUTHORITATIVE_ABSORPTION",
    "requests":[
        {"id":"REQ01","required":"V29/Q40 ATOMIC_RECORDS, PROVENANCE, CONFLICT_LEDGER, EXCLUDED_RECORDS and paper/source registry","reason":"replace derived snapshot and bind canonical sample/condition IDs"},
        {"id":"REQ02","required":"byte-level SHA-256 for every consumed primary PDF/XML and package member path/CRC","reason":"satisfy source_hash contract"},
        {"id":"REQ03","required":"replicate-level creep rate/life, specimen count, SD/SE and censoring","reason":"valid uncertainty and hierarchical model"},
        {"id":"REQ04","required":"exact tables/curves for Materials Characterization 112067, MSEA 144279, Materials Characterization 111249 and associated supplements","reason":"close identified cohort gaps without figure guessing"},
        {"id":"REQ05","required":"raw time-strain series and rupture records across connected temperature-stress grid","reason":"LMP/MG and rupture-surface identifiability"},
        {"id":"REQ06","required":"independent digitization QA for Wang thesis Fig. 4-6 and Li thesis creep figures","reason":"promote figure evidence only after dual-reader validation"},
    ]
})
write_text("LOCAL_ABSORPTION_PROMPT.md",'''# Local absorption prompt

Reject the superseded `FINAL_QM14.zip`. Verify `FINAL_QM14_REBUILT.zip` with `CHECKSUMS.sha256`, ZIP CRC/testzip, schema/UID uniqueness and independent recalculation of every lnRR. Map derived paper/sample/condition IDs onto the authoritative V29/Q40 registry without overwriting conflicts. Attach original PDF/XML byte hashes and member provenance. Keep all current results at Claim Level 2 and do not promote to Gold, production models or VALIDATED formulations. Re-run after satisfying `WEB_TO_LOCAL_REQUEST.json`; only then consider authoritative snapshot promotion.
''')
write_text("acceptance_commands.md",'''# Acceptance commands

```bash
python -m pip install -r requirements.lock
python plot_code/reproduce_all.py
python tests/test_outputs.py .
sha256sum -c CHECKSUMS.sha256
python - <<'PY'
import zipfile
z=zipfile.ZipFile('../FINAL_QM14_REBUILT.zip')
assert z.testzip() is None
assert not any(n.lower().endswith(('.zip','.7z','.rar')) for n in z.namelist())
print('ZIP_PASS')
PY
```
''')
write_text("requirements.lock","matplotlib==3.10.3\nnumpy==2.2.6\npandas==2.2.3\npillow==11.2.1\n")

status={
    "window_id":"QM14","snapshot_id":SNAPSHOT_ID,"papers_seen":len(sources),"papers_included":len(sources),
    "independent_papers":len({s['paper_uid'] for s in sources}),"independent_program_families":len({s['paper_family_uid'] for s in sources}),
    "atomic_rows":len(curve_df),"matched_pairs":len(pair_df),"effect_estimates":len(effect_df),"plots_generated":6,
    "open_conflicts":sum(c['status'].startswith('OPEN') for c in conflicts),"claim_level_max":2,
    "status":"CONTINUE_DATA_GAP","next_action":"Authoritative V29/Q40 reconciliation, byte hashes, exact missing tables and replicate/censoring recovery",
}
write_json("WINDOW_STATUS.json",status)

# Test script.
test_script='''#!/usr/bin/env python3\nimport csv,hashlib,json,math,sys,zipfile\nfrom pathlib import Path\nroot=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()\nrequired=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','CREEP_CURVE_LEDGER.csv','CREEP_PARAMETERS.csv','RUPTURE_EFFECTS.csv','CREEP_MECHANISM_REGIMES.csv','SUPERSESSION_NOTICE.md']\nchecks=[]\ndef ok(name,cond):\n    checks.append((name,bool(cond))); assert cond,name\nok('required_files',all((root/x).exists() for x in required))\ndef readcsv(n):\n    with (root/n).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))\ncurves=readcsv('CREEP_CURVE_LEDGER.csv'); pairs=readcsv('PAIR_MATCHES.csv'); eff=readcsv('EFFECT_ESTIMATES.csv')\nok('atomic_uid_unique',len({r['record_uid'] for r in curves})==len(curves))\nok('pair_uid_unique',len({r['pair_uid'] for r in pairs})==len(pairs))\nok('effect_uid_unique',len({r['effect_uid'] for r in eff})==len(eff))\nok('effect_math',all(abs(float(r['lnRR'])-math.log(float(r['treatment_value'])/float(r['control_value'])))<1e-12 for r in eff))\ncreep=[r for r in eff if r['outcome']=='steady_creep_rate_s-1']\nok('creep_effects_condition_specific',len(creep)>=25 and all(float(r['lnRR'])<0 for r in creep))\nstatus=json.loads((root/'WINDOW_STATUS.json').read_text())\nok('status_legal',status['status']=='CONTINUE_DATA_GAP' and status['claim_level_max']==2)\nfor i in range(1,7):\n    stem=json.loads((root/'PLOT_SPECS.json').read_text())[i-1]['stem']\n    for ext in ['svg','pdf','png']:\n        p=root/'figures'/f'{stem}.{ext}'; ok(f'plot_{i}_{ext}',p.exists() and p.stat().st_size>1000)\nfor line in (root/'CHECKSUMS.sha256').read_text().splitlines():\n    h,name=line.split('  ',1); p=root/name; ok('sha_'+name,hashlib.sha256(p.read_bytes()).hexdigest()==h)\nok('no_nested_archive',not any(p.suffix.lower() in {'.zip','.7z','.rar'} for p in root.rglob('*') if p.is_file()))\nprint(json.dumps({'pass':True,'checks':len(checks)},indent=2))\n'''
write_text("tests/test_outputs.py",test_script)

# Validation report is deterministic and then covered by the manifest/checksums.
write_json("validation_report.json",{
    "pass":True,"planned_assertion_groups":10,"required_files":True,"atomic_uid_unique":True,"pair_effect_math":True,
    "plots":{"count":6,"formats":["SVG","PDF","PNG_600dpi"]},"no_nested_archives":True,"claim_level_max":2,
    "note":"Workflow executes tests/test_outputs.py after final checksums are written; workflow failure invalidates the artifact."
})

# Manifest excludes itself and checksum file to avoid recursive hashes.
manifest_files=[]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256"}:
        manifest_files.append({"path":p.relative_to(OUT).as_posix(),"bytes":p.stat().st_size,"sha256":sha256_file(p)})
manifest={"window_id":"QM14","snapshot_id":SNAPSHOT_ID,"status":"CONTINUE_DATA_GAP","claim_level_max":2,"file_count_excluding_manifest_and_checksums":len(manifest_files),"files":manifest_files,"acceptance":{"atomic_rows":len(curve_df),"matched_pairs":len(pair_df),"effect_estimates":len(effect_df),"independent_papers":len(sources),"plots":6,"nested_zip":False,"production_model_registration":False,"gold_promotion":False}}
write_json("MANIFEST.json",manifest)
checksum_lines=[]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name!="CHECKSUMS.sha256":
        checksum_lines.append(f"{sha256_file(p)}  {p.relative_to(OUT).as_posix()}")
write_text("CHECKSUMS.sha256","\n".join(checksum_lines))

# Execute acceptance tests after checksums are final.
proc=subprocess.run([sys.executable,str(OUT/"tests"/"test_outputs.py"),str(OUT)],check=True,capture_output=True,text=True)

# Package with no nested archives.
zip_path=ROOT/"output"/"FINAL_QM14_REBUILT.zip"
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(OUT.rglob("*")):
        if p.is_file(): z.write(p,p.relative_to(OUT).as_posix())
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert not any(n.lower().endswith((".zip",".7z",".rar")) for n in z.namelist())
zip_sha=sha256_file(zip_path)
summary={"window_id":"QM14","artifact":zip_path.name,"sha256":zip_sha,"bytes":zip_path.stat().st_size,"snapshot_id":SNAPSHOT_ID,"status":"CONTINUE_DATA_GAP","validation":"PASS","test_output":json.loads(proc.stdout),"independent_papers":len(sources),"atomic_rows":len(curve_df),"matched_pairs":len(pair_df),"effect_estimates":len(effect_df),"plots":6,"supersedes_sha256":"35bcb0c2bbdbafde0dea1bf16afb89a3dac3b4ba49b5e729547dd764486a8d56"}
(ROOT/"output"/"FINAL_QM14_REBUILT_SHA256.txt").write_text(zip_sha+"  FINAL_QM14_REBUILT.zip\n",encoding="utf-8")
(ROOT/"output"/"FINAL_QM14_REBUILT_DELIVERY_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for name in ["FINAL_QM14_REBUILT.zip","FINAL_QM14_REBUILT_SHA256.txt","FINAL_QM14_REBUILT_DELIVERY_SUMMARY.json"]:
    shutil.copy2(ROOT/"output"/name,ART/name)
print(json.dumps(summary,ensure_ascii=False,indent=2))
