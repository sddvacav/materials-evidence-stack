#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "v31" / "control" / "MC02" / "_build"
PKG = WORK / "FINAL_MC02"
DELIVERY = ROOT / "delivery" / "MC02"
ZIP_PATH = DELIVERY / "FINAL_MC02.zip"
SHA_PATH = DELIVERY / "FINAL_MC02.sha256"
SUMMARY_PATH = DELIVERY / "FINAL_MC02.summary.json"
BATCH = "V31_TITMC_MODEL_WAR_20260713"
WINDOW = "MC02"
STATUS = "BLOCKED_INPUT"
GENERATED_AT = "2026-07-13T03:54:47.502717+00:00"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
REQUIRED_AUTHORITY = [
    "v31/control/MC01/MODEL_INPUT_SNAPSHOT.json",
    "v31/control/MC01/SPLIT_AUTHORITY.json",
    "v31/control/MC01/SEED_REGISTRY.json",
    "v31/gold/SCREENED_GOLD.parquet",
    "v29/ATOMIC_RECORDS.parquet",
    "v29/PROVENANCE.jsonl",
    "v29/CONFLICT_LEDGER.csv",
]
ALLOWED_STATES = {
    "USED_DIRECTLY", "USED_AS_REFERENCE", "SUPERSEDED_BY_HASH",
    "OUT_OF_SCOPE", "BLOCKED_CORRUPT", "NOT_RELEVANT_TO_WINDOW",
}
REQUIRED_MEMBERS = [
    "00_EXECUTIVE_VERDICT.md", "SOURCE_UTILIZATION_MATRIX.csv",
    "PRIMARY_LITERATURE_AUDIT.csv", "INPUT_LEDGER.csv", "DATASET_CARD.md",
    "RUN_CONFIG.yaml", "ENVIRONMENT_LOCK.txt", "TRAINING_LOG.jsonl",
    "OOF_PREDICTIONS.parquet", "METRICS_BY_FOLD.csv", "METRICS_BY_SEED.csv",
    "ERROR_ANALYSIS.csv", "MODEL_CARD.md", "METHODS.md", "LIMITATIONS.md",
    "NEGATIVE_RESULTS.md", "OPEN_ISSUES.md", "WEB_TO_LOCAL_REQUEST.json",
    "LOCAL_ABSORPTION_PROMPT.md", "WINDOW_STATUS.json", "MANIFEST.json",
    "CHECKSUMS.sha256", "TARGET_SEMANTICS.csv", "FEATURE_REGISTRY.csv",
    "FEATURE_FIREWALL.md", "PREPROCESSING_CONTRACT.json",
    "MISSINGNESS_POLICY.md", "COMPOSITION_CONSTRAINTS.md",
    "TARGET_TASK_MATRIX.csv", "ORIGINAL_PAPER_SEMANTIC_CHECK.csv", "README.md",
    "DESIGN.md", "ACCEPTANCE_COMMANDS.md", "requirements.lock", "run_all.sh",
    "run_all.ps1", "configs/mc02.yaml", "src/__init__.py",
    "src/mc02_contract.py", "src/build_training_table.py",
    "src/validate_package.py", "src/resume.py", "src/infer.py",
    "tests/test_contract.py", "artifacts/CONTROL_CONTRACT.json",
    "artifacts/OOF_SCHEMA.json", "artifacts/README.md",
    "artifacts/checkpoints/README.md", "TEST_REPORT.txt", "VALIDATION_REPORT.json",
]


def dedent(value: str) -> str:
    return textwrap.dedent(value).lstrip("\n")


def write_text(rel: str, value: str) -> None:
    path = PKG / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(value), encoding="utf-8", newline="\n")


