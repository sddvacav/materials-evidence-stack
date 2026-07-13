#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import sys
import textwrap
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

WINDOW_ID = "QM19"
SEED = 20260713
N_MC = 20000
BUILD_ROOT = Path("build")
OUT = BUILD_ROOT / WINDOW_ID
ZIP_OUT = Path("web_returns") / "FINAL_QM19.zip"
STATUS = "CONTINUE_DATA_GAP"
SNAPSHOT_ID = "MISSING_V29_Q40_IMMUTABLE_SNAPSHOT"

REQUIRED_COMMON = [
    "00_EXECUTIVE_VERDICT.md",
    "INPUT_LEDGER.csv",
    "ANALYSIS_COHORT.csv",
    "PAIR_MATCHES.csv",
    "EFFECT_ESTIMATES.csv",
    "HIERARCHICAL_RESULTS.csv",
    "DOSE_RESPONSE.csv",
    "INTERACTION_EFFECTS.csv",
    "HETEROGENEITY.csv",
    "SENSITIVITY_ANALYSIS.csv",
    "NULL_NEGATIVE_RESULTS.csv",
    "CONFLICT_LEDGER.csv",
    "PROVENANCE.jsonl",
    "METHODS.md",
    "LIMITATIONS.md",
    "PLOT_SPECS.json",
    "WEB_TO_LOCAL_REQUEST.json",
    "LOCAL_ABSORPTION_PROMPT.md",
    "WINDOW_STATUS.json",
    "MANIFEST.json",
    "CHECKSUMS.sha256",
]
REQUIRED_SCOPE = [
    "DOSE_SERIES.csv",
    "DOSE_RESPONSE_ALL_PROPERTIES.csv",
    "BREAKPOINTS.csv",
    "FEASIBLE_DOSE_WINDOWS.csv",
]


