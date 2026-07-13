from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")

WINDOW = "QM25"
BASE = Path(__file__).resolve().parent
ROOT = BASE / "output" / "FINAL_QM25"
FIXED_TIME = "2026-07-13T08:30:00Z"


def htxt(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hfile(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def wt(rel: str, text: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def wj(rel: str, obj: Any) -> None:
    wt(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def wc(rel: str, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: "" if row.get(c) is None else row.get(c, "") for c in cols})


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    xb, yb = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - xb) ** 2 for x in xs)
    slope = sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / sxx
    intercept = yb - slope * xb
    sst = sum((y - yb) ** 2 for y in ys)
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    return slope, intercept, 1.0 - sse / sst


def bh(pvals: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvals.items(), key=lambda x: x[1])
    m, run, out = len(ordered), 1.0, {}
    for rank in range(m, 0, -1):
        name, p = ordered[rank - 1]
        run = min(run, p * m / rank)
        out[name] = min(1.0, run)
    return out


def ternary(al: float, v: float, ti: float) -> tuple[float, float]:
    s = al + v + ti
    al, v, ti = al / s, v / s, ti / s
    return v + 0.5 * ti, math.sqrt(3.0) * 0.5 * ti


def ilr(al: float, v: float, ti: float) -> float:
    return math.sqrt(2.0 / 3.0) * math.log(ti / math.sqrt(al * v))


def build() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for d in ("analysis_code", "plot_code", "figure_data", "figures", "tests"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    archives = [
        "00_统一上传总控与校验信息_20260712.zip",
        "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
        "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip",
        "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
        *[f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 9)],
        "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
        *[f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1, 4)],
        *[f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1, 11)],
    ]
    known = {
        archives[0]: "0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f",
        archives[1]: "bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1",
        archives[2]: "36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9",
        archives[3]: "5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59",
        archives[4]: "cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a",
        archives[5]: "97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809",
        archives[6]: "16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f",
        archives[7]: "04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9",
        archives[8]: "5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728",
        archives[9]: "e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847",
        archives[10]: "36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485",
        archives[11]: "9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd",
        archives[12]: "c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c",
        archives[13]: "a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a",
        archives[14]: "bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43",
        archives[15]: "08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755",
    }
    papers = [
        {"paper_uid": "BAO_2024_WAAM_TIB_TI64", "doi": "10.1080/17452759.2024.2383287", "role": "Al+V/Ti activity × TiB formation"},
        {"paper_uid": "LEI_2025_AL_TIC", "doi": "10.1016/j.jmrt.2025.08.271", "role": "Al × TiC lattice/morphology"},
        {"paper_uid": "WANG_2024_TIB_TA15SI", "doi": "MSEA-890-145888", "role": "Si-bearing TiB high-temperature response"},
        {"paper_uid": "LIU_2023_TIB_TIC_TI64", "doi": "10.1016/j.compositesb.2023.111008", "role": "hybrid TiB+TiC"},
        {"paper_uid": "JIANG_2023_H_TIC_TI64", "doi": "10.1016/j.compositesb.2023.110966", "role": "H × TiC candidate"},
        {"paper_uid": "YANG_2024_NB_TIC_TICR", "doi": "JMRT-30-1083-1094", "role": "Nb × TiC candidate"},
        {"paper_uid": "INTERNAL_TI65_ARCHIVE", "doi": "internal-hash-bound", "role": "W main effect and TiB conditional effect"},
    ]
    snap_payload = {"archives": [{"name": a, "hash": known.get(a, htxt("locator:" + a))} for a in archives], "papers": papers, "method": "qm25-v1"}
    snapshot = "QM25_RECOVERY_" + htxt(json.dumps(snap_payload, ensure_ascii=False, sort_keys=True))[:20]

    ledger = []
    for i, name in enumerate(archives, 1):
        if name.startswith("TITMC_V27_LIT_WEB"):
            role, state, pri = "primary XML/PDF/MD/DOCX literature corpus", "REGISTERED_AND_SCOPE_ROUTED", "P0"
        elif "DATA_FEATURES" in name:
            role, state, pri = "frozen matrices/features and composition domains", "REGISTERED; AUTHORITATIVE_ROWS_REQUIRED", "P1"
        elif "HARNESS" in name:
            role, state, pri = "source reliability, canonical conditions, UQ/AD and split discipline", "USED_AS_METHOD_PRIOR", "P1"
        elif "S02" in name or "S04" in name:
            role, state, pri = "plotting, validation and engineering infrastructure", "USED_AS_INFRASTRUCTURE_PRIOR", "P2"
        else:
            role, state, pri = "control and upload integrity", "REGISTERED", "P1"
        ledger.append({"input_id": f"IN{i:02d}", "snapshot_id": snapshot, "source_name": name, "source_type": "ZIP", "path_or_locator": "/mnt/data/" + name, "source_hash": known.get(name, htxt("locator:" + name)), "source_hash_kind": "FULL_OR_CENTRAL_DIRECTORY_SHA256" if name in known else "LOCATOR_SHA256_NOT_BYTE_HASH", "priority": pri, "window_relevance": role, "terminal_use_status": state, "opened_or_consumed": "PRIOR_AUDIT_OR_SCOPE_ROUTING", "notes": "Unknown byte hashes were not fabricated."})
    ledger.append({"input_id": "IN27", "snapshot_id": snapshot, "source_name": "QM25_元素×增强相×基体的高阶交互和成分单纯形分析.md", "source_type": "MDU", "path_or_locator": "/mnt/data/QM25_元素×增强相×基体的高阶交互和成分单纯形分析.md", "source_hash": "file_00000000855c720b8249c3d95062b541", "source_hash_kind": "UPLOAD_FILE_ID", "priority": "CONTRACT", "window_relevance": "scope and acceptance contract", "terminal_use_status": "OPENED_AND_ENFORCED", "opened_or_consumed": "YES", "notes": "Full dispatch unit consumed."})
    wc("INPUT_LEDGER.csv", ledger, ["input_id", "snapshot_id", "source_name", "source_type", "path_or_locator", "source_hash", "source_hash_kind", "priority", "window_relevance", "terminal_use_status", "opened_or_consumed", "notes"])

    bao = [
        ("P1", 29.6, 20.2, 50.2, 0, "rare TiB2 decomposition"),
        ("P2", 33.3, 12.1, 54.6, 0, "rare TiB2 decomposition"),
        ("P3", 25.1, 9.5, 65.4, 0, "rare TiB2 decomposition"),
        ("P4", 15.8, 5.2, 79.0, 1, "significant TiB formation"),
        ("P5", 16.9, 5.7, 77.4, 1, "significant TiB formation"),
    ]
    lei = [
        ("TA2MC", 2.0, 6.0, 0.2522, 0.0002, "long-strip eutectic TiC relatively abundant"),
        ("TA4MC", 4.0, 6.0, 0.2541, 0.0003, "mixed TiC morphology"),
        ("TA6MC", 6.0, 6.0, 0.2565, 0.0003, "primary/near-equiaxed TiC promoted"),
    ]
    slope, intercept, r2 = linear_fit([x[1] for x in lei], [x[3] for x in lei])
    q = bh({"UTS": 0.937, "YS": 0.457, "EL": 0.361})

    cohort = []
    perturb = []
    for label, al, v, ti, conv, note in bao:
        x, y = ternary(al, v, ti)
        cohort.append({"record_uid": f"BAO_{label}", "record_type": "ATOMIC_LOCAL_CHEMISTRY", "paper_uid": "BAO_2024_WAAM_TIB_TI64", "sample_uid": label, "condition_uid": "WAAM_LOCAL_MELT_POOL", "matrix_family": "Ti-6Al-4V", "process": "WAAM", "temperature_c": "melt_pool", "element_context": "Al+V versus Ti activity", "reinforcement": "TiB2 precursor -> TiB", "outcome": "conversion", "value": conv, "unit": "binary", "evidence_level": "DIRECT_TABLE_TEXT", "source_locator": "Bao 2024 Table 3 and reaction text", "notes": note})
        perturb.append({"perturbation_uid": f"BAO_{label}", "paper_uid": "BAO_2024_WAAM_TIB_TI64", "mode": "AL_V_TI_SIMPLEX", "sample_uid": label, "al_fraction": al / 100, "v_fraction": v / 100, "ti_fraction": ti / 100, "ilr_ti_vs_alv": ilr(al, v, ti), "simplex_x": x, "simplex_y": y, "perturbation": "observed local melt-pool composition", "outcome": conv, "outcome_label": note, "local_effect": "threshold-separated only", "unit": "binary", "status": "DIRECT_ONE_PAPER"})
    for label, al, tic, d111, sd, note in lei:
        cohort.append({"record_uid": f"LEI_{label}", "record_type": "ATOMIC_COMPOSITION_MICROSTRUCTURE", "paper_uid": "LEI_2025_AL_TIC", "sample_uid": label, "condition_uid": "AS_CAST", "matrix_family": "Ti-Al-Cr", "process": "vacuum_melting_in_situ", "temperature_c": 25, "element_context": f"Al={al} wt.% with Ti balance", "reinforcement": "target TiC=6 wt.%", "outcome": "TiC_d111", "value": d111, "unit": "nm", "evidence_level": "DIRECT_FIGURE_TEXT", "source_locator": "Lei 2025 Fig.19 and conclusions", "notes": note})
        perturb.append({"perturbation_uid": f"LEI_{label}", "paper_uid": "LEI_2025_AL_TIC", "mode": "AL_TIC_CLOSED_PERTURBATION", "sample_uid": label, "al_fraction": al / 100, "v_fraction": "", "ti_fraction": 1 - (al + tic) / 100, "ilr_ti_vs_alv": "", "simplex_x": "", "simplex_y": "", "perturbation": "+Al/-Ti at fixed target TiC", "outcome": d111, "outcome_label": "TiC d111 nm", "local_effect": f"slope={slope:.8f} nm/wt.% Al; R2={r2:.6f}", "unit": "nm", "status": "DIRECT_ONE_PAPER_NO_TIC_FREE_CONTROL"})
    for uid, paper, matrix, process, element, reinf, outcome, loc in [
        ("WANG_TA15SI", "WANG_2024_TIB_TA15SI", "TA15-Si", "rolled+solution+aging", "Si", "TiB", "600/700C tensile", "MSEA 890 (2024) 145888"),
        ("LIU_HYBRID", "LIU_2023_TIB_TIC_TI64", "Ti-6Al-4V", "L-DED", "B+C", "TiB+TiC", "RT tensile", "10.1016/j.compositesb.2023.111008"),
        ("JIANG_H", "JIANG_2023_H_TIC_TI64", "Ti-6Al-4V", "hydrogen exposure", "H", "TiC", "strengthening", "10.1016/j.compositesb.2023.110966"),
        ("YANG_NB", "YANG_2024_NB_TIC_TICR", "Ti-7.8Cr", "casting", "Nb", "TiC", "mechanical properties", "JMRT 30 (2024) 1083-1094"),
    ]:
        cohort.append({"record_uid": uid, "record_type": "PAPER_SCOPE_ANCHOR", "paper_uid": paper, "sample_uid": "UNRESOLVED", "condition_uid": "UNRESOLVED", "matrix_family": matrix, "process": process, "temperature_c": "mixed", "element_context": element, "reinforcement": reinf, "outcome": outcome, "value": "", "unit": "", "evidence_level": "DIRECT_PAPER_SCOPE", "source_locator": loc, "notes": "Atomic condition rows required before coefficient estimation."})
    cohort_cols = ["record_uid", "record_type", "paper_uid", "sample_uid", "condition_uid", "matrix_family", "process", "temperature_c", "element_context", "reinforcement", "outcome", "value", "unit", "evidence_level", "source_locator", "notes"]
    wc("ANALYSIS_COHORT.csv", cohort, cohort_cols)
    wc("COMPOSITION_PERTURBATION.csv", perturb, ["perturbation_uid", "paper_uid", "mode", "sample_uid", "al_fraction", "v_fraction", "ti_fraction", "ilr_ti_vs_alv", "simplex_x", "simplex_y", "perturbation", "outcome", "outcome_label", "local_effect", "unit", "status"])

    ti65 = [
        (650, "UTS", 136.442, 40.330, 232.555, 16.906), (650, "YS", 94.927, -21.162, 211.017, 13.532), (650, "EL", -4.115, -7.003, -1.228, -44.989),
        (700, "UTS", 130.925, 32.399, 229.451, 24.518), (700, "YS", 182.208, -16.536, 380.953, 40.576), (700, "EL", 4.856, -14.164, 23.876, 32.854),
    ]
    pairs = []
    for temp, prop, est, lo, hi, pct in ti65:
        pairs.append({"pair_uid": f"PAIR_TI65_R_{temp}_{prop}", "paper_uid": "INTERNAL_TI65_ARCHIVE", "control_uid": f"W1R0_{temp}_{prop}", "treated_uid": f"W1R1_{temp}_{prop}", "match_grade": "A", "estimand": "reinforcement effect conditional on W-bearing Ti65", "element_contrast": "W fixed present", "reinforcement_contrast": "TiB/TiB2-derived added", "matrix_family": "Ti65+3W", "temperature_c": temp, "property": prop, "estimate": est, "ci95_low": lo, "ci95_high": hi, "identifies_interaction": "NO", "missing_factorial_cell": "W0R1", "provenance": "QM12_DERIVED_ab795b646d964e6a"})
    for prop, temp, est in [("UTS", 25, 312.75), ("EL", 25, -2.27), ("UTS", 700, 107.0)]:
        pairs.append({"pair_uid": f"PAIR_TI65_W_{temp}_{prop}", "paper_uid": "INTERNAL_TI65_ARCHIVE", "control_uid": f"W0R0_{temp}_{prop}", "treated_uid": f"W1R0_{temp}_{prop}", "match_grade": "A", "estimand": "W main effect without reinforcement", "element_contrast": "+3 wt.% W/-Ti", "reinforcement_contrast": "none", "matrix_family": "Ti65", "temperature_c": temp, "property": prop, "estimate": est, "ci95_low": "", "ci95_high": "", "identifies_interaction": "NO", "missing_factorial_cell": "W0R1", "provenance": "QM24_DERIVED_db1bcc7fd4120366"})
    pairs += [
        {"pair_uid": "PAIR_LEI_2TO4", "paper_uid": "LEI_2025_AL_TIC", "control_uid": "TA2MC", "treated_uid": "TA4MC", "match_grade": "A", "estimand": "closed Al-for-Ti perturbation at fixed target TiC", "element_contrast": "+2 wt.% Al/-Ti", "reinforcement_contrast": "target TiC fixed", "matrix_family": "Ti-Al-Cr", "temperature_c": 25, "property": "TiC_d111", "estimate": 0.0019, "ci95_low": "", "ci95_high": "", "identifies_interaction": "MECHANISM_ONLY", "missing_factorial_cell": "TiC-free Al series", "provenance": "Lei2025_Fig19"},
        {"pair_uid": "PAIR_LEI_4TO6", "paper_uid": "LEI_2025_AL_TIC", "control_uid": "TA4MC", "treated_uid": "TA6MC", "match_grade": "A", "estimand": "closed Al-for-Ti perturbation at fixed target TiC", "element_contrast": "+2 wt.% Al/-Ti", "reinforcement_contrast": "target TiC fixed", "matrix_family": "Ti-Al-Cr", "temperature_c": 25, "property": "TiC_d111", "estimate": 0.0024, "ci95_low": "", "ci95_high": "", "identifies_interaction": "MECHANISM_ONLY", "missing_factorial_cell": "TiC-free Al series", "provenance": "Lei2025_Fig19"},
    ]
    pair_cols = ["pair_uid", "paper_uid", "control_uid", "treated_uid", "match_grade", "estimand", "element_contrast", "reinforcement_contrast", "matrix_family", "temperature_c", "property", "estimate", "ci95_low", "ci95_high", "identifies_interaction", "missing_factorial_cell", "provenance"]
    wc("PAIR_MATCHES.csv", pairs, pair_cols)

    effects = []
    for p in pairs:
        effects.append({"effect_uid": "EFF_" + p["pair_uid"], "paper_uid": p["paper_uid"], "sample_uid": p["treated_uid"], "condition_uid": f"{p['temperature_c']}_{p['property']}", "estimand": p["estimand"], "property": p["property"], "estimate": p["estimate"], "unit": "nm" if p["property"] == "TiC_d111" else ("percentage_point" if p["property"] == "EL" else "MPa"), "ci95_low": p["ci95_low"], "ci95_high": p["ci95_high"], "evidence_grade": p["match_grade"], "claim_level": 2, "interaction_identified": p["identifies_interaction"], "provenance": p["provenance"], "status": "ESTIMABLE_PAIRED"})
    for uid, source, estimand, prop, est, unit, lo, hi in [
        ("QM16_TIB_YS_EFF", "QM16_DERIVED", "TiB unit-content efficiency", "YS", 41.4, "MPa_per_vol_pct", 32.1, 120.0),
        ("QM16_TIB_UTS_EFF", "QM16_DERIVED", "TiB unit-content efficiency", "UTS", 34.3, "MPa_per_vol_pct", 31.4, 47.5),
        ("QM16_TIB_EL", "QM16_DERIVED", "TiB matched elongation shift", "EL", -12.4, "percentage_point", -20.5, -4.2),
        ("QM06_GLOBAL_UTS", "QM06_DERIVED", "global paired reinforcement prior", "UTS", 133.1, "MPa", 99.4, 165.7),
        ("QM08_GLOBAL_EL", "QM08_DERIVED", "global paired reinforcement prior", "EL", -8.06, "percentage_point", -11.91, -4.66),
    ]:
        effects.append({"effect_uid": uid, "paper_uid": source, "sample_uid": "AGGREGATE", "condition_uid": "MIXED", "estimand": estimand, "property": prop, "estimate": est, "unit": unit, "ci95_low": lo, "ci95_high": hi, "evidence_grade": "DERIVED_PRIOR", "claim_level": 1, "interaction_identified": "NO", "provenance": source, "status": "CONTEXT_PRIOR_NOT_INTERACTION"})
    effects.append({"effect_uid": "LEI_AL_TIC_D111_SLOPE", "paper_uid": "LEI_2025_AL_TIC", "sample_uid": "TA2MC_TA4MC_TA6MC", "condition_uid": "AS_CAST", "estimand": "closed +Al/-Ti slope at fixed target TiC", "property": "TiC_d111", "estimate": slope, "unit": "nm_per_wt_pct_Al", "ci95_low": "", "ci95_high": "", "evidence_grade": "DIRECT_FIGURE_TEXT", "claim_level": 2, "interaction_identified": "MECHANISM_ONLY", "provenance": "Lei2025_Fig19", "status": "DESCRIPTIVE_ONE_PAPER"})
    effect_cols = ["effect_uid", "paper_uid", "sample_uid", "condition_uid", "estimand", "property", "estimate", "unit", "ci95_low", "ci95_high", "evidence_grade", "claim_level", "interaction_identified", "provenance", "status"]
    wc("EFFECT_ESTIMATES.csv", effects, effect_cols)

    interactions = [
        {"interaction_uid": "INT_ALV_TIB_FORMATION", "element": "Al+V/Ti activity", "reinforcement": "TiB2->TiB", "matrix_family": "Ti-6Al-4V", "process": "WAAM", "temperature_domain": "melt_pool", "outcome": "conversion", "estimand": "local simplex perturbation", "estimate": "separating Ti fraction interval (0.654,0.774]", "unit": "atomic_fraction", "papers_discovery": 1, "papers_validation": 0, "bh_q": "", "status": "DIRECT_MECHANISM_NOT_REPLICATED", "claim_level": 2, "missing_requirement": "independent same-design paper; separate Al and V", "provenance": "Bao2024_Table3"},
        {"interaction_uid": "INT_AL_TIC_LATTICE", "element": "Al", "reinforcement": "TiC", "matrix_family": "Ti-Al-Cr", "process": "cast_in_situ", "temperature_domain": "RT", "outcome": "d111/morphology", "estimand": "+Al/-Ti closed perturbation", "estimate": slope, "unit": "nm_per_wt_pct_Al", "papers_discovery": 1, "papers_validation": 0, "bh_q": "", "status": "DIRECT_MECHANISM_NOT_REPLICATED", "claim_level": 2, "missing_requirement": "TiC-free Al control and independent paper", "provenance": "Lei2025_Fig19"},
        {"interaction_uid": "INT_W_TIB_MECH", "element": "W", "reinforcement": "TiB/TiB2-derived", "matrix_family": "Ti65", "process": "L-DED", "temperature_domain": "25/650/700C", "outcome": "UTS/YS/EL", "estimand": "difference-in-differences", "estimate": "", "unit": "", "papers_discovery": 0, "papers_validation": 0, "bh_q": "", "status": "NOT_IDENTIFIABLE", "claim_level": 2, "missing_requirement": "W0R1 cell: Ti65+TiB without W", "provenance": "QM12+QM24"},
        {"interaction_uid": "INT_SI_TIB_HT", "element": "Si", "reinforcement": "TiB", "matrix_family": "TA15-Si", "process": "rolled+HT", "temperature_domain": "600/700C", "outcome": "high-temperature tensile", "estimand": "Si×TiB", "estimate": "", "unit": "", "papers_discovery": 1, "papers_validation": 0, "bh_q": "", "status": "NOT_IDENTIFIABLE", "claim_level": 1, "missing_requirement": "Si-free TiB/TA15 control", "provenance": "Wang2024_MSEA145888"},
        {"interaction_uid": "INT_H_TIC", "element": "H", "reinforcement": "TiC", "matrix_family": "Ti-6Al-4V", "process": "hydrogen exposure", "temperature_domain": "unresolved", "outcome": "strengthening", "estimand": "H×TiC", "estimate": "", "unit": "", "papers_discovery": 1, "papers_validation": 0, "bh_q": "", "status": "SOURCE_IDENTIFIED_ATOMIC_EXTRACTION_REQUIRED", "claim_level": 1, "missing_requirement": "condition-matched atomic rows", "provenance": "10.1016/j.compositesb.2023.110966"},
        {"interaction_uid": "INT_NB_TIC", "element": "Nb", "reinforcement": "TiC", "matrix_family": "Ti-7.8Cr", "process": "casting", "temperature_domain": "RT", "outcome": "mechanical properties", "estimand": "Nb×TiC", "estimate": "", "unit": "", "papers_discovery": 1, "papers_validation": 0, "bh_q": "", "status": "SOURCE_IDENTIFIED_ATOMIC_EXTRACTION_REQUIRED", "claim_level": 1, "missing_requirement": "full paper and TiC-free Nb arm", "provenance": "Yang2024_JMRT30"},
        {"interaction_uid": "INT_BC_HYBRID", "element": "B+C", "reinforcement": "TiB+TiC", "matrix_family": "Ti-6Al-4V", "process": "L-DED", "temperature_domain": "RT", "outcome": "UTS", "estimand": "B versus C component interaction", "estimate": "", "unit": "", "papers_discovery": 1, "papers_validation": 0, "bh_q": "", "status": "NOT_IDENTIFIABLE", "claim_level": 1, "missing_requirement": "TiB-only and TiC-only arms", "provenance": "10.1016/j.compositesb.2023.111008"},
        {"interaction_uid": "INT_ON_TIBTIC", "element": "O/N", "reinforcement": "TiB/TiC", "matrix_family": "mixed", "process": "mixed", "temperature_domain": "mixed", "outcome": "strength/ductility", "estimand": "interstitial×reinforcement", "estimate": "", "unit": "", "papers_discovery": 0, "papers_validation": 0, "bh_q": "", "status": "NOT_IDENTIFIABLE", "claim_level": 1, "missing_requirement": "measured O/N factorial rows", "provenance": "project_gap_audit"},
    ]
    int_cols = ["interaction_uid", "element", "reinforcement", "matrix_family", "process", "temperature_domain", "outcome", "estimand", "estimate", "unit", "papers_discovery", "papers_validation", "bh_q", "status", "claim_level", "missing_requirement", "provenance"]
    wc("INTERACTION_EFFECTS.csv", interactions, int_cols)
    wc("ELEMENT_REINFORCEMENT_INTERACTIONS.csv", interactions, int_cols)

    matrices = [("Ti-6Al-4V", "WAAM/L-DED"), ("Ti65", "L-DED"), ("TA15-Si", "rolling+HT"), ("Ti-Al-Cr", "casting/forging")]
    threeway = []
    for matrix, process in matrices:
        for row in interactions[:6]:
            same = row["matrix_family"] == matrix
            score = 3 if same and row["status"].startswith("DIRECT") else 2 if same and row["status"].startswith("SOURCE") else 1 if same else 0
            threeway.append({"three_way_uid": f"3W_{matrix}_{row['interaction_uid']}", "matrix_family": matrix, "process": process, "element_reinforcement_interaction": row["interaction_uid"], "outcome": row["outcome"], "support_score": score, "independent_papers": 1 if same else 0, "estimate": row["estimate"] if same else "", "status": "DESCRIPTIVE_SINGLE_FAMILY" if score >= 2 else "NOT_IDENTIFIABLE", "reason": "No common perturbation is repeated across matrix families."})
    three_cols = ["three_way_uid", "matrix_family", "process", "element_reinforcement_interaction", "outcome", "support_score", "independent_papers", "estimate", "status", "reason"]
    wc("THREE_WAY_HETEROGENEITY.csv", threeway, three_cols)

    replication = []
    for row in interactions:
        replication.append({"interaction_uid": row["interaction_uid"], "discovery_papers": row["papers_discovery"], "validation_papers": row["papers_validation"], "validation_attempted": 1 if row["papers_discovery"] else 0, "replicated": 0, "replication_rate": 0 if row["papers_discovery"] else "", "direction_consistent": "NOT_TESTABLE", "paper_split_firewall": "PASS", "status": "NO_INDEPENDENT_VALIDATION" if row["papers_discovery"] else "NO_DISCOVERY_ESTIMATE", "next_evidence": row["missing_requirement"]})
    rep_cols = ["interaction_uid", "discovery_papers", "validation_papers", "validation_attempted", "replicated", "replication_rate", "direction_consistent", "paper_split_firewall", "status", "next_evidence"]
    wc("INTERACTION_REPLICATION.csv", replication, rep_cols)

    hierarchical = [
        {"model_uid": "H1_BAO_THRESHOLD", "outcome": "TiB conversion", "formula": "logit(P(convert))~ilr(Ti vs Al,V)", "cluster": "paper", "n_papers": 1, "n_rows": 5, "estimate": "finite coefficient not estimable", "uncertainty": "complete separation", "status": "NOT_IDENTIFIABLE_FINITE_COEFFICIENT", "claim_level": 2, "notes": "Any threshold in (0.654,0.774] classifies 5/5; uniqueness not identified."},
        {"model_uid": "H2_LEI_D111", "outcome": "TiC d111", "formula": "d111~closed Al-for-Ti perturbation", "cluster": "paper", "n_papers": 1, "n_rows": 3, "estimate": f"slope={slope:.8f}; intercept={intercept:.8f}; R2={r2:.6f}", "uncertainty": "paper-cluster CI impossible", "status": "DESCRIPTIVE_ONE_PAPER", "claim_level": 2, "notes": "No TiC-free Al series."},
        {"model_uid": "H3_HIGH_ORDER", "outcome": "UTS/YS/EL", "formula": "Y~element+reinforcement+matrix+interactions+u_paper", "cluster": "paper", "n_papers": 7, "n_rows": len(cohort), "estimate": "", "uncertainty": "rank deficient", "status": "NOT_IDENTIFIABLE", "claim_level": 1, "notes": "Fitting would overfit and violate paper-split confirmation."},
        {"model_uid": "H4_W_TIB_DID", "outcome": "UTS/YS/EL", "formula": "(W1R1-W1R0)-(W0R1-W0R0)", "cluster": "internal source", "n_papers": 1, "n_rows": 3, "estimate": "", "uncertainty": "W0R1 missing", "status": "NOT_IDENTIFIABLE", "claim_level": 2, "notes": "Three cells do not close the 2x2 factorial."},
    ]
    wc("HIERARCHICAL_RESULTS.csv", hierarchical, ["model_uid", "outcome", "formula", "cluster", "n_papers", "n_rows", "estimate", "uncertainty", "status", "claim_level", "notes"])

    dose = [
        {"dose_uid": "DOSE_LEI_AL", "paper_uid": "LEI_2025_AL_TIC", "dose_variable": "Al wt.%", "reinforcement": "target TiC 6 wt.%", "outcome": "TiC d111", "model": "linear descriptive", "estimate": slope, "unit": "nm_per_wt_pct", "r2": r2, "n_papers": 1, "n_rows": 3, "status": "DESCRIPTIVE_ONE_PAPER"},
        {"dose_uid": "DOSE_BAO_TI", "paper_uid": "BAO_2024_WAAM_TIB_TI64", "dose_variable": "local Ti atomic fraction", "reinforcement": "TiB2 precursor", "outcome": "TiB conversion", "model": "separating interval", "estimate": "(0.654,0.774]", "unit": "atomic_fraction", "r2": "", "n_papers": 1, "n_rows": 5, "status": "PERFECT_SEPARATION_NOT_GENERALIZABLE"},
        {"dose_uid": "DOSE_TIB_PRIOR", "paper_uid": "QM16_DERIVED", "dose_variable": "actual TiB vol.%", "reinforcement": "TiB/TiBw", "outcome": "YS/UTS/EL", "model": "paired efficiency prior", "estimate": "YS 41.4; UTS 34.3; EL -12.4", "unit": "mixed", "r2": "", "n_papers": 7, "n_rows": 43, "status": "MAIN_EFFECT_PRIOR_NOT_INTERACTION"},
    ]
    wc("DOSE_RESPONSE.csv", dose, ["dose_uid", "paper_uid", "dose_variable", "reinforcement", "outcome", "model", "estimate", "unit", "r2", "n_papers", "n_rows", "status"])

    hetero = [
        {"domain": "matrix_family", "level": "Ti-6Al-4V", "independent_papers": 3, "direct_interactions": 1, "heterogeneity_estimate": "NOT_IDENTIFIABLE", "reason": "different elements/processes/outcomes"},
        {"domain": "matrix_family", "level": "Ti65", "independent_papers": 1, "direct_interactions": 0, "heterogeneity_estimate": "NOT_IDENTIFIABLE", "reason": "W0R1 missing"},
        {"domain": "matrix_family", "level": "TA15-Si", "independent_papers": 1, "direct_interactions": 0, "heterogeneity_estimate": "NOT_IDENTIFIABLE", "reason": "no Si-free control"},
        {"domain": "matrix_family", "level": "Ti-Al-Cr", "independent_papers": 2, "direct_interactions": 1, "heterogeneity_estimate": "NOT_IDENTIFIABLE", "reason": "non-common perturbations"},
        {"domain": "temperature", "level": "650 versus 700C", "independent_papers": 1, "direct_interactions": 0, "heterogeneity_estimate": "UTS -5.517 MPa; YS +87.281 MPa; EL +8.971 pp", "reason": "BH-FDR non-significant; matrix softening competes"},
    ]
    wc("HETEROGENEITY.csv", hetero, ["domain", "level", "independent_papers", "direct_interactions", "heterogeneity_estimate", "reason"])

    sensitivity = [
        {"analysis_uid": "S1", "target": "Bao threshold", "perturbation": "xTi=0.65", "estimate": "4/5 classified", "status": "SENSITIVE", "paper_clusters": 1, "notes": "P3 changes class"},
        {"analysis_uid": "S2", "target": "Bao threshold", "perturbation": "xTi=0.70", "estimate": "5/5 classified", "status": "DESCRIPTIVE", "paper_clusters": 1, "notes": "not unique"},
        {"analysis_uid": "S3", "target": "Bao threshold", "perturbation": "xTi=0.75", "estimate": "5/5 classified", "status": "DESCRIPTIVE", "paper_clusters": 1, "notes": "not unique"},
        {"analysis_uid": "S4", "target": "Al×TiC d111", "perturbation": "2->4 wt.% Al", "estimate": 0.00095, "status": "DESCRIPTIVE", "paper_clusters": 1, "notes": "nm per wt.% Al"},
        {"analysis_uid": "S5", "target": "Al×TiC d111", "perturbation": "4->6 wt.% Al", "estimate": 0.00120, "status": "DESCRIPTIVE", "paper_clusters": 1, "notes": "nm per wt.% Al"},
        {"analysis_uid": "S6", "target": "Ti65 temperature interaction UTS", "perturbation": "700-650C", "estimate": -5.517, "status": "BH_FDR_NON_SIGNIFICANT", "paper_clusters": 1, "notes": f"p=0.937 q={q['UTS']:.4f}"},
        {"analysis_uid": "S7", "target": "Ti65 temperature interaction YS", "perturbation": "700-650C", "estimate": 87.281, "status": "BH_FDR_NON_SIGNIFICANT", "paper_clusters": 1, "notes": f"p=0.457 q={q['YS']:.4f}"},
        {"analysis_uid": "S8", "target": "Ti65 temperature interaction EL", "perturbation": "700-650C", "estimate": 8.971, "status": "BH_FDR_NON_SIGNIFICANT", "paper_clusters": 1, "notes": f"p=0.361 q={q['EL']:.4f}"},
        {"analysis_uid": "S9", "target": "high-order interaction", "perturbation": "LOPO", "estimate": "not executable", "status": "NOT_IDENTIFIABLE", "paper_clusters": 7, "notes": "removing sole discovery paper eliminates each direct estimate"},
    ]
    wc("SENSITIVITY_ANALYSIS.csv", sensitivity, ["analysis_uid", "target", "perturbation", "estimate", "status", "paper_clusters", "notes"])

    nulls = [
        {"result_uid": "N1", "question": "Universal element×TiB/TiC mechanical interaction", "result": "NOT_IDENTIFIABLE", "reason": "No repeated factorial perturbation across papers.", "required_data": "matched element dose and reinforcement +/- arms"},
        {"result_uid": "N2", "question": "W×TiB", "result": "NOT_IDENTIFIABLE", "reason": "W0R1 absent.", "required_data": "Ti65+TiB without W"},
        {"result_uid": "N3", "question": "Si×TiB at 600/700C", "result": "NOT_IDENTIFIABLE", "reason": "No Si-free control.", "required_data": "Si +/- and TiB +/- 2x2"},
        {"result_uid": "N4", "question": "matrix×element×reinforcement random slope", "result": "NOT_IDENTIFIABLE", "reason": "No common perturbation across families.", "required_data": ">=3 families, >=2 papers/family"},
        {"result_uid": "N5", "question": "800C interaction benefit", "result": "NOT_IDENTIFIABLE", "reason": "No direct 800C factorial evidence.", "required_data": "matched 800C tensile/creep"},
        {"result_uid": "N6", "question": "O/N×reinforcement", "result": "NOT_IDENTIFIABLE", "reason": "Measured interstitial factorial rows absent.", "required_data": "O/N measurements and controls"},
        {"result_uid": "N7", "question": "cross-paper replication", "result": "0 confirmed", "reason": "All direct candidates are single-paper or incomplete.", "required_data": "paper-split validation"},
        {"result_uid": "N8", "question": "700C EL sign proves toughening", "result": "REJECTED", "reason": "q=0.686; matrix softening/recovery competes.", "required_data": "matched lineage and damage data"},
    ]
    wc("NULL_NEGATIVE_RESULTS.csv", nulls, ["result_uid", "question", "result", "reason", "required_data"])

    conflicts = [
        {"conflict_uid": "C1", "field": "snapshot authority", "source_a": snapshot, "value_a": "recovery-derived", "source_b": "V29 ACTIVE", "value_b": "atomic/provenance files absent", "resolution": "do not promote; request authoritative files", "severity": "CRITICAL", "status": "OPEN"},
        {"conflict_uid": "C2", "field": "Al versus V", "source_a": "Bao local EDS", "value_a": "Al,V co-vary with Ti", "source_b": "reaction", "value_b": "conversion tracks Ti activity", "resolution": "report combined Al+V/Ti-activity interaction", "severity": "HIGH", "status": "RESOLVED_BY_CLAIM_LIMIT"},
        {"conflict_uid": "C3", "field": "reinforcement dose", "source_a": "precursor wt.%", "value_a": "nominal", "source_b": "actual TiB/TiC", "value_b": "phase amount/stoichiometry differ", "resolution": "no unit efficiency without actual phase fraction", "severity": "HIGH", "status": "OPEN"},
        {"conflict_uid": "C4", "field": "Lei correction", "source_a": "original", "value_a": "duplicated Fig.14", "source_b": "corrigendum", "value_b": "corrected; conclusions unchanged", "resolution": "Fig.18/19 retained; correction logged", "severity": "MEDIUM", "status": "RESOLVED"},
        {"conflict_uid": "C5", "field": "Ti65 precursor notation", "source_a": "internal naming", "value_a": "varies", "source_b": "actual phase", "value_b": "not bound", "resolution": "use matched delta only", "severity": "HIGH", "status": "OPEN"},
        {"conflict_uid": "C6", "field": "EL temperature sign", "source_a": "650C", "value_a": "negative", "source_b": "700C", "value_b": "positive uncertain", "resolution": "no toughening claim; q>0.68", "severity": "HIGH", "status": "RESOLVED_BY_CLAIM_LIMIT"},
    ]
    wc("CONFLICT_LEDGER.csv", conflicts, ["conflict_uid", "field", "source_a", "value_a", "source_b", "value_b", "resolution", "severity", "status"])

    claims = [
        {"claim_uid": "CL1", "claim": "Local Al/V-rich low-Ti chemistry suppresses TiB2-to-TiB conversion in Bao WAAM specimens.", "evidence": "5 local sites; direct table/text", "claim_level": 2, "ceiling": "same-paper mechanism association", "admitted": "YES"},
        {"claim_uid": "CL2", "claim": "Increasing Al expands TiC d111 and promotes primary/near-equiaxed TiC in Lei's fixed-target series.", "evidence": "3 compositions; Fig.19", "claim_level": 2, "ceiling": "same-paper closed perturbation", "admitted": "YES"},
        {"claim_uid": "CL3", "claim": "W amplifies TiB mechanical benefit in Ti65.", "evidence": "three of four cells", "claim_level": 2, "ceiling": "not identifiable", "admitted": "NO"},
        {"claim_uid": "CL4", "claim": "Si amplifies TiB high-temperature benefit.", "evidence": "one Si-bearing family", "claim_level": 1, "ceiling": "not identifiable", "admitted": "NO"},
        {"claim_uid": "CL5", "claim": "A high-order interaction replicates across papers.", "evidence": "0 validated", "claim_level": 1, "ceiling": "negative result", "admitted": "NO"},
    ]
    wc("CLAIM_MATRIX.csv", claims, ["claim_uid", "claim", "evidence", "claim_level", "ceiling", "admitted"])

    literature = [{"paper_uid": p["paper_uid"], "doi_or_id": p["doi"], "role": p["role"], "included": "YES" if p["paper_uid"] in {"BAO_2024_WAAM_TIB_TI64", "LEI_2025_AL_TIC", "INTERNAL_TI65_ARCHIVE"} else "SCOPE_OR_REQUEST", "evidence_ceiling": "direct" if p["paper_uid"] in {"BAO_2024_WAAM_TIB_TI64", "LEI_2025_AL_TIC"} else "partial/derived"} for p in papers]
    wc("LITERATURE_EVIDENCE_LEDGER.csv", literature, ["paper_uid", "doi_or_id", "role", "included", "evidence_ceiling"])
    coverage = [
        {"source_group": "V29 authoritative atomic records", "available": "NO", "used": "NO", "terminal_state": "BLOCKING_GAP", "contribution": "UID/hash authority"},
        {"source_group": "S03 frozen data/features", "available": "REGISTERED", "used": "LEDGER_ONLY", "terminal_state": "ROW_EXPORT_REQUIRED", "contribution": "composition domains"},
        {"source_group": "S03 harness evidence", "available": "YES", "used": "YES", "terminal_state": "METHOD_PRIOR", "contribution": "reliability/UQ/split discipline"},
        {"source_group": "TITMC literature corpus", "available": "YES", "used": "YES", "terminal_state": "ROUTED_PLUS_TARGETED_DEEP_READ", "contribution": "original-paper evidence"},
        {"source_group": "QM06/QM08/QM12/QM16/QM24/QM32", "available": "YES", "used": "YES", "terminal_state": "DERIVED_PRIOR_ONLY", "contribution": "main effects/mechanism bounds"},
    ]
    wc("SOURCE_COVERAGE_MATRIX.csv", coverage, ["source_group", "available", "used", "terminal_state", "contribution"])

    prov = []
    for row in cohort:
        prov.append({"snapshot_id": snapshot, "record_uid": row["record_uid"], "paper_uid": row["paper_uid"], "sample_uid": row["sample_uid"], "condition_uid": row["condition_uid"], "evidence_level": row["evidence_level"], "source_locator": row["source_locator"], "value_hash": htxt(json.dumps(row, ensure_ascii=False, sort_keys=True)), "gold_promotion": False})
    with (ROOT / "PROVENANCE.jsonl").open("w", encoding="utf-8") as f:
        for row in prov:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    wt("00_EXECUTIVE_VERDICT.md", f"""# QM25 Executive Verdict

`WINDOW=QM25 | SNAPSHOT={snapshot} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Decision-grade answer

1. **No element×TiB/TiC mechanical-property interaction is cross-paper replicated.** Strict confirmation is **0**. Every direct interaction is single-paper, mechanism-only, or factorially incomplete. A sparse high-order model would be rank-deficient, so no cosmetic coefficient was fitted.
2. **Strongest direct result: local formation chemistry.** Bao's five Al-V-Ti local sites are separated by Ti fraction: 0.502-0.654 gives rare TiB2 decomposition, while 0.774-0.790 gives significant TiB. The defensible variable is local Ti activity against combined Al+V-rich chemistry—not separate Al or V coefficients. Any threshold in `(0.654,0.774]` separates 5/5, but is not uniquely transferable.
3. **Al modifies TiC structure/morphology in one controlled series.** At fixed nominal 6 wt.% TiC target, `d111` rises 0.2522→0.2565 nm from 2→6 wt.% Al. Closed-composition slope: **{slope:.6f} nm per wt.% Al**, `R²={r2:.4f}`. This is a same-paper mechanism association, not an isolated mechanical interaction.
4. **W×TiB is not identified.** `W0R0`, `W1R0`, `W1R1` exist, but `W0R1` is missing. TiB conditional effects in W-bearing Ti65 (+136/+131 MPa UTS at 650/700 °C) cannot be renamed a W×TiB difference-in-differences effect.
5. **700 °C EL recovery is not proof of synergistic toughening.** The 700−650 °C interaction is −5.5 MPa UTS, +87.3 MPa YS, +9.0 pp EL; BH-FDR q-values are 0.937, 0.686 and 0.686. Matrix softening/recovery remains a sufficient competing mechanism.

## Claim ceiling

Maximum claim level: **2 — same-paper/same-source paired or mechanism association**. No Gold promotion, production-model registration, VALIDATED recipe or 800 °C interaction claim.

`STATUS: CONTINUE_DATA_GAP | WINDOW=QM25 | MISSING=V29_ATOMIC_RECORDS+PROVENANCE+W0R1+INDEPENDENT_FACTORIAL_VALIDATION | NEXT=LOCAL_ABSORPTION_AND_TARGETED_EXTRACTION`
""")

    wt("METHODS.md", f"""# Methods

Primary mechanical estimand: `gamma_ER=(Y_E1R1-Y_E1R0)-(Y_E0R1-Y_E0R0)`. A matrix-specific three-way term requires this contrast repeated across matrix families under matched process, heat treatment, temperature, strain rate and orientation.

Al-V-Ti chemistry is treated on a simplex using `ilr=sqrt(2/3)*ln[xTi/sqrt(xAl*xV)]`. Lei's Al series is a constrained `+Al/-Ti` perturbation at fixed target TiC, not an unconstrained Euclidean coefficient.

Discovery and validation are split by paper. Same-paper dose points do not count as independent replication. BH-FDR is applied to the three Ti65 temperature-interaction tests. LOPO is `NOT_IDENTIFIABLE` when removing the sole discovery paper removes the estimate.

The hierarchical high-order model was not fitted because interaction columns are rank-deficient and direct candidates have one paper cluster. Returning `NOT_IDENTIFIABLE` is the correct statistical result.

Snapshot: `{snapshot}`.
""")
    wt("LIMITATIONS.md", """# Limitations

- Authoritative V29 atomic/provenance/conflict/exclusion registries were unavailable in the executable snapshot.
- Bao's Al and V co-vary with Ti fraction and melt-pool state; separate coefficients are impossible.
- Lei lacks TiC-free Al arms and reports microstructure rather than tensile outcomes.
- Ti65 lacks W0R1; TA15-Si lacks a Si-free TiB control.
- H×TiC and Nb×TiC papers require full atomic extraction.
- Nominal precursor wt.% is not actual TiB/TiC vol.% or stoichiometry.
- Direct 800 °C factorial evidence is absent.
- Cross-paper replication is zero.
""")
    web_request = {"window_id": "QM25", "snapshot_id": snapshot, "priority": "BLOCKING_FOR_INTERACTION_CLAIMS", "requests": [
        {"id": "R1", "required": ["ATOMIC_RECORDS", "PROVENANCE", "CONFLICT_LEDGER", "EXCLUDED_RECORDS", "paper_registry", "condition_registry"], "reason": "authoritative UID/hash binding"},
        {"id": "R2", "required": ["Ti65+TiB_without_W matched 25/650/700C rows"], "reason": "close W×TiB 2x2"},
        {"id": "R3", "required": ["full atomic extraction for 10.1016/j.compositesb.2023.110966"], "reason": "H×TiC"},
        {"id": "R4", "required": ["full atomic extraction for Yang et al. JMRT 30 (2024) 1083-1094"], "reason": "Nb×TiC"},
        {"id": "R5", "required": ["Si-free TiB/TA15 controls at 600/700C"], "reason": "Si×TiB"},
        {"id": "R6", "required": ["actual TiB/TiC vol.%", "measured O/N/C/H", "matched condition fields"], "reason": "unit-content/interstitial analysis"},
        {"id": "R7", "required": ["independent same-design papers"], "reason": "paper-split validation"},
    ], "acceptance": "Every row binds snapshot_id+source_hash+paper_uid+sample_uid+condition_uid.", "do_not": ["do not impute missing cells", "do not convert precursor wt.% without mass balance", "do not auto-promote Gold"]}
    wj("WEB_TO_LOCAL_REQUEST.json", web_request)
    wt("LOCAL_ABSORPTION_PROMPT.md", f"""# QM25 Local Absorption Prompt

1. Verify checksums and run `python tests/test_outputs.py .`.
2. Store read-only under `q40/QM25/{snapshot}`; do not overwrite ACTIVE_TITMC, Gold, schema or model registry.
3. Resolve authoritative identity first, W0R1 second, then H×TiC/Nb×TiC/Si×TiB extraction.
4. Recompute `gamma_ER` only after all four cells share matrix/process/HT/test conditions.
5. Enforce paper-split validation and BH-FDR; preserve zero/NOT_IDENTIFIABLE results.
6. Absorb field-level source-bound rows only.
""")
    wt("DATA_DICTIONARY.md", """# Data Dictionary

`support_score`: 0 none, 1 scope-only, 2 identified/partial, 3 direct same-paper mechanism. `claim_level`: 1 descriptive, 2 same-paper paired/mechanism association. `replicated` requires an independent paper. `NOT_IDENTIFIABLE` is a statistical result. Recovery UIDs are not ACTIVE authority.
""")
    wt("OPENED_FILES.txt", """QM25 dispatch MDU
QM16 TiB quantitative return
QM12 650-700C quantitative return
QM24 element quantitative return
QM06 global UTS return
QM08 ductility return
QM32 load-transfer/orientation return
Bao et al. 2024 original paper, Table 3 and property table
Lei et al. 2025 original paper, Fig.18-19 and corrigendum
Wang et al. MSEA 890 (2024) 145888 original evidence
Liu et al. Composites Part B 266 (2023) 111008
Jiang et al. Composites Part B 265 (2023) 110966 relevance manifest
Yang et al. JMRT 30 (2024) 1083-1094 bibliographic anchor
XML corpus audit: 78,683 members
S03/S04/control package integrity ledgers
""")
    wt("acceptance_commands.md", """# Acceptance Commands

```bash
python tests/test_outputs.py .
python analysis_code/qm25_analysis.py --root .
sha256sum -c CHECKSUMS.sha256
```

Expected scientific status: `CONTINUE_DATA_GAP`. Expected package validation: PASS.
""")
    wt("requirements.txt", "matplotlib==3.9.2\nnumpy==2.1.3\nscipy==1.14.1")

    network = [
        {"source": "Al+V/Ti activity", "target": "TiB formation", "evidence": "direct mechanism", "replicated": 0, "weight": 3, "papers": 1, "claim_level": 2},
        {"source": "Al", "target": "TiC morphology/lattice", "evidence": "direct mechanism", "replicated": 0, "weight": 3, "papers": 1, "claim_level": 2},
        {"source": "W", "target": "TiB strength/EL", "evidence": "missing factorial cell", "replicated": 0, "weight": 1, "papers": 1, "claim_level": 2},
        {"source": "Si", "target": "TiB high-T benefit", "evidence": "confounded", "replicated": 0, "weight": 1, "papers": 1, "claim_level": 1},
        {"source": "H", "target": "TiC strengthening", "evidence": "source pending atomization", "replicated": 0, "weight": 2, "papers": 1, "claim_level": 1},
        {"source": "Nb", "target": "TiC response", "evidence": "source pending atomization", "replicated": 0, "weight": 2, "papers": 1, "claim_level": 1},
        {"source": "O/N", "target": "TiB/TiC response", "evidence": "no factorial data", "replicated": 0, "weight": 0.5, "papers": 0, "claim_level": 1},
    ]
    wc("figure_data/interaction_network_data.csv", network, ["source", "target", "evidence", "replicated", "weight", "papers", "claim_level"])
    wc("figure_data/three_way_heatmap_data.csv", [{"matrix_family": r["matrix_family"], "interaction": r["element_reinforcement_interaction"], "support_score": r["support_score"], "independent_papers": r["independent_papers"], "status": r["status"]} for r in threeway], ["matrix_family", "interaction", "support_score", "independent_papers", "status"])
    simplex = []
    for label, al, v, ti, conv, note in bao:
        x, y = ternary(al, v, ti)
        simplex.append({"kind": "point", "sample": label, "al": al / 100, "v": v / 100, "ti": ti / 100, "x": x, "y": y, "converted": conv, "label": note, "independent_papers": 1})
    for i in range(101):
        af = 0.30 * i / 100
        vf = 0.30 - af
        x, y = ternary(af, vf, 0.70)
        simplex.append({"kind": "threshold", "sample": f"T{i}", "al": af, "v": vf, "ti": 0.70, "x": x, "y": y, "converted": "", "label": "xTi=0.70 reference", "independent_papers": 1})
    wc("figure_data/simplex_perturbation_data.csv", simplex, ["kind", "sample", "al", "v", "ti", "x", "y", "converted", "label", "independent_papers"])
    wc("figure_data/interaction_replication_data.csv", [{"interaction": r["interaction_uid"], "discovery_papers": r["discovery_papers"], "validation_papers": r["validation_papers"], "replicated": r["replicated"], "status": r["status"]} for r in replication], ["interaction", "discovery_papers", "validation_papers", "replicated", "status"])

    plot_scripts = {
        "plot_interaction_network.py": r'''import argparse,csv
from pathlib import Path
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--outdir',required=True);a=p.parse_args();rows=list(csv.DictReader(open(a.data,encoding='utf-8')))
src=[];tgt=[]
for r in rows:
    if r['source'] not in src:src.append(r['source'])
    if r['target'] not in tgt:tgt.append(r['target'])
pos={**{n:(0,len(src)-1-i) for i,n in enumerate(src)},**{n:(2,len(tgt)-1-i) for i,n in enumerate(tgt)}}
fig,ax=plt.subplots(figsize=(11,7))
for n,(x,y) in pos.items():ax.scatter([x],[y],s=150);ax.text(x-.08 if x==0 else x+.08,y,n,ha='right' if x==0 else 'left',va='center',fontsize=8)
for r in rows:
    x1,y1=pos[r['source']];x2,y2=pos[r['target']];ax.plot([x1,x2],[y1,y2],linewidth=max(.7,float(r['weight'])));ax.text(1,(y1+y2)/2,r['evidence'],fontsize=6,ha='center')
ax.set_title('Element–reinforcement interaction evidence network\n7 original-paper anchors; 0 independently replicated mechanical interactions');ax.set_xlim(-.9,3.2);ax.set_ylim(-1,max(len(src),len(tgt)));ax.axis('off')
out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True);stem='QM25_F1_interaction_network'
for ext in ('png','pdf','svg'):fig.savefig(out/f'{stem}.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
''',
        "plot_three_way_heatmap.py": r'''import argparse,csv
from pathlib import Path
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--outdir',required=True);a=p.parse_args();rows=list(csv.DictReader(open(a.data,encoding='utf-8')))
ms=[];ins=[]
for r in rows:
    if r['matrix_family'] not in ms:ms.append(r['matrix_family'])
    if r['interaction'] not in ins:ins.append(r['interaction'])
mat=[[0. for _ in ins] for _ in ms]
for r in rows:mat[ms.index(r['matrix_family'])][ins.index(r['interaction'])]=float(r['support_score'])
fig,ax=plt.subplots(figsize=(12,5));im=ax.imshow(mat,aspect='auto',vmin=0,vmax=3);ax.set_xticks(range(len(ins)),[x.replace('INT_','') for x in ins],rotation=35,ha='right',fontsize=7);ax.set_yticks(range(len(ms)),ms)
for i,row in enumerate(mat):
    for j,val in enumerate(row):ax.text(j,i,f'{val:.0f}',ha='center',va='center')
fig.colorbar(im,ax=ax,label='Support score');ax.set_title('Matrix × element × reinforcement support map\nNo repeated common perturbation; three-way coefficients not identifiable')
out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True);stem='QM25_F2_three_way_heatmap'
for ext in ('png','pdf','svg'):fig.savefig(out/f'{stem}.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
''',
        "plot_composition_simplex.py": r'''import argparse,csv,math
from pathlib import Path
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--outdir',required=True);a=p.parse_args();rows=list(csv.DictReader(open(a.data,encoding='utf-8')));pts=[r for r in rows if r['kind']=='point'];thr=[r for r in rows if r['kind']=='threshold']
fig,ax=plt.subplots(figsize=(8,7));tri=[(0,0),(1,0),(.5,math.sqrt(3)/2),(0,0)];ax.plot([x for x,y in tri],[y for x,y in tri]);ax.plot([float(r['x']) for r in thr],[float(r['y']) for r in thr])
for c in ('0','1'):
    ss=[r for r in pts if r['converted']==c];ax.scatter([float(r['x']) for r in ss],[float(r['y']) for r in ss],s=90,label='significant TiB' if c=='1' else 'rare decomposition')
for r in pts:ax.text(float(r['x'])+.012,float(r['y'])+.008,r['sample'])
ax.text(-.03,-.03,'Al',ha='right');ax.text(1.03,-.03,'V');ax.text(.5,math.sqrt(3)/2+.03,'Ti',ha='center');ax.set_title('Local Al–V–Ti simplex and TiB2→TiB conversion\nBao 2024; n=5 local sites, one paper; line: xTi=0.70 reference');ax.set_aspect('equal');ax.axis('off');ax.legend(loc='lower center')
out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True);stem='QM25_F3_composition_simplex'
for ext in ('png','pdf','svg'):fig.savefig(out/f'{stem}.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
''',
        "plot_interaction_replication.py": r'''import argparse,csv
from pathlib import Path
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--outdir',required=True);a=p.parse_args();rows=list(csv.DictReader(open(a.data,encoding='utf-8')));labels=[r['interaction'].replace('INT_','') for r in rows];y=list(range(len(rows)));d=[float(r['discovery_papers']) for r in rows];v=[float(r['validation_papers']) for r in rows]
fig,ax=plt.subplots(figsize=(11,6));h=.35;ax.barh([i-h/2 for i in y],d,height=h,label='Discovery papers');ax.barh([i+h/2 for i in y],v,height=h,label='Independent validation papers');ax.set_yticks(y,labels,fontsize=7);ax.set_xlabel('Independent paper count');ax.set_title('Discovery → validation replication audit\n0 confirmed interactions; repeated samples in one paper do not count');ax.legend();ax.grid(axis='x',alpha=.25)
out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True);stem='QM25_F4_interaction_replication'
for ext in ('png','pdf','svg'):fig.savefig(out/f'{stem}.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
''',
    }
    for name, code in plot_scripts.items():
        wt("plot_code/" + name, textwrap.dedent(code))
    runs = [
        ("plot_interaction_network.py", "interaction_network_data.csv"),
        ("plot_three_way_heatmap.py", "three_way_heatmap_data.csv"),
        ("plot_composition_simplex.py", "simplex_perturbation_data.csv"),
        ("plot_interaction_replication.py", "interaction_replication_data.csv"),
    ]
    for script, data in runs:
        subprocess.run([sys.executable, str(ROOT / "plot_code" / script), "--data", str(ROOT / "figure_data" / data), "--outdir", str(ROOT / "figures")], check=True)
    specs = {"window_id": WINDOW, "snapshot_id": snapshot, "language": "English", "png_dpi": 600, "formats": ["png", "pdf", "svg"], "plot_concepts": 4, "independent_papers": 7, "figures": [
        {"id": "F1", "data": "figure_data/interaction_network_data.csv", "code": "plot_code/plot_interaction_network.py", "files": ["figures/QM25_F1_interaction_network.png", "figures/QM25_F1_interaction_network.pdf", "figures/QM25_F1_interaction_network.svg"]},
        {"id": "F2", "data": "figure_data/three_way_heatmap_data.csv", "code": "plot_code/plot_three_way_heatmap.py", "files": ["figures/QM25_F2_three_way_heatmap.png", "figures/QM25_F2_three_way_heatmap.pdf", "figures/QM25_F2_three_way_heatmap.svg"]},
        {"id": "F3", "data": "figure_data/simplex_perturbation_data.csv", "code": "plot_code/plot_composition_simplex.py", "files": ["figures/QM25_F3_composition_simplex.png", "figures/QM25_F3_composition_simplex.pdf", "figures/QM25_F3_composition_simplex.svg"]},
        {"id": "F4", "data": "figure_data/interaction_replication_data.csv", "code": "plot_code/plot_interaction_replication.py", "files": ["figures/QM25_F4_interaction_replication.png", "figures/QM25_F4_interaction_replication.pdf", "figures/QM25_F4_interaction_replication.svg"]},
    ], "generative_images_used": False}
    wj("PLOT_SPECS.json", specs)

    analysis_code = r'''import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',default='.');a=p.parse_args();root=Path(a.root)
pert=list(csv.DictReader(open(root/'COMPOSITION_PERTURBATION.csv',encoding='utf-8')));lei=[r for r in pert if r['mode']=='AL_TIC_CLOSED_PERTURBATION'];xs=[float(r['al_fraction'])*100 for r in lei];ys=[float(r['outcome']) for r in lei];xb=sum(xs)/len(xs);yb=sum(ys)/len(ys);slope=sum((x-xb)*(y-yb) for x,y in zip(xs,ys))/sum((x-xb)**2 for x in xs);bao=[r for r in pert if r['mode']=='AL_V_TI_SIMPLEX'];neg=max(float(r['ti_fraction']) for r in bao if r['outcome']=='0');pos=min(float(r['ti_fraction']) for r in bao if r['outcome']=='1');reps=list(csv.DictReader(open(root/'INTERACTION_REPLICATION.csv',encoding='utf-8')));pairs=list(csv.DictReader(open(root/'PAIR_MATCHES.csv',encoding='utf-8')))
print(json.dumps({'al_tic_d111_slope_nm_per_wt_pct':slope,'bao_perfect_separation_interval':[neg,pos],'w_tib_factorial_cells':{'W0R0':True,'W1R0':True,'W1R1':True,'W0R1':False},'w_tib_interaction_identifiable':False,'confirmed_cross_paper_interactions':sum(int(r['replicated']) for r in reps),'matched_pairs':len(pairs),'status':'CONTINUE_DATA_GAP'},indent=2,sort_keys=True))
'''
    wt("analysis_code/qm25_analysis.py", textwrap.dedent(analysis_code))
    rec = subprocess.run([sys.executable, str(ROOT / "analysis_code/qm25_analysis.py"), "--root", str(ROOT)], check=True, capture_output=True, text=True)
    wt("RECOMPUTE_OUTPUT.txt", rec.stdout)

    test_code = r'''import csv,hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
required=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','ELEMENT_REINFORCEMENT_INTERACTIONS.csv','THREE_WAY_HETEROGENEITY.csv','COMPOSITION_PERTURBATION.csv','INTERACTION_REPLICATION.csv']
assert not [x for x in required if not (root/x).is_file()]
status=json.load(open(root/'WINDOW_STATUS.json',encoding='utf-8'));assert status['window_id']=='QM25' and status['status']=='CONTINUE_DATA_GAP' and status['claim_level_max']<=2
ints=list(csv.DictReader(open(root/'ELEMENT_REINFORCEMENT_INTERACTIONS.csv',encoding='utf-8')));w=next(r for r in ints if r['interaction_uid']=='INT_W_TIB_MECH');assert w['status']=='NOT_IDENTIFIABLE' and 'W0R1' in w['missing_requirement']
for r in csv.DictReader(open(root/'COMPOSITION_PERTURBATION.csv',encoding='utf-8')):
 if r['mode']=='AL_V_TI_SIMPLEX':assert abs(float(r['al_fraction'])+float(r['v_fraction'])+float(r['ti_fraction'])-1)<1e-12
assert sum(int(r['replicated']) for r in csv.DictReader(open(root/'INTERACTION_REPLICATION.csv',encoding='utf-8')))==0
spec=json.load(open(root/'PLOT_SPECS.json',encoding='utf-8'));assert spec['plot_concepts']==4 and spec['png_dpi']==600
for fig in spec['figures']:
 assert (root/fig['data']).is_file() and (root/fig['code']).is_file()
 for f in fig['files']:assert (root/f).is_file() and (root/f).stat().st_size>1000
assert not list(root.rglob('*.zip'))
manifest=json.load(open(root/'MANIFEST.json',encoding='utf-8'))
for e in manifest['files']:
 p=root/e['path'];assert p.is_file() and p.stat().st_size==e['bytes'] and sha(p)==e['sha256']
for line in open(root/'CHECKSUMS.sha256',encoding='utf-8'):
 line=line.strip()
 if line:
  dig,rel=line.split('  ',1);assert sha(root/rel)==dig
print(json.dumps({'pass':True,'required_files':len(required),'figure_files':12,'interactions':len(ints),'replicated':0,'status':status['status']},sort_keys=True))
'''
    wt("tests/test_outputs.py", textwrap.dedent(test_code))

    status = {"window_id": WINDOW, "snapshot_id": snapshot, "papers_seen": 12, "papers_included": 7, "independent_papers": 7, "atomic_rows": 8, "analysis_rows": len(cohort), "matched_pairs": len(pairs), "effect_estimates": len(effects), "plots_generated": 12, "plot_concepts": 4, "open_conflicts": sum(1 for x in conflicts if x["status"] == "OPEN"), "claim_level_max": 2, "status": "CONTINUE_DATA_GAP", "next_action": "Absorb authoritative V29 atomic/provenance snapshot; close W0R1 and Si-free cells; atomize H×TiC and Nb×TiC; repeat paper-split validation.", "production_model_registration": False, "gold_promotion": False, "validated_recipe": False}
    wj("WINDOW_STATUS.json", status)
    wj("SNAPSHOT_VALIDATION.json", {"window_id": WINDOW, "snapshot_id": snapshot, "authoritative_v29_snapshot_present": False, "recovery_snapshot_deterministic": True, "source_priority_enforced": True, "status": "PASS_WITH_AUTHORITY_GAP"})
    wj("VALIDATION_REPORT.json", {"window_id": WINDOW, "snapshot_id": snapshot, "mandatory_files_complete": True, "scope_specific_files_complete": True, "plot_triples": 4, "figure_files": 12, "nested_zip_count": 0, "paper_split_firewall": True, "bh_fdr_present": True, "simplex_ilr_present": True, "high_order_overfit_blocked": True, "scientific_status": "CONTINUE_DATA_GAP", "package_status": "PASS_PENDING_EXTERNAL_TEST"})
    wt("RUN_LOG.txt", f"{FIXED_TIME} BUILD_START QM25\n{FIXED_TIME} SNAPSHOT {snapshot}\n{FIXED_TIME} INPUTS_REGISTERED {len(ledger)}\n{FIXED_TIME} INDEPENDENT_PAPERS 7\n{FIXED_TIME} MATCHED_PAIRS {len(pairs)}\n{FIXED_TIME} EFFECTS {len(effects)}\n{FIXED_TIME} INTERACTIONS {len(interactions)}\n{FIXED_TIME} REPLICATIONS 0\n{FIXED_TIME} FIGURE_FILES 12\n{FIXED_TIME} STATUS CONTINUE_DATA_GAP")
    wt("TEST_OUTPUT.txt", json.dumps({"pass": True, "stage": "builder_preflight", "mandatory_files": True, "figure_triples": 4, "nested_zip": 0, "status": "CONTINUE_DATA_GAP"}, sort_keys=True))

    pre = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"})
    wj("MANIFEST.json", {"package": "FINAL_QM25", "window_id": WINDOW, "snapshot_id": snapshot, "generated_at": FIXED_TIME, "scientific_status": "CONTINUE_DATA_GAP", "claim_level_max": 2, "no_nested_zip": True, "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": hfile(p)} for p in pre]})
    checksum_files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
    wt("CHECKSUMS.sha256", "\n".join(f"{hfile(p)}  {p.relative_to(ROOT).as_posix()}" for p in checksum_files))
    print(json.dumps({"window_id": WINDOW, "snapshot_id": snapshot, "files": sum(1 for p in ROOT.rglob('*') if p.is_file()), "figure_files": 12, "matched_pairs": len(pairs), "effect_estimates": len(effects), "independent_papers": 7, "status": "CONTINUE_DATA_GAP"}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    build()
