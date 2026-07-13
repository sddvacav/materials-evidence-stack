#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import runpy
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM27"
ZIP_PATH = ROOT / "FINAL_QM27.zip"
ZIP_SHA_PATH = ROOT / "FINAL_QM27.sha256"
SUMMARY_PATH = ROOT / "DELIVERY_SUMMARY.json"
GENERATED_AT = "2026-07-13T05:00:00Z"
WINDOW_ID = "QM27"
STATUS = "CONTINUE_DATA_GAP"

if OUT.exists():
    shutil.rmtree(OUT)
if ZIP_PATH.exists():
    ZIP_PATH.unlink()
for d in [OUT, OUT / "figure_data", OUT / "plot_code", OUT / "figures", OUT / "analysis_code"]:
    d.mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def identity_fp(identifier: str, title: str) -> str:
    return sha256_text(f"IDENTITY|{identifier}|{title}")


def write_text(rel: str, text: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(rel: str, obj: Any) -> None:
    write_text(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def write_csv(rel: str, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            raise ValueError(f"fieldnames required for empty CSV: {rel}")
        fieldnames = list(rows[0].keys())
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def fnum(x: float | None, nd: int = 6) -> str:
    if x is None:
        return ""
    return f"{x:.{nd}f}".rstrip("0").rstrip(".")


SOURCES = {
    "ZHAI2016": {
        "paper_uid": "doi:10.1016/j.ijfatigue.2016.08.009",
        "doi": "10.1016/j.ijfatigue.2016.08.009",
        "title": "Fatigue crack growth behavior and microstructural mechanisms in Ti-6Al-4V manufactured by laser engineered net shaping",
        "year": 2016,
        "source_pointer": "file_library:turn6file0",
        "source_type": "P0_PRIMARY_ORIGINAL",
    },
    "LIN2016": {
        "paper_uid": "doi:10.1016/j.matdes.2016.04.018",
        "doi": "10.1016/j.matdes.2016.04.018",
        "title": "Microstructural evolution and mechanical properties of Ti-6Al-4V wall deposited by pulsed plasma arc additive manufacturing",
        "year": 2016,
        "source_pointer": "file_library:turn6file1",
        "source_type": "P0_PRIMARY_ORIGINAL",
    },
    "TRAN2017": {
        "paper_uid": "doi:10.1016/j.matdes.2017.04.092",
        "doi": "10.1016/j.matdes.2017.04.092",
        "title": "3D thermal finite element analysis of laser cladding processed Ti-6Al-4V part with microstructural correlations",
        "year": 2017,
        "source_pointer": "file_library:turn8file0",
        "source_type": "P0_PRIMARY_ORIGINAL",
    },
    "SYED2021": {
        "paper_uid": "doi:10.1016/j.msea.2021.141194",
        "doi": "10.1016/j.msea.2021.141194",
        "title": "Effect of deposition strategies on fatigue crack growth behaviour of wire + arc additive manufactured titanium alloy Ti-6Al-4V",
        "year": 2021,
        "source_pointer": "file_library:turn9file7",
        "source_type": "P0_PRIMARY_ORIGINAL",
    },
    "CAO2023": {
        "paper_uid": "doi:10.1038/s41524-023-01152-y",
        "doi": "10.1038/s41524-023-01152-y",
        "title": "A machine learning method to quantitatively predict alpha phase morphology in additively manufactured Ti-6Al-4V",
        "year": 2023,
        "source_pointer": "file_library:turn7file3",
        "source_type": "P0_PRIMARY_ORIGINAL_METHOD_CONTEXT",
    },
    "ZAREI2025": {
        "paper_uid": "doi:10.1016/j.jmrt.2025.05.106",
        "doi": "10.1016/j.jmrt.2025.05.106",
        "title": "Microstructural heterogeneity and anisotropic mechanical properties of titanium alloys manufactured by wire arc additive manufacturing: A review",
        "year": 2025,
        "source_pointer": "file_library:turn6file2",
        "source_type": "P3_REVIEW_SOURCE_LOCATOR",
    },
    "CCTSUPP": {
        "paper_uid": "doi:10.1016/j.ijfatigue.2019.105358:supplement",
        "doi": "10.1016/j.ijfatigue.2019.105358",
        "title": "Supplementary continuous-cooling-transformation evidence for Ti-6Al-4V",
        "year": 2019,
        "source_pointer": "file_library:turn7file15",
        "source_type": "P0B_SAME_WORK_SUPPLEMENT",
    },
    "FIGEVIDENCE": {
        "paper_uid": "project:figure_evidence_jsonl",
        "doi": "",
        "title": "Project figure evidence registry entries for thermal simulations and GxR plots",
        "year": 2026,
        "source_pointer": "file_library:turn7file11;turn7file16",
        "source_type": "P1_PROVENANCED_STRUCTURED",
    },
}
for s in SOURCES.values():
    s["source_hash"] = identity_fp(s["doi"] or s["paper_uid"], s["title"])
    s["hash_scope"] = "IDENTITY_FINGERPRINT_NOT_RAW_FILE_SHA"

snapshot_payload = {
    "window": WINDOW_ID,
    "dispatch": "V30_TITMC_Q40_20260713",
    "sources": sorted((k, v["source_hash"]) for k, v in SOURCES.items()),
    "frozen_numeric_anchors": {
        "zhai_table1": [330, 780, 1.0, 2.0, 0.3, 0.4, 0.5, 1.0, 0.6, 0.8],
        "zhai_table2": [1005, 1103, 4, 360, 1000, 1073, 9, 330, 990, 1042, 7, 325, 991, 1044, 10, 320, 970, 1030, 16, 320],
        "zhai_lath": [0.73, 0.11, 0.86, 0.22, 0.79, 0.16, 1.06, 0.21],
        "lin_macro": [1.40, 0.40, 2.00, 0.66, 3.43, 2.58, 0.86, 6.90, 278],
        "lin_tensile": [909, 13.6, 988, 19.2, 7.5, 0.5],
        "tran_sensor": [1074, 400, 28, 2100, 7, 10, 42.5, 1053, 973, 0.35],
    },
}
SNAPSHOT_ID = "QM27_DERIVED_" + sha256_text(json.dumps(snapshot_payload, sort_keys=True, separators=(",", ":")))[:20]

# ---------------------------------------------------------------------------
# Input ledger: every visible top-level package receives a terminal state.
# ---------------------------------------------------------------------------
archive_names = [
    "00_统一上传总控与校验信息_20260712.zip",
    "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
] + [f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 9)] + [
    "S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip",
    "S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip",
    "S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip",
    "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
] + [f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1, 11)]

input_ledger: list[dict[str, Any]] = []
input_fields = [
    "input_uid", "input_name", "category", "priority", "availability", "terminal_state",
    "actual_use", "source_hash", "hash_scope", "snapshot_id", "reason_or_gap", "member_audit"
]
input_ledger.append({
    "input_uid": "dispatch_qm27",
    "input_name": "QM27_冷却速率、热循环、层间温度和构建位置的隐变量重建.md",
    "category": "dispatch_contract",
    "priority": 0,
    "availability": "DIRECT_UPLOAD_REFERENCE",
    "terminal_state": "USED_DIRECTLY",
    "actual_use": "scope, estimands, schemas, figures, claim ceiling, status contract",
    "source_hash": identity_fp("QM27", "QM27 dispatch contract"),
    "hash_scope": "IDENTITY_FINGERPRINT_NOT_RAW_FILE_SHA",
    "snapshot_id": SNAPSHOT_ID,
    "reason_or_gap": "Raw file SHA unavailable to GitHub fallback runtime; content was fully supplied to the execution window.",
    "member_audit": "not_applicable_single_markdown",
})
for idx, name in enumerate(archive_names, start=1):
    if name.startswith("TITMC_V27_LIT_WEB"):
        category = "primary_literature_archive"
        use = "Registered; file-library-exposed primary originals from this literature plane were read directly."
        state = "USED_AS_REFERENCE_WITH_MEMBER_AUDIT_GAP"
    elif name.startswith("S03_CODEX_ML_DATA_FEATURES"):
        category = "frozen_data_features"
        use = "Required authoritative frozen matrices registered; unavailable for member-level inspection in current artifact runtime."
        state = "BLOCKED_RUNTIME_MEMBER_AUDIT"
    elif name.startswith("S03_CODEX_ML_HARNESS"):
        category = "harness_evidence"
        use = "Registered for UQ/AD/provenance compatibility; unavailable for member-level inspection in current artifact runtime."
        state = "BLOCKED_RUNTIME_MEMBER_AUDIT"
    elif name.startswith("S04"):
        category = "engineering_code_history"
        use = "Registered; not used to manufacture scientific values."
        state = "NOT_RELEVANT_TO_SCIENTIFIC_ESTIMAND"
    elif name.startswith("S02"):
        category = "platform_return_plot_code"
        use = "Registered as engineering reference; artifact uses isolated deterministic plotting scripts."
        state = "USED_AS_REFERENCE"
    else:
        category = "control_validation"
        use = "Registered as upload/control source; member-level audit unavailable."
        state = "USED_AS_REFERENCE_WITH_MEMBER_AUDIT_GAP"
    input_ledger.append({
        "input_uid": f"archive_{idx:02d}",
        "input_name": name,
        "category": category,
        "priority": 1 if category in {"primary_literature_archive", "frozen_data_features", "harness_evidence"} else 2,
        "availability": "TOP_LEVEL_PATH_DECLARED",
        "terminal_state": state,
        "actual_use": use,
        "source_hash": "",
        "hash_scope": "RAW_ARCHIVE_SHA_NOT_AVAILABLE_IN_FALLBACK_RUNTIME",
        "snapshot_id": SNAPSHOT_ID,
        "reason_or_gap": "Local container session was unavailable; no ZIP member or CRC claim is made.",
        "member_audit": "NOT_EXECUTED_DO_NOT_INFER_PASS",
    })
for key, s in SOURCES.items():
    input_ledger.append({
        "input_uid": f"source_{key.lower()}",
        "input_name": s["title"],
        "category": "paper_or_structured_evidence",
        "priority": 1 if s["source_type"].startswith("P0") else 2,
        "availability": "OPENED_MULTIMODALLY_OR_PARSED",
        "terminal_state": "USED_DIRECTLY" if s["source_type"].startswith("P0") or s["source_type"].startswith("P1") else "USED_AS_REFERENCE",
        "actual_use": "numeric extraction and/or source navigation with evidence-level restrictions",
        "source_hash": s["source_hash"],
        "hash_scope": s["hash_scope"],
        "snapshot_id": SNAPSHOT_ID,
        "reason_or_gap": s["source_pointer"],
        "member_audit": "full document pages opened where available; exact raw-file SHA unavailable",
    })
write_csv("INPUT_LEDGER.csv", input_ledger, input_fields)

# ---------------------------------------------------------------------------
# Atomic cohort.
# ---------------------------------------------------------------------------
cohort_fields = [
    "record_uid", "snapshot_id", "source_hash", "hash_scope", "paper_uid", "sample_uid", "condition_uid",
    "matrix", "process", "thermal_measurement_level", "thermal_proxy_type", "thermal_proxy_value",
    "thermal_proxy_unit", "build_position", "cycle_count", "heat_treatment", "test_mode", "test_temperature_C",
    "orientation", "property_name", "value", "value_lower", "value_upper", "unit", "sd", "censoring",
    "evidence_level", "source_locator", "comparison_role", "calibration_domain", "independent_paper", "notes"
]
cohort: list[dict[str, Any]] = []


def add_record(source_key: str, sample: str, condition: str, property_name: str, value: Any, unit: str,
               *, process: str, thermal_level: str, proxy_type: str = "", proxy_value: Any = "", proxy_unit: str = "",
               build_position: str = "", cycle_count: Any = "", ht: str = "as-built", test_mode: str = "",
               temp_c: Any = "", orientation: str = "", sd: Any = "", lower: Any = "", upper: Any = "",
               censoring: str = "none", evidence: str = "DIRECT_TABLE_TEXT", locator: str = "",
               role: str = "analysis", domain: str = "", notes: str = "") -> str:
    s = SOURCES[source_key]
    uid_seed = f"{s['paper_uid']}|{sample}|{condition}|{property_name}|{value}|{unit}"
    uid = "rec_" + sha256_text(uid_seed)[:16]
    cohort.append({
        "record_uid": uid, "snapshot_id": SNAPSHOT_ID, "source_hash": s["source_hash"], "hash_scope": s["hash_scope"],
        "paper_uid": s["paper_uid"], "sample_uid": sample, "condition_uid": condition, "matrix": "Ti-6Al-4V",
        "process": process, "thermal_measurement_level": thermal_level, "thermal_proxy_type": proxy_type,
        "thermal_proxy_value": proxy_value, "thermal_proxy_unit": proxy_unit, "build_position": build_position,
        "cycle_count": cycle_count, "heat_treatment": ht, "test_mode": test_mode, "test_temperature_C": temp_c,
        "orientation": orientation, "property_name": property_name, "value": value, "value_lower": lower,
        "value_upper": upper, "unit": unit, "sd": sd, "censoring": censoring, "evidence_level": evidence,
        "source_locator": locator, "comparison_role": role, "calibration_domain": domain,
        "independent_paper": "1", "notes": notes,
    })
    return uid

# Zhai et al. Table 2 records.
zhai_vals = {
    "LPAF": (1005, 1103, 4, 360, "low-power as-fabricated"),
    "LPHT": (1000, 1073, 9, 330, "low-power heat-treated"),
    "HPAF": (990, 1042, 7, 325, "high-power as-fabricated"),
    "HPHT": (991, 1044, 10, 320, "high-power heat-treated"),
    "SUB": (970, 1030, 16, 320, "mill-annealed substrate"),
}
zhai_records: dict[tuple[str, str], str] = {}
for cond, (ys, uts, el, hv, label) in zhai_vals.items():
    if cond.startswith("LP"):
        proxy, pval = "line_energy", 33.0
        domain = "Optomec LENS 850-R; 330 W; 0.6 m/min; 1.0 g/min; 0.3 mm layer; 0.5 mm hatch"
    elif cond.startswith("HP"):
        proxy, pval = "line_energy", 58.5
        domain = "Optomec LENS 850-R; 780 W; 0.8 m/min; 2.0 g/min; 0.4 mm layer; 1.0 mm hatch"
    else:
        proxy, pval = "", ""
        domain = "mill-annealed Ti-6Al-4V plate"
    ht = "760 C 1 h vacuum + air cool" if cond.endswith("HT") else ("mill-annealed" if cond == "SUB" else "as-built")
    for prop, val, unit in [("YS", ys, "MPa"), ("UTS", uts, "MPa"), ("EL", el, "%"), ("microhardness", hv, "HV")]:
        uid = add_record("ZHAI2016", f"ZHAI_{cond}", cond, prop, val, unit, process="LENS" if cond != "SUB" else "wrought substrate",
                         thermal_level="PROCESS_PROXY" if cond != "SUB" else "REFERENCE_MATERIAL",
                         proxy_type=proxy, proxy_value=pval, proxy_unit="J/mm" if proxy else "", ht=ht,
                         test_mode="tension" if prop != "microhardness" else "Vickers 1.96 N 10 s",
                         temp_c=25, orientation="reported build extraction; tensile orientation not isolated in Table 2",
                         locator="Table 2, article page 55", domain=domain,
                         notes=f"{label}; reported table value; no replicate count supplied in table")
        zhai_records[(cond, prop)] = uid

# Zhai local layer/micro-HAZ microstructure.
zhai_records[("LP_LAYER", "alpha_lath_thickness")] = add_record(
    "ZHAI2016", "ZHAI_LP_AF_LOCAL", "LP_WITHIN_LAYER", "alpha_prime_lath_thickness", 0.73, "um",
    process="LENS", thermal_level="LOCAL_REHEAT_POSITION_PROXY", proxy_type="micro_HAZ_position", proxy_value=0,
    proxy_unit="binary", build_position="within one deposited layer", ht="as-built", sd=0.11, upper=0.73,
    censoring="upper_bound", evidence="FIGURE_DERIVED", locator="Fig. 7a and text, article pages 55/59",
    domain="Optomec LENS 850-R low-power condition", notes="Text states less than 0.73 um; 0.73 is used only as conservative upper bound."
)
zhai_records[("LP_HAZ", "alpha_lath_thickness")] = add_record(
    "ZHAI2016", "ZHAI_LP_AF_LOCAL", "LP_MICRO_HAZ", "alpha_prime_lath_thickness", 0.86, "um",
    process="LENS", thermal_level="LOCAL_REHEAT_POSITION_PROXY", proxy_type="micro_HAZ_position", proxy_value=1,
    proxy_unit="binary", build_position="interlayer micro-HAZ", ht="as-built", sd=0.22,
    evidence="FIGURE_DERIVED", locator="Fig. 7c and text, article pages 55/59",
    domain="Optomec LENS 850-R low-power condition", notes="Coarsening attributed to partial remelting/reheating."
)
zhai_records[("HP_LAYER", "alpha_lath_thickness")] = add_record(
    "ZHAI2016", "ZHAI_HP_AF_LOCAL", "HP_WITHIN_LAYER", "alpha_lath_thickness", 0.79, "um",
    process="LENS", thermal_level="LOCAL_REHEAT_POSITION_PROXY", proxy_type="micro_HAZ_position", proxy_value=0,
    proxy_unit="binary", build_position="within one deposited layer", ht="as-built", sd=0.16,
    evidence="FIGURE_DERIVED", locator="Fig. 7b and text, article pages 55/59",
    domain="Optomec LENS 850-R high-power condition", notes="Within-layer alpha lath."
)
zhai_records[("HP_HAZ", "alpha_lath_thickness")] = add_record(
    "ZHAI2016", "ZHAI_HP_AF_LOCAL", "HP_MICRO_HAZ", "alpha_lath_thickness", 1.06, "um",
    process="LENS", thermal_level="LOCAL_REHEAT_POSITION_PROXY", proxy_type="micro_HAZ_position", proxy_value=1,
    proxy_unit="binary", build_position="interlayer micro-HAZ", ht="as-built", sd=0.21,
    evidence="FIGURE_DERIVED", locator="Fig. 7d and text, article pages 55/59",
    domain="Optomec LENS 850-R high-power condition", notes="Coarsening attributed to partial remelting/reheating."
)

# Lin et al. process, build position, cycles, and properties.
lin_records: dict[str, str] = {}
lin_records["band_spacing"] = add_record(
    "LIN2016", "LIN_16L_WALL", "PPAM_WALL_LAYER_BANDS", "layer_band_spacing", 1.40, "mm",
    process="wire-feed PPAM", thermal_level="OBSERVABLE_THERMAL_PROXY", proxy_type="layer_band_spacing",
    proxy_value=1.40, proxy_unit="mm", build_position="whole wall", cycle_count="multiple", sd=0.40,
    lower=0.87, upper=2.13, evidence="DIRECT_TABLE_TEXT", locator="Table 3, article page 9",
    domain="16-layer PPAM wall; delta-Z=1.5 mm; prior layer below 300 C before deposition",
    notes="Compared with programmed layer increment 1.5 mm only within this equipment/process domain."
)
lin_records["beta_length_mean"] = add_record(
    "LIN2016", "LIN_16L_WALL", "PPAM_WALL_BETA_GRAINS", "prior_beta_grain_length", 3.43, "mm",
    process="wire-feed PPAM", thermal_level="BUILD_POSITION_PROXY", proxy_type="normalized_build_height",
    proxy_value="0-1", proxy_unit="normalized", build_position="whole wall", cycle_count=16, sd=2.58,
    lower=0.86, upper=6.90, evidence="DIRECT_TABLE_TEXT", locator="Table 3 and Sec. 3.1, article pages 8-9",
    domain="16-layer PPAM wall", notes="Min was reported in bottom region and max in top region; extremes are not regional means."
)
lin_records["beta_bottom_min"] = add_record(
    "LIN2016", "LIN_16L_WALL", "PPAM_BOTTOM_EXTREME", "prior_beta_grain_length_extreme", 0.86, "mm",
    process="wire-feed PPAM", thermal_level="BUILD_POSITION_PROXY", proxy_type="normalized_build_height",
    proxy_value=0, proxy_unit="normalized", build_position="bottom region", cycle_count=16,
    evidence="DIRECT_TABLE_TEXT", locator="Sec. 3.1 and Table 3, article pages 8-9",
    domain="16-layer PPAM wall", notes="Observed minimum, not bottom-region mean."
)
lin_records["beta_top_max"] = add_record(
    "LIN2016", "LIN_16L_WALL", "PPAM_TOP_EXTREME", "prior_beta_grain_length_extreme", 6.90, "mm",
    process="wire-feed PPAM", thermal_level="BUILD_POSITION_PROXY", proxy_type="normalized_build_height",
    proxy_value=1, proxy_unit="normalized", build_position="top region", cycle_count=16,
    evidence="DIRECT_TABLE_TEXT", locator="Sec. 3.1 and Table 3, article pages 8-9",
    domain="16-layer PPAM wall", notes="Observed maximum, not top-region mean."
)
for layers, present, height in [(1, 0, 1.7), (3, 0, 3.7), (4, 1, 6.4)]:
    lin_records[f"band_{layers}"] = add_record(
        "LIN2016", f"LIN_{layers}L_BUILD", f"PPAM_{layers}_LAYERS", "layer_band_present", present, "binary",
        process="wire-feed PPAM", thermal_level="CYCLE_COUNT_PROXY", proxy_type="total_deposited_layers",
        proxy_value=layers, proxy_unit="layers", build_position=f"separate {layers}-layer coupon; height {height} mm",
        cycle_count=layers, evidence="DIRECT_TEXT_FIGURE", locator="Fig. 10 and discussion, article pages 17-19",
        domain="PPAM layer-count sub-experiments", notes="Band absent through three layers and visible after the fourth layer."
    )
lin_records["top_three_no_bands"] = add_record(
    "LIN2016", "LIN_16L_WALL", "PPAM_LAST_3_LAYERS", "layer_band_present", 0, "binary",
    process="wire-feed PPAM", thermal_level="SUBSEQUENT_CYCLE_PROXY", proxy_type="future_reheat_count",
    proxy_value="low/zero", proxy_unit="ordinal", build_position="top three layers; reported height 6.28 mm", cycle_count=16,
    evidence="DIRECT_TEXT_FIGURE", locator="Fig. 3 and Sec. 3.1, article pages 8-9",
    domain="16-layer PPAM wall", notes="Final layers lacked later reheating sufficient to reveal layer bands."
)
for prop, val, sd, unit in [("YS", 909, 13.6, "MPa"), ("UTS", 988, 19.2, "MPa"), ("EL", 7.5, 0.5, "%")]:
    lin_records[prop] = add_record(
        "LIN2016", "LIN_16L_WALL_TENSILE", "PPAM_AS_BUILT", prop, val, unit,
        process="wire-feed PPAM", thermal_level="CONTROLLED_INTERPASS_AND_LAYERWISE_HEAT_INPUT",
        proxy_type="interpass_temperature_ceiling", proxy_value=300, proxy_unit="C", build_position="reported tensile extraction direction",
        cycle_count=16, ht="as-built", test_mode="tension", temp_c=25, orientation="deposition direction",
        sd=sd, evidence="DIRECT_TABLE_TEXT", locator="Table 5 and Sec. 3.3.2, article pages 15-16",
        domain="16-layer PPAM; 70 Hz; 0.25 m/min; 3.5 m/min wire feed",
        notes="Wall-average property; does not isolate build height."
    )
lin_records["fine_lath_mid"] = add_record(
    "LIN2016", "LIN_MIDDLE_LB", "PPAM_FINE_WIDMANSTATTEN", "alpha_lamella_range_midpoint", 0.40, "um",
    process="wire-feed PPAM", thermal_level="LOCAL_BAND_POSITION_PROXY", proxy_type="microstructure_region",
    proxy_value="fine_Widmanstatten", build_position="middle wall / layer-band neighborhood", cycle_count="multiple",
    lower=0.28, upper=0.52, evidence="DIRECT_TABLE_TEXT", locator="Table 4 and Fig. 4, article pages 10-11",
    domain="PPAM middle-wall microstructure", notes="Midpoint is derived from reported range; not a reported mean."
)
lin_records["coarse_lath_mid"] = add_record(
    "LIN2016", "LIN_MIDDLE_LB", "PPAM_COARSE_BASKETWEAVE", "alpha_lamella_range_midpoint", 0.47, "um",
    process="wire-feed PPAM", thermal_level="LOCAL_BAND_POSITION_PROXY", proxy_type="microstructure_region",
    proxy_value="coarse_basketweave", build_position="middle wall / within layer band", cycle_count="multiple",
    lower=0.35, upper=0.59, evidence="DIRECT_TABLE_TEXT", locator="Table 4 and Fig. 4, article pages 10-11",
    domain="PPAM middle-wall microstructure", notes="Midpoint is derived from reported range; overlapping ranges preclude a precise mean effect."
)

# Tran et al. direct thermocouple/model calibration anchors.
tran_records: dict[str, str] = {}
tran_records["Tmax"] = add_record(
    "TRAN2017", "TRAN_10L_7TRACK", "SUBSTRATE_THERMOCOUPLE", "substrate_temperature_max", 1053, "K",
    process="powder-fed laser cladding", thermal_level="DIRECT_SENSOR", proxy_type="K_thermocouple_3mm_below_cup",
    proxy_value=1053, proxy_unit="K", build_position="substrate, 3 mm below cup base", cycle_count=10,
    evidence="DIRECT_FIGURE_TEXT", locator="Fig. 2 and Sec. 2, article pages 8-9",
    domain="Irepa Nd:YAG; 1074 W; 400 mm/min; 10 layers x 7 tracks",
    notes="Direct substrate measurement, not melt-pool temperature."
)
tran_records["Tend"] = add_record(
    "TRAN2017", "TRAN_10L_7TRACK", "SUBSTRATE_THERMOCOUPLE", "substrate_temperature_end_before_laser_off", 973, "K",
    process="powder-fed laser cladding", thermal_level="DIRECT_SENSOR", proxy_type="K_thermocouple_3mm_below_cup",
    proxy_value=973, proxy_unit="K", build_position="substrate, 3 mm below cup base", cycle_count=10,
    evidence="DIRECT_FIGURE_TEXT", locator="Fig. 2 and Sec. 2, article pages 8-9",
    domain="Irepa Nd:YAG; 1074 W; 400 mm/min; 10 layers x 7 tracks",
    notes="Temperature at end of deposition sequence before final cooling."
)
tran_records["absorptivity"] = add_record(
    "TRAN2017", "TRAN_FE_MODEL", "CALIBRATED_FE_MODEL", "laser_absorptivity", 0.35, "dimensionless",
    process="3D thermal FE model", thermal_level="MODEL_CALIBRATED_TO_SENSOR", proxy_type="calibrated_absorptivity",
    proxy_value=0.35, proxy_unit="dimensionless", build_position="model-wide", cycle_count=10,
    evidence="DIRECT_TEXT_DERIVED_MODEL_PARAMETER", locator="Sec. 3.2, article page 11",
    domain="same Irepa geometry, laser, scan path, material properties and boundary conditions",
    notes="Calibration parameter; not transferable without re-calibration."
)
tran_records["layer_time"] = add_record(
    "TRAN2017", "TRAN_10L_7TRACK", "PROCESS_SCHEDULE", "building_time_per_layer", 42.5, "s",
    process="powder-fed laser cladding", thermal_level="DIRECT_PROCESS_SCHEDULE", proxy_type="layer_time",
    proxy_value=42.5, proxy_unit="s/layer", build_position="all layers", cycle_count=10,
    evidence="DIRECT_TABLE_TEXT", locator="Table 1, article page 8",
    domain="10-layer, 7-track curved deposit", notes="Approximately 42.5 s per layer."
)

write_csv("ANALYSIS_COHORT.csv", cohort, cohort_fields)

# ---------------------------------------------------------------------------
# Pair matches and effect estimates.
# ---------------------------------------------------------------------------
pair_fields = [
    "pair_uid", "snapshot_id", "paper_uid", "source_hash", "control_record_uid", "treated_record_uid",
    "matching_grade", "matched_fields", "thermal_contrast", "property_name", "comparator_validity",
    "causal_identification", "calibration_domain", "source_locator", "notes"
]
pairs: list[dict[str, Any]] = []


def add_pair(name: str, source_key: str, control_uid: str, treated_uid: str, grade: str, matched: str,
             contrast: str, prop: str, validity: str, causal: str, domain: str, locator: str, notes: str = "") -> str:
    uid = "pair_" + sha256_text(name)[:16]
    s = SOURCES[source_key]
    pairs.append({
        "pair_uid": uid, "snapshot_id": SNAPSHOT_ID, "paper_uid": s["paper_uid"], "source_hash": s["source_hash"],
        "control_record_uid": control_uid, "treated_record_uid": treated_uid, "matching_grade": grade,
        "matched_fields": matched, "thermal_contrast": contrast, "property_name": prop,
        "comparator_validity": validity, "causal_identification": causal, "calibration_domain": domain,
        "source_locator": locator, "notes": notes,
    })
    return uid

pair_ids: dict[str, str] = {}
pair_ids["HP_HAZ"] = add_pair(
    "ZHAI_HP_LAYER_HAZ", "ZHAI2016", zhai_records[("HP_LAYER", "alpha_lath_thickness")], zhai_records[("HP_HAZ", "alpha_lath_thickness")],
    "A", "same paper, sample, build, power regime, as-built state and microscopy scale", "within-layer -> interlayer micro-HAZ reheating",
    "alpha_lath_thickness", "valid local matched contrast", "level-2 paired association; position is not randomized",
    "Optomec LENS high-power condition", "Fig. 7b,d and text", "Most defensible thermal-cycle estimand in this return."
)
pair_ids["LP_HAZ"] = add_pair(
    "ZHAI_LP_LAYER_HAZ", "ZHAI2016", zhai_records[("LP_LAYER", "alpha_lath_thickness")], zhai_records[("LP_HAZ", "alpha_lath_thickness")],
    "A", "same paper, sample, build, power regime, as-built state and microscopy scale", "within-layer -> interlayer micro-HAZ reheating",
    "alpha_prime_lath_thickness", "valid but control is right-censored upper bound", "level-2 paired lower-bound association",
    "Optomec LENS low-power condition", "Fig. 7a,c and text", "Effect must be reported as a lower bound."
)
for prop in ["YS", "UTS", "EL", "microhardness"]:
    pair_ids[f"POWER_{prop}"] = add_pair(
        f"ZHAI_POWER_{prop}", "ZHAI2016", zhai_records[("LPAF", prop)], zhai_records[("HPAF", prop)],
        "B", "same paper, alloy, as-built state and test condition; multiple process settings differ", "low-power process bundle -> high-power process bundle",
        prop, "near-match process-bundle contrast", "level-2 paired association; not isolated cooling-rate causality",
        "Optomec LENS only", "Tables 1-2", "Power, feed, layer thickness, hatch spacing and speed co-vary."
    )
    pair_ids[f"LPHT_{prop}"] = add_pair(
        f"ZHAI_LP_HT_{prop}", "ZHAI2016", zhai_records[("LPAF", prop)], zhai_records[("LPHT", prop)],
        "A", "same paper, alloy, process regime and test condition", "as-built -> 760 C/1 h vacuum anneal + air cool",
        prop, "valid same-regime heat-treatment contrast", "level-2 paired association",
        "Optomec LENS low-power condition", "Table 2", "Post-process heat treatment is distinct from intrinsic layer cycling."
    )
    pair_ids[f"HPHT_{prop}"] = add_pair(
        f"ZHAI_HP_HT_{prop}", "ZHAI2016", zhai_records[("HPAF", prop)], zhai_records[("HPHT", prop)],
        "A", "same paper, alloy, process regime and test condition", "as-built -> 760 C/1 h vacuum anneal + air cool",
        prop, "valid same-regime heat-treatment contrast", "level-2 paired association",
        "Optomec LENS high-power condition", "Table 2", "Post-process heat treatment is distinct from intrinsic layer cycling."
    )
pair_ids["LIN_SPACING"] = add_pair(
    "LIN_BAND_SPACING_LAYER_INCREMENT", "LIN2016", lin_records["band_spacing"], lin_records["band_spacing"],
    "A_CALIBRATION", "same wall and equipment; observable spacing compared with programmed delta-Z", "programmed 1.5 mm layer increment -> observed 1.40 mm band spacing",
    "thermal_proxy_calibration", "valid within-domain proxy calibration", "not a treatment effect",
    "16-layer PPAM wall only", "Table 3", "Self-reference is intentional: this is observable-vs-programmed calibration, not a biological control pair."
)
pair_ids["LIN_POSITION"] = add_pair(
    "LIN_BOTTOM_TOP_EXTREME", "LIN2016", lin_records["beta_bottom_min"], lin_records["beta_top_max"],
    "E", "same wall only; values are regional extrema rather than means", "bottom observed minimum -> top observed maximum",
    "prior_beta_grain_length_extreme", "descriptive support-range contrast only", "level-1 descriptive; no causal claim",
    "16-layer PPAM wall", "Sec. 3.1 and Table 3", "Cannot be interpreted as the average build-height slope."
)
pair_ids["LIN_CYCLE"] = add_pair(
    "LIN_3L_4L_BAND_ONSET", "LIN2016", lin_records["band_3"], lin_records["band_4"],
    "B", "same paper and PPAM setup; separate layer-count coupons", "3 deposited layers -> 4 deposited layers",
    "layer_band_present", "change-point bracket", "level-2 same-paper association; layer count bundles thermal exposure and geometry",
    "PPAM layer-count experiment", "Fig. 10 and discussion", "Onset is bracketed as 3 < total layers <= 4."
)
write_csv("PAIR_MATCHES.csv", pairs, pair_fields)

effect_fields = [
    "effect_uid", "pair_uid", "snapshot_id", "paper_uid", "source_hash", "property_name", "estimand",
    "control_value", "treated_value", "unit", "delta", "delta_semantics", "lnRR", "percent_change",
    "effect_lower", "effect_upper", "uncertainty_type", "independent_papers", "matching_grade", "evidence_level",
    "claim_level", "support_domain", "identifiability", "source_locator", "notes"
]
effects: list[dict[str, Any]] = []


def add_effect(name: str, pair_uid: str, source_key: str, prop: str, estimand: str, control: float | None,
               treated: float | None, unit: str, *, delta: float | None = None, delta_semantics: str = "absolute",
               lnrr: float | None = None, pct: float | None = None, lower: Any = "", upper: Any = "",
               uncertainty: str = "no_sampling_CI_reported", grade: str = "A", evidence: str = "DIRECT_TABLE_TEXT",
               claim: int = 2, domain: str, ident: str = "ESTIMABLE", locator: str, notes: str = "") -> None:
    if delta is None and control is not None and treated is not None:
        delta = treated - control
    if lnrr is None and control is not None and treated is not None and control > 0 and treated > 0:
        lnrr = math.log(treated / control)
    if pct is None and lnrr is not None:
        pct = 100.0 * (math.exp(lnrr) - 1.0)
    s = SOURCES[source_key]
    effects.append({
        "effect_uid": "eff_" + sha256_text(name)[:16], "pair_uid": pair_uid, "snapshot_id": SNAPSHOT_ID,
        "paper_uid": s["paper_uid"], "source_hash": s["source_hash"], "property_name": prop,
        "estimand": estimand, "control_value": fnum(control), "treated_value": fnum(treated), "unit": unit,
        "delta": fnum(delta), "delta_semantics": delta_semantics, "lnRR": fnum(lnrr), "percent_change": fnum(pct),
        "effect_lower": lower, "effect_upper": upper, "uncertainty_type": uncertainty, "independent_papers": 1,
        "matching_grade": grade, "evidence_level": evidence, "claim_level": claim, "support_domain": domain,
        "identifiability": ident, "source_locator": locator, "notes": notes,
    })

# Primary local thermal-cycle effects.
add_effect(
    "ZHAI_HP_HAZ_LATH", pair_ids["HP_HAZ"], "ZHAI2016", "alpha_lath_thickness",
    "E[lath thickness | micro-HAZ] - E[lath thickness | within layer] in the same high-power build", 0.79, 1.06, "um",
    lower=fnum(0.27 - math.sqrt(0.16**2 + 0.21**2)), upper=fnum(0.27 + math.sqrt(0.16**2 + 0.21**2)),
    uncertainty="reported_SD_rss_contrast_not_CI; replicate_n_unknown", grade="A", evidence="FIGURE_DERIVED",
    domain="Optomec LENS 850-R, high-power parameter bundle, as-built Ti-6Al-4V",
    locator="Fig. 7b,d and pages 55/59", notes="Delta=+0.27 um; +34.18%. SD propagation is descriptive only."
)
add_effect(
    "ZHAI_LP_HAZ_LATH", pair_ids["LP_HAZ"], "ZHAI2016", "alpha_prime_lath_thickness",
    "lower bound for micro-HAZ minus within-layer lath thickness in the same low-power build", 0.73, 0.86, "um",
    delta=0.13, lnrr=math.log(0.86 / 0.73), pct=(0.86 / 0.73 - 1) * 100,
    lower=">=0.13", upper="", uncertainty="right-censored_control_upper_bound; reported_SDs_not_CI",
    grade="A", evidence="FIGURE_DERIVED", domain="Optomec LENS 850-R, low-power parameter bundle, as-built Ti-6Al-4V",
    locator="Fig. 7a,c and pages 55/59", notes="Because control is <0.73 um, all reported effect metrics are conservative lower bounds."
)

# Power-regime bundle effects.
for prop, unit in [("YS", "MPa"), ("UTS", "MPa"), ("EL", "%"), ("microhardness", "HV")]:
    c = float(next(r["value"] for r in cohort if r["record_uid"] == zhai_records[("LPAF", prop)]))
    t = float(next(r["value"] for r in cohort if r["record_uid"] == zhai_records[("HPAF", prop)]))
    add_effect(
        f"ZHAI_POWER_{prop}", pair_ids[f"POWER_{prop}"], "ZHAI2016", prop,
        "high-power process-bundle minus low-power process-bundle in as-built state", c, t, unit,
        delta_semantics="percentage_points" if prop == "EL" else "absolute",
        grade="B", domain="Optomec LENS 850-R; only the two reported bundles",
        locator="Tables 1-2", notes="Not an isolated cooling-rate coefficient; line-energy and nominal VED rank the regimes differently."
    )
    for regime, ccond, tcond in [("LP", "LPAF", "LPHT"), ("HP", "HPAF", "HPHT")]:
        c2 = float(next(r["value"] for r in cohort if r["record_uid"] == zhai_records[(ccond, prop)]))
        t2 = float(next(r["value"] for r in cohort if r["record_uid"] == zhai_records[(tcond, prop)]))
        add_effect(
            f"ZHAI_{regime}_HT_{prop}", pair_ids[f"{regime}HT_{prop}"], "ZHAI2016", prop,
            f"post-LENS anneal minus as-built within {regime} regime", c2, t2, unit,
            delta_semantics="percentage_points" if prop == "EL" else "absolute", grade="A",
            domain=f"Optomec LENS 850-R {regime} regime; 760 C 1 h vacuum + air cool",
            locator="Table 2", notes="Heat-treatment effect, retained to separate intrinsic thermal cycling from post-process annealing."
        )

# Lin proxy calibration, extrema and cycle onset.
add_effect(
    "LIN_SPACING_CAL", pair_ids["LIN_SPACING"], "LIN2016", "layer_band_spacing",
    "observed layer-band spacing minus programmed layer increment", 1.5, 1.40, "mm",
    uncertainty="observed band spacing SD=0.40 mm; no n", grade="A_CALIBRATION", evidence="DIRECT_TABLE_TEXT",
    claim=2, domain="16-layer PPAM wall, delta-Z=1.5 mm", locator="Table 3",
    notes="Observed/programmed ratio=0.933; calibration is not transferable to another machine or geometry."
)
add_effect(
    "LIN_POSITION_EXTREME", pair_ids["LIN_POSITION"], "LIN2016", "prior_beta_grain_length_extreme",
    "top observed maximum minus bottom observed minimum", 0.86, 6.90, "mm",
    uncertainty="observed_extrema_not_regional_means", grade="E", evidence="DIRECT_TABLE_TEXT", claim=1,
    domain="single 16-layer PPAM wall", locator="Sec. 3.1 and Table 3",
    notes="Support-range illustration only; excluded from causal or average build-height slope claims."
)
add_effect(
    "LIN_CYCLE_ONSET", pair_ids["LIN_CYCLE"], "LIN2016", "layer_band_present",
    "risk difference for visible layer-band onset between 3-layer and 4-layer coupons", 0, 1, "binary",
    delta=1, lnrr=None, pct=None, uncertainty="interval-censored change point: 3 < total layers <= 4",
    grade="B", evidence="DIRECT_TEXT_FIGURE", claim=2, domain="PPAM layer-count sub-experiments",
    locator="Fig. 10 and discussion", notes="Binary visibility; not a universal cycle threshold."
)
write_csv("EFFECT_ESTIMATES.csv", effects, effect_fields)

# ---------------------------------------------------------------------------
# Scope-specific registries.
# ---------------------------------------------------------------------------
proxy_fields = [
    "proxy_uid", "snapshot_id", "paper_uid", "source_hash", "latent_variable", "observable_proxy", "formula_or_definition",
    "reported_or_derived_value", "unit", "measurement_level", "calibration_domain", "directional_expectation",
    "known_confounders", "transfer_status", "evidence_level", "source_locator", "claim_ceiling", "notes"
]
proxies = [
    {
        "proxy_uid": "proxy_zhai_line_energy_lp", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
        "latent_variable": "integrated heat input / cooling regime", "observable_proxy": "line energy, low-power bundle", "formula_or_definition": "P/v",
        "reported_or_derived_value": 33.0, "unit": "J/mm", "measurement_level": "DERIVED_PROCESS_PROXY", "calibration_domain": "Optomec LENS 850-R low-power bundle",
        "directional_expectation": "higher line energy usually increases thermal exposure", "known_confounders": "powder rate, layer thickness, hatch spacing, geometry, absorptivity",
        "transfer_status": "WITHIN_DOMAIN_ONLY", "evidence_level": "DERIVED_CALCULATION", "source_locator": "Table 1",
        "claim_ceiling": "association", "notes": "330 W / (0.6 m/min = 10 mm/s)."
    },
    {
        "proxy_uid": "proxy_zhai_line_energy_hp", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
        "latent_variable": "integrated heat input / cooling regime", "observable_proxy": "line energy, high-power bundle", "formula_or_definition": "P/v",
        "reported_or_derived_value": 58.5, "unit": "J/mm", "measurement_level": "DERIVED_PROCESS_PROXY", "calibration_domain": "Optomec LENS 850-R high-power bundle",
        "directional_expectation": "higher than LP by this proxy", "known_confounders": "powder rate, layer thickness, hatch spacing, geometry, absorptivity",
        "transfer_status": "WITHIN_DOMAIN_ONLY", "evidence_level": "DERIVED_CALCULATION", "source_locator": "Table 1",
        "claim_ceiling": "association", "notes": "780 W / (0.8 m/min = 13.333 mm/s)."
    },
    {
        "proxy_uid": "proxy_zhai_ved_lp", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
        "latent_variable": "nominal local energy density", "observable_proxy": "nominal volumetric energy density, LP", "formula_or_definition": "P/(v*hatch*layer_thickness)",
        "reported_or_derived_value": 220.0, "unit": "J/mm3", "measurement_level": "DERIVED_PROCESS_PROXY", "calibration_domain": "Optomec LENS low-power bundle",
        "directional_expectation": "higher than HP by this proxy", "known_confounders": "powder catch efficiency, melt-pool geometry, overlap, absorptivity",
        "transfer_status": "WITHIN_DOMAIN_ONLY", "evidence_level": "DERIVED_CALCULATION", "source_locator": "Table 1",
        "claim_ceiling": "association", "notes": "Proxy ranking reverses relative to line energy; no single scalar thermal ordering is defensible."
    },
    {
        "proxy_uid": "proxy_zhai_ved_hp", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
        "latent_variable": "nominal local energy density", "observable_proxy": "nominal volumetric energy density, HP", "formula_or_definition": "P/(v*hatch*layer_thickness)",
        "reported_or_derived_value": 146.25, "unit": "J/mm3", "measurement_level": "DERIVED_PROCESS_PROXY", "calibration_domain": "Optomec LENS high-power bundle",
        "directional_expectation": "lower than LP by this proxy", "known_confounders": "powder catch efficiency, melt-pool geometry, overlap, absorptivity",
        "transfer_status": "WITHIN_DOMAIN_ONLY", "evidence_level": "DERIVED_CALCULATION", "source_locator": "Table 1",
        "claim_ceiling": "association", "notes": "Proxy ranking reverses relative to line energy."
    },
    {
        "proxy_uid": "proxy_lin_interpass", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["LIN2016"]["paper_uid"], "source_hash": SOURCES["LIN2016"]["source_hash"],
        "latent_variable": "interpass thermal accumulation", "observable_proxy": "maximum prior-layer temperature before next layer", "formula_or_definition": "deposit only when prior layer < 300 C",
        "reported_or_derived_value": "<300", "unit": "C", "measurement_level": "DIRECT_CONTROL_THRESHOLD", "calibration_domain": "wire-feed PPAM setup",
        "directional_expectation": "caps interpass accumulation but does not reconstruct full thermal trace", "known_confounders": "thermocouple location, wall geometry, layerwise current schedule",
        "transfer_status": "WITHIN_DOMAIN_ONLY", "evidence_level": "DIRECT_TEXT", "source_locator": "Sec. 2.2, article page 6",
        "claim_ceiling": "controlled threshold, not local melt-pool temperature", "notes": "Thermocouple probes were 5 mm below deposited surface."
    },
    {
        "proxy_uid": "proxy_lin_band_spacing", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["LIN2016"]["paper_uid"], "source_hash": SOURCES["LIN2016"]["source_hash"],
        "latent_variable": "reheating isotherm / layer-cycle imprint", "observable_proxy": "layer-band spacing", "formula_or_definition": "observed spacing / programmed delta-Z",
        "reported_or_derived_value": "1.40±0.40; ratio 0.933", "unit": "mm; dimensionless", "measurement_level": "DIRECT_MICROSTRUCTURE_PROXY", "calibration_domain": "16-layer PPAM wall, delta-Z=1.5 mm",
        "directional_expectation": "tracks layer increment within uncertainty", "known_confounders": "etch contrast, curved isotherm, local bead geometry",
        "transfer_status": "CALIBRATE_PER_DEVICE_GEOMETRY", "evidence_level": "DIRECT_TABLE_TEXT+DERIVED_CALCULATION", "source_locator": "Table 3",
        "claim_ceiling": "proxy association", "notes": "Observed min-max 0.87-2.13 mm."
    },
    {
        "proxy_uid": "proxy_tran_sensor", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["TRAN2017"]["paper_uid"], "source_hash": SOURCES["TRAN2017"]["source_hash"],
        "latent_variable": "substrate thermal accumulation", "observable_proxy": "K-thermocouple trace 3 mm below cup", "formula_or_definition": "direct T(t) measurement",
        "reported_or_derived_value": "Tmax=1053; Tend=973", "unit": "K", "measurement_level": "DIRECT_SENSOR", "calibration_domain": "Irepa 10-layer x 7-track thick deposit",
        "directional_expectation": "direct at sensor; spatial extrapolation requires model", "known_confounders": "sensor lag/location and boundary conditions",
        "transfer_status": "SENSOR_DIRECT_MODEL_DOMAIN_LIMITED", "evidence_level": "DIRECT_FIGURE_TEXT", "source_locator": "Fig. 2",
        "claim_ceiling": "direct only at sensor location", "notes": "Not the melt-pool peak temperature."
    },
    {
        "proxy_uid": "proxy_tran_model", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["TRAN2017"]["paper_uid"], "source_hash": SOURCES["TRAN2017"]["source_hash"],
        "latent_variable": "spatial thermal history", "observable_proxy": "sensor-calibrated 3D FE model", "formula_or_definition": "thermal FE with calibrated absorptivity beta=0.35",
        "reported_or_derived_value": 0.35, "unit": "absorptivity", "measurement_level": "MODEL_CALIBRATED_TO_DIRECT_SENSOR", "calibration_domain": "same equipment, geometry, path, material and boundary conditions",
        "directional_expectation": "can reconstruct T(x,y,z,t) only after validation", "known_confounders": "material properties, convection, radiation, mesh and heat-source assumptions",
        "transfer_status": "RECALIBRATION_REQUIRED", "evidence_level": "DIRECT_TEXT_MODEL", "source_locator": "Secs. 3.2-3.3",
        "claim_ceiling": "calibrated model estimate", "notes": "Raw model residuals were not available in this return."
    },
    {
        "proxy_uid": "proxy_gr_missing", "snapshot_id": SNAPSHOT_ID, "paper_uid": "MULTI", "source_hash": "",
        "latent_variable": "G/R solidification state", "observable_proxy": "G, R, G/R, GxR", "formula_or_definition": "requires validated thermal/solidification field",
        "reported_or_derived_value": "NOT_AVAILABLE", "unit": "", "measurement_level": "MISSING_CRITICAL_INPUT", "calibration_domain": "none",
        "directional_expectation": "not estimable from P and v alone", "known_confounders": "geometry, absorptivity, boundary conditions and melt-pool convection",
        "transfer_status": "NOT_IDENTIFIABLE", "evidence_level": "UNRESOLVED", "source_locator": "project figure registry indicates candidate GxR plots but raw values unavailable",
        "claim_ceiling": "none", "notes": "No fabricated G/R values."
    },
    {
        "proxy_uid": "proxy_cao_lpbf_range", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["CAO2023"]["paper_uid"], "source_hash": SOURCES["CAO2023"]["source_hash"],
        "latent_variable": "LPBF cooling-rate regime", "observable_proxy": "literature range stated in method context", "formula_or_definition": "reported range",
        "reported_or_derived_value": "1e3-1e8", "unit": "C/s", "measurement_level": "DATABASE_PRIOR_NOT_SAMPLE_MEASUREMENT", "calibration_domain": "LPBF Ti-6Al-4V context",
        "directional_expectation": "rapid cooling favors alpha-prime", "known_confounders": "local geometry and scan history",
        "transfer_status": "REFERENCE_ONLY", "evidence_level": "DATABASE_PRIOR", "source_locator": "Introduction",
        "claim_ceiling": "method-context prior", "notes": "Excluded from pooled effect estimation."
    },
]
write_csv("THERMAL_PROXY_REGISTRY.csv", proxies, proxy_fields)

build_pos_fields = [
    "effect_uid", "snapshot_id", "paper_uid", "source_hash", "property_name", "low_position", "high_position",
    "low_value", "high_value", "unit", "delta", "relative_change_pct", "evidence_level", "headline_eligible",
    "matching_grade", "support_domain", "source_locator", "interpretation", "notes"
]
build_position = [
    {
        "effect_uid": "bp_lin_beta_extrema", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["LIN2016"]["paper_uid"], "source_hash": SOURCES["LIN2016"]["source_hash"],
        "property_name": "prior_beta_grain_length_extreme", "low_position": "bottom observed minimum", "high_position": "top observed maximum",
        "low_value": 0.86, "high_value": 6.90, "unit": "mm", "delta": 6.04, "relative_change_pct": fnum((6.90/0.86-1)*100),
        "evidence_level": "DIRECT_TABLE_TEXT", "headline_eligible": "NO", "matching_grade": "E",
        "support_domain": "single 16-layer PPAM wall", "source_locator": "Sec. 3.1 and Table 3",
        "interpretation": "build-height-associated support range, not an average slope", "notes": "Values are extrema."
    },
    {
        "effect_uid": "bp_carroll_ys_secondary", "snapshot_id": SNAPSHOT_ID, "paper_uid": "doi:10.1016/j.actamat.2014.12.054", "source_hash": identity_fp("10.1016/j.actamat.2014.12.054", "Anisotropic tensile behavior of Ti-6Al-4V components fabricated with directed energy deposition additive manufacturing"),
        "property_name": "YS_vertical", "low_position": "top", "high_position": "bottom", "low_value": 945, "high_value": 970,
        "unit": "MPa", "delta": 25, "relative_change_pct": fnum((970/945-1)*100), "evidence_level": "DATABASE_PRIOR_FROM_2025_REVIEW_TABLE",
        "headline_eligible": "NO", "matching_grade": "SECONDARY", "support_domain": "DED Ti-6Al-4V vertical specimens",
        "source_locator": "Zarei 2025 review Table 2; original paper unavailable in this runtime",
        "interpretation": "candidate build-position effect pending original-paper verification", "notes": "Do not promote until original table and condition lineage are checked."
    },
    {
        "effect_uid": "bp_carroll_uts_secondary", "snapshot_id": SNAPSHOT_ID, "paper_uid": "doi:10.1016/j.actamat.2014.12.054", "source_hash": identity_fp("10.1016/j.actamat.2014.12.054", "Anisotropic tensile behavior of Ti-6Al-4V components fabricated with directed energy deposition additive manufacturing"),
        "property_name": "UTS_vertical", "low_position": "top", "high_position": "bottom", "low_value": 1041, "high_value": 1087,
        "unit": "MPa", "delta": 46, "relative_change_pct": fnum((1087/1041-1)*100), "evidence_level": "DATABASE_PRIOR_FROM_2025_REVIEW_TABLE",
        "headline_eligible": "NO", "matching_grade": "SECONDARY", "support_domain": "DED Ti-6Al-4V vertical specimens",
        "source_locator": "Zarei 2025 review Table 2; original paper unavailable in this runtime",
        "interpretation": "candidate build-position effect pending original-paper verification", "notes": "Do not promote until original table and condition lineage are checked."
    },
    {
        "effect_uid": "bp_carroll_el_secondary", "snapshot_id": SNAPSHOT_ID, "paper_uid": "doi:10.1016/j.actamat.2014.12.054", "source_hash": identity_fp("10.1016/j.actamat.2014.12.054", "Anisotropic tensile behavior of Ti-6Al-4V components fabricated with directed energy deposition additive manufacturing"),
        "property_name": "EL_vertical", "low_position": "top", "high_position": "bottom", "low_value": 14.5, "high_value": 13.6,
        "unit": "%", "delta": -0.9, "relative_change_pct": fnum((13.6/14.5-1)*100), "evidence_level": "DATABASE_PRIOR_FROM_2025_REVIEW_TABLE",
        "headline_eligible": "NO", "matching_grade": "SECONDARY", "support_domain": "DED Ti-6Al-4V vertical specimens",
        "source_locator": "Zarei 2025 review Table 2; original paper unavailable in this runtime",
        "interpretation": "candidate build-position effect pending original-paper verification", "notes": "Do not promote until original table and condition lineage are checked."
    },
]
write_csv("BUILD_POSITION_EFFECTS.csv", build_position, build_pos_fields)

cycle_fields = [
    "effect_uid", "snapshot_id", "paper_uid", "source_hash", "cycle_proxy", "control_state", "reheated_state",
    "property_name", "control_value", "reheated_value", "unit", "effect", "effect_type", "uncertainty",
    "evidence_level", "claim_level", "support_domain", "source_locator", "notes"
]
cycle_rows = [
    {
        "effect_uid": "tc_zhai_hp_haz", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
        "cycle_proxy": "interlayer micro-HAZ position", "control_state": "within layer", "reheated_state": "micro-HAZ",
        "property_name": "alpha_lath_thickness", "control_value": 0.79, "reheated_value": 1.06, "unit": "um",
        "effect": 0.27, "effect_type": "+34.18% paired local association", "uncertainty": "SD 0.16 and 0.21; n unavailable",
        "evidence_level": "FIGURE_DERIVED", "claim_level": 2, "support_domain": "Zhai high-power LENS build",
        "source_locator": "Fig. 7b,d", "notes": "Direct local thermal-cycle proxy contrast."
    },
    {
        "effect_uid": "tc_zhai_lp_haz", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
        "cycle_proxy": "interlayer micro-HAZ position", "control_state": "within layer (<0.73 um)", "reheated_state": "micro-HAZ",
        "property_name": "alpha_prime_lath_thickness", "control_value": "<0.73", "reheated_value": 0.86, "unit": "um",
        "effect": ">=0.13", "effect_type": ">=17.81% lower-bound paired association", "uncertainty": "right-censored control",
        "evidence_level": "FIGURE_DERIVED", "claim_level": 2, "support_domain": "Zhai low-power LENS build",
        "source_locator": "Fig. 7a,c", "notes": "Conservative lower bound."
    },
    {
        "effect_uid": "tc_lin_onset", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["LIN2016"]["paper_uid"], "source_hash": SOURCES["LIN2016"]["source_hash"],
        "cycle_proxy": "total deposited layers in separate coupons", "control_state": "3 layers", "reheated_state": "4 layers",
        "property_name": "visible_layer_band", "control_value": 0, "reheated_value": 1, "unit": "binary",
        "effect": "change point 3 < layers <= 4", "effect_type": "interval-censored onset", "uncertainty": "separate coupons; not universal",
        "evidence_level": "DIRECT_TEXT_FIGURE", "claim_level": 2, "support_domain": "Lin PPAM setup",
        "source_locator": "Fig. 10 and discussion", "notes": "Last three layers in 16-layer wall also lack bands because of insufficient future reheating."
    },
    {
        "effect_uid": "tc_tran_pia", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["TRAN2017"]["paper_uid"], "source_hash": SOURCES["TRAN2017"]["source_hash"],
        "cycle_proxy": "sensor-calibrated simulated repeated peaks and pseudo-isothermal annealing time", "control_state": "last solidification", "reheated_state": "successive remelting/PIA",
        "property_name": "mixed_microstructure_state", "control_value": "alpha-prime dominated candidate", "reheated_value": "alpha-prime + alpha/beta Widmanstatten + possible retained beta + alpha-m",
        "unit": "categorical", "effect": "qualitative phase decomposition pathway", "effect_type": "calibrated-model mechanism",
        "uncertainty": "raw nodal histories and phase fractions unavailable", "evidence_level": "DIRECT_TEXT_MODEL",
        "claim_level": 1, "support_domain": "Tran 10-layer thick deposit", "source_locator": "Fig. 13 and conclusions",
        "notes": "Not used as a numerical pooled effect."
    },
]
write_csv("THERMAL_CYCLE_EFFECTS.csv", cycle_rows, cycle_fields)

missing_fields = [
    "step", "snapshot_id", "paper_uid", "source_hash", "target", "known_information", "missing_dimension",
    "support_lower", "support_upper", "interval_width", "incremental_width", "unit", "uncertainty_semantics",
    "calibration_domain", "evidence_level", "notes"
]
missing_rows = [
    {"step": 0, "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
     "target": "UTS", "known_information": "LPAF condition fully specified", "missing_dimension": "none", "support_lower": 1103, "support_upper": 1103,
     "interval_width": 0, "incremental_width": 0, "unit": "MPa", "uncertainty_semantics": "empirical within-paper support set, not a confidence interval",
     "calibration_domain": "Zhai Table 2 Ti-6Al-4V RT tension", "evidence_level": "DIRECT_TABLE_TEXT", "notes": "Baseline."},
    {"step": 1, "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
     "target": "UTS", "known_information": "low-power LENS, RT tension", "missing_dimension": "post-LENS heat-treatment state", "support_lower": 1073, "support_upper": 1103,
     "interval_width": 30, "incremental_width": 30, "unit": "MPa", "uncertainty_semantics": "empirical support interval",
     "calibration_domain": "Zhai low-power conditions", "evidence_level": "DIRECT_TABLE_TEXT", "notes": "LPAF and LPHT."},
    {"step": 2, "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
     "target": "UTS", "known_information": "LENS Ti-6Al-4V, RT tension", "missing_dimension": "power/feed/layer/hatch/speed thermal-proxy bundle", "support_lower": 1042, "support_upper": 1103,
     "interval_width": 61, "incremental_width": 31, "unit": "MPa", "uncertainty_semantics": "empirical support interval",
     "calibration_domain": "four Zhai LENS states", "evidence_level": "DIRECT_TABLE_TEXT", "notes": "LPAF, LPHT, HPAF, HPHT."},
    {"step": 3, "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
     "target": "UTS", "known_information": "Ti-6Al-4V RT tension in reported paper", "missing_dimension": "manufacturing domain (LENS vs mill-annealed substrate)", "support_lower": 1030, "support_upper": 1103,
     "interval_width": 73, "incremental_width": 12, "unit": "MPa", "uncertainty_semantics": "empirical support interval",
     "calibration_domain": "Zhai Table 2 only", "evidence_level": "DIRECT_TABLE_TEXT", "notes": "Not an out-of-paper prediction interval."},
    {"step": 4, "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
     "target": "alpha_lath_thickness", "known_information": "high-power as-built LENS", "missing_dimension": "local reheating position", "support_lower": 0.79, "support_upper": 1.06,
     "interval_width": 0.27, "incremental_width": 0.27, "unit": "um", "uncertainty_semantics": "empirical local support interval",
     "calibration_domain": "Zhai HP within-layer/micro-HAZ", "evidence_level": "FIGURE_DERIVED", "notes": "Separate target; not plotted in UTS waterfall."},
]
write_csv("THERMAL_MISSINGNESS_UQ.csv", missing_rows, missing_fields)

# ---------------------------------------------------------------------------
# Model/heterogeneity/sensitivity outputs with explicit non-identifiability.
# ---------------------------------------------------------------------------
hier_fields = [
    "result_uid", "snapshot_id", "outcome", "model_specification", "independent_papers", "effect_rows",
    "estimate", "standard_error", "CI95", "prediction_interval", "tau2", "status", "reason", "claim_level"
]
hier_rows = []
for outcome, nrows in [
    ("alpha_lath_thickness_local_reheat", 2), ("UTS_power_or_anneal", 3), ("YS_power_or_anneal", 3),
    ("EL_power_or_anneal", 3), ("microhardness_power_or_anneal", 3), ("build_position_prior_beta", 1),
    ("layer_band_cycle_onset", 1),
]:
    hier_rows.append({
        "result_uid": "hier_" + sha256_text(outcome)[:12], "snapshot_id": SNAPSHOT_ID, "outcome": outcome,
        "model_specification": "paper-random-intercept / random-slope candidate", "independent_papers": 1,
        "effect_rows": nrows, "estimate": "", "standard_error": "", "CI95": "", "prediction_interval": "", "tau2": "",
        "status": "NOT_IDENTIFIABLE", "reason": "Only one independent paper supplies a semantically comparable effect definition.",
        "claim_level": 2 if outcome.startswith(("alpha", "UTS", "YS", "EL", "micro")) else 1,
    })
write_csv("HIERARCHICAL_RESULTS.csv", hier_rows, hier_fields)

# No defensible thermal dose-response across equipment domains.
dose_fields = ["result_uid", "snapshot_id", "outcome", "dose_variable", "dose_unit", "independent_papers", "n_points", "model", "estimate", "status", "reason", "support_domain"]
dose_rows = [
    {"result_uid": "dose_line_energy_uts", "snapshot_id": SNAPSHOT_ID, "outcome": "UTS", "dose_variable": "line_energy", "dose_unit": "J/mm", "independent_papers": 1, "n_points": 2,
     "model": "candidate monotone/nonlinear", "estimate": "", "status": "NOT_IDENTIFIABLE", "reason": "Two bundles co-vary in powder rate, layer thickness, hatch and speed; line energy and nominal VED reverse the ordering.", "support_domain": "Zhai LENS only"},
    {"result_uid": "dose_cycle_band", "snapshot_id": SNAPSHOT_ID, "outcome": "layer_band_present", "dose_variable": "total_layers", "dose_unit": "layers", "independent_papers": 1, "n_points": 3,
     "model": "interval-censored change point", "estimate": "3 < onset <= 4", "status": "DESCRIPTIVE_CHANGE_POINT_ONLY", "reason": "Separate coupons and device-specific thermal schedule.", "support_domain": "Lin PPAM only"},
]
write_csv("DOSE_RESPONSE.csv", dose_rows, dose_fields)

interaction_fields = [
    "interaction_uid", "snapshot_id", "paper_uid", "source_hash", "outcome", "factor_A", "factor_B", "contrast_definition",
    "estimate", "unit", "uncertainty", "evidence_level", "claim_level", "support_domain", "status", "notes"
]
interaction_rows = []
for prop, unit in [("YS", "MPa"), ("UTS", "MPa"), ("EL", "percentage_points"), ("microhardness", "HV")]:
    lp_change = float(next(e["delta"] for e in effects if e["pair_uid"] == pair_ids[f"LPHT_{prop}"]))
    hp_change = float(next(e["delta"] for e in effects if e["pair_uid"] == pair_ids[f"HPHT_{prop}"]))
    did = hp_change - lp_change
    interaction_rows.append({
        "interaction_uid": "int_" + sha256_text(prop)[:12], "snapshot_id": SNAPSHOT_ID,
        "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"],
        "outcome": prop, "factor_A": "process bundle (LP vs HP)", "factor_B": "post-LENS anneal (AF vs HT)",
        "contrast_definition": "(HPHT-HPAF) - (LPHT-LPAF)", "estimate": fnum(did), "unit": unit,
        "uncertainty": "no replicate-level covariance or sample n", "evidence_level": "DERIVED_CALCULATION_FROM_DIRECT_TABLE",
        "claim_level": 2, "support_domain": "Zhai Optomec LENS two bundles", "status": "ESTIMABLE_DESCRIPTIVE_INTERACTION",
        "notes": "Cannot be assigned to cooling rate alone because process factors co-vary."
    })