def write_json(rel: str, value: Any) -> None:
    write_text(rel, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_csv(rel: str, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path = PKG / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_rows() -> list[dict[str, Any]]:
    fields = []
    prior = [
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
    ]
    rows: list[dict[str, Any]] = []
    for name, digest, kind, size, members, priority in prior:
        rows.append({
            "source_name": name, "source_locator": f"/mnt/data/{name}",
            "priority": priority, "hash": digest, "hash_kind": kind,
            "hash_scope": "PRIOR_CANONICAL_AUDIT; CURRENT_RUNTIME_REBIND_REQUIRED",
            "bytes_prior": size, "member_count_prior": members,
            "opened_or_consumed": "YES_REFERENCE_LEDGER",
            "terminal_use_status": "USED_AS_REFERENCE",
            "window_relevance": "registered engineering/data/harness reference; not substituted for MC01 authority",
            "exclusion_or_use_reason": "MC01 snapshot/split/seed absent; no internal matrix was silently promoted to authority.",
        })
    v27 = [
        (1, "(12)", "42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0", 499460308, 15),
        (2, "(14)", "05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193", 490572377, 154),
        (3, "(15)", "535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917", 490379244, 4610),
        (4, "(14)", "bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a", 490620829, 7747),
        (5, "(12)", "1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1", 490762545, 10068),
        (6, "(15)", "5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13", 490902802, 11778),
        (7, "(14)", "4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1", 491018449, 13499),
        (8, "(12)", "478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341", 491203652, 15702),
        (9, "(13)", "b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a", 491501617, 20036),
        (10, "", "faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d", 367381900, 57717),
    ]
    for number, suffix, digest, size, members in v27:
        name = f"TITMC_V27_LIT_WEB_P{number:03d}_OF_010{suffix}.zip" if number < 10 else "TITMC_V27_LIT_WEB_P010_OF_010.zip"
        rows.append({
            "source_name": name, "source_locator": f"/mnt/data/{name}",
            "priority": "P0_PRIMARY_ORIGINAL", "hash": digest,
            "hash_kind": "ZIP_CENTRAL_DIRECTORY_SHA256",
            "hash_scope": "PRIOR_CANONICAL_UNSUFFIXED_COPY; CURRENT_UPLOAD_REBIND_REQUIRED",
            "bytes_prior": size, "member_count_prior": members,
            "opened_or_consumed": "YES_SCOPED_ORIGINAL_AUDIT",
            "terminal_use_status": "USED_AS_REFERENCE",
            "window_relevance": "primary-literature universe; targeted originals below used directly",
            "exclusion_or_use_reason": "Corpus registered; training rows withheld until V29/MC01 identity authority exists.",
        })
    rows += [
        {
            "source_name": "V31_TITMC_MODEL_WAR_MASTER_PROMPT_20260713.md",
            "source_locator": "project file library", "priority": "P0_CONTRACT",
            "hash": "7e8aea57f74d037282fd59c2691cd43faa1592bb9d0701cf7e4b9e26693c8de7",
            "hash_kind": "FULL_FILE_SHA256", "hash_scope": "PROJECT_DELIVERY_SUMMARY",
            "bytes_prior": "", "member_count_prior": 1, "opened_or_consumed": "YES",
            "terminal_use_status": "USED_DIRECTLY",
            "window_relevance": "W0 no-training and input-gate authority",
            "exclusion_or_use_reason": "Direct governing contract.",
        },
        {
            "source_name": "FINAL_MC00.zip", "source_locator": "project file library",
            "priority": "P1_PROVENANCED_STRUCTURED",
            "hash": "c507a1250062d13272a6ab8bcb65b7e9d6f6ac796435287487c954c9e06ac000",
            "hash_kind": "FULL_FILE_SHA256", "hash_scope": "DELIVERY_SHA_ONLY; NOT_SNAPSHOT_SHA",
            "bytes_prior": "", "member_count_prior": "", "opened_or_consumed": "YES_REFERENCE_ONLY",
            "terminal_use_status": "USED_AS_REFERENCE",
            "window_relevance": "MC00 exists but cannot substitute MC01 snapshot/split/seed",
            "exclusion_or_use_reason": "No snapshot identity derived from delivery SHA.",
        },
    ]
    assert all(row["terminal_use_status"] in ALLOWED_STATES for row in rows)
    return rows


def paper_rows() -> list[dict[str, str]]:
    return [
        {"doi":"10.1016/j.msea.2023.145806","title":"Tensile properties of Ti6.5Al2Zr1Mo1V titanium alloy fabricated via electron beam selective melting at high temperature","source_type":"FULL_ORIGINAL_PDF","source_hash":"UNBOUND_FILE_LIBRARY_COPY","source_locator":"Methods pp.2-3; Table 2 p.3","semantic_objects_checked":"UTS;YS;EL;temperature;direction;strain rate;replicates;stabilization","finding":"INSTRON 5569 high-temperature tension at 5e-4 s^-1; three samples/condition; 15 min stabilization; horizontal middle-region specimens. At 773/823/873/923/973/1023 K: UTS 636/580/513/409/296/238 MPa; EL 18.8/19.7/23.8/32.5/34.5/47.3%; YS 498/474/453/378/272/209 MPa. Post-test TEM/fracture/dislocation state is leakage.","decision":"USED_DIRECTLY","evidence_level":"P0_PRIMARY_ORIGINAL","conflict_or_limit":"YS proof method not explicit in inspected passage; EBSM is not L-DED."},
        {"doi":"10.1016/j.matdes.2015.08.112","title":"Effect of dispersion method on deterioration, interfacial interactions and re-agglomeration of carbon nanotubes in titanium metal matrix composites","source_type":"FULL_ORIGINAL_PDF","source_hash":"UNBOUND_FILE_LIBRARY_COPY","source_locator":"Experimental 2.1-2.5; Tables 1-3; Fig.10","semantic_objects_checked":"precursor;actual phase;nano hardness;indentation modulus;load;dwell;replication","finding":"0.5 wt.% MWCNT is precursor and in-situ TiC is actual product phase. Hysitron TI-950/Berkovich, 5000 uN, 10 s load/10 s dwell/10 s unload, >=20 indents in 5x4 array at three positions, 20 um spacing, Oliver-Pharr. Unmilled Ti hardness 4.285 GPa and indentation modulus 100.056 GPa.","decision":"USED_DIRECTLY","evidence_level":"P0_PRIMARY_ORIGINAL","conflict_or_limit":"Never relabel indentation modulus/hardness as tensile properties."},
        {"doi":"10.1016/j.matdes.2013.04.048","title":"TiB whiskers reinforced Ti60 composites with network microstructure","source_type":"PUBLISHER_XML","source_hash":"7b009eb2b56153b4b91960e9c00f3034c4760046136d9040475490632994d902","source_locator":"P009 XML","semantic_objects_checked":"matrix;TiBw vol%;UTS;temperature;EL provenance","finding":"Direct text supports Ti60 and 5/8 vol.% TiBw UTS at 600/700/800 C; EL remains figure-derived.","decision":"USED_DIRECTLY","evidence_level":"DIRECT_TEXT_UTS_FIGURE_DERIVED_EL","conflict_or_limit":"Do not promote figure-derived EL to direct text."},
        {"doi":"10.1016/j.jallcom.2025.180981","title":"Microscopic structural modeling and mechanical behavior of TiB reinforced titanium composites","source_type":"PUBLISHER_XML","source_hash":"da00d93156e5a71fcd6b30539eb4b39757ce79fa149af4347864c0f7a20012f0","source_locator":"P006 XML","semantic_objects_checked":"network/uniform/matrix UTS;temperature;uncertainty","finding":"Direct text reports network, uniform and matrix UTS at 600/700/800 C with uncertainty.","decision":"USED_DIRECTLY","evidence_level":"DIRECT_TEXT_ORIGINAL_XML","conflict_or_limit":"Architecture arms remain separate."},
        {"doi":"10.1016/j.jallcom.2025.181955","title":"Enhanced high temperature properties of TiBw/TA15 by multi-DOF forming","source_type":"PUBLISHER_XML","source_hash":"bbf5b022d8f3aac998a895d42a3770a3d0637aa9ca7a547ce2d1de4d373ce655","source_locator":"P006 XML Table 1","semantic_objects_checked":"800 C YS;UTS;EL;replication","finding":"Direct table reports 800 C YS/UTS/EL for as-sintered and multi-DOF formed TiBw/TA15; at least three tests.","decision":"USED_DIRECTLY","evidence_level":"DIRECT_TABLE_TEXT_ORIGINAL_XML","conflict_or_limit":"Process states remain separate."},
        {"doi":"10.1016/j.matdes.2016.03.091","title":"Effect of Zr, Mo and TiC on cast titanium matrix composites","source_type":"PUBLISHER_XML","source_hash":"9b0d5b2ef42506159b5acc982ba05c7318e43fb1244c63f1a404be58657ba94a","source_locator":"P008 XML","semantic_objects_checked":"800 C UTS;EL;uncertainty;composition arms","finding":"Original table reports five 800 C UTS/EL arms with uncertainties.","decision":"USED_DIRECTLY","evidence_level":"DIRECT_TABLE_TEXT_ORIGINAL_XML","conflict_or_limit":"Composition arms remain distinct samples."},
        {"doi":"10.1016/0921-5093(94)90373-5","title":"Properties of SiC-fibre reinforced titanium alloys","source_type":"PUBLISHER_XML","source_hash":"8753e100a19623ad8264f0d8c1ec95c430c8ef6c183e5b8b1e42d0b771cd87d4","source_locator":"P009 XML","semantic_objects_checked":"UTS;temperature;fibre fraction;matrix;EL missingness","finding":"Direct text reports 1500 MPa UTS at 800 C for 0.40 vf SiC-fibre/IMI834.","decision":"USED_DIRECTLY","evidence_level":"DIRECT_TEXT_ORIGINAL_XML","conflict_or_limit":"EL is NOT_REPORTED, never zero."},
        {"doi":"10.1016/j.matdes.2015.07.058","title":"Heat treatment effects on TiBw/near-alpha Ti composites","source_type":"PUBLISHER_XML","source_hash":"fed57cf5ba75312c691092603ebcd9a6210176f91b68a31d14de3fe54886412e","source_locator":"P009 XML","semantic_objects_checked":"UTS;temperature;heat-treatment state;EL missingness","finding":"Direct text reports as-aged UTS 760/540/400 MPa at 700/750/800 C.","decision":"USED_DIRECTLY","evidence_level":"DIRECT_TEXT_ORIGINAL_XML_UTS","conflict_or_limit":"Qualitative EL cannot become a numeric label."},
    ]


def target_rows() -> list[dict[str, str]]:
    specs = [
        ("TENSILE_UTS_ENGINEERING","ultimate_tensile_strength","Maximum engineering tensile stress; not true-stress peak.","MPa","UTS;tensile strength;ultimate strength","compressive strength;true-stress peak;fracture stress","tension","engineering curve or explicit UTS","test_temperature_C;specimen_direction;strain_rate_s-1;environment","identity","mode and temperature required"),
        ("TENSILE_YS_0P2","yield_strength_0p2","Explicit 0.2% offset/proof tensile stress.","MPa","YS;Rp0.2;0.2% proof stress","unspecified YS;compressive yield","tension","proof method explicit","test_temperature_C;specimen_direction;strain_rate_s-1","identity","method explicit"),
        ("TENSILE_YS_UNSPECIFIED","yield_strength_unspecified","Reported tensile yield with proof method absent.","MPa","yield strength","Rp0.2 when explicit;compression","tension","retain separate","test_temperature_C;specimen_direction;strain_rate_s-1","identity","sensitivity only"),
        ("TENSILE_EL_TOTAL","elongation_to_fracture","Gauge-length-dependent engineering elongation to fracture.","%","EL;elongation;A%","uniform elongation;RA;compression strain","tension","gauge/standard retained","test_temperature_C;direction;strain_rate;gauge_length","identity","separate from uniform/RA"),
        ("TENSILE_EL_UNIFORM","uniform_elongation","Engineering strain at onset of necking.","%","uniform elongation","total EL;RA","tension","explicit uniform definition","temperature;direction;strain_rate","identity","separate task"),
        ("TENSILE_RA","reduction_in_area","Area reduction at fracture.","%","RA;reduction of area","elongation","tension","final/initial area or direct report","temperature;direction","identity","separate task"),
        ("COMPRESSIVE_YIELD","compressive_yield_strength","Yield/proof stress in compression.","MPa","CYS;compressive yield","tensile YS","compression","compression method explicit","temperature;direction;strain_rate","identity","never pool tensile"),
        ("COMPRESSIVE_STRENGTH","compressive_strength","Peak or criterion-specific compressive stress.","MPa","compressive strength","UTS","compression","peak/strain criterion explicit","temperature;direction;strain_rate;criterion","identity","criterion-specific"),
        ("HARDNESS_VICKERS","vickers_hardness","Vickers hardness with load and dwell retained.","HV","HV;Vickers","nano hardness;Rockwell","indentation","load/dwell required or missing-coded","temperature;load;dwell","identity","method/load partition"),
        ("HARDNESS_NANO","nanoindentation_hardness","Instrumented indentation hardness.","GPa","nano hardness","Vickers;macrohardness","instrumented_indentation","tip/load/dwell/method retained","temperature;tip;load;method","identity","not converted to HV"),
        ("MODULUS_TENSILE","youngs_modulus_tensile","Young modulus from tensile loading.","GPa","Young modulus;tensile modulus","indentation/dynamic modulus","tension","method retained","temperature;direction;strain_rate","identity","method-specific"),
        ("MODULUS_INDENTATION","indentation_modulus","Reduced/elastic modulus from instrumented indentation.","GPa","indentation modulus;reduced modulus","tensile Young modulus","instrumented_indentation","tip/load/analysis method retained","temperature;tip;load;method","identity","never pool tensile"),
        ("CREEP_MIN_RATE","minimum_creep_rate","Minimum steady-state creep rate.","s^-1","minimum creep rate","tensile strain rate","creep","stress/temperature/environment required","temperature;stress;environment","log10_optional","separate creep"),
        ("CREEP_RUPTURE_LIFE","creep_rupture_life","Time to rupture under fixed stress/temperature.","h","rupture life","fatigue life;exposure time","creep","stress/temperature/environment required","temperature;stress;environment","log10_optional","separate creep"),
        ("FATIGUE_LIFE","fatigue_cycles_to_failure","Cycles to failure under declared fatigue protocol.","cycles","Nf;fatigue life","creep life","fatigue","R/frequency/control required","temperature;R;frequency;control","log10_optional","separate fatigue"),
    ]
    names = ["target_semantic_id","canonical_name","definition","canonical_unit","accepted_aliases","excluded_aliases","test_mode","method_requirements","task_partition_fields","allowed_transform","quality_gate"]
    rows = []
    for spec in specs:
        row = dict(zip(names, spec))
        row.update(label_source_headline="SCREENED_GOLD_ONLY", silver_use="SENSITIVITY_ONLY", evidence_only_use="PROHIBITED_AS_LABEL", source_example="10.1016/j.msea.2023.145806 tensile; 10.1016/j.matdes.2015.08.112 nanoindentation")
        rows.append(row)
    return rows


def feature_rows() -> list[dict[str, str]]:
    columns = ["feature_id","canonical_name","dtype","unit","semantic_role","tier","availability_time","allowed_headline","allowed_state_aware","firewall_status","reason","provenance_requirement","missing_policy"]
    rows: list[dict[str, str]] = []
    def add(*values: str) -> None:
        rows.append(dict(zip(columns, values)))
    for element in ["Al","V","Mo","Sn","Zr","Nb","Ta","W","Si","B","C","O","N","Fe","Ni","Co","Cr","Mn","Cu","Ti"]:
        add(f"COMP_{element.upper()}_WT", f"comp_{element}_wt_pct", "float64", "wt.%", "input", "EX_ANTE", "before_processing", "true", "true", "ALLOW_CONDITIONAL", "Requires composition_basis and closure policy.", "source locator plus nominal/measured/inferred flag", "preserve missing; fold-local handling")
    fixed = [
        ("COMPOSITION_BASIS","composition_basis","category","","metadata","EX_ANTE","before_processing","true","true","REQUIRED_COMPANION","Matrix nominal, bulk nominal/measured and inferred balance remain distinct.","field provenance","STRUCTURAL_MISSING forbidden"),
        ("MATRIX_FAMILY","matrix_alloy_family","category","","input","EX_ANTE","before_processing","true","true","ALLOW","Context only, not composition replacement.","grade/source","UNKNOWN"),
        ("PRECURSOR_TYPE","precursor_type","category","","input","EX_ANTE","before_processing","true","true","ALLOW","Distinct from product phase.","direct process description","UNKNOWN"),
        ("PRECURSOR_AMOUNT","precursor_amount","float64","source basis","input","EX_ANTE","before_processing","true","true","ALLOW_CONDITIONAL","Basis required; no wt/vol pooling.","amount+basis","preserve missing"),
        ("PRECURSOR_BASIS","precursor_basis","category","","metadata","EX_ANTE","before_processing","true","true","REQUIRED_COMPANION","Required for precursor amount.","direct/inferred","NOT_APPLICABLE if none"),
        ("REINF_TYPE","intended_reinforcement_type","category","","input","EX_ANTE","before_processing","true","true","ALLOW","Design intent, not actual phase.","formulation","UNKNOWN"),
        ("REINF_FRAC","intended_reinforcement_fraction","float64","source basis","input","EX_ANTE","before_processing","true","true","ALLOW_CONDITIONAL","Basis required.","amount+basis","preserve missing"),
        ("REINF_BASIS","intended_reinforcement_basis","category","","metadata","EX_ANTE","before_processing","true","true","REQUIRED_COMPANION","Required for fraction.","source basis","NOT_APPLICABLE if none"),
        ("ACTUAL_PHASE_TYPE","actual_phase_type","category","","state","PRETEST_STATE","after_processing_before_test","false","true","STATE_AWARE_ONLY","Measured product phase unavailable for prospective ex-ante model.","XRD/TEM locator","UNKNOWN"),
        ("ACTUAL_PHASE_FRAC","actual_phase_fraction","float64","source basis","state","PRETEST_STATE","after_processing_before_test","false","true","STATE_AWARE_ONLY","Never substitute for precursor dose.","measurement+basis","preserve missing"),
        ("ACTUAL_PHASE_BASIS","actual_phase_basis","category","","metadata","PRETEST_STATE","after_processing_before_test","false","true","STATE_AWARE_ONLY","Basis required.","measurement","NOT_APPLICABLE if absent"),
        ("PROCESS_ROUTE","process_route","category","","input","EX_ANTE","before_processing","true","true","ALLOW","Known route.","methods locator","UNKNOWN"),
    ]
    for row in fixed: add(*row)
    for fid, name, unit in [("LASER_POWER","laser_power_W","W"),("SCAN_SPEED","scan_speed_mm_s","mm/s"),("FEED_RATE","powder_feed_rate_g_min","g/min"),("LAYER_THICKNESS","layer_thickness_um","um"),("HATCH_SPACING","hatch_spacing_um","um"),("BEAM_DIAMETER","beam_diameter_um","um"),("PREHEAT_T","substrate_preheat_C","degC"),("HT_TEMP","heat_treatment_temperature_C","degC"),("HT_TIME","heat_treatment_time_h","h"),("COOLING_ROUTE","cooling_route","category")]:
        add(fid, name, "category" if unit == "category" else "float64", unit, "input", "EX_ANTE", "before_test", "true", "true", "ALLOW", "Known process variable; temperatures remain distinct.", "methods locator", "NOT_APPLICABLE or preserve missing")
    for fid, name, unit in [("DENSITY","density_g_cm3","g/cm3"),("REL_DENSITY","relative_density_pct","%"),("POROSITY","porosity_pct","%"),("GRAIN_SIZE","grain_size_um","um"),("PRIOR_BETA","prior_beta_grain_um","um"),("ALPHA_LATH","alpha_lath_thickness_um","um"),("ALPHA_FRAC","alpha_phase_fraction","%"),("BETA_FRAC","beta_phase_fraction","%"),("TEXTURE","texture_metric","method-specific"),("PRETEST_GND","pretest_gnd_density_m2","m^-2")]:
        add(fid, name, "float64", unit, "state", "PRETEST_STATE", "after_processing_before_test", "false", "true", "STATE_AWARE_ONLY", "Only preregistered state-aware task measured before target.", "method+sample+locator", "preserve missing")
    for fid, name, dtype, unit in [("TEST_MODE","test_mode","category",""),("TEST_TEMP","test_temperature_C","float64","degC"),("DIRECTION","specimen_direction","category",""),("STRAIN_RATE","strain_rate_s-1","float64","s^-1"),("ENVIRONMENT","test_environment","category",""),("GAUGE_LENGTH","gauge_length_mm","float64","mm")]:
        add(fid, name, dtype, unit, "task_context", "EX_ANTE", "before_test", "true", "true", "ALLOW_TASK_CONTEXT", "Defines task; unknown explicit.", "test methods locator", "preserve missing or UNKNOWN")
    for fid, name in [("POST_FRACTURE","post_fracture_morphology"),("POST_NECKING","post_test_necking"),("POST_TEM","post_test_tem_features"),("POST_DISLOCATION","post_test_dislocation_density"),("POST_DRX","post_test_drx_label")]:
        add(fid, name, "string", "", "post_outcome", "FORBIDDEN", "after_target_observed", "false", "false", "BLOCK", "Measured after target-generating test; direct leakage.", "n/a", "exclude")
    for fid, name in [("LABEL_UTS","uts_MPa"),("LABEL_YS","ys_MPa"),("LABEL_EL","elongation_pct"),("LABEL_H","hardness"),("LABEL_E","modulus_GPa"),("SDP","strength_ductility_product"),("DELTA_UTS","delta_uts_vs_control"),("MODEL_RESIDUAL","oof_residual"),("SHAP","shap_value"),("PREDICTION","model_prediction")]:
        add(fid, name, "float64", "", "label_or_derived", "FORBIDDEN", "target_or_post_model", "false", "false", "BLOCK", "Target, target-derived or model-derived proxy.", "n/a", "exclude")
    for fid, name in [("PAPER_ID","paper_uid"),("SAMPLE_ID","sample_uid"),("CONDITION_ID","condition_uid"),("DOI","doi")]:
        add(fid, name, "string", "", "grouping_key", "GROUP_ONLY", "identity", "false", "false", "GROUP_ONLY", "Provenance/grouping only, never predictive.", "identity authority", "no imputation")
    assert len(rows) >= 55
    return rows


def task_rows() -> list[dict[str, str]]:
    specs = [
        ("RT_TENSILE_UTS","TENSILE_UTS_ENGINEERING","tension","RT_EXACT_25C","exact","exact_or_UNKNOWN","primary"),
        ("RT_TENSILE_YS_0P2","TENSILE_YS_0P2","tension","RT_EXACT_25C","exact","exact_or_UNKNOWN","primary"),
        ("RT_TENSILE_EL_TOTAL","TENSILE_EL_TOTAL","tension","RT_EXACT_25C","exact","exact_or_UNKNOWN","primary"),
        ("HT_TENSILE_UTS","TENSILE_UTS_ENGINEERING","tension","EXACT_CONTINUOUS_TEMPERATURE","exact","exact_or_UNKNOWN","primary"),
        ("HT_TENSILE_YS_0P2","TENSILE_YS_0P2","tension","EXACT_CONTINUOUS_TEMPERATURE","exact","exact_or_UNKNOWN","primary"),
        ("HT_TENSILE_EL_TOTAL","TENSILE_EL_TOTAL","tension","EXACT_CONTINUOUS_TEMPERATURE","exact","exact_or_UNKNOWN","primary"),
        ("COMP_YIELD","COMPRESSIVE_YIELD","compression","EXACT_CONTINUOUS_TEMPERATURE","exact","exact_or_UNKNOWN","separate"),
        ("COMP_STRENGTH","COMPRESSIVE_STRENGTH","compression","EXACT_CONTINUOUS_TEMPERATURE","exact","exact_or_UNKNOWN","separate"),
        ("VICKERS_HARDNESS","HARDNESS_VICKERS","indentation","EXACT_CONTINUOUS_TEMPERATURE","load+dwell","n/a","method_partitioned"),
        ("NANO_HARDNESS","HARDNESS_NANO","instrumented_indentation","EXACT_CONTINUOUS_TEMPERATURE","tip+load+dwell+method","n/a","method_partitioned"),
        ("TENSILE_MODULUS","MODULUS_TENSILE","tension","EXACT_CONTINUOUS_TEMPERATURE","exact","exact_or_UNKNOWN","method_partitioned"),
        ("INDENTATION_MODULUS","MODULUS_INDENTATION","instrumented_indentation","EXACT_CONTINUOUS_TEMPERATURE","tip+load+method","n/a","method_partitioned"),
        ("CREEP_MIN_RATE","CREEP_MIN_RATE","creep","EXACT_CONTINUOUS_TEMPERATURE","stress+environment","n/a","separate"),
        ("CREEP_RUPTURE","CREEP_RUPTURE_LIFE","creep","EXACT_CONTINUOUS_TEMPERATURE","stress+environment","n/a","separate"),
    ]
    rows = []
    for task_id, target, mode, temperature, direction, strain, level in specs:
        rows.append({"task_id":task_id,"target_semantic_id":target,"test_mode":mode,"temperature_protocol":temperature,"direction_protocol":direction,"strain_rate_protocol":strain,"task_key_template":"target_semantic_id|test_mode|temperature_protocol|specimen_direction|strain_rate_protocol","headline_or_secondary":level,"label_authority":"SCREENED_GOLD_ONLY","silver_policy":"SENSITIVITY_ONLY","status":"BLOCKED_INPUT_GATE","blocking_reason":"MC01 snapshot/split/seed and V29 atom/provenance authority absent"})
    return rows


def build_tables() -> None:
    source_fields = ["source_name","source_locator","priority","hash","hash_kind","hash_scope","bytes_prior","member_count_prior","opened_or_consumed","terminal_use_status","window_relevance","exclusion_or_use_reason"]
    sources = source_rows()
    write_csv("INPUT_LEDGER.csv", source_fields, sources)
    write_csv("SOURCE_UTILIZATION_MATRIX.csv", source_fields, sources)
    paper_fields = ["doi","title","source_type","source_hash","source_locator","semantic_objects_checked","finding","decision","evidence_level","conflict_or_limit"]
    papers = paper_rows()
    write_csv("PRIMARY_LITERATURE_AUDIT.csv", paper_fields, papers)
    write_csv("ORIGINAL_PAPER_SEMANTIC_CHECK.csv", paper_fields, papers)
    targets = target_rows()
    write_csv("TARGET_SEMANTICS.csv", list(targets[0].keys()), targets)
    features = feature_rows()
    write_csv("FEATURE_REGISTRY.csv", list(features[0].keys()), features)
    tasks = task_rows()
    write_csv("TARGET_TASK_MATRIX.csv", list(tasks[0].keys()), tasks)


def build_docs() -> None:
    unblock = "\n".join(f"- `{path}`" for path in REQUIRED_AUTHORITY)
    write_text("00_EXECUTIVE_VERDICT.md", f'''# MC02 Executive Verdict

`WINDOW=MC02 | SNAPSHOT=missing | SPLIT=missing | SOURCE_MODE=FULL_AUDIT_AND_SCOPED_USE`

## Decision
MC02 freezes target semantics, feature eligibility, preprocessing, missingness and composition constraints under a fail-closed control contract. It does not create or replace MC01 snapshot/split/seed authority, Gold, ACTIVE, unified Schema, a training table, fitted preprocessor, model, checkpoint, OOF prediction or metric. The exact MC01/V29 authority inputs were not present; FINAL_MC00 and historical/recovery matrices are not substitutes. Status is `{STATUS}`.

## Scientific boundary
UTS, proof-method-specific YS, total/uniform elongation, reduction of area, compression, hardness modalities, tensile/indentation modulus, creep and fatigue are separate semantics. Task identity includes target, test mode, exact test temperature, specimen direction and strain-rate protocol. Build preheat, heat treatment, exposure and test temperature are distinct. Matrix/bulk composition, precursor, intended reinforcement and actual phase remain separate; wt.% and vol.% never silently pool. Post-test observations, labels, target-derived increments and model outputs are blocked. Every learned transform is outer-training-fold local.

## Evidence
All named top-level packages are terminally registered. Current suffixed V27 uploads require fresh local byte/hash rebinding; prior canonical central-directory fingerprints are references. Eight original-paper semantic checks were used directly, including full high-temperature tensile and nanoindentation papers plus six hash-bound publisher XMLs.

## Required unblock
{unblock}

## Claim ceiling
Trainable semantics and feature eligibility only. No importance, causal mechanism, performance, candidate validation or production claim.''')
    write_text("DATASET_CARD.md", f'''# Dataset Card — MC02 Semantic Contract

Status `{STATUS}`; snapshot/split missing; rows materialized 0. This is a control-contract card, not a released dataset. Headline labels are `SCREENED_GOLD` only; Silver is sensitivity-only; Evidence-only cannot label. The physical row unit is paper × sample × process × test condition. Paper/sample/condition identifiers are provenance/grouping keys, not features. No target distribution, missingness rate or row count is asserted without MC01 authority.''')
    write_text("FEATURE_FIREWALL.md", '''# Feature Firewall

Chronology: `formulation -> processing -> pre-test state -> test context -> target -> post-test state -> model outputs`.
Headline ex-ante models stop before pre-test state. Pre-test density, porosity, actual phase, microstructure and GND are allowed only in separately named state-aware tasks measured before the target test on the same state. Hard blocks: UTS/YS/EL/hardness/modulus and transforms; strength–ductility products and matched increments; post-test fracture, necking, TEM, dislocation and DRX; predictions, OOF residuals, SHAP/ALE; free-text conclusions; paper/sample/DOI IDs. Every imputer, encoder, scaler, selector, target encoder, SSL fit, early stopping and tuner is fitted inside the outer training fold. Target encoding is disabled by default and, if preregistered, inner cross-fit only. Global/transductive pretraining is separately labeled and cannot claim inductive generalization. Same physical specimen, duplicate, same-source derivative and near-duplicate identities cannot cross folds.''')
    write_text("MISSINGNESS_POLICY.md", '''# Missingness Policy

Allowed semantic states: `OBSERVED`, `EXPLICIT_ZERO`, `NOT_REPORTED`, `NOT_APPLICABLE`, `BELOW_DETECTION`, `STRUCTURAL_MISSING`, `AMBIGUOUS`. Unknown impurity is not zero. No global imputation. Numeric robust-median and categorical `UNKNOWN` handling, where enabled, are fit inside each outer training fold. Missing indicators require a declared materials interpretation and comparison against no-indicator and complete-case sensitivities. Features above 80% missing are excluded from headline models unless preregistered. Target-informed imputation is prohibited.''')
    write_text("COMPOSITION_CONSTRAINTS.md", '''# Composition Constraints

Maintain distinct blocks for matrix nominal, bulk nominal, bulk measured, precursor dose, intended reinforcement and measured actual phase. wt.% and vol.% never pool. Unknown is not zero; Ti balance is allowed only when the source explicitly permits it and the field is marked inferred. A claimed complete bulk wt.% vector must satisfy `abs(sum(w_i)-100)<=0.5`; partial vectors remain partial and are not silently renormalized. Conversion requires constituent density, equation, uncertainty and provenance while preserving the original basis: `w_i = rho_i * phi_i / sum_j(rho_j * phi_j)`. Optional multiplicative replacement/ilr applies only to a declared closed block, is parameterized inside the outer training fold and coexists with raw fractions. MWCNT precursor and in-situ TiC product phase remain separate.''')
    write_text("METHODS.md", '''# Methods

MC02 registered every named source, deep-checked representative original papers, defined canonical targets/units, constructed target × mode × temperature × direction × strain-rate tasks, classified features by availability time, blocked label/proxy/post-test leakage, and specified basis-aware composition and fold-local missingness/preprocessing. Temperature conversion is `T_C=T_K-273.15` with original value/unit retained. Stress is canonicalized to MPa. No mode, temperature, direction, hardness load or modulus method is silently pooled. W0 performs no model training; zero-row OOF and header-only metrics are deliberate schema-valid non-applicable artifacts.''')
    write_text("DESIGN.md", '''# Design and Formal Invariants

`task_key = target_semantic_id | test_mode | temperature_protocol | direction | strain_rate_protocol`. Different mode or test temperature cannot share a task. Unknown direction remains `UNKNOWN`. Unit transforms: `T[degC]=T[K]-273.15`; `sigma[MPa]=1000*sigma[GPa]`; `sigma[MPa]=sigma[Pa]/1e6`. Original values/units remain in lineage. Complete composition closure is `abs(sum_i w_i-100)<=0.5`; partial vectors are not renormalized. Leakage chronology is formulation -> processing -> pre-test state -> test context -> target -> post-test state -> model outputs. All learned transforms are nested in outer training folds.''')
    write_text("MODEL_CARD.md", f'''# Model Card

No model exists in MC02. This is a W0 control window and status is `{STATUS}` because snapshot/split/seed and canonical V29 atom/provenance inputs are absent. `artifacts/` contains only control and OOF-schema metadata. No checkpoint, inference capability, metric, feature importance or candidate prediction exists.''')
    write_text("LIMITATIONS.md", '''# Limitations

MC01 snapshot/split/seed and V29 atomic/provenance/conflict inputs are absent. Current suffixed V27 copies were not freshly byte-hashed in the web execution backend; prior canonical central-directory fingerprints are clearly scoped and require local rebind/testzip. Original-paper checking is targeted semantic adjudication, not a claim that every corpus member was reread in full. No dataset distribution, OOF, metric or model behavior is asserted.''')
    write_text("NEGATIVE_RESULTS.md", '''# Negative Results / Explicit Non-Actions

Recovery snapshots, FINAL_MC00 and historical feature matrices were rejected as substitutes for MC01. Tensile/compression, engineering/true stress, total/uniform elongation, Vickers/nano hardness and tensile/indentation modulus pooling were rejected. Post-test microscopy and target-derived mechanism increments were rejected as features. No training, global preprocessing, target encoding, SSL fitting, OOF generation, checkpoint creation or model registration was performed.''')
    write_text("OPEN_ISSUES.md", f'''# Open Issues

1. Supply and hash-verify:\n{unblock}
2. Recompute full-file SHA-256 and testzip for current suffixed V27 uploads and reconcile prior canonical fingerprints.
3. Resolve proof-stress method for records labeled only YS.
4. Bind every row to paper/sample/condition/source locator and hash.
5. Run duplicate/same-physical-specimen grouping audit before split consumption.''')
    write_text("README.md", '''# FINAL_MC02

MC02 freezes target semantics, feature eligibility, preprocessing, missingness and composition constraints. It is executable and testable but intentionally blocked from training until MC01/V29 authorities are supplied. Run `./run_all.sh` on Linux/WSL2 or `powershell -ExecutionPolicy Bypass -File run_all.ps1` on Windows.''')
    write_text("ACCEPTANCE_COMMANDS.md", '''# Acceptance Commands

Linux/WSL2: `python -m pip install -r requirements.lock && ./run_all.sh`.
Windows: `py -m pip install -r requirements.lock; powershell -ExecutionPolicy Bypass -File .\\run_all.ps1`.
Expected state is `BLOCKED_INPUT`; all contract tests and package validation pass. Nonzero exit means corruption or contract violation.''')
    write_text("RUN_CONFIG.yaml", f'''batch: {BATCH}
window: MC02
wave: W0
status: {STATUS}
snapshot_id: null
snapshot_sha256: null
split_id: null
source_mode: FULL_AUDIT_AND_SCOPED_USE
headline_label_authority: SCREENED_GOLD_ONLY
silver_policy: SENSITIVITY_ONLY
evidence_only_label_policy: PROHIBITED
primary_cv: STANDARD_KFOLD_FROM_MC01
fit_boundary: OUTER_TRAIN_FOLD_ONLY
composition_closure_tolerance_wt_pct: 0.5
high_missingness_exclusion_threshold: 0.80
training_enabled: false
blocking_files:
''' + "".join(f"  - {path}\n" for path in REQUIRED_AUTHORITY))
    write_text("configs/mc02.yaml", '''window: MC02
mode: CONTROL_CONTRACT
training: disabled
fail_closed: true
outer_fold_fit_only: true
target_encoding: disabled
optional_ilr: disabled_by_default
''')
    write_text("ENVIRONMENT_LOCK.txt", '''OS=ubuntu-24.04 compatible
PYTHON=3.12
NUMPY=1.26.4
PYARROW=17.0.0
TEST_FRAMEWORK=stdlib unittest
GPU=NOT_REQUIRED_CONTROL_WINDOW
''')
    write_text("requirements.lock", "numpy==1.26.4\npyarrow==17.0.0\n")
    write_text("TRAINING_LOG.jsonl", json.dumps({"timestamp":GENERATED_AT,"window":"MC02","event":"NOT_APPLICABLE_CONTROL_WINDOW","status":STATUS,"snapshot_id":None,"split_id":None,"rows":0,"models":0,"message":"W0 freezes semantics/interfaces only; MC01 authority missing."}) + "\n")
    write_json("PREPROCESSING_CONTRACT.json", {"schema_version":"1.0.0","window":"MC02","status":STATUS,"snapshot_id":None,"split_id":None,"outer_fold_fit_only":True,"steps":[{"order":1,"name":"semantic_filter","fit_scope":"none"},{"order":2,"name":"unit_canonicalization_preserve_original","fit_scope":"none"},{"order":3,"name":"composition_validation","fit_scope":"none"},{"order":4,"name":"missingness_encoding","fit_scope":"outer_train_only"},{"order":5,"name":"categorical_encoding","fit_scope":"outer_train_only"},{"order":6,"name":"scaling","fit_scope":"outer_train_only"},{"order":7,"name":"feature_selection","fit_scope":"outer_train_only"},{"order":8,"name":"target_encoding_disabled_default","fit_scope":"nested_inner_crossfit_only"},{"order":9,"name":"optional_ilr","fit_scope":"outer_train_only"}],"label_policy":{"headline":"SCREENED_GOLD_ONLY","silver":"SENSITIVITY_ONLY","evidence_only":"PROHIBITED"},"grouping_policy":["same_physical_specimen","duplicate_record","same_source_derivative","near_duplicate"],"stress_tests":["standard_kfold_primary","leave_paper_source_out","leave_family_out","time_out"],"global_transductive_pretraining":"SEPARATE_REPORT_ONLY","forbidden_fit_scopes":["full_dataset","outer_test_fold","held_out_source","global_target_statistics"]})
    write_json("WEB_TO_LOCAL_REQUEST.json", {"window":"MC02","status":STATUS,"priority":"BLOCKING","required_files":REQUIRED_AUTHORITY,"actions":["verify full-file SHA-256 and internal checksums","confirm snapshot/split/seed identity agreement","rebind current V27 hashes and run testzip","rerun run_all without mutating ACTIVE/Gold/Schema"],"acceptance":"authority hashes bound; no physical duplicate crosses folds; registry columns resolve"})
    write_text("LOCAL_ABSORPTION_PROMPT.md", f'''# Local Absorption Prompt

Verify `CHECKSUMS.sha256`, run `run_all`, and keep `{STATUS}` until all authority files below are mounted and hash-verified:\n{unblock}
After unblocking, materialize from `SCREENED_GOLD` only, consume MC01 fold assignments unchanged and fit preprocessing inside each outer training fold. Do not mutate ACTIVE/Gold/Schema, register a model or label a candidate VALIDATED.''')
    write_json("artifacts/OOF_SCHEMA.json", {"status":"NOT_APPLICABLE_CONTROL_WINDOW","rows":0,"format":"parquet","columns":{"row_uid":"string","task_id":"string","fold":"int32","seed":"int64","y_true":"float64","y_pred":"float64","status":"string"}})
    write_json("artifacts/CONTROL_CONTRACT.json", {"window":"MC02","batch":BATCH,"status":STATUS,"snapshot_id":None,"split_id":None,"contracts":["TARGET_SEMANTICS.csv","FEATURE_REGISTRY.csv","FEATURE_FIREWALL.md","PREPROCESSING_CONTRACT.json","MISSINGNESS_POLICY.md","COMPOSITION_CONSTRAINTS.md","TARGET_TASK_MATRIX.csv"],"required_authority":REQUIRED_AUTHORITY,"claim_ceiling":"TRAINABLE_SEMANTICS_AND_FEATURE_ELIGIBILITY_ONLY"})
    write_text("artifacts/README.md", "This directory contains control artifacts only. No model or fitted preprocessor is present.\n")
    write_text("artifacts/checkpoints/README.md", "No checkpoint is applicable. Creating one in MC02 would violate the W0 boundary.\n")
    write_csv("METRICS_BY_FOLD.csv", ["task_id","fold","seed","n","metric","value","status","reason"], [])
    write_csv("METRICS_BY_SEED.csv", ["task_id","seed","folds","n","metric","mean","std","ci95_low","ci95_high","status","reason"], [])
    write_csv("ERROR_ANALYSIS.csv", ["row_uid","task_id","fold","seed","error","subgroup","status","reason"], [])


def build_source_code() -> None:
    write_text("src/__init__.py", "")
    write_text("src/mc02_contract.py", r'''
from __future__ import annotations
import math
from typing import Iterable, Mapping
MISSING_CODES={'OBSERVED','EXPLICIT_ZERO','NOT_REPORTED','NOT_APPLICABLE','BELOW_DETECTION','STRUCTURAL_MISSING','AMBIGUOUS'}
FORBIDDEN_TOKENS=('post_test','post_fracture','fracture_morphology','necking','post_tem','post_dislocation','post_drx','strength_ductility_product','delta_uts','delta_ys','delta_el','oof_residual','shap_value','model_prediction')
TARGET_NAMES={'uts_mpa','ys_mpa','elongation_pct','hardness','modulus_gpa','y_true','target'}
def normalize_temperature(value:float,unit:str)->float:
 u=unit.strip().lower().replace('°','')
 if u in {'c','degc','celsius'}:return float(value)
 if u in {'k','kelvin'}:return float(value)-273.15
 raise ValueError('unsupported temperature unit')
def normalize_stress_to_mpa(value:float,unit:str)->float:
 u=unit.strip().lower()
 if u=='mpa':return float(value)
 if u=='gpa':return float(value)*1000
 if u=='pa':return float(value)/1e6
 raise ValueError('unsupported stress unit')
def build_task_key(target,test_mode,temperature_protocol,direction,strain_rate_protocol):
 vals=[target,test_mode,temperature_protocol,direction or 'UNKNOWN',strain_rate_protocol or 'UNKNOWN']
 if any('|' in str(v) for v in vals):raise ValueError('delimiter in component')
 return '|'.join(str(v).strip() for v in vals)
def validate_composition_closure(values:Mapping[str,float|None],complete:bool,tolerance:float=0.5):
 observed=[float(v) for v in values.values() if v is not None];total=sum(observed)
 if any(v<0 or v>100 for v in observed):return False,total
 return ((abs(total-100)<=tolerance) if complete else True),total
def classify_missing(value,explicit_zero=False,applicable=True,below_detection=False,ambiguous=False):
 if ambiguous:return 'AMBIGUOUS'
 if not applicable:return 'NOT_APPLICABLE'
 if below_detection:return 'BELOW_DETECTION'
 if explicit_zero:return 'EXPLICIT_ZERO'
 if value is None or (isinstance(value,float) and math.isnan(value)):return 'NOT_REPORTED'
 return 'OBSERVED'
def firewall_decision(feature_name,availability_time='before_test'):
 name=feature_name.strip().lower()
 if name in TARGET_NAMES or any(token in name for token in FORBIDDEN_TOKENS):return False,'label/proxy/post-test/model-derived'
 if availability_time in {'after_target_observed','post_test','post_model'}:return False,'unavailable before target'
 if name in {'paper_uid','sample_uid','condition_uid','doi'}:return False,'grouping key only'
 return True,'eligible subject to registry tier'
def assert_fit_scope(fit_row_ids:Iterable[str],outer_train_ids:Iterable[str]):
 leaked=set(fit_row_ids)-set(outer_train_ids)
 if leaked:raise ValueError('fit outside outer train: '+str(sorted(leaked)[:5]))
def validate_fraction_basis(precursor_basis,actual_phase_basis):
 valid={None,'wt_pct','vol_pct','mass_fraction','volume_fraction'}
 if precursor_basis not in valid or actual_phase_basis not in valid:raise ValueError('unsupported basis')
 if precursor_basis=='actual_phase' or actual_phase_basis=='precursor':raise ValueError('conflated')
def can_merge_modulus(method_a,method_b):return method_a.strip().lower()==method_b.strip().lower()
''')
    write_text("src/build_training_table.py", r'''
from __future__ import annotations
import argparse,json
from pathlib import Path
import pyarrow.parquet as pq
REQUIRED=['v31/control/MC01/MODEL_INPUT_SNAPSHOT.json','v31/control/MC01/SPLIT_AUTHORITY.json','v31/control/MC01/SEED_REGISTRY.json','v31/gold/SCREENED_GOLD.parquet','v29/ATOMIC_RECORDS.parquet','v29/PROVENANCE.jsonl','v29/CONFLICT_LEDGER.csv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--authority-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 missing=[rel for rel in REQUIRED if not (a.authority_root/rel).is_file()]
 if missing:print(json.dumps({'status':'BLOCKED_INPUT','missing':missing},indent=2));return 2
 snapshot=json.loads((a.authority_root/REQUIRED[0]).read_text())
 if not snapshot.get('snapshot_sha256'):print(json.dumps({'status':'BLOCKED_INPUT','reason':'snapshot_sha256 absent'},indent=2));return 2
 table=pq.read_table(a.authority_root/'v31/gold/SCREENED_GOLD.parquet');a.output.parent.mkdir(parents=True,exist_ok=True);pq.write_table(table,a.output,compression='zstd')
 print(json.dumps({'status':'MATERIALIZED_WITHOUT_PREPROCESSOR_FIT','rows':table.num_rows,'snapshot_sha256':snapshot['snapshot_sha256']},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
''')
    write_text("src/resume.py", "import json\nif __name__=='__main__':print(json.dumps({'window':'MC02','status':'NOT_APPLICABLE_CONTROL_WINDOW','checkpoint':None},indent=2))\n")
    write_text("src/infer.py", "import json\nif __name__=='__main__':print(json.dumps({'window':'MC02','status':'NO_MODEL_CONTROL_WINDOW','predictions':[]},indent=2))\n")
    validator = r'''
from __future__ import annotations
import argparse,csv,hashlib,json,re
from pathlib import Path
import pyarrow.parquet as pq
REQUIRED=__REQUIRED__
ALLOWED={'USED_DIRECTLY','USED_AS_REFERENCE','SUPERSEDED_BY_HASH','OUT_OF_SCOPE','BLOCKED_CORRUPT','NOT_RELEVANT_TO_WINDOW'}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,default=Path('.'));args=parser.parse_args();root=args.package.resolve();errors=[]
 missing=sorted(rel for rel in REQUIRED if not (root/rel).is_file())
 if missing:errors.append({'missing_required':missing})
 checks={}
 if (root/'CHECKSUMS.sha256').is_file():
  for line in (root/'CHECKSUMS.sha256').read_text().splitlines():
   if line.strip():digest,rel=line.split('  ',1);checks[rel]=digest
  for rel,digest in checks.items():
   path=root/rel
   if not path.is_file() or sha(path)!=digest:errors.append({'checksum_mismatch':rel})
 for rel in ['METRICS_BY_FOLD.csv','METRICS_BY_SEED.csv','ERROR_ANALYSIS.csv']:
  with (root/rel).open(newline='') as handle:
   rows=list(csv.reader(handle))
   if len(rows)!=1:errors.append({'nonempty_schema_only_file':rel,'rows':len(rows)-1})
 with (root/'SOURCE_UTILIZATION_MATRIX.csv').open(newline='') as handle:
  for row in csv.DictReader(handle):
   if row['terminal_use_status'] not in ALLOWED:errors.append({'invalid_state':row})
 with (root/'FEATURE_REGISTRY.csv').open(newline='') as handle:
  for row in csv.DictReader(handle):
   if row['firewall_status']=='BLOCK' and row['allowed_headline']=='true':errors.append({'blocked_allowed':row['canonical_name']})
 with (root/'TARGET_TASK_MATRIX.csv').open(newline='') as handle:
  rows=list(csv.DictReader(handle));ids=[row['task_id'] for row in rows]
  if len(ids)!=len(set(ids)):errors.append('duplicate tasks')
  if any(row['status']!='BLOCKED_INPUT_GATE' for row in rows):errors.append('task gate open')
 oof=pq.read_table(root/'OOF_PREDICTIONS.parquet')
 if oof.num_rows!=0:errors.append({'oof_rows':oof.num_rows})
 status=json.loads((root/'WINDOW_STATUS.json').read_text())
 if status.get('status')!='BLOCKED_INPUT' or status.get('snapshot_id') is not None or status.get('training_performed') is not False:errors.append({'bad_status':status})
 archives=[path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file() and path.suffix.lower() in {'.zip','.7z','.tar','.gz'}]
 if archives:errors.append({'nested_archives':archives})
 secret_patterns=[re.compile(r'sk-[A-Za-z0-9]{20,}'),re.compile(r'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'),re.compile(r'ghp_[A-Za-z0-9]{30,}')]
 for path in root.rglob('*'):
  if path.is_file() and path.suffix.lower()!='.parquet':
   try:text=path.read_text(errors='ignore')
   except Exception:continue
   if any(pattern.search(text) for pattern in secret_patterns):errors.append({'secret_pattern':path.relative_to(root).as_posix()})
 result={'pass':not errors,'errors':errors,'files':sum(1 for path in root.rglob('*') if path.is_file()),'oof_rows':oof.num_rows}
 print(json.dumps(result,indent=2,sort_keys=True));return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
'''.replace("__REQUIRED__", repr(REQUIRED_MEMBERS))
    write_text("src/validate_package.py", validator)
    write_text("tests/test_contract.py", r'''
import unittest
from src.mc02_contract import normalize_temperature,normalize_stress_to_mpa,build_task_key,validate_composition_closure,classify_missing,firewall_decision,assert_fit_scope,validate_fraction_basis,can_merge_modulus
class ContractTests(unittest.TestCase):
 def test_post(self):self.assertFalse(firewall_decision('post_test_tem_features')[0])
 def test_proxy(self):self.assertFalse(firewall_decision('strength_ductility_product')[0])
 def test_target(self):self.assertFalse(firewall_decision('uts_MPa')[0])
 def test_group(self):self.assertFalse(firewall_decision('paper_uid')[0])
 def test_kelvin(self):self.assertAlmostEqual(normalize_temperature(773,'K'),499.85)
 def test_gpa(self):self.assertEqual(normalize_stress_to_mpa(1.5,'GPa'),1500)
 def test_temp_task(self):self.assertNotEqual(build_task_key('UTS','tension','500C','LD','5e-4'),build_task_key('UTS','tension','600C','LD','5e-4'))
 def test_mode_task(self):self.assertNotEqual(build_task_key('S','tension','25C','LD','1e-3'),build_task_key('S','compression','25C','LD','1e-3'))
 def test_close_pass(self):self.assertTrue(validate_composition_closure({'Ti':90,'Al':6,'V':4},True)[0])
 def test_close_fail(self):self.assertFalse(validate_composition_closure({'Ti':80,'Al':6,'V':4},True)[0])
 def test_unknown(self):self.assertEqual(classify_missing(None),'NOT_REPORTED')
 def test_zero(self):self.assertEqual(classify_missing(None,explicit_zero=True),'EXPLICIT_ZERO')
 def test_fold_guard(self):
  with self.assertRaises(ValueError):assert_fit_scope(['a','test'],['a','b'])
 def test_basis(self):validate_fraction_basis('wt_pct','vol_pct')
 def test_modulus(self):self.assertFalse(can_merge_modulus('tensile','indentation'))
if __name__=='__main__':unittest.main()
''')
    write_text("run_all.sh", '''#!/usr/bin/env bash
set -euo pipefail
python -m unittest discover -s tests -v
python src/validate_package.py --package .
python src/resume.py
python src/infer.py
''')
    (PKG / "run_all.sh").chmod(0o755)
    write_text("run_all.ps1", "$ErrorActionPreference='Stop'\npy -m unittest discover -s tests -v\npy src/validate_package.py --package .\npy src/resume.py\npy src/infer.py\n")


def make_oof() -> None:
    schema = pa.schema([
        ("row_uid", pa.string()), ("task_id", pa.string()), ("fold", pa.int32()),
        ("seed", pa.int64()), ("y_true", pa.float64()), ("y_pred", pa.float64()),
        ("status", pa.string()),
    ])
    table = pa.Table.from_arrays([pa.array([], type=field.type) for field in schema], schema=schema)
    pq.write_table(table, PKG / "OOF_PREDICTIONS.parquet", compression="zstd")


def run_unit_tests() -> tuple[int, int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PKG)
    process = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=PKG, env=env, text=True, capture_output=True)
    total = 15
    passed = total if process.returncode == 0 else 0
    report = process.stdout + process.stderr
    if process.returncode:
        raise RuntimeError(report)
    return passed, total, report


def write_status_and_reports(passed: int, total: int, report: str) -> None:
    write_text("TEST_REPORT.txt", f"returncode=0\npassed={passed}\ntotal={total}\n\n{report}")
    predicted_count = len(REQUIRED_MEMBERS)
    write_json("WINDOW_STATUS.json", {"window":WINDOW,"batch":BATCH,"wave":"W0","status":STATUS,"snapshot_id":None,"snapshot_sha256":None,"split_id":None,"source_mode":"FULL_AUDIT_AND_SCOPED_USE","tests":{"passed":passed,"total":total},"training_performed":False,"oof_rows":0,"required":REQUIRED_AUTHORITY,"claim_ceiling":"trainable semantics and feature eligibility only","artifact_count":predicted_count})
    write_json("VALIDATION_REPORT.json", {"stage":"pre-manifest structural and unit validation","pass":True,"tests":{"passed":passed,"total":total},"status":STATUS,"expected_final_members":predicted_count})


def generate_manifest_checksums() -> None:
    for name in ["MANIFEST.json", "CHECKSUMS.sha256"]:
        path = PKG / name
        if path.exists(): path.unlink()
    files = sorted(path for path in PKG.rglob("*") if path.is_file())
    entries = [{"path":path.relative_to(PKG).as_posix(),"bytes":path.stat().st_size,"sha256":sha256(path)} for path in files]
    write_json("MANIFEST.json", {"batch":BATCH,"window":WINDOW,"status":STATUS,"generated_at":GENERATED_AT,"snapshot_id":None,"split_id":None,"entry_count":len(entries),"entries":entries,"manifest_scope":"all files except MANIFEST.json and CHECKSUMS.sha256 to avoid circularity"})
    checksum_files = sorted(path for path in PKG.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    write_text("CHECKSUMS.sha256", "".join(f"{sha256(path)}  {path.relative_to(PKG).as_posix()}\n" for path in checksum_files))


def validate_package() -> dict[str, Any]:
    process = subprocess.run([sys.executable, "src/validate_package.py", "--package", "."], cwd=PKG, text=True, capture_output=True)
    if process.returncode:
        raise RuntimeError(process.stdout + process.stderr)
    return json.loads(process.stdout)


def deterministic_zip(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in PKG.rglob("*") if item.is_file()):
            rel = path.relative_to(PKG).as_posix()
            info = zipfile.ZipInfo(rel, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    if WORK.exists(): shutil.rmtree(WORK)
    PKG.mkdir(parents=True)
    DELIVERY.mkdir(parents=True, exist_ok=True)
    build_tables()
    build_docs()
    build_source_code()
    make_oof()
    passed, total, report = run_unit_tests()
    write_status_and_reports(passed, total, report)
    generate_manifest_checksums()
    validation = validate_package()
    if sorted(path.relative_to(PKG).as_posix() for path in PKG.rglob("*") if path.is_file()) != sorted(REQUIRED_MEMBERS):
        actual = {path.relative_to(PKG).as_posix() for path in PKG.rglob("*") if path.is_file()}
        raise RuntimeError(f"member mismatch missing={sorted(set(REQUIRED_MEMBERS)-actual)} extra={sorted(actual-set(REQUIRED_MEMBERS))}")
    deterministic_zip(ZIP_PATH)
    repeat = DELIVERY / "FINAL_MC02.repeat.zip"
    deterministic_zip(repeat)
    if ZIP_PATH.read_bytes() != repeat.read_bytes():
        raise RuntimeError("deterministic ZIP check failed")
    repeat.unlink()
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise RuntimeError("ZIP duplicate/corruption")
        if any(name.lower().endswith((".zip", ".7z", ".tar", ".gz")) for name in names):
            raise RuntimeError("nested archive")
    digest = sha256(ZIP_PATH)
    SHA_PATH.write_text(f"{digest}  FINAL_MC02.zip\n", encoding="utf-8")
    summary = {"artifact":"FINAL_MC02.zip","sha256":digest,"bytes":ZIP_PATH.stat().st_size,"members":len(names),"tests":{"passed":passed,"total":total},"status":STATUS,"snapshot":None,"split":None,"package_validation":validation,"deterministic_repeat":True}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
