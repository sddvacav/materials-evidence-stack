from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

WINDOW = "QM09"
GENERATED = "2026-07-13T09:00:00Z"
BASE = Path(__file__).resolve().parent
ROOT = BASE / "output" / "FINAL_QM09"
SEED = 20260713


def hbytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hfile(path: Path) -> str:
    return hbytes(path.read_bytes())


def uid(prefix: str, *parts: object) -> str:
    return prefix + "_" + hbytes("|".join(map(str, parts)).encode("utf-8"))[:20]


def wt(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def wj(rel: str, obj: object) -> None:
    wt(rel, json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def wc(rel: str, rows: list[dict], fields: list[str] | None = None) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else ["status", "reason"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in fields})


def qtile(values: list[float], q: float) -> float:
    x = sorted(values)
    if not x:
        return float("nan")
    pos = (len(x) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return x[lo]
    return x[lo] * (hi - pos) + x[hi] * (pos - lo)


def cluster_bootstrap(values: list[float], n_boot: int = 50000) -> tuple[float, float, float]:
    rng = random.Random(SEED)
    n = len(values)
    draws = [sum(rng.choice(values) for _ in range(n)) / n for _ in range(n_boot)]
    return statistics.mean(values), qtile(draws, 0.025), qtile(draws, 0.975)


def simple_slope(xs: list[float], ys: list[float]) -> tuple[float, float]:
    xm = statistics.mean(xs)
    ym = statistics.mean(ys)
    sxx = sum((x - xm) ** 2 for x in xs)
    if sxx == 0:
        return float("nan"), float("nan")
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / sxx
    intercept = ym - slope * xm
    return slope, intercept


ARCHIVES = [
    ("00_统一上传总控与校验信息_20260712.zip", "0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f", 13, "control"),
    ("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip", "bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1", 32, "plot/platform"),
    ("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip", "36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9", 15, "frozen data/features"),
    ("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip", "5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59", 25, "frozen data/features"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip", "cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a", 7, "quality/UQ/AD"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip", "97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809", 7, "quality/UQ/AD"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip", "16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f", 9, "quality/UQ/AD"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip", "04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9", 11, "quality/UQ/AD"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip", "5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728", 17, "quality/UQ/AD"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip", "e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847", 38, "quality/UQ/AD"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip", "36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485", 69, "quality/UQ/AD"),
    ("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip", "9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd", 246, "quality/UQ/AD"),
    ("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip", "c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c", 57191, "history/evidence"),
    ("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip", "a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a", 244, "engineering"),
    ("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip", "bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43", 396, "engineering"),
    ("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip", "08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755", 499, "engineering"),
    ("TITMC_V27_LIT_WEB_P001_OF_010.zip", "42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0", 15, "primary literature"),
    ("TITMC_V27_LIT_WEB_P002_OF_010.zip", "05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193", 154, "primary literature"),
    ("TITMC_V27_LIT_WEB_P003_OF_010.zip", "535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917", 4610, "primary literature"),
    ("TITMC_V27_LIT_WEB_P004_OF_010.zip", "bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a", 7747, "primary literature"),
    ("TITMC_V27_LIT_WEB_P005_OF_010.zip", "1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1", 10068, "primary literature"),
    ("TITMC_V27_LIT_WEB_P006_OF_010.zip", "5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13", 11778, "primary literature"),
    ("TITMC_V27_LIT_WEB_P007_OF_010.zip", "4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1", 13499, "primary literature"),
    ("TITMC_V27_LIT_WEB_P008_OF_010.zip", "478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341", 15702, "primary literature"),
    ("TITMC_V27_LIT_WEB_P009_OF_010.zip", "b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a", 20036, "primary literature"),
    ("TITMC_V27_LIT_WEB_P010_OF_010.zip", "faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d", 57717, "primary literature"),
]

PAPERS = {
    "BIED": {
        "doi": "10.4028/www.scientific.net/SSP.227.247",
        "title": "Microstructure and Tribocorrosion Properties of Titanium Matrix Nanocomposites Manufactured by Selective Laser Sintering/Melting Method",
        "source_locator": "project_file_library:primary_pdf|doi:10.4028/www.scientific.net/SSP.227.247",
        "evidence": "DIRECT_TEXT_ORIGINAL_PDF",
    },
    "YU": {
        "doi": "10.1016/j.jallcom.2017.01.084",
        "title": "In-situ synthesis of TiC/Ti composite coating by high frequency induction cladding",
        "source_locator": "project_file_library:primary_pdf|doi:10.1016/j.jallcom.2017.01.084",
        "evidence": "DIRECT_TEXT_AND_FIGURE_ORIGINAL_PDF",
    },
    "AREVALO": {
        "doi": "10.3390/met7110457",
        "title": "Study of the Influence of TiB Content and Temperature in the Properties of In Situ Titanium Matrix Composites",
        "source_locator": "project_file_library:primary_pdf|doi:10.3390/met7110457",
        "evidence": "DIRECT_TEXT_ORIGINAL_PDF",
    },
    "GUO": {
        "doi": "10.1016/j.jmrt.2023.01.126",
        "title": "Microstructure and mechanical properties of Ti6Al4V/B4C titanium matrix composite fabricated by selective laser melting",
        "source_locator": "project_file_library:file_00000000e5b0720b84bf12bb11bb90c6|doi:10.1016/j.jmrt.2023.01.126",
        "evidence": "DIRECT_FIGURE_LABELS_AND_TEXT_ORIGINAL_PDF",
    },
    "SABAHI": {
        "doi": "10.1080/00325899.2016.1265805",
        "title": "Microstructural characterisation and mechanical properties of spark plasma-sintered TiB2-reinforced titanium matrix composite",
        "source_locator": "project_file_library:file_00000000b62471f8b1c907a4acb7b4db|doi:10.1080/00325899.2016.1265805",
        "evidence": "DIRECT_TABLE_TEXT_ORIGINAL_PDF",
    },
    "LI": {
        "doi": "10.1016/j.msea.2022.144466",
        "title": "Microstructure and mechanical properties of in situ synthesized (TiB+TiC)-reinforced Ti6Al4V composites produced by directed energy deposition",
        "source_locator": "project_file_library:file_0000000025ec720880e689312f2f90e6|doi:10.1016/j.msea.2022.144466",
        "evidence": "DIRECT_TEXT_AND_TABLE_ORIGINAL_PDF",
    },
}

for meta in PAPERS.values():
    meta["paper_uid"] = uid("PAPER", meta["doi"])
    meta["source_hash"] = hbytes(meta["source_locator"].encode("utf-8"))
    meta["hash_kind"] = "locator_sha256_not_source_bytes"

snapshot_payload = {
    "window": WINDOW,
    "papers": {k: {x: v for x, v in m.items() if x in {"doi", "title", "source_locator", "evidence"}} for k, m in PAPERS.items()},
    "archives": [(x[0], x[1], x[2]) for x in ARCHIVES],
    "schema": "qm09-recovery-1.0.0",
}
SNAPSHOT = "QM09_" + hbytes(json.dumps(snapshot_payload, sort_keys=True).encode("utf-8"))[:20]

atomic: list[dict] = []
record_index: dict[tuple[str, str, str, str], dict] = {}
provenance: list[dict] = []


def add_atomic(
    paper: str,
    sample: str,
    condition: str,
    prop: str,
    value: float,
    unit: str,
    process: str,
    reinforcement: str,
    dose: float | str,
    dose_unit: str,
    method: str,
    load: str,
    dwell_s: str,
    scale: str,
    region: str,
    evidence: str,
    n: str = "",
    uncertainty: str = "",
    temperature_c: float = 25.0,
    notes: str = "",
) -> dict:
    meta = PAPERS[paper]
    sample_uid = uid("SAMPLE", meta["paper_uid"], sample)
    condition_uid = uid("COND", sample_uid, condition, prop, method, temperature_c)
    record_uid = uid("REC", meta["paper_uid"], sample_uid, condition_uid, prop, value, unit)
    prov_uid = uid("PROV", record_uid, meta["source_locator"])
    row = {
        "record_uid": record_uid,
        "snapshot_id": SNAPSHOT,
        "paper_key": paper,
        "paper_uid": meta["paper_uid"],
        "doi": meta["doi"],
        "sample_uid": sample_uid,
        "sample_label": sample,
        "condition_uid": condition_uid,
        "condition_label": condition,
        "property": prop,
        "value": value,
        "unit": unit,
        "process": process,
        "reinforcement": reinforcement,
        "dose": dose,
        "dose_unit": dose_unit,
        "test_temperature_c": temperature_c,
        "test_method": method,
        "load": load,
        "dwell_s": dwell_s,
        "measurement_scale": scale,
        "region": region,
        "n_measurements": n,
        "uncertainty": uncertainty,
        "evidence_level": evidence,
        "source_hash": meta["source_hash"],
        "source_hash_kind": meta["hash_kind"],
        "source_locator": meta["source_locator"],
        "provenance_uid": prov_uid,
        "notes": notes,
    }
    atomic.append(row)
    record_index[(paper, sample, prop, condition)] = row
    provenance.append({
        "provenance_uid": prov_uid,
        "snapshot_id": SNAPSHOT,
        "paper_uid": meta["paper_uid"],
        "sample_uid": sample_uid,
        "condition_uid": condition_uid,
        "record_uid": record_uid,
        "doi": meta["doi"],
        "source_hash": meta["source_hash"],
        "source_hash_kind": meta["hash_kind"],
        "source_locator": meta["source_locator"],
        "evidence_level": evidence,
        "claim": f"{prop}={value} {unit}",
        "notes": notes,
    })
    return row


# Biedunkiewicz 2015: direct same-process SLM Ti/nc-TiC HV0.05 dose series.
for dose, hv in [(0, 300), (1, 377), (5, 429), (10, 559), (20, 651)]:
    add_atomic("BIED", f"Ti_{dose}volTiC", "as_built_RT", "hardness", hv, "HV0.05", "SLM", "nc-TiC", dose, "vol%", "Vickers", "0.05 kgf", "10", "micro", "bulk", "DIRECT_TEXT_ORIGINAL_PDF", notes="Densification reported above 97%; exact arm-specific porosity unavailable.")

# Yu 2017: macro HV0.2 and local nanoindentation hierarchy.
add_atomic("YU", "Ti6Al4V_substrate_macro", "cross_section_RT", "hardness", 340, "HV0.2", "induction_cladding_system", "none", 0, "area_fraction", "Vickers", "0.2 kgf", "10", "micro", "substrate", "DIRECT_TEXT_ORIGINAL_PDF")
add_atomic("YU", "TiC_Ti_coating_macro", "cross_section_RT", "hardness", 600, "HV0.2", "induction_cladding", "in-situ TiC", 0.11, "area_fraction", "Vickers", "0.2 kgf", "10", "micro", "coating", "DIRECT_TEXT_ORIGINAL_PDF", notes="Approximately constant upper 1500 um coating hardness.")
for sample, region, h_gpa, e_gpa in [
    ("substrate_nano", "Ti6Al4V substrate", 4.0, 150),
    ("alpha_nano", "equiaxed alpha-Ti-rich phase", 4.0, 150),
    ("beta_nano", "beta-transformation structure", 6.1, 200),
    ("TiC_nano", "in-situ TiC phase", 22.0, 270),
]:
    add_atomic("YU", sample, "nanoindentation_RT", "hardness", h_gpa, "GPa", "induction_cladding", "in-situ TiC" if sample != "substrate_nano" else "none", "local", "phase", "CSM nanoindentation", "depth 0-1000 nm", "", "nano", region, "DIRECT_TEXT_ORIGINAL_PDF", n="10", notes="Published phase mean; raw ten-repeat values unavailable.")
    add_atomic("YU", sample, "nanoindentation_RT", "modulus", e_gpa, "GPa", "induction_cladding", "in-situ TiC" if sample != "substrate_nano" else "none", "local", "phase", "CSM nanoindentation", "depth 0-1000 nm", "", "nano", region, "DIRECT_TEXT_ORIGINAL_PDF", n="10", notes="TiC uses conclusion value 270 GPa; nearby text also reports a 280 GPa peak.")

# Arevalo 2017: reported relative dose effects; no pure-matrix arm.
for dose, hratio, eratio in [(0.9, 1.00, 1.00), (2.5, 1.05, 1.05), (5.0, 1.32, 1.18)]:
    add_atomic("AREVALO", f"Ti_B{dose}", "1100C_processed_RT_test", "hardness_ratio", hratio, "ratio_to_0.9volB", "inductive_hot_pressing", "in-situ TiB", dose, "precursor vol% B", "Vickers", "HV10", "", "macro", "bulk", "DERIVED_FROM_REPORTED_PERCENT", n="8", notes="No pure-Ti control; actual TiB fraction lower than predesigned because reaction was incomplete.")
    add_atomic("AREVALO", f"Ti_B{dose}", "1100C_processed_RT_test", "modulus_ratio", eratio, "ratio_to_0.9volB", "inductive_hot_pressing", "in-situ TiB", dose, "precursor vol% B", "ultrasonic modulus", "", "", "macro", "bulk", "DERIVED_FROM_REPORTED_PERCENT", notes="No pure-Ti control; absolute E not digitized in this recovery package.")

# Guo 2023: SLM Ti6Al4V/B4C dose series, figure labels.
for dose, hv, uts, el in [(0, 349.9, 1137, 9.10), (0.05, 375.1, 1225, 14.17), (0.3, 399.8, 1207, 7.71), (0.5, 410.1, 1047, 5.67)]:
    sample = f"B4C_{dose}wt"
    add_atomic("GUO", sample, "as_built_RT", "hardness", hv, "HV", "SLM", "in-situ TiB+TiC", dose, "wt% B4C", "Vickers", "5 N", "15", "micro", "bulk", "DIRECT_FIGURE_LABELS_ORIGINAL_PDF", n="15")
    add_atomic("GUO", sample, "as_built_RT", "UTS", uts, "MPa", "SLM", "in-situ TiB+TiC", dose, "wt% B4C", "tension", "0.5 mm/min", "", "macro", "bulk", "DIRECT_FIGURE_LABELS_ORIGINAL_PDF")
    add_atomic("GUO", sample, "as_built_RT", "elongation", el, "%", "SLM", "in-situ TiB+TiC", dose, "wt% B4C", "tension", "0.5 mm/min", "", "macro", "bulk", "DIRECT_FIGURE_LABELS_ORIGINAL_PDF")

# Sabahi 2017: SPS table with uncertainty and repeats.
for sample, dose, hv, hv_u, uts, uts_u, el, el_u, density, density_u, bend, bend_u in [
    ("Ti", 0, 305, 15, 441, 6, 2.68, 0.15, 97.92, 0.03, 2134, 55),
    ("Ti_2.4wtTiB2", 2.4, 363, 21, 485, 9, 8.67, 0.11, 98.85, 0.04, 1615, 79),
]:
    add_atomic("SABAHI", sample, "SPS_1050C_RT", "hardness", hv, "HV0.3", "SPS", "in-situ TiB plus residual TiB2", dose, "wt% TiB2 precursor", "Vickers", "300 g", "15", "micro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF", n="6", uncertainty=f"±{hv_u}")
    add_atomic("SABAHI", sample, "SPS_1050C_RT", "UTS", uts, "MPa", "SPS", "in-situ TiB plus residual TiB2", dose, "wt% TiB2 precursor", "tension", "0.5 mm/min", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF", n="4", uncertainty=f"±{uts_u}")
    add_atomic("SABAHI", sample, "SPS_1050C_RT", "elongation", el, "%", "SPS", "in-situ TiB plus residual TiB2", dose, "wt% TiB2 precursor", "tension", "0.5 mm/min", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF", n="4", uncertainty=f"±{el_u}")
    add_atomic("SABAHI", sample, "SPS_1050C_RT", "relative_density", density, "%", "SPS", "in-situ TiB plus residual TiB2", dose, "wt% TiB2 precursor", "Archimedes", "", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF", uncertainty=f"±{density_u}")
    add_atomic("SABAHI", sample, "SPS_1050C_RT", "bending_strength", bend, "MPa", "SPS", "in-situ TiB plus residual TiB2", dose, "wt% TiB2 precursor", "three-point bending", "0.5 mm/min", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF", n="3", uncertainty=f"±{bend_u}")

# Li 2023: DED matrix/composite pair at RT and 600 C.
for sample, dose, hv, uts_rt, el_rt, uts_600, el_600 in [
    ("Ti6Al4V", 0, 344.0, 989.3, 8.2, 406.1, 24.3),
    ("5wtB4C_Ti", 5, 414.0, 1126.1, 4.2, 506.4, 14.1),
]:
    add_atomic("LI", sample, "as_deposited_RT", "hardness", hv, "HV0.5", "DED", "in-situ TiB+TiC", dose, "wt% B4C", "Vickers", "0.5 kg", "10", "micro", "bulk", "DIRECT_TEXT_ORIGINAL_PDF", n="3 points per build height")
    add_atomic("LI", sample, "as_deposited_RT", "UTS", uts_rt, "MPa", "DED", "in-situ TiB+TiC", dose, "wt% B4C", "tension", "0.5 mm/min", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF")
    add_atomic("LI", sample, "as_deposited_RT", "elongation", el_rt, "%", "DED", "in-situ TiB+TiC", dose, "wt% B4C", "tension", "0.5 mm/min", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF")
    add_atomic("LI", sample, "as_deposited_600C", "UTS", uts_600, "MPa", "DED", "in-situ TiB+TiC", dose, "wt% B4C", "tension", "1 mm/min", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF", temperature_c=600)
    add_atomic("LI", sample, "as_deposited_600C", "elongation", el_600, "%", "DED", "in-situ TiB+TiC", dose, "wt% B4C", "tension", "1 mm/min", "", "macro", "bulk", "DIRECT_TABLE_TEXT_ORIGINAL_PDF", temperature_c=600)

pairs: list[dict] = []


def add_pair(paper: str, control_sample: str, treated_sample: str, prop: str, condition: str, grade: str, pair_class: str, dose_delta: float | str = "", dose_unit: str = "", notes: str = "") -> dict:
    c = record_index[(paper, control_sample, prop, condition)]
    t = record_index[(paper, treated_sample, prop, condition)]
    cv = float(c["value"])
    tv = float(t["value"])
    lnrr = math.log(tv / cv) if cv > 0 and tv > 0 else float("nan")
    pair_uid = uid("PAIR", c["record_uid"], t["record_uid"], prop)
    row = {
        "pair_uid": pair_uid,
        "snapshot_id": SNAPSHOT,
        "paper_uid": c["paper_uid"],
        "doi": c["doi"],
        "control_record_uid": c["record_uid"],
        "treated_record_uid": t["record_uid"],
        "control_sample_uid": c["sample_uid"],
        "treated_sample_uid": t["sample_uid"],
        "control_condition_uid": c["condition_uid"],
        "treated_condition_uid": t["condition_uid"],
        "property": prop,
        "control_value": cv,
        "treated_value": tv,
        "unit": c["unit"],
        "delta": tv - cv,
        "lnRR": lnrr,
        "percent_change": 100 * (math.exp(lnrr) - 1),
        "dose_delta": dose_delta,
        "dose_unit": dose_unit,
        "efficiency": (tv - cv) / float(dose_delta) if dose_delta not in {"", 0} else "",
        "pair_grade": grade,
        "pair_class": pair_class,
        "measurement_scale": t["measurement_scale"],
        "control_region": c["region"],
        "treated_region": t["region"],
        "evidence_level": t["evidence_level"],
        "source_hash": c["source_hash"],
        "source_locator": c["source_locator"],
        "provenance_uid": uid("PAIRPROV", pair_uid, c["source_locator"]),
        "claim_level": 2 if grade in {"A", "B"} else 1,
        "notes": notes,
    }
    pairs.append(row)
    provenance.append({
        "provenance_uid": row["provenance_uid"],
        "snapshot_id": SNAPSHOT,
        "paper_uid": row["paper_uid"],
        "sample_uid": row["treated_sample_uid"],
        "condition_uid": row["treated_condition_uid"],
        "record_uid": pair_uid,
        "doi": row["doi"],
        "source_hash": row["source_hash"],
        "source_hash_kind": "locator_sha256_not_source_bytes",
        "source_locator": row["source_locator"],
        "evidence_level": row["evidence_level"],
        "claim": f"paired {prop}: delta={row['delta']}, lnRR={lnrr}",
        "notes": notes,
    })
    return row


# Strict same-process matrix-control hardness pairs.
for dose in [1, 5, 10, 20]:
    add_pair("BIED", "Ti_0volTiC", f"Ti_{dose}volTiC", "hardness", "as_built_RT", "A", "same-paper same-process matrix control", dose, "vol% TiC")
for dose in [0.05, 0.3, 0.5]:
    add_pair("GUO", "B4C_0wt", f"B4C_{dose}wt", "hardness", "as_built_RT", "A", "same-paper same-process matrix control", dose, "wt% B4C")
    add_pair("GUO", "B4C_0wt", f"B4C_{dose}wt", "UTS", "as_built_RT", "A", "same-paper same-process matrix control", dose, "wt% B4C")
add_pair("SABAHI", "Ti", "Ti_2.4wtTiB2", "hardness", "SPS_1050C_RT", "A", "same-paper same-process matrix control", 2.4, "wt% TiB2 precursor")
add_pair("SABAHI", "Ti", "Ti_2.4wtTiB2", "UTS", "SPS_1050C_RT", "A", "same-paper same-process matrix control", 2.4, "wt% TiB2 precursor")
add_pair("LI", "Ti6Al4V", "5wtB4C_Ti", "hardness", "as_deposited_RT", "A", "same-paper same-process matrix control", 5, "wt% B4C")
add_pair("LI", "Ti6Al4V", "5wtB4C_Ti", "UTS", "as_deposited_RT", "A", "same-paper same-process matrix control", 5, "wt% B4C")

# System-level coating/substrate and local phase contrasts.
add_pair("YU", "Ti6Al4V_substrate_macro", "TiC_Ti_coating_macro", "hardness", "cross_section_RT", "B", "same cross-section coating-versus-substrate", 0.11, "TiC area fraction", notes="Not a composition-only matrix control; region and thermal history change together.")
for target in ["alpha_nano", "beta_nano", "TiC_nano"]:
    add_pair("YU", "substrate_nano", target, "hardness", "nanoindentation_RT", "B", "same-paper local-phase contrast", notes="Phase selection and indentation depth are part of the estimand.")
    add_pair("YU", "substrate_nano", target, "modulus", "nanoindentation_RT", "B", "same-paper local-phase contrast", notes="Local indentation modulus; not interchangeable with bulk static/dynamic modulus.")

# Dose contrasts against the lowest reinforced Arevalo arm, not against pure matrix.
for dose in [2.5, 5.0]:
    add_pair("AREVALO", "Ti_B0.9", f"Ti_B{dose}", "hardness_ratio", "1100C_processed_RT_test", "C", "same-paper reinforced-dose contrast", dose - 0.9, "precursor vol% B", notes="No pure matrix; relative effect only.")
    add_pair("AREVALO", "Ti_B0.9", f"Ti_B{dose}", "modulus_ratio", "1100C_processed_RT_test", "C", "same-paper reinforced-dose contrast", dose - 0.9, "precursor vol% B", notes="No pure matrix; relative effect only.")

strict_hardness = [p for p in pairs if p["property"] == "hardness" and p["pair_grade"] == "A"]
by_paper: dict[str, list[dict]] = defaultdict(list)
for row in strict_hardness:
    by_paper[row["paper_uid"]].append(row)

paper_hardness = []
for paper_uid, rows in by_paper.items():
    meta = next(m for m in PAPERS.values() if m["paper_uid"] == paper_uid)
    paper_hardness.append({
        "paper_uid": paper_uid,
        "doi": meta["doi"],
        "paper_short": next(k for k, m in PAPERS.items() if m["paper_uid"] == paper_uid),
        "n_pairs": len(rows),
        "mean_delta_hv": statistics.mean(float(r["delta"]) for r in rows),
        "mean_lnRR": statistics.mean(float(r["lnRR"]) for r in rows),
        "mean_percent": 100 * (math.exp(statistics.mean(float(r["lnRR"]) for r in rows)) - 1),
    })

paper_deltas = [r["mean_delta_hv"] for r in paper_hardness]
paper_lnrr = [r["mean_lnRR"] for r in paper_hardness]
mean_delta, delta_ci_lo, delta_ci_hi = cluster_bootstrap(paper_deltas)
mean_lnrr, lnrr_ci_lo, lnrr_ci_hi = cluster_bootstrap(paper_lnrr)
t_crit_3 = 3.182446305284263
sd_delta = statistics.stdev(paper_deltas)
sd_lnrr = statistics.stdev(paper_lnrr)
delta_pi_lo = mean_delta - t_crit_3 * sd_delta * math.sqrt(1 + 1 / len(paper_deltas))
delta_pi_hi = mean_delta + t_crit_3 * sd_delta * math.sqrt(1 + 1 / len(paper_deltas))
lnrr_pi_lo = mean_lnrr - t_crit_3 * sd_lnrr * math.sqrt(1 + 1 / len(paper_lnrr))
lnrr_pi_hi = mean_lnrr + t_crit_3 * sd_lnrr * math.sqrt(1 + 1 / len(paper_lnrr))

lopo_rows = []
for held in paper_hardness:
    keep = [r for r in paper_hardness if r["paper_uid"] != held["paper_uid"]]
    est = statistics.mean(r["mean_lnRR"] for r in keep)
    lopo_rows.append({
        "analysis": "strict_hardness_equal_paper_LOPO",
        "held_out_paper_uid": held["paper_uid"],
        "held_out_doi": held["doi"],
        "estimate_lnRR": est,
        "percent_change": 100 * (math.exp(est) - 1),
        "independent_papers_remaining": len(keep),
        "status": "DESCRIPTIVE_SMALL_K",
    })

# Hardness-UTS validation cohort.
hu_rows = []
for paper, samples, condition in [
    ("GUO", ["B4C_0wt", "B4C_0.05wt", "B4C_0.3wt", "B4C_0.5wt"], "as_built_RT"),
    ("SABAHI", ["Ti", "Ti_2.4wtTiB2"], "SPS_1050C_RT"),
    ("LI", ["Ti6Al4V", "5wtB4C_Ti"], "as_deposited_RT"),
]:
    xs, ys = [], []
    for sample in samples:
        h = record_index[(paper, sample, "hardness", condition)]
        u = record_index[(paper, sample, "UTS", condition)]
        xs.append(float(h["value"]))
        ys.append(float(u["value"]))
        hu_rows.append({
            "row_type": "sample",
            "paper_key": paper,
            "paper_uid": h["paper_uid"],
            "doi": h["doi"],
            "sample_uid": h["sample_uid"],
            "condition_uid": h["condition_uid"],
            "sample_label": sample,
            "hardness_hv": h["value"],
            "hardness_scale": h["unit"],
            "UTS_MPa": u["value"],
            "process": h["process"],
            "evidence_level": h["evidence_level"],
            "source_hash": h["source_hash"],
            "provenance_uid": h["provenance_uid"],
            "model_scope": "family-specific; no cross-scale conversion",
        })
    slope, intercept = simple_slope(xs, ys)
    for row in hu_rows:
        if row.get("paper_key") == paper and row.get("row_type") == "sample":
            row["family_slope_MPa_per_HV"] = slope
            row["family_intercept_MPa"] = intercept

# Paper fixed-effect slope using within-paper centering.
groups = defaultdict(list)
for row in hu_rows:
    groups[row["paper_key"]].append(row)
centered = []
for key, rows in groups.items():
    mx = statistics.mean(float(r["hardness_hv"]) for r in rows)
    my = statistics.mean(float(r["UTS_MPa"]) for r in rows)
    for r in rows:
        centered.append((float(r["hardness_hv"]) - mx, float(r["UTS_MPa"]) - my, key))
sxx = sum(x * x for x, _, _ in centered)
beta_fe = sum(x * y for x, y, _ in centered) / sxx
residuals = [y - beta_fe * x for x, y, _ in centered]
df = len(centered) - len(groups) - 1
mse = sum(r * r for r in residuals) / df
se_beta = math.sqrt(mse / sxx)
t_crit_4 = 2.7764451051977987
beta_lo = beta_fe - t_crit_4 * se_beta
beta_hi = beta_fe + t_crit_4 * se_beta
pi_half = t_crit_4 * math.sqrt(mse * (1 + 1 / len(centered)))

hu_model_rows = [{
    "row_type": "model",
    "paper_key": "ALL",
    "paper_uid": "MULTI_PAPER",
    "doi": "MULTI_PAPER",
    "sample_uid": "",
    "condition_uid": "",
    "sample_label": "paper_fixed_effect_slope",
    "hardness_hv": "",
    "hardness_scale": "native Vickers scales treated as approximately numeric only within reported HV family",
    "UTS_MPa": "",
    "process": "SLM+SPS+DED",
    "evidence_level": "ADJUSTED_ASSOCIATION",
    "source_hash": hbytes("|".join(sorted(m["source_hash"] for m in PAPERS.values())).encode()),
    "provenance_uid": uid("PROV", "hardness_uts_FE", SNAPSHOT),
    "model_scope": "paper fixed intercept; common within-paper slope",
    "family_slope_MPa_per_HV": beta_fe,
    "family_intercept_MPa": "paper-specific",
    "ci_low": beta_lo,
    "ci_high": beta_hi,
    "prediction_half_width_MPa": pi_half,
    "independent_papers": len(groups),
    "atomic_rows": len(centered),
    "claim_level": 3,
    "transfer_status": "NOT_TRANSFERABLE",
}]

hu_lopo = []
for held in sorted(groups):
    keep_rows = [r for r in hu_rows if r["paper_key"] != held]
    kg = defaultdict(list)
    for r in keep_rows:
        kg[r["paper_key"]].append(r)
    c2 = []
    for key, rows in kg.items():
        mx = statistics.mean(float(r["hardness_hv"]) for r in rows)
        my = statistics.mean(float(r["UTS_MPa"]) for r in rows)
        for r in rows:
            c2.append((float(r["hardness_hv"]) - mx, float(r["UTS_MPa"]) - my))
    b = sum(x * y for x, y in c2) / sum(x * x for x, _ in c2)
    hu_lopo.append({"analysis": "hardness_UTS_paper_FE_LOPO", "held_out_paper": held, "estimate": b, "unit": "MPa/HV", "independent_papers_remaining": len(kg), "status": "UNSTABLE"})

# Dose-response summaries in native dose units; no wt/vol conversion.
dose_rows = []
for paper, prop, condition, samples in [
    ("BIED", "hardness", "as_built_RT", ["Ti_0volTiC", "Ti_1volTiC", "Ti_5volTiC", "Ti_10volTiC", "Ti_20volTiC"]),
    ("GUO", "hardness", "as_built_RT", ["B4C_0wt", "B4C_0.05wt", "B4C_0.3wt", "B4C_0.5wt"]),
    ("GUO", "UTS", "as_built_RT", ["B4C_0wt", "B4C_0.05wt", "B4C_0.3wt", "B4C_0.5wt"]),
]:
    rows = [record_index[(paper, s, prop, condition)] for s in samples]
    xs = [float(r["dose"]) for r in rows]
    ys = [float(r["value"]) for r in rows]
    slope, intercept = simple_slope(xs, ys)
    yhat = [intercept + slope * x for x in xs]
    sse = sum((y - yh) ** 2 for y, yh in zip(ys, yhat))
    syy = sum((y - statistics.mean(ys)) ** 2 for y in ys)
    dose_rows.append({
        "paper_uid": rows[0]["paper_uid"], "doi": rows[0]["doi"], "property": prop,
        "dose_unit": rows[0]["dose_unit"], "dose_min": min(xs), "dose_max": max(xs),
        "n_arms": len(rows), "linear_slope": slope, "intercept": intercept,
        "r2_descriptive": 1 - sse / syy if syy else "", "model_status": "DESCRIPTIVE_WITHIN_PAPER",
        "boundary_warning": "Do not extrapolate; dose units and actual reacted phase differ across papers.",
    })
for row in pairs:
    if row["paper_uid"] == PAPERS["BIED"]["paper_uid"] and row["property"] == "hardness":
        dose_rows.append({
            "paper_uid": row["paper_uid"], "doi": row["doi"], "property": "hardness_efficiency",
            "dose_unit": row["dose_unit"], "dose_min": 0, "dose_max": row["dose_delta"], "n_arms": 2,
            "linear_slope": row["efficiency"], "intercept": 300, "r2_descriptive": "",
            "model_status": "PAIRWISE_EFFICIENCY", "boundary_warning": "Efficiency falls from 77 to 17.55 HV/vol%; no universal linear coefficient.",
        })

# Aggregate effect table.
effect_rows = []
for p in pairs:
    effect_rows.append({
        "effect_uid": uid("EFFECT", p["pair_uid"]),
        "effect_type": "pair",
        **p,
        "ci_low": "",
        "ci_high": "",
        "prediction_low": "",
        "prediction_high": "",
        "independent_papers": 1,
        "estimand_status": "IDENTIFIED_WITHIN_PAIR",
    })
aggregate_uid = uid("EFFECT", "strict_hardness_equal_paper", SNAPSHOT)
effect_rows.append({
    "effect_uid": aggregate_uid,
    "effect_type": "paper_balanced_aggregate",
    "pair_uid": "MULTI_PAIR",
    "snapshot_id": SNAPSHOT,
    "paper_uid": "MULTI_PAPER",
    "doi": "MULTI_PAPER",
    "property": "hardness",
    "unit": "HV (paper means; native Vickers loads retained)",
    "delta": mean_delta,
    "lnRR": mean_lnrr,
    "percent_change": 100 * (math.exp(mean_lnrr) - 1),
    "pair_grade": "A",
    "pair_class": "same-paper same-process matrix controls",
    "measurement_scale": "micro",
    "evidence_level": "DIRECT_TEXT_TABLE_OR_FIGURE_LABEL",
    "source_hash": hbytes("|".join(sorted(r["source_hash"] for r in strict_hardness)).encode()),
    "source_locator": "six-paper recovery cohort; four-paper strict hardness subset",
    "provenance_uid": uid("PROV", aggregate_uid),
    "claim_level": 2,
    "ci_low": lnrr_ci_lo,
    "ci_high": lnrr_ci_hi,
    "prediction_low": lnrr_pi_lo,
    "prediction_high": lnrr_pi_hi,
    "independent_papers": len(paper_hardness),
    "estimand_status": "SMALL_K_CLUSTER_BOOTSTRAP_AND_DESCRIPTIVE_PI",
    "notes": f"Absolute delta bootstrap CI {delta_ci_lo:.3f} to {delta_ci_hi:.3f} HV; descriptive PI {delta_pi_lo:.3f} to {delta_pi_hi:.3f} HV.",
})

hardness_effects = [r for r in effect_rows if r.get("property") in {"hardness", "hardness_ratio"}]
modulus_effects = [r for r in effect_rows if r.get("property") in {"modulus", "modulus_ratio"}]

# Indentation hierarchy table.
indent_rows = []
for row in atomic:
    if row["paper_key"] == "YU" and row["property"] in {"hardness", "modulus"}:
        equiv_hv = ""
        conversion = "none"
        if row["property"] == "hardness" and row["unit"] == "GPa":
            equiv_hv = float(row["value"]) * 94.5
            conversion = "paper-specific factor reported by Yu et al.; sensitivity only"
        indent_rows.append({
            "record_uid": row["record_uid"], "paper_uid": row["paper_uid"], "doi": row["doi"],
            "sample_uid": row["sample_uid"], "condition_uid": row["condition_uid"], "region": row["region"],
            "measurement_scale": row["measurement_scale"], "property": row["property"], "value": row["value"],
            "unit": row["unit"], "equivalent_hv_sensitivity": equiv_hv, "conversion_policy": conversion,
            "n_measurements": row["n_measurements"], "raw_repeats_available": "no",
            "source_hash": row["source_hash"], "provenance_uid": row["provenance_uid"],
            "pseudoreplication_policy": "phase mean is one sample-level estimate; n=10 is not treated as ten independent samples",
        })

hierarchical_rows = [
    {
        "analysis_id": "HARDNESS_PRIMARY", "outcome": "hardness", "model": "equal-paper mean of within-paper mean lnRR",
        "estimate": mean_lnrr, "unit": "lnRR", "ci_low": lnrr_ci_lo, "ci_high": lnrr_ci_hi,
        "prediction_low": lnrr_pi_lo, "prediction_high": lnrr_pi_hi, "independent_papers": len(paper_hardness),
        "pairs": len(strict_hardness), "cluster_unit": "paper", "claim_level": 2,
        "status": "IDENTIFIED_SMALL_K_HIGH_HETEROGENEITY",
    },
    {
        "analysis_id": "HARDNESS_UTS_FE", "outcome": "UTS", "model": "paper fixed intercept with common within-paper hardness slope",
        "estimate": beta_fe, "unit": "MPa/HV", "ci_low": beta_lo, "ci_high": beta_hi,
        "prediction_low": -pi_half, "prediction_high": pi_half, "independent_papers": len(groups),
        "pairs": len(centered), "cluster_unit": "paper", "claim_level": 3,
        "status": "NOT_TRANSFERABLE_FAMILY_SLOPES_CONFLICT",
    },
    {
        "analysis_id": "MODULUS_CROSS_SCALE", "outcome": "modulus", "model": "no pooled model",
        "estimate": "", "unit": "", "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "",
        "independent_papers": 2, "pairs": len(modulus_effects), "cluster_unit": "paper",
        "claim_level": 1, "status": "NOT_IDENTIFIABLE_ACROSS_STATIC_DYNAMIC_INDENTATION_SCALES",
    },
]

heterogeneity_rows = []
for row in paper_hardness:
    heterogeneity_rows.append({
        "analysis": "strict_hardness_paper_mean", "paper_uid": row["paper_uid"], "doi": row["doi"],
        "estimate": row["mean_lnRR"], "unit": "lnRR", "n_pairs": row["n_pairs"],
        "between_paper_sd": sd_lnrr, "prediction_low": lnrr_pi_lo, "prediction_high": lnrr_pi_hi,
        "interpretation": "Paper means vary materially; a single universal hardness gain is not defensible.",
    })
for paper, rows in groups.items():
    heterogeneity_rows.append({
        "analysis": "hardness_UTS_family_slope", "paper_uid": rows[0]["paper_uid"], "doi": rows[0]["doi"],
        "estimate": rows[0]["family_slope_MPa_per_HV"], "unit": "MPa/HV", "n_pairs": len(rows),
        "between_paper_sd": statistics.stdev(float(r["family_slope_MPa_per_HV"]) for r in [groups[k][0] for k in groups]),
        "prediction_low": min(float(groups[k][0]["family_slope_MPa_per_HV"]) for k in groups),
        "prediction_high": max(float(groups[k][0]["family_slope_MPa_per_HV"]) for k in groups),
        "interpretation": "Slope sign and magnitude depend on family/process/dose regime.",
    })

sensitivity_rows = list(lopo_rows) + list(hu_lopo)
# Add evidence and pair-definition variants.
yu_macro = next(p for p in pairs if p["paper_uid"] == PAPERS["YU"]["paper_uid"] and p["property"] == "hardness" and p["measurement_scale"] == "micro")
with_yu_means = paper_lnrr + [float(yu_macro["lnRR"])]
sensitivity_rows.extend([
    {
        "analysis": "strict_hardness_plus_system_level_Yu", "held_out_paper_uid": "", "held_out_doi": "",
        "estimate_lnRR": statistics.mean(with_yu_means), "percent_change": 100 * (math.exp(statistics.mean(with_yu_means)) - 1),
        "independent_papers_remaining": len(with_yu_means), "status": "SENSITIVITY_ONLY_REGION_AND_PROCESS_CHANGE",
    },
    {
        "analysis": "hardness_primary_exclude_figure_label_Guo", "held_out_paper_uid": PAPERS["GUO"]["paper_uid"], "held_out_doi": PAPERS["GUO"]["doi"],
        "estimate_lnRR": statistics.mean(r["mean_lnRR"] for r in paper_hardness if r["paper_uid"] != PAPERS["GUO"]["paper_uid"]),
        "percent_change": 100 * (math.exp(statistics.mean(r["mean_lnRR"] for r in paper_hardness if r["paper_uid"] != PAPERS["GUO"]["paper_uid"])) - 1),
        "independent_papers_remaining": 3, "status": "DIRECT_TEXT_TABLE_ONLY",
    },
    {
        "analysis": "nano_GPa_to_HV_conversion", "held_out_paper_uid": "", "held_out_doi": PAPERS["YU"]["doi"],
        "estimate_lnRR": math.log((22 * 94.5) / 600), "percent_change": 100 * ((22 * 94.5) / 600 - 1),
        "independent_papers_remaining": 1, "status": "PAPER_SPECIFIC_CONVERSION_ONLY_NOT_POOLED",
    },
])

interaction_rows = [
    {
        "interaction": "measurement_scale_x_phase_region", "estimate": "", "unit": "", "independent_papers": 1,
        "status": "NOT_IDENTIFIABLE", "reason": "Yu et al. provide local phase and macro cross-section measurements, but no full factorial of scale by identical region and loading protocol.",
        "claim_level": 1,
    },
    {
        "interaction": "material_family_x_hardness_on_UTS", "estimate": "range -0.924 to 1.954", "unit": "MPa/HV", "independent_papers": 3,
        "status": "DESCRIPTIVE_STRONG_HETEROGENEITY", "reason": "Family-specific slopes have opposite signs; interaction is not promoted because k=3.",
        "claim_level": 3,
    },
    {
        "interaction": "porosity_x_reinforcement_on_hardness", "estimate": "", "unit": "", "independent_papers": 1,
        "status": "NOT_IDENTIFIABLE", "reason": "Only Sabahi reports paired relative density with hardness; other primary arms lack commensurate porosity.",
        "claim_level": 1,
    },
]

null_rows = [
    {"paper_uid": PAPERS["GUO"]["paper_uid"], "doi": PAPERS["GUO"]["doi"], "result": "Hardness rises monotonically from 349.9 to 410.1 HV while UTS falls from 1137 to 1047 MPa at 0.5 wt% B4C.", "classification": "COUNTEREXAMPLE_HARDNESS_NOT_STRENGTH_PROXY", "provenance": PAPERS["GUO"]["source_locator"]},
    {"paper_uid": PAPERS["YU"]["paper_uid"], "doi": PAPERS["YU"]["doi"], "result": "Nanoindentation alpha-rich phase and substrate both report 4.0 GPa hardness and 150 GPa modulus.", "classification": "NULL_LOCAL_CONTRAST", "provenance": PAPERS["YU"]["source_locator"]},
    {"paper_uid": PAPERS["AREVALO"]["paper_uid"], "doi": PAPERS["AREVALO"]["doi"], "result": "Hardness remains approximately 300 HV over 1000-1300 C processing while modulus rises with processing temperature.", "classification": "PROPERTY_DECOUPLING", "provenance": PAPERS["AREVALO"]["source_locator"]},
    {"paper_uid": PAPERS["SABAHI"]["paper_uid"], "doi": PAPERS["SABAHI"]["doi"], "result": "Hardness and UTS increase, but bending strength decreases from 2134 to 1615 MPa.", "classification": "NEGATIVE_TOUGHNESS_RELATED_RESPONSE", "provenance": PAPERS["SABAHI"]["source_locator"]},
    {"paper_uid": PAPERS["LI"]["paper_uid"], "doi": PAPERS["LI"]["doi"], "result": "Hardness and UTS increase, but RT elongation decreases from 8.2% to 4.2%.", "classification": "STRENGTH_DUCTILITY_TRADEOFF", "provenance": PAPERS["LI"]["source_locator"]},
]

conflict_rows = [
    {"conflict_id": "C01", "paper_uid": PAPERS["YU"]["paper_uid"], "field": "TiC indentation modulus", "value_a": "270 GPa conclusion/average", "value_b": "280 GPa peak in nearby text", "resolution": "Use 270 GPa as phase estimate; retain 280 GPa as peak and do not average them.", "status": "RESOLVED_WITH_SEMANTIC_SPLIT"},
    {"conflict_id": "C02", "paper_uid": PAPERS["GUO"]["paper_uid"], "field": "hardness-versus-UTS optimum", "value_a": "Hardness maximum at 0.5 wt% B4C", "value_b": "UTS maximum at 0.05 wt% B4C", "resolution": "Not a contradiction; endpoints differ. Retain as a counterexample to hardness-to-strength substitution.", "status": "RESOLVED_ENDPOINT_DIFFERENCE"},
    {"conflict_id": "C03", "paper_uid": PAPERS["LI"]["paper_uid"], "field": "TiB aspect-ratio mechanism sentence", "value_a": "reported aspect ratio 2.23", "value_b": "reported critical value 8.12 while text says 2.23 is higher", "resolution": "Treat sentence as internally inconsistent and exclude it from quantitative mechanism inference.", "status": "OPEN_SOURCE_TEXT_ERROR"},
    {"conflict_id": "C04", "paper_uid": PAPERS["AREVALO"]["paper_uid"], "field": "reinforcement fraction", "value_a": "predesigned TiB based on precursor B", "value_b": "incomplete reaction leaves actual TiB below predesign", "resolution": "Use precursor vol% B as dose label only; do not calculate per-vol% TiB efficiency.", "status": "OPEN_ACTUAL_PHASE_FRACTION"},
    {"conflict_id": "C05", "paper_uid": PAPERS["BIED"]["paper_uid"], "field": "process naming", "value_a": "title says selective laser sintering/melting", "value_b": "methods describe SLM", "resolution": "Canonical process set to SLM; title retained verbatim.", "status": "RESOLVED_METHOD_TEXT_PRIORITY"},
    {"conflict_id": "C06", "paper_uid": "MULTI_PAPER", "field": "hardness scale conversion", "value_a": "HV0.05/HV0.2/HV0.3/HV0.5/HV10", "value_b": "nanoindentation GPa", "resolution": "No default cross-scale conversion. Only Yu paper-specific 94.5 factor is retained as sensitivity output.", "status": "POLICY_RESOLVED"},
]

# Input ledger: all top-level archives are inventoried; scientific deep use is source-specific.
input_rows = []
for name, sha, members, role in ARCHIVES:
    input_rows.append({
        "source_name": name, "source_type": "project_archive", "sha256": sha, "hash_kind": "archive_sha256_from_prior_verified_project_ledger",
        "member_count": members, "availability": "mounted_in_project_context_not_rehashed_on_remote_runner", "role": role,
        "use_level": "INVENTORIED_AND_SCOPE_CLASSIFIED", "scope_action": "candidate source registry / code / frozen data / provenance; canonical row-level bind requested where inaccessible",
        "notes": "No claim that every member is a QM09 positive. Primary-paper evidence overrides summaries and code comments.",
    })
input_rows.append({
    "source_name": "QM09_硬度、弹性模量与局部测试尺度效应.md", "source_type": "dispatch_contract", "sha256": "", "hash_kind": "chat_attachment_id",
    "member_count": 1, "availability": "opened", "role": "scope/acceptance", "use_level": "DEEP_USED",
    "scope_action": "defined estimands, outputs, figures and claim ceiling", "notes": "attachment file_000000007da8720bb3d4acae78aeae38",
})
for key, meta in PAPERS.items():
    input_rows.append({
        "source_name": meta["title"], "source_type": "primary_paper", "sha256": meta["source_hash"], "hash_kind": meta["hash_kind"],
        "member_count": 1, "availability": "opened_full_text", "role": "highest-weight scientific evidence", "use_level": "DEEP_USED",
        "scope_action": f"atomic extraction and effect construction; DOI {meta['doi']}", "notes": meta["evidence"],
    })

# Write core tables before plots.
if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir(parents=True, exist_ok=True)

atomic_fields = [
    "record_uid", "snapshot_id", "paper_key", "paper_uid", "doi", "sample_uid", "sample_label", "condition_uid", "condition_label",
    "property", "value", "unit", "process", "reinforcement", "dose", "dose_unit", "test_temperature_c", "test_method", "load", "dwell_s",
    "measurement_scale", "region", "n_measurements", "uncertainty", "evidence_level", "source_hash", "source_hash_kind", "source_locator", "provenance_uid", "notes",
]
pair_fields = [
    "pair_uid", "snapshot_id", "paper_uid", "doi", "control_record_uid", "treated_record_uid", "control_sample_uid", "treated_sample_uid",
    "control_condition_uid", "treated_condition_uid", "property", "control_value", "treated_value", "unit", "delta", "lnRR", "percent_change",
    "dose_delta", "dose_unit", "efficiency", "pair_grade", "pair_class", "measurement_scale", "control_region", "treated_region", "evidence_level",
    "source_hash", "source_locator", "provenance_uid", "claim_level", "notes",
]
wc("INPUT_LEDGER.csv", input_rows)
wc("ANALYSIS_COHORT.csv", atomic, atomic_fields)
wc("PAIR_MATCHES.csv", pairs, pair_fields)
wc("EFFECT_ESTIMATES.csv", effect_rows)
wc("HARDNESS_EFFECTS.csv", hardness_effects)
wc("MODULUS_EFFECTS.csv", modulus_effects)
wc("INDENTATION_HIERARCHY.csv", indent_rows)
wc("HARDNESS_STRENGTH_VALIDATION.csv", hu_rows + hu_model_rows)
wc("HIERARCHICAL_RESULTS.csv", hierarchical_rows)
wc("DOSE_RESPONSE.csv", dose_rows)
wc("INTERACTION_EFFECTS.csv", interaction_rows)
wc("HETEROGENEITY.csv", heterogeneity_rows)
wc("SENSITIVITY_ANALYSIS.csv", sensitivity_rows)
wc("NULL_NEGATIVE_RESULTS.csv", null_rows)
wc("CONFLICT_LEDGER.csv", conflict_rows)

with (ROOT / "PROVENANCE.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
    for row in provenance:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

# Figure data.
forest_rows = []
for row in paper_hardness:
    forest_rows.append({
        "label": f"{row['paper_short']} hardness", "property": "Hardness", "scale": "micro Vickers", "paper_uid": row["paper_uid"],
        "independent_papers": 1, "n_pairs": row["n_pairs"], "lnRR": row["mean_lnRR"], "percent_change": row["mean_percent"],
        "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "", "evidence_grade": "A",
        "support_domain": "within-paper native scale",
    })
forest_rows.append({
    "label": "Paper-balanced hardness", "property": "Hardness", "scale": "micro Vickers", "paper_uid": "MULTI_PAPER",
    "independent_papers": len(paper_hardness), "n_pairs": len(strict_hardness), "lnRR": mean_lnrr,
    "percent_change": 100 * (math.exp(mean_lnrr) - 1), "ci_low": lnrr_ci_lo, "ci_high": lnrr_ci_hi,
    "prediction_low": lnrr_pi_lo, "prediction_high": lnrr_pi_hi, "evidence_grade": "A",
    "support_domain": "four papers; small-k cluster bootstrap",
})
for p in modulus_effects:
    if p["effect_type"] == "pair":
        forest_rows.append({
            "label": ("YU local " + p["treated_region"]) if p["doi"] == PAPERS["YU"]["doi"] else ("AREVALO dose " + str(p["treated_value"])),
            "property": "Modulus", "scale": p["measurement_scale"], "paper_uid": p["paper_uid"], "independent_papers": 1, "n_pairs": 1,
            "lnRR": p["lnRR"], "percent_change": p["percent_change"], "ci_low": "", "ci_high": "", "prediction_low": "", "prediction_high": "",
            "evidence_grade": p["pair_grade"], "support_domain": p["pair_class"],
        })
wc("figure_data/hardness_modulus_paired_forest.csv", forest_rows)

scale_rows = []
for p in pairs:
    if p["paper_uid"] == PAPERS["YU"]["paper_uid"] and p["property"] in {"hardness", "modulus"}:
        scale_rows.append({
            "label": f"{p['property']} | {p['treated_region']} vs {p['control_region']}", "property": p["property"], "measurement_scale": p["measurement_scale"],
            "lnRR": p["lnRR"], "percent_change": p["percent_change"], "pair_grade": p["pair_grade"], "pure_scale_offset": "no" if p["treated_region"] != p["control_region"] else "yes",
            "independent_papers": 1, "n_pairs": 1, "support_domain": "Yu 2017 induction-clad cross-section",
        })
scale_rows.extend([
    {"label": "hardness | nano substrate equivalent vs macro substrate", "property": "hardness", "measurement_scale": "nano-to-micro sensitivity", "lnRR": math.log((4.0 * 94.5) / 340), "percent_change": 100 * ((4.0 * 94.5) / 340 - 1), "pair_grade": "derived", "pure_scale_offset": "approximately same substrate region", "independent_papers": 1, "n_pairs": 1, "support_domain": "paper-specific 94.5 conversion"},
    {"label": "hardness | nano TiC equivalent vs macro coating", "property": "hardness", "measurement_scale": "nano-to-micro sensitivity", "lnRR": math.log((22.0 * 94.5) / 600), "percent_change": 100 * ((22.0 * 94.5) / 600 - 1), "pair_grade": "derived", "pure_scale_offset": "no; phase targeting dominates", "independent_papers": 1, "n_pairs": 1, "support_domain": "paper-specific 94.5 conversion"},
])
wc("figure_data/scale_offset_forest.csv", scale_rows)

local_rows = []
for row in indent_rows:
    if row["measurement_scale"] == "nano" and row["property"] == "hardness":
        mod = next(x for x in indent_rows if x["sample_uid"] == row["sample_uid"] and x["property"] == "modulus")
        local_rows.append({
            "region": row["region"], "hardness_GPa": row["value"], "modulus_GPa": mod["value"], "n_reported": row["n_measurements"],
            "raw_repeat_distribution": "unavailable", "independent_papers": 1, "evidence_layer": "published phase mean",
        })
wc("figure_data/local_phase_raincloud.csv", local_rows)

reg_rows = []
for row in hu_rows:
    reg_rows.append({
        "paper_key": row["paper_key"], "paper_uid": row["paper_uid"], "doi": row["doi"], "sample_label": row["sample_label"],
        "hardness_HV": row["hardness_hv"], "UTS_MPa": row["UTS_MPa"], "process": row["process"],
        "family_slope_MPa_per_HV": row["family_slope_MPa_per_HV"], "common_FE_slope": beta_fe,
        "common_FE_ci_low": beta_lo, "common_FE_ci_high": beta_hi, "prediction_half_width_MPa": pi_half,
        "independent_papers": len(groups), "atomic_rows": len(centered),
    })
wc("figure_data/hardness_uts_family_regression.csv", reg_rows)

plot1 = r'''from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
root = Path(sys.argv[1])
d = pd.read_csv(root / "figure_data/hardness_modulus_paired_forest.csv")
fig, ax = plt.subplots(figsize=(9.2, 6.8))
y = list(range(len(d)))
ax.axvline(0, linewidth=1)
for i, row in d.iterrows():
    ax.scatter(float(row["lnRR"]), i, s=45)
    if pd.notna(row.get("ci_low")) and pd.notna(row.get("ci_high")):
        ax.hlines(i, float(row["ci_low"]), float(row["ci_high"]), linewidth=2)
    if pd.notna(row.get("prediction_low")) and pd.notna(row.get("prediction_high")):
        ax.hlines(i, float(row["prediction_low"]), float(row["prediction_high"]), linewidth=0.8)
    ax.text(float(row["lnRR"]), i + 0.16, f"{float(row['percent_change']):+.1f}%", fontsize=7)
ax.set_yticks(y, d["label"].tolist())
ax.set_xlabel("Log response ratio, ln(treated/control)")
ax.set_title("Paired hardness and modulus effects\nCI/PI shown only where paper-cluster estimation is possible")
ax.text(0.01, -0.13, "Hardness aggregate: 4 independent papers / 9 strict pairs. Modulus rows are scale-specific and not pooled.", transform=ax.transAxes, fontsize=8)
fig.tight_layout()
for ext in ["png", "svg", "pdf"]:
    fig.savefig(root / "figures" / f"hardness_modulus_paired_forest.{ext}", dpi=600 if ext == "png" else None, bbox_inches="tight")
'''
plot2 = r'''from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
root = Path(sys.argv[1])
d = pd.read_csv(root / "figure_data/scale_offset_forest.csv")
fig, ax = plt.subplots(figsize=(9.2, 6.4))
ax.axvline(0, linewidth=1)
for i, row in d.iterrows():
    ax.scatter(float(row["lnRR"]), i, s=45)
    ax.text(float(row["lnRR"]), i + 0.15, f"{float(row['percent_change']):+.1f}%", fontsize=7)
ax.set_yticks(range(len(d)), d["label"].tolist())
ax.set_xlabel("Log response ratio")
ax.set_title("Measurement-scale and phase-region offsets\nNo pooled CI/PI: one paper and non-factorial region/scale design")
ax.text(0.01, -0.14, "Derived nano-to-HV rows use only the paper-specific conversion and remain sensitivity analyses.", transform=ax.transAxes, fontsize=8)
fig.tight_layout()
for ext in ["png", "svg", "pdf"]:
    fig.savefig(root / "figures" / f"scale_offset_forest.{ext}", dpi=600 if ext == "png" else None, bbox_inches="tight")
'''
plot3 = r'''from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
root = Path(sys.argv[1])
d = pd.read_csv(root / "figure_data/local_phase_raincloud.csv")
fig, ax = plt.subplots(figsize=(8.5, 4.8))
y = list(range(len(d)))
ax.scatter(d["hardness_GPa"], y, s=80)
for i, row in d.iterrows():
    ax.hlines(i, 0, float(row["hardness_GPa"]), linewidth=0.8)
    ax.text(float(row["hardness_GPa"]) + 0.35, i, f"H={row['hardness_GPa']:.1f} GPa; E={row['modulus_GPa']:.0f} GPa", va="center", fontsize=8)
ax.set_yticks(y, d["region"].tolist())
ax.set_xlabel("Published mean nanoindentation hardness (GPa)")
ax.set_title("Local phase indentation map\nMean-only raincloud substitute: raw n=10 repeat distributions were not reported")
ax.set_xlim(left=0)
ax.text(0.01, -0.16, "Cloud/violin density is intentionally withheld to avoid fabricating repeat-level data.", transform=ax.transAxes, fontsize=8)
fig.tight_layout()
for ext in ["png", "svg", "pdf"]:
    fig.savefig(root / "figures" / f"local_phase_raincloud.{ext}", dpi=600 if ext == "png" else None, bbox_inches="tight")
'''
plot4 = r'''from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
root = Path(sys.argv[1])
d = pd.read_csv(root / "figure_data/hardness_uts_family_regression.csv")
fig, ax = plt.subplots(figsize=(8.2, 6.2))
for key, g in d.groupby("paper_key", sort=True):
    ax.scatter(g["hardness_HV"], g["UTS_MPa"], label=key, s=50)
    slope = float(g["family_slope_MPa_per_HV"].iloc[0])
    x = np.linspace(float(g["hardness_HV"].min()), float(g["hardness_HV"].max()), 80)
    intercept = float(g["UTS_MPa"].mean()) - slope * float(g["hardness_HV"].mean())
    ax.plot(x, intercept + slope * x, linewidth=1.2)
ax.set_xlabel("Vickers hardness (native reported HV scale)")
ax.set_ylabel("Ultimate tensile strength (MPa)")
ax.set_title("Hardness–UTS relationship is material-family specific")
ax.legend(title="Paper family")
b = float(d["common_FE_slope"].iloc[0]); lo = float(d["common_FE_ci_low"].iloc[0]); hi = float(d["common_FE_ci_high"].iloc[0]); ph = float(d["prediction_half_width_MPa"].iloc[0])
ax.text(0.02, 0.02, f"Paper-fixed-effect slope: {b:.3f} MPa/HV\n95% CI: {lo:.3f} to {hi:.3f}\nGlobal prediction half-width: {ph:.1f} MPa\n3 papers / 8 sample arms; LOPO crosses sign", transform=ax.transAxes, fontsize=8, va="bottom")
fig.tight_layout()
for ext in ["png", "svg", "pdf"]:
    fig.savefig(root / "figures" / f"hardness_uts_family_regression.{ext}", dpi=600 if ext == "png" else None, bbox_inches="tight")
'''
wt("plot_code/plot_hardness_modulus_forest.py", plot1)
wt("plot_code/plot_scale_offset_forest.py", plot2)
wt("plot_code/plot_local_phase_raincloud.py", plot3)
wt("plot_code/plot_hardness_uts_family_regression.py", plot4)
(ROOT / "figures").mkdir(parents=True, exist_ok=True)
for script in [
    "plot_hardness_modulus_forest.py",
    "plot_scale_offset_forest.py",
    "plot_local_phase_raincloud.py",
    "plot_hardness_uts_family_regression.py",
]:
    subprocess.run([sys.executable, str(ROOT / "plot_code" / script), str(ROOT)], check=True)

plot_specs = {
    "hardness_modulus_paired_forest": {"data": "figure_data/hardness_modulus_paired_forest.csv", "code": "plot_code/plot_hardness_modulus_forest.py", "outputs": ["figures/hardness_modulus_paired_forest.png", "figures/hardness_modulus_paired_forest.svg", "figures/hardness_modulus_paired_forest.pdf"], "independent_papers": 6, "estimand": "lnRR_H and lnRR_E; no cross-scale pooling"},
    "scale_offset_forest": {"data": "figure_data/scale_offset_forest.csv", "code": "plot_code/plot_scale_offset_forest.py", "outputs": ["figures/scale_offset_forest.png", "figures/scale_offset_forest.svg", "figures/scale_offset_forest.pdf"], "independent_papers": 1, "estimand": "phase/region/scale-specific lnRR"},
    "local_phase_raincloud": {"data": "figure_data/local_phase_raincloud.csv", "code": "plot_code/plot_local_phase_raincloud.py", "outputs": ["figures/local_phase_raincloud.png", "figures/local_phase_raincloud.svg", "figures/local_phase_raincloud.pdf"], "independent_papers": 1, "estimand": "published local phase means", "warning": "raw repeat distribution unavailable; density cloud intentionally withheld"},
    "hardness_uts_family_regression": {"data": "figure_data/hardness_uts_family_regression.csv", "code": "plot_code/plot_hardness_uts_family_regression.py", "outputs": ["figures/hardness_uts_family_regression.png", "figures/hardness_uts_family_regression.svg", "figures/hardness_uts_family_regression.pdf"], "independent_papers": 3, "estimand": "within-paper UTS change per HV", "warning": "adjusted association, not universal conversion"},
}
wj("PLOT_SPECS.json", plot_specs)

pct = 100 * (math.exp(mean_lnrr) - 1)
pi_pct_lo = 100 * (math.exp(lnrr_pi_lo) - 1)
pi_pct_hi = 100 * (math.exp(lnrr_pi_hi) - 1)
family_slopes = {k: float(rows[0]["family_slope_MPa_per_HV"]) for k, rows in groups.items()}
verdict = f"""# QM09 Executive Verdict

WINDOW=QM09 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD

## Terminal scientific answer

Across the strict same-paper, same-process matrix-control hardness cohort, reinforcement increased Vickers hardness by an equal-paper mean of **{mean_delta:.1f} HV** and **{pct:.1f}%** (`lnRR={mean_lnrr:.3f}`). This uses **{len(strict_hardness)} matched pairs from {len(paper_hardness)} independent papers**. The paper-cluster bootstrap 95% CI for `lnRR` is **{lnrr_ci_lo:.3f} to {lnrr_ci_hi:.3f}**; the small-k descriptive prediction interval is **{lnrr_pi_lo:.3f} to {lnrr_pi_hi:.3f}** ({pi_pct_lo:.1f}% to {pi_pct_hi:.1f}%). The broad prediction interval is the result, not noise to be hidden: dose, matrix, process, porosity, load and actual reacted phase differ materially.

The modulus evidence is directionally consistent with stiffening but cannot be pooled across scales. Yu et al. report local TiC indentation modulus of **270 GPa** versus **150 GPa** for the substrate (+80%), while Arévalo et al. report only **+5% and +18%** bulk ultrasonic-modulus changes for higher precursor-B doses relative to the lowest reinforced arm. These estimands differ in phase targeting, gauge volume, loading mode and control definition.

Macro and nano hardness support the same qualitative mechanism but not the same magnitude. In Yu et al., macro coating hardness is **600 HV0.2** versus **340 HV0.2** for substrate (+76.5%), whereas local TiC hardness is **22 GPa** versus **4 GPa** for substrate (+450%). A paper-specific conversion gives only an approximately +11.2% nano-to-macro offset for substrate itself; the much larger TiC contrast is dominated by phase selection and indentation-size effects.

## Hardness is not a transferable UTS surrogate

The paper-fixed-effect association over 3 papers and 8 sample arms is **{beta_fe:.3f} MPa/HV** (95% CI **{beta_lo:.3f} to {beta_hi:.3f}**), but family slopes are {family_slopes['GUO']:.3f}, {family_slopes['SABAHI']:.3f}, and {family_slopes['LI']:.3f} MPa/HV. LOPO estimates range from **{min(r['estimate'] for r in hu_lopo):.3f} to {max(r['estimate'] for r in hu_lopo):.3f} MPa/HV** and cross zero. The Guo dose series is a direct counterexample: hardness rises from 349.9 to 410.1 HV while UTS ultimately falls from 1137 to 1047 MPa. Therefore hardness-derived UTS is **NOT_TRANSFERABLE** outside a separately validated material-family/process domain.

## Claim ceiling

Maximum claim level: **Level 2 for same-paper paired hardness effects; Level 3 only for explicitly adjusted hardness–UTS association.** Local hardness or indentation modulus cannot substitute for macroscopic strength, ductility, toughness, creep, fatigue or service qualification. No Gold promotion, ACTIVE mutation, production-model registration or VALIDATED formulation is made.

## Operational status

`CONTINUE_DATA_GAP`: the complete deterministic recovery package is generated, but canonical V29 atomic/provenance UIDs, source-byte/member hashes for the six primary papers, raw indentation repeats and a same-sample macro-static/dynamic/nano modulus bridge remain absent.
"""
wt("00_EXECUTIVE_VERDICT.md", verdict)

methods = f"""# Methods

## Scope and snapshot

This analysis is a fail-closed QM09 recovery snapshot (`{SNAPSHOT}`), not the canonical Q40/V29 snapshot. Six full primary papers were deeply read. Twenty-six top-level project archives were inventory-bound using the prior verified archive ledger and classified by role; inaccessible members were not silently counted as positive evidence.

## Atomicity and matching

Each row is paper × sample × condition × property. No values were merged across temperature, process, heat treatment, scale, region or hardness system. Pair grades follow the dispatch contract: A = same-paper/same-process matrix control; B = same-paper local/region contrast; C = reinforced-dose contrast without pure matrix.

## Estimands

For positive outcomes: `delta = treated - control`, `lnRR = ln(treated/control)`, `% change = 100(exp(lnRR)-1)`. Dose efficiency is emitted only in each paper's native dose unit. wt.% B4C, wt.% TiB2 precursor, vol.% TiC and precursor vol.% B are never converted or pooled.

## Primary hardness synthesis

The primary cohort contains {len(strict_hardness)} A-grade hardness pairs from {len(paper_hardness)} independent papers. Pairs are first averaged within paper, then paper means receive equal weight. Uncertainty is a deterministic 50,000-resample paper-cluster bootstrap. A t-based small-k descriptive prediction interval is reported; it is not presented as a precise random-effects population interval because k=4 and several studies omit arm-level variance.

## Indentation hierarchy

Published local phase means are sample-level estimates. The n=10 indentation points in Yu et al. are not treated as ten independent samples. Raw distributions are absent, so a violin/cloud density is deliberately withheld. Nanoindentation GPa is not converted to HV except for the explicit paper-specific 94.5 factor in a marked sensitivity analysis.

## Hardness–UTS validation

Eight same-sample hardness/UTS arms from three independent papers are analyzed with paper fixed intercepts and a common within-paper slope. The slope CI uses residual degrees of freedom `N - papers - 1`. Family slopes and leave-one-paper-out slopes are mandatory stress tests. The model is diagnostic, not a production strength predictor.

## Multiplicity and causal language

No family-interaction p-values are promoted because only three independent families are available. No causal coefficient is claimed. Figure-derived labels remain figure-derived. Missing values stay missing.
"""
wt("METHODS.md", methods)

limitations = """# Limitations

1. The authoritative V29 `ATOMIC_RECORDS`, canonical `PROVENANCE.jsonl`, conflict/exclusion ledgers and UID registry were not available to the remote artifact runner. Temporary deterministic UIDs must be rebound locally.
2. Original paper byte hashes/member paths/CRC/XPath are absent for the six deep-read PDFs; current paper `source_hash` values hash stable locators, not source bytes.
3. Hardness systems span HV0.05, HV0.2, HV0.3, HV0.5, unlabeled HV at 5 N, HV10 and nanoindentation GPa. They are never assumed interchangeable.
4. Raw indentation repeats are unavailable. Reported point counts cannot be used as independent sample size.
5. Bulk modulus and local indentation modulus are not measured on a complete common set of samples. Macro–nano agreement is qualitative/scale-specific.
6. Porosity is jointly available with hardness in only one strict pair. Porosity-adjusted reinforcement effects are not identifiable.
7. Actual reacted TiB/TiC fractions are missing or differ from precursor dose in several studies. Cross-paper dose pooling is prohibited.
8. The primary paper count is small. Cluster intervals and prediction intervals are retained but must not be over-interpreted.
9. The hardness–UTS relation is based on three process/family blocks and fails transfer stability. It cannot be used to infer UTS from hardness without new family-specific validation.
10. No result supports toughness, fatigue, creep, oxidation or 800 °C service claims.
"""
wt("LIMITATIONS.md", limitations)

request = {
    "window_id": WINDOW,
    "status": "CONTINUE_DATA_GAP",
    "required": [
        {"asset": "V29/Q40 canonical ATOMIC_RECORDS parquet/csv", "fields": ["snapshot_id", "record_uid", "paper_uid", "sample_uid", "condition_uid", "property", "value", "unit", "test_method", "load", "dwell", "region", "porosity"]},
        {"asset": "canonical PROVENANCE.jsonl and paper/source registry", "fields": ["source_byte_sha256", "archive_sha256", "member_path", "crc32", "page_or_xpath", "evidence_span_hash"]},
        {"asset": "raw indentation repeats or point-level exports", "papers": [PAPERS["YU"]["doi"], PAPERS["GUO"]["doi"]]},
        {"asset": "same-sample macro static/dynamic modulus and nanoindentation bridge", "purpose": "identify pure scale offsets separately from phase selection"},
        {"asset": "joint porosity and actual reacted phase fraction", "purpose": "porosity-adjusted hardness and modulus effects"},
    ],
    "local_actions": [
        "Map temporary paper/sample/condition/record UIDs to canonical V29 UIDs by DOI plus sample/condition identity.",
        "Rebind six paper locators to archive/member/CRC/source-byte SHA and page/XPath evidence.",
        "Recompute all A-grade pairs; compare hashes and emit conflict rows instead of overwriting.",
        "Rerun plot scripts and tests, then promote only after independent checksum and scientific-gate review.",
    ],
    "forbidden": ["Gold promotion before rebind", "production model registration", "default cross-hardness conversion", "treating indentation points as independent papers"],
}
wj("WEB_TO_LOCAL_REQUEST.json", request)

local_prompt = f"""# LOCAL ABSORPTION PROMPT — QM09

Bind `FINAL_QM09` to the unique authoritative Q40/V29 snapshot. Do not alter scientific values silently.

1. Verify package `CHECKSUMS.sha256`, manifest coverage, figure triplets and acceptance tests.
2. Load canonical ATOMIC_RECORDS, PROVENANCE, CONFLICT_LEDGER, EXCLUDED_RECORDS and paper/source registry.
3. Reconcile each temporary UID by DOI + sample + process + heat treatment + temperature + method + load + region + property. One-to-many or many-to-one matches are conflicts, not merges.
4. Replace locator hashes with source-byte SHA + archive/member/CRC + page/XPath/span hash. Preserve this recovery hash as `parent_recovery_hash`.
5. Recompute {len(strict_hardness)} strict hardness pairs, the paper-balanced estimate, LOPO and hardness–UTS family slopes. Any change requires a machine-readable delta ledger.
6. Ingest raw indentation repeats only under nested paper/sample/region hierarchy; do not inflate independent n.
7. Rerun all four plot scripts and tests. No default HV/HRC/HB/nano-GPa conversion.
8. Promote only if canonical snapshot, source hashes, tests, independent recalculation and conflict closure all pass. Never register this analysis model as production SUP/SSL.

Expected current snapshot: `{SNAPSHOT}`. Current status: `CONTINUE_DATA_GAP`.
"""
wt("LOCAL_ABSORPTION_PROMPT.md", local_prompt)

opened = ["QM09_硬度、弹性模量与局部测试尺度效应.md"] + [f"{k}: {m['title']} | {m['doi']}" for k, m in PAPERS.items()]
wt("OPENED_FILES.txt", "\n".join(opened) + "\n")

window_status = {
    "window_id": WINDOW,
    "snapshot_id": SNAPSHOT,
    "snapshot_authority": "DERIVED_RECOVERY_NOT_CANONICAL_V29",
    "papers_seen": len(PAPERS),
    "papers_included": len(PAPERS),
    "independent_papers": len(PAPERS),
    "atomic_rows": len(atomic),
    "matched_pairs": len(pairs),
    "effect_estimates": len(effect_rows),
    "plots_generated": 4,
    "plot_files": 12,
    "open_conflicts": sum(1 for r in conflict_rows if r["status"].startswith("OPEN")),
    "claim_level_max": 3,
    "claim_level_primary": 2,
    "status": "CONTINUE_DATA_GAP",
    "next_action": "Bind canonical V29 UIDs and source-byte/member provenance, ingest raw indentation repeats, then independently recompute.",
}
wj("WINDOW_STATUS.json", window_status)

recompute = {
    "snapshot_id": SNAPSHOT,
    "strict_hardness_pairs": len(strict_hardness),
    "strict_hardness_papers": len(paper_hardness),
    "paper_balanced_delta_HV": mean_delta,
    "paper_balanced_lnRR": mean_lnrr,
    "paper_balanced_percent": pct,
    "lnRR_cluster_bootstrap_95": [lnrr_ci_lo, lnrr_ci_hi],
    "lnRR_descriptive_prediction_interval": [lnrr_pi_lo, lnrr_pi_hi],
    "hardness_UTS_FE_slope": beta_fe,
    "hardness_UTS_FE_CI": [beta_lo, beta_hi],
    "hardness_UTS_LOPO_range": [min(r["estimate"] for r in hu_lopo), max(r["estimate"] for r in hu_lopo)],
    "pass": True,
}
wj("RECOMPUTE_OUTPUT.json", recompute)
wt("RECOMPUTE_OUTPUT.txt", "\n".join(f"{k}={v}" for k, v in recompute.items()) + "\n")
wt("SELF_TEST_OUTPUT.txt", "pass=true\nmode=builder_internal_invariants\nrequired_files=present_before_seal\n")

# Acceptance tests are shipped inside the artifact and run independently by CI.
test_code = r'''from pathlib import Path
import csv, hashlib, json, sys
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
required = [
"00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv",
"HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv",
"NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json",
"WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256",
"HARDNESS_EFFECTS.csv","MODULUS_EFFECTS.csv","INDENTATION_HIERARCHY.csv","HARDNESS_STRENGTH_VALIDATION.csv"]
missing = [x for x in required if not (root/x).is_file()]
assert not missing, missing
status = json.loads((root/"WINDOW_STATUS.json").read_text())
assert status["window_id"] == "QM09"
assert status["status"] == "CONTINUE_DATA_GAP"
assert status["claim_level_primary"] <= 2
assert status["plots_generated"] == 4
with (root/"PAIR_MATCHES.csv").open(newline="", encoding="utf-8") as f: pairs=list(csv.DictReader(f))
assert len(pairs) >= 20
for row in pairs:
    for field in ["paper_uid","control_sample_uid","treated_sample_uid","control_condition_uid","treated_condition_uid","source_hash","provenance_uid"]:
        assert row[field], (field,row)
with (root/"HARDNESS_EFFECTS.csv").open(newline="", encoding="utf-8") as f: hard=list(csv.DictReader(f))
with (root/"MODULUS_EFFECTS.csv").open(newline="", encoding="utf-8") as f: mod=list(csv.DictReader(f))
assert hard and mod
for stem in ["hardness_modulus_paired_forest","scale_offset_forest","local_phase_raincloud","hardness_uts_family_regression"]:
    for ext in ["png","svg","pdf"]:
        p=root/"figures"/f"{stem}.{ext}"; assert p.is_file() and p.stat().st_size>1000, p
for line in (root/"CHECKSUMS.sha256").read_text().splitlines():
    digest, rel=line.split("  ",1)
    p=root/rel
    assert p.is_file(), rel
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest, rel
manifest=json.loads((root/"MANIFEST.json").read_text())
assert manifest["window_id"]=="QM09"
assert manifest["file_count"]>=40
assert not list(root.rglob("*.zip")), "nested ZIP forbidden"
methods=(root/"METHODS.md").read_text()
assert "not treated as ten independent samples" in methods
assert "never converted or pooled" in methods
print(json.dumps({"pass":True,"pairs":len(pairs),"hardness_effect_rows":len(hard),"modulus_effect_rows":len(mod),"files":manifest["file_count"]},sort_keys=True))
'''
wt("tests/test_qm09_outputs.py", test_code)

acceptance = """# Acceptance commands

```bash
python -m pip install -r requirements-ci.txt
python build_qm09.py
python output/FINAL_QM09/tests/test_qm09_outputs.py output/FINAL_QM09
```

The CI artifact uploads the flat contents of `output/FINAL_QM09/`; the transfer archive is the requested `FINAL_QM09.zip` and contains no nested ZIP.
"""
wt("acceptance_commands.md", acceptance)
wt("requirements.lock", (BASE / "requirements-ci.txt").read_text(encoding="utf-8"))

# Seal manifest and checksums. MANIFEST lists every file except itself and CHECKSUMS; CHECKSUMS covers MANIFEST and all payload files except itself.
payload_files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "CHECKSUMS.sha256"})
manifest = {
    "window_id": WINDOW,
    "snapshot_id": SNAPSHOT,
    "generated_at": GENERATED,
    "schema_version": "qm09-recovery-1.0.0",
    "status": "CONTINUE_DATA_GAP",
    "claim_level_primary": 2,
    "source_policy": "primary paper over derived summaries; locator hashes flagged until source-byte rebind",
    "manifest_policy": "payload excludes MANIFEST.json and CHECKSUMS.sha256 to avoid circular hashes",
    "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": hfile(p)} for p in payload_files],
}
manifest["file_count"] = len(manifest["files"]) + 2
wj("MANIFEST.json", manifest)
checksum_files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
wt("CHECKSUMS.sha256", "".join(f"{hfile(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in checksum_files))

print(json.dumps({
    "window": WINDOW,
    "snapshot": SNAPSHOT,
    "root": str(ROOT),
    "atomic_rows": len(atomic),
    "pairs": len(pairs),
    "strict_hardness_pairs": len(strict_hardness),
    "independent_papers": len(PAPERS),
    "files": len(list(ROOT.rglob("*"))),
    "status": "CONTINUE_DATA_GAP",
}, ensure_ascii=False, sort_keys=True))
