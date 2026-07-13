#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import textwrap
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

WINDOW_ID = "QM34"
PACKAGE_VERSION = "1.0.0"
BUILD_UTC = datetime.now(timezone.utc).isoformat()
STATUS_LINE = (
    "STATUS: CONTINUE_DATA_GAP | WINDOW=QM34 | "
    "MISSING=authoritative_V29_atomic_provenance_bundle,cross_method_same_sample_calibration,thermal_relaxation_time_series | "
    "NEXT=LOCAL_ABSORB_AND_PROTOCOL_AUDIT"
)

MANDATORY_FILES = [
    "00_EXECUTIVE_VERDICT.md", "INPUT_LEDGER.csv", "ANALYSIS_COHORT.csv",
    "PAIR_MATCHES.csv", "EFFECT_ESTIMATES.csv", "HIERARCHICAL_RESULTS.csv",
    "DOSE_RESPONSE.csv", "INTERACTION_EFFECTS.csv", "HETEROGENEITY.csv",
    "SENSITIVITY_ANALYSIS.csv", "NULL_NEGATIVE_RESULTS.csv", "CONFLICT_LEDGER.csv",
    "PROVENANCE.jsonl", "METHODS.md", "LIMITATIONS.md", "PLOT_SPECS.json",
    "WEB_TO_LOCAL_REQUEST.json", "LOCAL_ABSORPTION_PROMPT.md", "WINDOW_STATUS.json",
    "MANIFEST.json", "CHECKSUMS.sha256", "CTE_GND_INPUTS.csv",
    "DISLOCATION_DENSITY_CALIBRATION.csv", "DISLOCATION_CONTRIBUTIONS.csv",
    "GND_APPLICABILITY.csv"
]

INPUT_ARCHIVES = [
    ("00_统一上传总控与校验信息_20260712.zip", "0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f", "FULL_FILE_SHA256", 25479, 13, "P1_PROVENANCED_STRUCTURED"),
    ("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip", "bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1", "FULL_FILE_SHA256", 510259317, 32, "P3_PLATFORM_CODE"),
    ("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip", "36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9", "FULL_FILE_SHA256", 515903028, 15, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip", "5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59", "FULL_FILE_SHA256", 515906034, 25, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip", "cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a", "FULL_FILE_SHA256", 515901682, 7, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip", "97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809", "ZIP_CENTRAL_DIRECTORY_SHA256", 515901786, 7, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip", "16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f", "ZIP_CENTRAL_DIRECTORY_SHA256", 515902128, 9, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip", "04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9", "ZIP_CENTRAL_DIRECTORY_SHA256", 515903238, 11, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip", "5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728", "ZIP_CENTRAL_DIRECTORY_SHA256", 515905052, 17, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip", "e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847", "ZIP_CENTRAL_DIRECTORY_SHA256", 515913392, 38, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip", "36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485", "ZIP_CENTRAL_DIRECTORY_SHA256", 515924832, 69, "P2_EXECUTABLE_ARTIFACT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip", "9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd", "ZIP_CENTRAL_DIRECTORY_SHA256", 515989228, 246, "P2_EXECUTABLE_ARTIFACT"),
    ("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip", "c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c", "ZIP_CENTRAL_DIRECTORY_SHA256", 506137803, 57191, "P3_PLATFORM_CODE"),
    ("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip", "a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a", "ZIP_CENTRAL_DIRECTORY_SHA256", 515999572, 244, "P3_PLATFORM_CODE"),
    ("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip", "bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43", "ZIP_CENTRAL_DIRECTORY_SHA256", 516062924, 396, "P3_PLATFORM_CODE"),
    ("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip", "08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755", "ZIP_CENTRAL_DIRECTORY_SHA256", 516106394, 499, "P3_PLATFORM_CODE"),
    ("TITMC_V27_LIT_WEB_P001_OF_010.zip", "42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0", "ZIP_CENTRAL_DIRECTORY_SHA256", 499460308, 15, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P002_OF_010.zip", "05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193", "ZIP_CENTRAL_DIRECTORY_SHA256", 490572377, 154, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P003_OF_010.zip", "535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917", "ZIP_CENTRAL_DIRECTORY_SHA256", 490379244, 4610, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P004_OF_010.zip", "bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a", "ZIP_CENTRAL_DIRECTORY_SHA256", 490620829, 7747, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P005_OF_010.zip", "1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1", "ZIP_CENTRAL_DIRECTORY_SHA256", 490762545, 10068, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P006_OF_010.zip", "5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13", "ZIP_CENTRAL_DIRECTORY_SHA256", 490902802, 11778, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P007_OF_010.zip", "4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1", "ZIP_CENTRAL_DIRECTORY_SHA256", 491018449, 13499, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P008_OF_010.zip", "478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341", "ZIP_CENTRAL_DIRECTORY_SHA256", 491203652, 15702, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P009_OF_010.zip", "b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a", "ZIP_CENTRAL_DIRECTORY_SHA256", 491501617, 20036, "P0_PRIMARY_ORIGINAL"),
    ("TITMC_V27_LIT_WEB_P010_OF_010.zip", "faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d", "ZIP_CENTRAL_DIRECTORY_SHA256", 367381900, 57717, "P0_PRIMARY_ORIGINAL"),
]