interaction_rows.append({
    "interaction_uid": "int_strategy_orientation_syed", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["SYED2021"]["paper_uid"], "source_hash": SOURCES["SYED2021"]["source_hash"],
    "outcome": "fatigue_crack_growth", "factor_A": "deposition strategy", "factor_B": "crack propagation orientation",
    "contrast_definition": "single/parallel/oscillation x parallel/normal to layers", "estimate": "", "unit": "",
    "uncertainty": "raw curves and row-level values not extracted", "evidence_level": "DIRECT_ABSTRACT_TEXT",
    "claim_level": 1, "support_domain": "WAAM Ti-6Al-4V as-built", "status": "NOT_QUANTITATIVELY_IDENTIFIABLE",
    "notes": "Oscillation was coarser and showed lower crack-growth rates but greater anisotropy/scatter."
})
write_csv("INTERACTION_EFFECTS.csv", interaction_rows, interaction_fields)

hetero_fields = ["result_uid", "snapshot_id", "outcome", "independent_papers", "heterogeneity_metric", "value", "status", "reason", "qualitative_sources", "claim_ceiling"]
hetero_rows = [
    {"result_uid": "het_lath", "snapshot_id": SNAPSHOT_ID, "outcome": "local_reheat_lath_coarsening", "independent_papers": 1, "heterogeneity_metric": "tau2/I2", "value": "", "status": "NOT_IDENTIFIABLE", "reason": "LP effect is censored and both contrasts are from one paper.", "qualitative_sources": "Zhai2016; Lin2016", "claim_ceiling": "within-paper paired"},
    {"result_uid": "het_thermal_proxy", "snapshot_id": SNAPSHOT_ID, "outcome": "thermal_proxy_ordering", "independent_papers": 1, "heterogeneity_metric": "proxy ranking consistency", "value": "line energy: HP>LP; nominal VED: HP<LP", "status": "STRUCTURAL_CONFLICT", "reason": "Different scalar proxies encode different physics and reverse rank.", "qualitative_sources": "Zhai2016", "claim_ceiling": "no universal scalar proxy"},
    {"result_uid": "het_domain", "snapshot_id": SNAPSHOT_ID, "outcome": "cross-process transfer", "independent_papers": 4, "heterogeneity_metric": "domain comparability", "value": "LENS/PPAM/laser-cladding/WAAM differ", "status": "NO_POOLING", "reason": "Equipment, heat source, feedstock, geometry, cycle schedule and measurements differ.", "qualitative_sources": "Zhai2016; Lin2016; Tran2017; Syed2021", "claim_ceiling": "device-domain-specific"},
]
write_csv("HETEROGENEITY.csv", hetero_rows, hetero_fields)