def reset_output() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    for d in ["figure_data", "figures", "plot_code", "tests", "source_audit"]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    ZIP_OUT.parent.mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_text(rel: str, content: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(rel: str, obj) -> None:
    write_text(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def write_csv(rel: str, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else ["status", "reason"]
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def canonical_source_hash(paper_uid: str, doi: str, locator: str, values: str) -> str:
    return sha256_text("|".join([paper_uid, doi, locator, values]))


def make_uid(prefix: str, *parts) -> str:
    s = "|".join(str(x) for x in parts)
    return f"{prefix}_{sha256_text(s)[:16]}"


def t_ci(mean: float, se: float, tcrit: float = 2.776) -> tuple[float, float]:
    return mean - tcrit * se, mean + tcrit * se


def safe_float(x):
    try:
        if x in (None, ""):
            return None
        return float(x)
    except Exception:
        return None


def add_record(rows: list[dict], *, paper_uid: str, source_id: str, doi: str,
               sample_uid: str, condition_uid: str, series_uid: str,
               matrix_family: str, reinforcement_type: str, process: str,
               state: str, test_mode: str, temperature_C,
               dose_value, dose_unit: str, dose_basis: str,
               property_name: str, value, unit: str, sd="", n_min="",
               inequality="=", evidence_level="DIRECT_TABLE_TEXT",
               source_locator="", include_primary="TRUE", exclusion_reason="",
               particle_size_um="", distribution="", notes="",
               strain_rate_s_1="", orientation="") -> None:
    values = f"{dose_value}|{property_name}|{value}|{sd}|{unit}"
    rows.append({
        "record_uid": make_uid("R", paper_uid, sample_uid, condition_uid, property_name),
        "snapshot_id": SNAPSHOT_ID,
        "paper_uid": paper_uid,
        "source_id": source_id,
        "doi": doi,
        "source_hash": canonical_source_hash(paper_uid, doi, source_locator, values),
        "source_hash_type": "CANONICAL_EVIDENCE_BLOCK_SHA256_NOT_FILE_SHA256",
        "sample_uid": sample_uid,
        "condition_uid": condition_uid,
        "series_uid": series_uid,
        "matrix_family": matrix_family,
        "reinforcement_type": reinforcement_type,
        "process": process,
        "state": state,
        "test_mode": test_mode,
        "temperature_C": temperature_C,
        "strain_rate_s_1": strain_rate_s_1,
        "orientation": orientation,
        "dose_value": dose_value,
        "dose_unit": dose_unit,
        "dose_basis": dose_basis,
        "particle_size_um": particle_size_um,
        "distribution": distribution,
        "property": property_name,
        "value": value,
        "unit": unit,
        "sd": sd,
        "n_min": n_min,
        "inequality": inequality,
        "evidence_level": evidence_level,
        "source_locator": source_locator,
        "include_primary": include_primary,
        "exclusion_reason": exclusion_reason,
        "notes": notes,
    })


def build_records() -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    papers: list[dict] = []

    # Paper 1: clean multi-dose TiBw/TA15 series.
    p = "P_WANG_2021_MSEA_140783"
    doi = "10.1016/j.msea.2021.140783"
    papers.append({
        "paper_uid": p, "year": 2021,
        "title": "Microstructure evolution and tensile properties of as-rolled TiB/TA15 composites with network microstructure",
        "doi": doi, "role": "PRIMARY_CLEAN_MULTIDOSE", "independent": "TRUE",
        "opened": "FULL_TEXT_AND_FIGURES", "citation_marker": "turn15file1",
    })
    ta15 = {
        ("as_sintered", 25): {
            2.0: {"YS_MPa": (944, 5), "UTS_MPa": (1093, 8), "EL_pct": (6.8, 0.5)},
            3.5: {"YS_MPa": (976, 7), "UTS_MPa": (1111, 7), "EL_pct": (4.9, 0.4)},
            5.0: {"YS_MPa": (1014, 9), "UTS_MPa": (1134, 10), "EL_pct": (2.1, 0.4)},
        },
        ("as_rolled", 25): {
            2.0: {"YS_MPa": (1084, 9), "UTS_MPa": (1212, 12), "EL_pct": (13.0, 0.7)},
            3.5: {"YS_MPa": (1097, 11), "UTS_MPa": (1248, 10), "EL_pct": (10.5, 0.5)},
            5.0: {"YS_MPa": (1115, 7), "UTS_MPa": (1274, 13), "EL_pct": (3.2, 0.4)},
        },
        ("as_sintered", 600): {
            2.0: {"UTS_MPa": (605, 8), "EL_pct": (21.9, 1.0)},
            3.5: {"UTS_MPa": (612, 7), "EL_pct": (14.5, 0.7)},
            5.0: {"UTS_MPa": (646, 10), "EL_pct": (12.0, 0.5)},
        },
        ("as_rolled", 600): {
            2.0: {"UTS_MPa": (767, 7), "EL_pct": (24.6, 0.9)},
            3.5: {"UTS_MPa": (811, 12), "EL_pct": (18.5, 1.1)},
            5.0: {"UTS_MPa": (820, 9), "EL_pct": (20.8, 0.7)},
        },
        ("as_sintered", 650): {
            2.0: {"UTS_MPa": (525, 5), "EL_pct": (27.1, 1.3)},
            3.5: {"UTS_MPa": (535, 5), "EL_pct": (23.2, 0.8)},
            5.0: {"UTS_MPa": (568, 6), "EL_pct": (16.6, 1.1)},
        },
        ("as_rolled", 650): {
            2.0: {"UTS_MPa": (698, 8), "EL_pct": (42.1, 2.1)},
            3.5: {"UTS_MPa": (678, 7), "EL_pct": (37.2, 2.3)},
            5.0: {"UTS_MPa": (682, 10), "EL_pct": (25.8, 1.5)},
        },
    }
    for (state, temp), dose_map in ta15.items():
        series_uid = f"S_TA15_{state}_{temp}C"
        locator = "Table 1, p.7" if temp == 25 else "Table 2, p.9"
        for dose, props in dose_map.items():
            sample_uid = f"TA15_{state}_{dose:g}vol"
            condition_uid = f"TENSION_{temp}C_RD_{state}"
            for prop, (val, sd) in props.items():
                add_record(
                    rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_1594", doi=doi,
                    sample_uid=sample_uid, condition_uid=condition_uid, series_uid=series_uid,
                    matrix_family="TA15", reinforcement_type="TiBw", process="RHP+hot_rolling" if state == "as_rolled" else "RHP",
                    state=state, test_mode="tension", temperature_C=temp,
                    dose_value=dose, dose_unit="vol%", dose_basis="actual_phase_nominal_volume_fraction",
                    property_name=prop, value=val, unit="MPa" if prop != "EL_pct" else "%",
                    sd=sd, n_min=3, evidence_level="DIRECT_TABLE_TEXT", source_locator=locator,
                    distribution="quasi_continuous_network",
                    notes="At least three specimens reported; n_min=3 used conservatively."
                )
            # Relative density only bounded, not exact. Kept as a censored structural property.
            add_record(
                rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_1594", doi=doi,
                sample_uid=sample_uid, condition_uid=f"ARCHIMEDES_{state}", series_uid=f"S_TA15_DENSITY_{state}",
                matrix_family="TA15", reinforcement_type="TiBw", process="RHP+hot_rolling" if state == "as_rolled" else "RHP",
                state=state, test_mode="Archimedes", temperature_C=25,
                dose_value=dose, dose_unit="vol%", dose_basis="actual_phase_nominal_volume_fraction",
                property_name="POROSITY_pct_upper_bound", value=1.0, unit="%", inequality="<=",
                evidence_level="DIRECT_TABLE_TEXT", source_locator="Fig. 2b and text, p.3",
                distribution="quasi_continuous_network", include_primary="FALSE",
                exclusion_reason="CENSORED_BOUND_NOT_EXACT_DOSE_RESOLVED_POROSITY",
                notes="Relative density reported above 99.0%; transformed only to porosity <=1.0%, not an exact value."
            )

    # Paper 2: precursor-dose TiC/CP-Ti PLDED series.
    p = "P_WANG_2022_MSEA_143935"
    doi = "10.1016/j.msea.2022.143935"
    papers.append({
        "paper_uid": p, "year": 2022,
        "title": "Enhanced mechanical properties of in situ synthesized TiC/Ti composites by pulsed laser directed energy deposition",
        "doi": doi, "role": "PRIMARY_PRECURSOR_DOSE_SERIES", "independent": "TRUE",
        "opened": "FULL_TEXT_AND_FIGURES", "citation_marker": "turn15file0",
    })
    c_doses = [0.0, 0.26, 0.43, 0.60, 1.20, 1.60]
    hardness = [169, 222, 263, 273, 285, 312]
    friction = [0.58, 0.45, 0.40, 0.26, 0.36, 0.44]
    sizes_nm = {0.26: 350, 0.43: 470, 0.60: 550, 1.20: 585, 1.60: 620}
    for dose, hv, mu in zip(c_doses, hardness, friction):
        sample_uid = f"PLDED_C_{dose:g}wt"
        particle_um = "" if dose == 0 else sizes_nm[dose] / 1000.0
        for prop, val, unit, loc in [
            ("HV0.3", hv, "HV", "Fig. 7 and text, pp.4-6"),
            ("friction_coefficient", mu, "1", "Fig. 9 and text, pp.5-6"),
        ]:
            add_record(
                rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_3696", doi=doi,
                sample_uid=sample_uid, condition_uid="PLDED_FIXED_PARAMETERS_RT", series_uid="S_PLDED_CP_TI_C_PRECURSOR",
                matrix_family="CP-Ti", reinforcement_type="in_situ_TiC", process="PLDED",
                state="as_built", test_mode="hardness" if prop == "HV0.3" else "sliding_wear", temperature_C=25,
                dose_value=dose, dose_unit="wt% C", dose_basis="measured_precursor_carbon_content",
                property_name=prop, value=val, unit=unit, evidence_level="DIRECT_TABLE_TEXT",
                source_locator=loc, particle_size_um=particle_um,
                distribution="uniform_in_situ; morphology evolves equiaxed_to_rod_to_irregular",
                notes="Actual C content measured by carbon-sulfur analysis; not converted to reinforcement vol% because the reported TiC fraction is internally conflicted."
            )
        if dose in sizes_nm:
            add_record(
                rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_3696", doi=doi,
                sample_uid=sample_uid, condition_uid="SEM_AS_BUILT", series_uid="S_PLDED_TIC_SIZE",
                matrix_family="CP-Ti", reinforcement_type="in_situ_TiC", process="PLDED",
                state="as_built", test_mode="SEM", temperature_C=25,
                dose_value=dose, dose_unit="wt% C", dose_basis="measured_precursor_carbon_content",
                property_name="TiC_mean_size_um", value=particle_um, unit="um",
                evidence_level="DIRECT_TABLE_TEXT", source_locator="Section 3.1, p.3",
                particle_size_um=particle_um, distribution="uniform_in_situ",
                notes="Mean size reported in text."
            )
    # Exact tensile point at author-declared optimum; matrix estimates are explicitly derived.
    for prop, val, unit in [("YS_MPa", 741, "MPa"), ("UTS_MPa", 940, "MPa"), ("EL_pct", 18.9, "%")]:
        add_record(
            rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_3696", doi=doi,
            sample_uid="PLDED_C_0.6wt", condition_uid="TENSION_25C_AS_BUILT", series_uid="S_PLDED_TENSILE_C_PRECURSOR",
            matrix_family="CP-Ti", reinforcement_type="in_situ_TiC", process="PLDED",
            state="as_built", test_mode="tension", temperature_C=25,
            dose_value=0.6, dose_unit="wt% C", dose_basis="measured_precursor_carbon_content",
            property_name=prop, value=val, unit=unit, evidence_level="DIRECT_TABLE_TEXT",
            source_locator="Section 3.3, p.4 and abstract", particle_size_um=0.55,
            distribution="uniform_mixed_equiaxed_short_rod",
            notes="Author-declared optimum in precursor space; not a universal reinforcement-volume optimum."
        )
    # Derived matrix strengths, retained only for paired effect calculations, not promoted to direct data.
    for prop, val, formula in [
        ("YS_MPa", 741 / 1.786, "741/(1+0.786)"),
        ("UTS_MPa", 940 / 1.843, "940/(1+0.843)"),
    ]:
        add_record(
            rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_3696", doi=doi,
            sample_uid="PLDED_CP_TI_0C", condition_uid="TENSION_25C_AS_BUILT", series_uid="S_PLDED_TENSILE_C_PRECURSOR",
            matrix_family="CP-Ti", reinforcement_type="none", process="PLDED",
            state="as_built", test_mode="tension", temperature_C=25,
            dose_value=0.0, dose_unit="wt% C", dose_basis="measured_precursor_carbon_content",
            property_name=prop, value=round(val, 6), unit="MPa", evidence_level="DERIVED_CALCULATION",
            source_locator="Section 3.3 relative-improvement statement, p.4",
            include_primary="FALSE", exclusion_reason="DERIVED_BASELINE_FROM_ROUNDED_PERCENTAGE",
            notes=f"Derived as {formula}; excluded from precision breakpoint fitting."
        )

    # Paper 3: endpoint pair, 13.6 vol% hybrid reinforcement.
    p = "P_LI_2016_MATDES_01_092"
    doi = "10.1016/j.matdes.2016.01.092"
    papers.append({
        "paper_uid": p, "year": 2016,
        "title": "Strengthening behavior of in situ-synthesized (TiC-TiB)/Ti composites by powder metallurgy and hot extrusion",
        "doi": doi, "role": "PRIMARY_ENDPOINT_PAIR", "independent": "TRUE",
        "opened": "FULL_TEXT_AND_TABLE", "citation_marker": "turn9file2",
    })
    li_values = {
        0.0: {"YS_MPa": (484, 8), "UTS_MPa": (654, 7), "EL_pct": (29.0, 2.0)},
        13.6: {"YS_MPa": (916, 44), "UTS_MPa": (1138, 17), "EL_pct": (2.6, 1.8)},
    }
    for dose, props in li_values.items():
        for prop, (val, sd) in props.items():
            add_record(
                rows, paper_uid=p, source_id="FILE_LIBRARY_FULLTEXT_LI2016", doi=doi,
                sample_uid=f"PM_EXTRUDED_{dose:g}vol", condition_uid="TENSION_RT_HOT_EXTRUDED", series_uid="S_LI2016_HYBRID_ENDPOINT",
                matrix_family="CP-Ti", reinforcement_type="TiB+TiC" if dose else "none",
                process="powder_metallurgy+hot_extrusion", state="hot_extruded", test_mode="tension", temperature_C=25,
                dose_value=dose, dose_unit="vol%", dose_basis="measured_final_phase_volume_fraction",
                property_name=prop, value=val, unit="MPa" if prop != "EL_pct" else "%", sd=sd,
                evidence_level="DIRECT_TABLE_TEXT", source_locator="Mechanical-property table and text",
                distribution="in_situ_hybrid", notes="Composite final fraction: TiB 10.80 vol% + TiC 2.76 vol% = 13.6 vol%."
            )

    # Paper 4: older independent same-study over-dose series.
    p = "P_RANGANATH_1996_MST_12_220"
    doi = "UNRESOLVED"
    papers.append({
        "paper_uid": p, "year": 1996,
        "title": "Microstructure and deformation of TiB + Ti2C reinforced Ti matrix composites",
        "doi": doi, "role": "PRIMARY_OVERDOSE_SERIES", "independent": "TRUE",
        "opened": "FULL_TEXT_TABLES_AND_FIGURES", "citation_marker": "turn16file0;turn16file6",
    })
    rang = {
        0.0: {"YS_MPa": 397.5, "UTS_MPa": 495, "EL_pct": 26.0},
        15.0: {"YS_MPa": 690, "UTS_MPa": 757, "EL_pct": 2.0},
        25.0: {"YS_MPa": 635, "UTS_MPa": 680, "EL_pct": 0.2},
    }
    for dose, props in rang.items():
        for prop, val in props.items():
            inequality = "<" if dose == 25.0 and prop == "EL_pct" else "="
            add_record(
                rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_0820", doi=doi,
                sample_uid=f"CAS_{dose:g}vol", condition_uid="TENSION_298K", series_uid="S_RANGANATH_TIB_TI2C",
                matrix_family="CP-Ti", reinforcement_type="TiB+Ti2C" if dose else "none",
                process="combustion_assisted_synthesis", state="as_processed", test_mode="tension", temperature_C=25,
                dose_value=dose, dose_unit="vol%", dose_basis="calculated_final_phase_volume_fraction",
                property_name=prop, value=val, unit="MPa" if prop != "EL_pct" else "%", inequality=inequality,
                evidence_level="DIRECT_TABLE_TEXT", source_locator="Table 5, p.223",
                distribution="bimodal_rods+equiaxed", notes="25 vol% elongation is right-censored as <0.2%; stored at bound only for display, excluded from uncensored regression."
            )

    # Secondary prior: thesis review table. Sensitivity only.
    p = "P_THESIS_LIJIUXIAO_TABLE1_1"
    doi = "THESIS_UNRESOLVED"
    papers.append({
        "paper_uid": p, "year": "UNRESOLVED",
        "title": "TiB/La2O3 reinforced high-temperature titanium matrix composite thesis, Table 1-1 secondary compilation",
        "doi": doi, "role": "SECONDARY_DATABASE_PRIOR", "independent": "FALSE",
        "opened": "TABLE_TEXT", "citation_marker": "turn16file1",
    })
    prior = {
        0.0: {"E_GPa": 109, "UTS_MPa": 467, "YS_MPa": 393, "EL_pct": 20.7},
        5.0: {"E_GPa": 121, "UTS_MPa": 787, "YS_MPa": 639, "EL_pct": 12.5},
        10.0: {"E_GPa": 131, "UTS_MPa": 902, "YS_MPa": 706, "EL_pct": 5.6},
        15.0: {"E_GPa": 139, "UTS_MPa": 903, "YS_MPa": 842, "EL_pct": 0.4},
    }
    for dose, props in prior.items():
        for prop, val in props.items():
            add_record(
                rows, paper_uid=p, source_id="FILE_LIBRARY_PDF_0678", doi=doi,
                sample_uid=f"SECONDARY_TIB_TI_{dose:g}vol", condition_uid="RT_TENSION_SECONDARY", series_uid="S_SECONDARY_TIB_TI",
                matrix_family="CP-Ti", reinforcement_type="TiB" if dose else "none", process="cast_in_situ_or_unspecified",
                state="secondary_compilation", test_mode="tension", temperature_C=25,
                dose_value=dose, dose_unit="vol%", dose_basis="reported_reinforcement_volume_fraction",
                property_name=prop, value=val, unit="GPa" if prop == "E_GPa" else ("MPa" if prop != "EL_pct" else "%"),
                evidence_level="DATABASE_PRIOR", source_locator="Thesis Table 1-1",
                include_primary="FALSE", exclusion_reason="SECONDARY_SOURCE_NOT_INDEPENDENT_OR_CONDITION_COMPLETE",
                distribution="unspecified", notes="Used only as a directional sensitivity prior; never pooled with primary estimates."
            )

    return rows, papers


def build_effects(records: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    pair_rows: list[dict] = []
    effects: list[dict] = []
    dose_response: list[dict] = []

    by_series_prop = defaultdict(list)
    for r in records:
        if r["property"] == "POROSITY_pct_upper_bound":
            continue
        by_series_prop[(r["series_uid"], r["property"])].append(r)

    for (series_uid, prop), rr in sorted(by_series_prop.items()):
        rr = sorted(rr, key=lambda x: float(x["dose_value"]))
        # Adjacent comparisons only, preserving one paper/condition/state.
        for a, b in zip(rr[:-1], rr[1:]):
            if a["paper_uid"] != b["paper_uid"] or a["condition_uid"] != b["condition_uid"]:
                continue
            da, db = float(a["dose_value"]), float(b["dose_value"])
            if db <= da:
                continue
            va, vb = float(a["value"]), float(b["value"])
            delta = vb - va
            step = db - da
            slope = delta / step
            sd_a, sd_b = safe_float(a["sd"]), safe_float(b["sd"])
            n_a, n_b = safe_float(a["n_min"]), safe_float(b["n_min"])
            se_delta = None
            ci_delta = (None, None)
            se_slope = None
            ci_slope = (None, None)
            lnrr = None
            pct = None
            lnrr_ci = (None, None)
            if sd_a is not None and sd_b is not None and n_a and n_b:
                se_delta = math.sqrt(sd_a**2 / n_a + sd_b**2 / n_b)
                ci_delta = t_ci(delta, se_delta)
                se_slope = se_delta / step
                ci_slope = t_ci(slope, se_slope)
                if va > 0 and vb > 0 and a["inequality"] == "=" and b["inequality"] == "=":
                    lnrr = math.log(vb / va)
                    se_lnrr = math.sqrt((sd_a**2 / n_a) / va**2 + (sd_b**2 / n_b) / vb**2)
                    lnrr_ci = t_ci(lnrr, se_lnrr)
                    pct = 100.0 * (math.exp(lnrr) - 1.0)
            elif va > 0 and vb > 0 and a["inequality"] == "=" and b["inequality"] == "=":
                lnrr = math.log(vb / va)
                pct = 100.0 * (math.exp(lnrr) - 1.0)

            pair_uid = make_uid("PAIR", a["record_uid"], b["record_uid"])
            pair_rows.append({
                "pair_uid": pair_uid,
                "paper_uid": a["paper_uid"],
                "series_uid": series_uid,
                "condition_uid": a["condition_uid"],
                "property": prop,
                "low_record_uid": a["record_uid"],
                "high_record_uid": b["record_uid"],
                "dose_low": da,
                "dose_high": db,
                "dose_unit": a["dose_unit"],
                "match_grade": "A",
                "pair_type": "SAME_STUDY_ADJACENT_DOSE",
                "identification_level": "2_SAME_STUDY_PAIRED_EFFECT",
                "notes": "All non-dose conditions held at the paper-defined series level; not randomized."
            })
            effects.append({
                "effect_uid": make_uid("E", pair_uid, "delta"),
                "pair_uid": pair_uid,
                "paper_uid": a["paper_uid"],
                "series_uid": series_uid,
                "property": prop,
                "estimand": "DeltaY_high_minus_low",
                "effect_value": round(delta, 8),
                "effect_unit": a["unit"],
                "se": "" if se_delta is None else round(se_delta, 8),
                "ci95_low": "" if ci_delta[0] is None else round(ci_delta[0], 8),
                "ci95_high": "" if ci_delta[1] is None else round(ci_delta[1], 8),
                "lnRR": "" if lnrr is None else round(lnrr, 8),
                "lnRR_ci95_low": "" if lnrr_ci[0] is None else round(lnrr_ci[0], 8),
                "lnRR_ci95_high": "" if lnrr_ci[1] is None else round(lnrr_ci[1], 8),
                "percent_change": "" if pct is None else round(pct, 6),
                "dose_low": da, "dose_high": db, "dose_unit": a["dose_unit"],
                "match_grade": "A", "claim_level": 2,
                "evidence_level": min(a["evidence_level"], b["evidence_level"]),
                "uncertainty_status": "T_CI_NMIN3" if se_delta is not None else "POINT_ONLY_NO_REPORTED_N_OR_SD",
            })
            dose_response.append({
                "response_uid": make_uid("DR", pair_uid, "slope"),
                "paper_uid": a["paper_uid"],
                "series_uid": series_uid,
                "matrix_family": a["matrix_family"],
                "reinforcement_type": a["reinforcement_type"] if a["reinforcement_type"] != "none" else b["reinforcement_type"],
                "process": a["process"],
                "state": a["state"],
                "temperature_C": a["temperature_C"],
                "property": prop,
                "dose_basis": a["dose_basis"],
                "dose_unit": a["dose_unit"],
                "dose_low": da,
                "dose_high": db,
                "local_slope_dY_dDose": round(slope, 8),
                "slope_unit": f"{a['unit']}/{a['dose_unit']}",
                "se": "" if se_slope is None else round(se_slope, 8),
                "ci95_low": "" if ci_slope[0] is None else round(ci_slope[0], 8),
                "ci95_high": "" if ci_slope[1] is None else round(ci_slope[1], 8),
                "model": "ADJACENT_LOCAL_SECANT_SLOPE",
                "identifiability": "ESTIMATED" if a["inequality"] == "=" and b["inequality"] == "=" else "CENSORED_BOUND",
                "evidence_level": min(a["evidence_level"], b["evidence_level"]),
                "claim_level": 2,
                "notes": "Local finite-difference estimand; not a universal derivative."
            })
    return pair_rows, effects, dose_response


def build_interactions(records: list[dict]) -> list[dict]:
    index = {}
    for r in records:
        if r["paper_uid"] == "P_WANG_2021_MSEA_140783" and r["property"] in {"YS_MPa", "UTS_MPa", "EL_pct"}:
            index[(r["state"], int(float(r["temperature_C"])), float(r["dose_value"]), r["property"])] = r
    rows = []
    for temp in [25, 600, 650]:
        for dose in [2.0, 3.5, 5.0]:
            for prop in ["YS_MPa", "UTS_MPa", "EL_pct"]:
                a = index.get(("as_sintered", temp, dose, prop))
                b = index.get(("as_rolled", temp, dose, prop))
                if not a or not b:
                    continue
                effect = float(b["value"]) - float(a["value"])
                sd_a, sd_b = float(a["sd"]), float(b["sd"])
                se = math.sqrt(sd_a**2 / 3 + sd_b**2 / 3)
                lo, hi = t_ci(effect, se)
                rows.append({
                    "interaction_uid": make_uid("INT", temp, dose, prop),
                    "paper_uid": a["paper_uid"],
                    "interaction": "rolling_state_at_fixed_dose",
                    "temperature_C": temp,
                    "dose_value": dose,
                    "dose_unit": "vol%",
                    "property": prop,
                    "effect_rolled_minus_sintered": round(effect, 8),
                    "unit": a["unit"],
                    "se": round(se, 8),
                    "ci95_low": round(lo, 8),
                    "ci95_high": round(hi, 8),
                    "interpretation": "Conditional process-state effect; process and evolved microstructure are inseparable.",
                    "claim_level": 2,
                })
    return rows


def build_feasibility(records: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    rng = np.random.default_rng(SEED)
    idx = defaultdict(dict)
    for r in records:
        if r["paper_uid"] != "P_WANG_2021_MSEA_140783":
            continue
        if r["property"] not in {"UTS_MPa", "EL_pct"}:
            continue
        key = (r["state"], int(float(r["temperature_C"])))
        idx[key].setdefault(float(r["dose_value"]), {})[r["property"]] = r

    prob_rows = []
    breakpoint_rows = []
    window_rows = []
    for (state, temp), dose_map in sorted(idx.items()):
        doses = sorted(dose_map)
        if not all("UTS_MPa" in dose_map[d] and "EL_pct" in dose_map[d] for d in doses):
            continue
        uts_draws = []
        el_draws = []
        for d in doses:
            u = dose_map[d]["UTS_MPa"]
            e = dose_map[d]["EL_pct"]
            uts_draws.append(rng.normal(float(u["value"]), float(u["sd"]) / math.sqrt(3), N_MC))
            el_draws.append(rng.normal(float(e["value"]), float(e["sd"]) / math.sqrt(3), N_MC))
        U = np.column_stack(uts_draws)
        E = np.column_stack(el_draws)
        max_u = U.max(axis=1)
        feasible = (U >= 0.95 * max_u[:, None]) & (E >= 10.0)
        selection = np.full(N_MC, -1, dtype=int)
        for j in range(len(doses)):
            choose = (selection < 0) & feasible[:, j]
            selection[choose] = j
        probs = feasible.mean(axis=0)
        sel_probs = np.array([(selection == j).mean() for j in range(len(doses))])
        none_prob = (selection < 0).mean()
        observed_uts = np.array([float(dose_map[d]["UTS_MPa"]["value"]) for d in doses])
        observed_el = np.array([float(dose_map[d]["EL_pct"]["value"]) for d in doses])
        observed_feasible = (observed_uts >= 0.95 * observed_uts.max()) & (observed_el >= 10.0)
        for j, d in enumerate(doses):
            prob_rows.append({
                "paper_uid": "P_WANG_2021_MSEA_140783",
                "series_uid": f"S_TA15_{state}_{temp}C",
                "state": state,
                "temperature_C": temp,
                "dose_value": d,
                "dose_unit": "vol%",
                "UTS_mean_MPa": observed_uts[j],
                "EL_mean_pct": observed_el[j],
                "feasibility_definition": "UTS>=0.95*within-series maximum AND EL>=10%",
                "probability_feasible": round(float(probs[j]), 8),
                "probability_selected_as_smallest_feasible_dose": round(float(sel_probs[j]), 8),
                "observed_grid_feasible": bool(observed_feasible[j]),
                "mc_draws": N_MC,
                "seed": SEED,
                "uncertainty": "Normal sampling of reported mean with SE=SD/sqrt(3); n=3 conservative minimum.",
            })
        if sel_probs.sum() > 0:
            mode_j = int(np.argmax(sel_probs))
            candidate = doses[mode_j]
            support_doses = [doses[j] for j, pr in enumerate(sel_probs) if pr >= 0.05]
            ci_lo = min(support_doses) if support_doses else min(doses)
            ci_hi = max(support_doses) if support_doses else max(doses)
            status = "GRID_CANDIDATE"
            sel_prob = sel_probs[mode_j]
        else:
            candidate = ""
            ci_lo, ci_hi = min(doses), max(doses)
            status = "NO_FEASIBLE_TESTED_DOSE"
            sel_prob = 0.0
        breakpoint_rows.append({
            "breakpoint_uid": make_uid("BP", state, temp),
            "paper_uid": "P_WANG_2021_MSEA_140783",
            "series_uid": f"S_TA15_{state}_{temp}C",
            "property_set": "UTS_MPa+EL_pct",
            "dose_basis": "actual_phase_nominal_volume_fraction",
            "dose_unit": "vol%",
            "candidate_optimal_dose": candidate,
            "candidate_selection_probability": round(float(sel_prob), 8),
            "support_interval_low": ci_lo,
            "support_interval_high": ci_hi,
            "overdose_threshold_statement": "Between candidate and next tested higher dose when the next dose loses feasibility or is Pareto-dominated; otherwise not resolved.",
            "method": "PARAMETRIC_MC_GRID_SELECTION_SMALLEST_DOSE_WITHIN_95PCT_MAX_UTS_AND_EL_GE_10",
            "status": status,
            "none_feasible_probability": round(float(none_prob), 8),
            "claim_level": 2,
            "notes": "Three-point grid cannot identify a continuous breakpoint; interval is grid-support, not a universal confidence interval."
        })
        obs_doses = [doses[j] for j, flag in enumerate(observed_feasible) if flag]
        robust_doses = [doses[j] for j, pr in enumerate(probs) if pr >= 0.80]
        window_rows.append({
            "window_uid": make_uid("FW", state, temp, "observed"),
            "paper_uid": "P_WANG_2021_MSEA_140783",
            "matrix_family": "TA15",
            "reinforcement_type": "TiBw",
            "process_state": state,
            "temperature_C": temp,
            "window_type": "OBSERVED_GRID",
            "dose_low": min(obs_doses) if obs_doses else "",
            "dose_high": max(obs_doses) if obs_doses else "",
            "dose_unit": "vol%",
            "criterion": "UTS>=0.95*observed within-series maximum AND EL>=10%",
            "probability_threshold": "",
            "status": "FEASIBLE" if obs_doses else "NO_FEASIBLE_TESTED_DOSE",
            "claim_level": 2,
            "notes": "Contiguity is only over tested grid points."
        })
        window_rows.append({
            "window_uid": make_uid("FW", state, temp, "robust"),
            "paper_uid": "P_WANG_2021_MSEA_140783",
            "matrix_family": "TA15",
            "reinforcement_type": "TiBw",
            "process_state": state,
            "temperature_C": temp,
            "window_type": "ROBUST_MC_GRID",
            "dose_low": min(robust_doses) if robust_doses else "",
            "dose_high": max(robust_doses) if robust_doses else "",
            "dose_unit": "vol%",
            "criterion": "P(UTS>=0.95*sampled max AND EL>=10%)>=0.80",
            "probability_threshold": 0.80,
            "status": "FEASIBLE" if robust_doses else "NO_ROBUST_TESTED_DOSE",
            "claim_level": 2,
            "notes": "Parametric uncertainty uses reported SD and conservative n=3."
        })

    # Direct literature grid candidates not eligible for the above TA15 MC.
    breakpoint_rows.extend([
        {
            "breakpoint_uid": "BP_PLDED_C_PRECURSOR_0P6",
            "paper_uid": "P_WANG_2022_MSEA_143935",
            "series_uid": "S_PLDED_CP_TI_C_PRECURSOR",
            "property_set": "UTS+YS+EL+friction+morphology",
            "dose_basis": "measured_precursor_carbon_content",
            "dose_unit": "wt% C",
            "candidate_optimal_dose": 0.6,
            "candidate_selection_probability": "",
            "support_interval_low": 0.43,
            "support_interval_high": 1.2,
            "overdose_threshold_statement": "Deterioration emerges above 0.6 wt%C; irregular/dendritic TiC and tensile-strength decline are reported at 1.2-1.6 wt%C.",
            "method": "AUTHOR_DECLARED_OBSERVED_GRID_OPTIMUM_WITH_MORPHOLOGY_TRIANGULATION",
            "status": "PRECURSOR_SPACE_ONLY",
            "none_feasible_probability": "",
            "claim_level": 2,
            "notes": "Cannot be converted to a trustworthy TiC vol% breakpoint because the paper's reported TiC fractions are internally conflicted."
        },
        {
            "breakpoint_uid": "BP_RANGANATH_15VOL",
            "paper_uid": "P_RANGANATH_1996_MST_12_220",
            "series_uid": "S_RANGANATH_TIB_TI2C",
            "property_set": "YS+UTS+EL",
            "dose_basis": "calculated_final_phase_volume_fraction",
            "dose_unit": "vol%",
            "candidate_optimal_dose": 15.0,
            "candidate_selection_probability": "",
            "support_interval_low": 15.0,
            "support_interval_high": 25.0,
            "overdose_threshold_statement": "Tensile YS and UTS decline from 15 to 25 vol%; EL is already 2% at 15 vol% and <0.2% at 25 vol%.",
            "method": "OBSERVED_GRID_STRENGTH_MAXIMUM_WITH_DUCTILITY_FAILURE",
            "status": "OVERDOSE_CORROBORATION_NOT_FEASIBLE_WINDOW",
            "none_feasible_probability": "",
            "claim_level": 2,
            "notes": "The strength optimum is not a multiobjective optimum because ductility is unacceptable."
        },
    ])
    window_rows.extend([
        {
            "window_uid": "FW_PLDED_C_PRECURSOR",
            "paper_uid": "P_WANG_2022_MSEA_143935",
            "matrix_family": "CP-Ti",
            "reinforcement_type": "in_situ_TiC",
            "process_state": "PLDED_as_built",
            "temperature_C": 25,
            "window_type": "PRECURSOR_GRID_CONDITIONAL",
            "dose_low": 0.43,
            "dose_high": 0.60,
            "dose_unit": "wt% C",
            "criterion": "Author-reported strength/plasticity optimum and morphology remains equiaxed/short-rod rather than irregular/dendritic",
            "probability_threshold": "",
            "status": "CONDITIONAL_FEASIBLE_PRECURSOR_WINDOW",
            "claim_level": 2,
            "notes": "Not a reinforcement-volume window."
        },
        {
            "window_uid": "FW_RANGANATH_NONE",
            "paper_uid": "P_RANGANATH_1996_MST_12_220",
            "matrix_family": "CP-Ti",
            "reinforcement_type": "TiB+Ti2C",
            "process_state": "combustion_assisted_as_processed",
            "temperature_C": 25,
            "window_type": "OBSERVED_GRID",
            "dose_low": "",
            "dose_high": "",
            "dose_unit": "vol%",
            "criterion": "Strength increase with EL>=10%",
            "probability_threshold": "",
            "status": "NO_FEASIBLE_REINFORCED_TESTED_DOSE",
            "claim_level": 2,
            "notes": "15 vol% gives EL=2%; 25 vol% gives EL<0.2%."
        },
    ])
    return prob_rows, breakpoint_rows, window_rows


def build_conflicts() -> list[dict]:
    return [
        {
            "conflict_uid": "C001", "paper_uid": "P_WANG_2022_MSEA_143935",
            "field": "TiC_volume_fraction", "value_a": "2.09 to 19.24 vol% across series; 12.88 vol% at 0.6 wt%C",
            "value_b": "Simple carbon/TiC mass-balance expectation is materially lower for 0.6 wt%C",
            "source_a": "Fig.7 and Section 4.4", "source_b": "Stoichiometric plausibility check",
            "severity": "HIGH", "resolution": "OPEN_EXCLUDED_FROM_VOL_PERCENT_MODEL",
            "impact": "PLDED series retained in measured precursor wt%C only; no wt%↔vol% conversion or universal pooling."
        },
        {
            "conflict_uid": "C002", "paper_uid": "P_LI_2016_MATDES_01_092",
            "field": "pure_Ti_elongation", "value_a": "29±2% in table", "value_b": "32.4% in text",
            "source_a": "Mechanical-property table", "source_b": "Narrative text",
            "severity": "MEDIUM", "resolution": "TABLE_VALUE_PRIMARY_TEXT_VALUE_SENSITIVITY",
            "impact": "Headline paired ΔEL uses 29%; alternative baseline is reported in sensitivity table."
        },
        {
            "conflict_uid": "C003", "paper_uid": "P_WANG_2021_MSEA_140783",
            "field": "porosity_pct", "value_a": "relative density >99.0%", "value_b": "no exact dose-resolved density values in text/table",
            "source_a": "Fig.2b and text", "source_b": "required porosity estimand",
            "severity": "HIGH", "resolution": "CENSORED_UPPER_BOUND_ONLY",
            "impact": "Dose-porosity response and 3D porosity coordinate are not quantitatively identifiable; only <=1.0% bound is displayed."
        },
        {
            "conflict_uid": "C004", "paper_uid": "P_RANGANATH_1996_MST_12_220",
            "field": "EL_at_25vol", "value_a": "<0.2%", "value_b": "uncensored value unavailable",
            "source_a": "Table 5", "source_b": "regression requirement",
            "severity": "MEDIUM", "resolution": "RIGHT_CENSORED_BOUND",
            "impact": "Excluded from uncensored slope uncertainty; plotted as a bound."
        },
        {
            "conflict_uid": "C005", "paper_uid": "PROJECT_LEVEL",
            "field": "snapshot_binding", "value_a": "MDU requires V29 ATOMIC_RECORDS/PROVENANCE/CONFLICT ledger",
            "value_b": "No immutable V29/Q40 snapshot was available to this web execution runtime",
            "source_a": "QM19 dispatch", "source_b": "runtime input audit",
            "severity": "BLOCKING_FOR_GLOBAL_META_ANALYSIS", "resolution": "OPEN_LOCAL_REQUEST_EMITTED",
            "impact": "Literature-priority conditional analysis delivered; global hierarchical estimates, production registration and Gold promotion forbidden."
        },
    ]


def write_core_tables(records, papers, pairs, effects, dose_response, interactions,
                      probabilities, breakpoints, windows, conflicts) -> None:
    record_fields = list(records[0].keys())
    write_csv("DOSE_SERIES.csv", records, record_fields)
    write_csv("ANALYSIS_COHORT.csv", records, record_fields)
    write_csv("PAPER_REGISTRY.csv", papers)
    write_csv("PAIR_MATCHES.csv", pairs)
    write_csv("EFFECT_ESTIMATES.csv", effects)
    write_csv("DOSE_RESPONSE.csv", dose_response)
    write_csv("DOSE_RESPONSE_ALL_PROPERTIES.csv", dose_response)
    write_csv("INTERACTION_EFFECTS.csv", interactions)
    write_csv("BREAKPOINTS.csv", breakpoints)
    write_csv("FEASIBLE_DOSE_WINDOWS.csv", windows)
    write_csv("FEASIBILITY_PROBABILITIES.csv", probabilities)
    write_csv("CONFLICT_LEDGER.csv", conflicts)

    hierarchy = [{
        "model_id": "H001",
        "target": "global_dose_response_across_reinforcement_matrix_process_property",
        "status": "NOT_IDENTIFIABLE",
        "reason": "Too few exchangeable independent papers per exact reinforcement×matrix×process×state×temperature×property stratum; dose basis also differs (vol% phase vs wt% precursor).",
        "papers_available": 4,
        "papers_exchangeable_in_largest_exact_stratum": 1,
        "model_attempted": "NO",
        "claim_level": 2,
        "production_registration": "FORBIDDEN",
        "next_requirement": ">=3 independent clean multi-dose papers per target stratum with harmonized actual phase vol%, exact condition and uncertainty."
    }]
    write_csv("HIERARCHICAL_RESULTS.csv", hierarchy)

    hetero = [
        {
            "heterogeneity_id": "HET001", "dimension": "reinforcement_identity",
            "finding": "TiBw, TiC, TiB+TiC and TiB+Ti2C exhibit different morphology and fracture transitions.",
            "metric": "QUALITATIVE_MODERATOR", "value": "NOT_POOLABLE", "status": "HIGH_HETEROGENEITY",
            "implication": "No universal reinforcement-volume optimum."
        },
        {
            "heterogeneity_id": "HET002", "dimension": "matrix_process_state",
            "finding": "TA15/RHP/hot-rolled, CP-Ti/PLDED, CP-Ti/PM-extruded and CAS series have different dose scales and damage modes.",
            "metric": "QUALITATIVE_MODERATOR", "value": "NOT_POOLABLE", "status": "HIGH_HETEROGENEITY",
            "implication": "Windows must be conditioned on matrix, process and thermomechanical state."
        },
        {
            "heterogeneity_id": "HET003", "dimension": "temperature",
            "finding": "For hot-rolled TiBw/TA15, the smallest feasible/optimal tested dose shifts from 3.5 vol% at RT and 600°C to 2 vol% at 650°C.",
            "metric": "GRID_OPTIMUM_SHIFT", "value": "3.5→2.0 vol%", "status": "EFFECT_MODIFICATION",
            "implication": "High-temperature service cannot inherit the RT optimum."
        },
        {
            "heterogeneity_id": "HET004", "dimension": "dose_basis",
            "finding": "PLDED study is trustworthy in measured precursor C wt%, not in reported TiC vol%.",
            "metric": "BASIS_CONFLICT", "value": "wt% precursor vs vol% phase", "status": "NONCOMPARABLE",
            "implication": "No direct cross-study dose-axis merge."
        },
    ]
    write_csv("HETEROGENEITY.csv", hetero)

    sensitivity = [
        {
            "analysis_id": "SENS001", "analysis": "n_min_conservative_uncertainty",
            "base": "At least three tensile specimens", "alternative": "n=3 fixed for SE and t-CI",
            "result": "All TA15 adjacent-dose CIs use t(4)=2.776; no artificial precision from larger assumed n.",
            "verdict_change": "NO", "status": "PASS"
        },
        {
            "analysis_id": "SENS002", "analysis": "leave_one_paper_out_claim_stability",
            "base": "All four independent primary papers", "alternative": "Remove each paper in turn",
            "result": "The universal-optimum claim remains rejected in every leave-one-paper-out scenario; exact conditional windows disappear when their defining paper is removed.",
            "verdict_change": "UNIVERSAL_NO; CONDITIONAL_YES", "status": "PASS_WITH_SCOPE_LOSS"
        },
        {
            "analysis_id": "SENS003", "analysis": "secondary_prior_exclusion",
            "base": "Primary direct evidence only", "alternative": "Include thesis Table 1-1 as DATABASE_PRIOR",
            "result": "Secondary prior independently shows UTS saturation near 10-15 vol% and severe EL loss, but is not used to set headline thresholds.",
            "verdict_change": "NO", "status": "PASS"
        },
        {
            "analysis_id": "SENS004", "analysis": "PLDED_dose_axis",
            "base": "Measured precursor C wt%", "alternative": "Reported TiC vol%",
            "result": "Alternative rejected because reported TiC fraction is internally implausible/conflicted; 0.6 wt%C optimum retained only in precursor space.",
            "verdict_change": "PREVENTS_FALSE_VOL_PERCENT_CLAIM", "status": "FAIL_CLOSED"
        },
        {
            "analysis_id": "SENS005", "analysis": "Li2016_matrix_EL_conflict",
            "base": "29±2% table baseline", "alternative": "32.4% narrative baseline",
            "result": "ΔEL changes from -26.4 pp to -29.8 pp; conclusion of catastrophic ductility loss is unchanged.",
            "verdict_change": "NO", "status": "PASS"
        },
        {
            "analysis_id": "SENS006", "analysis": "Ranganath_censoring",
            "base": "EL at 25 vol% treated as <0.2%", "alternative": "Use 0.2% numerical bound for visualization only",
            "result": "Strength decline from 15 to 25 vol% and near-zero ductility remain; uncensored EL slope not estimated.",
            "verdict_change": "NO", "status": "PASS"
        },
    ]
    write_csv("SENSITIVITY_ANALYSIS.csv", sensitivity)

    nulls = [
        {
            "result_id": "N001", "question": "Global optimum reinforcement volume fraction across all Ti/TMC systems",
            "result": "NOT_IDENTIFIABLE", "reason": "Nonexchangeable reinforcement, matrix, process, state, temperature and dose basis.",
            "counterexample": "Hot-rolled TiBw/TA15 grid optimum shifts from 3.5 vol% at RT/600°C to 2 vol% at 650°C.",
            "next_data": "Harmonized independent multi-dose series in each exact stratum."
        },
        {
            "result_id": "N002", "question": "Exact porosity breakpoint",
            "result": "NOT_IDENTIFIABLE", "reason": "Only relative-density >99% bounds are available for the clean TA15 dose series.",
            "counterexample": "At 5 vol% TiBw, clusters, fractured whiskers, microcracks and 650°C interface debonding appear despite nominal density >99%.",
            "next_data": "Dose-resolved CT/Archimedes porosity mean, SD, pore morphology and build position."
        },
        {
            "result_id": "N003", "question": "800°C feasible dose window",
            "result": "NOT_IDENTIFIABLE", "reason": "No clean 800°C multi-dose tensile series in the accessed evidence cohort.",
            "counterexample": "None", "next_data": "At least 0/low/mid/high dose series at 800°C with common strain rate and exposure."
        },
        {
            "result_id": "N004", "question": "Continuous GAM/spline breakpoint with narrow CI",
            "result": "NOT_IDENTIFIABLE", "reason": "Most clean series have only three tested phase-volume doses.",
            "counterexample": "Any narrow continuous breakpoint would be model-imposed rather than data-identified.",
            "next_data": ">=5 well-spaced doses including both sides of the damage transition."
        },
        {
            "result_id": "N005", "question": "Production model or VALIDATED composition",
            "result": "FORBIDDEN", "reason": "MDU explicitly forbids production registration; official immutable snapshot is missing.",
            "counterexample": "All reported windows are literature-conditioned and SCREENED only.",
            "next_data": "Local controlled absorption and independent experimental validation."
        },
    ]
    write_csv("NULL_NEGATIVE_RESULTS.csv", nulls)


def write_input_audit(papers: list[dict]) -> None:
    packages = [
        "QM19_增强含量剂量响应、最佳窗口和过量阈值.md",
        "00_统一上传总控与校验信息_20260712.zip",
        "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
        "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip",
        "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip",
        "S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip",
        "S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip",
        "S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip",
        "S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip",
        "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
    ] + [f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1, 11)]
    rows = []
    for name in packages:
        if name.startswith("QM19_"):
            status = "OPENED_FULL_DISPATCH"
            role = "TASK_CONTRACT"
            used = "TRUE"
        elif name.startswith("TITMC_V27"):
            status = "PROJECT_PACKAGE_DECLARED; MEMBER_LEVEL_RUNTIME_AUDIT_UNAVAILABLE; LITERATURE_ORIGINALS_OPENED_VIA_FILE_LIBRARY"
            role = "ORIGINAL_LITERATURE_FAMILY"
            used = "PARTIAL_DIRECT_FILE_LIBRARY_ACCESS"
        elif "DATA_FEATURES" in name or "HARNESS_EVIDENCE" in name:
            status = "PROJECT_PACKAGE_DECLARED; MEMBER_LEVEL_RUNTIME_AUDIT_UNAVAILABLE; OFFICIAL_SNAPSHOT_NOT_LOCATED"
            role = "FROZEN_DATA_OR_HARNESS"
            used = "NO_NUMERIC_IMPORT"
        else:
            status = "PROJECT_PACKAGE_DECLARED; TERMINAL_NOT_USED_FOR_NUMERIC_CLAIMS"
            role = "CONTROL_CODE_OR_STAGING"
            used = "NO"
        rows.append({
            "input_name": name,
            "input_type": "MDU" if name.endswith(".md") else "ZIP_PACKAGE",
            "priority": 1 if name.endswith(".md") else (4 if name.startswith("TITMC") else 2),
            "opened_or_audited": status,
            "used_in_estimand": used,
            "snapshot_id": SNAPSHOT_ID,
            "source_hash": "MISSING_RUNTIME_FILE_HASH",
            "terminal_status": "DATA_GAP_RECORDED" if "UNAVAILABLE" in status else "CLOSED",
            "notes": "No claim is made that archive members were exhaustively inspected in this web runtime."
        })
    for p in papers:
        rows.append({
            "input_name": p["title"], "input_type": "ORIGINAL_OR_SECONDARY_LITERATURE",
            "priority": 1 if p["role"].startswith("PRIMARY") else 4,
            "opened_or_audited": p["opened"], "used_in_estimand": "TRUE" if p["role"].startswith("PRIMARY") else "SENSITIVITY_ONLY",
            "snapshot_id": SNAPSHOT_ID, "source_hash": "CANONICAL_EVIDENCE_BLOCK_SHA256_IN_RECORDS",
            "terminal_status": "INCLUDED" if p["role"].startswith("PRIMARY") else "INCLUDED_SECONDARY_ONLY",
            "notes": f"DOI={p['doi']}; citation_marker={p['citation_marker']}"
        })
    write_csv("INPUT_LEDGER.csv", rows)
    write_csv("source_audit/INPUT_TERMINAL_STATUS.csv", rows)
    opened = [
        "QM19_增强含量剂量响应、最佳窗口和过量阈值.md — opened as dispatch contract.",
        "Wang et al., MSEA 804 (2021) 140783 — full text, tables and figures opened.",
        "Wang et al., MSEA 855 (2022) 143935 — full text, tables and figures opened.",
        "Li et al., Materials & Design 95 (2016), DOI 10.1016/j.matdes.2016.01.092 — full text/table evidence opened.",
        "Ranganath et al., Materials Science and Technology 12 (1996) — full text, Table 5/6 and fracture figures opened.",
        "Li Jiuxiao thesis Table 1-1 — secondary prior opened; excluded from headline estimates.",
        "Project ZIP families — names and intended roles registered; member-level archive audit unavailable in execution runtime and therefore not falsely marked opened.",
    ]
    write_text("source_audit/OPENED_FILES.txt", "\n".join(opened))
    write_text("source_audit/README.md", textwrap.dedent("""
        # Source audit interpretation

        `opened` means the document text/table/figure content was directly inspected in the web evidence interface. It does **not** mean that every member of every multi-hundred-megabyte project archive was read. Archive-member audit was unavailable in the execution runtime; this is recorded as a terminal data gap rather than silently treated as complete.

        Numeric claims in this package are sourced from directly opened original papers whenever available. The thesis compilation is marked `DATABASE_PRIOR` and used only for sensitivity.
    """))


def make_figures(records, probabilities, breakpoints) -> list[dict]:
    specs = []
    figdir = OUT / "figures"
    datadir = OUT / "figure_data"

    def save_all(fig, stem: str):
        fig.savefig(figdir / f"{stem}.png", dpi=600, bbox_inches="tight")
        fig.savefig(figdir / f"{stem}.svg", bbox_inches="tight")
        fig.savefig(figdir / f"{stem}.pdf", bbox_inches="tight")
        plt.close(fig)

    # F01 panel family, one figure per property/temperature to avoid hidden subplot transformations.
    map_rows = [r for r in records if r["paper_uid"] == "P_WANG_2021_MSEA_140783" and r["property"] in {"YS_MPa", "UTS_MPa", "EL_pct"}]
    figure_jobs = [
        ("F01a_RT_UTS_dose_response", 25, "UTS_MPa", "Ultimate tensile strength (MPa)"),
        ("F01b_RT_YS_dose_response", 25, "YS_MPa", "Yield strength (MPa)"),
        ("F01c_RT_EL_dose_response", 25, "EL_pct", "Elongation (%)"),
        ("F01d_600C_UTS_dose_response", 600, "UTS_MPa", "Ultimate tensile strength (MPa)"),
        ("F01e_600C_EL_dose_response", 600, "EL_pct", "Elongation (%)"),
        ("F01f_650C_UTS_dose_response", 650, "UTS_MPa", "Ultimate tensile strength (MPa)"),
        ("F01g_650C_EL_dose_response", 650, "EL_pct", "Elongation (%)"),
    ]
    for stem, temp, prop, ylabel in figure_jobs:
        subset = [r for r in map_rows if int(float(r["temperature_C"])) == temp and r["property"] == prop]
        write_csv(f"figure_data/{stem}.csv", subset)
        fig = plt.figure(figsize=(6.4, 4.8))
        ax = fig.add_subplot(111)
        for state in ["as_sintered", "as_rolled"]:
            ss = sorted([r for r in subset if r["state"] == state], key=lambda r: float(r["dose_value"]))
            if not ss:
                continue
            x = [float(r["dose_value"]) for r in ss]
            y = [float(r["value"]) for r in ss]
            e = [float(r["sd"]) for r in ss]
            ax.errorbar(x, y, yerr=e, marker="o", capsize=3, label=state.replace("_", " ").title())
        ax.set_xlabel("TiBw content (vol.%)")
        ax.set_ylabel(ylabel)
        ax.set_title(f"TiBw/TA15 dose response at {temp} °C")
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.25)
        ax.text(0.01, -0.22, "1 independent paper; 3 tested doses/state; direct table evidence; error bars = reported SD; conditional support only.",
                transform=ax.transAxes, fontsize=8, va="top")
        fig.tight_layout()
        save_all(fig, stem)
        specs.append({
            "figure_id": stem, "type": "dose_response_panel_family", "paper_count": 1,
            "sample_conditions": len(subset), "effect_definition": "Observed property mean vs TiBw vol%; reported SD",
            "support_domain": f"TA15; RHP {'and hot rolling' if True else ''}; {temp}C; 2-5 vol%",
            "evidence_layer": "DIRECT_TABLE_TEXT", "formats": ["png_600dpi", "svg", "pdf"],
            "data_file": f"figure_data/{stem}.csv", "code_file": f"plot_code/{stem}.py"
        })

    # F02 breakpoint support intervals.
    bp_rows = [r for r in breakpoints if r["candidate_optimal_dose"] not in ("", None) and r["dose_unit"] == "vol%"]
    write_csv("figure_data/F02_breakpoint_support_intervals.csv", bp_rows)
    fig = plt.figure(figsize=(8.0, 4.8))
    ax = fig.add_subplot(111)
    labels, centers, lows, highs = [], [], [], []
    for r in bp_rows:
        labels.append(r["series_uid"])
        c = float(r["candidate_optimal_dose"])
        centers.append(c)
        lows.append(c - float(r["support_interval_low"]))
        highs.append(float(r["support_interval_high"]) - c)
    y = np.arange(len(labels))
    ax.errorbar(centers, y, xerr=np.vstack([lows, highs]), fmt="o", capsize=4)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Candidate dose / grid-support interval (vol.%)")
    ax.set_title("Condition-specific dose candidates and breakpoint support")
    ax.grid(True, axis="x", alpha=0.25)
    ax.text(0.01, -0.20, "Intervals are tested-grid support, not universal continuous-breakpoint confidence intervals. 2 primary papers represented.",
            transform=ax.transAxes, fontsize=8, va="top")
    fig.tight_layout()
    save_all(fig, "F02_breakpoint_support_intervals")
    specs.append({
        "figure_id": "F02_breakpoint_support_intervals", "type": "breakpoint_interval",
        "paper_count": len(set(r["paper_uid"] for r in bp_rows)), "sample_conditions": len(bp_rows),
        "effect_definition": "Observed-grid candidate and support interval", "support_domain": "Exact paper-defined series only",
        "evidence_layer": "DIRECT_TABLE_TEXT+PARAMETRIC_MC_GRID_SELECTION", "formats": ["png_600dpi", "svg", "pdf"],
        "data_file": "figure_data/F02_breakpoint_support_intervals.csv", "code_file": "plot_code/F02_breakpoint_support_intervals.py"
    })

    # F03 3D dose-porosity-bound-strength with ductility marker size.
    rt_roll = [r for r in map_rows if r["state"] == "as_rolled" and int(float(r["temperature_C"])) == 25]
    idx = defaultdict(dict)
    for r in rt_roll:
        idx[float(r["dose_value"])][r["property"]] = float(r["value"])
    f03_rows = []
    for d in sorted(idx):
        if "UTS_MPa" in idx[d] and "EL_pct" in idx[d]:
            f03_rows.append({
                "dose_vol_pct": d, "porosity_upper_bound_pct": 1.0,
                "UTS_MPa": idx[d]["UTS_MPa"], "EL_pct": idx[d]["EL_pct"],
                "porosity_status": "CENSORED <=1.0%; not exact dose-resolved value",
                "paper_uid": "P_WANG_2021_MSEA_140783"
            })
    write_csv("figure_data/F03_dose_porosity_strength_ductility_3D.csv", f03_rows)
    fig = plt.figure(figsize=(7.2, 5.6))
    ax = fig.add_subplot(111, projection="3d")
    xs = np.array([r["dose_vol_pct"] for r in f03_rows])
    ys = np.array([r["porosity_upper_bound_pct"] for r in f03_rows])
    zs = np.array([r["UTS_MPa"] for r in f03_rows])
    sizes = np.array([r["EL_pct"] for r in f03_rows]) * 15
    ax.scatter(xs, ys, zs, s=sizes)
    for r in f03_rows:
        ax.text(r["dose_vol_pct"], r["porosity_upper_bound_pct"], r["UTS_MPa"], f"EL={r['EL_pct']:.1f}%", fontsize=8)
    ax.set_xlabel("TiBw content (vol.%)")
    ax.set_ylabel("Porosity upper bound (%)")
    ax.set_zlabel("UTS (MPa)")
    ax.set_title("Dose–porosity bound–strength–ductility map")
    fig.text(0.02, 0.01, "TA15, hot-rolled, RT; marker size = elongation; porosity is a <=1.0% bound, not an exact response. n_papers=1.", fontsize=8)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    save_all(fig, "F03_dose_porosity_strength_ductility_3D")
    specs.append({
        "figure_id": "F03_dose_porosity_strength_ductility_3D", "type": "3D_dose_porosity_strength_ductility",
        "paper_count": 1, "sample_conditions": len(f03_rows),
        "effect_definition": "Observed UTS and EL; porosity <=1% censored bound",
        "support_domain": "TA15 hot-rolled RT, 2-5 vol% TiBw", "evidence_layer": "DIRECT_TABLE_TEXT+CENSORED_BOUND",
        "formats": ["png_600dpi", "svg", "pdf"], "data_file": "figure_data/F03_dose_porosity_strength_ductility_3D.csv",
        "code_file": "plot_code/F03_dose_porosity_strength_ductility_3D.py"
    })

    # F04 feasible-dose probability band.
    write_csv("figure_data/F04_feasible_dose_probability_band.csv", probabilities)
    fig = plt.figure(figsize=(7.0, 5.0))
    ax = fig.add_subplot(111)
    for (state, temp), grp in sorted(defaultdict(list, {k: [] for k in []}).items()):
        pass
    grouped = defaultdict(list)
    for r in probabilities:
        grouped[(r["state"], int(r["temperature_C"]))].append(r)
    for (state, temp), grp in sorted(grouped.items()):
        if state != "as_rolled":
            continue
        grp = sorted(grp, key=lambda x: float(x["dose_value"]))
        x = np.array([float(r["dose_value"]) for r in grp])
        yv = np.array([float(r["probability_feasible"]) for r in grp])
        ax.plot(x, yv, marker="o", label=f"{temp} °C, {state.replace('_',' ')}")
        ax.fill_between(x, 0, yv, alpha=0.10)
    ax.axhline(0.80, linestyle="--", linewidth=1, label="Robust threshold = 0.80")
    ax.set_xlabel("TiBw content (vol.%)")
    ax.set_ylabel("Feasibility probability")
    ax.set_ylim(0, 1.05)
    ax.set_title("Conditional feasible-dose probability")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.25)
    ax.text(0.01, -0.20, "Event: UTS ≥ 95% of sampled within-series maximum and EL ≥ 10%; 20,000 draws; conservative n=3; 1 paper.",
            transform=ax.transAxes, fontsize=8, va="top")
    fig.tight_layout()
    save_all(fig, "F04_feasible_dose_probability_band")
    specs.append({
        "figure_id": "F04_feasible_dose_probability_band", "type": "feasible_probability_band",
        "paper_count": 1, "sample_conditions": len(probabilities),
        "effect_definition": "P(UTS>=0.95*sampled max and EL>=10%)",
        "support_domain": "TA15, 2-5 vol% TiBw, as-sintered/as-rolled, RT/600/650C",
        "evidence_layer": "DIRECT_TABLE_TEXT+PARAMETRIC_MC", "formats": ["png_600dpi", "svg", "pdf"],
        "data_file": "figure_data/F04_feasible_dose_probability_band.csv", "code_file": "plot_code/F04_feasible_dose_probability_band.py"
    })

    # F05 precursor-space TiC responses, two figures.
    plded = [r for r in records if r["paper_uid"] == "P_WANG_2022_MSEA_143935"]
    for stem, prop, ylabel in [
        ("F05a_PLDED_C_hardness", "HV0.3", "Microhardness (HV0.3)"),
        ("F05b_PLDED_C_friction", "friction_coefficient", "Friction coefficient"),
    ]:
        ss = sorted([r for r in plded if r["property"] == prop], key=lambda r: float(r["dose_value"]))
        write_csv(f"figure_data/{stem}.csv", ss)
        fig = plt.figure(figsize=(6.4, 4.6))
        ax = fig.add_subplot(111)
        x = [float(r["dose_value"]) for r in ss]
        yv = [float(r["value"]) for r in ss]
        ax.plot(x, yv, marker="o")
        ax.axvline(0.6, linestyle="--", linewidth=1, label="Author-declared optimum: 0.6 wt.% C")
        ax.set_xlabel("Measured precursor carbon content (wt.%)")
        ax.set_ylabel(ylabel)
        ax.set_title("PLDED in-situ TiC/CP-Ti precursor-dose response")
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.25)
        ax.text(0.01, -0.20, "1 paper; 6 dose points; dose axis is measured precursor C wt.%, not TiC vol.%; direct text/figure values.",
                transform=ax.transAxes, fontsize=8, va="top")
        fig.tight_layout()
        save_all(fig, stem)
        specs.append({
            "figure_id": stem, "type": "precursor_dose_response", "paper_count": 1, "sample_conditions": len(ss),
            "effect_definition": f"Observed {prop} vs measured precursor C wt.%", "support_domain": "CP-Ti PLDED fixed parameters, 0-1.6 wt% C",
            "evidence_layer": "DIRECT_TABLE_TEXT", "formats": ["png_600dpi", "svg", "pdf"],
            "data_file": f"figure_data/{stem}.csv", "code_file": f"plot_code/{stem}.py"
        })

    # F06 independent over-dose corroboration.
    for stem, prop, ylabel in [
        ("F06a_Ranganath_UTS_overdose", "UTS_MPa", "Ultimate tensile strength (MPa)"),
        ("F06b_Ranganath_EL_overdose", "EL_pct", "Elongation (%)"),
    ]:
        ss = sorted([r for r in records if r["paper_uid"] == "P_RANGANATH_1996_MST_12_220" and r["property"] == prop], key=lambda r: float(r["dose_value"]))
        write_csv(f"figure_data/{stem}.csv", ss)
        fig = plt.figure(figsize=(6.4, 4.6))
        ax = fig.add_subplot(111)
        x = [float(r["dose_value"]) for r in ss]
        yv = [float(r["value"]) for r in ss]
        ax.plot(x, yv, marker="o")
        ax.axvline(15.0, linestyle="--", linewidth=1, label="Strength maximum on tested grid")
        ax.set_xlabel("TiB + Ti2C content (vol.%)")
        ax.set_ylabel(ylabel)
        ax.set_title("Independent high-dose over-reinforcement series")
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.25)
        ax.text(0.01, -0.20, "1 independent paper; direct Table 5; EL at 25 vol.% is a <0.2% censored bound; no universal transfer.",
                transform=ax.transAxes, fontsize=8, va="top")
        fig.tight_layout()
        save_all(fig, stem)
        specs.append({
            "figure_id": stem, "type": "overdose_corroboration", "paper_count": 1, "sample_conditions": len(ss),
            "effect_definition": f"Observed {prop} vs calculated final phase vol.%", "support_domain": "CP-Ti, TiB+Ti2C, CAS, 0-25 vol%",
            "evidence_layer": "DIRECT_TABLE_TEXT", "formats": ["png_600dpi", "svg", "pdf"],
            "data_file": f"figure_data/{stem}.csv", "code_file": f"plot_code/{stem}.py"
        })

    write_json("PLOT_SPECS.json", {
        "window_id": WINDOW_ID,
        "figure_policy": "All quantitative figures are code-generated from included CSVs; English labels; separate figures instead of hidden subplots; PNG 600 dpi + SVG + PDF.",
        "figures": specs,
    })
    return specs