PAPERS = [
    {
        "paper_uid": "P_BAO_2024_10_1080_17452759_2024_2383287",
        "short": "Bao 2024", "year": 2024,
        "doi": "10.1080/17452759.2024.2383287",
        "title": "Wire-arc additive manufacturing of TiB/Ti6Al4V composites using Ti-TiB2 cored wire",
        "included": "YES", "role": "PRIMARY_MATCHED_CTE_GND_ANCHOR",
        "source_locator": "project literature corpus; DOI-bound primary source evidence capture",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
    {
        "paper_uid": "P_QIAO_2025_10_1007_S42114_025_01557_X",
        "short": "Qiao 2025", "year": 2025,
        "doi": "10.1007/s42114-025-01557-x",
        "title": "Microstructure evolution and mechanical properties of high entropy alloy reinforced titanium matrix composites processed by cold spray-friction stir processing composite additive manufacturing",
        "included": "YES", "role": "PRIMARY_THEORY_BUDGET_AND_KAM_QUALITATIVE",
        "source_locator": "File Library primary PDF; DOI-bound",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
    {
        "paper_uid": "P_XU_2025_10_1016_J_JMRT_2025_11_223",
        "short": "Xu 2025", "year": 2025,
        "doi": "10.1016/j.jmrt.2025.11.223",
        "title": "Synthesis of carbon fiber reinforced titanium matrix composites by using microwave pressureless sintering",
        "included": "YES", "role": "PRIMARY_KAM_DENSITY_RED_TEAM",
        "source_locator": "File Library primary PDF; DOI-bound",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
    {
        "paper_uid": "P_LI_2026_JMST_242_290_305",
        "short": "Li 2026", "year": 2026,
        "doi": "", "title": "Enhancing strength-ductility synergy of TiBw/Ti55 composites by introducing bimodal grain structure",
        "included": "YES", "role": "PRIMARY_PROCESS_GND_COUNTERATTRIBUTION",
        "source_locator": "project literature evidence capture; Journal of Materials Science & Technology 242 (2026) 290-305",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
    {
        "paper_uid": "P_JIAO_2019_POWDER_TECH_356_980_989",
        "short": "Jiao 2019", "year": 2019,
        "doi": "", "title": "Two-scale Ti5Si3/TiBw reinforced Ti6Al4V composite",
        "included": "YES", "role": "PRIMARY_MATCHED_NULL_COUNTEREXAMPLE",
        "source_locator": "project literature evidence capture; Powder Technology 356 (2019) 980-989",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
    {
        "paper_uid": "P_MUNIR_2018_10_1016_J_MTLA_2018_08_015",
        "short": "Munir 2018", "year": 2018,
        "doi": "10.1016/j.mtla.2018.08.015",
        "title": "Interdependencies between graphitization of carbon nanotubes and strengthening mechanisms in titanium matrix composites",
        "included": "YES", "role": "PRIMARY_THERMAL_MISMATCH_BUDGET_RED_TEAM",
        "source_locator": "File Library primary PDF; DOI-bound",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
    {
        "paper_uid": "P_MATERIALS_2026_10_3390_MA19010035",
        "short": "Materials 2026", "year": 2026,
        "doi": "10.3390/ma19010035", "title": "TiB/Ti55531 modeling study",
        "included": "NO", "role": "METHOD_PRIOR_ONLY",
        "source_locator": "project literature evidence capture",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
    {
        "paper_uid": "P_GENERIC_REVIEW_CTE_FORMULA",
        "short": "Review formula", "year": None, "doi": "",
        "title": "Generic thermal-mismatch GND formula prior",
        "included": "NO", "role": "DATABASE_PRIOR_ONLY",
        "source_locator": "project review evidence; OCR/unit conflict",
        "source_hash": "", "hash_status": "NOT_APPLICABLE",
    },
    {
        "paper_uid": "P_HREBSD_TIWFE_2026",
        "short": "HR-EBSD Ti-W-Fe", "year": 2026, "doi": "",
        "title": "HR-EBSD dislocation-density study in Ti-W-Fe alloy",
        "included": "NO", "role": "OUT_OF_SCOPE_METHOD_WARNING",
        "source_locator": "project literature evidence capture",
        "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
    },
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, obj: Any) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def normalize_value(v: Any) -> Any:
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return ""
    if v is None:
        return ""
    return v


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    ensure_dir(path.parent)
    if fieldnames is None:
        fieldnames = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: normalize_value(row.get(k, "")) for k in fieldnames})


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_uid(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(x) for x in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def taylor_stress_mpa(rho_m2: float, prefactor: float, g_pa: float, b_m: float) -> float:
    return prefactor * g_pa * b_m * math.sqrt(max(rho_m2, 0.0)) / 1e6


def rho_from_stress(delta_sigma_mpa: float, prefactor: float, g_pa: float, b_m: float) -> float:
    return (delta_sigma_mpa * 1e6 / (prefactor * g_pa * b_m)) ** 2


def rho_cte(delta_alpha: float, delta_t: float, v: float, b_m: float, d_m: float) -> float:
    return 12.0 * delta_alpha * delta_t * v / (b_m * d_m * (1.0 - v))


def rho_em(epsilon_mismatch: float, v: float, b_m: float, d_m: float) -> float:
    return 8.0 * epsilon_mismatch * v / (b_m * d_m)


def sequential_cte_increment_mpa(rho_cte_m2: float, rho_other_m2: float, prefactor: float, g_pa: float, b_m: float) -> float:
    total = taylor_stress_mpa(rho_cte_m2 + rho_other_m2, prefactor, g_pa, b_m)
    background = taylor_stress_mpa(rho_other_m2, prefactor, g_pa, b_m)
    return total - background


def save_figure(fig: plt.Figure, stem: Path) -> None:
    ensure_dir(stem.parent)
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def build_input_ledger(snapshot_id: str) -> list[dict[str, Any]]:
    rows = []
    for i, (name, digest, hash_kind, size, members, priority) in enumerate(INPUT_ARCHIVES):
        relevance = (
            "primary literature corpus: inventory-bound and relevance screened"
            if name.startswith("TITMC_V27_LIT_WEB")
            else "frozen data/features, harness, provenance, plotting, or staging infrastructure"
        )
        rows.append({
            "index": i,
            "input_id": stable_uid("IN", name, digest),
            "snapshot_id": snapshot_id,
            "source_name": name,
            "source_type": "ZIP",
            "path_or_locator": f"/mnt/data/{name}",
            "source_hash": digest,
            "source_hash_kind": hash_kind,
            "bytes": size,
            "member_count": members,
            "central_directory_status": "READABLE_IN_RECOVERED_PROJECT_LEDGER",
            "priority": priority,
            "window_relevance": relevance,
            "terminal_use_status": "INVENTORIED_AND_SCOPE_FILTERED",
            "opened_or_consumed": "BOUND_VIA_RECOVERED_PROJECT_LEDGER",
            "current_window_direct_byte_open": "NO",
            "notes": "Hash/member metadata are recovered from the project-level integrity ledger. Current runtime could not reopen multi-GB ZIP bytes; no false direct-open claim is made.",
        })
    return rows


def make_data(snapshot_id: str) -> dict[str, list[dict[str, Any]]]:
    G_TI = 45.6e9
    B_BAO = 0.29e-9
    C_BAO = 0.6
    BAO_DA = 1.0e-7
    BAO_DT = 1500.0
    BAO_EPS = 0.0002

    bao_rows: list[dict[str, Any]] = []
    for sample, v, ds_gnd, dy in [("S1_2volTiB", 0.02, 10.0, 138.0), ("S2_5volTiB", 0.05, 21.0, 321.0)]:
        rho_total = rho_from_stress(ds_gnd, C_BAO, G_TI, B_BAO)
        ratio = (12 * BAO_DA * BAO_DT / (1 - v)) / (8 * BAO_EPS)
        frac_cte = ratio / (1 + ratio)
        r_cte = rho_total * frac_cte
        r_em = rho_total - r_cte
        d_back = v * (12 * BAO_DA * BAO_DT / (1 - v) + 8 * BAO_EPS) / (B_BAO * rho_total)
        ds_cte_standalone = taylor_stress_mpa(r_cte, C_BAO, G_TI, B_BAO)
        ds_em_standalone = taylor_stress_mpa(r_em, C_BAO, G_TI, B_BAO)
        ds_cte_seq = ds_gnd - ds_em_standalone
        bao_rows.append({
            "paper_uid": PAPERS[0]["paper_uid"], "paper_short": "Bao 2024",
            "sample_uid": stable_uid("S", PAPERS[0]["paper_uid"], sample), "sample_label": sample,
            "condition_uid": stable_uid("C", PAPERS[0]["paper_uid"], sample, "RT_compression_BD"),
            "matrix": "Ti6Al4V", "reinforcement": "TiB", "process": "WAAM",
            "test_mode": "compression", "temperature_c": 25, "volume_fraction": v,
            "delta_alpha_per_k": BAO_DA, "delta_t_k": BAO_DT,
            "epsilon_mismatch": BAO_EPS, "b_m": B_BAO, "g_pa": G_TI,
            "taylor_prefactor": C_BAO, "particle_size_m": "", "particle_size_status": "NOT_OPENED_DIRECTLY",
            "backsolved_d_m": d_back, "rho_cte_m2": r_cte, "rho_em_m2": r_em,
            "rho_total_m2": rho_total, "delta_sigma_cte_standalone_mpa": ds_cte_standalone,
            "delta_sigma_em_standalone_mpa": ds_em_standalone,
            "delta_sigma_cte_sequential_mpa": ds_cte_seq,
            "delta_sigma_gnd_total_mpa": ds_gnd, "observed_delta_ys_mpa": dy,
            "gnd_share_observed_pct": 100 * ds_gnd / dy,
            "cte_seq_share_observed_pct": 100 * ds_cte_seq / dy,
            "match_grade": "A", "evidence_grade": "DIRECT_TABLE_TEXT+DERIVED_CALCULATION",
            "claim_level": 2,
            "notes": "Source total GND term includes CTE and elastic-mismatch densities. CTE sequential increment is order-dependent and reported only to prevent linear double counting.",
        })

    Q_UID = PAPERS[1]["paper_uid"]
    Q_V = 0.072
    Q_D = 1.3e-6
    Q_B = 0.347e-9
    Q_G = 45.6e9
    Q_C = 1.25
    Q_EPS = 0.0075
    Q_DA = 7.8e-6
    q_rho_em = rho_em(Q_EPS, Q_V, Q_B, Q_D)
    q_rho_total_source = 27.3e12
    q_rho_cte_source = q_rho_total_source - q_rho_em
    q_dt_back = q_rho_cte_source * Q_B * Q_D * (1 - Q_V) / (12 * Q_DA * Q_V)
    q_scenarios = []
    for label, dt, evidence in [
        ("SOURCE_BACKSOLVED", q_dt_back, "SOURCE_CALCULATION_AUDIT"),
        ("PHYSICAL_830C_TO_25C", 805.0, "DERIVED_SCENARIO"),
        ("FIFTY_PERCENT_EFFECTIVE_COOLING", 402.5, "DERIVED_RELAXATION_SCENARIO"),
    ]:
        r_cte = rho_cte(Q_DA, dt, Q_V, Q_B, Q_D)
        r_total = r_cte + q_rho_em
        ds_total = taylor_stress_mpa(r_total, Q_C, Q_G, Q_B)
        ds_cte_standalone = taylor_stress_mpa(r_cte, Q_C, Q_G, Q_B)
        ds_em_standalone = taylor_stress_mpa(q_rho_em, Q_C, Q_G, Q_B)
        ds_seq = ds_total - ds_em_standalone
        q_scenarios.append({
            "paper_uid": Q_UID, "paper_short": "Qiao 2025",
            "sample_uid": stable_uid("S", Q_UID, "CFAM_HEA_TA1"), "sample_label": "CFAM_HEA_TA1",
            "condition_uid": stable_uid("C", Q_UID, label), "matrix": "TA1",
            "reinforcement": "Al0.6CoCrFeNi HEA", "process": "cold spray + FSP",
            "test_mode": "tension", "temperature_c": 25, "volume_fraction": Q_V,
            "delta_alpha_per_k": Q_DA, "delta_t_k": dt, "epsilon_mismatch": Q_EPS,
            "b_m": Q_B, "g_pa": Q_G, "taylor_prefactor": Q_C, "particle_size_m": Q_D,
            "particle_size_status": "DIRECT_TEXT_AVERAGE_AFTER_CFAM", "backsolved_d_m": "",
            "rho_cte_m2": r_cte, "rho_em_m2": q_rho_em, "rho_total_m2": r_total,
            "delta_sigma_cte_standalone_mpa": ds_cte_standalone,
            "delta_sigma_em_standalone_mpa": ds_em_standalone,
            "delta_sigma_cte_sequential_mpa": ds_seq,
            "delta_sigma_gnd_total_mpa": ds_total, "observed_delta_ys_mpa": "",
            "composite_ys_mpa": 737.0, "gnd_share_composite_ys_pct": 100 * ds_total / 737.0,
            "cte_seq_share_composite_ys_pct": 100 * ds_seq / 737.0,
            "match_grade": "E", "evidence_grade": evidence,
            "claim_level": 1 if label != "SOURCE_BACKSOLVED" else 2,
            "notes": "No unreinforced same-condition YS control. Source text labels 9.6 and 27.3 as MPa, but dimensional reconstruction shows densities in 1e12 m^-2. Backsolved source ΔT is audited against the measured 830°C peak.",
        })

    pair_matches: list[dict[str, Any]] = []
    for b in bao_rows:
        pair_matches.append({
            "pair_uid": stable_uid("PAIR", b["sample_uid"], "matrix"), "snapshot_id": snapshot_id,
            "paper_uid": b["paper_uid"], "paper_short": b["paper_short"],
            "control_sample_uid": stable_uid("S", b["paper_uid"], "S0_matrix"),
            "treatment_sample_uid": b["sample_uid"], "condition_uid": b["condition_uid"],
            "property": "compressive_yield_strength", "unit": "MPa",
            "control_value": "", "treatment_value": "", "delta_y": b["observed_delta_ys_mpa"],
            "lnRR": "", "percent_change": "", "match_grade": "A",
            "analysis_eligible": "YES", "evidence_grade": "DIRECT_TABLE_TEXT",
            "notes": "Source provides matched ΔYS and mechanism budget; absolute pair values were not reconstructed without the primary table bytes.",
        })

    # Jiao matched null counterexample.
    J_UID = PAPERS[4]["paper_uid"]
    pair_matches.append({
        "pair_uid": stable_uid("PAIR", J_UID, "TiBw_3.4vol"), "snapshot_id": snapshot_id,
        "paper_uid": J_UID, "paper_short": "Jiao 2019",
        "control_sample_uid": stable_uid("S", J_UID, "Ti6Al4V"),
        "treatment_sample_uid": stable_uid("S", J_UID, "3.4volTiBw"),
        "condition_uid": stable_uid("C", J_UID, "RT_tension_same_sintering"),
        "property": "yield_strength", "unit": "MPa", "control_value": 770.0,
        "treatment_value": 930.0, "delta_y": 160.0,
        "lnRR": math.log(930.0 / 770.0), "percent_change": 100 * (930.0 / 770.0 - 1),
        "match_grade": "A", "analysis_eligible": "YES", "evidence_grade": "DIRECT_TABLE_TEXT",
        "notes": "Source states thermal-mismatch dislocation strengthening is negligible because Ti6Al4V, TiB and Ti5Si3 CTE values are close; no numeric zero is imputed.",
    })

    # Munir matched matrix/composite rows.
    M_UID = PAPERS[5]["paper_uid"]
    munir_cases = [
        ("B1_0.5wt", 0.0086, 822.0, 159.0), ("B2_0.5wt", 0.0086, 782.0, 159.0),
        ("B3_0.5wt", 0.0086, 920.0, 159.0), ("B1_1.0wt", 0.0172, 800.0, 225.0),
        ("B2_1.0wt", 0.0172, 610.0, 225.0), ("B3_1.0wt", 0.0172, 860.0, 225.0),
    ]
    munir_rows = []
    for label, v, ys, thermal in munir_cases:
        delta = ys - 695.0
        pair_matches.append({
            "pair_uid": stable_uid("PAIR", M_UID, label), "snapshot_id": snapshot_id,
            "paper_uid": M_UID, "paper_short": "Munir 2018",
            "control_sample_uid": stable_uid("S", M_UID, "CP_Ti"),
            "treatment_sample_uid": stable_uid("S", M_UID, label),
            "condition_uid": stable_uid("C", M_UID, label, "RT_compression"),
            "property": "compressive_yield_strength", "unit": "MPa",
            "control_value": 695.0, "treatment_value": ys, "delta_y": delta,
            "lnRR": math.log(ys / 695.0), "percent_change": 100 * (ys / 695.0 - 1),
            "match_grade": "A", "analysis_eligible": "YES", "evidence_grade": "DIRECT_TABLE_TEXT",
            "notes": "Same matrix and sintering control. Batch changes CNT dispersion, TiC fraction, porosity and graphitization; thermal mismatch is a source-calculated budget term, not an isolated causal effect.",
        })
        munir_rows.append({
            "paper_uid": M_UID, "paper_short": "Munir 2018", "sample_label": label,
            "sample_uid": stable_uid("S", M_UID, label), "condition_uid": stable_uid("C", M_UID, label, "RT_compression"),
            "volume_fraction": v, "observed_delta_ys_mpa": delta,
            "source_thermal_mismatch_mpa": thermal,
            "share_observed_pct": 100 * thermal / delta if delta != 0 else "",
            "budget_closure_status": "OPPOSITE_SIGN" if delta < 0 else ("OVERCLOSES" if thermal > delta else "UNDER_100_PERCENT"),
            "evidence_grade": "DIRECT_TABLE_TEXT+SOURCE_CALCULATION",
        })

    # Li hot-forging process GND counter-attribution.
    L_UID = PAPERS[3]["paper_uid"]
    li_cases = [
        ("Ti55", 0.24e14, 4.16e14, 90.9, 155.0),
        ("TMC_L", 0.38e14, 4.79e14, 88.1, 165.0),
        ("TMC_H", 0.26e14, 4.95e14, 96.1, 155.0),
    ]
    li_rows = []
    for label, rho_ar, rho_hf, ds, delta_ys in li_cases:
        pair_matches.append({
            "pair_uid": stable_uid("PAIR", L_UID, label), "snapshot_id": snapshot_id,
            "paper_uid": L_UID, "paper_short": "Li 2026",
            "control_sample_uid": stable_uid("S", L_UID, label, "AR"),
            "treatment_sample_uid": stable_uid("S", L_UID, label, "HF"),
            "condition_uid": stable_uid("C", L_UID, label, "RT_tension"),
            "property": "yield_strength", "unit": "MPa", "control_value": "",
            "treatment_value": "", "delta_y": delta_ys, "lnRR": "", "percent_change": "",
            "match_grade": "A", "analysis_eligible": "YES", "evidence_grade": "FIGURE_DERIVED+DIRECT_TEXT_MECHANISM",
            "notes": "YS increment digitized to approximately ±20 MPa. GND increase is caused by hot forging/heterogeneous deformation, not by CTE mismatch.",
        })
        li_rows.append({
            "paper_uid": L_UID, "paper_short": "Li 2026", "sample_label": label,
            "sample_uid": stable_uid("S", L_UID, label, "HF"),
            "rho_ar_m2": rho_ar, "rho_hf_m2": rho_hf,
            "delta_sigma_gnd_mpa": ds, "observed_process_delta_ys_mpa": delta_ys,
            "share_observed_pct": 100 * ds / delta_ys,
            "share_low_pct": 100 * ds / (delta_ys + 20),
            "share_high_pct": 100 * ds / (delta_ys - 20),
            "origin": "HOT_FORGING_PROCESS_GND_NOT_CTE", "evidence_grade": "DIRECT_TEXT+FIGURE_DERIVED",
        })

    # Xu same-temperature performance pair, but density mismatch prevents mechanism attribution.
    X_UID = PAPERS[2]["paper_uid"]
    pair_matches.append({
        "pair_uid": stable_uid("PAIR", X_UID, "1CF_1100"), "snapshot_id": snapshot_id,
        "paper_uid": X_UID, "paper_short": "Xu 2025",
        "control_sample_uid": stable_uid("S", X_UID, "Ti_1100"),
        "treatment_sample_uid": stable_uid("S", X_UID, "1CF_1100"),
        "condition_uid": stable_uid("C", X_UID, "1100C_240min_RT_tension"),
        "property": "ultimate_tensile_strength", "unit": "MPa", "control_value": 505.0,
        "treatment_value": 648.0, "delta_y": 143.0,
        "lnRR": math.log(648.0 / 505.0), "percent_change": 100 * (648.0 / 505.0 - 1),
        "match_grade": "A", "analysis_eligible": "YES_FOR_PERFORMANCE_ONLY",
        "evidence_grade": "DIRECT_TABLE_TEXT",
        "notes": "The paper does not report a KAM-derived density for the 1CF-1100 specimen in the recovered evidence; no mechanism share is computed.",
    })

    # Qiao process comparison retained but excluded from matrix estimand.
    pair_matches.append({
        "pair_uid": stable_uid("PAIR", Q_UID, "CSAM_CFAM"), "snapshot_id": snapshot_id,
        "paper_uid": Q_UID, "paper_short": "Qiao 2025",
        "control_sample_uid": stable_uid("S", Q_UID, "CSAM"),
        "treatment_sample_uid": stable_uid("S", Q_UID, "CFAM"),
        "condition_uid": stable_uid("C", Q_UID, "RT_tension"),
        "property": "ultimate_tensile_strength", "unit": "MPa", "control_value": 196.0,
        "treatment_value": 924.0, "delta_y": 728.0,
        "lnRR": math.log(924.0 / 196.0), "percent_change": 100 * (924.0 / 196.0 - 1),
        "match_grade": "B", "analysis_eligible": "NO_FOR_MATRIX_CTE_ESTIMAND",
        "evidence_grade": "DIRECT_TABLE_TEXT",
        "notes": "CSAM versus CFAM changes densification, porosity, grain size, interface, particle size and processing strain; it is not a matrix-control contrast.",
    })

    # Analysis cohort: atomic paper × sample × condition × property rows.
    cohort: list[dict[str, Any]] = []
    def add_atom(paper_uid: str, short: str, sample: str, condition: str, prop: str, value: Any, unit: str,
                 matrix: str, reinforcement: str, process: str, test_mode: str, temperature_c: Any,
                 evidence: str, notes: str = "") -> None:
        cohort.append({
            "snapshot_id": snapshot_id, "paper_uid": paper_uid, "paper_short": short,
            "sample_uid": stable_uid("S", paper_uid, sample), "sample_label": sample,
            "condition_uid": stable_uid("C", paper_uid, condition), "condition_label": condition,
            "matrix": matrix, "reinforcement": reinforcement, "process": process,
            "heat_treatment": condition, "microstructure_state": "AS_REPORTED",
            "test_mode": test_mode, "temperature_c": temperature_c, "strain_rate_s-1": "",
            "orientation": "AS_REPORTED", "property": prop, "value": value, "unit": unit,
            "evidence_grade": evidence, "source_hash": "", "hash_status": "ORIGINAL_BYTE_HASH_REQUESTED",
            "notes": notes,
        })

    for b in bao_rows:
        add_atom(b["paper_uid"], "Bao 2024", b["sample_label"], "RT_compression_BD", "delta_yield_strength", b["observed_delta_ys_mpa"], "MPa", "Ti6Al4V", "TiB", "WAAM", "compression", 25, "DIRECT_TABLE_TEXT")
        add_atom(b["paper_uid"], "Bao 2024", b["sample_label"], "RT_compression_BD", "gnd_dislocation_density", b["rho_total_m2"], "m^-2", "Ti6Al4V", "TiB", "WAAM", "compression", 25, "DERIVED_CALCULATION")
    add_atom(Q_UID, "Qiao 2025", "CFAM", "RT_tension", "yield_strength", 737.0, "MPa", "TA1", "HEA", "CS+FSP", "tension", 25, "DIRECT_TABLE_TEXT")
    add_atom(Q_UID, "Qiao 2025", "CFAM", "RT_tension", "ultimate_tensile_strength", 924.0, "MPa", "TA1", "HEA", "CS+FSP", "tension", 25, "DIRECT_TABLE_TEXT")
    add_atom(Q_UID, "Qiao 2025", "CFAM", "theory_budget", "gnd_dislocation_density", q_rho_total_source, "m^-2", "TA1", "HEA", "CS+FSP", "none", "", "SOURCE_CALCULATION_AUDIT", "Reinterpreted as density rather than MPa.")
    xu_values = [("Ti_1100", 1100, 505.0), ("0.5CF_1100", 1100, 578.0), ("1CF_1100", 1100, 648.0), ("1.5CF_1100", 1100, 510.0), ("2CF_1100", 1100, 472.0), ("1CF_1000", 1000, 405.0), ("1CF_1150", 1150, 736.0)]
    for sample, sinter_t, uts in xu_values:
        add_atom(X_UID, "Xu 2025", sample, f"sinter_{sinter_t}C_240min_RT_tension", "ultimate_tensile_strength", uts, "MPa", "CP-Ti", "TiC/CF", "microwave pressureless sintering", "tension", 25, "DIRECT_TABLE_TEXT")
    xu_rhos = [("Ti_1100", 1100, 8.652e16), ("1CF_1000", 1000, 2.869e17), ("1CF_1150", 1150, 3.136e17)]
    for sample, sinter_t, rho in xu_rhos:
        add_atom(X_UID, "Xu 2025", sample, f"sinter_{sinter_t}C_EBSD", "kam_gnd_density", rho, "m^-2", "CP-Ti", "TiC/CF", "microwave pressureless sintering", "EBSD_KAM", "", "DIRECT_TEXT+DERIVED_KAM", "Local KAM-derived density; not a validated bulk Taylor density.")
    for l in li_rows:
        add_atom(L_UID, "Li 2026", l["sample_label"] + "_AR", "AR_EBSD", "gnd_dislocation_density", l["rho_ar_m2"], "m^-2", "Ti55", "TiBw or none", "as-received", "EBSD", "", "DIRECT_TEXT")
        add_atom(L_UID, "Li 2026", l["sample_label"] + "_HF", "HF_EBSD", "gnd_dislocation_density", l["rho_hf_m2"], "m^-2", "Ti55", "TiBw or none", "hot forging", "EBSD", "", "DIRECT_TEXT")
    add_atom(J_UID, "Jiao 2019", "Ti6Al4V", "same_sintering_RT_tension", "yield_strength", 770.0, "MPa", "Ti6Al4V", "none", "powder metallurgy", "tension", 25, "DIRECT_TABLE_TEXT")
    add_atom(J_UID, "Jiao 2019", "3.4volTiBw", "same_sintering_RT_tension", "yield_strength", 930.0, "MPa", "Ti6Al4V", "TiBw", "powder metallurgy", "tension", 25, "DIRECT_TABLE_TEXT")
    add_atom(M_UID, "Munir 2018", "CP_Ti", "1100C_vacuum_sinter_RT_compression", "compressive_yield_strength", 695.0, "MPa", "CP-Ti", "none", "vacuum sintering", "compression", 25, "DIRECT_TABLE_TEXT")
    for m in munir_rows:
        ys = 695.0 + m["observed_delta_ys_mpa"]
        add_atom(M_UID, "Munir 2018", m["sample_label"], "1100C_vacuum_sinter_RT_compression", "compressive_yield_strength", ys, "MPa", "CP-Ti", "MWCNT/TiC", "vacuum sintering", "compression", 25, "DIRECT_TABLE_TEXT")

    # Scope-specific inputs.
    cte_inputs = []
    for b in bao_rows:
        cte_inputs.append({
            "snapshot_id": snapshot_id, "formula_id": "BAO_RHO_CTE_PLUS_EM",
            "scenario": "SOURCE_RECONSTRUCTION", **b,
            "parameter_source": "Source formula/constants; rho and d partition derived from source total stress",
            "identifiability": "PARTIALLY_IDENTIFIABLE", "thermal_cycle_relaxation": "NOT_REPORTED",
        })
    for q in q_scenarios:
        cte_inputs.append({
            "snapshot_id": snapshot_id, "formula_id": "QIAO_RHO_CTE_PLUS_EM",
            "scenario": q["condition_uid"], **q,
            "parameter_source": "Source formula/constants; scenario-specific ΔT",
            "identifiability": "SCENARIO_IDENTIFIABLE_NOT_CAUSAL", "thermal_cycle_relaxation": "UNKNOWN_OR_SCENARIO",
        })
    cte_inputs.extend([
        {
            "snapshot_id": snapshot_id, "formula_id": "JIAO_QUALITATIVE_NEGLIGIBLE",
            "scenario": "SOURCE_NULL_STATEMENT", "paper_uid": J_UID, "paper_short": "Jiao 2019",
            "sample_uid": stable_uid("S", J_UID, "3.4volTiBw"), "matrix": "Ti6Al4V", "reinforcement": "TiBw/Ti5Si3",
            "delta_alpha_per_k": "", "matrix_cte_per_k": 9.5e-6, "reinforcement_cte_per_k": "7.2e-6 TiB; 7.0e-6 Ti5Si3",
            "delta_t_k": "", "volume_fraction": 0.034, "particle_size_m": "", "rho_cte_m2": "",
            "delta_sigma_gnd_total_mpa": "", "parameter_source": "Direct text CTE values and qualitative conclusion",
            "evidence_grade": "DIRECT_TEXT", "identifiability": "NOT_IDENTIFIABLE_NUMERIC",
            "thermal_cycle_relaxation": "NOT_REPORTED", "notes": "Do not encode the word negligible as an exact zero.",
        },
    ])
    for m in munir_rows:
        cte_inputs.append({
            "snapshot_id": snapshot_id, "formula_id": "MUNIR_SOURCE_THERMAL_MISMATCH_TERM",
            "scenario": "SOURCE_REPORTED_CONTRIBUTION", "paper_uid": M_UID, "paper_short": "Munir 2018",
            "sample_uid": m["sample_uid"], "matrix": "CP-Ti", "reinforcement": "MWCNT/TiC",
            "volume_fraction": m["volume_fraction"], "delta_alpha_per_k": "", "delta_t_k": "",
            "particle_size_m": "", "rho_cte_m2": "", "delta_sigma_gnd_total_mpa": m["source_thermal_mismatch_mpa"],
            "observed_delta_ys_mpa": m["observed_delta_ys_mpa"], "parameter_source": "Source strengthening budget",
            "evidence_grade": m["evidence_grade"], "identifiability": "BUDGET_RED_TEAM_ONLY",
            "thermal_cycle_relaxation": "NOT_REPORTED", "notes": "Positive source thermal term can exceed or oppose observed ΔYS; not pooled.",
        })

    # Contributions table.
    contributions = []
    for b in bao_rows:
        contributions.extend([
            {
                "snapshot_id": snapshot_id, "contribution_uid": stable_uid("EFF", b["sample_uid"], "GND_TOTAL"),
                "paper_uid": b["paper_uid"], "paper_short": b["paper_short"], "sample_uid": b["sample_uid"],
                "condition_uid": b["condition_uid"], "mechanism": "GND_TOTAL_CTE_PLUS_ELASTIC_MISMATCH",
                "rho_m2": b["rho_total_m2"], "delta_sigma_mpa": b["delta_sigma_gnd_total_mpa"],
                "denominator": "same-paper observed ΔYS", "denominator_mpa": b["observed_delta_ys_mpa"],
                "share_pct": b["gnd_share_observed_pct"], "estimand": "matched contribution share",
                "match_grade": "A", "evidence_grade": b["evidence_grade"], "claim_level": 2,
                "double_count_guard": "Do not add standalone CTE and standalone EM Taylor stresses.",
            },
            {
                "snapshot_id": snapshot_id, "contribution_uid": stable_uid("EFF", b["sample_uid"], "CTE_SEQ"),
                "paper_uid": b["paper_uid"], "paper_short": b["paper_short"], "sample_uid": b["sample_uid"],
                "condition_uid": b["condition_uid"], "mechanism": "CTE_INCREMENT_CONDITIONAL_ON_EM_BACKGROUND",
                "rho_m2": b["rho_cte_m2"], "delta_sigma_mpa": b["delta_sigma_cte_sequential_mpa"],
                "denominator": "same-paper observed ΔYS", "denominator_mpa": b["observed_delta_ys_mpa"],
                "share_pct": b["cte_seq_share_observed_pct"], "estimand": "matched sequential CTE share",
                "match_grade": "A", "evidence_grade": "DERIVED_CALCULATION", "claim_level": 2,
                "double_count_guard": "Order-dependent incremental contrast; not an additive source term.",
            },
        ])
    q_source = q_scenarios[0]
    contributions.extend([
        {
            "snapshot_id": snapshot_id, "contribution_uid": stable_uid("EFF", Q_UID, "GND_SOURCE"),
            "paper_uid": Q_UID, "paper_short": "Qiao 2025", "sample_uid": q_source["sample_uid"],
            "condition_uid": q_source["condition_uid"], "mechanism": "GND_TOTAL_CTE_PLUS_MODULUS_MISMATCH",
            "rho_m2": q_source["rho_total_m2"], "delta_sigma_mpa": q_source["delta_sigma_gnd_total_mpa"],
            "denominator": "composite YS; no matrix control", "denominator_mpa": 737.0,
            "share_pct": q_source["gnd_share_composite_ys_pct"], "estimand": "descriptive composite-strength fraction",
            "match_grade": "E", "evidence_grade": "SOURCE_CALCULATION_AUDIT", "claim_level": 1,
            "double_count_guard": "Not a matched reinforcement effect; source budget also includes Hall-Petch/load transfer/Orowan.",
        },
        {
            "snapshot_id": snapshot_id, "contribution_uid": stable_uid("EFF", Q_UID, "CTE_SEQ_SOURCE"),
            "paper_uid": Q_UID, "paper_short": "Qiao 2025", "sample_uid": q_source["sample_uid"],
            "condition_uid": q_source["condition_uid"], "mechanism": "CTE_INCREMENT_CONDITIONAL_ON_EM_BACKGROUND",
            "rho_m2": q_source["rho_cte_m2"], "delta_sigma_mpa": q_source["delta_sigma_cte_sequential_mpa"],
            "denominator": "composite YS; no matrix control", "denominator_mpa": 737.0,
            "share_pct": q_source["cte_seq_share_composite_ys_pct"], "estimand": "descriptive sequential fraction",
            "match_grade": "E", "evidence_grade": "DERIVED_CALCULATION", "claim_level": 1,
            "double_count_guard": "Source ΔT appears inconsistent with measured thermal history; scenario only.",
        },
    ])
    for l in li_rows:
        contributions.append({
            "snapshot_id": snapshot_id, "contribution_uid": stable_uid("EFF", l["sample_uid"], "PROCESS_GND"),
            "paper_uid": L_UID, "paper_short": "Li 2026", "sample_uid": l["sample_uid"],
            "condition_uid": stable_uid("C", L_UID, l["sample_label"], "HF"),
            "mechanism": "PROCESS_GND_HOT_FORGING_NOT_CTE", "rho_m2": l["rho_hf_m2"],
            "delta_sigma_mpa": l["delta_sigma_gnd_mpa"], "denominator": "hot-forging-associated ΔYS",
            "denominator_mpa": l["observed_process_delta_ys_mpa"], "share_pct": l["share_observed_pct"],
            "share_low_pct": l["share_low_pct"], "share_high_pct": l["share_high_pct"],
            "estimand": "same-material process contribution share", "match_grade": "A",
            "evidence_grade": l["evidence_grade"], "claim_level": 2,
            "double_count_guard": "Counter-attribution: cannot be relabeled as CTE mismatch.",
        })
    for m in munir_rows:
        contributions.append({
            "snapshot_id": snapshot_id, "contribution_uid": stable_uid("EFF", m["sample_uid"], "SOURCE_TMS"),
            "paper_uid": M_UID, "paper_short": "Munir 2018", "sample_uid": m["sample_uid"],
            "condition_uid": m["condition_uid"], "mechanism": "SOURCE_THERMAL_MISMATCH_TERM",
            "rho_m2": "", "delta_sigma_mpa": m["source_thermal_mismatch_mpa"],
            "denominator": "same-paper observed Δcompressive YS", "denominator_mpa": m["observed_delta_ys_mpa"],
            "share_pct": m["share_observed_pct"], "estimand": "budget closure audit",
            "match_grade": "A", "evidence_grade": m["evidence_grade"], "claim_level": 2,
            "double_count_guard": "Overclosure/opposite sign demonstrates non-independent budget terms and confounding.",
        })
    contributions.append({
        "snapshot_id": snapshot_id, "contribution_uid": stable_uid("EFF", J_UID, "NULL_CTE"),
        "paper_uid": J_UID, "paper_short": "Jiao 2019", "sample_uid": stable_uid("S", J_UID, "3.4volTiBw"),
        "condition_uid": stable_uid("C", J_UID, "same_sintering_RT_tension"),
        "mechanism": "CTE_GND_SOURCE_STATED_NEGLIGIBLE", "rho_m2": "", "delta_sigma_mpa": "",
        "denominator": "same-paper observed ΔYS", "denominator_mpa": 160.0, "share_pct": "",
        "estimand": "qualitative matched null", "match_grade": "A", "evidence_grade": "DIRECT_TEXT",
        "claim_level": 2, "double_count_guard": "No exact zero or numeric share imputed.",
    })

    # Measurement-method calibration audit.
    calibration = []
    for b in bao_rows:
        calibration.append({
            "snapshot_id": snapshot_id, "paper_uid": b["paper_uid"], "paper_short": b["paper_short"],
            "sample_uid": b["sample_uid"], "method": "CTE_PLUS_EM_THEORY_BACKCALCULATED",
            "rho_reported_m2": "", "rho_used_m2": b["rho_total_m2"],
            "taylor_prefactor": C_BAO, "g_pa": G_TI, "b_m": B_BAO,
            "implied_delta_sigma_mpa": b["delta_sigma_gnd_total_mpa"],
            "reference_strength_or_increment_mpa": b["observed_delta_ys_mpa"],
            "ratio_implied_to_reference": b["delta_sigma_gnd_total_mpa"] / b["observed_delta_ys_mpa"],
            "same_sample_cross_method": "NO", "calibration_status": "SOURCE_FORMULA_RECONSTRUCTED",
            "notes": "Density back-calculated from source Taylor stress; not a direct dislocation measurement.",
        })
    calibration.append({
        "snapshot_id": snapshot_id, "paper_uid": Q_UID, "paper_short": "Qiao 2025",
        "sample_uid": q_source["sample_uid"], "method": "CTE_PLUS_EM_THEORY_SOURCE_DENSITY",
        "rho_reported_m2": 27.3e12, "rho_used_m2": 27.3e12, "taylor_prefactor": Q_C,
        "g_pa": Q_G, "b_m": Q_B, "implied_delta_sigma_mpa": q_source["delta_sigma_gnd_total_mpa"],
        "reference_strength_or_increment_mpa": 737.0,
        "ratio_implied_to_reference": q_source["delta_sigma_gnd_total_mpa"] / 737.0,
        "same_sample_cross_method": "NO", "calibration_status": "DIMENSIONAL_UNIT_CORRECTION_REQUIRED",
        "notes": "Source text calls 9.6 and 27.3 MPa; formula and Taylor reconstruction require 10^12 m^-2 densities.",
    })
    common_c, common_g, common_b = 0.9, 45.6e9, 0.29e-9
    xu_cal = [("Ti_1100", 8.652e16, 505.0), ("1CF_1000", 2.869e17, 405.0), ("1CF_1150", 3.136e17, 736.0)]
    for label, rho, ref in xu_cal:
        implied = taylor_stress_mpa(rho, common_c, common_g, common_b)
        calibration.append({
            "snapshot_id": snapshot_id, "paper_uid": X_UID, "paper_short": "Xu 2025",
            "sample_uid": stable_uid("S", X_UID, label), "method": "EBSD_KAM_GND",
            "rho_reported_m2": rho, "rho_used_m2": rho, "taylor_prefactor": common_c,
            "g_pa": common_g, "b_m": common_b, "implied_delta_sigma_mpa": implied,
            "reference_strength_or_increment_mpa": ref, "ratio_implied_to_reference": implied / ref,
            "same_sample_cross_method": "NO", "calibration_status": "FAILS_BULK_TAYLOR_SCALE_AUDIT",
            "notes": "Common Ti constants are an audit convention, not a claim about the authors' constants. Local KAM density cannot be inserted as a homogeneous bulk density without calibration.",
        })
    for l in li_rows:
        calibration.append({
            "snapshot_id": snapshot_id, "paper_uid": L_UID, "paper_short": "Li 2026",
            "sample_uid": l["sample_uid"], "method": "EBSD_GND_DIFFERENCE",
            "rho_reported_m2": l["rho_hf_m2"], "rho_used_m2": l["rho_hf_m2"],
            "taylor_prefactor": "SOURCE_SPECIFIC", "g_pa": "SOURCE_SPECIFIC", "b_m": "SOURCE_SPECIFIC",
            "implied_delta_sigma_mpa": l["delta_sigma_gnd_mpa"],
            "reference_strength_or_increment_mpa": l["observed_process_delta_ys_mpa"],
            "ratio_implied_to_reference": l["delta_sigma_gnd_mpa"] / l["observed_process_delta_ys_mpa"],
            "same_sample_cross_method": "NO", "calibration_status": "SOURCE_DIFFERENCE_FORMULA_CONSISTENT",
            "notes": "Process GND increment, not CTE. Strength denominator is figure-derived with ±20 MPa scenario uncertainty.",
        })
    calibration.extend([
        {
            "snapshot_id": snapshot_id, "paper_uid": "", "paper_short": "Missing calibration",
            "sample_uid": "", "method": "TEM_DISLOCATION_COUNT", "rho_reported_m2": "", "rho_used_m2": "",
            "taylor_prefactor": "", "g_pa": "", "b_m": "", "implied_delta_sigma_mpa": "",
            "reference_strength_or_increment_mpa": "", "ratio_implied_to_reference": "",
            "same_sample_cross_method": "NO", "calibration_status": "NOT_IDENTIFIABLE",
            "notes": "No same-sample TEM numeric density paired with KAM/XRD in the frozen evidence.",
        },
        {
            "snapshot_id": snapshot_id, "paper_uid": "", "paper_short": "Missing calibration",
            "sample_uid": "", "method": "XRD_LINE_PROFILE", "rho_reported_m2": "", "rho_used_m2": "",
            "taylor_prefactor": "", "g_pa": "", "b_m": "", "implied_delta_sigma_mpa": "",
            "reference_strength_or_increment_mpa": "", "ratio_implied_to_reference": "",
            "same_sample_cross_method": "NO", "calibration_status": "NOT_IDENTIFIABLE",
            "notes": "No same-sample XRD line-profile density paired with KAM/TEM in the frozen evidence.",
        },
    ])

    # Effect table combines matched performance effects and mechanism terms.
    effects = []
    for p in pair_matches:
        effects.append({
            "effect_uid": stable_uid("EFF", p["pair_uid"], "DELTA"), "snapshot_id": snapshot_id,
            "paper_uid": p["paper_uid"], "paper_short": p["paper_short"], "sample_uid": p["treatment_sample_uid"],
            "condition_uid": p["condition_uid"], "estimand": "absolute paired effect ΔY",
            "outcome": p["property"], "estimate": p["delta_y"], "unit": p["unit"],
            "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "",
            "uncertainty_type": "SOURCE_OR_FIGURE_SCENARIO; NO_PSEUDO_CI", "match_grade": p["match_grade"],
            "evidence_grade": p["evidence_grade"], "claim_level": 2 if p["match_grade"] == "A" else 1,
            "analysis_eligible": p["analysis_eligible"], "notes": p["notes"],
        })
        if p.get("lnRR", "") != "":
            effects.append({
                "effect_uid": stable_uid("EFF", p["pair_uid"], "LNRR"), "snapshot_id": snapshot_id,
                "paper_uid": p["paper_uid"], "paper_short": p["paper_short"], "sample_uid": p["treatment_sample_uid"],
                "condition_uid": p["condition_uid"], "estimand": "log response ratio lnRR",
                "outcome": p["property"], "estimate": p["lnRR"], "unit": "log ratio",
                "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "",
                "uncertainty_type": "SOURCE_VALUES_ONLY", "match_grade": p["match_grade"],
                "evidence_grade": p["evidence_grade"], "claim_level": 2 if p["match_grade"] == "A" else 1,
                "analysis_eligible": p["analysis_eligible"], "notes": p["notes"],
            })
    for c in contributions:
        effects.append({
            "effect_uid": c["contribution_uid"], "snapshot_id": snapshot_id,
            "paper_uid": c["paper_uid"], "paper_short": c["paper_short"], "sample_uid": c["sample_uid"],
            "condition_uid": c["condition_uid"], "estimand": c["estimand"], "outcome": c["mechanism"],
            "estimate": c["delta_sigma_mpa"], "unit": "MPa", "ci_low": "", "ci_high": "",
            "prediction_low": c.get("share_low_pct", ""), "prediction_high": c.get("share_high_pct", ""),
            "uncertainty_type": "SCENARIO_OR_SOURCE_BUDGET", "match_grade": c["match_grade"],
            "evidence_grade": c["evidence_grade"], "claim_level": c["claim_level"],
            "analysis_eligible": "YES_WITH_CLAIM_CEILING", "notes": c["double_count_guard"],
        })

    # Dose response and interaction/sensitivity outputs.
    bao_slope = (bao_rows[1]["delta_sigma_gnd_total_mpa"] - bao_rows[0]["delta_sigma_gnd_total_mpa"]) / ((bao_rows[1]["volume_fraction"] - bao_rows[0]["volume_fraction"]) * 100)
    dose_response = [
        {
            "snapshot_id": snapshot_id, "paper_uid": PAPERS[0]["paper_uid"], "paper_short": "Bao 2024",
            "dose_definition": "actual TiB vol.%", "dose_low": 2.0, "dose_high": 5.0,
            "outcome": "source total GND strengthening", "effect_low_mpa": 10.0, "effect_high_mpa": 21.0,
            "descriptive_slope_mpa_per_volpct": bao_slope, "independent_papers": 1,
            "model_status": "DESCRIPTIVE_TWO_POINT_ONLY", "claim_level": 2,
            "notes": "Particle size and morphology also change; slope is not a universal dose coefficient.",
        },
        {
            "snapshot_id": snapshot_id, "paper_uid": M_UID, "paper_short": "Munir 2018",
            "dose_definition": "MWCNT vol.%", "dose_low": 0.86, "dose_high": 1.72,
            "outcome": "source thermal-mismatch term", "effect_low_mpa": 159.0, "effect_high_mpa": 225.0,
            "descriptive_slope_mpa_per_volpct": (225 - 159) / (1.72 - 0.86), "independent_papers": 1,
            "model_status": "BATCH_CONFOUNDED_BUDGET_RED_TEAM", "claim_level": 1,
            "notes": "Each dose spans three dispersion batches with different TiC, porosity and CNT graphitization; no causal dose fit.",
        },
        {
            "snapshot_id": snapshot_id, "paper_uid": "MULTI", "paper_short": "Cross-paper",
            "dose_definition": "reinforcement fraction", "dose_low": "", "dose_high": "",
            "outcome": "CTE/GND strengthening", "effect_low_mpa": "", "effect_high_mpa": "",
            "descriptive_slope_mpa_per_volpct": "", "independent_papers": 6,
            "model_status": "NOT_IDENTIFIABLE", "claim_level": 1,
            "notes": "Dose units, architecture, process, formula, measurement method and strength denominator are non-commensurate.",
        },
    ]

    interaction_effects = [
        {"snapshot_id": snapshot_id, "interaction": "ΔCTE × ΔT", "scale": "Taylor stress", "local_elasticity_a": 0.5, "local_elasticity_b": 0.5, "status": "FORMULA_DEFINED", "notes": "At fixed V,d,G,b,prefactor, stress is proportional to sqrt(ΔCTE·ΔT)."},
        {"snapshot_id": snapshot_id, "interaction": "V × particle size", "scale": "Taylor stress", "local_elasticity_a": "0.5/(1-V)", "local_elasticity_b": -0.5, "status": "FORMULA_DEFINED", "notes": "At fixed other inputs, stress scales as sqrt[V/(d(1−V))]."},
        {"snapshot_id": snapshot_id, "interaction": "thermal relaxation × ΔT", "scale": "Qiao scenario", "local_elasticity_a": "nonlinear", "local_elasticity_b": "nonlinear", "status": "SCENARIO_ONLY", "notes": "Reducing effective cooling from source-backsolved ~1095 K to 805 K and 402.5 K lowers total and incremental CTE terms."},
        {"snapshot_id": snapshot_id, "interaction": "measurement method × Taylor conversion", "scale": "cross-method", "local_elasticity_a": "not estimable", "local_elasticity_b": "not estimable", "status": "NOT_IDENTIFIABLE", "notes": "No same-sample KAM/TEM/XRD calibration layer."},
    ]

    # Generic sensitivity grid and summary.
    da_grid = np.linspace(0.1e-6, 8.0e-6, 51)
    dt_grid = np.linspace(300.0, 1500.0, 51)
    v0, d0, b0, g0, c0 = 0.05, 5e-6, 0.29e-9, 45.6e9, 1.25
    fig02_rows = []
    for da in da_grid:
        for dt in dt_grid:
            rho = rho_cte(float(da), float(dt), v0, b0, d0)
            ds = taylor_stress_mpa(rho, c0, g0, b0)
            fig02_rows.append({
                "delta_cte_per_k": da, "delta_cte_micro_per_k": da * 1e6,
                "delta_t_k": dt, "volume_fraction": v0, "particle_size_um": d0 * 1e6,
                "rho_cte_m2": rho, "delta_sigma_cte_standalone_mpa": ds,
                "formula": "12*Δα*ΔT*V/[b*d*(1−V)] then C*G*b*sqrt(rho)",
            })
    sensitivity = []
    for da in [0.1e-6, 1e-6, 3e-6, 8e-6]:
        for dt in [300, 800, 1500]:
            for v in [0.01, 0.05, 0.10]:
                for d_um in [0.5, 5.0, 50.0]:
                    r = rho_cte(da, dt, v, b0, d_um * 1e-6)
                    sensitivity.append({
                        "snapshot_id": snapshot_id, "analysis": "GENERIC_CTE_GND_SENSITIVITY",
                        "delta_alpha_per_k": da, "delta_t_k": dt, "volume_fraction": v,
                        "particle_size_um": d_um, "taylor_prefactor": c0, "g_pa": g0, "b_m": b0,
                        "rho_cte_m2": r, "delta_sigma_cte_standalone_mpa": taylor_stress_mpa(r, c0, g0, b0),
                        "support_status": "FORMULA_SCENARIO_NOT_MATERIAL_MEASUREMENT",
                    })
    for q in q_scenarios:
        sensitivity.append({
            "snapshot_id": snapshot_id, "analysis": "QIAO_EFFECTIVE_DELTAT_SCENARIO",
            "delta_alpha_per_k": Q_DA, "delta_t_k": q["delta_t_k"], "volume_fraction": Q_V,
            "particle_size_um": Q_D * 1e6, "taylor_prefactor": Q_C, "g_pa": Q_G, "b_m": Q_B,
            "rho_cte_m2": q["rho_cte_m2"], "delta_sigma_cte_standalone_mpa": q["delta_sigma_cte_standalone_mpa"],
            "delta_sigma_cte_sequential_mpa": q["delta_sigma_cte_sequential_mpa"],
            "delta_sigma_gnd_total_mpa": q["delta_sigma_gnd_total_mpa"],
            "support_status": q["evidence_grade"],
        })

    hierarchical = [
        {
            "snapshot_id": snapshot_id, "model_id": "QM34_CROSS_PAPER_HIERARCHICAL_CTE_GND",
            "estimand": "universal CTE/GND strengthening coefficient", "independent_papers": 6,
            "effect_rows_available": len(contributions), "fit_status": "NOT_IDENTIFIABLE",
            "estimate": "", "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "",
            "reason": "Theory-derived densities, EBSD/KAM densities, process-generated GND, source budgets, qualitative nulls and different denominators cannot be treated as exchangeable observations.",
            "claim_level": 1,
        },
        {
            "snapshot_id": snapshot_id, "model_id": "QM34_STRICT_MATCHED_CTE_SHARE",
            "estimand": "CTE-sequential share of observed matched ΔYS", "independent_papers": 1,
            "effect_rows_available": 2, "fit_status": "NOT_IDENTIFIABLE_FOR_META_ANALYSIS",
            "estimate": statistics.mean([b["cte_seq_share_observed_pct"] for b in bao_rows]),
            "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "",
            "reason": "Only Bao provides quantitative strict matched CTE+EM budget under one protocol; Jiao is qualitative-null only.",
            "claim_level": 2,
        },
    ]

    heterogeneity = [
        {
            "snapshot_id": snapshot_id, "heterogeneity_id": "H1", "estimand_family": "strict matched total GND share",
            "independent_papers": 1, "rows": 2, "min_pct": min(b["gnd_share_observed_pct"] for b in bao_rows),
            "median_pct": statistics.median(b["gnd_share_observed_pct"] for b in bao_rows),
            "max_pct": max(b["gnd_share_observed_pct"] for b in bao_rows), "I2_pct": "NOT_ESTIMABLE",
            "tau2": "NOT_ESTIMABLE", "prediction_interval": "NOT_ESTIMABLE", "notes": "Single independent paper.",
        },
        {
            "snapshot_id": snapshot_id, "heterogeneity_id": "H2", "estimand_family": "process GND share",
            "independent_papers": 1, "rows": 3, "min_pct": min(l["share_observed_pct"] for l in li_rows),
            "median_pct": statistics.median(l["share_observed_pct"] for l in li_rows),
            "max_pct": max(l["share_observed_pct"] for l in li_rows), "I2_pct": "NOT_ESTIMABLE",
            "tau2": "NOT_ESTIMABLE", "prediction_interval": "NOT_ESTIMABLE", "notes": "Hot-forging GND; not CTE.",
        },
        {
            "snapshot_id": snapshot_id, "heterogeneity_id": "H3", "estimand_family": "source thermal-mismatch budget closure",
            "independent_papers": 1, "rows": 6,
            "min_pct": min(float(m["share_observed_pct"]) for m in munir_rows),
            "median_pct": statistics.median(float(m["share_observed_pct"]) for m in munir_rows),
            "max_pct": max(float(m["share_observed_pct"]) for m in munir_rows), "I2_pct": "NOT_ESTIMABLE",
            "tau2": "NOT_ESTIMABLE", "prediction_interval": "NOT_ESTIMABLE",
            "notes": "Includes opposite-sign observed ΔYS and >100% closure; retained as red-team evidence, not pooled.",
        },
        {
            "snapshot_id": snapshot_id, "heterogeneity_id": "H4", "estimand_family": "cross-method density",
            "independent_papers": 4, "rows": len([c for c in calibration if c.get("rho_used_m2", "") != ""]),
            "min_pct": "", "median_pct": "", "max_pct": "", "I2_pct": "NOT_APPLICABLE",
            "tau2": "NOT_APPLICABLE", "prediction_interval": "NOT_APPLICABLE",
            "notes": "Method-specific densities differ by >4 orders of magnitude; measurement-scale calibration is absent.",
        },
    ]

    null_negative = [
        {
            "snapshot_id": snapshot_id, "result_uid": "NULL_JIAO_CTE", "paper_uid": J_UID,
            "sample_uid": stable_uid("S", J_UID, "3.4volTiBw"), "result_type": "QUALITATIVE_NULL",
            "observed_performance": "+160 MPa YS versus Ti6Al4V", "mechanism_result": "CTE/GND contribution stated negligible",
            "evidence_grade": "DIRECT_TEXT", "interpretation": "Large strengthening can occur with negligible CTE/GND; other mechanisms dominate.",
        },
        {
            "snapshot_id": snapshot_id, "result_uid": "NEG_MUNIR_B2_1WT", "paper_uid": M_UID,
            "sample_uid": stable_uid("S", M_UID, "B2_1.0wt"), "result_type": "OPPOSITE_SIGN_BUDGET",
            "observed_performance": "Δcompressive YS = -85 MPa", "mechanism_result": "+225 MPa source thermal-mismatch term",
            "evidence_grade": "DIRECT_TABLE_TEXT+SOURCE_CALCULATION", "interpretation": "Positive formula term does not imply net strengthening and cannot be read causally.",
        },
        {
            "snapshot_id": snapshot_id, "result_uid": "NULL_CROSS_METHOD_CAL", "paper_uid": "MULTI",
            "sample_uid": "", "result_type": "NOT_IDENTIFIABLE",
            "observed_performance": "KAM/TEM/XRD same-sample calibration absent", "mechanism_result": "No transferable conversion factor",
            "evidence_grade": "UNRESOLVED", "interpretation": "Method labels are not interchangeable dislocation-density measurements.",
        },
        {
            "snapshot_id": snapshot_id, "result_uid": "NEG_XU_KAM_BULK", "paper_uid": X_UID,
            "sample_uid": stable_uid("S", X_UID, "1CF_1150"), "result_type": "SCALE_CONTRADICTION",
            "observed_performance": "UTS 736 MPa", "mechanism_result": "Common-constant Taylor insertion gives multi-GPa stress",
            "evidence_grade": "DERIVED_CALCULATION", "interpretation": "Local KAM density is not a calibrated homogeneous bulk density.",
        },
    ]

    conflicts = [
        ("C01", Q_UID, "UNIT_LABEL", "Qiao text labels 9.6 and 27.3 as MPa although formula/Taylor reconstruction requires densities near 10^12 m^-2.", "OPEN_HIGH", "Treat as density; request original equation/table audit."),
        ("C02", Q_UID, "THERMAL_HISTORY", f"Qiao source density back-solves ΔT≈{q_dt_back:.1f} K versus measured 830°C peak to 25°C drop≈805 K.", "OPEN_HIGH", "Retain source and corrected/relaxed scenarios separately."),
        ("C03", Q_UID, "NON_ADDITIVE_BUDGET", "Standalone CTE and elastic-mismatch Taylor stresses are square-root terms and cannot be linearly added.", "RESOLVED_BY_METHOD", "Report total and sequential conditional increment."),
        ("C04", X_UID, "METHOD_SCALE", "Xu KAM densities imply multi-GPa Taylor stresses under common Ti constants, far above measured strength.", "OPEN_HIGH", "Require step-size/noise/Nye-tensor and same-sample calibration."),
        ("C05", PAPERS[0]["paper_uid"], "FORMULA_OCR", "Bao elastic-mismatch term is recovered as 8 ε_y V/(bd); original equation bytes should be checked.", "OPEN_MEDIUM", "Bind original PDF equation and dimensional audit locally."),
        ("C06", "MULTI", "CALIBRATION_GAP", "No same-sample KAM/TEM/XRD density calibration was recovered.", "OPEN_HIGH", "Acquire raw EBSD/TEM/XRD measurements under one sample/condition."),
        ("C07", L_UID, "ATTRIBUTION", "Li GND increase is caused by hot forging/heterogeneous deformation, not CTE mismatch.", "RESOLVED_BY_SCOPE", "Use as counter-attribution only."),
        ("C08", J_UID, "QUALITATIVE_NULL", "Jiao calls CTE/GND negligible but provides no numeric density or contribution.", "OPEN_MEDIUM", "Do not impute zero; retain qualitative null."),
        ("C09", M_UID, "BUDGET_OVERCLOSURE", "Munir source thermal-mismatch terms exceed observed ΔYS in multiple rows and remain positive when ΔYS is negative.", "OPEN_HIGH", "Treat as budget red-team evidence; do not pool."),
        ("C10", "MULTI", "DOUBLE_COUNTING", "Hall-Petch, process work hardening, HDI/back stress, residual stress and GND may share the same microstructural origin.", "OPEN_HIGH", "Require mutually exclusive estimands or joint latent-mechanism model with direct observables."),
        ("C11", "MULTI", "HIGH_TEMPERATURE_AD", "No quantitative 600–800°C CTE/GND retention or relaxation series was identified.", "OPEN_HIGH", "Acquire temperature-dependent G, recovery and thermal-cycle data."),
    ]
    conflict_rows = [
        {"conflict_id": cid, "snapshot_id": snapshot_id, "paper_uid": p, "conflict_type": typ,
         "description": desc, "status": status, "resolution_or_request": resolution}
        for cid, p, typ, desc, status, resolution in conflicts
    ]

    applicability = []
    for c in contributions:
        paper = c["paper_short"]
        measured = "YES" if "PROCESS_GND" in c["mechanism"] else "NO"
        physical_dt = "PARTIAL" if paper == "Qiao 2025" else ("SOURCE" if paper == "Bao 2024" else "NO")
        same_perf = "YES" if c["match_grade"] == "A" else "NO"
        relaxed = "NO"
        separated = "PARTIAL" if paper in {"Bao 2024", "Qiao 2025"} else "NO"
        admissible = (
            "MATCHED_SOURCE_BUDGET_WITH_CEILING" if paper == "Bao 2024"
            else "PROCESS_GND_NOT_CTE" if paper == "Li 2026"
            else "RED_TEAM_ONLY" if paper == "Munir 2018"
            else "DESCRIPTIVE_ONLY" if paper == "Qiao 2025"
            else "QUALITATIVE_NULL" if paper == "Jiao 2019"
            else "NOT_IDENTIFIABLE"
        )
        applicability.append({
            "snapshot_id": snapshot_id, "contribution_uid": c["contribution_uid"], "paper_uid": c["paper_uid"],
            "sample_uid": c["sample_uid"], "mechanism": c["mechanism"],
            "direct_dislocation_measurement": measured, "cte_inputs_bound": "YES" if paper in {"Bao 2024", "Qiao 2025"} else "NO",
            "physical_delta_t_audited": physical_dt, "particle_size_direct": "YES" if paper == "Qiao 2025" else "NO_OR_NOT_NEEDED",
            "same_sample_performance": same_perf, "thermal_cycle_relaxation_measured": relaxed,
            "separated_from_hp_work_hardening": separated, "temperature_dependent_G_used": "NO_RT_ONLY",
            "applicability_status": admissible, "claim_level_max": c["claim_level"],
        })

    # Figure datasets.
    fig01 = []
    for b in bao_rows:
        fig01.extend([
            {"paper_short": "Bao 2024", "sample_label": b["sample_label"], "method": "Theory total", "mechanism": "CTE+EM GND", "rho_m2": b["rho_total_m2"], "delta_sigma_mpa": b["delta_sigma_gnd_total_mpa"], "evidence": "source stress + reconstruction", "support_domain": "RT compression; WAAM TiB/Ti6Al4V"},
            {"paper_short": "Bao 2024", "sample_label": b["sample_label"] + " CTE", "method": "Theory component", "mechanism": "CTE standalone", "rho_m2": b["rho_cte_m2"], "delta_sigma_mpa": b["delta_sigma_cte_standalone_mpa"], "evidence": "derived partition", "support_domain": "RT compression; WAAM TiB/Ti6Al4V"},
        ])
    fig01.extend([
        {"paper_short": "Qiao 2025", "sample_label": "CFAM source", "method": "Theory total", "mechanism": "CTE+EM GND", "rho_m2": q_source["rho_total_m2"], "delta_sigma_mpa": q_source["delta_sigma_gnd_total_mpa"], "evidence": "source density audit", "support_domain": "RT tension; CFAM HEA/TA1"},
        {"paper_short": "Qiao 2025", "sample_label": "CFAM CTE", "method": "Theory component", "mechanism": "CTE standalone", "rho_m2": q_source["rho_cte_m2"], "delta_sigma_mpa": q_source["delta_sigma_cte_standalone_mpa"], "evidence": "derived partition", "support_domain": "RT tension; no matrix control"},
    ])
    for l in li_rows:
        fig01.append({"paper_short": "Li 2026", "sample_label": l["sample_label"] + " HF", "method": "EBSD GND", "mechanism": "process GND increment", "rho_m2": l["rho_hf_m2"], "delta_sigma_mpa": l["delta_sigma_gnd_mpa"], "evidence": "direct density/source Taylor difference", "support_domain": "RT tension; hot forging"})
    for label, rho, ref in xu_cal:
        fig01.append({"paper_short": "Xu 2025", "sample_label": label, "method": "EBSD KAM audit", "mechanism": "common-constant implied", "rho_m2": rho, "delta_sigma_mpa": taylor_stress_mpa(rho, common_c, common_g, common_b), "evidence": "local KAM density + audit constants", "support_domain": "RT tension; microwave sintering"})

    fig03 = [
        {
            "paper_short": c["paper_short"], "sample_label": c.get("sample_uid", ""), "method": c["method"],
            "rho_m2": c.get("rho_used_m2", ""), "implied_delta_sigma_mpa": c.get("implied_delta_sigma_mpa", ""),
            "reference_strength_or_increment_mpa": c.get("reference_strength_or_increment_mpa", ""),
            "ratio_implied_to_reference": c.get("ratio_implied_to_reference", ""),
            "calibration_status": c["calibration_status"], "same_sample_cross_method": c["same_sample_cross_method"],
        }
        for c in calibration if c.get("rho_used_m2", "") != "" and c.get("ratio_implied_to_reference", "") != ""
    ]

    fig04 = []
    for c in contributions:
        if c.get("share_pct", "") == "":
            continue
        label = f"{c['paper_short']} | {c['mechanism'][:22]} | {str(c['sample_uid'])[-6:]}"
        share = float(c["share_pct"])
        low = float(c.get("share_low_pct", share) or share)
        high = float(c.get("share_high_pct", share) or share)
        fig04.append({
            "label": label, "paper_short": c["paper_short"], "mechanism": c["mechanism"],
            "share_pct": share, "share_low_pct": min(low, high), "share_high_pct": max(low, high),
            "denominator": c["denominator"], "match_grade": c["match_grade"], "evidence_grade": c["evidence_grade"],
            "support_domain": "paper-specific; no cross-family pooling",
        })

    return {
        "bao": bao_rows, "qiao": q_scenarios, "munir": munir_rows, "li": li_rows,
        "cohort": cohort, "pairs": pair_matches, "cte_inputs": cte_inputs,
        "contributions": contributions, "calibration": calibration, "effects": effects,
        "dose_response": dose_response, "interaction_effects": interaction_effects,
        "sensitivity": sensitivity, "hierarchical": hierarchical, "heterogeneity": heterogeneity,
        "null_negative": null_negative, "conflicts": conflict_rows, "applicability": applicability,
        "fig01": fig01, "fig02": fig02_rows, "fig03": fig03, "fig04": fig04,
    }


def generate_plots(root: Path, data: dict[str, list[dict[str, Any]]]) -> None:
    figures = root / "figures"
    ensure_dir(figures)

    df1 = pd.DataFrame(data["fig01"])
    fig = plt.figure(figsize=(8.5, 6.2))
    ax = fig.add_subplot(111)
    markers = ["o", "s", "^", "D", "v", "P"]
    for idx, (method, group) in enumerate(df1.groupby("method", sort=True)):
        ax.scatter(group["rho_m2"], group["delta_sigma_mpa"], marker=markers[idx % len(markers)], label=method)
    for _, row in df1.iterrows():
        ax.annotate(row["sample_label"], (row["rho_m2"], row["delta_sigma_mpa"]), fontsize=6, xytext=(3, 3), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Dislocation density used in Taylor relation, ρ (m⁻²)")
    ax.set_ylabel("Dislocation strengthening contribution, Δσ (MPa)")
    ax.set_title("ρ–Δσ distribution | 4 papers | theory and EBSD/KAM are not interchangeable")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", alpha=0.25)
    fig.text(0.01, 0.01, "Effect: paper-specific Taylor contribution; evidence: direct/source calculation/derived audit; support: RT Ti/TMC only", fontsize=7)
    save_figure(fig, figures / "fig01_rho_delta_sigma_distribution")

    df2 = pd.DataFrame(data["fig02"])
    x = np.sort(df2["delta_cte_micro_per_k"].unique())
    y = np.sort(df2["delta_t_k"].unique())
    z = df2.pivot(index="delta_t_k", columns="delta_cte_micro_per_k", values="delta_sigma_cte_standalone_mpa").loc[y, x].values
    fig = plt.figure(figsize=(8.2, 6.2))
    ax = fig.add_subplot(111)
    contour = ax.contourf(x, y, z, levels=20)
    fig.colorbar(contour, ax=ax, label="Standalone CTE Taylor term, Δσ (MPa)")
    ax.set_xlabel("CTE mismatch, ΔCTE (10⁻⁶ K⁻¹)")
    ax.set_ylabel("Cooling interval, ΔT (K)")
    ax.set_title("ΔCTE × ΔT sensitivity | V=5 vol.%, d=5 μm, Ti RT constants")
    fig.text(0.01, 0.01, "Model surface, not measurement; ρ=12ΔαΔTV/[bd(1−V)], Δσ=1.25Gb√ρ", fontsize=7)
    save_figure(fig, figures / "fig02_cte_dt_sensitivity_surface")

    df3 = pd.DataFrame(data["fig03"])
    fig = plt.figure(figsize=(8.5, 6.2))
    ax = fig.add_subplot(111)
    for idx, (method, group) in enumerate(df3.groupby("method", sort=True)):
        ax.scatter(group["rho_m2"], group["ratio_implied_to_reference"], marker=markers[idx % len(markers)], label=method)
    for _, row in df3.iterrows():
        ax.annotate(row["paper_short"], (row["rho_m2"], row["ratio_implied_to_reference"]), fontsize=6, xytext=(3, 3), textcoords="offset points")
    ax.axhline(1.0, linestyle="--", linewidth=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Reported/reconstructed density, ρ (m⁻²)")
    ax.set_ylabel("Taylor contribution / observed strength scale")
    ax.set_title("Dislocation-method calibration audit | same-sample KAM–TEM–XRD calibration unavailable")
    ax.legend(fontsize=6)
    ax.grid(True, which="both", alpha=0.25)
    fig.text(0.01, 0.01, "Ratios use paper-specific denominators; position relative to 1 is an audit, not a pooled calibration curve", fontsize=7)
    save_figure(fig, figures / "fig03_measurement_method_calibration")

    df4 = pd.DataFrame(data["fig04"]).sort_values("share_pct")
    y_pos = np.arange(len(df4))
    center = df4["share_pct"].to_numpy(float)
    lo = df4["share_low_pct"].to_numpy(float)
    hi = df4["share_high_pct"].to_numpy(float)
    xerr = np.vstack([center - lo, hi - center])
    fig = plt.figure(figsize=(10.5, max(6.5, 0.36 * len(df4) + 2.0)))
    ax = fig.add_subplot(111)
    ax.errorbar(center, y_pos, xerr=xerr, fmt="o", capsize=2)
    ax.axvline(0.0, linewidth=1)
    ax.axvline(100.0, linestyle="--", linewidth=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df4["label"], fontsize=6)
    ax.set_xlabel("Reported or reconstructed contribution share (%)")
    ax.set_title("Dislocation contribution-share forest | denominators and estimands are paper-specific")
    ax.grid(True, axis="x", alpha=0.25)
    fig.text(0.01, 0.01, "Bao: matched GND/CTE share; Qiao: fraction of composite YS; Li: hot-forging GND; Munir: budget-closure red team", fontsize=7)
    save_figure(fig, figures / "fig04_dislocation_share_forest")


def plot_script_text(fig_no: int) -> str:
    if fig_no == 1:
        body = r'''
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
df=pd.read_csv(ROOT/"figure_data/fig01_rho_delta_sigma_distribution.csv")
fig=plt.figure(figsize=(8.5,6.2)); ax=fig.add_subplot(111)
markers=["o","s","^","D","v","P"]
for i,(method,g) in enumerate(df.groupby("method",sort=True)):
    ax.scatter(g.rho_m2,g.delta_sigma_mpa,marker=markers[i%len(markers)],label=method)
for _,r in df.iterrows(): ax.annotate(r.sample_label,(r.rho_m2,r.delta_sigma_mpa),fontsize=6,xytext=(3,3),textcoords="offset points")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Dislocation density used in Taylor relation, ρ (m⁻²)"); ax.set_ylabel("Dislocation strengthening contribution, Δσ (MPa)")
ax.set_title("ρ–Δσ distribution | 4 papers | theory and EBSD/KAM are not interchangeable")
ax.legend(fontsize=7); ax.grid(True,which="both",alpha=.25)
fig.text(.01,.01,"Effect: paper-specific Taylor contribution; evidence: direct/source calculation/derived audit; support: RT Ti/TMC only",fontsize=7)
for ext in ["png","pdf","svg"]: fig.savefig(ROOT/f"figures/fig01_rho_delta_sigma_distribution.{ext}",dpi=600 if ext=="png" else None,bbox_inches="tight")
plt.close(fig)
'''
    elif fig_no == 2:
        body = r'''
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
df=pd.read_csv(ROOT/"figure_data/fig02_cte_dt_sensitivity_surface.csv")
x=np.sort(df.delta_cte_micro_per_k.unique()); y=np.sort(df.delta_t_k.unique())
z=df.pivot(index="delta_t_k",columns="delta_cte_micro_per_k",values="delta_sigma_cte_standalone_mpa").loc[y,x].values
fig=plt.figure(figsize=(8.2,6.2)); ax=fig.add_subplot(111)
c=ax.contourf(x,y,z,levels=20); fig.colorbar(c,ax=ax,label="Standalone CTE Taylor term, Δσ (MPa)")
ax.set_xlabel("CTE mismatch, ΔCTE (10⁻⁶ K⁻¹)"); ax.set_ylabel("Cooling interval, ΔT (K)")
ax.set_title("ΔCTE × ΔT sensitivity | V=5 vol.%, d=5 μm, Ti RT constants")
fig.text(.01,.01,"Model surface, not measurement; ρ=12ΔαΔTV/[bd(1−V)], Δσ=1.25Gb√ρ",fontsize=7)
for ext in ["png","pdf","svg"]: fig.savefig(ROOT/f"figures/fig02_cte_dt_sensitivity_surface.{ext}",dpi=600 if ext=="png" else None,bbox_inches="tight")
plt.close(fig)
'''
    elif fig_no == 3:
        body = r'''
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
df=pd.read_csv(ROOT/"figure_data/fig03_measurement_method_calibration.csv")
fig=plt.figure(figsize=(8.5,6.2)); ax=fig.add_subplot(111); markers=["o","s","^","D","v","P"]
for i,(method,g) in enumerate(df.groupby("method",sort=True)):
    ax.scatter(g.rho_m2,g.ratio_implied_to_reference,marker=markers[i%len(markers)],label=method)
for _,r in df.iterrows(): ax.annotate(r.paper_short,(r.rho_m2,r.ratio_implied_to_reference),fontsize=6,xytext=(3,3),textcoords="offset points")
ax.axhline(1,linestyle="--",linewidth=1); ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Reported/reconstructed density, ρ (m⁻²)"); ax.set_ylabel("Taylor contribution / observed strength scale")
ax.set_title("Dislocation-method calibration audit | same-sample KAM–TEM–XRD calibration unavailable")
ax.legend(fontsize=6); ax.grid(True,which="both",alpha=.25)
fig.text(.01,.01,"Ratios use paper-specific denominators; position relative to 1 is an audit, not a pooled calibration curve",fontsize=7)
for ext in ["png","pdf","svg"]: fig.savefig(ROOT/f"figures/fig03_measurement_method_calibration.{ext}",dpi=600 if ext=="png" else None,bbox_inches="tight")
plt.close(fig)
'''
    else:
        body = r'''
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
df=pd.read_csv(ROOT/"figure_data/fig04_dislocation_share_forest.csv").sort_values("share_pct")
y=np.arange(len(df)); c=df.share_pct.to_numpy(float); lo=df.share_low_pct.to_numpy(float); hi=df.share_high_pct.to_numpy(float)
fig=plt.figure(figsize=(10.5,max(6.5,.36*len(df)+2))); ax=fig.add_subplot(111)
ax.errorbar(c,y,xerr=np.vstack([c-lo,hi-c]),fmt="o",capsize=2); ax.axvline(0,linewidth=1); ax.axvline(100,linestyle="--",linewidth=1)
ax.set_yticks(y); ax.set_yticklabels(df.label,fontsize=6); ax.set_xlabel("Reported or reconstructed contribution share (%)")
ax.set_title("Dislocation contribution-share forest | denominators and estimands are paper-specific"); ax.grid(True,axis="x",alpha=.25)
fig.text(.01,.01,"Bao: matched GND/CTE share; Qiao: fraction of composite YS; Li: hot-forging GND; Munir: budget-closure red team",fontsize=7)
for ext in ["png","pdf","svg"]: fig.savefig(ROOT/f"figures/fig04_dislocation_share_forest.{ext}",dpi=600 if ext=="png" else None,bbox_inches="tight")
plt.close(fig)
'''
    return "#!/usr/bin/env python3\n" + textwrap.dedent(body).lstrip()


def write_code_and_tests(root: Path) -> None:
    for i in range(1, 5):
        write_text(root / "plot_code" / f"plot_fig{i:02d}.py", plot_script_text(i))
    write_text(root / "plot_code" / "run_all.py", textwrap.dedent('''
        #!/usr/bin/env python3
        import subprocess, sys
        from pathlib import Path
        HERE=Path(__file__).resolve().parent
        for p in sorted(HERE.glob("plot_fig*.py")):
            subprocess.run([sys.executable,str(p)],check=True)
        print("PASS: regenerated 4 figure triplets")
    ''').lstrip())
    write_text(root / "validate_package.py", textwrap.dedent('''
        #!/usr/bin/env python3
        import csv, hashlib, json, sys, zipfile
        from pathlib import Path
        ROOT=Path(__file__).resolve().parent
        mandatory=''' + repr(MANDATORY_FILES) + '''
        errors=[]
        for rel in mandatory:
            if not (ROOT/rel).exists(): errors.append(f"missing:{rel}")
        for p in ROOT.rglob("*.zip"): errors.append(f"nested_zip:{p.relative_to(ROOT)}")
        checks=ROOT/"CHECKSUMS.sha256"
        if checks.exists():
            for line in checks.read_text(encoding="utf-8").splitlines():
                if not line.strip(): continue
                digest,rel=line.split("  ",1); path=ROOT/rel
                if not path.exists(): errors.append(f"checksum_missing:{rel}"); continue
                got=hashlib.sha256(path.read_bytes()).hexdigest()
                if got!=digest: errors.append(f"checksum_mismatch:{rel}")
        status=json.loads((ROOT/"WINDOW_STATUS.json").read_text(encoding="utf-8")) if (ROOT/"WINDOW_STATUS.json").exists() else {}
        if status.get("window_id")!="QM34": errors.append("wrong_window_id")
        report={"pass":not errors,"errors":errors,"mandatory_files":len(mandatory)}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        raise SystemExit(0 if not errors else 1)
    ''').lstrip())

    tests = {
        "test_formulas.py": '''
import math, unittest
class FormulaTests(unittest.TestCase):
    def test_taylor_inverse(self):
        C,G,b,ds=.6,45.6e9,.29e-9,10.0
        rho=(ds*1e6/(C*G*b))**2
        self.assertAlmostEqual(C*G*b*math.sqrt(rho)/1e6,ds,places=8)
    def test_cte_positive(self):
        rho=12*1e-6*800*.05/(.29e-9*5e-6*(1-.05))
        self.assertGreater(rho,0)
    def test_sequential_not_additive(self):
        a,b=4e12,9e12
        self.assertLess(math.sqrt(a+b)-math.sqrt(b),math.sqrt(a))
''',
        "test_schema.py": '''
import csv, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SchemaTests(unittest.TestCase):
    def test_scope_files_have_rows(self):
        for name in ["CTE_GND_INPUTS.csv","DISLOCATION_DENSITY_CALIBRATION.csv","DISLOCATION_CONTRIBUTIONS.csv","GND_APPLICABILITY.csv"]:
            with (ROOT/name).open(encoding="utf-8-sig") as f: self.assertGreater(len(list(csv.DictReader(f))),0,name)
    def test_pair_provenance_keys(self):
        with (ROOT/"PAIR_MATCHES.csv").open(encoding="utf-8-sig") as f:
            rows=list(csv.DictReader(f))
        self.assertTrue(all(r["paper_uid"] and r["condition_uid"] for r in rows))
''',
        "test_manifest.py": '''
import hashlib, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ManifestTests(unittest.TestCase):
    def test_manifest_hashes(self):
        m=json.loads((ROOT/"MANIFEST.json").read_text(encoding="utf-8"))
        for x in m["files"]:
            p=ROOT/x["path"]
            self.assertTrue(p.exists(),x["path"])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),x["sha256"])
''',
        "test_no_nested_zip.py": '''
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ZipTests(unittest.TestCase):
    def test_no_nested_zip(self): self.assertEqual(list(ROOT.rglob("*.zip")),[])
''',
        "test_figures.py": '''
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FigureTests(unittest.TestCase):
    def test_figure_triplets(self):
        for i,stem in enumerate(["fig01_rho_delta_sigma_distribution","fig02_cte_dt_sensitivity_surface","fig03_measurement_method_calibration","fig04_dislocation_share_forest"],1):
            for ext in ["png","pdf","svg"]: self.assertGreater((ROOT/"figures"/f"{stem}.{ext}").stat().st_size,1000)
    def test_figure_data(self): self.assertEqual(len(list((ROOT/"figure_data").glob("*.csv"))),4)
''',
        "test_status.py": '''
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StatusTests(unittest.TestCase):
    def test_status(self):
        s=json.loads((ROOT/"WINDOW_STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(s["window_id"],"QM34")
        self.assertEqual(s["status"],"CONTINUE_DATA_GAP")
        self.assertLessEqual(s["claim_level_max"],2)
        self.assertFalse(s["production_model_registered"])
''',
        "test_claim_ceiling.py": '''
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ClaimTests(unittest.TestCase):
    def test_forbidden_claims_absent(self):
        text=(ROOT/"00_EXECUTIVE_VERDICT.md").read_text(encoding="utf-8")
        self.assertIn("not a direct measurement",text.lower())
        self.assertIn("No Gold promotion",text)
        self.assertIn("STATUS: CONTINUE_DATA_GAP",text)
''',
    }
    for name, body in tests.items():
        write_text(root / "tests" / name, textwrap.dedent(body).lstrip())


def build_markdown(root: Path, snapshot_id: str, data: dict[str, list[dict[str, Any]]], input_ledger: list[dict[str, Any]]) -> None:
    bao = data["bao"]
    q = data["qiao"]
    li = data["li"]
    munir = data["munir"]
    q_source, q_phys, q_relax = q
    executive = f"""# QM34 Executive Verdict — CTE mismatch, GND/dislocation density, and strengthening contribution

`WINDOW=QM34 | SNAPSHOT={snapshot_id} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Terminal scientific answer

**The defensible matched evidence does not support a universal claim that CTE mismatch is the dominant strengthening mechanism in Ti/TMCs.** In the cleanest same-paper matrix-controlled anchor (Bao 2024), the source total GND term is **10 and 21 MPa**, only **{bao[0]['gnd_share_observed_pct']:.2f}% and {bao[1]['gnd_share_observed_pct']:.2f}%** of the matched 138 and 321 MPa yield-strength increments. Because the Taylor relation is nonlinear in density, the standalone CTE and elastic-mismatch stresses cannot be added. A sequential CTE increment conditional on the elastic-mismatch background is only **{bao[0]['delta_sigma_cte_sequential_mpa']:.2f} and {bao[1]['delta_sigma_cte_sequential_mpa']:.2f} MPa**, or **{bao[0]['cte_seq_share_observed_pct']:.2f}% and {bao[1]['cte_seq_share_observed_pct']:.2f}%** of the observed increments.

Qiao 2025 supplies the largest internally reconstructable CTE/GND budget: the source density corresponds to about **{q_source['delta_sigma_gnd_total_mpa']:.1f} MPa** total GND strengthening, while the sequential CTE increment is about **{q_source['delta_sigma_cte_sequential_mpa']:.1f} MPa**. This is **not a matrix-control effect**; it is {q_source['gnd_share_composite_ys_pct']:.1f}% and {q_source['cte_seq_share_composite_ys_pct']:.1f}% of the 737 MPa composite YS. The source density back-solves an effective cooling interval of about **{q_source['delta_t_k']:.0f} K**, inconsistent with the measured 830°C peak-to-room-temperature drop of about 805 K. Using 805 K lowers the total/sequential terms to **{q_phys['delta_sigma_gnd_total_mpa']:.1f}/{q_phys['delta_sigma_cte_sequential_mpa']:.1f} MPa**; a 50% effective-cooling relaxation scenario lowers them to **{q_relax['delta_sigma_gnd_total_mpa']:.1f}/{q_relax['delta_sigma_cte_sequential_mpa']:.1f} MPa**.

Direct EBSD/KAM-derived density cannot be inserted into a bulk Taylor law without method calibration. Xu 2025 reports KAM/GND densities of 8.652×10¹⁶–3.136×10¹⁷ m⁻²; common Ti constants imply multi-GPa stresses, far above measured 405–736 MPa strengths. This is a scale/calibration failure, not evidence for multi-GPa dislocation strengthening. Conversely, Li 2026 shows that process-generated GND can be material: hot-forging GND contributes **{min(x['delta_sigma_gnd_mpa'] for x in li):.1f}–{max(x['delta_sigma_gnd_mpa'] for x in li):.1f} MPa**, roughly **{min(x['share_observed_pct'] for x in li):.1f}–{max(x['share_observed_pct'] for x in li):.1f}%** of the process-associated YS increment. That contribution is caused by hot forging/heterogeneous deformation, not CTE mismatch.

Munir 2018 is the decisive budget red team: source thermal-mismatch terms of 159–225 MPa exceed the observed strengthening in several rows, and remain positive for a specimen whose compressive YS drops by 85 MPa. Jiao 2019 is the matched null counterexample: YS increases by 160 MPa while the authors state thermal-mismatch dislocation strengthening is negligible. These results block additive, universal mechanism budgets.

## Quantitative scope

- {len(PAPERS)} paper identities reviewed; 6 primary papers included.
- {len(data['cohort'])} atomic paper×sample×condition×property rows.
- {len([p for p in data['pairs'] if str(p['analysis_eligible']).startswith('YES')])} analysis-eligible same-paper pairs and one excluded process comparison.
- {len(data['effects'])} performance/mechanism effect records.
- 4 required quantitative figures, each supplied as SVG/PDF/600-dpi PNG with source CSV and standalone Python code.
- 26 project archives hash/member-bound through the recovered project integrity ledger. Current runtime could not honestly claim a fresh byte-open of the multi-GB archives; the exact local absorption request is machine-readable.

## Claim ceiling

Maximum supported claim level is **2: same-paper matched effect/source-calculation audit**. CTE formulas are model estimates, not a direct measurement of GND. Cross-paper hierarchical pooling, causal mechanism decomposition, KAM↔TEM↔XRD conversion, high-temperature retention, and a universal contribution fraction are `NOT_IDENTIFIABLE` in this snapshot. No Gold promotion, ACTIVE mutation, production-model registration, or VALIDATED formulation is performed.

{STATUS_LINE}
"""
    write_text(root / "00_EXECUTIVE_VERDICT.md", executive)

    methods = f"""# Methods

## Estimands and atomicity

Rows are kept at `paper × sample × actual reinforcement × process × heat treatment × test mode × temperature × property`. The primary estimands are same-paper `ΔY`, `lnRR` where both values are positive, total dislocation strengthening `Δσ = C G b √ρ`, and the contribution share relative to an explicitly named denominator.

## Thermal-mismatch/GND model

For the particle model used by the quantitative anchors:

`ρ_CTE = 12 Δα ΔT V / [b d (1−V)]`

`ρ_EM = 8 ε_m V / (b d)`

`Δσ_total = C G b √(ρ_CTE + ρ_EM)`

The two standalone Taylor stresses are not additive. To avoid double counting, the package reports an order-explicit sequential increment:

`Δσ_CTE|EM = C G b [√(ρ_CTE+ρ_EM) − √ρ_EM]`.

This is a decomposition convention, not a directly observed causal effect. Reversing the order changes the component attribution while leaving the total unchanged.

## Source-specific reconstruction

- Bao 2024: source constants `C=0.6`, `G=45.6 GPa`, `b=0.29 nm`, `Δα=1×10⁻⁷ K⁻¹`, `ΔT=1500 K`, `ε_m=0.02%`; total density is back-calculated from the source 10/21 MPa Taylor terms, then partitioned using the source formula. Back-solved particle size is an audit variable, not a substitute for the original microscopy value.
- Qiao 2025: source constants `C=1.25`, `G=45.6 GPa`, `b=0.347 nm`, `V=7.2%`, `d=1.3 μm`, `ε_m=0.75%`, `ΔCTE=7.8×10⁻⁶ K⁻¹`. The text's 9.6 and 27.3 “MPa” are dimensionally audited as densities in 10¹² m⁻². Source-backsolved, physical-cooling, and 50%-effective-cooling scenarios are kept separate.
- Xu 2025: KAM-derived densities are audited with common Ti constants only to test scale consistency. The result is not used as an accepted bulk strengthening term.
- Li 2026: the source's difference-of-square-roots Taylor contribution is retained as a process-GND effect. YS increments are figure-derived with ±20 MPa sensitivity.
- Munir 2018: source thermal-mismatch terms are retained for budget-closure red teaming, not pooled.
- Jiao 2019: “negligible” is retained as qualitative null; no exact zero is imputed.

## Uncertainty and sensitivity

Sparse papers do not report joint parameter covariance. Therefore the package does not fabricate confidence intervals. It reports source uncertainty where available, ±20 MPa figure-read scenarios for Li, physical/effective ΔT scenarios for Qiao, and a full ΔCTE×ΔT grid. The generic formula elasticities are +0.5 for ΔCTE, +0.5 for ΔT, −0.5 for particle size, and `0.5/(1−V)` for V.

## Hierarchical model, LOPO and multiplicity

A cross-paper hierarchical coefficient was deliberately not fit because the rows are non-exchangeable across theory/KAM/EBSD, loading mode, denominator, processing origin and directness. Strict quantitative CTE-share evidence comes from one independent paper, so LOPO/meta-analysis is mathematically uninformative. BH-FDR is not applicable because no family of inferential hypothesis tests is reported.

## Claim language

“CTE estimate,” “source budget,” “same-paper matched share,” and “method audit” are allowed. “Measured CTE strengthening,” “universal contribution,” “causal mechanism fraction,” and “validated material law” are forbidden.
"""
    write_text(root / "METHODS.md", methods)

    limitations = """# Limitations

1. The authoritative V29/Q40 atomic snapshot, registries, provenance and conflict ledgers were not exposed as a directly open canonical bundle in this runtime. This package uses a derived snapshot and explicitly requests the missing bytes.
2. Original publication byte hashes are missing for the six included papers. DOI/title binding and recovered project-source captures are retained, but Gold promotion is forbidden.
3. No same-sample, same-condition numerical calibration links EBSD-KAM, EBSD-Nye/GND, TEM dislocation counts and XRD line-profile densities.
4. CTE models require an effective cooling interval. Peak temperature minus room temperature is not automatically the retained misfit because plasticity, recovery, interfacial sliding, phase transformation and thermal cycling relax stress.
5. Taylor constants, Burgers vector and shear modulus are temperature-, phase- and texture-dependent. Most source calculations use room-temperature constants.
6. Particle size, aspect ratio and spacing are not interchangeable. Bao's particle size is not directly re-opened and is therefore only back-solved for formula audit.
7. Hall-Petch, work hardening, HDI/back stress, residual stress, load transfer and GND terms can share underlying deformation. Linear summation can double count.
8. Li YS increments are figure-derived and scenario-bounded; they are not table-grade values.
9. No defensible quantitative 600–800°C retention/relaxation series was recovered. Room-temperature contributions cannot be projected to 800°C service.
10. Cross-paper pooling and causal claims are not identifiable; the package deliberately returns null models rather than attractive but unsupported coefficients.
"""
    write_text(root / "LIMITATIONS.md", limitations)

    readme = f"""# FINAL_QM34

Deterministic return package for **QM34 — thermal-expansion mismatch, GND/dislocation density and dislocation strengthening contribution**.

Snapshot: `{snapshot_id}`  
Status: `CONTINUE_DATA_GAP`  
Claim ceiling: Level 2.

Run `python validate_package.py`, then `python -m unittest discover -s tests -v`. Regenerate figures with `python plot_code/run_all.py`.
"""
    write_text(root / "README.md", readme)

    evidence_md = """# Primary-source evidence ledger

This file records paraphrased evidence only; it does not reproduce copyrighted papers.

- Bao 2024, DOI 10.1080/17452759.2024.2383287: same-paper Ti6Al4V/TiB WAAM matrix control; source CTE+elastic-mismatch GND equations and 10/21 MPa total GND terms; matched ΔYS 138/321 MPa.
- Qiao 2025, DOI 10.1007/s42114-025-01557-x: TA1/HEA CFAM; 7.2 vol.% HEA, 1.3 μm average particle size, 830°C peak, 737 MPa YS; source CTE+modulus-mismatch equation and internally inconsistent density/stress unit labels.
- Xu 2025, DOI 10.1016/j.jmrt.2025.11.223: microwave-sintered Ti/CF-TiC; direct UTS table and KAM-derived density values used for scale audit.
- Li 2026, Journal of Materials Science & Technology 242, 290–305: as-received/hot-forged GND densities and source 88.1–96.1 MPa process-GND strengthening; not a CTE contrast.
- Jiao 2019, Powder Technology 356, 980–989: matched Ti6Al4V/TiBw YS increase with source statement that thermal-mismatch dislocation strengthening is negligible.
- Munir 2018, DOI 10.1016/j.mtla.2018.08.015: matched CP-Ti/MWCNT compressive YS, volume fractions and source thermal-mismatch budget terms used for overclosure/opposite-sign audit.
"""
    write_text(root / "source_evidence" / "PRIMARY_SOURCE_EVIDENCE.md", evidence_md)

    reproduce = """# Reproduce and validate

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python plot_code/run_all.py
python validate_package.py
python -m unittest discover -s tests -v
```

Windows PowerShell activation: `.venv\\Scripts\\Activate.ps1`.

The build script is included as `build_qm34_package.py`. It regenerates the analysis tables and figures from the encoded provenance-bound source observations; it does not fetch or overwrite ACTIVE/Gold assets.
"""
    write_text(root / "REPRODUCE.md", reproduce)
    write_text(root / "acceptance_commands.md", "```bash\npython validate_package.py && python -m unittest discover -s tests -v && python plot_code/run_all.py\n```\n")
    write_text(root / "requirements.txt", "matplotlib==3.10.3\nnumpy==2.2.6\npandas==2.2.3\n")

    absorption = f"""# Local absorption prompt — QM34

1. Verify `FINAL_QM34.zip` against the externally supplied SHA-256.
2. Extract into a quarantine directory; reject any nested ZIP, path traversal, missing mandatory file, checksum mismatch or failed test.
3. Run `python validate_package.py` and `python -m unittest discover -s tests -v`.
4. Confirm `WINDOW_STATUS.json.snapshot_id == {snapshot_id}` and `status == CONTINUE_DATA_GAP`.
5. Rebind each effect to the authoritative V29 `paper_uid + sample_uid + condition_uid`; do not fuzzy-merge.
6. Supply the files listed in `WEB_TO_LOCAL_REQUEST.json`, then rerun the formula/unit and same-sample calibration audits.
7. Do not modify `ACTIVE_TITMC`, Gold, unified Schema, production model registry, or validated-formulation tables. This package is an analysis return only.
8. Preserve original PDFs as evidence; do not delete them after text extraction.
"""
    write_text(root / "LOCAL_ABSORPTION_PROMPT.md", absorption)

    request = {
        "window_id": WINDOW_ID,
        "snapshot_id": snapshot_id,
        "status": "CONTINUE_DATA_GAP",
        "required": [
            {"priority": 0, "object": "Q40_INPUT_SNAPSHOT/MANIFEST.json", "reason": "Bind authoritative snapshot and all source hashes."},
            {"priority": 0, "object": "ATOMIC_RECORDS.parquet or csv", "reason": "Rebuild cohort from authoritative atomic rows."},
            {"priority": 0, "object": "PROVENANCE.jsonl, CONFLICT_LEDGER.csv, EXCLUDED_RECORDS.csv", "reason": "Merge without losing evidence/negative results."},
            {"priority": 0, "object": "PAPER_REGISTRY.csv, SAMPLE_REGISTRY.csv, CONDITION_REGISTRY.csv", "reason": "Resolve paper/sample/condition identities without fuzzy matching."},
            {"priority": 1, "object": "Original PDFs and full-file SHA-256 for Bao/Qiao/Xu/Li/Jiao/Munir", "reason": "Lock equations, tables, particle sizes and units to original bytes."},
            {"priority": 1, "object": "Raw EBSD KAM/Nye maps plus step size, kernel, threshold and cleanup settings", "reason": "Recalculate method-dependent density and spatial uncertainty."},
            {"priority": 1, "object": "Same-sample TEM dislocation counts and XRD line-profile density", "reason": "Fit KAM↔TEM↔XRD calibration layer."},
            {"priority": 1, "object": "Thermal-cycle/time-resolved residual stress or density data", "reason": "Estimate retained effective ΔT and relaxation."},
            {"priority": 2, "object": "Temperature-dependent G(T), b(T), phase fraction and recovery data to 800°C", "reason": "Define high-temperature applicability domain."},
        ],
        "acceptance": {
            "hash_required": True, "no_gold_promotion": True, "no_production_registration": True,
            "join_key": ["snapshot_id", "source_hash", "paper_uid", "sample_uid", "condition_uid"],
        },
    }
    write_json(root / "WEB_TO_LOCAL_REQUEST.json", request)


def build_provenance(root: Path, snapshot_id: str, data: dict[str, list[dict[str, Any]]]) -> None:
    paper_map = {p["paper_uid"]: p for p in PAPERS}
    rows = []
    for effect in data["effects"]:
        paper = paper_map.get(effect["paper_uid"], {})
        record = {
            "snapshot_id": snapshot_id, "record_type": "effect_estimate",
            "effect_uid": effect["effect_uid"], "paper_uid": effect["paper_uid"],
            "sample_uid": effect["sample_uid"], "condition_uid": effect["condition_uid"],
            "source_title": paper.get("title", "MULTI/DERIVED"), "doi": paper.get("doi", ""),
            "source_locator": paper.get("source_locator", "derived package"),
            "source_hash": paper.get("source_hash", ""), "hash_status": paper.get("hash_status", "DERIVED"),
            "evidence_grade": effect["evidence_grade"], "estimand": effect["estimand"],
            "value": effect["estimate"], "unit": effect["unit"],
            "transformation": effect["notes"], "claim_level": effect["claim_level"],
        }
        record["record_sha256"] = sha256_bytes(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        rows.append(record)
    write_text(root / "PROVENANCE.jsonl", "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in rows))


def write_plot_specs(root: Path) -> None:
    specs = {
        "window_id": WINDOW_ID,
        "rules": {"language": "English", "formats": ["SVG", "PDF", "PNG 600 dpi"], "generative_images": False, "one_plot_per_figure": True},
        "plots": [
            {"id": "fig01", "title": "ρ–Δσ distribution", "data": "figure_data/fig01_rho_delta_sigma_distribution.csv", "code": "plot_code/plot_fig01.py", "outputs": ["figures/fig01_rho_delta_sigma_distribution.svg", "figures/fig01_rho_delta_sigma_distribution.pdf", "figures/fig01_rho_delta_sigma_distribution.png"], "required_annotations": ["paper", "method", "evidence", "support domain"]},
            {"id": "fig02", "title": "ΔCTE×ΔT sensitivity surface", "data": "figure_data/fig02_cte_dt_sensitivity_surface.csv", "code": "plot_code/plot_fig02.py", "outputs": ["figures/fig02_cte_dt_sensitivity_surface.svg", "figures/fig02_cte_dt_sensitivity_surface.pdf", "figures/fig02_cte_dt_sensitivity_surface.png"], "required_annotations": ["formula", "V", "d", "Ti constants", "model-not-measurement"]},
            {"id": "fig03", "title": "Dislocation measurement-method calibration audit", "data": "figure_data/fig03_measurement_method_calibration.csv", "code": "plot_code/plot_fig03.py", "outputs": ["figures/fig03_measurement_method_calibration.svg", "figures/fig03_measurement_method_calibration.pdf", "figures/fig03_measurement_method_calibration.png"], "required_annotations": ["same-sample calibration unavailable", "method", "reference denominator"]},
            {"id": "fig04", "title": "Dislocation contribution-share forest", "data": "figure_data/fig04_dislocation_share_forest.csv", "code": "plot_code/plot_fig04.py", "outputs": ["figures/fig04_dislocation_share_forest.svg", "figures/fig04_dislocation_share_forest.pdf", "figures/fig04_dislocation_share_forest.png"], "required_annotations": ["denominator", "estimand", "match grade", "evidence"]},
        ],
    }
    write_json(root / "PLOT_SPECS.json", specs)


def build_remaining_tables(root: Path, snapshot_id: str, data: dict[str, list[dict[str, Any]]], input_ledger: list[dict[str, Any]]) -> None:
    write_csv(root / "INPUT_LEDGER.csv", input_ledger)
    write_csv(root / "ANALYSIS_COHORT.csv", data["cohort"])
    write_csv(root / "PAIR_MATCHES.csv", data["pairs"])
    write_csv(root / "EFFECT_ESTIMATES.csv", data["effects"])
    write_csv(root / "HIERARCHICAL_RESULTS.csv", data["hierarchical"])
    write_csv(root / "DOSE_RESPONSE.csv", data["dose_response"])
    write_csv(root / "INTERACTION_EFFECTS.csv", data["interaction_effects"])
    write_csv(root / "HETEROGENEITY.csv", data["heterogeneity"])
    write_csv(root / "SENSITIVITY_ANALYSIS.csv", data["sensitivity"])
    write_csv(root / "NULL_NEGATIVE_RESULTS.csv", data["null_negative"])
    write_csv(root / "CONFLICT_LEDGER.csv", data["conflicts"])
    write_csv(root / "CTE_GND_INPUTS.csv", data["cte_inputs"])
    write_csv(root / "DISLOCATION_DENSITY_CALIBRATION.csv", data["calibration"])
    write_csv(root / "DISLOCATION_CONTRIBUTIONS.csv", data["contributions"])
    write_csv(root / "GND_APPLICABILITY.csv", data["applicability"])
    write_csv(root / "figure_data" / "fig01_rho_delta_sigma_distribution.csv", data["fig01"])
    write_csv(root / "figure_data" / "fig02_cte_dt_sensitivity_surface.csv", data["fig02"])
    write_csv(root / "figure_data" / "fig03_measurement_method_calibration.csv", data["fig03"])
    write_csv(root / "figure_data" / "fig04_dislocation_share_forest.csv", data["fig04"])

    excluded = [
        {"paper_uid": p["paper_uid"], "paper_short": p["short"], "reason": p["role"], "status": "EXCLUDED_FROM_CORE_ESTIMAND"}
        for p in PAPERS if p["included"] == "NO"
    ]
    write_csv(root / "EXCLUDED_RECORDS.csv", excluded)

    open_log = []
    for row in input_ledger:
        open_log.append({
            "object": row["source_name"], "object_type": "PROJECT_ARCHIVE",
            "directly_opened_current_window": "NO", "bound_from_prior_integrity_ledger": "YES",
            "use": row["window_relevance"], "honesty_note": row["notes"],
        })
    open_log.extend([
        {"object": "QM34 MDU", "object_type": "DISPATCH", "directly_opened_current_window": "YES", "bound_from_prior_integrity_ledger": "NO", "use": "Execution contract", "honesty_note": "User-provided text."},
        {"object": "Qiao 2025 primary PDF", "object_type": "PRIMARY_PDF", "directly_opened_current_window": "YES", "bound_from_prior_integrity_ledger": "YES", "use": "Formula, constants, microstructure, KAM and mechanical data", "honesty_note": "File Library parsed PDF; original byte hash requested."},
        {"object": "Munir 2018 primary PDF", "object_type": "PRIMARY_PDF", "directly_opened_current_window": "YES", "bound_from_prior_integrity_ledger": "YES", "use": "Matched strengths, volumes, thermal budget and counterexample", "honesty_note": "File Library parsed PDF; original byte hash requested."},
        {"object": "Xu 2025 primary PDF", "object_type": "PRIMARY_PDF", "directly_opened_current_window": "YES", "bound_from_prior_integrity_ledger": "YES", "use": "UTS tables, KAM formula and density audit", "honesty_note": "File Library parsed PDF; original byte hash requested."},
        {"object": "Bao/Li/Jiao project evidence captures", "object_type": "PRIMARY_EVIDENCE_CAPTURE", "directly_opened_current_window": "NO_FULL_BYTE", "bound_from_prior_integrity_ledger": "YES", "use": "Matched CTE/GND anchor, process-GND contrast, qualitative null", "honesty_note": "Values retained with explicit evidence grade; original PDFs/hashes requested."},
    ])
    write_csv(root / "SOURCE_OPEN_LOG.csv", open_log)

    utilization = []
    for p in PAPERS:
        utilization.append({
            "paper_uid": p["paper_uid"], "paper_short": p["short"], "included": p["included"],
            "role": p["role"], "source_locator": p["source_locator"], "hash_status": p["hash_status"],
            "terminal_use": "CORE_QUANTITATIVE" if p["included"] == "YES" else "METHOD_PRIOR_OR_EXCLUDED",
        })
    write_csv(root / "SOURCE_UTILIZATION_SUMMARY.csv", utilization)

    formula_audit = [
        {"formula_id": "F1", "formula": "ρ_CTE=12ΔαΔTV/[bd(1−V)]", "dimension": "m^-2", "status": "PASS", "risk": "effective ΔT/relaxation unknown"},
        {"formula_id": "F2", "formula": "ρ_EM=8εV/(bd)", "dimension": "m^-2", "status": "PASS_WITH_SOURCE_OCR_CHECK", "risk": "ε definition and original equation bytes"},
        {"formula_id": "F3", "formula": "Δσ=CGb√ρ", "dimension": "Pa", "status": "PASS", "risk": "method scale and temperature dependence"},
        {"formula_id": "F4", "formula": "Δσ_CTE|EM=CGb(√(ρ_CTE+ρ_EM)−√ρ_EM)", "dimension": "Pa", "status": "PASS_AS_ORDERED_DECOMPOSITION", "risk": "order-dependent, non-causal"},
        {"formula_id": "F5", "formula": "ρ_GND=2Δθ/(μb)", "dimension": "m^-2", "status": "METHOD_DEPENDENT", "risk": "step size, kernel, noise, local-vs-bulk scale"},
    ]
    write_csv(root / "source_evidence" / "FORMULA_AUDIT.csv", formula_audit)


def validate_root(root: Path) -> dict[str, Any]:
    errors = []
    for rel in MANDATORY_FILES:
        if not (root / rel).exists():
            errors.append(f"missing:{rel}")
    nested = [str(p.relative_to(root)) for p in root.rglob("*.zip")]
    if nested:
        errors.extend(f"nested_zip:{p}" for p in nested)
    for stem in ["fig01_rho_delta_sigma_distribution", "fig02_cte_dt_sensitivity_surface", "fig03_measurement_method_calibration", "fig04_dislocation_share_forest"]:
        for ext in ["png", "pdf", "svg"]:
            p = root / "figures" / f"{stem}.{ext}"
            if not p.exists() or p.stat().st_size < 1000:
                errors.append(f"bad_figure:{p.relative_to(root)}")
    if (root / "CHECKSUMS.sha256").exists():
        for line in (root / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, rel = line.split("  ", 1)
            p = root / rel
            if not p.exists():
                errors.append(f"checksum_missing:{rel}")
            elif sha256_file(p) != digest:
                errors.append(f"checksum_mismatch:{rel}")
    return {"pass": not errors, "errors": errors, "checked_at_utc": BUILD_UTC, "mandatory_count": len(MANDATORY_FILES)}


def write_manifest_and_checksums(root: Path, snapshot_id: str, status: dict[str, Any]) -> None:
    for p in [root / "MANIFEST.json", root / "CHECKSUMS.sha256"]:
        if p.exists():
            p.unlink()
    files = []
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        rel = p.relative_to(root).as_posix()
        files.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    manifest = {
        "window_id": WINDOW_ID, "package_version": PACKAGE_VERSION, "snapshot_id": snapshot_id,
        "generated_at_utc": BUILD_UTC, "status": status["status"], "claim_level_max": status["claim_level_max"],
        "production_model_registered": False, "gold_promoted": False, "nested_zip": False,
        "files": files,
    }
    write_json(root / "MANIFEST.json", manifest)
    checksum_lines = []
    for p in sorted(x for x in root.rglob("*") if x.is_file() and x.name != "CHECKSUMS.sha256"):
        checksum_lines.append(f"{sha256_file(p)}  {p.relative_to(root).as_posix()}")
    write_text(root / "CHECKSUMS.sha256", "\n".join(checksum_lines) + "\n")


def build_package(output_parent: Path) -> tuple[Path, str, str, dict[str, Any]]:
    source_fingerprint = "|".join(x[1] for x in INPUT_ARCHIVES) + "|" + sha256_file(Path(__file__))
    snapshot_id = "QM34_DERIVED_" + sha256_bytes(source_fingerprint.encode("utf-8"))[:20]
    root = output_parent / "QM34_PACKAGE"
    if root.exists():
        shutil.rmtree(root)
    ensure_dir(root)

    input_ledger = build_input_ledger(snapshot_id)
    data = make_data(snapshot_id)
    build_remaining_tables(root, snapshot_id, data, input_ledger)
    build_provenance(root, snapshot_id, data)
    build_markdown(root, snapshot_id, data, input_ledger)
    write_plot_specs(root)
    write_code_and_tests(root)
    generate_plots(root, data)
    write_text(root / "build_qm34_package.py", Path(__file__).read_text(encoding="utf-8"))

    status = {
        "window_id": WINDOW_ID, "snapshot_id": snapshot_id,
        "papers_seen": len(PAPERS), "papers_included": len([p for p in PAPERS if p["included"] == "YES"]),
        "independent_papers": 6, "atomic_rows": len(data["cohort"]),
        "matched_pairs": len([p for p in data["pairs"] if str(p["analysis_eligible"]).startswith("YES")]),
        "effect_estimates": len(data["effects"]), "plots_generated": 4,
        "open_conflicts": len([c for c in data["conflicts"] if str(c["status"]).startswith("OPEN")]),
        "claim_level_max": 2, "status": "CONTINUE_DATA_GAP",
        "next_action": "LOCAL_ABSORB_AND_PROTOCOL_AUDIT",
        "production_model_registered": False, "gold_promoted": False,
        "authoritative_active_modified": False,
    }
    write_json(root / "WINDOW_STATUS.json", status)
    write_json(root / "VALIDATION_REPORT.json", {"pass": False, "phase": "PRE_MANIFEST"})
    write_manifest_and_checksums(root, snapshot_id, status)
    report = validate_root(root)
    write_json(root / "VALIDATION_REPORT.json", report)
    write_manifest_and_checksums(root, snapshot_id, status)
    final_report = validate_root(root)
    if not final_report["pass"]:
        raise RuntimeError(json.dumps(final_report, ensure_ascii=False))

    zip_path = output_parent / "FINAL_QM34.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(x for x in root.rglob("*") if x.is_file()):
            zf.write(p, p.relative_to(root).as_posix())
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"ZIP CRC failure: {bad}")
        if any(name.lower().endswith(".zip") for name in zf.namelist()):
            raise RuntimeError("Nested ZIP detected")
    digest = sha256_file(zip_path)
    write_text(output_parent / "FINAL_QM34.zip.sha256", f"{digest}  FINAL_QM34.zip\n")
    summary = {
        "zip": str(zip_path), "zip_bytes": zip_path.stat().st_size, "zip_sha256": digest,
        "snapshot_id": snapshot_id, "status": status["status"], "file_count": len([p for p in root.rglob("*") if p.is_file()]),
        "atomic_rows": status["atomic_rows"], "matched_pairs": status["matched_pairs"],
        "effect_estimates": status["effect_estimates"], "plots_generated": status["plots_generated"],
        "validation_pass": True,
    }
    write_json(output_parent / "FINAL_QM34_DELIVERY_SUMMARY.json", summary)
    return zip_path, digest, snapshot_id, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="deliverables/QM34")
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    ensure_dir(out)
    zip_path, digest, snapshot_id, summary = build_package(out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(STATUS_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