sens_fields = ["analysis_uid", "snapshot_id", "target_result", "perturbation", "baseline", "alternative", "change", "decision", "independent_papers_remaining", "notes"]
sens_rows = [
    {"analysis_uid": "sens_lopo_zhai", "snapshot_id": SNAPSHOT_ID, "target_result": "local micro-HAZ lath coarsening and power/HT property effects", "perturbation": "leave Zhai2016 out", "baseline": "estimable", "alternative": "no semantically matched effect", "change": "100% evidence loss", "decision": "LOPO_COLLAPSE", "independent_papers_remaining": 0, "notes": "Headline effects are single-paper and must not be generalized."},
    {"analysis_uid": "sens_lopo_lin", "snapshot_id": SNAPSHOT_ID, "target_result": "band onset / band spacing / build-height extrema", "perturbation": "leave Lin2016 out", "baseline": "estimable descriptive", "alternative": "not identifiable", "change": "100% evidence loss", "decision": "LOPO_COLLAPSE", "independent_papers_remaining": 0, "notes": "No pooled cycle threshold."},
    {"analysis_uid": "sens_lopo_tran", "snapshot_id": SNAPSHOT_ID, "target_result": "direct sensor/model calibration registry", "perturbation": "leave Tran2017 out", "baseline": "direct sensor anchor available", "alternative": "process proxies only", "change": "loss of direct sensor-calibrated source", "decision": "EVIDENCE_LEVEL_DOWNGRADE", "independent_papers_remaining": 0, "notes": "No spatial thermal reconstruction without model source."},
    {"analysis_uid": "sens_lp_bound", "snapshot_id": SNAPSHOT_ID, "target_result": "LP local lath coarsening", "perturbation": "replace conservative upper bound 0.73 with 0.62 (=0.73-0.11 SD)", "baseline": ">=0.13 um / >=17.81%", "alternative": "0.24 um / 38.71%", "change": "effect grows", "decision": "DIRECTION_ROBUST_MAGNITUDE_CENSORED", "independent_papers_remaining": 1, "notes": "Illustrates censoring sensitivity; not a confidence bound."},
    {"analysis_uid": "sens_proxy_choice", "snapshot_id": SNAPSHOT_ID, "target_result": "HP vs LP thermal ordering", "perturbation": "line energy -> nominal VED", "baseline": "HP/LP=1.773", "alternative": "HP/LP=0.665", "change": "ordering reverses", "decision": "NO_SINGLE_PROXY_CAUSAL_CLAIM", "independent_papers_remaining": 1, "notes": "Primary contradiction requiring direct sensor/model calibration."},
    {"analysis_uid": "sens_secondary_exclusion", "snapshot_id": SNAPSHOT_ID, "target_result": "build-position tensile effects", "perturbation": "exclude Zarei review-extracted Carroll rows", "baseline": "secondary candidate values present", "alternative": "no primary tensile build-position estimate", "change": "headline unchanged", "decision": "PRIMARY_ONLY_HEADLINE_ROBUST", "independent_papers_remaining": 1, "notes": "Lin extreme microstructure range remains descriptive only."},
]
write_csv("SENSITIVITY_ANALYSIS.csv", sens_rows, sens_fields)

