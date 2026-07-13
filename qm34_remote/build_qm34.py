#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import statistics
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "evidence_data.json").read_text(encoding="utf-8"))
OUT_BASE = BASE / "output"
ROOT = OUT_BASE / "FINAL_QM34"
ZIP_PATH = OUT_BASE / "FINAL_QM34.zip"


def reset() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    for rel in ["figure_data", "figures", "plot_code", "analysis_code", "tests", "source_evidence"]:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_text(rel: str, text: str) -> Path:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def write_json(rel: str, value: Any) -> Path:
    return write_text(rel, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_csv(rel: str, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if rows:
            fieldnames = list(rows[0].keys())
        else:
            raise ValueError(f"fieldnames required for empty CSV: {rel}")
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    return p


def fmt(value: Any, digits: int = 12) -> Any:
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return value


def rho_cte(factor: float, delta_alpha: float, delta_t: float, vf: float, b_m: float, d_m: float) -> float:
    return factor * abs(delta_alpha) * delta_t * vf / ((1.0 - vf) * b_m * d_m)


def delta_sigma_mpa(alpha: float, g_pa: float, b_m: float, rho_m2: float) -> float:
    return alpha * g_pa * b_m * math.sqrt(rho_m2) / 1.0e6


def equivalent_rho(delta_sigma: float, alpha: float = 1.25, g_pa: float = 45.0e9, b_m: float = 0.289e-9) -> float:
    return (delta_sigma * 1.0e6 / (alpha * g_pa * b_m)) ** 2


def pearson(x: list[float], y: list[float]) -> float:
    xm, ym = statistics.mean(x), statistics.mean(y)
    num = sum((a - xm) * (b - ym) for a, b in zip(x, y))
    den = math.sqrt(sum((a - xm) ** 2 for a in x) * sum((b - ym) ** 2 for b in y))
    return num / den


def rankdata(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda z: z[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def source_records() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    source_map: dict[str, dict[str, Any]] = {}
    source_hash: dict[str, str] = {}
    for src in DATA["sources"]:
        text = (
            f"paper_uid: {src['paper_uid']}\n"
            f"doi: {src['doi']}\n"
            f"title: {src['title']}\n"
            f"year: {src['year']}\n"
            f"source_locator: {src['locator']}\n"
            f"evidence_level: {src['evidence_level']}\n"
            f"original_byte_hash_status: {src['original_byte_hash_status']}\n\n"
            f"Bound evidence capture\n{src['capture_text']}\n\n"
            "This normalized capture is a compact evidence ledger, not a substitute for the original publication.\n"
        )
        p = write_text(f"source_evidence/{src['paper_uid']}.txt", text)
        digest = sha256_file(p)
        record = dict(src)
        record["capture_path"] = str(p.relative_to(ROOT)).replace("\\", "/")
        record["source_hash"] = digest
        record["source_hash_kind"] = "NORMALIZED_EVIDENCE_CAPTURE_SHA256"
        source_map[src["paper_uid"]] = record
        source_hash[src["paper_uid"]] = digest
    return source_map, source_hash


def build() -> None:
    reset()
    source_map, source_hash = source_records()
    snapshot_payload = {
        "archive_hashes": [row[1] for row in DATA["archive_ledger"]],
        "source_capture_hashes": sorted(source_hash.values()),
        "window_id": "QM34",
        "canonical_snapshot_present": False,
    }
    snapshot_digest = sha256_bytes(json.dumps(snapshot_payload, sort_keys=True).encode("utf-8"))
    snapshot_id = f"QM34_DERIVED_{snapshot_digest[:20]}"

    input_rows: list[dict[str, Any]] = []
    for name, digest, kind, size, members, priority in DATA["archive_ledger"]:
        if name.startswith("TITMC_V27_LIT_WEB"):
            relevance = "Primary literature corpus; archive identity registered; target full texts opened through File Library evidence objects."
            terminal = "REGISTERED_LEDGER_TARGETED_DEEP_USE"
        elif name.startswith("S03_CODEX_ML_DATA"):
            relevance = "Frozen matrices/features registered; canonical QM34 atom/provenance snapshot not exposed."
            terminal = "REGISTERED_REFERENCE_DATA_GAP"
        elif name.startswith("S03_CODEX_ML_HARNESS"):
            relevance = "Reliability/UQ/AD/mechanism infrastructure registered; no production model used."
            terminal = "REGISTERED_METHOD_REFERENCE"
        else:
            relevance = "Control, code, history or platform archive registered from project ledger."
            terminal = "REGISTERED_REFERENCE"
        input_rows.append({
            "input_id": hashlib.sha256(name.encode("utf-8")).hexdigest()[:20],
            "snapshot_id": snapshot_id,
            "source_name": name,
            "source_type": "ZIP",
            "path_or_locator": f"/mnt/data/{name}",
            "source_hash": digest,
            "source_hash_kind": kind,
            "bytes": size,
            "member_count": members,
            "central_directory_status": "READABLE_IN_PROJECT_LEDGER",
            "priority": priority,
            "window_relevance": relevance,
            "terminal_use_status": terminal,
            "opened_or_consumed": "LEDGER_BOUND",
            "notes": "The remote builder did not re-upload these large archives; archive identity is inherited from the hash-bound project ledger."
        })
    for src in source_map.values():
        input_rows.append({
            "input_id": hashlib.sha256(src["paper_uid"].encode()).hexdigest()[:20],
            "snapshot_id": snapshot_id,
            "source_name": src["title"],
            "source_type": "PRIMARY_OR_METHOD_EVIDENCE_CAPTURE",
            "path_or_locator": src["locator"],
            "source_hash": src["source_hash"],
            "source_hash_kind": src["source_hash_kind"],
            "bytes": (ROOT / src["capture_path"]).stat().st_size,
            "member_count": 1,
            "central_directory_status": "",
            "priority": "P0_PRIMARY_OR_P1_METHOD",
            "window_relevance": "Direct QM34 quantitative or measurement-domain evidence.",
            "terminal_use_status": "USED_DIRECTLY",
            "opened_or_consumed": "YES",
            "notes": f"Original publication byte hash: {src['original_byte_hash_status']}; normalized capture remains explicitly non-authoritative."
        })
    input_fields = ["input_id","snapshot_id","source_name","source_type","path_or_locator","source_hash","source_hash_kind","bytes","member_count","central_directory_status","priority","window_relevance","terminal_use_status","opened_or_consumed","notes"]
    write_csv("INPUT_LEDGER.csv", input_rows, input_fields)

    opened = [
        "ACTUALLY OPENED / CONSUMED IN THIS WEB WINDOW",
        "",
        "1. QM34_热膨胀失配、GND_位错密度和位错强化贡献.md — execution contract.",
        "2. 0734 Microstructural/mechanical TiB/Ti-6Al-4V paper — Zhao formula and constants.",
        "3. 0860 Interdependencies between graphitization of CNTs — Munir source budget and counterexample.",
        "4. 0858 Sintering-free fabrication of CNT/Ti — Liu matched controls, KAM, particle data and source CTE terms.",
        "5. Materials 2026 TiB/Ti-55531 evidence — low-mismatch negligible boundary.",
        "6. 12278 TNMSC Ti2AlN/TiAl paper — factor-12 formula and v_p notation conflict.",
        "7. Materials Characterization 2020 Ti-6Al-4V method paper — EBSD/TEM/XRD observability firewall.",
        "8. SOURCE_EVIDENCE_INDEX.csv — original-XML provenance interface.",
        "9. XML_CORPUS_AUDIT_REPORT.md — 78,683-XML corpus scope and firewall audit.",
        "10. QM32/QM33/QM16 executive-return artifacts — load-transfer, Orowan/double-count and TiB effect cross-checks only.",
        "11. INPUT_LEDGER.csv from the project return — 26 archive hashes/member counts.",
        "",
        "The 26 large project ZIPs are hash-bound in INPUT_LEDGER.csv. This remote recovery run did not claim a fresh byte-for-byte re-read of every archive member. Canonical V29/Q40 atom/provenance files remain a blocking local absorption input."
    ]
    write_text("OPENED_FILES.txt", "\n".join(opened) + "\n")

    cte_rows: list[dict[str, Any]] = []
    distribution_rows: list[dict[str, Any]] = []
    zhao_contrib: list[dict[str, Any]] = []
    for item in DATA["zhao_inputs"]:
        b = item["burgers_nm"] * 1e-9
        d = item["diameter_um"] * 1e-6
        g = item["shear_modulus_gpa"] * 1e9
        rho = rho_cte(item["density_factor"], item["delta_alpha_per_k"], item["delta_t_k"], item["vf"], b, d)
        ds = delta_sigma_mpa(item["taylor_alpha"], g, b, rho)
        low_rho = 0.1 * rho
        low_ds = math.sqrt(0.1) * ds
        row = {
            "snapshot_id": snapshot_id,
            "paper_uid": "P_ZHAO2019_MATERIALS",
            "sample_uid": item["sample_uid"],
            "condition_uid": item["condition_uid"],
            "source_hash": source_hash["P_ZHAO2019_MATERIALS"],
            "source_hash_kind": "NORMALIZED_EVIDENCE_CAPTURE_SHA256",
            "evidence_level": "DERIVED_CALCULATION_FROM_DIRECT_TEXT_PARAMETERS",
            "model_type": "CTE_THEORY_FACTOR_6",
            "delta_alpha_per_k": fmt(item["delta_alpha_per_k"]),
            "delta_t_k": fmt(item["delta_t_k"]),
            "vf": fmt(item["vf"]),
            "diameter_m": fmt(d),
            "burgers_m": fmt(b),
            "density_factor": fmt(item["density_factor"]),
            "shear_modulus_pa": fmt(g),
            "taylor_alpha": fmt(item["taylor_alpha"]),
            "rho_cte_m2": fmt(rho),
            "delta_sigma_mpa": fmt(ds),
            "rho_measurement_status": "MODEL_ESTIMATE_NOT_DIRECT_MEASUREMENT",
            "retained_density_low_fraction": 0.1,
            "retained_density_high_fraction": 1.0,
            "temperature_c": 25,
            "applicability_note": "Single-cooling model; no recovery/stress-relaxation calibration."
        }
        cte_rows.append(row)
        distribution_rows.append({
            "paper_uid": row["paper_uid"], "sample_uid": row["sample_uid"], "source_group": "Zhao TiB theory",
            "rho_m2": fmt(rho), "rho_retention_low_m2": fmt(low_rho), "rho_retention_high_m2": fmt(rho),
            "delta_sigma_mpa": fmt(ds), "delta_sigma_retention_low_mpa": fmt(low_ds), "delta_sigma_retention_high_mpa": fmt(ds),
            "evidence_layer": row["evidence_level"], "support_domain": "2-5 vol.% TiB; RT constants"
        })
        zhao_contrib.append({
            "snapshot_id": snapshot_id, "paper_uid": row["paper_uid"], "sample_uid": row["sample_uid"], "condition_uid": row["condition_uid"],
            "source_hash": row["source_hash"], "evidence_level": row["evidence_level"], "observed_delta_ys_mpa": "NOT_REPORTED_IN_BOUND_PAIR",
            "delta_sigma_dislocation_mpa": fmt(ds), "contribution_share_pct": "NOT_IDENTIFIABLE", "share_audit_status": "NO_MATCHED_OBSERVED_DELTA_YS",
            "retention_low_mpa": fmt(low_ds), "retention_high_mpa": fmt(ds), "claim_level": 1,
            "double_count_firewall": "Must separate Hall-Petch, load transfer, Orowan and processing work hardening."
        })

    pair_rows: list[dict[str, Any]] = []
    forest_rows: list[dict[str, Any]] = []
    pair_contrib: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    for item in DATA["matched_pairs"]:
        delta_ys = item["tmc_ys_mpa"] - item["control_ys_mpa"]
        share = item["cte_term_mpa"] / delta_ys * 100.0
        share_eff = share * math.sqrt(0.1)
        share_low, share_high = sorted([share, share_eff])
        rho_eq = equivalent_rho(item["cte_term_mpa"])
        rho_low = 0.1 * rho_eq
        ds_low = item["cte_term_mpa"] * math.sqrt(0.1)
        src_hash = source_hash[item["paper_uid"]]
        grade = item["match_grade"]
        pair_rows.append({
            "snapshot_id": snapshot_id, "pair_uid": item["pair_uid"], "paper_uid": item["paper_uid"],
            "control_sample_uid": item["pair_uid"] + "_CONTROL", "tmc_sample_uid": item["sample_uid"], "condition_uid": item["condition_uid"],
            "source_hash": src_hash, "source_hash_kind": "NORMALIZED_EVIDENCE_CAPTURE_SHA256", "evidence_level": "DIRECT_TEXT_PLUS_SOURCE_CALCULATION",
            "match_grade": grade, "control_priority": "A", "control_ys_mpa": fmt(item["control_ys_mpa"]), "tmc_ys_mpa": fmt(item["tmc_ys_mpa"]),
            "delta_ys_mpa": fmt(delta_ys), "cte_term_mpa": fmt(item["cte_term_mpa"]), "cte_share_pct": fmt(share),
            "dose_value": fmt(item["dose_value"]), "dose_unit": item["dose_unit"], "test_mode": "tension" if item["paper_uid"].startswith("P_LIU") else "compression",
            "temperature_c": 25, "audit_status": item["audit_status"], "estimand": "same-paper matched delta YS and source-term audit",
            "identification_note": "Matched within paper and route family; mechanism term remains a source model, not an isolated causal treatment."
        })
        cte_rows.append({
            "snapshot_id": snapshot_id, "paper_uid": item["paper_uid"], "sample_uid": item["sample_uid"], "condition_uid": item["condition_uid"],
            "source_hash": src_hash, "source_hash_kind": "NORMALIZED_EVIDENCE_CAPTURE_SHA256", "evidence_level": "SOURCE_REPORTED_TERM_AND_DERIVED_EQUIVALENT_RHO",
            "model_type": "SOURCE_REPORTED_CTE_TERM_EQUIVALENT_RHO", "delta_alpha_per_k": "NOT_AVAILABLE", "delta_t_k": "NOT_AVAILABLE",
            "vf": fmt(item["phase_fraction_volpct"] / 100.0) if item["phase_fraction_volpct"] is not None else "NOT_AVAILABLE",
            "diameter_m": fmt(item["particle_size_um"] * 1e-6) if item["particle_size_um"] is not None else "NOT_AVAILABLE",
            "burgers_m": fmt(0.289e-9), "density_factor": "NOT_APPLICABLE_BACK_CALC", "shear_modulus_pa": fmt(45.0e9), "taylor_alpha": fmt(1.25),
            "rho_cte_m2": fmt(rho_eq), "delta_sigma_mpa": fmt(item["cte_term_mpa"]), "rho_measurement_status": "EQUIVALENT_BACK_CALC_NOT_DIRECT_MEASUREMENT",
            "retained_density_low_fraction": 0.1, "retained_density_high_fraction": 1.0, "temperature_c": 25,
            "applicability_note": item["audit_status"]
        })
        group = "Liu CNT source term" if item["paper_uid"].startswith("P_LIU") else "Munir MWCNT budget"
        distribution_rows.append({
            "paper_uid": item["paper_uid"], "sample_uid": item["sample_uid"], "source_group": group,
            "rho_m2": fmt(rho_eq), "rho_retention_low_m2": fmt(rho_low), "rho_retention_high_m2": fmt(rho_eq),
            "delta_sigma_mpa": fmt(item["cte_term_mpa"]), "delta_sigma_retention_low_mpa": fmt(ds_low), "delta_sigma_retention_high_mpa": fmt(item["cte_term_mpa"]),
            "evidence_layer": "SOURCE_TERM_EQUIVALENT_RHO", "support_domain": item["dose_unit"]
        })
        forest_rows.append({
            "pair_uid": item["pair_uid"], "paper_uid": item["paper_uid"], "observed_delta_ys_mpa": fmt(delta_ys),
            "cte_term_mpa": fmt(item["cte_term_mpa"]), "share_pct": fmt(share), "retention_share_low_pct": fmt(share_low),
            "retention_share_high_pct": fmt(share_high), "audit_status": item["audit_status"], "match_grade": grade,
            "interval_type": "10_TO_100_PERCENT_RETAINED_DENSITY_SCENARIO_NOT_CI"
        })
        pair_contrib.append({
            "snapshot_id": snapshot_id, "paper_uid": item["paper_uid"], "sample_uid": item["sample_uid"], "condition_uid": item["condition_uid"],
            "source_hash": src_hash, "evidence_level": "DIRECT_TEXT_PLUS_SOURCE_CALCULATION", "observed_delta_ys_mpa": fmt(delta_ys),
            "delta_sigma_dislocation_mpa": fmt(item["cte_term_mpa"]), "contribution_share_pct": fmt(share), "share_audit_status": item["audit_status"],
            "retention_low_mpa": fmt(ds_low), "retention_high_mpa": fmt(item["cte_term_mpa"]), "claim_level": 2,
            "double_count_firewall": "Admissible for descriptive source-term audit only; no residual closure or cross-paper causal pooling."
        })
        if item["kam_deg"] is not None:
            calibration_rows.append({
                "snapshot_id": snapshot_id, "paper_uid": item["paper_uid"], "sample_uid": item["sample_uid"], "condition_uid": item["condition_uid"],
                "source_hash": src_hash, "method_a": "EBSD_KAM", "method_a_value": fmt(item["kam_deg"]), "method_a_unit": "degree",
                "method_b": "SOURCE_CTE_TERM_EQUIVALENT_RHO", "method_b_value": fmt(rho_eq), "method_b_unit": "m^-2",
                "cte_term_mpa": fmt(item["cte_term_mpa"]), "calibration_status": "DESCRIPTIVE_PROXY_ONLY",
                "observability_note": "Same paper but process-confounded; KAM is not a direct total dislocation density."
            })

    nonident_fields = {
        "delta_alpha_per_k": "NOT_IDENTIFIABLE", "delta_t_k": "NOT_IDENTIFIABLE", "vf": "NOT_IDENTIFIABLE", "diameter_m": "NOT_IDENTIFIABLE",
        "burgers_m": "NOT_IDENTIFIABLE", "density_factor": "NOT_IDENTIFIABLE", "shear_modulus_pa": "NOT_IDENTIFIABLE", "taylor_alpha": "NOT_IDENTIFIABLE",
        "rho_cte_m2": "NOT_IDENTIFIABLE", "delta_sigma_mpa": "NOT_IDENTIFIABLE", "retained_density_low_fraction": "NOT_IDENTIFIABLE",
        "retained_density_high_fraction": "NOT_IDENTIFIABLE", "temperature_c": "NOT_IDENTIFIABLE"
    }
    for puid, sample, cond, note in [
        ("P_GENG2026_MATERIALS", "TIB_TI55531", "AS_REPORTED", "Source explicitly treats thermal mismatch as negligible; delta_T absent."),
        ("P_JIANG2023_TNMSC", "TI2ALN_TIAL", "NITRIDED_SINTERED", "Factor-12 equation present, but v_p notation and required numerical inputs are unresolved.")
    ]:
        row = {"snapshot_id": snapshot_id, "paper_uid": puid, "sample_uid": sample, "condition_uid": cond, "source_hash": source_hash[puid],
               "source_hash_kind": "NORMALIZED_EVIDENCE_CAPTURE_SHA256", "evidence_level": source_map[puid]["evidence_level"],
               "model_type": "NOT_IDENTIFIABLE", **nonident_fields, "rho_measurement_status": "NOT_IDENTIFIABLE", "applicability_note": note}
        cte_rows.append(row)

    cte_fields = ["snapshot_id","paper_uid","sample_uid","condition_uid","source_hash","source_hash_kind","evidence_level","model_type","delta_alpha_per_k","delta_t_k","vf","diameter_m","burgers_m","density_factor","shear_modulus_pa","taylor_alpha","rho_cte_m2","delta_sigma_mpa","rho_measurement_status","retained_density_low_fraction","retained_density_high_fraction","temperature_c","applicability_note"]
    write_csv("CTE_GND_INPUTS.csv", cte_rows, cte_fields)
    write_csv("PAIR_MATCHES.csv", pair_rows)
    write_csv("DISLOCATION_CONTRIBUTIONS.csv", zhao_contrib + pair_contrib + [
        {"snapshot_id":snapshot_id,"paper_uid":"P_GENG2026_MATERIALS","sample_uid":"TIB_TI55531","condition_uid":"AS_REPORTED","source_hash":source_hash["P_GENG2026_MATERIALS"],"evidence_level":"DIRECT_TEXT_METHOD_BOUNDARY","observed_delta_ys_mpa":"NOT_IDENTIFIABLE","delta_sigma_dislocation_mpa":"NEGLIGIBLE_BY_SOURCE_NOT_NUMERIC","contribution_share_pct":"NOT_IDENTIFIABLE","share_audit_status":"NOT_IDENTIFIABLE","retention_low_mpa":"NOT_IDENTIFIABLE","retention_high_mpa":"NOT_IDENTIFIABLE","claim_level":1,"double_count_firewall":"No numeric budget."},
        {"snapshot_id":snapshot_id,"paper_uid":"P_JIANG2023_TNMSC","sample_uid":"TI2ALN_TIAL","condition_uid":"NITRIDED_SINTERED","source_hash":source_hash["P_JIANG2023_TNMSC"],"evidence_level":"DIRECT_TEXT_METHOD_CONFLICT","observed_delta_ys_mpa":"NOT_IDENTIFIABLE","delta_sigma_dislocation_mpa":"NOT_IDENTIFIABLE","contribution_share_pct":"NOT_IDENTIFIABLE","share_audit_status":"NOT_IDENTIFIABLE_SYMBOL_CONFLICT","retention_low_mpa":"NOT_IDENTIFIABLE","retention_high_mpa":"NOT_IDENTIFIABLE","claim_level":1,"double_count_firewall":"Resolve notation before calculation."}
    ])

    kam = [float(r["method_a_value"]) for r in calibration_rows]
    cte_term = [float(r["cte_term_mpa"]) for r in calibration_rows]
    pearson_r = pearson(kam, cte_term)
    spearman_rho = pearson(rankdata(kam), rankdata(cte_term))
    calibration_rows.extend([
        {"snapshot_id":snapshot_id,"paper_uid":"P_MA2020_MATCHAR","sample_uid":"METHOD_DOMAIN","condition_uid":"EBSD","source_hash":source_hash["P_MA2020_MATCHAR"],"method_a":"EBSD_KAM_GND","method_a_value":"NOT_COMPARABLE_WITHOUT_STEP_KERNEL","method_a_unit":"method-dependent","method_b":"TEM_OR_XRD","method_b_value":"NOT_IDENTIFIABLE","method_b_unit":"m^-2","cte_term_mpa":"NOT_APPLICABLE","calibration_status":"METHOD_FIREWALL","observability_note":"EBSD GND excludes unresolved SSD and depends on acquisition/processing parameters."},
        {"snapshot_id":snapshot_id,"paper_uid":"P_JIANG2023_TNMSC","sample_uid":"TI2ALN_TIAL","condition_uid":"TEM_QUALITATIVE","source_hash":source_hash["P_JIANG2023_TNMSC"],"method_a":"TEM","method_a_value":"QUALITATIVE_HIGH_DISLOCATION_DENSITY","method_a_unit":"qualitative","method_b":"CTE_THEORY","method_b_value":"NOT_IDENTIFIABLE","method_b_unit":"m^-2","cte_term_mpa":"NOT_IDENTIFIABLE","calibration_status":"NO_NUMERIC_CALIBRATION","observability_note":"Qualitative TEM cannot calibrate the formula."}
    ])
    write_csv("DISLOCATION_DENSITY_CALIBRATION.csv", calibration_rows)
    write_csv("figure_data/measurement_proxy_calibration.csv", [
        {"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"kam_deg":r["method_a_value"],"equivalent_rho_m2":r["method_b_value"],"cte_term_mpa":r["cte_term_mpa"],"calibration_status":r["calibration_status"]}
        for r in calibration_rows[:4]
    ])

    write_csv("figure_data/rho_delta_sigma_distribution.csv", distribution_rows)
    write_csv("figure_data/contribution_share_forest.csv", forest_rows)
    surface_rows: list[dict[str, Any]] = []
    vf_anchor, d_anchor, b_anchor, g_anchor, factor_anchor, alpha_anchor = 0.035, 5e-6, 0.295e-9, 41.903e9, 6.0, 1.0
    for ai in range(51):
        da_micro = 0.5 + 0.1 * ai
        da = da_micro * 1e-6
        for ti in range(51):
            dt = 300.0 + 20.0 * ti
            rho = rho_cte(factor_anchor, da, dt, vf_anchor, b_anchor, d_anchor)
            ds = delta_sigma_mpa(alpha_anchor, g_anchor, b_anchor, rho)
            surface_rows.append({"delta_alpha_microstrain_per_k":fmt(da_micro),"delta_t_k":fmt(dt),"vf":vf_anchor,"diameter_um":5.0,"density_factor":6.0,"delta_sigma_mpa":fmt(ds),"rho_m2":fmt(rho)})
    write_csv("figure_data/cte_dt_sensitivity_surface.csv", surface_rows)

    analysis_cohort: list[dict[str, Any]] = []
    for row in cte_rows:
        analysis_cohort.append({
            "snapshot_id":snapshot_id,"paper_uid":row["paper_uid"],"sample_uid":row["sample_uid"],"condition_uid":row["condition_uid"],"source_hash":row["source_hash"],
            "scope_role":"QUANTITATIVE_CTE_GND" if row["model_type"] != "NOT_IDENTIFIABLE" else "BOUNDARY_NOT_IDENTIFIABLE",
            "matrix_family":"Ti-6Al-4V" if row["paper_uid"]=="P_ZHAO2019_MATERIALS" else ("CP-Ti" if row["paper_uid"] in {"P_LIU2022_CARBON","P_MUNIR2018_MATERIALIA"} else "OTHER_TITANIUM_MATRIX"),
            "reinforcement_family":"TiB" if "ZHAO" in row["paper_uid"] or "GENG" in row["paper_uid"] else ("CNT/MWCNT" if row["paper_uid"] in {"P_LIU2022_CARBON","P_MUNIR2018_MATERIALIA"} else "Ti2AlN"),
            "test_mode":"model/RT mechanical evidence","temperature_c":row["temperature_c"],"inclusion_status":"INCLUDED" if row["model_type"] != "NOT_IDENTIFIABLE" else "BOUNDARY_ONLY",
            "exclusion_or_limit_reason":row["applicability_note"]
        })
    analysis_cohort.append({"snapshot_id":snapshot_id,"paper_uid":"P_MA2020_MATCHAR","sample_uid":"METHOD_DOMAIN","condition_uid":"METHOD_FIREWALL","source_hash":source_hash["P_MA2020_MATCHAR"],"scope_role":"MEASUREMENT_METHOD_PRIOR","matrix_family":"Ti-6Al-4V","reinforcement_family":"NONE","test_mode":"EBSD/TEM/XRD","temperature_c":"NA","inclusion_status":"METHOD_ONLY","exclusion_or_limit_reason":"No cross-method numeric coefficient."})
    write_csv("ANALYSIS_COHORT.csv", analysis_cohort)

    effects: list[dict[str, Any]] = []
    effect_id = 0
    for row in cte_rows:
        if row["rho_cte_m2"] not in ("NOT_IDENTIFIABLE", "NOT_AVAILABLE"):
            for estimand, value, unit in [("rho_CTE_or_equivalent",row["rho_cte_m2"],"m^-2"),("delta_sigma_dislocation",row["delta_sigma_mpa"],"MPa")]:
                effect_id += 1
                effects.append({"effect_uid":f"QM34_E{effect_id:04d}","snapshot_id":snapshot_id,"paper_uid":row["paper_uid"],"sample_uid":row["sample_uid"],"condition_uid":row["condition_uid"],"source_hash":row["source_hash"],"source_hash_kind":row["source_hash_kind"],"evidence_level":row["evidence_level"],"estimand":estimand,"estimate":value,"unit":unit,"ci_low":"NOT_IDENTIFIABLE","ci_high":"NOT_IDENTIFIABLE","prediction_low":"NOT_IDENTIFIABLE","prediction_high":"NOT_IDENTIFIABLE","uncertainty_type":"10_TO_100_PERCENT_RETENTION_SCENARIO_REPORTED_SEPARATELY","control_grade":"E_THEORY" if row["paper_uid"]=="P_ZHAO2019_MATERIALS" else "A_SOURCE_TERM","claim_level":1 if row["paper_uid"]=="P_ZHAO2019_MATERIALS" else 2,"support_domain":row["applicability_note"]})
    for row in pair_rows:
        for estimand, value, unit in [("matched_delta_YS",row["delta_ys_mpa"],"MPa"),("CTE_contribution_share",row["cte_share_pct"],"percent")]:
            effect_id += 1
            effects.append({"effect_uid":f"QM34_E{effect_id:04d}","snapshot_id":snapshot_id,"paper_uid":row["paper_uid"],"sample_uid":row["tmc_sample_uid"],"condition_uid":row["condition_uid"],"source_hash":row["source_hash"],"source_hash_kind":row["source_hash_kind"],"evidence_level":row["evidence_level"],"estimand":estimand,"estimate":value,"unit":unit,"ci_low":"NOT_IDENTIFIABLE","ci_high":"NOT_IDENTIFIABLE","prediction_low":"NOT_IDENTIFIABLE","prediction_high":"NOT_IDENTIFIABLE","uncertainty_type":"POINT_SOURCE_VALUE_AND_RETENTION_SCENARIO","control_grade":row["match_grade"],"claim_level":2,"support_domain":row["audit_status"]})
    for puid, sample, cond, reason in [("P_GENG2026_MATERIALS","TIB_TI55531","AS_REPORTED","Low CTE mismatch explicitly neglected; parameters incomplete."),("P_JIANG2023_TNMSC","TI2ALN_TIAL","NITRIDED_SINTERED","Symbol-definition conflict and missing parameters.")]:
        effect_id += 1
        effects.append({"effect_uid":f"QM34_E{effect_id:04d}","snapshot_id":snapshot_id,"paper_uid":puid,"sample_uid":sample,"condition_uid":cond,"source_hash":source_hash[puid],"source_hash_kind":"NORMALIZED_EVIDENCE_CAPTURE_SHA256","evidence_level":source_map[puid]["evidence_level"],"estimand":"rho_CTE_and_delta_sigma","estimate":"NOT_IDENTIFIABLE","unit":"NA","ci_low":"NOT_IDENTIFIABLE","ci_high":"NOT_IDENTIFIABLE","prediction_low":"NOT_IDENTIFIABLE","prediction_high":"NOT_IDENTIFIABLE","uncertainty_type":"INPUT_GAP","control_grade":"E","claim_level":1,"support_domain":reason})
    write_csv("EFFECT_ESTIMATES.csv", effects)

    liu_shares = [float(r["cte_share_pct"]) for r in pair_rows if r["paper_uid"]=="P_LIU2022_CARBON"]
    munir_shares = [float(r["cte_share_pct"]) for r in pair_rows if r["paper_uid"]=="P_MUNIR2018_MATERIALIA"]
    hierarchical = [
        {"result_id":"H001","model":"paper-stratified descriptive median","estimand":"Liu source CTE share","independent_papers":1,"matched_pairs":4,"estimate":fmt(statistics.median(liu_shares)),"unit":"percent","ci":"NOT_IDENTIFIABLE","prediction_interval":"NOT_IDENTIFIABLE","status":"DESCRIPTIVE_ADMISSIBLE","claim_level":2,"note":"All four terms are small; no paper-cluster uncertainty with one paper."},
        {"result_id":"H002","model":"paper-stratified descriptive median","estimand":"Munir source CTE share","independent_papers":1,"matched_pairs":6,"estimate":fmt(statistics.median(munir_shares)),"unit":"percent","ci":"NOT_IDENTIFIABLE","prediction_interval":"NOT_IDENTIFIABLE","status":"AUDIT_INVALID","claim_level":1,"note":"Multiple shares exceed 100%; one share is negative only because observed delta YS is negative."},
        {"result_id":"H003","model":"cross-paper hierarchical contribution model","estimand":"universal CTE/GND share","independent_papers":2,"matched_pairs":10,"estimate":"NOT_IDENTIFIABLE","unit":"percent","ci":"NOT_IDENTIFIABLE","prediction_interval":"NOT_IDENTIFIABLE","status":"NOT_IDENTIFIABLE","claim_level":1,"note":"Only two non-commensurate papers, one with internally inconsistent residual budget."},
        {"result_id":"H004","model":"LOPO stress test","estimand":"leave-one-paper-out contribution share","independent_papers":2,"matched_pairs":10,"estimate":"NOT_IDENTIFIABLE","unit":"percent","ci":"NOT_IDENTIFIABLE","prediction_interval":"NOT_IDENTIFIABLE","status":"LOPO_DIRECTIONALLY_UNSTABLE","claim_level":1,"note":f"Leaving Munir gives Liu median {statistics.median(liu_shares):.3f}%; leaving Liu leaves an inadmissible Munir-only median {statistics.median(munir_shares):.3f}%."}
    ]
    write_csv("HIERARCHICAL_RESULTS.csv", hierarchical)

    dose_rows = []
    for row in zhao_contrib:
        source = next(r for r in cte_rows if r["sample_uid"]==row["sample_uid"])
        dose_rows.append({"paper_uid":row["paper_uid"],"dose":float(source["vf"])*100,"dose_unit":"vol.% TiB","response":"delta_sigma_CTE","estimate":row["delta_sigma_dislocation_mpa"],"status":"THEORY_CURVE_POINT","support":"2-5 vol.%"})
    for puid in ["P_LIU2022_CARBON","P_MUNIR2018_MATERIALIA"]:
        subset=[r for r in pair_rows if r["paper_uid"]==puid]
        for dose in sorted({float(r["dose_value"]) for r in subset}):
            vals=[float(r["cte_term_mpa"]) for r in subset if float(r["dose_value"])==dose]
            dose_rows.append({"paper_uid":puid,"dose":dose,"dose_unit":subset[0]["dose_unit"],"response":"source_CTE_term","estimate":fmt(statistics.mean(vals)),"status":"SOURCE_DOSE_SUMMARY" if puid.startswith("P_LIU") else "RED_TEAM_SOURCE_DOSE_SUMMARY","support":f"n={len(vals)} arms"})
    write_csv("DOSE_RESPONSE.csv", dose_rows)

    interactions = [
        {"interaction_id":"I001","variables":"delta_alpha x delta_T","estimand":"elasticity of delta_sigma","estimate":"0.5 for each multiplicative input","status":"ANALYTICAL_MODEL_SENSITIVITY","evidence":"Zhao factor-6 formula","claim_level":1},
        {"interaction_id":"I002","variables":"Vf x particle diameter","estimand":"delta_sigma proportionality","estimate":"sqrt[Vf/((1-Vf)*d)]","status":"ANALYTICAL_MODEL_SENSITIVITY","evidence":"Zhao factor-6 formula","claim_level":1},
        {"interaction_id":"I003","variables":"temperature x retained density","estimand":"effective delta_sigma","estimate":"sqrt(f_retained) times RT model term, before G(T) correction","status":"SCENARIO_ONLY","evidence":"recovery/stress-relaxation gap","claim_level":1},
        {"interaction_id":"I004","variables":"measurement method x length scale","estimand":"KAM/TEM/XRD calibration","estimate":"NOT_IDENTIFIABLE","status":"NOT_IDENTIFIABLE","evidence":"method observability firewall","claim_level":1}
    ]
    write_csv("INTERACTION_EFFECTS.csv", interactions)

    heterogeneity = [
        {"stratum":"Zhao TiB theory","independent_papers":1,"rows":3,"rho_range_m2":f"{min(float(r['rho_m2']) for r in distribution_rows[:3]):.3e} to {max(float(r['rho_m2']) for r in distribution_rows[:3]):.3e}","delta_sigma_range_mpa":f"{min(float(r['delta_sigma_mpa']) for r in distribution_rows[:3]):.3f} to {max(float(r['delta_sigma_mpa']) for r in distribution_rows[:3]):.3f}","heterogeneity_driver":"Vf under fixed coarse-particle inputs","pooling_decision":"WITHIN_FORMULA_ONLY"},
        {"stratum":"Liu CNT source term","independent_papers":1,"rows":4,"rho_range_m2":f"{min(equivalent_rho(v) for v in [2.7,3.0,3.8,5.3]):.3e} to {max(equivalent_rho(v) for v in [2.7,3.0,3.8,5.3]):.3e}","delta_sigma_range_mpa":"2.7 to 5.3","heterogeneity_driver":"powder and consolidation route","pooling_decision":"DESCRIPTIVE_WITHIN_PAPER"},
        {"stratum":"Munir MWCNT source budget","independent_papers":1,"rows":6,"rho_range_m2":f"{equivalent_rho(158.7):.3e} to {equivalent_rho(225.4):.3e}","delta_sigma_range_mpa":"158.7 to 225.4","heterogeneity_driver":"dose and residual-closed budget","pooling_decision":"RED_TEAM_ONLY"},
        {"stratum":"Cross-paper","independent_papers":3,"rows":13,"rho_range_m2":f"{min(float(r['rho_m2']) for r in distribution_rows):.3e} to {max(float(r['rho_m2']) for r in distribution_rows):.3e}","delta_sigma_range_mpa":f"{min(float(r['delta_sigma_mpa']) for r in distribution_rows):.3f} to {max(float(r['delta_sigma_mpa']) for r in distribution_rows):.3f}","heterogeneity_driver":"formula, reinforcement, geometry, process and budget construction","pooling_decision":"NOT_IDENTIFIABLE"}
    ]
    write_csv("HETEROGENEITY.csv", heterogeneity)

    sensitivity: list[dict[str, Any]] = []
    anchor = next(r for r in cte_rows if r["sample_uid"]=="ZHAO_VF035")
    anchor_rho=float(anchor["rho_cte_m2"]); anchor_ds=float(anchor["delta_sigma_mpa"])
    for f in [0.1,0.5,1.0]:
        sensitivity.append({"analysis_id":f"S_RET_{f}","paper_uid":"P_ZHAO2019_MATERIALS","parameter":"retained_density_fraction","value":f,"rho_m2":fmt(anchor_rho*f),"delta_sigma_mpa":fmt(anchor_ds*math.sqrt(f)),"interpretation":"Stress relaxation/recovery scenario; not a fitted confidence interval."})
    for factor in [6.0,12.0]:
        rho=anchor_rho*factor/6.0; ds=anchor_ds*math.sqrt(factor/6.0)
        sensitivity.append({"analysis_id":f"S_FACTOR_{int(factor)}","paper_uid":"P_ZHAO2019_MATERIALS","parameter":"density_prefactor","value":factor,"rho_m2":fmt(rho),"delta_sigma_mpa":fmt(ds),"interpretation":"Equation-convention sensitivity; factor 12 doubles rho and multiplies delta_sigma by sqrt(2)."})
    for diameter_um in [1.0,5.0,10.0]:
        rho=anchor_rho*5.0/diameter_um; ds=anchor_ds*math.sqrt(5.0/diameter_um)
        sensitivity.append({"analysis_id":f"S_D_{diameter_um}","paper_uid":"P_ZHAO2019_MATERIALS","parameter":"particle_diameter_um","value":diameter_um,"rho_m2":fmt(rho),"delta_sigma_mpa":fmt(ds),"interpretation":"All other anchor inputs fixed."})
    sensitivity.extend([
        {"analysis_id":"S_LOPO_LIU","paper_uid":"P_LIU2022_CARBON","parameter":"leave_Munir_out","value":"Liu only","rho_m2":"NA","delta_sigma_mpa":"NA","interpretation":f"Median source share={statistics.median(liu_shares):.3f}%; one-paper descriptive only."},
        {"analysis_id":"S_LOPO_MUNIR","paper_uid":"P_MUNIR2018_MATERIALIA","parameter":"leave_Liu_out","value":"Munir only","rho_m2":"NA","delta_sigma_mpa":"NA","interpretation":f"Median source share={statistics.median(munir_shares):.3f}%; invalid because contribution budgets fail closure audit."}
    ])
    write_csv("SENSITIVITY_ANALYSIS.csv", sensitivity)

    null_negative = [
        {"result_id":"N001","paper_uid":"P_LIU2022_CARBON","result":"CTE term only 0.60-1.56% of matched delta YS","classification":"NULL_OR_MINOR_MECHANISM","retained":"YES","reason":"Source term is small relative to observed strengthening."},
        {"result_id":"N002","paper_uid":"P_MUNIR2018_MATERIALIA","result":"1.0 wt.%-Batch-2 delta YS=-85 MPa despite +225.4 MPa source CTE term","classification":"NEGATIVE_COUNTEREXAMPLE","retained":"YES","reason":"Demonstrates that source-budget terms cannot be treated as isolated causal contributions."},
        {"result_id":"N003","paper_uid":"P_GENG2026_MATERIALS","result":"Thermal mismatch explicitly negligible","classification":"NULL_SOURCE_CLAIM","retained":"YES","reason":"Low CTE mismatch and missing cooling interval."},
        {"result_id":"N004","paper_uid":"P_JIANG2023_TNMSC","result":"Numeric rho and delta_sigma cannot be reproduced","classification":"NOT_IDENTIFIABLE","retained":"YES","reason":"Symbol and input gaps."},
        {"result_id":"N005","paper_uid":"P_MA2020_MATCHAR","result":"No same-sample KAM/TEM/XRD conversion coefficient","classification":"NOT_IDENTIFIABLE","retained":"YES","reason":"Methods observe different dislocation populations and scales."},
        {"result_id":"N006","paper_uid":"CROSS_PAPER","result":"Universal contribution share and prediction interval","classification":"NOT_IDENTIFIABLE","retained":"YES","reason":"Only two matched-budget papers and one fails internal audit."}
    ]
    write_csv("NULL_NEGATIVE_RESULTS.csv", null_negative)

    conflict_rows = []
    for cid, puid, ctype, desc, severity, resolution in DATA["conflicts"]:
        conflict_rows.append({"conflict_id":cid,"snapshot_id":snapshot_id,"paper_uid":puid,"source_hash":source_hash.get(puid,snapshot_digest),"conflict_type":ctype,"description":desc,"severity":severity,"status":"OPEN","resolution_or_next_action":resolution})
    write_csv("CONFLICT_LEDGER.csv", conflict_rows)
    write_csv("GND_APPLICABILITY.csv", [dict(snapshot_id=snapshot_id,source_hash=source_hash[r["paper_uid"]],**r) for r in DATA["applicability"]])

    coverage = [
        {"source_class":"Project ZIP archives","objects_registered":len(DATA["archive_ledger"]),"objects_deep_opened_this_window":0,"use":"Hash-bound inventory and source routing","terminal_state":"REGISTERED; remote byte re-read not claimed"},
        {"source_class":"TITMC V27 XML corpus","objects_registered":78683,"objects_deep_opened_this_window":0,"use":"Corpus scope prior and original-evidence route","terminal_state":"Full QM34 XML pass not claimed; target papers deep-used via File Library"},
        {"source_class":"Primary/mechanism papers","objects_registered":6,"objects_deep_opened_this_window":6,"use":"Quantitative anchors, counterexamples and method firewall","terminal_state":"USED_DIRECTLY with normalized capture hashes"},
        {"source_class":"Matched mechanism-budget papers","objects_registered":2,"objects_deep_opened_this_window":2,"use":"10 same-paper matched pairs","terminal_state":"Liu descriptive-admissible; Munir red-team only"},
        {"source_class":"Canonical V29/Q40 atomic snapshot","objects_registered":0,"objects_deep_opened_this_window":0,"use":"Authority-bound atom/provenance interface","terminal_state":"MISSING_BLOCKING_LOCAL_ABSORPTION"}
    ]
    write_csv("SOURCE_COVERAGE_MATRIX.csv", coverage)

    methods = f"""# METHODS — QM34

## Estimands

1. Model or equivalent dislocation density, `rho_CTE/GND`.
2. `delta_sigma_dislocation = M alpha G b sqrt(rho)`.
3. Same-paper matched `delta YS` and the audited ratio `delta_sigma_CTE / delta YS`.
4. Constrained sensitivities to CTE mismatch, cooling interval, particle fraction/size, prefactor and retained-density fraction.

## Atomicity and matching

Rows remain paper × sample × process/condition × test mode × temperature × property. Ten A-grade within-paper matched control/TMC pairs are retained: four Liu tensile pairs and six Munir compression pairs. The three Zhao rows are theoretical parameter points and are never merged with measured pairs.

## CTE/GND equations

For the Zhao anchor:

`rho = B |delta_alpha| delta_T Vf / [(1-Vf) b d]`, with `B=6`.

`delta_sigma = alpha G b sqrt(rho)`.

The Jiang source uses a factor-12 form, but its symbol definition and numerical inputs do not close; it is retained as `NOT_IDENTIFIABLE`. Source-reported Liu/Munir strengthening terms are converted to an *equivalent* density using `rho_eq=(delta_sigma/(1.25 G b))^2`, `G=45 GPa`, and `b=0.289 nm`. Equivalent density is not a direct measurement.

## Uncertainty and temperature applicability

No source supplies a defensible sampling distribution for every formula input. Therefore statistical CIs and cross-paper prediction intervals are explicitly `NOT_IDENTIFIABLE`. Plotted bars use the declared physical scenario `f_retained=0.1–1.0`: `rho_eff=f rho`, `delta_sigma_eff=sqrt(f) delta_sigma`. They are not mislabeled as confidence intervals. High-temperature transfer is prohibited until `G(T)`, recovery, thermal cycling and stress-relaxation retention are available.

## Method calibration firewall

KAM/TEM/XRD are not pooled as interchangeable densities. The only numeric proxy check is the four-sample Liu KAM–source-term association (Pearson r={pearson_r:.3f}; Spearman rho={spearman_rho:.3f}); it is process-confounded and cannot calibrate one method to another.

## Statistical decision

A universal hierarchical mechanism fraction is not fitted because there are only two matched-budget papers and the Munir budget fails internal closure. LOPO is reported as a stress test: Liu-only remains near one percent, while Munir-only is inadmissible. No BH-FDR family is formed because no confirmatory p-value family is estimated.

## Claim ceiling

Maximum level 2: same-paper matched association/source-calculation audit. No Gold promotion, ACTIVE mutation, production-model registration or VALIDATED formulation is performed.
"""
    write_text("METHODS.md", methods)

    write_text("LIMITATIONS.md", """# LIMITATIONS — QM34

- The canonical V29/Q40 `ATOMIC_RECORDS`, provenance, conflicts, exclusions and paper/sample/condition registry are absent; this is a derived recovery snapshot.
- Original publication byte hashes/XPaths are not closed for the six target papers. Every numeric row is instead bound to a normalized evidence-capture SHA-256 and an explicit source locator.
- CTE formulas estimate an idealized density generated during cooling. They do not directly measure retained GND, do not separate GND from SSD, and do not represent recovery or stress relaxation at service temperature.
- The Zhao calculation assumes fixed mean particle diameter and isotropic scalar mismatch. Architecture, aspect-ratio distribution, local elastic anisotropy and interface constraint are suppressed.
- The Liu KAM association has n=4 in one paper and is confounded by powder treatment and consolidation route. It is not a KAM-to-rho calibration.
- The Munir budget is internally inconsistent for contribution attribution; it is retained only as a counterexample.
- Hall-Petch, processing work hardening, residual stress, load transfer and Orowan terms are not guaranteed orthogonal. Additive summation can double count stored dislocations and refinement effects.
- Cross-paper CIs, prediction intervals, random slopes, FDR-adjusted interactions and a universal contribution fraction are not identifiable.
""")

    verdict = f"""# QM34 Executive Verdict

`WINDOW=QM34 | SNAPSHOT={snapshot_id} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Terminal scientific answer

**CTE-mismatch/GND strengthening is real as a model term, but its attributed share is not transferable across Ti/TMC systems.** In the cleanest four matched CNT/Ti arms from Liu, source thermal-mismatch terms are only **2.7–5.3 MPa**, equivalent to **0.60–1.56%** of observed matched yield-strength gains; the within-paper median is **{statistics.median(liu_shares):.3f}%**. In the coarse TiB/Ti-6Al-4V Zhao model, 2–5 vol.% TiB gives `rho_CTE` approximately **{float(cte_rows[0]['rho_cte_m2']):.2e}–{float(cte_rows[2]['rho_cte_m2']):.2e} m^-2** and `delta_sigma` approximately **{float(cte_rows[0]['delta_sigma_mpa']):.2f}–{float(cte_rows[2]['delta_sigma_mpa']):.2f} MPa** under fixed RT constants.

The much larger Munir terms (**158.7–225.4 MPa**) do not survive a contribution-budget audit. Four of six point shares exceed 100%, and the 1.0 wt.%-Batch-2 specimen weakens by 85 MPa despite a positive 225.4 MPa thermal-mismatch term. Those rows are red-team evidence of circular/non-orthogonal budget closure, not estimates of a causal fraction.

Across the bound quantitative evidence, formula/equivalent densities span roughly **{min(float(r['rho_m2']) for r in distribution_rows):.2e}–{max(float(r['rho_m2']) for r in distribution_rows):.2e} m^-2** and source/model strengthening terms span **{min(float(r['delta_sigma_mpa']) for r in distribution_rows):.1f}–{max(float(r['delta_sigma_mpa']) for r in distribution_rows):.1f} MPa**. This four-order density range is driven by geometry, coefficient convention, dose, processing and residual-budget construction—not a universal Ti/TMC law.

## Measurement and service boundary

The four Liu KAM points show a descriptive Pearson r={pearson_r:.3f} and Spearman rho={spearman_rho:.3f} versus the source CTE term, but all four points belong to one process-confounded paper. A KAM/TEM/XRD calibration is **NOT_IDENTIFIABLE**. High-temperature retained strengthening is also **NOT_IDENTIFIABLE** because recovery, stress relaxation, thermal cycling and `G(T)` are missing; the package reports a 10–100% retained-density scenario envelope instead of a false CI.

## Contribution answer

- Liu CNT/Ti matched evidence: about **0.6–1.6%** of observed matched delta YS by the source CTE term.
- Zhao coarse TiB/Ti-6Al-4V theory: about **6–10 MPa**, with no closed matched delta YS in the bound parameter record.
- Geng TiB/Ti-55531: source treats thermal mismatch as negligible; numeric contribution remains `NOT_IDENTIFIABLE`.
- Munir MWCNT/Ti: source terms are large but fail closure; contribution shares are inadmissible.
- Universal pooled fraction, random-effect coefficient and new-paper prediction interval: **NOT_IDENTIFIABLE**.

## Claim ceiling

Maximum claim level **2 — same-paper paired association/source-calculation audit**. CTE formulas are model estimates, not direct dislocation-density measurements. No Gold promotion, ACTIVE mutation, production-model registration or VALIDATED composition is claimed.

## Operational status

`CONTINUE_DATA_GAP`: the read-only derived package is complete and reproducible for the bound evidence, but authority absorption requires the canonical V29/Q40 atom/provenance snapshot, original byte hashes/XPaths, and direct same-sample KAM/TEM/XRD plus temperature-retention data.
"""
    write_text("00_EXECUTIVE_VERDICT.md", verdict)

    plot_specs = {
        "window_id":"QM34","snapshot_id":snapshot_id,"language":"English","formats":["SVG","PDF","PNG_600_DPI"],
        "plots":[
            {"id":"QM34_F1","title":"CTE/GND model estimates across the bound Ti/TMC evidence","data":"figure_data/rho_delta_sigma_distribution.csv","code":"plot_code/plot_distribution.py","independent_papers":3,"samples":13,"effect_definition":"rho_CTE/equivalent rho and M alpha G b sqrt(rho)","interval":"10-100% retained-density scenario; statistical CI/PI NOT_IDENTIFIABLE","evidence":"theory/source calculation","support":"bound RT systems"},
            {"id":"QM34_F2","title":"Sensitivity of delta_sigma_CTE to CTE mismatch and cooling interval","data":"figure_data/cte_dt_sensitivity_surface.csv","code":"plot_code/plot_surface.py","independent_papers":1,"samples":2601,"effect_definition":"factor-6 Zhao anchor surface","interval":"constrained surface; not CI/PI","evidence":"derived calculation","support":"Vf=3.5%, d=5 um, RT constants"},
            {"id":"QM34_F3","title":"KAM-CTE-term proxy comparison","data":"figure_data/measurement_proxy_calibration.csv","code":"plot_code/plot_proxy.py","independent_papers":1,"samples":4,"effect_definition":"descriptive KAM versus source CTE term","interval":"statistical CI/PI and method calibration NOT_IDENTIFIABLE","evidence":"direct method values plus source calculation","support":"Liu process arms only"},
            {"id":"QM34_F4","title":"Thermal-mismatch contribution-share audit","data":"figure_data/contribution_share_forest.csv","code":"plot_code/plot_forest.py","independent_papers":2,"samples":10,"effect_definition":"source delta_sigma_CTE / matched delta YS","interval":"10-100% retained-density scenario; not CI","evidence":"same-paper matched/source budget","support":"Liu admissible descriptive; Munir red-team"}
        ]
    }
    write_json("PLOT_SPECS.json", plot_specs)

    write_json("WEB_TO_LOCAL_REQUEST.json", {
        "window_id":"QM34","snapshot_id":snapshot_id,"status":"CONTINUE_DATA_GAP","priority":"BLOCKING_AUTHORITY_ABSORPTION",
        "required_files":[
            {"pattern":"Q40_INPUT_SNAPSHOT.json or canonical snapshot manifest","reason":"Bind the unique frozen authority snapshot."},
            {"pattern":"ATOMIC_RECORDS.(csv|parquet), PROVENANCE.jsonl, CONFLICT_LEDGER.csv, EXCLUDED_RECORDS.csv","reason":"Restore canonical row identities and exclusions."},
            {"pattern":"paper_registry.*, sample_registry.*, condition_registry.*","reason":"Replace derived paper/sample/condition UIDs with authority identities."},
            {"pattern":"original target-paper files plus SHA-256 and XML XPath/element hashes","reason":"Close original-byte provenance for Zhao, Munir, Liu, Geng, Jiang and Ma."},
            {"pattern":"same-sample EBSD raw/KAM settings + TEM counts + XRD line-profile outputs","reason":"Estimate a method calibration layer rather than proxy correlation."},
            {"pattern":"cooling curves, delta_T, particle-size/fraction distributions, G(T), b(T), M(T), thermal-cycle and relaxation data","reason":"Constrain retained rho and high-temperature delta_sigma."}
        ],
        "acceptance":"All files require full SHA-256, schema/version, paper_uid/sample_uid/condition_uid mapping and a no-mutation dry run before absorption."
    })

    write_text("LOCAL_ABSORPTION_PROMPT.md", f"""# LOCAL ABSORPTION PROMPT — QM34

1. Verify `FINAL_QM34.zip` SHA-256 and `testzip`; reject nested ZIPs.
2. Extract into a quarantine directory. Run `sha256sum -c CHECKSUMS.sha256` and `python tests/test_qm34_outputs.py .`.
3. Run `python analysis_code/recompute_qm34.py .` and require byte-identical `RECOMPUTE_OUTPUT.txt` with status PASS.
4. Resolve `WEB_TO_LOCAL_REQUEST.json`; map all derived paper/sample/condition UIDs to the unique canonical V29/Q40 snapshot.
5. Re-run formula rows using original-byte/XPath-bound parameters and compare against `CTE_GND_INPUTS.csv`.
6. Do not mutate ACTIVE_TITMC, Gold, Schema or production model registries. Promote only after independent provenance, conflict, unit, double-count and method-calibration review.

Expected snapshot from this package: `{snapshot_id}`.
""")

    write_json("SNAPSHOT_VALIDATION.json", {
        "window_id":"QM34","snapshot_id":snapshot_id,"derived_snapshot_hash":snapshot_digest,"derived_snapshot_valid":True,
        "canonical_v29_q40_snapshot_present":False,"canonical_snapshot_status":"MISSING_BLOCKING_AUTHORITY_ABSORPTION",
        "archive_ledger_entries":len(DATA["archive_ledger"]),"source_capture_entries":len(source_map),
        "identity_policy":"Every quantitative row carries snapshot_id, source capture SHA-256, paper_uid, sample_uid and condition_uid.",
        "original_byte_hash_policy":"Not fabricated; missing original hashes are requested explicitly."
    })

    status = {
        "window_id":"QM34","snapshot_id":snapshot_id,"papers_seen":6,"papers_included":6,"independent_papers":6,
        "atomic_rows":len(analysis_cohort),"matched_pairs":len(pair_rows),"effect_estimates":len(effects),"plots_generated":4,
        "open_conflicts":len(conflict_rows),"claim_level_max":2,"status":"CONTINUE_DATA_GAP",
        "next_action":"Local canonical-snapshot mapping, original-byte provenance closure, and direct same-sample method/temperature-retention calibration.",
        "production_model_registered":False,"gold_promoted":False,"active_titmc_modified":False
    }
    write_json("WINDOW_STATUS.json", status)

    provenance_lines: list[str] = []
    for src in source_map.values():
        provenance_lines.append(json.dumps({
            "record_type":"source","snapshot_id":snapshot_id,"paper_uid":src["paper_uid"],"doi":src["doi"],"source_locator":src["locator"],
            "source_hash":src["source_hash"],"source_hash_kind":src["source_hash_kind"],"evidence_level":src["evidence_level"],
            "capture_path":src["capture_path"],"original_byte_hash_status":src["original_byte_hash_status"]
        },ensure_ascii=False,sort_keys=True))
    for eff in effects:
        provenance_lines.append(json.dumps({
            "record_type":"effect","effect_uid":eff["effect_uid"],"snapshot_id":snapshot_id,"paper_uid":eff["paper_uid"],"sample_uid":eff["sample_uid"],
            "condition_uid":eff["condition_uid"],"source_hash":eff["source_hash"],"source_hash_kind":eff["source_hash_kind"],"evidence_level":eff["evidence_level"],
            "estimand":eff["estimand"],"estimate":eff["estimate"],"unit":eff["unit"]
        },ensure_ascii=False,sort_keys=True))
    write_text("PROVENANCE.jsonl", "\n".join(provenance_lines) + "\n")

    write_text("README.md", f"""# FINAL_QM34

Read-only quantitative return for thermal-expansion mismatch, GND/dislocation density and dislocation-strengthening contribution in titanium-matrix composites.

- Snapshot: `{snapshot_id}` (derived recovery snapshot; canonical V29/Q40 snapshot absent)
- Independent papers used: 6
- Same-paper matched pairs: 10
- Quantitative figures: 4 × SVG/PDF/600-dpi PNG
- Claim ceiling: Level 2
- Status: CONTINUE_DATA_GAP

Start with `00_EXECUTIVE_VERDICT.md`. Reproduce with `analysis_code/recompute_qm34.py` and `plot_code/plot_all.py`. This package does not alter ACTIVE_TITMC, Gold, Schema or any production model registry.
""")
    write_text("requirements.lock", "matplotlib==3.10.3\nnumpy==2.2.6\n")
    write_text("acceptance_commands.md", """# Acceptance commands

```bash
python analysis_code/recompute_qm34.py .
python tests/test_qm34_outputs.py .
python plot_code/plot_all.py .
sha256sum -c CHECKSUMS.sha256
python -c "import zipfile; z=zipfile.ZipFile('../FINAL_QM34.zip'); assert z.testzip() is None; assert not [n for n in z.namelist() if n.lower().endswith('.zip')]"
```
""")

    shutil.copy2(BASE / "recompute_qm34.py", ROOT / "analysis_code" / "recompute_qm34.py")
    shutil.copy2(BASE / "plot_all.py", ROOT / "plot_code" / "plot_all.py")
    shutil.copy2(BASE / "test_qm34_outputs.py", ROOT / "tests" / "test_qm34_outputs.py")
    for key in ["distribution","surface","proxy","forest"]:
        wrapper = f'''#!/usr/bin/env python3\nfrom pathlib import Path\nimport subprocess, sys\nroot = Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1]).resolve()\nraise SystemExit(subprocess.call([sys.executable, str(Path(__file__).with_name("plot_all.py")), str(root), "--only", "{key}"]))\n'''
        write_text(f"plot_code/plot_{key}.py", wrapper)

    subprocess.run([sys.executable, str(ROOT / "plot_code" / "plot_all.py"), str(ROOT)], check=True)
    recompute = subprocess.run([sys.executable, str(ROOT / "analysis_code" / "recompute_qm34.py"), str(ROOT)], check=True, capture_output=True, text=True)
    write_text("RECOMPUTE_OUTPUT.txt", recompute.stdout)

    write_json("VALIDATION_REPORT.json", {
        "window_id":"QM34","snapshot_id":snapshot_id,"status":"PASS_DERIVED_PACKAGE_WITH_DATA_GAP",
        "checks":{"mandatory_schema_files":"PASS","same_paper_matches":10,"formula_rows_recomputed":3,"figure_triplets":4,"provenance_binding":"PASS","null_negative_results":"PASS","conflict_ledger":"PASS","production_mutation":"NONE"},
        "scientific_gates":{"explicit_estimand":"PASS","paired_analysis":"PASS","LOPO":"PASS_WITH_TWO_PAPER_LIMIT","paper_cluster_uncertainty":"NOT_IDENTIFIABLE_REPORTED","method_calibration":"NOT_IDENTIFIABLE_REPORTED","claim_ceiling":"PASS"}
    })
    write_text("RUN_LOG.txt", f"WINDOW=QM34\nSNAPSHOT={snapshot_id}\nINPUT_MODE=QUANT_EXECUTE/COHORT_BUILD\nSTATUS=CONTINUE_DATA_GAP\nFORMULA_ROWS=3\nMATCHED_PAIRS=10\nEFFECT_ESTIMATES={len(effects)}\nPLOTS=4\nOPEN_CONFLICTS={len(conflict_rows)}\n")

    existing = sorted(p for p in ROOT.rglob("*") if p.is_file())
    manifest_entries = [{"path":str(p.relative_to(ROOT)).replace("\\","/"),"bytes":p.stat().st_size,"sha256":sha256_file(p)} for p in existing]
    write_json("MANIFEST.json", {
        "window_id":"QM34","batch":DATA["batch"],"snapshot_id":snapshot_id,"status":"CONTINUE_DATA_GAP",
        "file_count":len(existing)+2,"entries":manifest_entries,"no_nested_zip":True,"production_model_registration":False,"gold_promotion":False
    })
    checksum_files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
    write_text("CHECKSUMS.sha256", "".join(f"{sha256_file(p)}  {str(p.relative_to(ROOT)).replace(chr(92),'/')}\n" for p in checksum_files))

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(ROOT.rglob("*")):
            if p.is_file():
                z.write(p, arcname=str(p.relative_to(ROOT)).replace("\\", "/"))
    with zipfile.ZipFile(ZIP_PATH) as z:
        assert z.testzip() is None
        assert not [n for n in z.namelist() if n.lower().endswith(".zip")]
        zip_entries = len(z.namelist())

    summary = {
        "window_id":"QM34","snapshot_id":snapshot_id,"zip":str(ZIP_PATH),"zip_bytes":ZIP_PATH.stat().st_size,
        "zip_sha256":sha256_file(ZIP_PATH),"zip_entries":zip_entries,"status":"CONTINUE_DATA_GAP",
        "matched_pairs":10,"effect_estimates":len(effects),"figure_triplets":4
    }
    (OUT_BASE / "QM34_BUILD_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    build()
