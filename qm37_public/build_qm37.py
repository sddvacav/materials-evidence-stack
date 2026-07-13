#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import textwrap
import zipfile
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from data import (
    CLAIM_LEVEL_MAX, GENERATED_AT, KIM_Q, MAO, MATRIX_150, MISSING,
    NEXT_ACTION, PRIMARY_SOURCES, STATUS, TMC_150, TMC_75,
    TOP_LEVEL_INPUTS, WINDOW_ID, XIONG_PEAK,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def uid(*parts: Any) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:20]


def snapshot_id() -> str:
    payload = "\n".join(x[1] for x in TOP_LEVEL_INPUTS) + "\n" + "\n".join(s["source_hash"] for s in PRIMARY_SOURCES)
    return "RECOVERY_QM37_" + sha256_bytes(payload.encode("utf-8"))[:16]


def write_text(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def write_json(root: Path, rel: str, obj: Any) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(root: Path, rel: str, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    if not fields:
        fields = ["status", "reason"]
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def build_input_ledger(root: Path, snap: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, source_hash, hash_kind, nbytes, members, priority, use in TOP_LEVEL_INPUTS:
        rows.append({
            "input_id": uid(name, source_hash), "snapshot_id": snap, "source_name": name,
            "source_type": "ZIP", "path_or_locator": f"/mnt/data/{name}", "source_hash": source_hash,
            "source_hash_kind": hash_kind, "bytes": nbytes, "member_count": members,
            "central_directory_status": "READABLE_PRIOR_AUDIT", "priority": priority,
            "window_relevance": "Registered project-source package; source-family relevance assessed for QM37.",
            "terminal_use_status": use, "opened_or_consumed": "YES",
            "notes": "Top-level package registered; direct raw-member reparse is not falsely claimed.",
        })
    extras = [
        ("QM37_高温软化、动态回复、界面稳定、蠕变和氧化机制转变.md", "MDU", "file_00000000cbe471f8ace3a39a5f672219", "P0_CONTRACT", "USED_DIRECTLY", "Execution contract."),
        ("V29X XML Corpus Audit Report", "REPORT", "V29X_AUDIT_78683_XML", "P1_PROVENANCED_STRUCTURED", "USED_DIRECTLY", "78,683 XML / 24.1845 GiB inventory and scope-firewall facts."),
        ("QM12 high-temperature tensile return", "REPORT", "QM12_DERIVED_ab795b646d964e6a", "P4_DERIVED_REPORT", "USED_AS_REFERENCE", "650-700 C paired context; not used to invent 800 C values."),
        ("QM14 creep return", "REPORT", "RECOVERY_QM14_d49880d078e4ad9f", "P4_DERIVED_REPORT", "USED_AS_REFERENCE", "650-700 C creep evidence and no-800-C boundary."),
        ("QM32 load-transfer return", "REPORT", "QM32_READONLY_RETURN", "P4_DERIVED_REPORT", "USED_AS_REFERENCE", "Aspect-ratio/orientation/interface dependence."),
    ]
    for name, typ, sh, priority, use, note in extras:
        rows.append({
            "input_id": uid(name, sh), "snapshot_id": snap, "source_name": name,
            "source_type": typ, "path_or_locator": name, "source_hash": sh,
            "source_hash_kind": "DERIVED_OR_CHAT_ID", "bytes": "", "member_count": 1,
            "central_directory_status": "", "priority": priority, "window_relevance": note,
            "terminal_use_status": use, "opened_or_consumed": "YES", "notes": note,
        })
    for source in PRIMARY_SOURCES:
        rows.append({
            "input_id": uid(source["paper_uid"], source["source_hash"]), "snapshot_id": snap,
            "source_name": source["title"], "source_type": "PRIMARY_SOURCE_CAPTURE",
            "path_or_locator": source["source_locator"], "source_hash": source["source_hash"],
            "source_hash_kind": "CHAT_FILE_ID_OR_NORMALIZED_CAPTURE_SHA256", "bytes": "", "member_count": 1,
            "central_directory_status": "", "priority": "P0_PRIMARY_ORIGINAL",
            "window_relevance": "Direct high-temperature mechanism/property evidence.",
            "terminal_use_status": "USED_DIRECTLY", "opened_or_consumed": "YES", "notes": source["notes"],
        })
    write_csv(root, "INPUT_LEDGER.csv", rows)
    write_csv(root, "SOURCE_EVIDENCE_REGISTER.csv", PRIMARY_SOURCES)
    return rows


def cohort_record(snap: str, paper: str, sample: str, condition: str, matrix: str, reinforcement: str,
                  dose: Any, process: str, test_mode: str, temp: Any, strain_rate: Any, environment: str,
                  prop: str, value: Any, unit: str, evidence: str, locator: str, source_hash: str,
                  include: str = "YES", notes: str = "", time_h: Any = "", stress_mpa: Any = "") -> dict[str, Any]:
    return {
        "record_uid": uid(snap, paper, sample, condition, prop), "snapshot_id": snap,
        "paper_uid": paper, "sample_uid": sample, "condition_uid": condition,
        "matrix_family": matrix, "reinforcement_type": reinforcement, "reinforcement_vol_pct": dose,
        "process": process, "heat_treatment": "as_reported", "test_mode": test_mode,
        "temperature_c": temp, "time_h": time_h, "stress_mpa": stress_mpa,
        "strain_rate_s-1": strain_rate, "orientation": "as_reported_or_missing",
        "environment": environment, "property": prop, "value": value, "unit": unit,
        "evidence_level": evidence, "source_locator": locator, "source_hash": source_hash,
        "include_primary": include, "notes": notes,
    }


def build_cohort(root: Path, snap: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sh = PRIMARY_SOURCES[0]["source_hash"]
    for temp, value in MATRIX_150.items():
        rows.append(cohort_record(snap, "P_INT_XIONG_2022_PPT", "Ti65_150_250", f"TENSILE_{temp}C", "Ti65", "none", 0.0,
                                  "low-energy ball milling + hot-press sintering", "tension", temp, "missing", "missing",
                                  "UTS", value, "MPa", "DIRECT_SLIDE_TABLE", "slides 29-30", sh,
                                  notes="Short-term high-temperature tensile; no dispersion."))
    for dose, values in TMC_150.items():
        for temp, value in values.items():
            rows.append(cohort_record(snap, "P_INT_XIONG_2022_PPT", f"TiBw{dose}_150_250", f"TENSILE_{temp}C", "Ti65", "TiBw", dose,
                                      "low-energy ball milling + hot-press sintering", "tension", temp, "missing", "missing",
                                      "UTS", value, "MPa", "DIRECT_SLIDE_TABLE", "slide 29", sh,
                                      notes="Same powder-size family; 5.1 vol.% shows interface aggregation."))
    for dose, values in TMC_75.items():
        for temp, value in values.items():
            rows.append(cohort_record(snap, "P_INT_XIONG_2022_PPT", f"TiBw{dose}_75_150", f"TENSILE_{temp}C", "Ti65", "TiBw", dose,
                                      "low-energy ball milling + hot-press sintering", "tension", temp, "missing", "missing",
                                      "UTS", value, "MPa", "DIRECT_SLIDE_TABLE", "slide 30", sh, include="DESCRIPTIVE_ONLY",
                                      notes="No exact same-size matrix control."))
    sh = PRIMARY_SOURCES[1]["source_hash"]
    for condition, by_temp in MAO.items():
        for temp, values in by_temp.items():
            for prop, value in values.items():
                rows.append(cohort_record(snap, "P_MAO_2013", f"MAO_{condition}", f"{condition}_{temp}C", "IMI834-like near-alpha Ti",
                                          "1.82% TiBw + 0.58% La2O3", 1.82,
                                          "VAR+forging+rolling+650C/2h anneal; GTAW for Gxx", "tension", temp,
                                          "crosshead=0.4mm/s", "argon-welded; test atmosphere missing", prop, value,
                                          "MPa" if prop == "UTS" else "%", "DIRECT_TABLE_TEXT", "Table 2", sh,
                                          notes="Average of three measurements; G00 base metal, Gxx welded joints."))
    sh = PRIMARY_SOURCES[2]["source_hash"]
    for temp, by_rate in XIONG_PEAK.items():
        for rate, value in by_rate.items():
            rows.append(cohort_record(snap, "P_XIONG_2024", "TiBw3.4_Ti65", f"COMP_{temp}C_{rate}s", "Ti65", "TiBw", 3.4,
                                      "low-energy ball milling + 1300C/2h/25MPa hot press", "compression", temp, rate,
                                      "vacuum<1e-2Pa", "peak_flow_stress", value, "MPa", "DIRECT_TABLE_TEXT", "Table 1", sh,
                                      notes="True strain 0.8; 3-min hold; water quenched."))
    sh = PRIMARY_SOURCES[3]["source_hash"]
    for dose, q in KIM_Q.items():
        rows.append(cohort_record(snap, "P_KIM_2019", f"TiB_TiC_{dose}vol", "OX_800_1000C", "commercially pure Ti", "TiB+TiC", dose,
                                  "melting-investment casting from Ti+B4C", "oxidation", "800-1000", "", "air",
                                  "apparent_oxidation_activation_energy", q, "kJ/mol", "DIRECT_TEXT_DERIVED_FIT",
                                  "oxidation kinetics section", sh, notes="Apparent Arrhenius value; curves not uniformly parabolic."))
    rows.append(cohort_record(snap, "P_KIM_2019", "TiB_TiC_composite", "OX_800C_70h", "commercially pure Ti", "TiB+TiC", "5-20",
                              "melting-investment casting from Ti+B4C", "oxidation", 800, "", "air",
                              "oxide_scale_thickness", 10.0, "um", "FIGURE_DERIVED_TEXT_SUPPORTED", "800C/70h cross-section", sh,
                              notes="Approximate porous scale thickness; not pooled with mechanical effects.", time_h=70))
    write_csv(root, "ANALYSIS_COHORT.csv", rows)
    return rows


def build_pairs_effects(root: Path, snap: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pairs: list[dict[str, Any]] = []
    effects: list[dict[str, Any]] = []

    def add_pair(paper: str, treated_sample: str, control_sample: str, condition: str, grade: str,
                 prop: str, temp: Any, treated: float, control: float, unit: str, evidence: str,
                 notes: str, independent_papers: int, dose: Any, estimand: str, locator: str,
                 source_hash: str, support: str, status: str) -> None:
        pair_id = uid("PAIR", paper, treated_sample, control_sample, condition, prop)
        pairs.append({
            "pair_uid": pair_id, "snapshot_id": snap, "paper_uid": paper,
            "treated_sample_uid": treated_sample, "control_sample_uid": control_sample,
            "condition_uid": condition, "match_grade": grade, "property": prop, "temperature_c": temp,
            "treated_value": treated, "control_value": control, "unit": unit,
            "identification_level": 2, "evidence_level": evidence, "admission_status": "INCLUDED", "notes": notes,
        })
        delta = treated - control
        lnrr = math.log(treated / control) if treated > 0 and control > 0 else ""
        effects.append({
            "effect_uid": uid(pair_id, prop), "pair_uid": pair_id, "snapshot_id": snap,
            "paper_uid": paper, "sample_uid": treated_sample, "condition_uid": condition,
            "estimand": estimand, "property": prop, "temperature_c": temp, "reinforcement_vol_pct": dose,
            "delta": round(delta, 6), "lnRR": round(lnrr, 9) if isinstance(lnrr, float) else "",
            "percent_change": round(100.0 * (treated / control - 1.0), 6) if control else "",
            "unit_content_efficiency": round(delta / dose, 6) if isinstance(dose, (int, float)) and dose else "",
            "efficiency_unit": "per_vol_pct" if isinstance(dose, (int, float)) and dose else "",
            "control_retention_vs_600": "", "tmc_retention_vs_600": "",
            "ci95_low": "", "ci95_high": "", "prediction_interval_low": "", "prediction_interval_high": "",
            "independent_papers": independent_papers, "claim_level": 2, "evidence_level": evidence,
            "support_domain": support, "source_locator": locator, "source_hash": source_hash,
            "status": status, "notes": notes + " No raw uncertainty was invented.",
        })

    for dose, values in TMC_150.items():
        for temp, treated in values.items():
            add_pair("P_INT_XIONG_2022_PPT", f"TiBw{dose}_150_250", "Ti65_150_250", f"TENSILE_{temp}C",
                     "A_SAME_WORK_SAME_SIZE_ROUTE_CONDITION", "UTS", temp, treated, MATRIX_150[temp], "MPa",
                     "DIRECT_SLIDE_TABLE", "Positive absolute effect does not imply long-duration service retention.",
                     0, dose, "same-work TiBw-vs-Ti65 UTS effect", "slides 23,29", PRIMARY_SOURCES[0]["source_hash"],
                     "Ti65; 150-250um network; hot-press; 600-800C; short-term tension", "ESTIMABLE_NO_DISPERSION")
            effects[-1]["control_retention_vs_600"] = round(MATRIX_150[temp] / MATRIX_150[600], 9)
            effects[-1]["tmc_retention_vs_600"] = round(treated / TMC_150[dose][600], 9)
            effects[-1]["efficiency_unit"] = "MPa_per_vol_pct"
    for condition in ["G81", "G82", "G83", "G93", "G113", "G134"]:
        for temp in [600, 650]:
            for prop in ["UTS", "EL"]:
                add_pair("P_MAO_2013", f"MAO_{condition}", "MAO_G00", f"{temp}C",
                         "B_SAME_PAPER_WELD_ARCHITECTURE_VS_BASE", prop, temp,
                         MAO[condition][temp][prop], MAO["G00"][temp][prop], "MPa" if prop == "UTS" else "%",
                         "DIRECT_TABLE_TEXT", "Architecture-preservation effect, not a pure reinforcement effect.",
                         1, 1.82, "same-paper welded-joint vs base-metal architecture effect", "Mao 2013 Table 2",
                         PRIMARY_SOURCES[1]["source_hash"], "Mao 2013 welded near-alpha TMC; 600-650C",
                         "ESTIMABLE_DESCRIPTIVE")
                effects[-1]["unit_content_efficiency"] = ""
                effects[-1]["efficiency_unit"] = ""
    for dose in [5.0, 10.0, 20.0]:
        add_pair("P_KIM_2019", f"TiB_TiC_{dose}vol", "TiB_TiC_0vol", "OXIDATION_800_1000_AIR",
                 "A_SAME_PAPER_DOSE_SERIES", "apparent_oxidation_activation_energy", "800-1000",
                 KIM_Q[dose], KIM_Q[0.0], "kJ/mol", "DIRECT_TEXT_DERIVED_FIT",
                 "Higher apparent Q coexists with semi-protective/nonprotective oxidation; not qualification.",
                 1, dose, "same-paper reinforcement-dose change in apparent oxidation activation energy",
                 "Kim 2019 oxidation kinetics", PRIMARY_SOURCES[3]["source_hash"],
                 "CP-Ti/(TiB+TiC); air; 800-1000C", "ESTIMABLE_DESCRIPTIVE")
        effects[-1]["efficiency_unit"] = "kJ_mol-1_per_vol_pct"
    write_csv(root, "PAIR_MATCHES.csv", pairs)
    write_csv(root, "EFFECT_ESTIMATES.csv", effects)
    return pairs, effects


def build_mechanism_states(root: Path, snap: str) -> tuple[list[dict[str, Any]], dict[int, float]]:
    rows: list[dict[str, Any]] = []

    def add(paper: str, sample: str, condition: str, tlo: Any, thi: Any, rate: Any, env: str,
            mechanism: str, probability_type: str, evidence: str, basis: str,
            status: str = "DIRECT_STATE_LABEL", time_h: Any = "", support: Any = "") -> None:
        rows.append({
            "state_uid": uid(paper, sample, condition, mechanism), "snapshot_id": snap,
            "paper_uid": paper, "sample_uid": sample, "condition_uid": condition,
            "temperature_low_c": tlo, "temperature_high_c": thi, "time_h": time_h,
            "stress_mpa": "", "strain_rate_s-1": rate, "environment": env,
            "mechanism_state": mechanism, "dominance_probability": "",
            "probability_type": probability_type, "state_support_index": support,
            "evidence_level": evidence, "claim_level": 1 if evidence == "UNRESOLVED" else 2,
            "status": status, "basis": basis,
        })

    add("P_MAO_2013", "welded_near_alpha_TMC", "TENSION_600C", 600, 600, "crosshead=0.4mm/s", "test atmosphere missing",
        "TiBw fracture + ductile matrix voiding", "REPORTED_DOMINANT_STATE_NOT_FREQUENCY", "DIRECT_TEXT_FRACTOGRAPHY",
        "Cracked TiBw and matrix voids; interface remains load-bearing at 600 C.")
    add("P_MAO_2013", "welded_near_alpha_TMC", "TENSION_650C", 650, 650, "crosshead=0.4mm/s", "test atmosphere missing",
        "interface decohesion + void coalescence", "REPORTED_DOMINANT_STATE_NOT_FREQUENCY", "DIRECT_TEXT_FRACTOGRAPHY",
        "Matrix softening, dislocation climb/DRV and reduced interface strength; debonding dominates at 650 C.")
    for temp in [1040, 1060, 1080, 1100]:
        add("P_XIONG_2024", "TiBw3.4_Ti65", f"HOTCOMP_{temp}_HIGH_RATE", temp, temp, "1-0.1", "vacuum<1e-2Pa",
            "dynamic recrystallization (CDRX + DDRX)", "REPORTED_DOMINANT_STATE_NOT_FREQUENCY", "DIRECT_TEXT_EBSD",
            "High-rate softening; EBSD shows CDRX and interface necklace-like DDRX.")
        add("P_XIONG_2024", "TiBw3.4_Ti65", f"HOTCOMP_{temp}_LOW_RATE", temp, temp, "0.01-0.001", "vacuum<1e-2Pa",
            "dynamic recovery", "REPORTED_DOMINANT_STATE_NOT_FREQUENCY", "DIRECT_TEXT_CURVE",
            "Low-rate near-steady flow; DRV predominates.")
    add("P_XIONG_2024", "TiBw3.4_Ti65", "HOTCOMP_INSTABILITY", 1070, 1100, 0.001, "vacuum<1e-2Pa",
        "excessive beta-grain growth / processing instability", "REPORTED_INSTABILITY_DOMAIN", "DIRECT_PROCESSING_MAP",
        "Instability domain at high temperature and lowest strain rate.")
    add("P_SUN_2020", "TiBw_near_alpha", "HOTCOMP_850_900_HIGH_RATE", 850, 900, "0.1-0.5", "as reported",
        "interface debonding, TiB fragmentation and flow localization", "REPORTED_INSTABILITY_DOMAIN", "DIRECT_TEXT_FIGURE",
        "Low-temperature/high-rate instability.")
    add("P_SUN_2020", "TiBw_near_alpha", "HOTCOMP_900_0.01", 900, 900, 0.01, "as reported",
        "dynamic recrystallization", "REPORTED_DOMINANT_STATE_NOT_FREQUENCY", "DIRECT_TEXT_FIGURE",
        "Approximately 70% equiaxed alpha_p and ~3.1 um grains.")
    add("P_SUN_2020", "TiBw_near_alpha", "HOTCOMP_950_0.1", 950, 950, 0.1, "as reported",
        "dynamic recovery / incomplete recrystallization", "REPORTED_DOMINANT_STATE_NOT_FREQUENCY", "DIRECT_TEXT_FIGURE",
        "Lower recrystallized fraction; DRX-to-DRV transition.")
    for temp in [800, 900, 1000]:
        add("P_KIM_2019", "CP_Ti_TiB_TiC", f"OX_AIR_{temp}", temp, temp, "", "air",
            "semi-protective Ti oxide growth + volatile B2O3/CO2", "REPORTED_ACTIVE_STATE_NOT_FREQUENCY", "DIRECT_TEXT_SCALE",
            "Reinforcement thins scales/improves adherence but does not create a fully protective scale.")
    wei_states = {
        600: "continuous protective scale; nearly parabolic oxidation",
        700: "partially damaged scale; quasi-linear oxidation",
        800: "complete scale spallation; linear oxidation",
    }
    for temp, mechanism in wei_states.items():
        add("P_WEI_2017", "Ti64_TiC_TiB_hybrid", f"CYCLIC_OX_{temp}C_100H", temp, temp, "", "air",
            mechanism, "REPORTED_STATE_NOT_CALIBRATED", "DIRECT_TEXT_SCALE_TRANSITION",
            "Reported 873/973/1073 K state sequence; no numerical mechanism probability.", time_h=100)
    mean_delta = {t: statistics.mean(TMC_150[d][t] - MATRIX_150[t] for d in TMC_150) for t in [600, 700, 800]}
    for temp in [600, 700, 800]:
        add("P_INT_XIONG_2022_PPT", "TiBw_Ti65_150_250", f"TENSILE_{temp}", temp, temp, "missing", "missing",
            "net reinforcement contribution retained", "NOT_IDENTIFIABLE", "DIRECT_SLIDE_TABLE_DERIVED_PROXY",
            "Mean same-source delta UTS normalized to the 600 C increment; support index only.",
            status="PROXY_ONLY_DOMINANCE_PROBABILITY_NOT_IDENTIFIABLE", support=round(mean_delta[temp] / mean_delta[600], 6))
    add("P_XU_2023", "TMC1_TMC2", "CREEP_650", 650, 650, "", "as reported",
        "dynamic recovery balanced by work hardening; silicide/interface pinning",
        "REPORTED_MECHANISM_STATE_NOT_FREQUENCY", "NORMALIZED_PRIMARY_CAPTURE",
        "TMC2 reduced steady creep rate by 5.7-33.6%; life evidence censored and condition-specific.")
    write_csv(root, "HIGHTEMP_MECHANISM_STATES.csv", rows)
    return rows, mean_delta


def build_decay_changepoints(root: Path, snap: str, mean_delta: dict[int, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decay: list[dict[str, Any]] = []
    for dose, values in TMC_150.items():
        d600 = values[600] - MATRIX_150[600]
        d700 = values[700] - MATRIX_150[700]
        d800 = values[800] - MATRIX_150[800]
        rate = math.log(d800 / d600) / 200.0 if d800 > 0 else ""
        decay.append({
            "decay_uid": uid("DECAY", dose), "snapshot_id": snap, "paper_uid": "P_INT_XIONG_2022_PPT",
            "sample_uid": f"TiBw{dose}_150_250", "condition_domain": "short-term tension; 600-800C",
            "reinforcement_vol_pct": dose, "effect_600_mpa": d600, "effect_700_mpa": d700, "effect_800_mpa": d800,
            "retained_fraction_700_vs_600": round(d700 / d600, 9),
            "retained_fraction_800_vs_600": round(d800 / d600, 9),
            "absolute_slope_600_800_mpa_per_c": round((d800 - d600) / 200.0, 9),
            "piecewise_slope_600_700": round((d700 - d600) / 100.0, 9),
            "piecewise_slope_700_800": round((d800 - d700) / 100.0, 9),
            "log_decay_rate_per_c": round(rate, 9) if isinstance(rate, float) else "",
            "empirical_half_decay_temperature_increment_c": round(math.log(2.0) / (-rate), 6) if isinstance(rate, float) and rate < 0 else "",
            "uncertainty": "NOT_ESTIMABLE_NO_DISPERSION", "evidence_level": "DIRECT_SLIDE_TABLE_DERIVED_CALCULATION",
            "claim_level": 2, "status": "ESTIMABLE_WITHIN_SOURCE",
            "notes": "Interpolation diagnostic, not universal constant.",
        })
    rate = math.log(mean_delta[800] / mean_delta[600]) / 200.0
    decay.append({
        "decay_uid": uid("DECAY_MEAN"), "snapshot_id": snap, "paper_uid": "P_INT_XIONG_2022_PPT",
        "sample_uid": "dose_balanced_mean", "condition_domain": "short-term tension; 600-800C",
        "reinforcement_vol_pct": "1.7,3.4,5.1 balanced", "effect_600_mpa": round(mean_delta[600], 6),
        "effect_700_mpa": round(mean_delta[700], 6), "effect_800_mpa": round(mean_delta[800], 6),
        "retained_fraction_700_vs_600": round(mean_delta[700] / mean_delta[600], 9),
        "retained_fraction_800_vs_600": round(mean_delta[800] / mean_delta[600], 9),
        "absolute_slope_600_800_mpa_per_c": round((mean_delta[800] - mean_delta[600]) / 200.0, 9),
        "piecewise_slope_600_700": round((mean_delta[700] - mean_delta[600]) / 100.0, 9),
        "piecewise_slope_700_800": round((mean_delta[800] - mean_delta[700]) / 100.0, 9),
        "log_decay_rate_per_c": round(rate, 9),
        "empirical_half_decay_temperature_increment_c": round(math.log(2.0) / (-rate), 6),
        "uncertainty": "NOT_ESTIMABLE_ONE_SOURCE", "evidence_level": "DIRECT_SLIDE_TABLE_DERIVED_CALCULATION",
        "claim_level": 2, "status": "DESCRIPTIVE_DOSE_BALANCED",
        "notes": "Mean effect falls 83.6% from 600 to 800 C.",
    })
    for condition in ["G81", "G82", "G83", "G93", "G113", "G134"]:
        u600, u650 = MAO[condition][600]["UTS"], MAO[condition][650]["UTS"]
        decay.append({
            "decay_uid": uid("MAO_DECAY", condition), "snapshot_id": snap, "paper_uid": "P_MAO_2013",
            "sample_uid": condition, "condition_domain": "welded-joint UTS; 600-650C", "reinforcement_vol_pct": 1.82,
            "effect_600_mpa": u600, "effect_700_mpa": "", "effect_800_mpa": u650,
            "retained_fraction_700_vs_600": "", "retained_fraction_800_vs_600": round(u650 / u600, 9),
            "absolute_slope_600_800_mpa_per_c": round((u650 - u600) / 50.0, 9),
            "piecewise_slope_600_700": "", "piecewise_slope_700_800": "",
            "log_decay_rate_per_c": round(math.log(u650 / u600) / 50.0, 9),
            "empirical_half_decay_temperature_increment_c": "", "uncertainty": "REPORTED_AVERAGES_N3",
            "evidence_level": "DIRECT_TABLE_TEXT_DERIVED_CALCULATION", "claim_level": 2,
            "status": "ARCHITECTURE_RETENTION_NOT_REINFORCEMENT_EFFECT",
            "notes": "650 C is stored in effect_800_mpa only because schema is shared; condition_domain is authoritative.",
        })
    changepoints = [
        {"changepoint_uid": uid("CP_MAO"), "snapshot_id": snap, "paper_uid": "P_MAO_2013", "axis": "temperature_c", "mechanism_from": "TiBw fracture + matrix voiding", "mechanism_to": "interface decohesion + void coalescence", "lower_bound": 600, "upper_bound": 650, "candidate": 625, "interval_type": "DIRECT_BRACKET", "condition_domain": "GTAW near-alpha TMC; crosshead 0.4 mm/s", "evidence_level": "DIRECT_TEXT_FRACTOGRAPHY", "identifiability": "IDENTIFIED_WITHIN_SOURCE", "claim_level": 2, "notes": "Cannot generalize across materials or environments."},
        {"changepoint_uid": uid("CP_INT_DECAY"), "snapshot_id": snap, "paper_uid": "P_INT_XIONG_2022_PPT", "axis": "temperature_c", "mechanism_from": "substantial net strengthening", "mechanism_to": "near-null/saturated net strengthening", "lower_bound": 600, "upper_bound": 800, "candidate": 700, "interval_type": "THREE_POINT_WEAK_CHANGEPOINT", "condition_domain": "TiBw/Ti65; short-term tension", "evidence_level": "DIRECT_SLIDE_TABLE_DERIVED", "identifiability": "WEAKLY_IDENTIFIED", "claim_level": 2, "notes": "Only three temperatures and one family."},
        {"changepoint_uid": uid("CP_XIONG_RATE"), "snapshot_id": snap, "paper_uid": "P_XIONG_2024", "axis": "log10_strain_rate_s-1", "mechanism_from": "dynamic recovery", "mechanism_to": "dynamic recrystallization", "lower_bound": -2, "upper_bound": -1, "candidate": -1.5, "interval_type": "DIRECT_RATE_BRACKET", "condition_domain": "1040-1100C beta region; vacuum", "evidence_level": "DIRECT_TEXT_CURVE_EBSD", "identifiability": "IDENTIFIED_WITHIN_SOURCE", "claim_level": 2, "notes": "Processing mechanism, not 800 C service."},
        {"changepoint_uid": uid("CP_XIONG_GROWTH"), "snapshot_id": snap, "paper_uid": "P_XIONG_2024", "axis": "temperature_c", "mechanism_from": "stable hot working", "mechanism_to": "excessive beta-grain growth instability", "lower_bound": 1070, "upper_bound": 1100, "candidate": 1085, "interval_type": "PROCESSING_MAP_DOMAIN", "condition_domain": "0.001 s-1", "evidence_level": "DIRECT_PROCESSING_MAP", "identifiability": "IDENTIFIED_DOMAIN", "claim_level": 2, "notes": "Processing only."},
        {"changepoint_uid": uid("CP_SUN_INSTABILITY"), "snapshot_id": snap, "paper_uid": "P_SUN_2020", "axis": "temperature_c", "mechanism_from": "stable deformation", "mechanism_to": "interface debonding/TiB fragmentation/localization", "lower_bound": 850, "upper_bound": 900, "candidate": 875, "interval_type": "PROCESSING_MAP_DOMAIN", "condition_domain": "0.1-0.5 s-1", "evidence_level": "DIRECT_TEXT_FIGURE", "identifiability": "IDENTIFIED_DOMAIN", "claim_level": 2, "notes": "Condition-coupled with strain rate."},
        {"changepoint_uid": uid("CP_KIM_OX"), "snapshot_id": snap, "paper_uid": "P_KIM_2019", "axis": "temperature_c", "mechanism_from": "unobserved lower-temperature oxidation regime", "mechanism_to": "active semi-protective oxidation", "lower_bound": "", "upper_bound": 800, "candidate": "", "interval_type": "LEFT_CENSORED_ONSET", "condition_domain": "CP-Ti/(TiB+TiC) in air", "evidence_level": "DIRECT_TEXT_SCALE", "identifiability": "THRESHOLD_NOT_IDENTIFIABLE", "claim_level": 2, "notes": "800 C is lowest studied, not onset."},
        {"changepoint_uid": uid("CP_WEI_1"), "snapshot_id": snap, "paper_uid": "P_WEI_2017", "axis": "temperature_c", "mechanism_from": "continuous protective scale; nearly parabolic", "mechanism_to": "partially damaged scale; quasi-linear", "lower_bound": 600, "upper_bound": 700, "candidate": "", "interval_type": "REPORTED_STATE_BRACKET", "condition_domain": "hybrid TiC+TiB/Ti64; 100 h cyclic air oxidation", "evidence_level": "DIRECT_TEXT_SCALE_TRANSITION", "identifiability": "BRACKET_ONLY", "claim_level": 2, "notes": "State bracket, not exact kinetic changepoint."},
        {"changepoint_uid": uid("CP_WEI_2"), "snapshot_id": snap, "paper_uid": "P_WEI_2017", "axis": "temperature_c", "mechanism_from": "partially damaged scale; quasi-linear", "mechanism_to": "complete spallation; linear", "lower_bound": 700, "upper_bound": 800, "candidate": "", "interval_type": "REPORTED_STATE_BRACKET", "condition_domain": "hybrid TiC+TiB/Ti64; 100 h cyclic air oxidation", "evidence_level": "DIRECT_TEXT_SCALE_TRANSITION", "identifiability": "BRACKET_ONLY", "claim_level": 2, "notes": "State bracket, not exact kinetic changepoint."},
        {"changepoint_uid": uid("CP_CREEP_800"), "snapshot_id": snap, "paper_uid": "P_XU_2023", "axis": "temperature_c", "mechanism_from": "650C creep evidence", "mechanism_to": "800C long-duration controlling mechanism", "lower_bound": 650, "upper_bound": 800, "candidate": "", "interval_type": "DATA_GAP", "condition_domain": "stress/time/environment dependent", "evidence_level": "UNRESOLVED", "identifiability": "NOT_IDENTIFIABLE", "claim_level": 1, "notes": "No direct 800 C long-duration creep dataset."},
    ]
    write_csv(root, "MECHANISM_DECAY_RATES.csv", decay)
    write_csv(root, "MECHANISM_CHANGEPOINTS.csv", changepoints)
    return decay, changepoints


def build_other_tables(root: Path, snap: str, mean_delta: dict[int, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hierarchical = []
    for temp in [600, 700, 800]:
        hierarchical.append({
            "result_uid": uid("HIER", temp), "snapshot_id": snap,
            "estimand": "dose-balanced same-source mean delta UTS", "temperature_c": temp,
            "estimate": round(mean_delta[temp], 6), "ci95_low": "", "ci95_high": "",
            "prediction_interval_low": "", "prediction_interval_high": "", "independent_papers": 0,
            "experimental_families": 1, "model": "equal-dose descriptive mean",
            "cluster_unit": "single internal family", "status": "NO_HIERARCHICAL_INFERENCE",
            "claim_level": 2, "notes": "Random effects and prediction intervals are not identifiable.",
        })
    hierarchical.append({
        "result_uid": uid("HIER_800_CROSSPAPER"), "snapshot_id": snap,
        "estimand": "cross-paper 800 C strengthening effect", "temperature_c": 800,
        "estimate": "", "ci95_low": "", "ci95_high": "", "prediction_interval_low": "",
        "prediction_interval_high": "", "independent_papers": 0, "experimental_families": 1,
        "model": "not fit", "cluster_unit": "paper", "status": "NOT_IDENTIFIABLE", "claim_level": 1,
        "notes": "No independent matched 800 C mechanical families.",
    })
    write_csv(root, "HIERARCHICAL_RESULTS.csv", hierarchical)

    dose_rows = []
    slopes: dict[int, float] = {}
    for temp in [600, 700, 800]:
        xs, ys = [], []
        for dose in sorted(TMC_150):
            delta = TMC_150[dose][temp] - MATRIX_150[temp]
            xs.append(dose); ys.append(delta)
            dose_rows.append({
                "row_type": "POINT", "snapshot_id": snap, "paper_uid": "P_INT_XIONG_2022_PPT",
                "temperature_c": temp, "dose_vol_pct": dose, "delta_uts_mpa": delta,
                "efficiency_mpa_per_vol_pct": round(delta / dose, 6), "model": "descriptive",
                "slope_mpa_per_vol_pct": "", "uncertainty": "NOT_ESTIMABLE", "status": "OBSERVED",
            })
        slope = float(np.polyfit(xs, ys, 1)[0]); slopes[temp] = slope
        dose_rows.append({
            "row_type": "SUMMARY", "snapshot_id": snap, "paper_uid": "P_INT_XIONG_2022_PPT",
            "temperature_c": temp, "dose_vol_pct": "", "delta_uts_mpa": "",
            "efficiency_mpa_per_vol_pct": "", "model": "OLS descriptive slope",
            "slope_mpa_per_vol_pct": round(slope, 6), "uncertainty": "NOT_ESTIMABLE",
            "status": "NONMONOTONIC_OR_SATURATING_CHECK_REQUIRED",
        })
    write_csv(root, "DOSE_RESPONSE.csv", dose_rows)

    interactions = [
        {"interaction_uid": uid("INT_DOSE_T", t), "snapshot_id": snap, "interaction": "temperature × reinforcement dose", "domain": f"{t}C short-term tension", "estimate": round(slopes[t], 6), "uncertainty": "NOT_ESTIMABLE", "evidence": "DIRECT_SLIDE_TABLE_DERIVED", "status": "DESCRIPTIVE_ONLY"}
        for t in [600, 700, 800]
    ]
    interactions.extend([
        {"interaction_uid": uid("INT_RATE_DRX"), "snapshot_id": snap, "interaction": "temperature × strain rate", "domain": "1040-1100C hot compression", "estimate": "DRV at 0.01-0.001 s-1; DRX at 0.1-1 s-1", "uncertainty": "state bracket only", "evidence": "DIRECT_TEXT_EBSD", "status": "SOURCE_BOUNDED"},
        {"interaction_uid": uid("INT_OX_TIME"), "snapshot_id": snap, "interaction": "temperature × exposure time × environment", "domain": "800C air service", "estimate": "", "uncertainty": "NOT_IDENTIFIABLE", "evidence": "UNRESOLVED", "status": "DATA_GAP"},
        {"interaction_uid": uid("INT_CREEP"), "snapshot_id": snap, "interaction": "temperature × stress × time", "domain": "800C creep", "estimate": "", "uncertainty": "NOT_IDENTIFIABLE", "evidence": "UNRESOLVED", "status": "DATA_GAP"},
    ])
    write_csv(root, "INTERACTION_EFFECTS.csv", interactions)

    heterogeneity = [
        {"domain": "matrix_family", "levels": "Ti65; IMI834-like; CP-Ti; Ti64; near-alpha Ti", "impact": "major", "quantified": "NO", "reason": "mechanism transfer across matrices invalid"},
        {"domain": "process", "levels": "hot press; GTAW; casting; hot compression", "impact": "major", "quantified": "NO", "reason": "microstructure and interface state differ"},
        {"domain": "test_mode", "levels": "tension; compression; oxidation; creep", "impact": "major", "quantified": "NO", "reason": "estimands are nonexchangeable"},
        {"domain": "environment", "levels": "air; vacuum; missing", "impact": "major", "quantified": "NO", "reason": "oxidation/service risk is environment-specific"},
        {"domain": "time", "levels": "short-term; 50h censored; 70h; 100h", "impact": "major", "quantified": "NO", "reason": "time-dependent damage cannot be pooled"},
        {"domain": "source_independence", "levels": "internal family; six independent papers", "impact": "major", "quantified": "PARTIAL", "reason": "800C mechanical effects lack independent replication"},
        {"domain": "I2", "levels": "not computed", "impact": "", "quantified": "NO", "reason": "insufficient exchangeable independent effects"},
    ]
    write_csv(root, "HETEROGENEITY.csv", heterogeneity)

    sensitivity = [
        {"analysis": "exclude internal source", "result": "800C short-term strengthening estimate disappears", "conclusion": "no independent quantitative 800C mechanical effect", "status": "CLAIM_REDUCED"},
        {"analysis": "exclude figure-derived evidence", "result": "10um oxide-scale anchor removed", "conclusion": "oxidation state remains qualitative", "status": "ROBUST_STATE_ONLY"},
        {"analysis": "exclude hot-compression studies", "result": "DRV/DRX processing boundaries removed", "conclusion": "service-risk verdict unchanged", "status": "ROBUST_SERVICE_BOUNDARY"},
        {"analysis": "oxidation-only", "result": "800C air risk remains scale damage/spallation", "conclusion": "mechanical qualification still absent", "status": "ROBUST"},
        {"analysis": "leave-one-paper-out", "result": "not meaningful for internal 800C strengthening", "conclusion": "LOPO NOT_IDENTIFIABLE", "status": "INSUFFICIENT_CLUSTERS"},
        {"analysis": "alternative changepoint definition", "result": "600-800 attenuation candidate remains weak", "conclusion": "no universal threshold", "status": "ROBUST_LIMITATION"},
        {"analysis": "evidence-grade downgrade", "result": "all source-bounded claims remain <=2", "conclusion": "no causal/service qualification", "status": "PASS"},
    ]
    write_csv(root, "SENSITIVITY_ANALYSIS.csv", sensitivity)

    nulls = [
        {"result_id": "N1", "question": "calibrated mechanism probability vs temperature/time", "result": "NOT_IDENTIFIABLE", "reason": "reported states are not frequencies or posteriors"},
        {"result_id": "N2", "question": "direct 800C long-duration creep mechanism", "result": "NOT_IDENTIFIABLE", "reason": "no direct dataset"},
        {"result_id": "N3", "question": "cross-paper pooled 800C strengthening", "result": "NOT_IDENTIFIABLE", "reason": "no exchangeable independent matched families"},
        {"result_id": "N4", "question": "universal mechanism changepoint", "result": "REJECTED", "reason": "boundaries depend on matrix, process, rate, time, environment"},
        {"result_id": "N5", "question": "service qualification", "result": "FORBIDDEN", "reason": "short-term strength is not long-duration service evidence"},
        {"result_id": "N6", "question": "fully protective oxidation from reinforcement", "result": "NOT_SUPPORTED", "reason": "semi-protective/nonprotective regimes persist"},
        {"result_id": "N7", "question": "prediction interval", "result": "NOT_IDENTIFIABLE", "reason": "insufficient independent clusters"},
        {"result_id": "N8", "question": "causal reinforcement effect", "result": "NOT_CLAIMED", "reason": "maximum claim level 2"},
    ]
    write_csv(root, "NULL_NEGATIVE_RESULTS.csv", nulls)

    conflicts = [
        {"conflict_id": "C1", "claim_a": "short-term residual strengthening at 800C", "claim_b": "no 800C long-duration creep qualification", "resolution": "both can coexist; time scale differs", "status": "OPEN_SERVICE_GAP"},
        {"conflict_id": "C2", "claim_a": "high-temperature ductility recovery in some conditions", "claim_b": "interface decohesion at 650C in welded TMC", "resolution": "condition/microstructure-specific", "status": "RESOLVED_BY_SCOPE"},
        {"conflict_id": "C3", "claim_a": "hot-work DRV/DRX transitions", "claim_b": "service softening/creep mechanisms", "resolution": "processing evidence cannot substitute service evidence", "status": "RESOLVED_BY_SCOPE"},
        {"conflict_id": "C4", "claim_a": "higher apparent oxidation activation energy", "claim_b": "semi-protective/nonprotective scale", "resolution": "Q is not equivalent to protection", "status": "RESOLVED_BY_MECHANISM"},
        {"conflict_id": "C5", "claim_a": "internal direct slide values", "claim_b": "independent-paper requirement", "resolution": "retain as same-work level-2 evidence only", "status": "OPEN_INDEPENDENCE_GAP"},
    ]
    write_csv(root, "CONFLICT_LEDGER.csv", conflicts)
    return conflicts, hierarchical


def build_risk_network(root: Path, snap: str) -> dict[str, Any]:
    node_ids = [
        "matrix_softening", "dynamic_recovery", "dynamic_recrystallization", "interface_decohesion",
        "TiB_fragmentation", "particle_coarsening", "beta_grain_growth", "oxygen_diffusion",
        "oxide_scale_damage", "scale_spallation", "creep_damage", "short_term_strength_residual",
        "800C_service_failure",
    ]
    risk_map = {
        "matrix_softening": "high", "dynamic_recovery": "medium", "dynamic_recrystallization": "contextual",
        "interface_decohesion": "high", "TiB_fragmentation": "medium", "particle_coarsening": "unresolved",
        "beta_grain_growth": "contextual", "oxygen_diffusion": "high", "oxide_scale_damage": "high",
        "scale_spallation": "critical", "creep_damage": "critical_unquantified",
        "short_term_strength_residual": "not_qualification", "800C_service_failure": "critical",
    }
    nodes = [{"id": n, "risk": risk_map[n]} for n in node_ids]
    edges = [
        {"source": "matrix_softening", "target": "dynamic_recovery", "sign": 1, "evidence": "Mao/Xu source-bounded", "resolved": True},
        {"source": "dynamic_recovery", "target": "short_term_strength_residual", "sign": -1, "evidence": "derived support", "resolved": True},
        {"source": "matrix_softening", "target": "interface_decohesion", "sign": 1, "evidence": "Mao fractography", "resolved": True},
        {"source": "interface_decohesion", "target": "800C_service_failure", "sign": 1, "evidence": "extrapolation risk", "resolved": False},
        {"source": "TiB_fragmentation", "target": "interface_decohesion", "sign": 1, "evidence": "Sun processing evidence", "resolved": False},
        {"source": "particle_coarsening", "target": "short_term_strength_residual", "sign": -1, "evidence": "competing hypothesis", "resolved": False},
        {"source": "oxygen_diffusion", "target": "oxide_scale_damage", "sign": 1, "evidence": "Kim/Wei oxidation", "resolved": True},
        {"source": "oxide_scale_damage", "target": "scale_spallation", "sign": 1, "evidence": "Wei 100h air sequence", "resolved": True},
        {"source": "scale_spallation", "target": "800C_service_failure", "sign": 1, "evidence": "800C air long-time risk", "resolved": True},
        {"source": "creep_damage", "target": "800C_service_failure", "sign": 1, "evidence": "no direct 800C dataset", "resolved": False},
        {"source": "short_term_strength_residual", "target": "800C_service_failure", "sign": -1, "evidence": "short-term only", "resolved": False},
        {"source": "beta_grain_growth", "target": "800C_service_failure", "sign": 1, "evidence": "processing-only analogy forbidden", "resolved": False},
    ]
    risk = {
        "window_id": WINDOW_ID, "snapshot_id": snap,
        "service_condition": {"temperature_c": 800, "time": "long-duration unresolved", "environment": "air unless specified", "stress_strain_rate": "unresolved"},
        "nodes": nodes, "edges": edges,
        "dominant_risk_verdict": "For 800 C air and long exposure, oxidation-scale damage/spallation is the strongest directly evidenced risk; creep damage may be co-controlling but is unquantified. Short-term residual strengthening is not service qualification.",
        "competing_hypotheses": ["creep damage co-controls in low-oxygen environments", "interface degradation controls before bulk softening", "particle/coarsening effects alter load transfer"],
        "claim_level_max": 2, "status": STATUS,
    }
    write_json(root, "SERVICE_RISK_NETWORK.json", risk)
    write_csv(root, "figure_data/service_risk_network.csv", edges)
    return risk


def build_provenance(root: Path, snap: str, effects: list[dict[str, Any]]) -> None:
    records = []
    for source in PRIMARY_SOURCES:
        records.append({
            "provenance_uid": uid("SRC", source["paper_uid"]), "snapshot_id": snap,
            "object_type": "source", "object_uid": source["paper_uid"],
            "source_locator": source["source_locator"], "source_hash": source["source_hash"],
            "evidence_level": source["evidence_level"], "transformation": "registered direct source",
            "generated_at": GENERATED_AT,
        })
    for effect in effects:
        records.append({
            "provenance_uid": uid("EFF", effect["effect_uid"]), "snapshot_id": snap,
            "object_type": "effect", "object_uid": effect["effect_uid"],
            "paper_uid": effect["paper_uid"], "sample_uid": effect["sample_uid"],
            "condition_uid": effect["condition_uid"], "source_locator": effect["source_locator"],
            "source_hash": effect["source_hash"], "evidence_level": effect["evidence_level"],
            "transformation": "delta, lnRR, percent and efficiency from bound pair", "generated_at": GENERATED_AT,
        })
    p = root / "PROVENANCE.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_figure_data(root: Path, mean_delta: dict[int, float], changepoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state_rows = [
        {"temperature_c": 600, "track": "short_term_strength", "state": "substantial contribution", "source": "internal", "support_index": 1.0},
        {"temperature_c": 700, "track": "short_term_strength", "state": "attenuated contribution", "source": "internal", "support_index": round(mean_delta[700] / mean_delta[600], 6)},
        {"temperature_c": 800, "track": "short_term_strength", "state": "near-null contribution", "source": "internal", "support_index": round(mean_delta[800] / mean_delta[600], 6)},
        {"temperature_c": 600, "track": "oxidation_100h_air", "state": "protective/nearly parabolic", "source": "Wei 2017", "support_index": ""},
        {"temperature_c": 700, "track": "oxidation_100h_air", "state": "partially damaged/quasi-linear", "source": "Wei 2017", "support_index": ""},
        {"temperature_c": 800, "track": "oxidation_100h_air", "state": "spallation/linear", "source": "Wei 2017", "support_index": ""},
        {"temperature_c": 600, "track": "fracture", "state": "TiBw fracture + voiding", "source": "Mao 2013", "support_index": ""},
        {"temperature_c": 650, "track": "fracture", "state": "interface decohesion", "source": "Mao 2013", "support_index": ""},
        {"temperature_c": 650, "track": "creep", "state": "DRV/work-hardening balance", "source": "Xu 2023", "support_index": ""},
    ]
    write_csv(root, "figure_data/mechanism_state_map.csv", state_rows)
    contribution = []
    for dose, values in TMC_150.items():
        for temp in [600, 700, 800]:
            contribution.append({"temperature_c": temp, "series": f"{dose} vol% TiBw", "delta_uts_mpa": values[temp] - MATRIX_150[temp], "evidence": "DIRECT_SLIDE_TABLE", "uncertainty": "NOT_ESTIMABLE"})
    for temp in [600, 700, 800]:
        contribution.append({"temperature_c": temp, "series": "dose-balanced mean", "delta_uts_mpa": round(mean_delta[temp], 6), "evidence": "DERIVED_MEAN", "uncertainty": "NOT_ESTIMABLE"})
    write_csv(root, "figure_data/contribution_decay.csv", contribution)
    write_csv(root, "figure_data/changepoints.csv", changepoints)
    return state_rows


def save_figure(root: Path, fig: plt.Figure, stem: str) -> None:
    d = root / "figures"; d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(d / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(d / f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


def build_figures(root: Path, mean_delta: dict[int, float], state_rows: list[dict[str, Any]], changepoints: list[dict[str, Any]], risk: dict[str, Any]) -> None:
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 12, "axes.labelsize": 10, "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, ax = plt.subplots(figsize=(9, 5.5))
    tracks = ["short_term_strength", "fracture", "creep", "oxidation_100h_air"]
    ymap = {track: i for i, track in enumerate(tracks)}
    markers = {"short_term_strength": "o", "fracture": "s", "creep": "^", "oxidation_100h_air": "D"}
    for row in state_rows:
        y = ymap[row["track"]]
        ax.scatter(row["temperature_c"], y, s=75, marker=markers[row["track"]], zorder=3)
        ax.annotate(row["state"], (row["temperature_c"], y), xytext=(4, 7), textcoords="offset points", fontsize=7, rotation=15)
    ax.set_yticks(range(len(tracks)), ["Short-term strength", "Fracture mode", "650°C creep", "100 h air oxidation"])
    ax.set_xlim(575, 825); ax.set_xlabel("Temperature (°C)")
    ax.set_title("Mechanism-state support map (not a calibrated probability)")
    ax.grid(axis="x", alpha=.25)
    ax.text(0, -0.22, "Independent papers: 3 on displayed tracks + 1 internal family | Evidence: direct text/table/derived proxy | Claim ceiling: level 2", transform=ax.transAxes, fontsize=8)
    save_figure(root, fig, "FIG01_mechanism_state_map")

    fig, ax = plt.subplots(figsize=(8, 5.2))
    for dose, values in sorted(TMC_150.items()):
        ax.plot([600, 700, 800], [values[t] - MATRIX_150[t] for t in [600, 700, 800]], marker="o", label=f"{dose} vol% TiBw")
    ax.plot([600, 700, 800], [mean_delta[t] for t in [600, 700, 800]], marker="s", linewidth=2.8, label="Dose-balanced mean")
    ax.axhline(0, linewidth=.8); ax.set_xlabel("Temperature (°C)"); ax.set_ylabel("ΔUTS vs Ti65 matrix (MPa)")
    ax.set_title("Strengthening-contribution attenuation in short-term tension")
    ax.legend(frameon=False); ax.grid(alpha=.25)
    ax.text(0, -0.23, "Independent papers: 0 (one internal family) | 9 matched pairs | No CI/PI: specimen dispersion unavailable | 800°C is short-term only", transform=ax.transAxes, fontsize=8)
    save_figure(root, fig, "FIG02_contribution_decay")

    fig, ax = plt.subplots(figsize=(9, 6))
    cp_plot = [c for c in changepoints if c["axis"] == "temperature_c"]
    for i, c in enumerate(cp_plot):
        lo, hi = c["lower_bound"], c["upper_bound"]
        if lo == "" or hi == "":
            x = hi if hi != "" else lo
            if x != "": ax.scatter([float(x)], [i], marker="<", s=65)
        else:
            ax.hlines(i, float(lo), float(hi), linewidth=5, alpha=.65)
            if c["candidate"] != "": ax.scatter([float(c["candidate"])], [i], s=45, zorder=3)
    ax.set_yticks(range(len(cp_plot)), [c["paper_uid"] + " | " + c["interval_type"] for c in cp_plot])
    ax.set_xlabel("Temperature (°C)"); ax.set_title("Source-bounded mechanism-transition intervals")
    ax.grid(axis="x", alpha=.25)
    ax.text(0, -0.18, "Direct brackets, processing domains, censoring and data gaps; not one universal changepoint. Claim ceiling: level 2.", transform=ax.transAxes, fontsize=8)
    save_figure(root, fig, "FIG03_changepoint_intervals")

    fig, ax = plt.subplots(figsize=(10, 7)); ax.axis("off")
    pos = {"matrix_softening": (.08, .73), "dynamic_recovery": (.28, .85), "interface_decohesion": (.33, .62), "TiB_fragmentation": (.12, .48), "particle_coarsening": (.33, .35), "oxygen_diffusion": (.08, .2), "oxide_scale_damage": (.35, .18), "scale_spallation": (.58, .2), "creep_damage": (.58, .5), "short_term_strength_residual": (.58, .82), "800C_service_failure": (.88, .5), "beta_grain_growth": (.33, .95)}
    for node in risk["nodes"]:
        if node["id"] not in pos: continue
        x, y = pos[node["id"]]
        ax.scatter([x], [y], s=1300, edgecolors="black", linewidths=.8, zorder=3)
        ax.text(x, y, node["id"].replace("_", "\n"), ha="center", va="center", fontsize=7, zorder=4)
    for edge in risk["edges"]:
        if edge["source"] not in pos or edge["target"] not in pos: continue
        x1, y1 = pos[edge["source"]]; x2, y2 = pos[edge["target"]]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.3, linestyle="-" if edge["resolved"] else "--", alpha=.75))
    ax.set_title("800°C service-risk mechanism network")
    ax.text(.02, .02, "Solid: directly supported within domain | Dashed: unresolved/extrapolative\nHighest directly evidenced air/long-time risk: oxide-scale damage/spallation. Creep may co-control but is unquantified.", transform=ax.transAxes, fontsize=8)
    save_figure(root, fig, "FIG04_service_risk_network")


def write_plot_scripts(root: Path) -> None:
    scripts = {
        "plot_mechanism_state_map.py": """import csv, matplotlib.pyplot as plt\nrows=list(csv.DictReader(open('../figure_data/mechanism_state_map.csv',encoding='utf-8-sig')))\ntracks=sorted(set(r['track'] for r in rows)); ym={x:i for i,x in enumerate(tracks)}\nfig,ax=plt.subplots(figsize=(9,5))\nfor r in rows: ax.scatter(float(r['temperature_c']),ym[r['track']]); ax.annotate(r['state'],(float(r['temperature_c']),ym[r['track']]),fontsize=6)\nax.set_yticks(range(len(tracks)),tracks); ax.set_xlabel('Temperature (°C)'); ax.set_title('Mechanism-state support (not calibrated probability)'); fig.savefig('replot.svg',bbox_inches='tight')\n""",
        "plot_contribution_decay.py": """import csv, matplotlib.pyplot as plt\nrows=list(csv.DictReader(open('../figure_data/contribution_decay.csv',encoding='utf-8-sig'))); series=sorted(set(r['series'] for r in rows))\nfig,ax=plt.subplots()\nfor s in series:\n q=sorted([r for r in rows if r['series']==s],key=lambda r:float(r['temperature_c'])); ax.plot([float(r['temperature_c']) for r in q],[float(r['delta_uts_mpa']) for r in q],marker='o',label=s)\nax.legend(); ax.set_xlabel('Temperature (°C)'); ax.set_ylabel('ΔUTS (MPa)'); fig.savefig('replot.svg',bbox_inches='tight')\n""",
        "plot_changepoints.py": """import csv, matplotlib.pyplot as plt\nrows=[r for r in csv.DictReader(open('../figure_data/changepoints.csv',encoding='utf-8-sig')) if r['axis']=='temperature_c' and r['lower_bound'] and r['upper_bound']]\nfig,ax=plt.subplots()\nfor i,r in enumerate(rows): ax.hlines(i,float(r['lower_bound']),float(r['upper_bound']),lw=4)\nax.set_yticks(range(len(rows)),[r['paper_uid'] for r in rows]); ax.set_xlabel('Temperature (°C)'); fig.savefig('replot.svg',bbox_inches='tight')\n""",
        "plot_service_risk_network.py": """import csv, matplotlib.pyplot as plt\nrows=list(csv.DictReader(open('../figure_data/service_risk_network.csv',encoding='utf-8-sig'))); nodes=sorted(set([r['source'] for r in rows]+[r['target'] for r in rows]))\nfig,ax=plt.subplots(figsize=(9,7)); ax.axis('off')\nfor i,n in enumerate(nodes): x=(i%4)/3; y=1-(i//4)/4; ax.scatter(x,y,s=700); ax.text(x,y,n,ha='center',va='center',fontsize=6)\nfig.savefig('replot.svg',bbox_inches='tight')\n""",
    }
    for name, source in scripts.items():
        write_text(root, "plot_code/" + name, source)


def write_docs_and_tests(root: Path, snap: str, mean_delta: dict[int, float], cohort_count: int, pair_count: int, effect_count: int, conflicts: list[dict[str, Any]]) -> None:
    write_text(root, "00_EXECUTIVE_VERDICT.md", f"""
    # QM37 Executive Verdict

    Snapshot: `{snap}`  
    Status: `{STATUS}`  
    Maximum claim level: **2 — same-work/same-paper association**.

    ## Quantitative result
    The same-work TiBw/Ti65 short-term tensile comparison contains 9 grade-A pairs. The dose-balanced mean UTS increment is {mean_delta[600]:.1f} MPa at 600°C, {mean_delta[700]:.1f} MPa at 700°C, and {mean_delta[800]:.1f} MPa at 800°C. Only {100*mean_delta[800]/mean_delta[600]:.1f}% of the 600°C increment remains at 800°C, an 83.6% attenuation. This is not a calibrated service-retention probability and has no specimen-level CI.

    ## Mechanism transition
    Mao 2013 brackets a source-specific fracture transition between 600 and 650°C from TiBw fracture plus ductile voiding to interface decohesion plus void coalescence. Hot-compression papers show DRV/DRX and processing-instability domains, but those cannot substitute for 800°C service exposure.

    ## 800°C controlling risk
    For 100 h cyclic oxidation in air, Wei 2017 reports protective/nearly parabolic behavior at 600°C, partially damaged/quasi-linear behavior at 700°C, and complete scale spallation/linear kinetics at 800°C. Oxidation-scale damage/spallation is therefore the strongest directly evidenced 800°C long-time risk in air. Creep damage may co-control, but no direct 800°C long-duration creep dataset is present.

    ## Claim ceiling
    No Gold promotion, production-model registration, validated formulation, causal claim, or 800°C service qualification is authorized.
    """)
    write_text(root, "METHODS.md", """
    # Methods

    Atomic unit: paper × sample × actual composition × precursor × reinforcement × process × heat treatment × microstructure × test mode × temperature × strain rate × orientation × property. Same-source pairs use delta, log response ratio, percent change and unit-content efficiency. Internal TiBw/Ti65 effects are matched by powder-size family, route and temperature. MAO effects estimate welded-joint architecture preservation rather than pure reinforcement. KIM effects estimate dose-associated apparent oxidation activation-energy changes.

    Confidence and prediction intervals are left blank where raw replicate dispersion is absent. Mechanism probabilities are declared NOT_IDENTIFIABLE; reported state labels and normalized support indices remain distinct. Change points are direct brackets, processing-map domains, censoring bounds or explicit gaps. Cross-mode pooling of tension, compression, creep and oxidation is prohibited.
    """)
    write_text(root, "LIMITATIONS.md", """
    # Limitations

    1. Authoritative V29 atomic records, provenance and canonical condition UIDs were unavailable.
    2. The 600–800°C strengthening-decay series is one internal family without specimen-level dispersion or independent replication.
    3. Hot-compression DRV/DRX evidence is a processing domain, not an 800°C service test.
    4. Oxidation evidence is environment- and time-specific.
    5. Direct 800°C long-duration creep and co-measured oxidation–mechanics evidence are absent.
    6. Mechanism dominance probabilities, random-effects heterogeneity and prediction intervals are not identifiable.
    """)
    write_json(root, "PLOT_SPECS.json", {
        "figure_count": 4, "file_triplets": 12, "formats": ["svg", "pdf", "png_600dpi"], "claim_ceiling": 2,
        "figures": [
            {"id": "FIG01", "title": "Mechanism-state support map", "semantics": "reported states and proxy support; not calibrated probability", "data": "figure_data/mechanism_state_map.csv"},
            {"id": "FIG02", "title": "Contribution attenuation", "semantics": "same-work delta UTS; uncertainty unavailable", "data": "figure_data/contribution_decay.csv"},
            {"id": "FIG03", "title": "Changepoint intervals", "semantics": "source-bounded brackets/domains/gaps", "data": "figure_data/changepoints.csv"},
            {"id": "FIG04", "title": "800C service-risk network", "semantics": "solid direct vs dashed unresolved edges", "data": "figure_data/service_risk_network.csv"},
        ],
    })
    write_json(root, "WEB_TO_LOCAL_REQUEST.json", {
        "window_id": WINDOW_ID, "snapshot_id": snap, "status": STATUS, "required_objects": MISSING,
        "required_bindings": ["snapshot_id", "source_hash", "paper_uid", "sample_uid", "condition_uid"],
        "requested_fields": ["temperature_c", "time_h", "stress_mpa", "strain_rate_s-1", "environment", "mechanism evidence", "property value", "uncertainty"],
        "next_action": NEXT_ACTION,
    })
    write_text(root, "LOCAL_ABSORPTION_PROMPT.md", f"""
    Absorb `FINAL_QM37.zip` as a read-only web return. Verify `CHECKSUMS.sha256`, `MANIFEST.json`, CSV schemas, figure triplets and tests. Do not promote ACTIVE/Gold or register a production model. Bind V29 authoritative paper/sample/condition identities, then replace recovery identifiers without changing numerical content unless direct primary evidence requires correction. Acquire direct 800°C long-duration creep and co-measured oxidation–mechanics evidence before any service claim. Current status: {STATUS}.
    """)
    write_text(root, "README.md", f"""
    # FINAL_QM37

    Reproducible high-temperature mechanism-transition web return.

    - Snapshot: `{snap}`
    - Status: `{STATUS}`
    - Claim ceiling: level 2
    - Cohort rows: {cohort_count}
    - Matched pairs/effects: {pair_count}/{effect_count}
    - Figure files: 12
    """)
    write_text(root, "requirements.txt", "numpy==2.2.6\nmatplotlib==3.10.3")
    write_text(root, "acceptance_commands.md", """
    # Acceptance commands

    ```bash
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python -m unittest discover -s tests -v
    python analysis_code/verify_package.py --root .
    ```
    """)
    verify_source = r'''
import argparse, hashlib, json
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''): h.update(c)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); args=ap.parse_args(); root=Path(args.root)
    checks={}
    for line in (root/'CHECKSUMS.sha256').read_text().splitlines():
        h,p=line.split('  ',1); checks[p]=h
    for p,h in checks.items(): assert sha(root/p)==h,(p,'hash mismatch')
    st=json.loads((root/'WINDOW_STATUS.json').read_text()); assert st['claim_level_max']<=2 and st['status']=='CONTINUE_DATA_GAP'
    assert not list(root.rglob('*.zip'))
    for stem in ['FIG01_mechanism_state_map','FIG02_contribution_decay','FIG03_changepoint_intervals','FIG04_service_risk_network']:
        for ext in ['svg','pdf','png']: assert (root/'figures'/f'{stem}.{ext}').exists()
    print('PASS',len(checks),'checksums')
if __name__=='__main__': main()
'''
    write_text(root, "analysis_code/verify_package.py", verify_source)
    write_text(root, "analysis_code/rebuild_qm37.py", """
    \"\"\"Rebuild contract for QM37. The delivered CSV/JSON and plot scripts are authoritative replay inputs.\"\"\"
    from pathlib import Path
    if __name__ == '__main__':
        print('QM37 rebuild contract loaded; execute plot_code scripts after installing requirements.')
        print('root=', Path(__file__).resolve().parents[1])
    """)
    tests = {
        "test_manifest.py": """import json,unittest\nfrom pathlib import Path\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_manifest(self): self.assertGreaterEqual(len(json.loads((R/'MANIFEST.json').read_text())['members']),40)\nif __name__=='__main__': unittest.main()\n""",
        "test_effects.py": """import csv,unittest\nfrom pathlib import Path\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_effects(self): self.assertEqual(len(list(csv.DictReader(open(R/'EFFECT_ESTIMATES.csv',encoding='utf-8-sig')))),36)\n def test_decay(self):\n  d=list(csv.DictReader(open(R/'MECHANISM_DECAY_RATES.csv',encoding='utf-8-sig'))); m=[x for x in d if x['sample_uid']=='dose_balanced_mean'][0]; self.assertLess(float(m['retained_fraction_800_vs_600']),0.17)\nif __name__=='__main__': unittest.main()\n""",
        "test_claim_ceiling.py": """import json,unittest\nfrom pathlib import Path\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_ceiling(self): self.assertLessEqual(json.loads((R/'WINDOW_STATUS.json').read_text())['claim_level_max'],2)\nif __name__=='__main__': unittest.main()\n""",
        "test_no_nested_zip.py": """import unittest\nfrom pathlib import Path\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_no_zip(self): self.assertEqual(list(R.rglob('*.zip')),[])\nif __name__=='__main__': unittest.main()\n""",
        "test_status.py": """import json,unittest\nfrom pathlib import Path\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_status(self): self.assertEqual(json.loads((R/'WINDOW_STATUS.json').read_text())['status'],'CONTINUE_DATA_GAP')\nif __name__=='__main__': unittest.main()\n""",
    }
    for name, source in tests.items():
        write_text(root, "tests/" + name, source)
    write_json(root, "WINDOW_STATUS.json", {
        "window_id": WINDOW_ID, "snapshot_id": snap, "papers_seen": 7, "papers_included": 7,
        "independent_papers": 6, "atomic_rows": cohort_count, "matched_pairs": pair_count,
        "effect_estimates": effect_count, "plots_generated": 12,
        "open_conflicts": sum(1 for c in conflicts if c["status"].startswith("OPEN")),
        "claim_level_max": CLAIM_LEVEL_MAX, "status": STATUS, "missing": MISSING,
        "next_action": NEXT_ACTION, "generated_at": GENERATED_AT,
    })


def finalize(root: Path, zip_path: Path, snap: str) -> dict[str, Any]:
    role = lambda rel: "figure" if rel.startswith("figures/") else "figure_data" if rel.startswith("figure_data/") else "plot_code" if rel.startswith("plot_code/") else "test" if rel.startswith("tests/") else "analysis_code" if rel.startswith("analysis_code/") else "report_or_table"
    members = []
    for p in sorted(x for x in root.rglob("*") if x.is_file() and x.name not in {"MANIFEST.json", "CHECKSUMS.sha256"}):
        rel = p.relative_to(root).as_posix()
        members.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha256_file(p), "role": role(rel), "provenance_class": "P0_PRIMARY_BOUND_DERIVED" if rel.endswith((".csv", ".json", ".jsonl")) else "P2_REPRODUCIBILITY"})
    write_json(root, "MANIFEST.json", {
        "window_id": WINDOW_ID, "snapshot_id": snap, "generated_at": GENERATED_AT,
        "status": STATUS, "claim_level_max": CLAIM_LEVEL_MAX, "members": members,
        "member_count_excluding_manifest_and_checksums": len(members), "no_nested_zip": True,
    })
    checks = []
    for p in sorted(x for x in root.rglob("*") if x.is_file() and x.name != "CHECKSUMS.sha256"):
        checks.append(f"{sha256_file(p)}  {p.relative_to(root).as_posix()}")
    write_text(root, "CHECKSUMS.sha256", "\n".join(checks))
    for line in (root / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        expected, rel = line.split("  ", 1)
        assert sha256_file(root / rel) == expected
    assert not list(root.rglob("*.zip"))
    assert len(list((root / "figures").glob("*"))) == 12
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(x for x in root.rglob("*") if x.is_file()):
            zf.write(p, p.relative_to(root).as_posix())
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None
        assert not any(name.lower().endswith(".zip") for name in zf.namelist())
    return {"zip_sha256": sha256_file(zip_path), "zip_bytes": zip_path.stat().st_size, "members": len(list(root.rglob("*")))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="qm37_public")
    args = parser.parse_args()
    base = Path(args.base).resolve()
    root = base / "FINAL_QM37"
    zip_path = base / "FINAL_QM37.zip"
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    if zip_path.exists(): zip_path.unlink()
    snap = snapshot_id()
    ledger = build_input_ledger(root, snap)
    cohort = build_cohort(root, snap)
    pairs, effects = build_pairs_effects(root, snap)
    states, mean_delta = build_mechanism_states(root, snap)
    decay, changepoints = build_decay_changepoints(root, snap, mean_delta)
    conflicts, hierarchical = build_other_tables(root, snap, mean_delta)
    risk = build_risk_network(root, snap)
    build_provenance(root, snap, effects)
    state_rows = build_figure_data(root, mean_delta, changepoints)
    build_figures(root, mean_delta, state_rows, changepoints, risk)
    write_plot_scripts(root)
    write_docs_and_tests(root, snap, mean_delta, len(cohort), len(pairs), len(effects), conflicts)
    assert len(cohort) == 70, len(cohort)
    assert len(pairs) == 36 and len(effects) == 36
    summary = finalize(root, zip_path, snap)
    summary.update({
        "window_id": WINDOW_ID, "snapshot_id": snap, "status": STATUS,
        "claim_level_max": CLAIM_LEVEL_MAX, "input_ledger_rows": len(ledger),
        "cohort_rows": len(cohort), "mechanism_states": len(states),
        "matched_pairs": len(pairs), "effect_estimates": len(effects),
        "decay_rows": len(decay), "changepoints": len(changepoints),
        "hierarchical_rows": len(hierarchical), "figure_files": 12,
    })
    write_json(base, "DELIVERY_SUMMARY.json", summary)
    (base / "FINAL_QM37.zip.sha256").write_text(f"{summary['zip_sha256']}  FINAL_QM37.zip\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
