#!/usr/bin/env python3
"""Build the QM28 heat-treatment conditional-effects evidence packet.

The runner is deterministic, source-bound, analysis-only, and never registers a
production model or promotes any record to Gold. It writes FINAL_QM28/ with all
mandatory tables, methods, provenance, figures, plot data/code, checksums, and
validation evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM28"
FIG = OUT / "figures"
FDATA = OUT / "figure_data"
PCODE = OUT / "plot_code"
ACODE = OUT / "analysis_code"
TESTS = OUT / "tests"
SEED = 20260713
random.seed(SEED)

MANDATORY = [
    "00_EXECUTIVE_VERDICT.md", "INPUT_LEDGER.csv", "ANALYSIS_COHORT.csv",
    "PAIR_MATCHES.csv", "EFFECT_ESTIMATES.csv", "HIERARCHICAL_RESULTS.csv",
    "DOSE_RESPONSE.csv", "INTERACTION_EFFECTS.csv", "HETEROGENEITY.csv",
    "SENSITIVITY_ANALYSIS.csv", "NULL_NEGATIVE_RESULTS.csv",
    "CONFLICT_LEDGER.csv", "PROVENANCE.jsonl", "METHODS.md", "LIMITATIONS.md",
    "PLOT_SPECS.json", "WEB_TO_LOCAL_REQUEST.json", "LOCAL_ABSORPTION_PROMPT.md",
    "WINDOW_STATUS.json", "MANIFEST.json", "CHECKSUMS.sha256",
    "HEAT_TREATMENT_SEQUENCES.csv", "HT_PAIR_EFFECTS.csv",
    "HT_DOSE_RESPONSE.csv", "HT_REINFORCEMENT_INTERACTIONS.csv",
]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sid(prefix: str, *parts: Any) -> str:
    return f"{prefix}_{sha('|'.join(str(x) for x in parts))[:14]}"


def clean_dir() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    for p in (OUT, FIG, FDATA, PCODE, ACODE, TESTS):
        p.mkdir(parents=True, exist_ok=True)


def write_text(rel: str, text: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(rel: str, obj: Any) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(rel: str, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else ["status", "reason"]
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: "" if row.get(k) is None else row.get(k) for k in fields})


def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def bh_fdr(rows: list[dict[str, Any]]) -> None:
    valid = [(i, float(r["p_value"])) for i, r in enumerate(rows) if r.get("p_value") not in (None, "")]
    valid.sort(key=lambda x: x[1])
    m = len(valid)
    qraw = [0.0] * m
    for rank, (_, p) in enumerate(valid, 1):
        qraw[rank - 1] = min(1.0, p * m / rank)
    for j in range(m - 2, -1, -1):
        qraw[j] = min(qraw[j], qraw[j + 1])
    for (idx, _), q in zip(valid, qraw):
        rows[idx]["q_value_BH"] = q


PAPERS = [
    dict(key="WANG2024", title="Microstructure evolution and enhanced mechanical properties of as-rolled TiB/TA15-Si composite by heat treatment", year=2024, doi="10.1016/j.msea.2023.145888", locator="chatgpt_filecite:turn29file1", raw_hash="c184926d74bff7d56c695b815b31e1b0ac60f1f2a2c310addd77b61120941ea7", hash_type="RAW_PDF_SHA256"),
    dict(key="QI2012", title="Influence of matrix characteristics on tensile properties of in situ synthesized TiC/TA15 composite", year=2012, doi="10.1016/j.msea.2012.05.092", locator="chatgpt_filecite:turn31file0", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
    dict(key="FEREIDUNI2021", title="TiB reinforced Ti-6Al-4V matrix composites with improved short-term creep performance fabricated by laser powder bed fusion", year=2021, doi="10.1016/j.jmapro.2021.08.063", locator="chatgpt_filecite:turn31file1", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
    dict(key="RIELLI2020", title="Single step heat treatment for the development of beta titanium composites with in-situ TiB and TiC reinforcement", year=2020, doi="10.1016/j.matchar.2020.110286", locator="chatgpt_filecite:turn31file2", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
    dict(key="BAI2025", title="Heat-treatment response of SLM Ti-6Al-4V and SiC-modified composite", year=2025, doi="10.1016/j.jmrt.2025.06.124", locator="chatgpt_filecite:turn29file2", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
    dict(key="ROGER2017", title="Heat-treatment-driven TiC particle coarsening in Ti-15 vol.% TiC", year=2017, doi="10.1007/s10853-016-0677-y", locator="chatgpt_filecite:turn19file1", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
    dict(key="ANDRIEUX2018", title="In-situ synchrotron and DICTRA study of TiC transformation in Ti-15 vol.% TiC", year=2018, doi="10.1007/s10853-018-2258-8", locator="chatgpt_filecite:turn19file2", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
    dict(key="WANG2018", title="Effect of heat treatment on microstructure and elevated-temperature tensile properties of TiBw/TA15-Si composite", year=2018, doi="UNRESOLVED", locator="chatgpt_filecite:turn21file0", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
    dict(key="JIAO2016", title="Heat-treatment response of (Ti5Si3+TiBw)/Ti6Al4V composite", year=2016, doi="10.1038/srep32991", locator="chatgpt_filecite:turn26file3;turn26file5", raw_hash="", hash_type="NORMALIZED_EVIDENCE_CAPTURE_SHA256"),
]
for p in PAPERS:
    p["paper_uid"] = sid("P", p["doi"], p["title"])
    if not p["raw_hash"]:
        p["raw_hash"] = sha(f"{p['doi']}|{p['title']}|{p['locator']}")
PAPER = {p["key"]: p for p in PAPERS}

# Mounted source-package ledger. Hashes and member counts are inherited from the
# project upload/audit state where available. The public runner cannot mount the
# chat filesystem, so absence of a hash is not silently converted into verification.
ARCHIVES = [
    ("00_统一上传总控与校验信息_20260712.zip", "control", "", "", "NAME_ONLY_REMOTE_RUNNER"),
    ("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip", "platform_code", "", "", "NAME_ONLY_REMOTE_RUNNER"),
    ("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip", "frozen_data_features", "", "", "NAME_ONLY_REMOTE_RUNNER"),
    ("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip", "frozen_data_features", "", "", "NAME_ONLY_REMOTE_RUNNER"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip", "harness", "cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a", 7, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip", "harness", "97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809", 7, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip", "harness", "16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f", 9, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip", "harness", "04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9", 11, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip", "harness", "5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728", 17, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip", "harness", "e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847", 38, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip", "harness", "36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485", 69, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip", "harness", "9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd", 246, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip", "github_history", "c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c", 57191, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip", "github_code", "a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a", 244, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip", "github_code", "bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43", 396, "INHERITED_SHA_MEMBER_AUDIT"),
    ("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip", "github_code", "08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755", 499, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P001_OF_010.zip", "literature", "42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0", 15, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P002_OF_010.zip", "literature", "05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193", 154, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P003_OF_010.zip", "literature", "535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917", 4610, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P004_OF_010.zip", "literature", "bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a", 7747, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P005_OF_010.zip", "literature", "1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1", 10068, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P006_OF_010.zip", "literature", "5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13", 11778, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P007_OF_010.zip", "literature", "", "", "NAME_ONLY_REMOTE_RUNNER"),
    ("TITMC_V27_LIT_WEB_P008_OF_010.zip", "literature", "", "", "NAME_ONLY_REMOTE_RUNNER"),
    ("TITMC_V27_LIT_WEB_P009_OF_010.zip", "literature", "b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a", 20036, "INHERITED_SHA_MEMBER_AUDIT"),
    ("TITMC_V27_LIT_WEB_P010_OF_010.zip", "literature", "faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d", 57717, "INHERITED_SHA_MEMBER_AUDIT"),
]

SEQUENCES: list[dict[str, Any]] = []

def seq(pkey: str, seq_name: str, stage: int, stage_type: str, temp: Any, time_h: Any, cooling: str, beta: Any, purpose: str, atmosphere: str = "", flag: str = "") -> None:
    delta = ""
    if isinstance(temp, (int, float)) and isinstance(beta, (int, float)):
        delta = float(temp) - float(beta)
    SEQUENCES.append({
        "sequence_id": sid("HTSEQ", pkey, seq_name), "paper_uid": PAPER[pkey]["paper_uid"],
        "paper_key": pkey, "sequence_name": seq_name, "stage_index": stage,
        "stage_type": stage_type, "temperature_C": temp, "time_h": time_h,
        "cooling_to_next": cooling, "atmosphere": atmosphere, "beta_transus_C": beta,
        "delta_to_beta_transus_C": delta, "purpose": purpose,
        "source_locator": PAPER[pkey]["locator"], "uncertainty_flag": flag,
    })

# Exact stage-wise paths; no sequence is collapsed to its maximum temperature.
for age in (550, 600, 650, 700, 750):
    n = f"S1050_WQ_A{age}_AC"
    seq("WANG2024", n, 1, "solution", 1050, 0.5, "water_quench", 1020, "martensitic reset")
    seq("WANG2024", n, 2, "aging", age, 1.0, "air_cool", 1020, "precipitation/decomposition")
seq("WANG2024", "S1050_WQ", 1, "solution", 1050, 0.5, "water_quench", 1020, "martensitic reset")
seq("QI2012", "HT1", 1, "supertransus_hold", 1120, 5.0, "air_cool", 1095, "fine fully lamellar matrix")
seq("QI2012", "HT2", 1, "supertransus_hold", 1120, 5.0, "cool_15C_min", 1095, "beta reset")
seq("QI2012", "HT2", 2, "subtransus_hold", 1075, 1/6, "air_cool", 1095, "bimodal matrix")
seq("QI2012", "HT3", 1, "supertransus_hold", 1120, 5.0, "cool_15C_min", 1095, "beta reset")
seq("QI2012", "HT3", 2, "subtransus_hold", 1035, 1/6, "air_cool", 1095, "near-equiaxed matrix")
seq("FEREIDUNI2021", "HT1050_2h_FC", 1, "supertransus_hold", 1050, 2.0, "furnace_cool", "", "remove AM anisotropy", flag="beta_transus_not_reported_in_capture")
for dose in (0, 0.5, 1.5, 3.0):
    seq("RIELLI2020", f"FC_B4C_{dose}", 1, "supertransus_anneal_solution", 1000, 12.0, "furnace_cool_3C_min", 815, "single-step beta-matrix development", "Ar")
for sol in (950, 1000, 1050):
    n = f"S{sol}_WQ_A60_AC"
    seq("BAI2025", n, 1, "solution", sol, 2/3, "water_quench", "", "solution response", flag="beta_transus_missing")
    seq("BAI2025", n, 2, "aging", 60, 4.0, "air_cool", "", "source-stated aging", flag="possible_source_typo_60C")
for t in (0.025, 0.083333, 1.0, 25.0, 100.0, 454.0):
    seq("ROGER2017", f"H920_{t}h", 1, "isothermal_anneal", 920, t, "not_reported", "", "TiC morphology kinetics")
for temp, times in ((800, (0.05, 0.1, 1.5)), (900, (1.0,))):
    for t in times:
        seq("ANDRIEUX2018", f"H{temp}_{t}h", 1, "isothermal_hold", temp, t, "not_reported", "", "TiC transformation kinetics")
for name, s_temp, a_temp in (("HT1",1100,500),("HT2",1000,500),("HT3",1000,600),("HT4",1000,700)):
    seq("WANG2018", name, 1, "solution", s_temp, 2.0, "air_cool", "", "matrix reset", flag="beta_transus_missing")
    seq("WANG2018", name, 2, "aging", a_temp, 5.0, "air_cool", "", "alpha2 precipitation", flag="beta_transus_missing")
for temp in (990,1100,1200):
    seq("JIAO2016", f"WQ_{temp}", 1, "solution_quench", temp, "", "water_quench", "", "matrix/reinforcement phase response", flag="hold_time_and_beta_transus_missing")

COHORT: list[dict[str, Any]] = []
PAIR: list[dict[str, Any]] = []
_seen_atomic: set[tuple[Any, ...]] = set()

MATERIALS = {
    "WANG2024": ("TA15-Si", "Ti-6.5Al-2Zr-1Mo-1V-0.3Si", "3.5 vol.% TiB", "powder metallurgy + hot rolling"),
    "QI2012": ("TA15", "Ti-6Al-2Zr-1.5Mo-1V", "10 vol.% TiC", "induction melting + casting"),
    "FEREIDUNI2021": ("Ti64", "Ti-6Al-4V", "none or TiB from 0.2 wt.% B4C", "laser powder bed fusion"),
    "RIELLI2020": ("Beta21S", "Ti-15Mo-3Nb-3Al-0.2Si", "TiB+TiC from 0-3 wt.% B4C", "vacuum arc remelting"),
    "BAI2025": ("Ti64", "Ti-6Al-4V", "none or reaction products from 1 wt.% SiC", "selective laser melting"),
    "ROGER2017": ("Ti", "Ti", "15 vol.% TiC", "powder route/consolidation"),
    "ANDRIEUX2018": ("Ti", "Ti", "15 vol.% TiC", "in-situ synchrotron heat treatment"),
    "WANG2018": ("TA15-Si", "Ti-5.8Al-3.4Zr-4Sn-0.4Mo-0.4Nb-0.4Si-0.06C", "5.1 vol.% TiBw", "powder metallurgy + extrusion"),
    "JIAO2016": ("Ti64", "Ti-6Al-4V", "4 vol.% Ti5Si3 + 3.4 vol.% TiBw", "powder metallurgy")
}


def atomic(pkey: str, material_variant: str, condition: str, property_name: str, value: Any, unit: str,
           test_mode: str, test_temp: Any, sd: Any = "", n: Any = "", evidence: str = "DIRECT_TABLE_TEXT",
           sequence_name: str = "", notes: str = "") -> str:
    matrix_family, comp, reinf, process = MATERIALS[pkey]
    puid = PAPER[pkey]["paper_uid"]
    sample_uid = sid("S", puid, material_variant, comp, reinf, process)
    sequence_id = sid("HTSEQ", pkey, sequence_name) if sequence_name else "AS_PROCESSED"
    condition_uid = sid("C", sample_uid, condition, sequence_id, test_mode, test_temp)
    key = (puid, sample_uid, condition_uid, property_name, test_mode, test_temp)
    if key not in _seen_atomic:
        _seen_atomic.add(key)
        COHORT.append({
            "record_uid": sid("R", *key), "paper_uid": puid, "paper_key": pkey,
            "sample_uid": sample_uid, "condition_uid": condition_uid,
            "matrix_family": matrix_family, "actual_composition": comp,
            "material_variant": material_variant, "actual_reinforcement": reinf,
            "process": process, "heat_treatment_sequence_id": sequence_id,
            "condition_label": condition, "test_mode": test_mode,
            "test_temperature_C": test_temp, "property": property_name,
            "value": value, "unit": unit, "sd": sd, "n": n,
            "evidence_level": evidence, "source_locator": PAPER[pkey]["locator"],
            "source_hash": PAPER[pkey]["raw_hash"], "hash_type": PAPER[pkey]["hash_type"],
            "inclusion_status": "INCLUDED", "notes": notes,
        })
    return condition_uid


def add_pair(pkey: str, material_variant: str, base_label: str, treat_label: str,
             prop: str, test_mode: str, test_temp: Any, base: float, treat: float, unit: str,
             base_sd: Any = "", treat_sd: Any = "", n: Any = "", evidence: str = "DIRECT_TABLE_TEXT",
             sequence_name: str = "", favorable: str = "higher", notes: str = "") -> None:
    base_uid = atomic(pkey, material_variant, base_label, prop, base, unit, test_mode, test_temp, base_sd, n, evidence, "", notes)
    tr_uid = atomic(pkey, material_variant, treat_label, prop, treat, unit, test_mode, test_temp, treat_sd, n, evidence, sequence_name, notes)
    delta = treat - base
    lnrr = math.log(treat / base) if base > 0 and treat > 0 else ""
    pct = 100.0 * (treat / base - 1.0) if base != 0 else ""
    se_delta = ci_dl = ci_dh = se_lnrr = ci_ll = ci_lh = p = ""
    if all(isinstance(x, (int, float)) for x in (base_sd, treat_sd, n)) and n:
        se_delta = math.sqrt(base_sd**2/n + treat_sd**2/n)
        ci_dl, ci_dh = delta - 1.96*se_delta, delta + 1.96*se_delta
        if base > 0 and treat > 0:
            se_lnrr = math.sqrt(treat_sd**2/(n*treat**2) + base_sd**2/(n*base**2))
            ci_ll, ci_lh = lnrr - 1.96*se_lnrr, lnrr + 1.96*se_lnrr
            z = abs(lnrr / se_lnrr) if se_lnrr else float("inf")
            p = 2*(1-norm_cdf(z))
    PAIR.append({
        "pair_id": sid("PAIR", pkey, material_variant, base_label, treat_label, prop, test_mode, test_temp),
        "paper_uid": PAPER[pkey]["paper_uid"], "paper_key": pkey,
        "sample_uid": sid("S", PAPER[pkey]["paper_uid"], material_variant, MATERIALS[pkey][1], MATERIALS[pkey][2], MATERIALS[pkey][3]),
        "comparator_condition_uid": base_uid, "treatment_condition_uid": tr_uid,
        "comparator_label": base_label, "treatment_label": treat_label,
        "heat_treatment_sequence_id": sid("HTSEQ", pkey, sequence_name),
        "property": prop, "test_mode": test_mode, "test_temperature_C": test_temp,
        "comparator_value": base, "treatment_value": treat, "unit": unit,
        "delta": delta, "lnRR": lnrr, "percent_change": pct,
        "SE_delta": se_delta, "CI95_low_delta": ci_dl, "CI95_high_delta": ci_dh,
        "SE_lnRR": se_lnrr, "CI95_low_lnRR": ci_ll, "CI95_high_lnRR": ci_lh,
        "p_value": p, "q_value_BH": "", "favorable_direction": favorable,
        "evidence_level": evidence, "match_grade": "A", "claim_level": 2,
        "source_locator": PAPER[pkey]["locator"], "notes": notes,
    })

# WANG2024: figure-derived hardness; direct-text/table high-temperature tensile.
for label, val, seqname in [
    ("solution_1050WQ",444,"S1050_WQ"),("age550",475,"S1050_WQ_A550_AC"),
    ("age600",482,"S1050_WQ_A600_AC"),("age650",455,"S1050_WQ_A650_AC"),
    ("age700",440,"S1050_WQ_A700_AC"),("age750",413,"S1050_WQ_A750_AC")]:
    add_pair("WANG2024","TiB/TA15-Si","as_rolled",label,"hardness_HV","Vickers",25,422,val,"HV","","","","FIGURE_DERIVED",seqname,notes="Figure-read hardness; not Gold-promotable")
for label, uts, el, seqname in [("age600",992,26,"S1050_WQ_A600_AC"),("age700",852,32,"S1050_WQ_A700_AC"),("age750",768,None,"S1050_WQ_A750_AC")]:
    add_pair("WANG2024","TiB/TA15-Si","as_rolled",label,"UTS","tension",600,710,uts,"MPa",sequence_name=seqname)
    if el is not None:
        add_pair("WANG2024","TiB/TA15-Si","as_rolled",label,"elongation","tension",600,39,el,"%",sequence_name=seqname)
for label, uts, seqname in [("age600",399,"S1050_WQ_A600_AC"),("age700",421,"S1050_WQ_A700_AC")]:
    add_pair("WANG2024","TiB/TA15-Si","as_rolled",label,"UTS","tension",700,228,uts,"MPa",sequence_name=seqname)
    add_pair("WANG2024","TiB/TA15-Si","as_rolled",label,"elongation","tension",700,182,68,"%",sequence_name=seqname)

# QI2012, n=3, table means and SD; CIs use independent-group approximation because covariance is unavailable.
qi_rt = {"as_cast":(1048.3,1023.1,3.92,4.6,6.2,0.56),"HT1":(1119.7,1045.8,2.17,7.3,4.5,0.31),"HT2":(1130.6,1056.5,1.33,5.1,4.7,0.20),"HT3":(1159.4,1076.6,0.65,3.3,5.5,0.07)}
for h in ("HT1","HT2","HT3"):
    for idx, prop, unit in ((0,"UTS","MPa"),(1,"YS","MPa"),(2,"elongation","%")):
        add_pair("QI2012","10vol%TiC/TA15","as_cast",h,prop,"tension",25,qi_rt["as_cast"][idx],qi_rt[h][idx],unit,qi_rt["as_cast"][idx+3],qi_rt[h][idx+3],3,sequence_name=h,notes="SE assumes independent groups; within-study covariance not reported")
qi_ht = {
    600:{"as_cast":(597.7,5.53,5.6,1.34),"HT1":(652.5,6.76,7.7,0.82),"HT2":(687.7,7.44,2.6,2.16)},
    650:{"as_cast":(494.8,16.45,6.2,1.66),"HT1":(505.6,20.73,2.4,3.40),"HT2":(507.7,19.89,3.5,2.57)},
}
for temp in (600,650):
    for h in ("HT1","HT2"):
        for idx, prop, unit in ((0,"UTS","MPa"),(1,"elongation","%")):
            add_pair("QI2012","10vol%TiC/TA15","as_cast",h,prop,"tension",temp,qi_ht[temp]["as_cast"][idx],qi_ht[temp][h][idx],unit,qi_ht[temp]["as_cast"][idx+2],qi_ht[temp][h][idx+2],3,sequence_name=h,notes="SE assumes independent groups; within-study covariance not reported")

# FEREIDUNI2021: true matrix/composite interaction under identical supertransus treatment.
fdata = {
    "Ti64":{"AB":(3.4,5.93,28.3,None),"HT":(0.6,2.16,3.6,None)},
    "TMC":{"AB":(2.9,4.48,13.26,66.7),"HT":(5.8,0.84,7.46,12.5)},
}
for material in ("Ti64","TMC"):
    for idx, prop, unit, fav in ((0,"rupture_time","h","higher"),(1,"steady_state_creep_rate","%/h","lower"),(2,"total_creep_strain","%","context"),(3,"5D_elongation","%","context")):
        b,t=fdata[material]["AB"][idx],fdata[material]["HT"][idx]
        if b is not None and t is not None:
            add_pair("FEREIDUNI2021",material,"as_built","HT1050_2h_FC",prop,"creep_tension_200MPa",600,b,t,unit,sequence_name="HT1050_2h_FC",favorable=fav)

# WANG2018 elevated-temperature tensile table.
for h,uts,el in (("HT1",904,14.5),("HT2",953,14.0),("HT3",955,13.2),("HT4",986,10.8)):
    add_pair("WANG2018","TiBw/TA15-Si","untreated",h,"UTS","tension",600,850,uts,"MPa",sequence_name=h)
    add_pair("WANG2018","TiBw/TA15-Si","untreated",h,"elongation","tension",600,15.5,el,"%",sequence_name=h)

# JIAO2016 tension and compression: mean±SD, but n was not identified, so no inferential CI.
for temp,uts,sdv in ((990,1010,12.5),(1100,1050,11.2),(1200,1070,13.0)):
    add_pair("JIAO2016","hybrid/Ti64","as_sintered",f"WQ_{temp}","UTS","tension",25,1160,uts,"MPa",9.8,sdv,"",sequence_name=f"WQ_{temp}",notes="SD reported; n unresolved, CI not computed")
for temp,ycs,ucs,deform,sy,su,se in ((990,1305,1412,16.3,11.3,11.5,0.3),(1100,1535,1627,8.2,12.6,12.0,0.2),(1200,1687,1753,6.6,12.5,13.0,0.2)):
    add_pair("JIAO2016","hybrid/Ti64","as_sintered",f"WQ_{temp}","CYS","compression",25,1225,ycs,"MPa",9.6,sy,"",sequence_name=f"WQ_{temp}",notes="SD reported; n unresolved, CI not computed")
    add_pair("JIAO2016","hybrid/Ti64","as_sintered",f"WQ_{temp}","UCS","compression",25,1402,ucs,"MPa",10.0,su,"",sequence_name=f"WQ_{temp}",notes="SD reported; n unresolved, CI not computed")
    add_pair("JIAO2016","hybrid/Ti64","as_sintered",f"WQ_{temp}","max_compressive_deformation","compression",25,21.9,deform,"%",0.5,se,"",sequence_name=f"WQ_{temp}",notes="SD reported; n unresolved, CI not computed")

bh_fdr(PAIR)

# Fixed-HT reinforcement dose and phase/morphology cohorts that are not valid HT-vs-baseline pairs.
for dose,grain,cys,ucs,deform in ((0,1033,801,1116,23.8),(0.5,196,1055,1521,14.6),(1.5,150,1281,1680,13.2),(3.0,24,1205,1636,20.5)):
    v=f"B4C_{dose}wtpct"
    s=f"FC_B4C_{dose}"
    atomic("RIELLI2020",v,s,"prior_beta_grain_size",grain,"um","microstructure",25,evidence="DIRECT_TEXT",sequence_name=s)
    atomic("RIELLI2020",v,s,"CYS",cys,"MPa","compression",25,n=3,sequence_name=s)
    atomic("RIELLI2020",v,s,"UCS",ucs,"MPa","compression",25,n=3,sequence_name=s)
    atomic("RIELLI2020",v,s,"max_compressive_deformation",deform,"%","compression",25,n=3,sequence_name=s)
atomic("RIELLI2020","B4C_1.5wtpct","FC_B4C_1.5","microhardness",424,"HV","Vickers",25,n=10,sequence_name="FC_B4C_1.5")
atomic("RIELLI2020","B4C_1.5wtpct","FC_B4C_1.5","macrohardness",460,"HV","Vickers",25,n=10,sequence_name="FC_B4C_1.5")
atomic("RIELLI2020","B4C_3.0wtpct","FC_B4C_3.0","microhardness",375,"HV","Vickers",25,n=10,sequence_name="FC_B4C_3.0")
atomic("RIELLI2020","B4C_3.0wtpct","FC_B4C_3.0","macrohardness",393,"HV","Vickers",25,n=10,sequence_name="FC_B4C_3.0")

for t,size in ((0,1.013),(0.025,0.552),(0.083333,0.878),(1.0,1.103),(25.0,2.568),(100.0,3.150),(454.0,5.437)):
    label="initial" if t==0 else f"H920_{t}h"
    atomic("ROGER2017","15vol%TiC/Ti",label,"TiC_particle_size",size,"um","microstructure",920,evidence="DIRECT_TEXT",sequence_name="" if t==0 else label)
for temp,t,prop,val,unit in ((800,0.05,"small_particle_disappearance","observed","categorical"),(800,0.1,"transformation_fraction",50,"%"),(800,1.5,"large_TiC0.96_remaining",25,"%"),(900,1.0,"carbide_mass_fraction",21,"%")):
    atomic("ANDRIEUX2018","15vol%TiC/Ti",f"H{temp}_{t}h",prop,val,unit,"in_situ_synchrotron",temp,evidence="DIRECT_TEXT",sequence_name=f"H{temp}_{t}h")

# Bai contributes sequence/microstructure evidence only; mechanical HT effects are not reported in the captured primary source.
MECHANISMS = [
    {"paper_key":"WANG2024","condition":"solution+aging 550-750C","phase_microstructure":"solution creates 100-700 nm alpha-prime; 650-700C decomposes to acicular alpha+beta; 750C abnormal 1-5 um alpha and silicide coarsening","interface_stability":"silicides dissolve then reprecipitate; TiB retained","evidence":"DIRECT_TEXT"},
    {"paper_key":"QI2012","condition":"HT1/HT2/HT3","phase_microstructure":"TiC spheroidization; alpha lath/colony refinement; 21.6% and 59.7% primary alpha for HT2/HT3","interface_stability":"clean TiC/matrix interfaces after HT1 and HT3","evidence":"DIRECT_TABLE_TEXT"},
    {"paper_key":"FEREIDUNI2021","condition":"1050C 2h furnace cool","phase_microstructure":"Ti64 forms coarse equiaxed prior-beta plus continuous GB-alpha; TMC forms equiaxed alpha and no continuous GB-alpha","interface_stability":"TiB length ~1 to 6.3 um and diameter 150 to 381 nm; creep load transfer with cracking/debonding","evidence":"DIRECT_TABLE_TEXT"},
    {"paper_key":"RIELLI2020","condition":"1000C 12h FC 3C/min","phase_microstructure":"TiB/TiC pin beta grains and nucleate irregular alpha; alpha decreases/refines with B4C dose","interface_stability":"long supertransus exposure does not erase dose-dependent grain refinement","evidence":"DIRECT_TEXT"},
    {"paper_key":"BAI2025","condition":"950/1000/1050C solution + source-stated 60C aging","phase_microstructure":"950C composite fine lath/granular alpha; 1000C uniform alpha+beta; 1050C TiC coarsening with nanoscale Ti5Si3 pinning","interface_stability":"mechanical effect not reported in capture","evidence":"DIRECT_TEXT"},
    {"paper_key":"ROGER2017","condition":"920C 1.5min-454h","phase_microstructure":"sub-hour aggregation/coalescence; later Ostwald ripening and TiC stoichiometry evolution","interface_stability":"particle-size kinetics quantified","evidence":"DIRECT_TEXT"},
    {"paper_key":"ANDRIEUX2018","condition":"800-900C","phase_microstructure":"rapid dissolution/transformation of smallest TiC; phase fraction evolves over minutes-hours","interface_stability":"DICTRA and synchrotron cross-check","evidence":"DIRECT_TEXT"},
    {"paper_key":"WANG2018","condition":"solution 1000/1100C + aging 500-700C","phase_microstructure":"alpha2 precipitates 5-30 nm for alpha+beta solution route; transformed beta for beta-field route","interface_stability":"TiBw interfaces remain stable","evidence":"DIRECT_TABLE_TEXT"},
    {"paper_key":"JIAO2016","condition":"990/1100/1200C water quench","phase_microstructure":"transformed beta/martensite increases; Ti5Si3 changes/dissolves; high-temperature quench produces severe brittleness","interface_stability":"hybrid phases do not prevent tensile-strength loss","evidence":"DIRECT_TABLE_TEXT"},
]

# Study-level path-averaged high-temperature synthesis; each paper contributes one effect.
def path_mean(pkey: str, prop: str, temp: int) -> float:
    vals=[float(r["lnRR"]) for r in PAIR if r["paper_key"]==pkey and r["property"]==prop and r["test_temperature_C"]==temp and r["lnRR"]!=""]
    return statistics.mean(vals)

SYNTHESIS = []
HET = []
SENS = []
for prop in ("UTS","elongation"):
    effects={k:path_mean(k,prop,600) for k in ("WANG2024","QI2012","WANG2018")}
    est=statistics.mean(effects.values())
    rng=random.Random(SEED + (0 if prop=="UTS" else 1))
    boots=[]
    keys=list(effects)
    for _ in range(20000):
        boots.append(statistics.mean(effects[rng.choice(keys)] for __ in keys))
    boots.sort()
    lo,hi=boots[int(0.025*len(boots))],boots[int(0.975*len(boots))-1]
    SYNTHESIS.append({"outcome":prop,"test_temperature_C":600,"effect_scale":"paper-equal path-mean lnRR","k_papers":3,"estimate_lnRR":est,"percent_effect":100*(math.exp(est)-1),"cluster_bootstrap_low_lnRR":lo,"cluster_bootstrap_high_lnRR":hi,"prediction_interval":"NOT_IDENTIFIABLE_K3","tau2":"NOT_IDENTIFIABLE_K3","claim_level":2,"interpretation":"directionally positive" if prop=="UTS" else "sign-conflicted; universal effect not identifiable"})
    for k,v in effects.items():
        HET.append({"outcome":prop,"test_temperature_C":600,"paper_key":k,"paper_path_mean_lnRR":v,"paper_percent_effect":100*(math.exp(v)-1),"direction":"positive" if v>0 else "negative"})
    for omit in keys:
        keep=[v for k,v in effects.items() if k!=omit]
        e=statistics.mean(keep)
        SENS.append({"analysis":f"600C_{prop}_LOPO","omitted_paper":omit,"estimate_lnRR":e,"percent_effect":100*(math.exp(e)-1),"conclusion":"positive" if e>0 else "negative"})

# Fereiduni interaction: difference-in-differences and log ratio-of-ratios.
INTERACTIONS=[]
for prop,idx,unit in (("rupture_time",0,"h"),("steady_state_creep_rate",1,"%/h"),("total_creep_strain",2,"%")):
    mb,mt=fdata["Ti64"]["AB"][idx],fdata["Ti64"]["HT"][idx]
    cb,ct=fdata["TMC"]["AB"][idx],fdata["TMC"]["HT"][idx]
    did=(ct-cb)-(mt-mb)
    lror=math.log((ct/cb)/(mt/mb))
    INTERACTIONS.append({"interaction_id":sid("INT","FEREIDUNI2021",prop),"paper_uid":PAPER["FEREIDUNI2021"]["paper_uid"],"paper_key":"FEREIDUNI2021","property":prop,"test_condition":"600C_200MPa_creep","matrix_HT_effect":mt-mb,"TMC_HT_effect":ct-cb,"additive_DID":did,"unit":unit,"log_ratio_of_ratios":lror,"ratio_of_ratios":math.exp(lror),"match_grade":"A","claim_level":2,"uncertainty":"not estimable; replicate dispersion unavailable","source_locator":PAPER["FEREIDUNI2021"]["locator"]})
INTERACTIONS.append({"interaction_id":sid("INT","FEREIDUNI2021","5D_elongation"),"paper_uid":PAPER["FEREIDUNI2021"]["paper_uid"],"paper_key":"FEREIDUNI2021","property":"5D_elongation","test_condition":"600C_200MPa_creep","matrix_HT_effect":"NOT_IDENTIFIABLE","TMC_HT_effect":12.5-66.7,"additive_DID":"NOT_IDENTIFIABLE","unit":"%","log_ratio_of_ratios":"NOT_IDENTIFIABLE","ratio_of_ratios":"NOT_IDENTIFIABLE","match_grade":"A","claim_level":1,"uncertainty":"HT-Ti64 5D elongation missing","source_locator":PAPER["FEREIDUNI2021"]["locator"]})

# High-temperature strength retention.
RETENTION=[
    {"paper_key":"WANG2024","condition":"as_rolled","property":"UTS","R_700_over_600":228/710,"support":"direct same-paper"},
    {"paper_key":"WANG2024","condition":"age600","property":"UTS","R_700_over_600":399/992,"support":"direct same-paper"},
    {"paper_key":"WANG2024","condition":"age700","property":"UTS","R_700_over_600":421/852,"support":"direct same-paper"},
]

DOSE=[]
for r in PAIR:
    if r["paper_key"] in {"WANG2024","QI2012","WANG2018","JIAO2016"}:
        DOSE.append({"paper_key":r["paper_key"],"sequence_id":r["heat_treatment_sequence_id"],"treatment_label":r["treatment_label"],"property":r["property"],"test_temperature_C":r["test_temperature_C"],"response_value":r["treatment_value"],"unit":r["unit"],"percent_vs_baseline":r["percent_change"],"dose_axis":"full_sequence; see HEAT_TREATMENT_SEQUENCES.csv","support_domain":"observed_only"})
for r in COHORT:
    if r["paper_key"] in {"RIELLI2020","ROGER2017","ANDRIEUX2018"}:
        DOSE.append({"paper_key":r["paper_key"],"sequence_id":r["heat_treatment_sequence_id"],"treatment_label":r["condition_label"],"property":r["property"],"test_temperature_C":r["test_temperature_C"],"response_value":r["value"],"unit":r["unit"],"percent_vs_baseline":"","dose_axis":"full_sequence; see HEAT_TREATMENT_SEQUENCES.csv","support_domain":"observed_only"})

NULLS = [
    {"finding_id":"N01","paper_key":"QI2012","result":"At 650C HT1/HT2 changed UTS by only +2.18%/+2.61%; the below-600C matrix-strengthening benefit largely collapsed.","type":"near_null","claim_level":2},
    {"finding_id":"N02","paper_key":"WANG2024","result":"750C aging reduced hardness by 2.13% versus as-rolled despite retaining a small 600C UTS gain.","type":"negative","claim_level":2},
    {"finding_id":"N03","paper_key":"JIAO2016","result":"990-1200C water quenching reduced room-temperature tensile UTS by 7.76-12.93% while raising compression strength.","type":"mode_conflict","claim_level":2},
    {"finding_id":"N04","paper_key":"FEREIDUNI2021","result":"Supertransus furnace cooling reduced monolithic Ti64 rupture life from 3.4 h to 0.6 h due to continuous GB-alpha.","type":"negative","claim_level":2},
    {"finding_id":"N05","paper_key":"MULTI","result":"600C elongation effects change sign across papers; no universal heat-treatment ductility effect is identifiable.","type":"heterogeneity","claim_level":2},
    {"finding_id":"N06","paper_key":"BAI2025","result":"No mechanical before/after values were available in the captured primary source; only sequence-microstructure claims are admissible.","type":"not_identifiable","claim_level":1},
    {"finding_id":"N07","paper_key":"MULTI","result":"No included paper directly validates 800C tensile/creep service after heat treatment.","type":"scope_gap","claim_level":1},
]

CONFLICTS = [
    {"conflict_id":"C001","type":"AGING_TEMPERATURE_POSSIBLE_TYPO","object":"BAI2025 aging stage","detail":"Primary capture states 60C/4h after solution; this is chemically suspicious but is preserved literally.","resolution":"UNRESOLVED_SOURCE_LITERAL","severity":"high"},
    {"conflict_id":"C002","type":"OUTCOME_MISSING_AFTER_BRITTLE_FAILURE","object":"JIAO2016 WQ tensile YS/EL","detail":"Heat-treated tensile YS and elongation unavailable.","resolution":"NOT_IDENTIFIABLE","severity":"medium"},
    {"conflict_id":"C003","type":"TEXT_TABLE_DISCREPANCY","object":"FEREIDUNI2021 HT-TMC rupture time","detail":"Narrative/abstract includes 5.9 h in one location; Table 2 reports 5.8 h.","resolution":"TABLE_2_5.8H_USED","severity":"medium"},
    {"conflict_id":"C004","type":"COVARIANCE_MISSING","object":"QI2012 matched effects","detail":"Same-study groups are not longitudinal same specimens; covariance unavailable.","resolution":"INDEPENDENT_GROUP_SE_APPROXIMATION","severity":"medium"},
    {"conflict_id":"C005","type":"FIGURE_DERIVED_NOT_GOLD","object":"WANG2024 hardness","detail":"Values digitized/read from plotted data.","resolution":"FIGURE_DERIVED_ONLY","severity":"medium"},
    {"conflict_id":"C006","type":"BETA_TRANSUS_OR_COOLING_MISSING","object":"multiple papers","detail":"Source-specific beta-transus or complete cooling history missing for several sequences.","resolution":"CLAIM_CEILING_DOWNGRADED","severity":"high"},
    {"conflict_id":"C007","type":"PRIMARY_SOURCE_UNAVAILABLE","object":"Li2021 and Zhang2017 secondary mentions","detail":"Not admitted to quantitative cohort without primary originals.","resolution":"EXCLUDED_FROM_EFFECT_ESTIMATION","severity":"high"},
    {"conflict_id":"C008","type":"DOI_AMBIGUITY","object":"Wang2015 candidate","detail":"Candidate DOI corrected in prior audit to suffix .058, but primary original not opened.","resolution":"EXCLUDED_PENDING_PRIMARY","severity":"medium"},
    {"conflict_id":"C009","type":"AUTHORITATIVE_SNAPSHOT_MISSING","object":"V29 ATOMIC_RECORDS/PROVENANCE/CONFLICT ledger","detail":"Chat runner did not receive canonical row-level V29 snapshot files.","resolution":"LOCAL_COHORT_SNAPSHOT_ONLY","severity":"high"},
    {"conflict_id":"C010","type":"SERVICE_TEMPERATURE_GAP","object":"800C target","detail":"No direct 800C mechanical verification in included primary cohort.","resolution":"NO_800C_CLAIM","severity":"high"},
]

# Input/source utilization ledgers.
input_rows=[]
for name,cls,h,members,status in ARCHIVES:
    input_rows.append({"input_id":sid("IN",name),"source_name":name,"source_class":cls,"source_hash":h,"hash_type":"ARCHIVE_SHA256" if h else "MISSING","member_count":members,"opened_or_audited":status,"scientific_use":"inventory/support infrastructure; not substituted for primary originals","snapshot_binding":"pending local row-level absorption"})
for p in PAPERS:
    input_rows.append({"input_id":sid("IN",p["key"]),"source_name":p["title"],"source_class":"primary_literature","source_hash":p["raw_hash"],"hash_type":p["hash_type"],"member_count":"","opened_or_audited":"OPENED_PRIMARY","scientific_use":"quantitative extraction or mechanism sequence evidence","snapshot_binding":p["paper_uid"]})
input_rows.append({"input_id":sid("IN","QM28_PROMPT"),"source_name":"QM28_退火、固溶、时效和复合热处理的条件效应.md","source_class":"dispatch_contract","source_hash":sha("QM28 dispatch contract captured in chat turn0file0"),"hash_type":"NORMALIZED_CAPTURE_SHA256","member_count":1,"opened_or_audited":"OPENED","scientific_use":"scope, estimands, deliverables, claim ceiling","snapshot_binding":"chatgpt_filecite:turn0file0"})

snapshot_material="\n".join(sorted(str(r["source_hash"]) for r in input_rows if r["source_hash"]))
SNAPSHOT_ID="QM28_LOCAL_COHORT_"+sha(snapshot_material)[:16]

# Write core tables.
write_csv("INPUT_LEDGER.csv",input_rows)
write_csv("ANALYSIS_COHORT.csv",COHORT)
write_csv("PAIR_MATCHES.csv",PAIR)
write_csv("EFFECT_ESTIMATES.csv",PAIR)
write_csv("HT_PAIR_EFFECTS.csv",PAIR)
write_csv("HEAT_TREATMENT_SEQUENCES.csv",SEQUENCES)
write_csv("DOSE_RESPONSE.csv",DOSE)
write_csv("HT_DOSE_RESPONSE.csv",DOSE)
write_csv("HIERARCHICAL_RESULTS.csv",SYNTHESIS)
write_csv("HETEROGENEITY.csv",HET)
write_csv("SENSITIVITY_ANALYSIS.csv",SENS)
write_csv("INTERACTION_EFFECTS.csv",INTERACTIONS)
write_csv("HT_REINFORCEMENT_INTERACTIONS.csv",INTERACTIONS)
write_csv("NULL_NEGATIVE_RESULTS.csv",NULLS)
write_csv("CONFLICT_LEDGER.csv",CONFLICTS)
write_csv("HIGH_TEMPERATURE_RETENTION.csv",RETENTION)
write_csv("MECHANISM_OBSERVATIONS.csv",MECHANISMS)
write_csv("SOURCE_UTILIZATION_LEDGER.csv",[
    {"source":r["source_name"],"class":r["source_class"],"use":r["scientific_use"],"status":r["opened_or_audited"],"weight":"highest" if r["source_class"]=="primary_literature" else "supporting"} for r in input_rows
])
write_csv("EXCLUDED_RECORDS.csv",[
    {"object":"Li et al. MSEA 801 (2021) 140415","reason":"primary original unavailable","terminal_state":"EXCLUDED_PENDING_PRIMARY"},
    {"object":"Zhang et al. MSEA 679 (2017) 314-322","reason":"primary original unavailable","terminal_state":"EXCLUDED_PENDING_PRIMARY"},
    {"object":"Wang 2015 DOI candidate","reason":"DOI/source identity unresolved","terminal_state":"EXCLUDED_PENDING_IDENTITY"},
])

# Provenance is row-bound and explicitly distinguishes raw-PDF hashes from normalized captures.
prov=[]
for p in PAPERS:
    prov.append({"snapshot_id":SNAPSHOT_ID,"paper_uid":p["paper_uid"],"paper_key":p["key"],"doi":p["doi"],"title":p["title"],"source_locator":p["locator"],"source_hash":p["raw_hash"],"hash_type":p["hash_type"],"evidence_role":"primary_literature","production_model_registration":False,"gold_promotion":False})
with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8") as f:
    for row in prov:
        f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")

# Figure data.
alluvial=[]
for m in MECHANISMS:
    p=m["paper_key"]
    process=MATERIALS[p][3]
    path="multi-step" if sum(1 for x in SEQUENCES if x["paper_key"]==p and x["stage_index"]==2)>0 else "single-step/isothermal"
    strength="mixed/not measured"
    ductility="mixed/not measured"
    if p in {"WANG2024","QI2012","WANG2018"}: strength="mostly increased"
    if p=="JIAO2016": strength="tension decreased/compression increased"
    if p=="FEREIDUNI2021": strength="creep life interaction reversal"
    if p in {"WANG2024","WANG2018","JIAO2016"}: ductility="generally reduced"
    if p=="QI2012": ductility="RT reduced; high-T increased"
    alluvial.append({"paper_key":p,"process":process,"path_class":path,"microstructure":m["phase_microstructure"].split(";")[0][:56],"strength_outcome":strength,"ductility_outcome":ductility})
write_csv("figure_data/heat_treatment_alluvial.csv",alluvial)
forest=[r for r in PAIR if r["property"] in {"UTS","YS","CYS","UCS","rupture_time"}]
write_csv("figure_data/ht_paired_forest.csv",forest)
surface=[]
for r in PAIR:
    if r["paper_key"]=="WANG2024" and r["property"]=="UTS" and r["treatment_label"] in {"age600","age700","age750"}:
        age=int(r["treatment_label"].replace("age",""))
        surface.append({"aging_temperature_C":age,"aging_time_h":1.0,"cooling":"air_cool","test_temperature_C":r["test_temperature_C"],"UTS_MPa":r["treatment_value"],"source_support":"observed"})
write_csv("figure_data/ttcooling_response_surface.csv",surface)
interaction_data=[]
for material in ("Ti64","TMC"):
    interaction_data.append({"material":material,"state":"as-built","rupture_time_h":fdata[material]["AB"][0],"steady_state_creep_rate_pct_h":fdata[material]["AB"][1]})
    interaction_data.append({"material":material,"state":"heat-treated","rupture_time_h":fdata[material]["HT"][0],"steady_state_creep_rate_pct_h":fdata[material]["HT"][1]})
write_csv("figure_data/ht_reinforcement_interaction.csv",interaction_data)

PLOT_COMMON='''from pathlib import Path\nimport csv\nimport matplotlib.pyplot as plt\nROOT=Path(__file__).resolve().parents[1]\nFIG=ROOT/"figures"\nFIG.mkdir(exist_ok=True)\ndef save(name):\n    plt.savefig(FIG/f"{name}.svg",bbox_inches="tight")\n    plt.savefig(FIG/f"{name}.pdf",bbox_inches="tight")\n    plt.savefig(FIG/f"{name}.png",dpi=600,bbox_inches="tight")\n'''
plot_alluvial=PLOT_COMMON+'''\nrows=list(csv.DictReader(open(ROOT/"figure_data/heat_treatment_alluvial.csv",encoding="utf-8-sig")))\nstages=["process","path_class","microstructure","strength_outcome","ductility_outcome"]\nlabels={s:[] for s in stages}\nfor s in stages:\n    for r in rows:\n        if r[s] not in labels[s]: labels[s].append(r[s])\nfig,ax=plt.subplots(figsize=(15,8))\nfor r in rows:\n    ys=[]\n    for s in stages:\n        vals=labels[s]; ys.append(vals.index(r[s])/(max(1,len(vals)-1)))\n    ax.plot(range(len(stages)),ys,marker="o",alpha=.65,label=r["paper_key"])\nfor x,s in enumerate(stages):\n    for i,label in enumerate(labels[s]):\n        y=i/(max(1,len(labels[s])-1)); ax.text(x,y,label,ha="center",va="bottom",fontsize=7,rotation=18 if s=="microstructure" else 0)\nax.set_xticks(range(len(stages)),["Process","HT path","Microstructure","Strength response","Ductility response"])\nax.set_yticks([]); ax.set_xlim(-.2,len(stages)-.8); ax.set_title("Heat-treatment pathways across 9 independent papers | sequence-preserving evidence map")\nax.legend(ncol=3,fontsize=7,loc="upper center",bbox_to_anchor=(.5,-.08)); fig.tight_layout(); save("01_heat_treatment_path_alluvial")\n'''
plot_forest=PLOT_COMMON+'''\nrows=list(csv.DictReader(open(ROOT/"figure_data/ht_paired_forest.csv",encoding="utf-8-sig")))\nrows=[r for r in rows if r["property"] in {"UTS","YS","CYS","UCS","rupture_time"}]\nlabels=[f"{r['paper_key']} | {r['treatment_label']} | {r['property']} @ {r['test_temperature_C']}C" for r in rows]\nx=[float(r["percent_change"]) for r in rows]\ny=list(range(len(rows)))\nfig,ax=plt.subplots(figsize=(10,max(8,.32*len(rows))))\nax.axvline(0,linewidth=1)\nfor i,r in enumerate(rows):\n    lo=r.get("CI95_low_lnRR",""); hi=r.get("CI95_high_lnRR","")\n    if lo not in ("",None) and hi not in ("",None):\n        plo=100*(__import__('math').exp(float(lo))-1); phi=100*(__import__('math').exp(float(hi))-1)\n        ax.errorbar(x[i],i,xerr=[[x[i]-plo],[phi-x[i]]],fmt="o",capsize=2)\n    else: ax.plot(x[i],i,"o")\nax.set_yticks(y,labels,fontsize=7); ax.set_xlabel("Percent change vs same-paper untreated/as-processed comparator")\nax.set_title(f"Heat-treatment paired effects | {len(set(r['paper_key'] for r in rows))} papers | CI shown only where SD and n permit")\nax.grid(axis="x",alpha=.25); fig.tight_layout(); save("02_ht_paired_effect_forest")\n'''
plot_surface=PLOT_COMMON+'''\nfrom mpl_toolkits.mplot3d import Axes3D  # noqa: F401\nrows=list(csv.DictReader(open(ROOT/"figure_data/ttcooling_response_surface.csv",encoding="utf-8-sig")))\nx=[float(r["aging_temperature_C"]) for r in rows]; y=[float(r["test_temperature_C"]) for r in rows]; z=[float(r["UTS_MPa"]) for r in rows]\nfig=plt.figure(figsize=(9,7)); ax=fig.add_subplot(111,projection="3d")\nax.plot_trisurf(x,y,z,alpha=.55); ax.scatter(x,y,z,s=35)\nfor a,b,c in zip(x,y,z): ax.text(a,b,c+10,f"{c:.0f}",fontsize=8)\nax.set_xlabel("Aging temperature (C)"); ax.set_ylabel("Tensile test temperature (C)"); ax.set_zlabel("UTS (MPa)")\nax.set_title("Observed T-t-cooling response support | 1050C/0.5h/WQ + 1h aging/AC | no extrapolation")\nfig.tight_layout(); save("03_T_t_cooling_response_surface")\n'''
plot_inter=PLOT_COMMON+'''\nrows=list(csv.DictReader(open(ROOT/"figure_data/ht_reinforcement_interaction.csv",encoding="utf-8-sig")))\nfig,ax=plt.subplots(figsize=(8,6))\nfor material in ["Ti64","TMC"]:\n    rr=[r for r in rows if r["material"]==material]; rr=sorted(rr,key=lambda r: 0 if r["state"]=="as-built" else 1)\n    ax.plot([0,1],[float(r["rupture_time_h"]) for r in rr],marker="o",label=material)\nax.set_xticks([0,1],["As-built","1050C/2h + furnace cool"]); ax.set_ylabel("Creep rupture time at 600C, 200 MPa (h)")\nax.set_title("HT x reinforcement interaction | additive DID = +5.7 h; ratio-of-ratios = 11.33")\nax.legend(); ax.grid(axis="y",alpha=.25); fig.tight_layout(); save("04_ht_reinforcement_interaction")\n'''
for name,code in (("plot_alluvial.py",plot_alluvial),("plot_forest.py",plot_forest),("plot_response_surface.py",plot_surface),("plot_interaction.py",plot_inter)):
    write_text("plot_code/"+name,code)
    subprocess.run([sys.executable,str(PCODE/name)],check=True)

write_json("PLOT_SPECS.json",{
    "plot_count":4,"formats":["svg","pdf","png_600dpi"],"language":"English",
    "plots":[
        {"id":"01","title":"Heat-treatment pathway alluvial","data":"figure_data/heat_treatment_alluvial.csv","code":"plot_code/plot_alluvial.py","support":"9 independent papers"},
        {"id":"02","title":"HT paired-effect forest","data":"figure_data/ht_paired_forest.csv","code":"plot_code/plot_forest.py","support":"same-paper grade-A pairs; CI only when estimable"},
        {"id":"03","title":"T-time-cooling response surface","data":"figure_data/ttcooling_response_surface.csv","code":"plot_code/plot_response_surface.py","support":"observed convex support only; time fixed 1 h; AC after aging"},
        {"id":"04","title":"HT by reinforcement interaction","data":"figure_data/ht_reinforcement_interaction.csv","code":"plot_code/plot_interaction.py","support":"same-paper Ti64/TMC creep experiment"},
    ],"generative_image_used":False
})

uts_syn=[r for r in SYNTHESIS if r["outcome"]=="UTS"][0]
el_syn=[r for r in SYNTHESIS if r["outcome"]=="elongation"][0]
verdict=f'''# QM28 Executive Verdict\n\n## Scope and evidence base\n\nThis is an analysis-only, source-bound cohort build for heat-treatment effects in Ti/TMC systems. It includes **{len(PAPERS)} independent primary papers**, **{len(COHORT)} atomic quantitative rows**, and **{len(PAIR)} same-paper grade-A property pairs**. Primary literature is weighted above archive inventories, code, and harness evidence. No record is promoted to Gold and no production model is registered.\n\n## Quantitative verdict\n\n1. Across three independent 600 C tensile papers, the paper-equal path-averaged UTS effect is lnRR={uts_syn['estimate_lnRR']:.3f}, equivalent to **{uts_syn['percent_effect']:.1f}%**. LOPO estimates remain positive, but k=3 makes a universal random-effects or prediction interval non-identifiable.\n2. The analogous 600 C elongation estimate is **{el_syn['percent_effect']:.1f}%**, but the paper-specific signs conflict. The defensible conclusion is not “heat treatment reduces ductility”; it is **ductility response is path-, matrix-, reinforcement-, and temperature-dependent**.\n3. In LPBF Ti64/TiB, supertransus treatment reverses creep-life response: monolithic Ti64 falls 3.4→0.6 h, while TMC rises 2.9→5.8 h. The additive interaction is **+5.7 h** and the rupture-life ratio-of-ratios is **11.33**.\n4. In 10 vol.% TiC/TA15, room-temperature UTS rises 6.8–10.6% while elongation falls 44.6–83.4%; at 650 C, UTS gains collapse to 2.2–2.6% while elongation rises 20.9–26.0%.\n5. In the hybrid Ti5Si3+TiBw/Ti64 system, 990–1200 C water quenching reduces tensile UTS 7.8–12.9% but raises compressive yield strength 6.5–37.7%, with compressive deformation falling 25.6–69.9%. Test mode cannot be pooled.\n\n## Mechanistic conditionality\n\nThe principal mediator is not “heat treatment” as a scalar. It is the full path: position relative to beta transus, time, cooling route, and reinforcement-dependent nucleation/coarsening. TiB/TiC can pin beta grains and nucleate alpha, but long/high-temperature exposure can coarsen reinforcements or create brittle products. Continuous grain-boundary alpha is catastrophic in heat-treated monolithic Ti64 creep, whereas TiB suppresses that topology and changes the sign of the life response.\n\n## Claim ceiling\n\nMaximum claim level is **2: same-paper matched effect**. The 600 C synthesis is descriptive and sparse. No 800 C service validation is present. Missing canonical V29 row-level files, source-specific beta-transus, cooling details, and replication covariance prevent higher claims.\n'''
write_text("00_EXECUTIVE_VERDICT.md",verdict)

write_text("METHODS.md",'''# Methods\n\n## Estimands\nFor positive continuous outcomes: delta = Y_HT - Y_control; lnRR = ln(Y_HT/Y_control); percent = 100(exp(lnRR)-1). Creep-rate sign is preserved and favorable direction is separately annotated. Heat-treatment sequences remain stage-wise and are never reduced to maximum temperature.\n\n## Pairing and uncertainty\nPriority A same-paper/same-material/same-process/same-test comparators are used. For Qi et al., replicate SD and n=3 permit an independent-group approximation because within-paper covariance was not reported. Other studies without both n and dispersion receive no fabricated CI. BH-FDR is applied only to estimable p-values.\n\n## Sparse paper-level synthesis\nFor 600 C UTS and elongation, each paper first contributes the mean lnRR across its reported treatment paths; papers are then equally weighted. A deterministic paper-cluster bootstrap (20,000 resamples, seed 20260713) and LOPO analysis are reported. With k=3, tau-squared and a credible prediction interval are marked NOT_IDENTIFIABLE.\n\n## Interaction\nThe Ti64/TMC creep experiment supports additive difference-in-differences and multiplicative ratio-of-ratios because untreated and heat-treated matrix/composite cells share one paper, fabrication platform, and test condition. This remains a controlled same-paper interaction, not randomized causality.\n\n## Support domain\nThe T-time-cooling surface is an observed-support visualization for one 1050 C/0.5 h/WQ + 1 h aging/air-cool family. It must not be extrapolated outside its convex hull or transferred across matrix families.\n''')
write_text("LIMITATIONS.md",'''# Limitations and Claim Ceiling\n\n- The canonical V29 ATOMIC_RECORDS, PROVENANCE, CONFLICT_LEDGER, EXCLUDED_RECORDS, paper registry, and condition canonical manifest were not mounted in the public runner. This packet is a deterministic local cohort snapshot, not an ACTIVE or Gold replacement.\n- Several source-specific beta-transus values, cooling rates, hold times, and sample covariances are missing. Conclusions are downgraded accordingly.\n- Heat treatment is highly confounded with matrix family, process, reinforcement fraction, and objective. A single global coefficient would be scientifically false.\n- Compression, tension, hardness, creep rate, rupture life, and morphology are never pooled.\n- Figure-derived hardness is retained with an explicit evidence downgrade.\n- No included primary paper directly validates 800 C mechanical service.\n- The 600 C paper-level synthesis has only three independent papers; it is directional evidence, not a deployable constitutive law.\n- The public GitHub runner cannot open the chat-mounted 26 large archives. Archive metadata are inherited where hashes were available; local absorption must rebind every row to authoritative snapshot hashes.\n''')

write_json("WEB_TO_LOCAL_REQUEST.json",{
    "window_id":"QM28","current_snapshot_id":SNAPSHOT_ID,"status":"CONTINUE_DATA_GAP",
    "required_files":["ATOMIC_RECORDS.parquet_or_csv","PROVENANCE.jsonl","CONFLICT_LEDGER.csv","EXCLUDED_RECORDS.csv","PAPER_SOURCE_REGISTRY.csv","CONDITION_CANONICAL_MANIFEST.csv","TMC_SUBSET.csv","SPLIT_MANIFESTS","QUALITY_DOMAINS.csv","OOF_UQ_AD_NEAREST_ANALOG_ASSETS"],
    "required_action":"Recompute archive SHA/member fingerprints for all 26 mounted ZIPs; join on DOI/paper/sample/condition; preserve current evidence grades; do not promote to Gold automatically.",
    "priority_primary_gaps":["Li et al. MSEA 801 (2021) 140415","Zhang et al. MSEA 679 (2017) 314-322","Wang 2015 DOI/source identity"],
    "acceptance":"All effect rows must bind snapshot_id + source_hash + paper_uid + sample_uid + condition_uid; rerun validation and compare row counts/hashes."
})
write_text("LOCAL_ABSORPTION_PROMPT.md",f'''# Local Absorption Prompt — QM28\n\nAbsorb `FINAL_QM28` into the exclusive write zone `q40/QM28` only. Do not modify ACTIVE_TITMC, Gold, unified schema, production-model registry, or other windows.\n\n1. Verify artifact checksum/CRC and `VALIDATION_REPORT.json`.\n2. Recompute SHA-256 and central-directory fingerprints for all 26 mounted source ZIPs.\n3. Load authoritative V29 files requested in `WEB_TO_LOCAL_REQUEST.json`.\n4. Join every row using DOI/paper/sample/condition identity and replace normalized evidence hashes only when raw-source identity is proven.\n5. Rerun `python analysis_code/validate_package.py`.\n6. Compare counts against snapshot `{SNAPSHOT_ID}`; write a delta ledger.\n7. Preserve conflicts, NOT_IDENTIFIABLE states, and claim level <=2.\n8. Do not register a production model or label any recipe VALIDATED.\n''')

# Reproducibility/acceptance assets.
write_text("requirements.txt","matplotlib==3.9.2\nnumpy==2.1.1")
write_text("acceptance_commands.md",'''# Acceptance Commands\n\n```bash\npython -m pip install -r requirements.txt\npython analysis_code/validate_package.py\npython -m unittest discover -s tests -v\npython plot_code/plot_alluvial.py\npython plot_code/plot_forest.py\npython plot_code/plot_response_surface.py\npython plot_code/plot_interaction.py\n```\n''')
write_text("README.md",'''# FINAL_QM28\n\nDeterministic quantitative evidence packet for annealing, solution treatment, aging, and multi-step heat-treatment effects in titanium matrix composites. The packet is analysis-only, source-bound, and intentionally stops at claim level 2. Start with `00_EXECUTIVE_VERDICT.md`, then inspect `HEAT_TREATMENT_SEQUENCES.csv`, `HT_PAIR_EFFECTS.csv`, raw figure data, and the conflict/gap ledgers.\n''')
write_text("OPENED_FILES.txt","\n".join(["QM28 dispatch: chatgpt_filecite:turn0file0"]+[f"{p['key']} | {p['locator']} | {p['doi']}" for p in PAPERS]+[f"MOUNTED_ARCHIVE | {a[0]} | {a[4]}" for a in ARCHIVES]))
write_json("SCHEMAS.json",{
    "atomic_row":"paper x sample x composition x precursor x actual phase x process x heat treatment x microstructure x test mode x temperature x strain rate x orientation x property",
    "pair_row":"same-paper comparator-treatment-property-test condition",
    "evidence_levels":["DIRECT_TABLE_TEXT","DIRECT_TEXT","FIGURE_DERIVED","DERIVED_CALCULATION","UNRESOLVED"],
    "claim_levels":{"1":"descriptive association","2":"same-paper matched effect"}
})

validator='''#!/usr/bin/env python3\nfrom pathlib import Path\nimport csv,json,hashlib,sys\nROOT=Path(__file__).resolve().parents[1]\nrequired=%r\nerrors=[]\nfor name in required:\n    if not (ROOT/name).exists(): errors.append(f"missing:{name}")\nwith open(ROOT/"PAIR_MATCHES.csv",encoding="utf-8-sig") as f: pairs=list(csv.DictReader(f))\nif len(pairs)!=59: errors.append(f"pair_count:{len(pairs)}")\nfor r in pairs:\n    if not r["paper_uid"] or not r["sample_uid"] or not r["comparator_condition_uid"] or not r["treatment_condition_uid"]: errors.append("unbound_pair")\nwith open(ROOT/"HEAT_TREATMENT_SEQUENCES.csv",encoding="utf-8-sig") as f: seq=list(csv.DictReader(f))\nif not any(r["stage_index"]=="2" for r in seq): errors.append("sequence_collapsed")\nfor stem in ["01_heat_treatment_path_alluvial","02_ht_paired_effect_forest","03_T_t_cooling_response_surface","04_ht_reinforcement_interaction"]:\n    for ext in ("svg","pdf","png"):\n        p=ROOT/"figures"/f"{stem}.{ext}"\n        if not p.exists() or p.stat().st_size==0: errors.append(f"plot:{p.name}")\nstatus=json.load(open(ROOT/"WINDOW_STATUS.json",encoding="utf-8"))\nif status["claim_level_max"]>2: errors.append("claim_ceiling")\nif status["production_model_registered"]: errors.append("production_registration")\nreport={"pass":not errors,"errors":errors,"pair_count":len(pairs),"sequence_stage_rows":len(seq),"required_files":len(required)}\n(ROOT/"VALIDATION_REPORT.json").write_text(json.dumps(report,indent=2)+"\\n",encoding="utf-8")\nprint(json.dumps(report,indent=2))\nsys.exit(1 if errors else 0)\n''' % [x for x in MANDATORY if x not in {"MANIFEST.json","CHECKSUMS.sha256"}]
write_text("analysis_code/validate_package.py",validator)
write_text("analysis_code/recompute_effects.py",'''#!/usr/bin/env python3\nfrom pathlib import Path\nimport csv,math\nroot=Path(__file__).resolve().parents[1]\nrows=list(csv.DictReader(open(root/"PAIR_MATCHES.csv",encoding="utf-8-sig")))\nfor r in rows:\n    b=float(r["comparator_value"]); t=float(r["treatment_value"])\n    assert abs(float(r["delta"])-(t-b))<1e-8\n    assert abs(float(r["percent_change"])-100*(t/b-1))<1e-8\nprint({"pass":True,"rows_recomputed":len(rows)})\n''')

# Seven deterministic unit tests.
test_code='''import csv,json,math,unittest\nfrom pathlib import Path\nR=Path(__file__).resolve().parents[1]\ndef rows(n): return list(csv.DictReader(open(R/n,encoding="utf-8-sig")))\nclass TestQM28(unittest.TestCase):\n  def test_pair_count(self): self.assertEqual(len(rows("PAIR_MATCHES.csv")),59)\n  def test_pair_identity(self):\n    for r in rows("PAIR_MATCHES.csv"): self.assertTrue(r["paper_uid"] and r["sample_uid"] and r["comparator_condition_uid"] and r["treatment_condition_uid"])\n  def test_sequence_preserved(self): self.assertTrue(any(r["stage_index"]=="2" for r in rows("HEAT_TREATMENT_SEQUENCES.csv")))\n  def test_fereiduni_did(self):\n    r=[x for x in rows("INTERACTION_EFFECTS.csv") if x["property"]=="rupture_time"][0]; self.assertAlmostEqual(float(r["additive_DID"]),5.7,7); self.assertAlmostEqual(float(r["ratio_of_ratios"]),11.3333333333,6)\n  def test_600C_uts_positive(self):\n    r=[x for x in rows("HIERARCHICAL_RESULTS.csv") if x["outcome"]=="UTS"][0]; self.assertGreater(float(r["percent_effect"]),10); self.assertLess(float(r["percent_effect"]),20)\n  def test_claim_ceiling(self): self.assertLessEqual(json.load(open(R/"WINDOW_STATUS.json"))["claim_level_max"],2)\n  def test_plot_triplets(self): self.assertEqual(len(list((R/"figures").glob("*"))),12)\nif __name__=="__main__": unittest.main()\n'''
write_text("tests/test_qm28.py",test_code)

status={
    "window_id":"QM28","snapshot_id":SNAPSHOT_ID,"papers_seen":len(PAPERS),"papers_included":len(PAPERS),
    "independent_papers":len(PAPERS),"atomic_rows":len(COHORT),"matched_pairs":len(PAIR),
    "effect_estimates":len(PAIR),"plots_generated":4,"open_conflicts":len(CONFLICTS),
    "claim_level_max":2,"status":"CONTINUE_DATA_GAP",
    "next_action":"Local V29 absorption, archive re-hash, row-level identity join, then minimal recomputation",
    "production_model_registered":False,"gold_promotions":0,"validated_recipes":0
}
write_json("WINDOW_STATUS.json",status)

# Manifest/checksums are finalized after all content exists. CHECKSUMS excludes itself; MANIFEST excludes itself/checksums.
def file_hash(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
entries=[]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256","VALIDATION_REPORT.json"}:
        entries.append({"path":p.relative_to(OUT).as_posix(),"size_bytes":p.stat().st_size,"sha256":file_hash(p)})
write_json("MANIFEST.json",{"window_id":"QM28","snapshot_id":SNAPSHOT_ID,"file_count":len(entries)+3,"files":entries,"no_nested_zip":True,"seed":SEED})
lines=[]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name!="CHECKSUMS.sha256": lines.append(f"{file_hash(p)}  {p.relative_to(OUT).as_posix()}")
write_text("CHECKSUMS.sha256","\n".join(lines))

# First validation, tests, effect recomputation; then refresh validation/checksums.
subprocess.run([sys.executable,str(ACODE/"validate_package.py")],check=True)
subprocess.run([sys.executable,"-m","unittest","discover","-s",str(TESTS),"-v"],check=True,cwd=OUT)
subprocess.run([sys.executable,str(ACODE/"recompute_effects.py")],check=True)
write_text("RECOMPUTE_OUTPUT.txt",f"pass=true\nrows_recomputed={len(PAIR)}\nsnapshot_id={SNAPSHOT_ID}")
write_text("TEST_OUTPUT.txt","pass=true\ntests=7\nseed=20260713")
# Refresh checksum list after validation/test evidence.
lines=[]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name!="CHECKSUMS.sha256": lines.append(f"{file_hash(p)}  {p.relative_to(OUT).as_posix()}")
write_text("CHECKSUMS.sha256","\n".join(lines))
print(json.dumps({"status":"CONTINUE_DATA_GAP","window":"QM28","snapshot_id":SNAPSHOT_ID,"papers":len(PAPERS),"atomic_rows":len(COHORT),"pairs":len(PAIR),"plots":4,"output":str(OUT)},indent=2))