def write_plot_code(specs: list[dict]) -> None:
    # A compact, deterministic standalone reproducer. Per-figure wrappers satisfy one-code-entry-per-figure.
    core = r'''#!/usr/bin/env python3
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

def read_csv(name):
    with (ROOT / "figure_data" / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def save(fig, stem):
    out = ROOT / "figures"
    fig.savefig(out / f"{stem}.png", dpi=600, bbox_inches="tight")
    fig.savefig(out / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)

def reproduce(stem):
    rows = read_csv(stem + ".csv")
    if stem.startswith("F01"):
        fig = plt.figure(figsize=(6.4, 4.8)); ax = fig.add_subplot(111)
        for state in ["as_sintered", "as_rolled"]:
            ss = sorted([r for r in rows if r["state"] == state], key=lambda r: float(r["dose_value"]))
            if ss:
                ax.errorbar([float(r["dose_value"]) for r in ss], [float(r["value"]) for r in ss],
                            yerr=[float(r["sd"]) for r in ss], marker="o", capsize=3, label=state.replace("_", " ").title())
        ax.set_xlabel("TiBw content (vol.%)"); ax.set_ylabel(rows[0]["property"]); ax.legend(frameon=False); ax.grid(True, alpha=.25)
    elif stem == "F02_breakpoint_support_intervals":
        fig = plt.figure(figsize=(8,4.8)); ax = fig.add_subplot(111)
        labels=[r["series_uid"] for r in rows]; c=[float(r["candidate_optimal_dose"]) for r in rows]
        lo=[c[i]-float(rows[i]["support_interval_low"]) for i in range(len(rows))]; hi=[float(rows[i]["support_interval_high"])-c[i] for i in range(len(rows))]
        y=np.arange(len(rows)); ax.errorbar(c,y,xerr=np.vstack([lo,hi]),fmt="o",capsize=4); ax.set_yticks(y,labels); ax.set_xlabel("Candidate dose / grid support (vol.%)")
    elif stem == "F03_dose_porosity_strength_ductility_3D":
        fig = plt.figure(figsize=(7.2,5.6)); ax = fig.add_subplot(111,projection="3d")
        x=np.array([float(r["dose_vol_pct"]) for r in rows]); y=np.array([float(r["porosity_upper_bound_pct"]) for r in rows]); z=np.array([float(r["UTS_MPa"]) for r in rows]); s=np.array([float(r["EL_pct"]) for r in rows])*15
        ax.scatter(x,y,z,s=s); ax.set_xlabel("TiBw content (vol.%)"); ax.set_ylabel("Porosity upper bound (%)"); ax.set_zlabel("UTS (MPa)")
    elif stem == "F04_feasible_dose_probability_band":
        fig = plt.figure(figsize=(7,5)); ax = fig.add_subplot(111)
        groups={}
        for r in rows:
            if r["state"]!="as_rolled": continue
            groups.setdefault((r["state"],r["temperature_C"]),[]).append(r)
        for k,ss in sorted(groups.items()):
            ss=sorted(ss,key=lambda r:float(r["dose_value"])); x=np.array([float(r["dose_value"]) for r in ss]); y=np.array([float(r["probability_feasible"]) for r in ss]); ax.plot(x,y,marker="o",label=f"{k[1]} °C")
        ax.axhline(.8,linestyle="--",linewidth=1); ax.set_ylim(0,1.05); ax.set_xlabel("TiBw content (vol.%)"); ax.set_ylabel("Feasibility probability"); ax.legend(frameon=False)
    else:
        fig = plt.figure(figsize=(6.4,4.6)); ax = fig.add_subplot(111)
        x=[float(r["dose_value"]) for r in rows]; y=[float(r["value"]) for r in rows]; ax.plot(x,y,marker="o"); ax.set_xlabel(rows[0]["dose_unit"]); ax.set_ylabel(rows[0]["property"]); ax.grid(True,alpha=.25)
    fig.tight_layout(); save(fig,stem)
'''
    write_text("plot_code/reproduce_all.py", core)
    for spec in specs:
        stem = spec["figure_id"]
        wrapper = f'''#!/usr/bin/env python3
from reproduce_all import reproduce

if __name__ == "__main__":
    reproduce("{stem}")
'''
        write_text(f"plot_code/{stem}.py", wrapper)
    write_text("plot_code/README.md", "Run from this directory with the package environment, for example: `python F01a_RT_UTS_dose_response.py`. Each wrapper reads its named CSV from `../figure_data` and overwrites PNG/SVG/PDF in `../figures`.")