null_fields = ["result_uid", "snapshot_id", "paper_uid", "source_hash", "question", "result", "evidence_level", "support_domain", "reason_not_headline", "source_locator"]
null_rows = [
    {"result_uid": "null_zhai_hp_uts", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"], "question": "Does 760 C/1 h anneal raise UTS in HP condition?", "result": "+2 MPa (1042 to 1044), effectively negligible at table resolution", "evidence_level": "DIRECT_TABLE_TEXT", "support_domain": "Zhai HP LENS", "reason_not_headline": "no replicate uncertainty", "source_locator": "Table 2"},
    {"result_uid": "null_zhai_hp_ys", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZHAI2016"]["paper_uid"], "source_hash": SOURCES["ZHAI2016"]["source_hash"], "question": "Does anneal change YS in HP condition?", "result": "+1 MPa (990 to 991), effectively negligible at table resolution", "evidence_level": "DIRECT_TABLE_TEXT", "support_domain": "Zhai HP LENS", "reason_not_headline": "no replicate uncertainty", "source_locator": "Table 2"},
    {"result_uid": "null_lin_hardness_height", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["LIN2016"]["paper_uid"], "source_hash": SOURCES["LIN2016"]["source_hash"], "question": "Is hardness strongly different through build height?", "result": "authors report no obvious whole-wall difference; middle layer band slightly lower", "evidence_level": "DIRECT_TEXT_FIGURE", "support_domain": "Lin PPAM wall", "reason_not_headline": "raw point values unavailable", "source_locator": "Fig. 8 and Sec. 3.3.1"},
    {"result_uid": "null_lei_morphology", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["ZAREI2025"]["paper_uid"], "source_hash": SOURCES["ZAREI2025"]["source_hash"], "question": "Do 133.6-163.4 K/s WAAM cooling rates alter central basketweave morphology?", "result": "review reports no significant central morphology change across three deposition rates", "evidence_level": "DATABASE_PRIOR_REVIEW", "support_domain": "cited Lei study only", "reason_not_headline": "primary paper not opened", "source_locator": "Zarei 2025 Sec. 3.5"},
    {"result_uid": "null_syed_single_parallel", "snapshot_id": SNAPSHOT_ID, "paper_uid": SOURCES["SYED2021"]["paper_uid"], "source_hash": SOURCES["SYED2021"]["source_hash"], "question": "Are single and parallel pass strategies strongly separated?", "result": "abstract reports the two were very similar relative to oscillation", "evidence_level": "DIRECT_ABSTRACT_TEXT", "support_domain": "Syed WAAM as-built", "reason_not_headline": "raw curve-level effect unavailable", "source_locator": "Abstract"},
]
write_csv("NULL_NEGATIVE_RESULTS.csv", null_rows, null_fields)

conflict_fields = ["conflict_uid", "snapshot_id", "topic", "source_A", "source_B", "conflict", "impact", "resolution", "status"]
conflicts = [
    {"conflict_uid": "conf_proxy_rank", "snapshot_id": SNAPSHOT_ID, "topic": "thermal proxy ordering", "source_A": "Zhai line energy", "source_B": "Zhai nominal VED", "conflict": "HP ranks hotter by P/v but lower by P/(v*hatch*layer)", "impact": "blocks single-scalar cooling-rate attribution", "resolution": "retain both proxies; require direct sensor/model calibration", "status": "OPEN_HIGH_IMPACT"},
    {"conflict_uid": "conf_cooling_threshold", "snapshot_id": SNAPSHOT_ID, "topic": "martensite cooling-rate threshold", "source_A": "CCT supplement / Ahmed-Rack interpretation", "source_B": "review summaries with different thresholds", "conflict": "reported phase-regime thresholds depend on source and phase nomenclature", "impact": "blocks universal threshold imputation", "resolution": "keep as database prior; do not assign sample cooling rate from phase alone", "status": "OPEN"},
    {"conflict_uid": "conf_lin_extreme", "snapshot_id": SNAPSHOT_ID, "topic": "build-position effect", "source_A": "Lin text", "source_B": "requested build-height curve", "conflict": "only bottom minimum and top maximum are available, not regional means", "impact": "average slope not identifiable", "resolution": "plot and label extrema; exclude from headline causal estimate", "status": "RESOLVED_BY_DOWNGRADE"},
    {"conflict_uid": "conf_raw_hash", "snapshot_id": SNAPSHOT_ID, "topic": "source identity", "source_A": "file-library source pointer", "source_B": "required raw source_hash", "conflict": "raw PDF/ZIP hashes unavailable in fallback runtime", "impact": "prevents authoritative snapshot promotion", "resolution": "use identity fingerprints and request local hash-bound absorption", "status": "OPEN_BLOCKING_PROMOTION"},
]
write_csv("CONFLICT_LEDGER.csv", conflicts, conflict_fields)

# ---------------------------------------------------------------------------
# Figure data and standalone plotting code.
# ---------------------------------------------------------------------------
dag_nodes = [
    {"node": "domain", "label": "Equipment / geometry / material domain", "x": 0.08, "y": 0.82, "kind": "domain"},
    {"node": "settings", "label": "Power, speed, feed, hatch, layer, dwell", "x": 0.08, "y": 0.52, "kind": "observed"},
    {"node": "sensors", "label": "Thermocouple / pyrometry / melt-pool sensing", "x": 0.08, "y": 0.22, "kind": "direct"},
    {"node": "proxies", "label": "Line energy, VED, build height, band spacing", "x": 0.39, "y": 0.68, "kind": "proxy"},
    {"node": "latent", "label": "Latent thermal history: T(t), cooling rate, G/R, cycles", "x": 0.39, "y": 0.34, "kind": "latent"},
    {"node": "micro", "label": "Microstructure: beta grains, alpha laths, bands, phases", "x": 0.70, "y": 0.55, "kind": "outcome"},
    {"node": "perf", "label": "Performance: YS, UTS, EL, hardness, fatigue", "x": 0.70, "y": 0.22, "kind": "outcome"},
    {"node": "missing", "label": "Missingness / calibration error / extrapolation", "x": 0.39, "y": 0.05, "kind": "uncertainty"},
]
dag_edges = [
    {"source": "domain", "target": "settings", "label": "constrains"},
    {"source": "domain", "target": "sensors", "label": "calibrates"},
    {"source": "domain", "target": "proxies", "label": "defines validity"},
    {"source": "settings", "target": "proxies", "label": "derived"},
    {"source": "settings", "target": "latent", "label": "causal input"},
    {"source": "sensors", "target": "latent", "label": "direct evidence"},
    {"source": "proxies", "target": "latent", "label": "imperfect inference"},
    {"source": "latent", "target": "micro", "label": "phase/solidification path"},
    {"source": "latent", "target": "perf", "label": "residual/defect path"},
    {"source": "micro", "target": "perf", "label": "mediates"},
    {"source": "missing", "target": "latent", "label": "widens interval"},
    {"source": "missing", "target": "perf", "label": "prediction UQ"},
]
write_csv("figure_data/thermal_proxy_dag_nodes.csv", dag_nodes)
write_csv("figure_data/thermal_proxy_dag_edges.csv", dag_edges)
write_csv("figure_data/build_position_curve.csv", [
    {"normalized_build_position": 0.0, "prior_beta_grain_length_mm": 0.86, "point_semantics": "bottom observed minimum", "paper_uid": SOURCES["LIN2016"]["paper_uid"], "independent_papers": 1},
    {"normalized_build_position": 1.0, "prior_beta_grain_length_mm": 6.90, "point_semantics": "top observed maximum", "paper_uid": SOURCES["LIN2016"]["paper_uid"], "independent_papers": 1},
])
write_csv("figure_data/thermal_cycle_onset.csv", [
    {"total_layers": 1, "visible_layer_band": 0, "build_height_mm": 1.7, "evidence": "direct separate coupon"},
    {"total_layers": 3, "visible_layer_band": 0, "build_height_mm": 3.7, "evidence": "direct separate coupon"},
    {"total_layers": 4, "visible_layer_band": 1, "build_height_mm": 6.4, "evidence": "direct separate coupon"},
])
write_csv("figure_data/missingness_waterfall.csv", [
    {"step": "Heat-treatment state", "incremental_width_MPa": 30, "cumulative_width_MPa": 30},
    {"step": "Process / thermal-proxy bundle", "incremental_width_MPa": 31, "cumulative_width_MPa": 61},
    {"step": "Manufacturing domain", "incremental_width_MPa": 12, "cumulative_width_MPa": 73},
])

plot_dag = r'''from pathlib import Path
import csv
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
BASE = Path(__file__).resolve().parents[1]
with (BASE/'figure_data/thermal_proxy_dag_nodes.csv').open(encoding='utf-8-sig') as f:
    nodes = list(csv.DictReader(f))
with (BASE/'figure_data/thermal_proxy_dag_edges.csv').open(encoding='utf-8-sig') as f:
    edges = list(csv.DictReader(f))
pos = {r['node']:(float(r['x']),float(r['y'])) for r in nodes}
fig, ax = plt.subplots(figsize=(12,7))
for e in edges:
    x1,y1 = pos[e['source']]; x2,y2 = pos[e['target']]
    arr = FancyArrowPatch((x1+0.10,y1),(x2-0.02,y2),arrowstyle='-|>',mutation_scale=12,linewidth=1.1,connectionstyle='arc3,rad=0.05')
    ax.add_patch(arr)
for r in nodes:
    x,y = pos[r['node']]
    box = FancyBboxPatch((x,y),0.22,0.10,boxstyle='round,pad=0.015',linewidth=1.2,facecolor='white')
    ax.add_patch(box)
    ax.text(x+0.11,y+0.05,r['label'],ha='center',va='center',fontsize=9,wrap=True)
ax.set_title('Thermal-History Proxy DAG | 4 primary papers | calibration domain retained',fontsize=13)
ax.text(0.01,0.01,'Proxy variables are not direct physical measurements; arrows encode the analysis model, not proven causal magnitudes.',transform=ax.transAxes,fontsize=9)
ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
for ext in ['png','pdf','svg']:
    fig.savefig(BASE/f'figures/QM27_F1_thermal_proxy_DAG.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
plt.close(fig)
'''
plot_build = r'''from pathlib import Path
import csv
import matplotlib.pyplot as plt
BASE = Path(__file__).resolve().parents[1]
with (BASE/'figure_data/build_position_curve.csv').open(encoding='utf-8-sig') as f:
    rows=list(csv.DictReader(f))
x=[float(r['normalized_build_position']) for r in rows]
y=[float(r['prior_beta_grain_length_mm']) for r in rows]
fig,ax=plt.subplots(figsize=(8,5.5))
ax.plot(x,y,marker='o')
for r,xx,yy in zip(rows,x,y):
    ax.annotate(r['point_semantics'],(xx,yy),xytext=(8,8),textcoords='offset points',fontsize=9)
ax.set_xlabel('Normalized build position')
ax.set_ylabel('Prior beta grain length (mm)')
ax.set_title('Build Position–Microstructure Support Range | n=1 independent paper')
ax.text(0.02,0.96,'Observed extrema, not regional means; no average slope or causal effect.',transform=ax.transAxes,va='top',fontsize=9)
ax.set_xlim(-0.05,1.05); ax.grid(True,alpha=0.3)
for ext in ['png','pdf','svg']:
    fig.savefig(BASE/f'figures/QM27_F2_build_position_microstructure.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
plt.close(fig)
'''
plot_cycle = r'''from pathlib import Path
import csv
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parents[1]
with (BASE/'figure_data/thermal_cycle_onset.csv').open(encoding='utf-8-sig') as f:
    rows=list(csv.DictReader(f))
x=[int(r['total_layers']) for r in rows]
y=[int(r['visible_layer_band']) for r in rows]
fig,ax=plt.subplots(figsize=(8,5.5))
ax.step(x,y,where='post',linewidth=2)
ax.scatter(x,y,s=55)
ax.axvspan(3,4,alpha=0.15)
ax.text(3.05,0.55,'Onset bracket: 3 < layers <= 4',fontsize=10)
ax.set_xlabel('Total deposited layers in separate PPAM coupons')
ax.set_ylabel('Visible layer band (0/1)')
ax.set_yticks([0,1],labels=['Absent','Present'])
ax.set_xticks([1,3,4])
ax.set_title('Cumulative Thermal-Cycle Proxy | n=1 independent paper')
ax.text(0.02,0.96,'Layer count bundles thermal exposure and geometry; threshold is device-specific.',transform=ax.transAxes,va='top',fontsize=9)
ax.set_ylim(-0.15,1.15); ax.grid(True,axis='x',alpha=0.3)
for ext in ['png','pdf','svg']:
    fig.savefig(BASE/f'figures/QM27_F3_thermal_cycle_onset.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
plt.close(fig)
'''
plot_waterfall = r'''from pathlib import Path
import csv
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parents[1]
with (BASE/'figure_data/missingness_waterfall.csv').open(encoding='utf-8-sig') as f:
    rows=list(csv.DictReader(f))
labels=[r['step'] for r in rows]
inc=[float(r['incremental_width_MPa']) for r in rows]
starts=[]; s=0
for v in inc:
    starts.append(s); s+=v
fig,ax=plt.subplots(figsize=(9,5.5))
ax.bar(range(len(inc)),inc,bottom=starts)
for i,(b,v) in enumerate(zip(starts,inc)):
    ax.text(i,b+v/2,f'+{v:.0f}',ha='center',va='center',fontsize=10)
ax.plot(range(len(inc)),[b+v for b,v in zip(starts,inc)],marker='o')
ax.set_xticks(range(len(labels)),labels=labels,rotation=15,ha='right')
ax.set_ylabel('UTS empirical support-interval width (MPa)')
ax.set_title('Missing Thermal-History Uncertainty Waterfall | Zhai Table 2 | n=1 paper')
ax.text(0.02,0.96,'Support-set widening, not a confidence or prediction interval.',transform=ax.transAxes,va='top',fontsize=9)
ax.set_ylim(0,82); ax.grid(True,axis='y',alpha=0.3)
for ext in ['png','pdf','svg']:
    fig.savefig(BASE/f'figures/QM27_F4_missing_thermal_history_UQ.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
plt.close(fig)
'''
for name, code in [
    ("plot_thermal_proxy_dag.py", plot_dag), ("plot_build_position.py", plot_build),
    ("plot_thermal_cycle.py", plot_cycle), ("plot_missingness_waterfall.py", plot_waterfall),
]:
    write_text(f"plot_code/{name}", code)
    runpy.run_path(str(OUT / "plot_code" / name), run_name="__main__")

plot_specs = {
    "window_id": WINDOW_ID,
    "snapshot_id": SNAPSHOT_ID,
    "global_rules": {"language": "English", "formats": ["SVG", "PDF", "PNG"], "png_dpi": 600, "generative_image_used": False},
    "plots": [
        {"id": "QM27_F1", "title": "Thermal-History Proxy DAG", "data": ["figure_data/thermal_proxy_dag_nodes.csv", "figure_data/thermal_proxy_dag_edges.csv"], "code": "plot_code/plot_thermal_proxy_dag.py", "independent_papers": 4, "effect_definition": "analysis DAG", "evidence_layer": "P0/P1", "support_domain": "LENS/PPAM/laser-cladding/WAAM with domain nodes"},
        {"id": "QM27_F2", "title": "Build Position–Microstructure Support Range", "data": ["figure_data/build_position_curve.csv"], "code": "plot_code/plot_build_position.py", "independent_papers": 1, "effect_definition": "top observed maximum minus bottom observed minimum", "evidence_layer": "DIRECT_TABLE_TEXT", "support_domain": "Lin PPAM wall; extrema only"},
        {"id": "QM27_F3", "title": "Cumulative Thermal-Cycle Proxy", "data": ["figure_data/thermal_cycle_onset.csv"], "code": "plot_code/plot_thermal_cycle.py", "independent_papers": 1, "effect_definition": "layer-band visibility change-point", "evidence_layer": "DIRECT_TEXT_FIGURE", "support_domain": "Lin PPAM layer-count coupons"},
        {"id": "QM27_F4", "title": "Missing Thermal-History Uncertainty Waterfall", "data": ["figure_data/missingness_waterfall.csv"], "code": "plot_code/plot_missingness_waterfall.py", "independent_papers": 1, "effect_definition": "empirical support interval widening", "evidence_layer": "DIRECT_TABLE_TEXT", "support_domain": "Zhai Table 2 only"},
    ],
}
write_json("PLOT_SPECS.json", plot_specs)

# ---------------------------------------------------------------------------
# Narrative and methods.
# ---------------------------------------------------------------------------
executive = f"""# QM27 Executive Verdict

`WINDOW=QM27 | SNAPSHOT={SNAPSHOT_ID} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Quantitative answer

Missing thermal history can be partially reconstructed, but only as a **domain-calibrated interval-valued latent variable**. The strongest direct same-build estimand is the local reheating contrast in Zhai et al.: in the high-power LENS condition, alpha-lath thickness increases from **0.79 to 1.06 um** between the within-layer region and the interlayer micro-HAZ, giving **Delta=+0.27 um, lnRR={math.log(1.06/0.79):.3f}, +{(1.06/0.79-1)*100:.2f}%**. In the low-power condition, the within-layer value is right-censored (`<0.73 um`), so the corresponding effect is conservatively **Delta>=+0.13 um and >=+17.81%**. These are level-2 same-paper paired associations, not universal cooling-rate coefficients.

Lin et al. provide a second, non-equivalent cycle proxy: layer bands are absent in separate one- and three-layer PPAM coupons and appear after the fourth layer, bracketing the device-specific visibility onset at **3 < total layers <= 4**. The measured layer-band spacing is **1.40±0.40 mm** versus a programmed **1.5 mm** layer increment (ratio **0.933**), supporting layer-band spacing as an in-domain reheating-isotherm proxy. The reported prior-beta grain-length support range expands from a **0.86 mm bottom-region minimum** to a **6.90 mm top-region maximum**, but these are extrema rather than regional means and therefore do not identify an average build-height slope.

A decisive contradiction is exposed by the Zhai process settings. Derived line energy ranks the high-power regime above low power (**58.5 vs 33.0 J/mm**), whereas nominal volumetric energy density ranks it below (**146.25 vs 220.0 J/mm3**). Because powder feed, layer thickness, hatch spacing and speed also change, no single scalar process proxy can be treated as cooling rate. Direct sensor/model calibration is required. Tran et al. supply such a calibration example: a K-thermocouple 3 mm below the cup records **Tmax=1053 K** and **Tend=973 K**, while the 3D thermal model uses a sensor-calibrated absorptivity of **0.35**. Its validity remains tied to the same machine, geometry, path and boundary conditions.

## Missingness uncertainty

Within Zhai Table 2, progressively hiding the heat-treatment state, process/thermal-proxy bundle and manufacturing domain widens the empirical UTS support interval from **0 to 30 to 61 to 73 MPa**. This is an observed support-set waterfall, not a confidence or prediction interval. Cross-paper UQ, random-effects variance, LOPO-stable coefficients and G/R reconstruction remain `NOT_IDENTIFIABLE` because the authoritative V29 atomic snapshot, raw source hashes and semantically matched multi-paper effects were unavailable.

## Claim ceiling

Maximum claim level: **2 — same-paper paired association**. Thermal proxies are not direct physical measurements. No Gold promotion, production-model registration, recipe validation or cross-device thermal imputation was performed.

`STATUS: {STATUS}`
"""
write_text("00_EXECUTIVE_VERDICT.md", executive)

methods = f"""# Methods

## 1. Scope and immutable analysis state

The analysis addresses four estimands: thermal-proxy association with microstructure/performance, build-position effects, cumulative cycle effects, and the uncertainty increment caused by missing thermal history. All rows are bound to `{SNAPSHOT_ID}`. Because raw archive hashes could not be read in the fallback runtime, `source_hash` is an explicitly labeled identity fingerprint; it is not misrepresented as a raw-file SHA-256.

## 2. Evidence hierarchy

Primary originals (Zhai 2016; Lin 2016; Tran 2017; Syed 2021; Cao 2023) dominate numerical and mechanistic claims. Zarei 2025 is used as a source locator and secondary sensitivity source only. Project `figure_evidence.jsonl` is registered as P1 structured evidence but cannot override original documents. Review-derived Carroll values are excluded from headline estimates until the original paper is verified.

## 3. Atomicity and matching

An atomic row is paper x sample x process/thermal state x location x test/property. Same-build local regions form the highest-quality thermal-cycle contrasts. Process-bundle comparisons remain paired but are downgraded because multiple process variables co-vary. The Lin bottom/top grain values are retained as extrema, not means. Elongation differences use percentage points for the absolute effect and lnRR only as a secondary ratio when values are positive.

## 4. Effect calculations

For positive continuous outcomes: `DeltaY = Y1-Y0`, `lnRR = ln(Y1/Y0)`, and `% change = 100*(exp(lnRR)-1)`. For the low-power lath value, the reported `<0.73 um` is treated as a right-censored control upper bound, yielding lower-bound effects. Reported standard deviations are not converted to standard errors or confidence intervals when replicate counts are unavailable.

## 5. Thermal proxy construction

Line energy is `P/v`; nominal volumetric energy density is `P/(v*hatch*layer thickness)`. Both are retained because their ordering conflict is scientifically informative. Layer-band spacing is compared with programmed delta-Z only in the same PPAM domain. Build height and layer count are ordinal/positional proxies. Direct thermocouple traces are direct only at the sensor location; spatial fields require a validated model. G, R, G/R and GxR are left unresolved when raw validated fields are missing.

## 6. Missingness UQ

Missingness is represented by empirical within-paper support intervals rather than point imputation. The waterfall starts from a fully specified Zhai UTS condition and expands the candidate set as heat-treatment state, process regime and manufacturing domain are hidden. It is not a probabilistic CI or PI.

## 7. Hierarchical and sensitivity analysis

Outcome-specific random-effects models require at least two independent papers with semantically equivalent estimands. That requirement is not met; numerical pooling is therefore `NOT_IDENTIFIABLE`. LOPO is executed as an evidence-deletion stress test and shows complete collapse of each headline estimand when its sole contributing paper is removed. Proxy-definition, censoring and evidence-level sensitivities are reported separately.

## 8. Reproducibility

All figures are generated from CSV data by standalone Python scripts and exported to SVG, PDF and 600-dpi PNG. `analysis_code/recompute.py` recomputes key effects; `analysis_code/validate_package.py` checks required outputs and checksums. The package is a non-nested ZIP.
"""
write_text("METHODS.md", methods)

limitations = """# Limitations

1. The authoritative V29 `ATOMIC_RECORDS`, `PROVENANCE.jsonl`, conflict/exclusion ledgers and a raw-hash-bound Q40 snapshot were not accessible. The return is a derived cohort, not an authoritative Gold update.
2. The local container could not perform member-level inspection of the 26 declared project ZIPs. Every package is registered in `INPUT_LEDGER.csv`, but no CRC/testzip/member-coverage claim is fabricated.
3. Most estimands have one independent paper. Random-effects variance, cluster bootstrap, prediction intervals and conventional LOPO performance cannot be estimated.
4. Zhai low- and high-power conditions change power, speed, powder feed, layer thickness and hatch spacing simultaneously. Cooling rate is not isolated.
5. The low-power within-layer lath thickness is censored (`<0.73 um`). Its effect is a lower bound.
6. Lin build-position values are extrema, not regional means. The plotted line is a support-range visualization, not a fitted height-response curve.
7. Review-derived Carroll build-position values are retained only as secondary candidates and are barred from headline conclusions pending original-paper verification.
8. Thermocouple data are location-specific. Melt-pool peaks and spatial thermal histories require a validated model and uncertainty propagation.
9. G/R and GxR values are unresolved. Process parameters alone are insufficient to reconstruct them reliably.
10. No production model, validated recipe, Gold row or ACTIVE pointer was created or modified.
"""
write_text("LIMITATIONS.md", limitations)

local_prompt = f"""# Local Absorption Prompt — QM27

Absorb `FINAL_QM27.zip` only into the exclusive `q40/QM27` return zone. Do not promote any row to Gold or register a production model.

1. Verify the external ZIP SHA-256 and `zipfile.testzip()`; reject on mismatch.
2. Bind the return to `{SNAPSHOT_ID}` and compare it against the authoritative `Q40_INPUT_SNAPSHOT`. This derived snapshot must not replace the authoritative snapshot.
3. Resolve every `INPUT_LEDGER.csv` row marked `BLOCKED_RUNTIME_MEMBER_AUDIT` by member-level ZIP inventory, CRC, raw SHA-256, and relevant-member extraction.
4. Join authoritative V29 atomic records/provenance/conflict/exclusion ledgers using DOI + paper/sample/condition identities. Never join only by title.
5. Replace identity fingerprints with raw source hashes while preserving both old and new identifiers in a lineage table.
6. Verify original Wang 2019, Carroll 2015, Lei, Akerfeldt, Yi and sensor/model sources; downgrade or remove any secondary-only row that fails.
7. Rerun `analysis_code/recompute.py`, all four plotting scripts and `analysis_code/validate_package.py`.
8. Only after at least two independent papers share an equivalent estimand, fit paper-cluster/hierarchical models and compute LOPO, CI and PI.
9. Return a delta ledger and do not mutate ACTIVE_TITMC, unified Schema or production model registry without separate authorization.
"""
write_text("LOCAL_ABSORPTION_PROMPT.md", local_prompt)

web_request = {
    "window_id": WINDOW_ID,
    "snapshot_id": SNAPSHOT_ID,
    "status": STATUS,
    "required": [
        {"priority": 1, "object": "V29_ATOMIC_RECORDS", "reason": "authoritative paper/sample/condition cohort and duplicate lineage"},
        {"priority": 1, "object": "V29_PROVENANCE_JSONL", "reason": "raw table/text/figure bindings and source SHA"},
        {"priority": 1, "object": "V29_CONFLICT_LEDGER_AND_EXCLUDED_RECORDS", "reason": "admission, exclusion and dependency decisions"},
        {"priority": 1, "object": "Q40_INPUT_SNAPSHOT_AND_RAW_PACKAGE_HASHES", "reason": "replace identity fingerprints and bind all windows to one immutable snapshot"},
        {"priority": 1, "object": "PRIMARY_ORIGINALS", "identifiers": ["10.1016/j.msea.2019.754.735", "10.1016/j.actamat.2014.12.054", "Lei WAAM deposition-rate study", "Akerfeldt 2016 MSEA 674:428-437", "Yi WAAM water-cooling study"], "reason": "verify build-height, dwell, cooling-rate and property effects now available only through a review"},
        {"priority": 1, "object": "DIRECT_THERMAL_FIELDS", "fields": ["T(x,y,z,t)", "cooling_rate", "G", "R", "G/R", "GxR", "interpass_temperature", "sensor_location", "model_residuals"], "reason": "calibrate proxies and quantify thermal missingness"},
        {"priority": 2, "object": "REPLICATE_LEVEL_MICROSTRUCTURE_AND_PROPERTIES", "fields": ["n", "raw lath measurements", "regional means", "within-paper covariance"], "reason": "cluster uncertainty, CI and prediction interval"},
    ],
    "acceptance": "hash-bound objects; stable paper/sample/condition IDs; no loose manual values; member-level CRC and independent recomputation",
    "next_action": "LOCAL_ABSORB_HASH_BIND_AND_RERUN_QM27_HIERARCHICAL_UQ",
}
write_json("WEB_TO_LOCAL_REQUEST.json", web_request)

# Common files that remain schema-valid but explicitly non-identifiable.
write_csv("DOSE_RESPONSE.csv", dose_rows, dose_fields)  # retained after narrative writes

# Provenance JSONL.
prov_entries = []
for key, s in SOURCES.items():
    prov_entries.append({
        "provenance_uid": "prov_" + sha256_text(key)[:16], "snapshot_id": SNAPSHOT_ID,
        "paper_uid": s["paper_uid"], "source_hash": s["source_hash"], "hash_scope": s["hash_scope"],
        "source_pointer": s["source_pointer"], "source_type": s["source_type"], "title": s["title"],
        "opened": True, "numeric_use": key in {"ZHAI2016", "LIN2016", "TRAN2017"},
        "restriction": "review/reference only" if key in {"ZAREI2025", "CAO2023", "CCTSUPP", "FIGEVIDENCE"} else "primary source",
    })
with (OUT / "PROVENANCE.jsonl").open("w", encoding="utf-8") as f:
    for row in prov_entries:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

source_matrix = []
for row in input_ledger:
    source_matrix.append({
        "source": row["input_name"], "category": row["category"], "terminal_state": row["terminal_state"],
        "used_for_values": "YES" if row["terminal_state"] == "USED_DIRECTLY" and row["category"] == "paper_or_structured_evidence" else "NO",
        "used_for_methods": "YES" if row["terminal_state"] in {"USED_DIRECTLY", "USED_AS_REFERENCE", "USED_AS_REFERENCE_WITH_MEMBER_AUDIT_GAP"} else "NO",
        "exclusion_or_gap": row["reason_or_gap"],
    })
write_csv("SOURCE_COVERAGE_MATRIX.csv", source_matrix)
write_text("OPENED_FILES.txt", "\n".join([
    "QM27 dispatch Markdown (direct upload)",
    "Zhai et al. 2016 DOI 10.1016/j.ijfatigue.2016.08.009 — full PDF opened multimodally",
    "Lin et al. 2016 DOI 10.1016/j.matdes.2016.04.018 — full PDF opened multimodally",
    "Tran et al. 2017 DOI 10.1016/j.matdes.2017.04.092 — full PDF opened multimodally",
    "Syed et al. 2021 DOI 10.1016/j.msea.2021.141194 — original abstract/full source pointer opened",
    "Zarei et al. 2025 DOI 10.1016/j.jmrt.2025.05.106 — full review opened for source navigation",
    "Cao et al. 2023 DOI 10.1038/s41524-023-01152-y — primary method context opened",
    "CCT supplementary evidence DOI 10.1016/j.ijfatigue.2019.105358 — parsed supplement opened",
    "Project figure_evidence.jsonl — thermal simulation/GxR registry snippets opened",
]))

pdf_qa = {
    "snapshot_id": SNAPSHOT_ID,
    "visual_review": [
        {"source": "Zhai2016", "pages": [2, 4, 5, 8, 9], "objects": ["Table 1", "Fig. 5", "Fig. 7", "Table 2"], "status": "reviewed"},
        {"source": "Lin2016", "pages": [5, 6, 8, 9, 10, 13, 14, 15, 17], "objects": ["Table 2", "Fig. 3", "Table 3", "Fig. 4", "Fig. 8", "Fig. 10"], "status": "reviewed"},
        {"source": "Tran2017", "pages": [7, 8, 12, 30], "objects": ["Fig. 1", "Table 1", "Fig. 2", "Fig. 13"], "status": "reviewed"},
        {"source": "Zarei2025", "pages": [1, 4, 6, 8, 9, 12, 13, 15], "objects": ["Figs. 2,4,6,9,10", "Table 2"], "status": "review/source-navigation only"},
    ],
    "warning": "Page numbers follow rendered document pages supplied by the file viewer; raw PDF SHA unavailable.",
}
write_json("PDF_VISUAL_QA.json", pdf_qa)

snapshot_validation = {
    "window_id": WINDOW_ID, "snapshot_id": SNAPSHOT_ID, "snapshot_type": "DERIVED_WEB_COHORT",
    "authoritative_q40_snapshot_present": False, "raw_source_hashes_present": False,
    "identity_fingerprints_present": True, "numeric_anchor_hash": sha256_text(json.dumps(snapshot_payload["frozen_numeric_anchors"], sort_keys=True)),
    "status": "PASS_FOR_DERIVED_ANALYSIS_ONLY", "promotion_allowed": False,
}
write_json("SNAPSHOT_VALIDATION.json", snapshot_validation)

# Recompute and package validation scripts.
recompute_code = r'''from pathlib import Path
import csv, math
BASE=Path(__file__).resolve().parents[1]
with (BASE/'EFFECT_ESTIMATES.csv').open(encoding='utf-8-sig') as f:
    rows=list(csv.DictReader(f))
def row(est):
    return next(r for r in rows if r['estimand']==est)
hp=row('E[lath thickness | micro-HAZ] - E[lath thickness | within layer] in the same high-power build')
assert abs(float(hp['delta'])-0.27)<1e-9
assert abs(float(hp['percent_change'])-100*(1.06/0.79-1))<1e-5
lp=row('lower bound for micro-HAZ minus within-layer lath thickness in the same low-power build')
assert float(lp['delta'])==0.13 and lp['effect_lower']=='>=0.13'
line_lp=330/(0.6*1000/60)
line_hp=780/(0.8*1000/60)
ved_lp=330/((0.6*1000/60)*0.5*0.3)
ved_hp=780/((0.8*1000/60)*1.0*0.4)
assert abs(line_lp-33.0)<1e-9 and abs(line_hp-58.5)<1e-9
assert abs(ved_lp-220.0)<1e-9 and abs(ved_hp-146.25)<1e-9
print('PASS: key effects and contradictory proxy rankings recomputed')
'''
validate_code = r'''from pathlib import Path
import csv, hashlib, json
BASE=Path(__file__).resolve().parents[1]
required=[
'00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv',
'HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv',
'NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json',
'WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256',
'THERMAL_PROXY_REGISTRY.csv','BUILD_POSITION_EFFECTS.csv','THERMAL_CYCLE_EFFECTS.csv','THERMAL_MISSINGNESS_UQ.csv']
missing=[p for p in required if not (BASE/p).exists()]
assert not missing, missing
for stem in ['QM27_F1_thermal_proxy_DAG','QM27_F2_build_position_microstructure','QM27_F3_thermal_cycle_onset','QM27_F4_missing_thermal_history_UQ']:
    for ext in ['png','pdf','svg']:
        assert (BASE/'figures'/f'{stem}.{ext}').exists()
with (BASE/'CHECKSUMS.sha256').open(encoding='utf-8') as f:
    for line in f:
        h,rel=line.rstrip().split('  ',1)
        got=hashlib.sha256((BASE/rel).read_bytes()).hexdigest()
        assert got==h,(rel,h,got)
with (BASE/'WINDOW_STATUS.json').open(encoding='utf-8') as f:
    status=json.load(f)
assert status['window_id']=='QM27'
assert status['claim_level_max']==2
with (BASE/'ANALYSIS_COHORT.csv').open(encoding='utf-8-sig') as f:
    assert sum(1 for _ in csv.DictReader(f))>=30
print('PASS: required files, figures, schemas, status and checksums')
'''
write_text("analysis_code/recompute.py", recompute_code)
write_text("analysis_code/validate_package.py", validate_code)
write_text("ACCEPTANCE_COMMANDS.md", """# Acceptance Commands

```bash
python3 analysis_code/recompute.py
python3 plot_code/plot_thermal_proxy_dag.py
python3 plot_code/plot_build_position.py
python3 plot_code/plot_thermal_cycle.py
python3 plot_code/plot_missingness_waterfall.py
python3 analysis_code/validate_package.py
```

External ZIP check:

```bash
sha256sum -c FINAL_QM27.sha256
python3 - <<'PY'
import zipfile
with zipfile.ZipFile('FINAL_QM27.zip') as z:
    assert z.testzip() is None
    assert not any(n.lower().endswith('.zip') for n in z.namelist())
print('PASS')
PY
```
""")

# Window status before manifest/checksums.
window_status = {
    "window_id": WINDOW_ID, "snapshot_id": SNAPSHOT_ID, "papers_seen": len(SOURCES),
    "papers_included": 6, "independent_papers": 4, "atomic_rows": len(cohort), "matched_pairs": len(pairs),
    "effect_estimates": len(effects), "plots_generated": 4, "open_conflicts": sum(1 for c in conflicts if c["status"].startswith("OPEN")),
    "claim_level_max": 2, "status": STATUS,
    "next_action": "LOCAL_ABSORB_HASH_BIND_AND_RERUN_QM27_HIERARCHICAL_UQ",
    "production_model_registered": False, "gold_promoted": False,
}
write_json("WINDOW_STATUS.json", window_status)
write_text("RUN_LOG.txt", f"generated_at={GENERATED_AT}\nwindow={WINDOW_ID}\nsnapshot={SNAPSHOT_ID}\nstatus={STATUS}\nplots=4\n")
write_text("README.md", f"""# FINAL_QM27

Derived, source-grounded quantitative return for cooling-rate, thermal-cycle, interpass-temperature and build-position latent reconstruction.

Snapshot: `{SNAPSHOT_ID}`  
Status: `{STATUS}`  
Claim ceiling: level 2 same-paper paired association.

Start with `00_EXECUTIVE_VERDICT.md`; reproduce with `ACCEPTANCE_COMMANDS.md`.
""")

# Run recomputation before manifest.
import contextlib, io
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    runpy.run_path(str(OUT / "analysis_code" / "recompute.py"), run_name="__main__")
write_text("RECOMPUTE_OUTPUT.txt", buf.getvalue().strip())

# Manifest excludes itself and CHECKSUMS to avoid recursion.
manifest_files = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"}:
        rel = p.relative_to(OUT).as_posix()
        manifest_files.append({"path": rel, "size_bytes": p.stat().st_size, "sha256": sha256_bytes(p.read_bytes())})
manifest = {
    "window_id": WINDOW_ID, "snapshot_id": SNAPSHOT_ID, "generated_at": GENERATED_AT,
    "status": STATUS, "manifest_self_excluded": True, "checksums_self_excluded": True,
    "file_count_before_manifest_and_checksums": len(manifest_files), "files": manifest_files,
}
write_json("MANIFEST.json", manifest)

checksum_lines = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name != "CHECKSUMS.sha256":
        checksum_lines.append(f"{sha256_bytes(p.read_bytes())}  {p.relative_to(OUT).as_posix()}")
write_text("CHECKSUMS.sha256", "\n".join(checksum_lines))

# Validate and record validation output. Adding TEST_OUTPUT requires checksum regeneration.
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    runpy.run_path(str(OUT / "analysis_code" / "validate_package.py"), run_name="__main__")
write_text("TEST_OUTPUT.txt", buf.getvalue().strip())
# Refresh manifest and checksums to include TEST_OUTPUT.
manifest_files = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"}:
        manifest_files.append({"path": p.relative_to(OUT).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha256_bytes(p.read_bytes())})
manifest["file_count_before_manifest_and_checksums"] = len(manifest_files)
manifest["files"] = manifest_files
write_json("MANIFEST.json", manifest)
checksum_lines = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name != "CHECKSUMS.sha256":
        checksum_lines.append(f"{sha256_bytes(p.read_bytes())}  {p.relative_to(OUT).as_posix()}")
write_text("CHECKSUMS.sha256", "\n".join(checksum_lines))
# Final validation after checksum refresh.
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    runpy.run_path(str(OUT / "analysis_code" / "validate_package.py"), run_name="__main__")
write_text("TEST_OUTPUT.txt", buf.getvalue().strip())
# One final checksum refresh because TEST_OUTPUT was rewritten.
checksum_lines = []
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name != "CHECKSUMS.sha256":
        checksum_lines.append(f"{sha256_bytes(p.read_bytes())}  {p.relative_to(OUT).as_posix()}")
write_text("CHECKSUMS.sha256", "\n".join(checksum_lines))

# Non-nested ZIP.
with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            z.write(p, arcname=p.relative_to(OUT).as_posix())
with zipfile.ZipFile(ZIP_PATH) as z:
    assert z.testzip() is None
    assert not any(n.lower().endswith(".zip") for n in z.namelist())
zip_sha = sha256_bytes(ZIP_PATH.read_bytes())
ZIP_SHA_PATH.write_text(f"{zip_sha}  FINAL_QM27.zip\n", encoding="utf-8")
summary = {
    "window_id": WINDOW_ID, "snapshot_id": SNAPSHOT_ID, "status": STATUS, "zip": ZIP_PATH.name,
    "zip_sha256": zip_sha, "zip_size_bytes": ZIP_PATH.stat().st_size,
    "zip_entries": len(zipfile.ZipFile(ZIP_PATH).namelist()), "testzip": "PASS", "nested_zip": False,
    "atomic_rows": len(cohort), "matched_pairs": len(pairs), "effect_estimates": len(effects),
    "plots": 4, "claim_level_max": 2, "next_action": window_status["next_action"],
}
SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