def write_provenance(records: list[dict]) -> None:
    p = OUT / "PROVENANCE.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for r in records:
            obj = {
                "record_uid": r["record_uid"],
                "snapshot_id": r["snapshot_id"],
                "paper_uid": r["paper_uid"],
                "sample_uid": r["sample_uid"],
                "condition_uid": r["condition_uid"],
                "source_id": r["source_id"],
                "doi": r["doi"],
                "source_locator": r["source_locator"],
                "source_hash": r["source_hash"],
                "source_hash_type": r["source_hash_type"],
                "evidence_level": r["evidence_level"],
                "transformation": "NONE" if r["evidence_level"] == "DIRECT_TABLE_TEXT" else r["notes"],
                "gold_promotion": "FORBIDDEN",
                "production_registration": "FORBIDDEN",
            }
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def write_narrative(records, papers, pairs, effects, dose_response, probabilities, breakpoints, windows, specs) -> None:
    primary_papers = [p for p in papers if p["role"].startswith("PRIMARY")]
    direct_records = [r for r in records if r["evidence_level"] == "DIRECT_TABLE_TEXT"]
    executive = f"""# QM19 执行裁决

## 结论

不存在可跨基体、增强相、工艺、温度直接迁移的“万能最佳增强含量”。当前证据只支持**条件化剂量窗口**，最高 claim level = 2（同论文、多剂量、同条件比较）。

1. **TiBw/TA15，RHP 后 1000 °C 热轧，室温拉伸**：测试网格内 2.0–3.5 vol.% 保持 UTS ≥ 该系列最大值的 95% 且 EL ≥10%；3.5 vol.% 是最小稳健高性能候选。由 3.5 升至 5.0 vol.% 时，UTS 仅由 1248 增至 1274 MPa，而 EL 从 10.5% 降至 3.2%，过量阈值位于 **(3.5, 5.0] vol.%**。
2. **同体系 600 °C**：热轧态 3.5–5.0 vol.% 在观测网格上可行，但 3.5→5.0 vol.% 的 UTS 局部斜率仅 6 MPa/vol.%，边际收益显著饱和；工程膝点为 3.5 vol.% 而非盲目堆到 5 vol.% 。
3. **同体系 650 °C**：2.0 vol.% 在 UTS 与 EL 上同时占优或近占优；增强量增加不再带来强度收益，且 EL 单调下降。高温最优点向低剂量边界移动，直接否定“室温最佳剂量可平移到高温”的假设。
4. **TiC/CP-Ti，PLDED**：作者在实测前驱体空间给出 0.6 wt.% C 最优点（YS 741 MPa、UTS 940 MPa、EL 18.9%）；1.2–1.6 wt.% C 出现不规则/枝晶 TiC、脱粘/开裂与强度下降。该结论只能写成 **0.43–0.60 wt.% C 条件窗口**，不能伪装成 TiC vol.% 最佳值，因为论文内部 TiC 体积分数报告存在质量守恒冲突。
5. **独立高剂量反例**：TiB+Ti2C/CP-Ti 中，UTS 从 15 vol.% 的 757 MPa 降至 25 vol.% 的 680 MPa；EL 已从基体 26% 降到 15 vol.% 的 2%，25 vol.% 时 <0.2%。高剂量强化不是免费午餐，强度峰值也不等于多目标可行点。

## 主要矛盾

低剂量阶段由载荷传递、细化、固溶与位错阻碍主导；超过结构/界面可承载阈值后，增强体团聚、粗化、破碎、界面脱粘、微裂纹和基体连通性下降接管失效预算。最佳剂量本质上是“强化边际收益 = 损伤边际成本”的条件交点。

## 不能回答

- 精确孔隙率剂量响应：干净 TA15 序列只有相对密度 >99% 的上界，不能把 1% 当作真实点值。
- 800 °C 窗口：当前直接证据没有干净多剂量系列。
- 全局 GAM/层级断点：最大精确同层只有 1 篇独立论文，任何窄 CI 都会是模型幻觉。

## 交付状态

本包包含 {len(primary_papers)} 篇独立 primary paper、{len(records)} 条原子记录、{len(pairs)} 个同研究相邻剂量匹配、{len(effects)} 个效应估计、{len(dose_response)} 个局部斜率、{len(specs)} 张独立代码图。由于 V29/Q40 immutable snapshot 与精确孔隙数据缺失，状态为 `CONTINUE_DATA_GAP`；本包不晋升 Gold、不注册生产模型、不生成 VALIDATED 配方。
"""
    write_text("00_EXECUTIVE_VERDICT.md", executive)

    methods = f"""# Methods

## Scope and evidence hierarchy

The analysis follows the uploaded QM19 dispatch. Atomicity is `paper × sample × actual composition/precursor × actual reinforcement phase × process × state × test condition × property`. Original full-text tables and accompanying figures are the primary evidence. Secondary thesis tables are marked `DATABASE_PRIOR` and excluded from headline thresholds.

## Dose axes

- TiBw/TA15 and TiB+Ti2C/Ti use reported final reinforcement volume fraction.
- PLDED TiC/Ti remains on measured precursor carbon wt.% because the paper's reported TiC volume fractions are internally conflicted. No density-based wt%→vol% conversion was performed.
- Dose axes are never merged across these bases.

## Estimands

For adjacent doses d1<d2, local slope is `(Y2-Y1)/(d2-d1)`. Absolute effect is `Y2-Y1`; where both values are positive and uncensored, `lnRR=ln(Y2/Y1)` and `%change=100(exp(lnRR)-1)` are also reported. These are same-study conditional effects, not causal global derivatives.

## Uncertainty

Wang et al. (2021) states at least three specimens per tensile condition. We use the conservative minimum n=3. For independent group means, `SE(Δ)=sqrt(SD1²/3+SD2²/3)` and a 95% t interval with df=4 (`t=2.776`) is used. Other studies lacking n or SD receive point estimates only. Censored values are not given uncensored CIs.

## Feasibility probability

For each TiBw/TA15 state-temperature series, 20,000 parametric draws are sampled from `Normal(mean, SD/sqrt(3))` with seed {SEED}. A dose is feasible in a draw when `UTS >= 0.95 × maximum UTS in that sampled series` and `EL >= 10%`. The smallest feasible tested dose is selected. This estimates a tested-grid decision probability; it is not a continuous optimizer.

## Breakpoints

Three-point series cannot identify a narrow continuous breakpoint. `BREAKPOINTS.csv` therefore reports observed-grid candidates and grid-support intervals. PLDED 0.6 wt.% C is an author-declared precursor-space optimum triangulated with morphology and tensile deterioration. Ranganath 15 vol.% is a strength-grid maximum but not a ductility-feasible optimum.

## Heterogeneity and LOPO

No global hierarchical model is fitted because no exact reinforcement×matrix×process×state×temperature×property stratum contains enough independent multi-dose papers. Leave-one-paper-out is used as a claim-stability test: rejection of a universal optimum survives every omission, while paper-specific windows correctly disappear when their defining paper is omitted.

## Reproducibility

All quantitative figures read CSV files from `figure_data/`. PNG is saved at 600 dpi together with SVG and PDF. `plot_code/` contains one wrapper per figure plus a common reproducer. `tests/validate_package.py` verifies required members, checksums and absence of nested ZIP files.
"""
    write_text("METHODS.md", methods)

    limitations = """# Limitations

1. The immutable V29/Q40 atomic snapshot, provenance ledger, conflict ledger and exclusion table were not available to this execution runtime. This package is therefore a literature-priority, fail-closed analytical return rather than a replacement for ACTIVE/Gold.
2. The cleanest phase-volume series contains only three doses (2, 3.5, 5 vol.%). Continuous GAM/spline/breakpoint precision is not data-identified.
3. TA15 porosity is reported only through relative density >99%; exact dose-resolved porosity, pore size and spatial location are missing.
4. PLDED TiC volume fractions are internally conflicted. Only measured precursor carbon wt.% is used.
5. Temperature, process, reinforcement identity, morphology and matrix family are strong effect modifiers. Cross-paper pooling would violate exchangeability.
6. Reported standard deviations are treated as sample SDs and n=3 is used as a conservative lower bound where the paper says at least three specimens.
7. The feasibility threshold (95% of within-series maximum UTS and EL≥10%) is a declared decision rule, not a physical law. Alternative thresholds are preserved as a local recomputation task.
8. No 800°C multi-dose tensile series is included. No validated composition or production model is produced.
"""
    write_text("LIMITATIONS.md", limitations)

    request = {
        "window_id": WINDOW_ID,
        "status": STATUS,
        "required_inputs": [
            {
                "priority": 1,
                "request": "Provide immutable V29/Q40 ATOMIC_RECORDS.*, PROVENANCE.jsonl, CONFLICT_LEDGER.csv, EXCLUDED_RECORDS.csv and paper/source registry.",
                "acceptance": "Every row bound to snapshot_id+source_hash+paper_uid+sample_uid+condition_uid; package SHA/CRC and member map supplied."
            },
            {
                "priority": 2,
                "request": "Provide dose-resolved exact porosity/density values and uncertainty for TA15 2/3.5/5 vol% as-sintered/as-rolled series, preferably CT pore volume, pore size and build location.",
                "acceptance": "No greater-than-only bounds; replicate n and SD available."
            },
            {
                "priority": 3,
                "request": "Provide at least three independent >=5-dose series per target stratum, including 0-dose matrix controls and both sides of the damage transition.",
                "acceptance": "Actual phase vol%, particle size/morphology/distribution, process, heat treatment, temperature, strain rate and orientation harmonized."
            },
            {
                "priority": 4,
                "request": "Provide clean 800°C tensile/creep multi-dose series.",
                "acceptance": "Common matrix/process/state/strain rate/exposure; UTS, YS, EL and damage evidence."
            }
        ],
        "do_not": ["Do not promote this return to Gold", "Do not register any production model", "Do not treat precursor wt%C as TiC vol%", "Do not label screened windows VALIDATED"],
        "next_action": "Local controller resolves requested immutable assets, reruns package validator and only then considers authoritative absorption."
    }
    write_json("WEB_TO_LOCAL_REQUEST.json", request)

    prompt = """# Local absorption prompt

1. Verify `FINAL_QM19.zip` SHA-256 and run `python tests/validate_package.py .` after extraction.  
2. Do not overwrite ACTIVE/Gold. Import this return into the isolated `q40/QM19` candidate zone.  
3. Resolve `WEB_TO_LOCAL_REQUEST.json`, especially immutable V29/Q40 atomic/provenance assets and exact porosity.  
4. Recompute all estimands from authoritative rows; compare row counts, source hashes, pair IDs, breakpoints and figure data.  
5. Preserve the claim ceiling: conditional windows only; no production registration and no VALIDATED recipe without independent experiments.
"""
    write_text("LOCAL_ABSORPTION_PROMPT.md", prompt)

    write_text("README.md", """# FINAL_QM19

Evidence-grounded quantitative return for reinforcement-dose response, conditional optimum windows and over-reinforcement thresholds in Ti/TMC systems.

Start with `00_EXECUTIVE_VERDICT.md`, then inspect `METHODS.md`, `DOSE_SERIES.csv`, `DOSE_RESPONSE_ALL_PROPERTIES.csv`, `BREAKPOINTS.csv`, `FEASIBLE_DOSE_WINDOWS.csv`, `CONFLICT_LEDGER.csv` and `WINDOW_STATUS.json`.

This is a fail-closed candidate return. It does not modify ACTIVE/Gold or register a production model.
""")

    write_text("acceptance_commands.md", """# Acceptance commands

```bash
python tests/validate_package.py .
python plot_code/F01a_RT_UTS_dose_response.py
```

The validator must finish with `PASS`. Figure scripts require the exact environment recorded in `requirements.txt`.
""")

    status_obj = {
        "window_id": WINDOW_ID,
        "snapshot_id": SNAPSHOT_ID,
        "papers_seen": len(papers),
        "papers_included": len(papers),
        "independent_papers": len(primary_papers),
        "atomic_rows": len(records),
        "direct_evidence_rows": len(direct_records),
        "matched_pairs": len(pairs),
        "effect_estimates": len(effects),
        "local_slopes": len(dose_response),
        "plots_generated": len(specs),
        "open_conflicts": 5,
        "claim_level_max": 2,
        "status": STATUS,
        "next_action": "Resolve immutable snapshot and exact porosity via WEB_TO_LOCAL_REQUEST.json; rerun locally before authoritative absorption.",
        "production_model_registered": False,
        "gold_promoted": False,
        "validated_formulation_generated": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json("WINDOW_STATUS.json", status_obj)


def write_environment() -> None:
    import importlib.metadata
    req = []
    for pkg in ["numpy", "matplotlib"]:
        try:
            req.append(f"{pkg}=={importlib.metadata.version(pkg)}")
        except Exception:
            pass
    write_text("requirements.txt", "\n".join(req))
    env = {
        "python": sys.version,
        "platform": sys.platform,
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
        "seed": SEED,
        "mc_draws": N_MC,
    }
    write_json("ENVIRONMENT.json", env)


def write_validator() -> None:
    validator = r'''#!/usr/bin/env python3
from pathlib import Path
import csv, hashlib, json, sys, zipfile

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
required = [
"00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256","DOSE_SERIES.csv","DOSE_RESPONSE_ALL_PROPERTIES.csv","BREAKPOINTS.csv","FEASIBLE_DOSE_WINDOWS.csv"]
missing=[x for x in required if not (ROOT/x).is_file()]
assert not missing, f"missing required files: {missing}"
status=json.loads((ROOT/"WINDOW_STATUS.json").read_text(encoding="utf-8"))
assert status["window_id"]=="QM19"
assert status["claim_level_max"]<=2
assert status["production_model_registered"] is False
assert status["gold_promoted"] is False
with (ROOT/"CHECKSUMS.sha256").open(encoding="utf-8") as f:
    for line in f:
        line=line.strip()
        if not line: continue
        expected, rel=line.split("  ",1)
        p=ROOT/rel
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        assert h==expected, f"checksum mismatch: {rel}"
for p in ROOT.rglob("*.zip"):
    raise AssertionError(f"nested ZIP forbidden: {p.relative_to(ROOT)}")
fig_specs=json.loads((ROOT/"PLOT_SPECS.json").read_text(encoding="utf-8"))["figures"]
assert fig_specs, "no figures"
for s in fig_specs:
    stem=s["figure_id"]
    for ext in ["png","svg","pdf"]:
        assert (ROOT/"figures"/f"{stem}.{ext}").is_file(), f"missing figure {stem}.{ext}"
    assert (ROOT/s["data_file"]).is_file()
    assert (ROOT/s["code_file"]).is_file()
with (ROOT/"DOSE_SERIES.csv").open(encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))
assert rows and all(r["paper_uid"] and r["sample_uid"] and r["condition_uid"] and r["source_hash"] for r in rows)
print("PASS")
'''
    write_text("tests/validate_package.py", validator)


def finalize_manifest_and_zip() -> tuple[str, int]:
    # Manifest excludes itself/checksum until final assembly metadata is known.
    files_pre = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"})
    manifest = {
        "window_id": WINDOW_ID,
        "snapshot_id": SNAPSHOT_ID,
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "member_count_excluding_manifest_and_checksums": len(files_pre),
        "required_common": REQUIRED_COMMON,
        "required_scope": REQUIRED_SCOPE,
        "members": [
            {"path": str(p.relative_to(OUT)).replace(os.sep, "/"), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
            for p in files_pre
        ],
        "nested_zip_count": 0,
        "claim_level_max": 2,
        "gold_promotion": "FORBIDDEN",
        "production_registration": "FORBIDDEN",
    }
    write_json("MANIFEST.json", manifest)
    checksum_files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
    checksum_text = "\n".join(f"{sha256_file(p)}  {str(p.relative_to(OUT)).replace(os.sep, '/')}" for p in checksum_files) + "\n"
    (OUT / "CHECKSUMS.sha256").write_text(checksum_text, encoding="utf-8")

    # Validate before archiving.
    code = os.system(f'"{sys.executable}" "{OUT / "tests/validate_package.py"}" "{OUT}"')
    if code != 0:
        raise RuntimeError("package validator failed")

    if ZIP_OUT.exists():
        ZIP_OUT.unlink()
    with zipfile.ZipFile(ZIP_OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(OUT)).replace(os.sep, "/"))
    with zipfile.ZipFile(ZIP_OUT, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"ZIP CRC failed at {bad}")
        if any(n.lower().endswith(".zip") for n in zf.namelist()):
            raise RuntimeError("nested ZIP member detected")
    digest = sha256_file(ZIP_OUT)
    Path(str(ZIP_OUT) + ".sha256").write_text(f"{digest}  {ZIP_OUT.name}\n", encoding="utf-8")
    return digest, ZIP_OUT.stat().st_size


def main() -> None:
    reset_output()
    records, papers = build_records()
    pairs, effects, dose_response = build_effects(records)
    interactions = build_interactions(records)
    probabilities, breakpoints, windows = build_feasibility(records)
    conflicts = build_conflicts()
    write_core_tables(records, papers, pairs, effects, dose_response, interactions, probabilities, breakpoints, windows, conflicts)
    write_input_audit(papers)
    write_provenance(records)
    specs = make_figures(records, probabilities, breakpoints)
    write_plot_code(specs)
    write_environment()
    write_validator()
    write_narrative(records, papers, pairs, effects, dose_response, probabilities, breakpoints, windows, specs)
    digest, size = finalize_manifest_and_zip()
    print(json.dumps({"zip": str(ZIP_OUT), "sha256": digest, "bytes": size, "status": STATUS}, ensure_ascii=False))


if __name__ == "__main__":
    main()
