from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM15"
SNAPSHOT_SEED = "QM15_RECOVERY_20260713"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(rel: str, text: str) -> Path:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")
    return p


def write_json(rel: str, obj) -> Path:
    return write_text(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def write_csv(rel: str, fieldnames: list[str], rows: list[dict]) -> Path:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    return p


def linreg(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    X = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    resid = y - pred
    sse = float(np.sum(resid**2))
    sst = float(np.sum((y - np.mean(y))**2))
    r2 = float(1 - sse / sst) if sst > 0 else float("nan")
    n, p = len(y), X.shape[1]
    if n > p:
        sigma2 = sse / (n - p)
        cov = sigma2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(cov))
    else:
        se = np.full(p, np.nan)
    return {
        "intercept": float(beta[0]),
        "slope": float(beta[1]),
        "intercept_se": float(se[0]),
        "slope_se": float(se[1]),
        "r2": r2,
        "n": int(n),
        "pred": pred,
        "resid": resid,
    }


def png_size(path: Path):
    with path.open("rb") as f:
        sig = f.read(24)
    if sig[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", sig[16:24])


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for d in [
        "figure_data", "plot_code", "figures/png", "figures/svg", "figures/pdf",
        "analysis_code", "tests", "source_evidence", "logs"
    ]:
        (OUT / d).mkdir(parents=True, exist_ok=True)

    package_inputs = [
        ("00_统一上传总控与校验信息_20260712.zip", "0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f", "FULL_FILE_SHA256", 25479, 13, "P1_PROVENANCED_STRUCTURED", "control manifest and integrity records", "USED_DIRECTLY"),
        ("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip", "bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1", "FULL_FILE_SHA256", 510259317, 32, "P3_PLATFORM_CODE", "plot/platform code inventory and output conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip", "36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9", "FULL_FILE_SHA256", 515903028, 15, "P2_EXECUTABLE_ARTIFACT", "frozen feature matrix inventory; canonical QM15 rows not exposed", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip", "5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59", "FULL_FILE_SHA256", 515906034, 25, "P2_EXECUTABLE_ARTIFACT", "frozen feature matrix inventory; canonical QM15 rows not exposed", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip", "cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a", "FULL_FILE_SHA256", 515901682, 7, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip", "97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809", "ZIP_CENTRAL_DIRECTORY_SHA256", 515901786, 7, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip", "16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f", "ZIP_CENTRAL_DIRECTORY_SHA256", 515902128, 9, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip", "04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9", "ZIP_CENTRAL_DIRECTORY_SHA256", 515903238, 11, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip", "5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728", "ZIP_CENTRAL_DIRECTORY_SHA256", 515905052, 17, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip", "e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847", "ZIP_CENTRAL_DIRECTORY_SHA256", 515913392, 38, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip", "36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485", "ZIP_CENTRAL_DIRECTORY_SHA256", 515924832, 69, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip", "9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd", "ZIP_CENTRAL_DIRECTORY_SHA256", 515989228, 246, "P2_EXECUTABLE_ARTIFACT", "source reliability/UQ/AD conventions", "USED_AS_REFERENCE"),
        ("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip", "c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c", "ZIP_CENTRAL_DIRECTORY_SHA256", 506137803, 57191, "P3_PLATFORM_CODE", "historical evidence workflows and high-temperature assets", "USED_DIRECTLY"),
        ("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip", "a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a", "ZIP_CENTRAL_DIRECTORY_SHA256", 515999572, 244, "P3_PLATFORM_CODE", "engineering/staging infrastructure", "USED_AS_REFERENCE"),
        ("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip", "bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43", "ZIP_CENTRAL_DIRECTORY_SHA256", 516062924, 396, "P3_PLATFORM_CODE", "engineering/staging infrastructure", "USED_AS_REFERENCE"),
        ("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip", "08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755", "ZIP_CENTRAL_DIRECTORY_SHA256", 516106394, 499, "P3_PLATFORM_CODE", "engineering/staging infrastructure", "USED_AS_REFERENCE"),
        ("TITMC_V27_LIT_WEB_P001_OF_010.zip", "42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0", "ZIP_CENTRAL_DIRECTORY_SHA256", 499460308, 15, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P002_OF_010.zip", "05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193", "ZIP_CENTRAL_DIRECTORY_SHA256", 490572377, 154, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P003_OF_010.zip", "535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917", "ZIP_CENTRAL_DIRECTORY_SHA256", 490379244, 4610, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P004_OF_010.zip", "bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a", "ZIP_CENTRAL_DIRECTORY_SHA256", 490620829, 7747, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P005_OF_010.zip", "1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1", "ZIP_CENTRAL_DIRECTORY_SHA256", 490762545, 10068, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P006_OF_010.zip", "5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13", "ZIP_CENTRAL_DIRECTORY_SHA256", 490902802, 11778, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P007_OF_010.zip", "4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1", "ZIP_CENTRAL_DIRECTORY_SHA256", 491018449, 13499, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P008_OF_010.zip", "478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341", "ZIP_CENTRAL_DIRECTORY_SHA256", 491203652, 15702, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P009_OF_010.zip", "b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a", "ZIP_CENTRAL_DIRECTORY_SHA256", 491501617, 20036, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
        ("TITMC_V27_LIT_WEB_P010_OF_010.zip", "faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d", "ZIP_CENTRAL_DIRECTORY_SHA256", 367381900, 57717, "P0_PRIMARY_ORIGINAL", "primary literature corpus", "USED_DIRECTLY"),
    ]
    snapshot_material = "|".join(r[1] for r in package_inputs) + "|" + SNAPSHOT_SEED
    snapshot_id = "RECOVERY_QM15_" + sha256_bytes(snapshot_material.encode())[:16]

    source_captures = {
        "KONG_2021_IJLMM.txt": "DOI 10.1016/j.ijlmm.2020.07.005; SiC/Ti-6Al-2Sn-4Zr-2Mo-0.1Si; 33 vol% SiC; force-controlled LCF R=0.1, 0.5 Hz; Table 1 stress-life rows 1500/4,1450/10,1400/198,1350/4112,1300/5292,1200/17736,1100/52338; prose conflict 52388.",
        "KIM_2019_MMI.txt": "DOI 10.1007/s12540-018-00212-z; Ti/(5,10,20) vol% (TiB+TiC); oxidation 800-1000 C; apparent activation energy Q kJ/mol: pure Ti 165, 5% 187, 10% 207, 20% 209; cyclic 800 C 2 h x20.",
        "WANG_PEIPEI_2010_MSC.txt": "TMC1 0.39 vol% TiB+0.11 La2O3; TMC2 1.42 TiB+0.4 La2O3; TMC3 3.09 TiB+1.21 TiC+0.4 La2O3. Thermal exposure 550/600/650 C 120h, qualitative post-exposure tensile trends; Table 4-1 exact creep rates at 150 MPa.",
        "LI_JIUXIAO_2013_PHD.txt": "(TiB+La2O3)/IMI834-like composite; thermal exposure 600/650/700 C for 100h; UTS slight increase and elongation significant decrease; minimum ductility at 650 C; reinforcement morphology/interface stable after exposure; exact retention ratios figure-only.",
        "NIU_2021_TAFM.txt": "DOI 10.1016/j.tafmec.2021.102980; Ti6242/SiC spectrum-loading crack model; friction-slip + Dugdale + Willenborg + Forman; Vf 0.34, Em110 GPa, Ef400 GPa, sigma_y795 MPa, KC46.3, C1.917e-10, m4.13, deltaKth1, tau74.52 MPa.",
        "TC17_2023_IJF_COMPARATOR.txt": "International Journal of Fatigue 176 (2023) 107896; non-composite comparator; 400 C 2h oxidation creates oxygen-rich hardened layer; high-stress surface oxidation shortens fatigue life; low-stress internal initiation dominates.",
        "JIAO_2018_JALCOM_REVIEW.txt": "DOI 10.1016/j.jallcom.2018.07.100; review used only to locate contrary fatigue/oxidation cases and primary references; not pooled as primary evidence.",
        "WEI_600C_ENDPOINT_CAPTURE.txt": "Recovered same-work endpoint capture: 600 C, 20h, Ti-6Al-4V matrix mass gain 1.99 mg/cm2 and TiC-containing composite 1.57 mg/cm2. Exact publication identity/source byte hash unresolved; retained as recovery-grade direct capture, not Gold.",
    }
    source_hash = {}
    for name, text in source_captures.items():
        p = write_text("source_evidence/" + name, text)
        source_hash[name] = sha256_file(p)

    contract_capture = dedent("""
    QM15 contract capture: quantify thermal-exposure retention, oxidation kinetics, fatigue survival and architecture-linked damage; preserve atomic paper/sample/condition provenance; handle fatigue runout as censoring; do not compress distinct damage modes into a scalar durability score; return CONTINUE_DATA_GAP when canonical snapshot is absent.
    """).strip()
    prompt_path = write_text("source_evidence/QM15_CONTRACT_CAPTURE.txt", contract_capture)
    prompt_hash = sha256_file(prompt_path)

    input_fields = ["input_id","snapshot_id","source_name","source_type","path_or_locator","source_hash","source_hash_kind","bytes","member_count","central_directory_status","priority","window_relevance","terminal_use_status","opened_or_consumed","notes"]
    input_rows = []
    for i, row in enumerate(package_inputs):
        name, h, kind, size, members, pri, relevance, use = row
        input_rows.append({
            "input_id": f"PKG{i:02d}", "snapshot_id": snapshot_id, "source_name": name,
            "source_type": "ZIP", "path_or_locator": f"/mnt/data/{name}", "source_hash": h,
            "source_hash_kind": kind, "bytes": size, "member_count": members,
            "central_directory_status": "READABLE", "priority": pri, "window_relevance": relevance,
            "terminal_use_status": use, "opened_or_consumed": "YES",
            "notes": "Bound from project source audit; package-level use is distinct from scientific row-level provenance."
        })
    input_rows.append({
        "input_id":"CONTRACT", "snapshot_id":snapshot_id, "source_name":"QM15_热暴露、氧化、疲劳和损伤容限的时间依赖风险包络.md",
        "source_type":"MDU", "path_or_locator":"/mnt/data/QM15_热暴露、氧化、疲劳和损伤容限的时间依赖风险包络.md",
        "source_hash":prompt_hash, "source_hash_kind":"NORMALIZED_CONTRACT_CAPTURE_SHA256", "bytes":"", "member_count":1,
        "central_directory_status":"N/A", "priority":"P0_CONTRACT", "window_relevance":"execution contract",
        "terminal_use_status":"USED_DIRECTLY", "opened_or_consumed":"YES", "notes":"Original file-byte hash must be rebound locally."
    })
    for j, (name, h) in enumerate(source_hash.items()):
        input_rows.append({
            "input_id":f"SRC{j:02d}", "snapshot_id":snapshot_id, "source_name":name,
            "source_type":"SOURCE_CAPTURE", "path_or_locator":"source_evidence/"+name,
            "source_hash":h, "source_hash_kind":"NORMALIZED_EVIDENCE_CAPTURE_SHA256", "bytes":(OUT/"source_evidence"/name).stat().st_size,
            "member_count":1, "central_directory_status":"N/A", "priority":"P0_PRIMARY_OR_CONTEXT",
            "window_relevance":"quantitative or mechanism evidence", "terminal_use_status":"USED_DIRECTLY" if "REVIEW" not in name and "COMPARATOR" not in name else "USED_AS_REFERENCE",
            "opened_or_consumed":"YES", "notes":"Capture hash is not original publication byte hash; requested for canonical absorption."
        })
    write_csv("INPUT_LEDGER.csv", input_fields, input_rows)
    write_csv("SOURCE_UTILIZATION_LEDGER.csv", input_fields, input_rows)
    write_text("OPENED_FILES.txt", "\n".join(r["source_name"] for r in input_rows))

    prov = []
    def add_prov(pid, paper, sample, condition, source_name, locator, evidence, excerpt, notes=""):
        rec = {
            "provenance_id":pid, "snapshot_id":snapshot_id, "paper_uid":paper,
            "sample_uid":sample, "condition_uid":condition, "source_name":source_name,
            "source_hash":source_hash.get(source_name, ""), "source_hash_kind":"NORMALIZED_EVIDENCE_CAPTURE_SHA256",
            "locator":locator, "evidence_grade":evidence, "excerpt_sha256":sha256_bytes(excerpt.encode()),
            "excerpt":excerpt, "notes":notes
        }
        prov.append(rec)
        return pid

    # Direct fatigue survival data
    fatigue_rows = []
    fatigue_data = [
        (1500,4,.66,.67,227,220), (1450,10,.66,.65,224,226), (1400,198,.63,.65,223,225),
        (1350,4112,.62,.64,220,221), (1300,5292,.59,.61,225,227),
        (1200,17736,.53,.53,227,229), (1100,52338,.47,.42,223,221)
    ]
    for i,(stress,nf,p1,p2,e1,e2) in enumerate(fatigue_data,1):
        cond = f"KONG_LCF_R0.1_F0.5_STRESS{stress}"
        pid = add_prov(f"P_KONG_T1_R{i}", "KONG2021_IJLMM", "KONG_SIC33_CYL", cond,
                       "KONG_2021_IJLMM.txt", "Table 1", "DIRECT_TABLE_TEXT",
                       f"maximum stress {stress} MPa; fatigue life {nf}; peak strain {p1}/{p2}; modulus {e1}/{e2} GPa")
        fatigue_rows.append({
            "snapshot_id":snapshot_id,"paper_uid":"KONG2021_IJLMM","sample_uid":"KONG_SIC33_CYL","condition_uid":cond,
            "matrix":"Ti-6Al-2Sn-4Zr-2Mo-0.1Si","reinforcement":"continuous SiC fiber","reinforcement_fraction_vol_pct":33,
            "topology":"unidirectional cylindrical; fibers parallel to load","test_temperature_C":25,"atmosphere":"laboratory air/not explicitly resolved",
            "fatigue_class":"LCF","control_mode":"axial force-controlled","waveform":"triangular","stress_ratio_R":0.1,"frequency_Hz":0.5,
            "maximum_stress_MPa":stress,"stress_amplitude_MPa":"","cycles":nf,"event_observed":1,"runout":0,"censor_type":"none",
            "peak_strain_first_pct":p1,"peak_strain_last_pct":p2,"modulus_first_GPa":e1,"modulus_last_GPa":e2,
            "evidence_grade":"DIRECT_TABLE_TEXT","provenance_id":pid,"claim_level":1,"notes":"Table value used; 1100 MPa row conflicts with 52388 in prose/abstract."
        })

    # Exact oxidation endpoint capture
    ox_rows = []
    for label,reinforcement,dose,mass in [
        ("MATRIX","none",0,1.99), ("TMC","TiC-containing Ti-6Al-4V composite","unresolved",1.57)
    ]:
        cond = f"WEI_600C_20H_{label}"
        pid = add_prov(f"P_WEI_{label}", "WEI_RECOVERY_600C", f"WEI_{label}", cond,
                       "WEI_600C_ENDPOINT_CAPTURE.txt", "recovered endpoint text capture", "DIRECT_TEXT_CAPTURE",
                       f"600 C 20 h mass gain {mass} mg/cm2", "Publication identity and original byte hash unresolved.")
        kp = mass**2/20.0
        ox_rows.append({
            "snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","sample_uid":f"WEI_{label}","condition_uid":cond,
            "matrix":"Ti-6Al-4V","reinforcement":reinforcement,"reinforcement_fraction_vol_pct":dose,
            "topology":"unresolved","atmosphere":"air","oxidation_mode":"isothermal","temperature_C":600,"time_h":20,
            "mass_gain_mg_cm2":mass,"scale_thickness_um":"","kinetic_law":"two-point origin-constrained parabolic diagnostic",
            "parameter_name":"apparent_kp","parameter_value":kp,"parameter_units":"mg2 cm-4 h-1","activation_energy_kJ_mol":"",
            "fit_basis":"single endpoint plus physical origin; not a multi-time kinetic fit","evidence_grade":"DIRECT_TEXT_CAPTURE+DERIVED_CALCULATION",
            "provenance_id":pid,"status":"RECOVERY_GRADE","notes":"Do not promote to Gold until exact source identity and raw curve are restored."
        })

    # Kim activation-energy dose series
    for dose,q in [(0,165),(5,187),(10,207),(20,209)]:
        cond=f"KIM_ISOTHERMAL_800_1000C_DOSE{dose}"
        pid=add_prov(f"P_KIM_Q_{dose}","KIM2019_MMI",f"KIM_DOSE{dose}",cond,"KIM_2019_MMI.txt","Results/Fig. 3 text","DIRECT_TEXT",
                     f"apparent activation energy {q} kJ/mol for {dose} vol% (TiB+TiC)")
        ox_rows.append({
            "snapshot_id":snapshot_id,"paper_uid":"KIM2019_MMI","sample_uid":f"KIM_DOSE{dose}","condition_uid":cond,
            "matrix":"commercially pure Ti","reinforcement":"(TiB+TiC)" if dose else "none","reinforcement_fraction_vol_pct":dose,
            "topology":"uniform particulate dispersion","atmosphere":"air","oxidation_mode":"isothermal","temperature_C":"800-1000","time_h":"curve series",
            "mass_gain_mg_cm2":"","scale_thickness_um":"","kinetic_law":"parabolic approximation with acknowledged deviations",
            "parameter_name":"apparent_activation_energy","parameter_value":q,"parameter_units":"kJ mol-1","activation_energy_kJ_mol":q,
            "fit_basis":"Arrhenius slope of reported apparent kp values","evidence_grade":"DIRECT_TEXT","provenance_id":pid,"status":"OBSERVED_SUPPORT",
            "notes":"Single-paper dose series; kinetics can transition toward linear behavior with time/temperature."
        })

    # Thermal exposure qualitative evidence: no invented numeric retention ratios
    thermal_rows=[]
    for temp in [550,600,650]:
        for micro in ["equiaxed_HT1","lamellar_HT2"]:
            for prop in ["UTS","EL"]:
                if prop=="UTS":
                    qual="slight increase or retained; exact value figure-only" if temp==550 else "change reported; exact value figure-only"
                else:
                    if temp==600:
                        qual="pronounced ductility loss; lamellar condition reported worse"
                    elif temp==650:
                        qual="below baseline but partial recovery relative to 600 C"
                    else:
                        qual="slight improvement or limited change"
                cond=f"WANG_TMC2_{micro}_{temp}C_120H_{prop}"
                pid=add_prov(f"P_WANG_TE_{temp}_{micro}_{prop}","WANG2010_MSC","WANG_TMC2",cond,"WANG_PEIPEI_2010_MSC.txt","thermal-exposure chapter text/figures","FIGURE_DERIVED_PENDING",
                             f"{temp} C 120h {micro} {prop}: {qual}")
                thermal_rows.append({
                    "snapshot_id":snapshot_id,"paper_uid":"WANG2010_MSC","sample_uid":"WANG_TMC2","condition_uid":cond,
                    "matrix":"7715D-type near-alpha Ti","reinforcement":"1.42 vol% TiB + 0.4 vol% La2O3","topology":"discontinuous in-situ reinforcement",
                    "heat_treatment":micro,"microstructure":micro.split("_")[0],"atmosphere":"air/unresolved","exposure_temp_C":temp,"exposure_time_h":120,
                    "property":prop,"pre_value":"","post_value":"","retention_ratio":"","qualitative_change":qual,
                    "evidence_grade":"FIGURE_DERIVED_PENDING","status":"NOT_IDENTIFIABLE_EXACT_RATIO","provenance_id":pid,"claim_level":1
                })
    for temp in [600,650,700]:
        for prop in ["UTS","EL"]:
            qual="slight increase/limited change" if prop=="UTS" else ("largest reported ductility loss" if temp==650 else "significant ductility loss; 700 C shows anomalous recovery versus 600/650 C")
            cond=f"LI_IMI834_TIB_LA2O3_{temp}C_100H_{prop}"
            pid=add_prov(f"P_LI_TE_{temp}_{prop}","LI2013_PHD","LI_TIB_LA2O3_IMI834",cond,"LI_JIUXIAO_2013_PHD.txt","Abstract and Chapter 5","DIRECT_TEXT_QUALITATIVE",
                         f"{temp} C 100h {prop}: {qual}")
            thermal_rows.append({
                "snapshot_id":snapshot_id,"paper_uid":"LI2013_PHD","sample_uid":"LI_TIB_LA2O3_IMI834","condition_uid":cond,
                "matrix":"IMI834-like near-alpha Ti","reinforcement":"TiB + La2O3","topology":"forging-aligned TiB; dispersed La2O3",
                "heat_treatment":"multiple HT states aggregated in recovered text","microstructure":"lamellar/bimodal by HT","atmosphere":"air/unresolved",
                "exposure_temp_C":temp,"exposure_time_h":100,"property":prop,"pre_value":"","post_value":"","retention_ratio":"",
                "qualitative_change":qual,"evidence_grade":"DIRECT_TEXT_QUALITATIVE","status":"NOT_IDENTIFIABLE_EXACT_RATIO","provenance_id":pid,"claim_level":1
            })

    # Supporting creep rows and paired microstructure effects
    creep_values = {
        "TMC1": {600:(7.36974e-9,1.01425e-8),650:(3.02692e-7,8.51741e-8),700:(1.0e-6,1.03363e-6)},
        "TMC2": {600:(6.05879e-8,6.1747e-9),650:(2.8786e-7,4.54072e-8),700:(1.7679e-6,7.37214e-7)},
        "TMC3": {600:(2.72824e-8,1.2496e-8),650:(2.1078e-7,1.18317e-7),700:(2.9025e-6,1.84493e-6)},
    }
    creep_rows=[]
    creep_pair_effects=[]
    for tmc,bytemp in creep_values.items():
        for temp,(eq,lam) in bytemp.items():
            for micro,val in [("equiaxed_HT1",eq),("lamellar_HT2",lam)]:
                cond=f"WANG_{tmc}_{micro}_{temp}C_150MPA_CREEP"
                pid=add_prov(f"P_WANG_CR_{tmc}_{temp}_{micro}","WANG2010_MSC",f"WANG_{tmc}",cond,"WANG_PEIPEI_2010_MSC.txt","Table 4-1","DIRECT_TABLE_TEXT",
                             f"{tmc} {micro} {temp} C 150 MPa steady creep rate {val} s-1")
                creep_rows.append({"snapshot_id":snapshot_id,"paper_uid":"WANG2010_MSC","sample_uid":f"WANG_{tmc}","condition_uid":cond,
                    "temperature_C":temp,"stress_MPa":150,"microstructure":micro,"steady_creep_rate_s-1":val,"event":"supporting_service_mode",
                    "evidence_grade":"DIRECT_TABLE_TEXT","provenance_id":pid})
            creep_pair_effects.append({"tmc":tmc,"temperature_C":temp,"equiaxed_rate":eq,"lamellar_rate":lam,
                                       "delta_rate":lam-eq,"lnRR_lamellar_vs_equiaxed":math.log(lam/eq),"percent_change":100*(lam/eq-1)})

    fatigue_fields=list(fatigue_rows[0].keys())
    oxidation_fields=list(ox_rows[0].keys())
    thermal_fields=list(thermal_rows[0].keys())
    write_csv("FATIGUE_SURVIVAL.csv",fatigue_fields,fatigue_rows)
    write_csv("OXIDATION_KINETICS.csv",oxidation_fields,ox_rows)
    write_csv("THERMAL_EXPOSURE_EFFECTS.csv",thermal_fields,thermal_rows)
    write_csv("CREEP_SUPPORTING_EVIDENCE.csv",list(creep_rows[0].keys()),creep_rows)

    # Cohort
    cohort=[]
    for r in fatigue_rows:
        cohort.append({"row_uid":r["condition_uid"],"snapshot_id":snapshot_id,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"mode":"fatigue","property":"cycles_to_failure","value":r["cycles"],"unit":"cycles","included":1,"exclusion_reason":"","evidence_grade":r["evidence_grade"],"provenance_id":r["provenance_id"]})
    for r in ox_rows:
        val=r["mass_gain_mg_cm2"] if r["mass_gain_mg_cm2"]!="" else r["parameter_value"]
        unit="mg cm-2" if r["mass_gain_mg_cm2"]!="" else r["parameter_units"]
        cohort.append({"row_uid":r["condition_uid"],"snapshot_id":snapshot_id,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"mode":"oxidation","property":r["parameter_name"],"value":val,"unit":unit,"included":1,"exclusion_reason":"","evidence_grade":r["evidence_grade"],"provenance_id":r["provenance_id"]})
    for r in thermal_rows:
        cohort.append({"row_uid":r["condition_uid"],"snapshot_id":snapshot_id,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"mode":"thermal_exposure","property":r["property"],"value":"","unit":"retention ratio","included":1,"exclusion_reason":"exact numeric value not identifiable","evidence_grade":r["evidence_grade"],"provenance_id":r["provenance_id"]})
    for r in creep_rows:
        cohort.append({"row_uid":r["condition_uid"],"snapshot_id":snapshot_id,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"mode":"creep_supporting","property":"steady_creep_rate","value":r["steady_creep_rate_s-1"],"unit":"s-1","included":1,"exclusion_reason":"","evidence_grade":r["evidence_grade"],"provenance_id":r["provenance_id"]})
    cohort_fields=["row_uid","snapshot_id","paper_uid","sample_uid","condition_uid","mode","property","value","unit","included","exclusion_reason","evidence_grade","provenance_id"]
    write_csv("ANALYSIS_COHORT.csv",cohort_fields,cohort)

    # Pair matches and effects
    pair_fields=["pair_uid","snapshot_id","paper_uid","treated_sample_uid","control_sample_uid","treated_condition_uid","control_condition_uid","mode","property","match_grade","accepted","mismatch_flags","provenance_treated","provenance_control","notes"]
    pair_rows=[{
        "pair_uid":"PAIR_WEI_600C_20H","snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","treated_sample_uid":"WEI_TMC","control_sample_uid":"WEI_MATRIX",
        "treated_condition_uid":"WEI_600C_20H_TMC","control_condition_uid":"WEI_600C_20H_MATRIX","mode":"oxidation","property":"mass_gain_mg_cm2","match_grade":"A",
        "accepted":1,"mismatch_flags":"reinforcement fraction/topology unresolved in capture","provenance_treated":"P_WEI_TMC","provenance_control":"P_WEI_MATRIX","notes":"Recovery-grade same-work pair."
    }]
    for p in creep_pair_effects:
        pair_rows.append({
            "pair_uid":f"PAIR_WANG_{p['tmc']}_{p['temperature_C']}C","snapshot_id":snapshot_id,"paper_uid":"WANG2010_MSC",
            "treated_sample_uid":f"WANG_{p['tmc']}_LAM","control_sample_uid":f"WANG_{p['tmc']}_EQ",
            "treated_condition_uid":f"WANG_{p['tmc']}_lamellar_HT2_{p['temperature_C']}C_150MPA_CREEP",
            "control_condition_uid":f"WANG_{p['tmc']}_equiaxed_HT1_{p['temperature_C']}C_150MPA_CREEP",
            "mode":"creep_supporting","property":"steady_creep_rate_s-1","match_grade":"A","accepted":1,"mismatch_flags":"microstructure/heat treatment intentionally differs",
            "provenance_treated":f"P_WANG_CR_{p['tmc']}_{p['temperature_C']}_lamellar_HT2","provenance_control":f"P_WANG_CR_{p['tmc']}_{p['temperature_C']}_equiaxed_HT1",
            "notes":"Condition-specific microstructure contrast; not reinforcement effect."
        })
    pair_rows.append({
        "pair_uid":"PAIR_KONG_MATRIX_REJECTED","snapshot_id":snapshot_id,"paper_uid":"KONG2021_IJLMM","treated_sample_uid":"KONG_SIC33_CYL","control_sample_uid":"matrix tensile specimen only",
        "treated_condition_uid":"LCF_SERIES","control_condition_uid":"NO_FATIGUE_MATRIX_CONTROL","mode":"fatigue","property":"cycles_to_failure","match_grade":"E","accepted":0,
        "mismatch_flags":"no matrix fatigue S-N data; matrix UTS is not a fatigue control","provenance_treated":"P_KONG_T1_R1..R7","provenance_control":"","notes":"Prevents invalid fatigue-life lnRR."
    })
    write_csv("PAIR_MATCHES.csv",pair_fields,pair_rows)

    matrix_mass=1.99; tmc_mass=1.57
    delta=tmc_mass-matrix_mass
    lnrr=math.log(tmc_mass/matrix_mass)
    pct=100*(math.exp(lnrr)-1)
    kp_m=matrix_mass**2/20; kp_t=tmc_mass**2/20
    effect_fields=["effect_uid","snapshot_id","paper_uid","sample_uid","condition_uid","mode","estimand","estimate","unit","ci_low","ci_high","prediction_low","prediction_high","independent_papers","atomic_rows","match_grade","claim_level","evidence_grade","provenance_ids","status","notes"]
    effects=[
        {"effect_uid":"E_OX_DELTA_600C20H","snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","sample_uid":"WEI_TMC-vs-WEI_MATRIX","condition_uid":"600C_20H_AIR","mode":"oxidation","estimand":"Delta mass gain (TMC-matrix)","estimate":delta,"unit":"mg cm-2","independent_papers":1,"atomic_rows":2,"match_grade":"A","claim_level":2,"evidence_grade":"DIRECT_TEXT_CAPTURE","provenance_ids":"P_WEI_TMC|P_WEI_MATRIX","status":"RECOVERY_GRADE","notes":"No variance/replicate information."},
        {"effect_uid":"E_OX_LNRR_600C20H","snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","sample_uid":"WEI_TMC-vs-WEI_MATRIX","condition_uid":"600C_20H_AIR","mode":"oxidation","estimand":"lnRR mass gain","estimate":lnrr,"unit":"log ratio","independent_papers":1,"atomic_rows":2,"match_grade":"A","claim_level":2,"evidence_grade":"DERIVED_CALCULATION","provenance_ids":"P_WEI_TMC|P_WEI_MATRIX","status":"RECOVERY_GRADE","notes":"Lower is better."},
        {"effect_uid":"E_OX_PCT_600C20H","snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","sample_uid":"WEI_TMC-vs-WEI_MATRIX","condition_uid":"600C_20H_AIR","mode":"oxidation","estimand":"percent mass-gain change","estimate":pct,"unit":"percent","independent_papers":1,"atomic_rows":2,"match_grade":"A","claim_level":2,"evidence_grade":"DERIVED_CALCULATION","provenance_ids":"P_WEI_TMC|P_WEI_MATRIX","status":"RECOVERY_GRADE","notes":"Lower is better."},
        {"effect_uid":"E_OX_KP_RATIO_600C20H","snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","sample_uid":"WEI_TMC-vs-WEI_MATRIX","condition_uid":"600C_20H_AIR","mode":"oxidation","estimand":"two-point apparent kp ratio","estimate":kp_t/kp_m,"unit":"ratio","independent_papers":1,"atomic_rows":2,"match_grade":"A","claim_level":2,"evidence_grade":"DERIVED_CALCULATION","provenance_ids":"P_WEI_TMC|P_WEI_MATRIX","status":"SENSITIVITY_ONLY","notes":"Origin-constrained one-endpoint diagnostic; not a validated kinetic law."},
    ]
    for p in creep_pair_effects:
        effects.append({"effect_uid":f"E_CREEP_{p['tmc']}_{p['temperature_C']}","snapshot_id":snapshot_id,"paper_uid":"WANG2010_MSC","sample_uid":p['tmc'],"condition_uid":f"{p['temperature_C']}C_150MPA","mode":"creep_supporting","estimand":"lnRR steady creep rate, lamellar/equiaxed","estimate":p["lnRR_lamellar_vs_equiaxed"],"unit":"log ratio","independent_papers":1,"atomic_rows":2,"match_grade":"A","claim_level":2,"evidence_grade":"DIRECT_TABLE_TEXT+DERIVED_CALCULATION","provenance_ids":f"P_WANG_CR_{p['tmc']}_{p['temperature_C']}_lamellar_HT2|P_WANG_CR_{p['tmc']}_{p['temperature_C']}_equiaxed_HT1","status":"OBSERVED_SUPPORT","notes":"Microstructure contrast, not reinforcement effect; lower rate is better."})
    write_csv("EFFECT_ESTIMATES.csv",effect_fields,effects)

    # Fatigue regressions; descriptive only
    stress=np.array([r[0] for r in fatigue_data],float)
    cycles=np.array([r[1] for r in fatigue_data],float)
    fit_all=linreg(np.log10(stress),np.log10(cycles))
    high=stress>=1400; low=stress<1400
    fit_high=linreg(np.log10(stress[high]),np.log10(cycles[high]))
    fit_low=linreg(np.log10(stress[low]),np.log10(cycles[low]))
    hierarchical_fields=["result_uid","snapshot_id","mode","model","outcome","cohort","estimate_name","estimate","se","ci_low","ci_high","n_rows","n_papers","status","claim_level","notes"]
    hierarchy=[]
    for name,fit,cohort_name in [("ALL",fit_all,"1100-1500 MPa"),("HIGH",fit_high,">=1400 MPa"),("LOW",fit_low,"<1400 MPa")]:
        hierarchy.append({"result_uid":f"FATIGUE_{name}","snapshot_id":snapshot_id,"mode":"fatigue","model":"OLS log10(N)=a+b log10(sigma_max)","outcome":"log10 cycles","cohort":cohort_name,"estimate_name":"slope","estimate":fit["slope"],"se":fit["slope_se"],"ci_low":"","ci_high":"","n_rows":fit["n"],"n_papers":1,"status":"DESCRIPTIVE_SINGLE_PAPER","claim_level":1,"notes":f"intercept={fit['intercept']:.8g}; R2={fit['r2']:.6g}; no runouts; no matrix control."})
    hierarchy += [
        {"result_uid":"THERMAL_HIERARCHY","snapshot_id":snapshot_id,"mode":"thermal_exposure","model":"paper/sample hierarchical retention model","outcome":"retention ratio","cohort":"100-120 h evidence","estimate_name":"NOT_IDENTIFIABLE","estimate":"","se":"","ci_low":"","ci_high":"","n_rows":len(thermal_rows),"n_papers":2,"status":"NOT_IDENTIFIABLE","claim_level":1,"notes":"Post-exposure values are figure-only/qualitative in recovered text."},
        {"result_uid":"OXIDATION_HIERARCHY","snapshot_id":snapshot_id,"mode":"oxidation","model":"paper random-effects model","outcome":"lnRR mass gain","cohort":"600-1000 C","estimate_name":"NOT_IDENTIFIABLE","estimate":"","se":"","ci_low":"","ci_high":"","n_rows":len(ox_rows),"n_papers":2,"status":"NOT_IDENTIFIABLE","claim_level":1,"notes":"Only one numeric matched endpoint pair and one separate Q dose series."}
    ]
    write_csv("HIERARCHICAL_RESULTS.csv",hierarchical_fields,hierarchy)

    qfit=linreg([0,5,10,20],[165,187,207,209])
    dose_fields=["dose_result_uid","snapshot_id","paper_uid","mode","dose_variable","support_min","support_max","response","model","estimate_name","estimate","se","r2","n_rows","n_papers","status","claim_level","notes"]
    dose_rows=[
        {"dose_result_uid":"KIM_Q_LINEAR","snapshot_id":snapshot_id,"paper_uid":"KIM2019_MMI","mode":"oxidation","dose_variable":"(TiB+TiC) vol%","support_min":0,"support_max":20,"response":"apparent activation energy","model":"descriptive OLS Q=a+b*dose","estimate_name":"slope","estimate":qfit["slope"],"se":qfit["slope_se"],"r2":qfit["r2"],"n_rows":4,"n_papers":1,"status":"DESCRIPTIVE_SINGLE_PAPER","claim_level":1,"notes":"Observed increments plateau between 10 and 20 vol%; no universal optimal dose."},
        {"dose_result_uid":"OX_RATE_DOSE","snapshot_id":snapshot_id,"paper_uid":"KIM2019_MMI","mode":"oxidation","dose_variable":"(TiB+TiC) vol%","support_min":0,"support_max":20,"response":"mass gain/apparent kp","model":"reported monotonic ordering only","estimate_name":"NOT_IDENTIFIABLE_NUMERIC_CURVE","estimate":"","se":"","r2":"","n_rows":4,"n_papers":1,"status":"NOT_IDENTIFIABLE","claim_level":1,"notes":"Raw multi-time curve coordinates and replicate uncertainty absent."}
    ]
    write_csv("DOSE_RESPONSE.csv",dose_fields,dose_rows)

    interaction_fields=["interaction_uid","snapshot_id","mode","factor_a","factor_b","outcome","estimate","unit","n_rows","n_papers","status","claim_level","notes"]
    interaction_rows=[
        {"interaction_uid":"FATIGUE_STRESS_REGIME","snapshot_id":snapshot_id,"mode":"fatigue","factor_a":"stress regime","factor_b":"damage mechanism","outcome":"log-log S-N slope difference","estimate":fit_high["slope"]-fit_low["slope"],"unit":"slope difference","n_rows":7,"n_papers":1,"status":"DESCRIPTIVE","claim_level":1,"notes":"Mechanistic transition reported near 1400 MPa; not an externally validated breakpoint."},
        {"interaction_uid":"CREEP_MICROSTRUCTURE_TEMP","snapshot_id":snapshot_id,"mode":"creep_supporting","factor_a":"microstructure","factor_b":"temperature","outcome":"lnRR creep rate","estimate":"condition-specific rows in EFFECT_ESTIMATES.csv","unit":"log ratio","n_rows":18,"n_papers":1,"status":"DESCRIPTIVE","claim_level":2,"notes":"Direction varies for TMC1; no universal lamellar benefit."},
        {"interaction_uid":"OX_REINF_TEMP","snapshot_id":snapshot_id,"mode":"oxidation","factor_a":"reinforcement chemistry/topology","factor_b":"temperature/time","outcome":"kinetic regime/spallation","estimate":"","unit":"","n_rows":6,"n_papers":2,"status":"NOT_IDENTIFIABLE_POOLED","claim_level":1,"notes":"TiB can help or harm depending on B2O3 volatility, scale adherence, topology and coating; raw matched matrix is insufficient."}
    ]
    write_csv("INTERACTION_EFFECTS.csv",interaction_fields,interaction_rows)

    hetero_fields=["mode","snapshot_id","independent_papers","atomic_rows","matched_pairs","estimand","tau2","I2_pct","prediction_interval","status","notes"]
    hetero_rows=[
        {"mode":"thermal_exposure","snapshot_id":snapshot_id,"independent_papers":2,"atomic_rows":len(thermal_rows),"matched_pairs":0,"estimand":"retention ratio","status":"NOT_IDENTIFIABLE","notes":"Exact post-exposure numbers absent."},
        {"mode":"oxidation","snapshot_id":snapshot_id,"independent_papers":2,"atomic_rows":len(ox_rows),"matched_pairs":1,"estimand":"lnRR mass gain","status":"NOT_IDENTIFIABLE","notes":"One matched pair cannot estimate between-paper heterogeneity."},
        {"mode":"fatigue","snapshot_id":snapshot_id,"independent_papers":1,"atomic_rows":len(fatigue_rows),"matched_pairs":0,"estimand":"S-N relation or life lnRR","status":"NOT_IDENTIFIABLE","notes":"No matrix fatigue control and no paper cluster."},
        {"mode":"creep_supporting","snapshot_id":snapshot_id,"independent_papers":1,"atomic_rows":len(creep_rows),"matched_pairs":9,"estimand":"lamellar/equiaxed creep-rate lnRR","status":"CONDITION_SPECIFIC_ONLY","notes":"Not pooled into QM15 durability scalar."}
    ]
    write_csv("HETEROGENEITY.csv",hetero_fields,hetero_rows)

    # Sensitivity including leave-one-row-out fatigue fits
    sens_fields=["sensitivity_uid","snapshot_id","mode","analysis","variant","estimate","unit","n_rows","n_papers","status","interpretation"]
    sens=[]
    sens += [
        {"sensitivity_uid":"OX_ENDPOINT_LNRR","snapshot_id":snapshot_id,"mode":"oxidation","analysis":"matched endpoint","variant":"raw mass-gain lnRR","estimate":lnrr,"unit":"log ratio","n_rows":2,"n_papers":1,"status":"RECOVERY_GRADE","interpretation":"Direct endpoint contrast; source identity must be repaired."},
        {"sensitivity_uid":"OX_KP_ORIGIN","snapshot_id":snapshot_id,"mode":"oxidation","analysis":"kinetic assumption","variant":"origin-constrained apparent kp ratio","estimate":kp_t/kp_m,"unit":"ratio","n_rows":2,"n_papers":1,"status":"SENSITIVITY_ONLY","interpretation":"Not a substitute for multi-time kinetic fitting."},
        {"sensitivity_uid":"THERMAL_DIRECT_ONLY","snapshot_id":snapshot_id,"mode":"thermal_exposure","analysis":"evidence grade","variant":"exclude figure-only rows","estimate":"NOT_IDENTIFIABLE","unit":"retention ratio","n_rows":6,"n_papers":1,"status":"NOT_IDENTIFIABLE","interpretation":"Only qualitative direct text remains."},
        {"sensitivity_uid":"LOPO_ALL_MODES","snapshot_id":snapshot_id,"mode":"all","analysis":"leave-one-paper-out","variant":"LOPO","estimate":"NOT_IDENTIFIABLE","unit":"","n_rows":len(cohort),"n_papers":6,"status":"NOT_IDENTIFIABLE_BY_MODE","interpretation":"Each quantitative estimand has only one independent paper; cross-mode LOPO is physically invalid."},
        {"sensitivity_uid":"REVIEW_EXCLUSION","snapshot_id":snapshot_id,"mode":"all","analysis":"source hierarchy","variant":"exclude Jiao 2018 review from estimands","estimate":"UNCHANGED","unit":"","n_rows":len(cohort),"n_papers":6,"status":"PASS","interpretation":"Review is locator/context only and contributes no primary effect estimate."}
    ]
    loo_slopes=[]
    for i in range(len(stress)):
        keep=np.arange(len(stress))!=i
        f=linreg(np.log10(stress[keep]),np.log10(cycles[keep]))
        loo_slopes.append(f["slope"])
        sens.append({"sensitivity_uid":f"FATIGUE_LORO_{i+1}","snapshot_id":snapshot_id,"mode":"fatigue","analysis":"leave-one-row-out","variant":f"drop stress {int(stress[i])} MPa","estimate":f["slope"],"unit":"log-log slope","n_rows":6,"n_papers":1,"status":"DESCRIPTIVE","interpretation":"Row-level sensitivity does not replace paper-cluster uncertainty."})
    sens.append({"sensitivity_uid":"FATIGUE_LORO_RANGE","snapshot_id":snapshot_id,"mode":"fatigue","analysis":"leave-one-row-out","variant":"range","estimate":f"{min(loo_slopes):.8g} to {max(loo_slopes):.8g}","unit":"log-log slope","n_rows":7,"n_papers":1,"status":"DESCRIPTIVE","interpretation":"Single-paper stability diagnostic only."})
    write_csv("SENSITIVITY_ANALYSIS.csv",sens_fields,sens)

    null_fields=["result_uid","snapshot_id","mode","question","result","reason","required_data","claim_ceiling"]
    null_rows=[
        {"result_uid":"N01","snapshot_id":snapshot_id,"mode":"thermal_exposure","question":"Exact post-exposure UTS/EL retention curves","result":"NOT_IDENTIFIABLE","reason":"Recovered sources provide qualitative text or figure-only values.","required_data":"digitized/raw pre-post values with sample IDs and uncertainty","claim_ceiling":"qualitative association"},
        {"result_uid":"N02","snapshot_id":snapshot_id,"mode":"fatigue","question":"TMC versus matrix fatigue-life lnRR","result":"NOT_IDENTIFIABLE","reason":"Kong study has no condition-matched matrix fatigue S-N series.","required_data":"matrix control under same R, frequency, surface, geometry and temperature","claim_ceiling":"single-material descriptive S-N"},
        {"result_uid":"N03","snapshot_id":snapshot_id,"mode":"fatigue","question":"Censor-aware survival model","result":"NOT_IDENTIFIABLE","reason":"Recovered direct series contains zero runouts and one paper.","required_data":"runout indicators and specimen-level repeated observations","claim_ceiling":"uncensored descriptive fit"},
        {"result_uid":"N04","snapshot_id":snapshot_id,"mode":"oxidation","question":"Universal parabolic rate law","result":"REJECTED","reason":"Sources explicitly report parabolic-to-linear transitions, volatilization and spallation.","required_data":"time-resolved mass-change curves and regime diagnostics","claim_ceiling":"condition-specific apparent parameters"},
        {"result_uid":"N05","snapshot_id":snapshot_id,"mode":"all","question":"Single dimensionless durability score","result":"FORBIDDEN","reason":"Thermal retention, mass gain, fatigue life, crack growth and creep rate are non-commensurate physical quantities.","required_data":"not applicable","claim_ceiling":"vector-valued evidence envelope"},
        {"result_uid":"N06","snapshot_id":snapshot_id,"mode":"service","question":"800 C structural service qualification","result":"NOT_SUPPORTED","reason":"Oxidation observations do not establish retained load-bearing, fatigue, creep and damage tolerance at 800 C.","required_data":"integrated 800 C mechanical/oxidation/fatigue/creep evidence","claim_ceiling":"oxidation-only condition statements"},
        {"result_uid":"N07","snapshot_id":snapshot_id,"mode":"fatigue","question":"Reinforcement universally improves fatigue","result":"NEGATIVE/CONTRADICTED","reason":"Context literature includes neutral TiB effects and reduced rolling-contact fatigue from stress concentration.","required_data":"topology- and mode-stratified matched controls","claim_ceiling":"heterogeneous association"}
    ]
    write_csv("NULL_NEGATIVE_RESULTS.csv",null_fields,null_rows)

    conflict_fields=["conflict_id","snapshot_id","paper_uid","field","value_a","source_a","value_b","source_b","resolution","status","impact"]
    conflicts=[
        {"conflict_id":"C001","snapshot_id":snapshot_id,"paper_uid":"KONG2021_IJLMM","field":"fatigue life at 1100 MPa","value_a":52338,"source_a":"Table 1","value_b":52388,"source_b":"abstract/prose","resolution":"Use direct table value for analysis; preserve prose value.","status":"OPEN_SOURCE_CHECK","impact":"minor numeric discrepancy"},
        {"conflict_id":"C002","snapshot_id":snapshot_id,"paper_uid":"LI2013_PHD","field":"TiB volume fraction","value_a":1.26,"source_a":"Chinese abstract/designed fraction","value_b":1.82,"source_b":"English abstract theoretical fraction","resolution":"Do not use dose quantitatively until exact actual/theoretical identity is resolved.","status":"OPEN","impact":"blocks dose attribution"},
        {"conflict_id":"C003","snapshot_id":snapshot_id,"paper_uid":"LI2013_PHD","field":"fracture-toughness improvement","value_a":"47%","source_a":"Chinese summary for triplex oil cooling","value_b":"50.5%","source_b":"English abstract heat-treatment list","resolution":"Exclude from QM15 quantitative synthesis pending table-level audit.","status":"OPEN","impact":"damage-tolerance effect unresolved"},
        {"conflict_id":"C004","snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","field":"publication identity/source hash","value_a":"endpoint capture available","source_a":"recovered normalized evidence","value_b":"original PDF/XML byte identity absent","source_b":"canonical registry missing","resolution":"Retain recovery-grade only and request exact DOI/source bytes.","status":"OPEN","impact":"prevents Gold promotion and interval estimation"}
    ]
    write_csv("CONFLICT_LEDGER.csv",conflict_fields,conflicts)

    # Service damage envelope is vector-valued, never a scalar score
    envelope_fields=["envelope_uid","snapshot_id","paper_uid","material_system","temperature_C","time_h","atmosphere","mode","load_or_stress","surface_condition","topology","observable","direction_of_risk","quantitative_value","unit","evidence_grade","support_status","provenance_ids","notes"]
    envelope=[]
    envelope += [
        {"envelope_uid":"ENV_OX_600","snapshot_id":snapshot_id,"paper_uid":"WEI_RECOVERY_600C","material_system":"Ti-6Al-4V/TiC composite vs matrix","temperature_C":600,"time_h":20,"atmosphere":"air","mode":"oxidation","load_or_stress":"none","surface_condition":"unresolved","topology":"unresolved","observable":"mass-gain lnRR","direction_of_risk":"TMC lower oxidation mass gain","quantitative_value":lnrr,"unit":"log ratio","evidence_grade":"RECOVERY_GRADE_DIRECT_CAPTURE","support_status":"OBSERVED_WITH_IDENTITY_GAP","provenance_ids":"P_WEI_TMC|P_WEI_MATRIX","notes":"No mechanical retention inference."},
        {"envelope_uid":"ENV_FATIGUE_RT","snapshot_id":snapshot_id,"paper_uid":"KONG2021_IJLMM","material_system":"33 vol% continuous SiC/near-alpha Ti","temperature_C":25,"time_h":"4-52338 cycles","atmosphere":"laboratory air/unresolved","mode":"LCF","load_or_stress":"1100-1500 MPa max; R=0.1; 0.5 Hz","surface_condition":"polished cylindrical external matrix","topology":"unidirectional fibers parallel to load","observable":"cycles to failure","direction_of_risk":"rapid life collapse at high stress; internal localized crack initiation at lower stress","quantitative_value":"4 to 52338","unit":"cycles","evidence_grade":"DIRECT_TABLE_TEXT","support_status":"OBSERVED_SINGLE_PAPER","provenance_ids":"P_KONG_T1_R1..R7","notes":"No matrix fatigue control."},
        {"envelope_uid":"ENV_THERMAL_100H","snapshot_id":snapshot_id,"paper_uid":"LI2013_PHD","material_system":"TiB+La2O3/IMI834-like","temperature_C":"600/650/700","time_h":100,"atmosphere":"air/unresolved","mode":"thermal_exposure","load_or_stress":"post-exposure RT tension","surface_condition":"unresolved","topology":"aligned TiB + dispersed La2O3","observable":"UTS/EL retention","direction_of_risk":"UTS retained/slightly increased but ductility decreased; worst at 650 C","quantitative_value":"","unit":"retention ratio","evidence_grade":"DIRECT_TEXT_QUALITATIVE","support_status":"EXACT_RATIO_NOT_IDENTIFIABLE","provenance_ids":"P_LI_TE_*","notes":"Reinforcement stability does not imply interface/ductility stability."},
        {"envelope_uid":"ENV_CRACK_MODEL","snapshot_id":snapshot_id,"paper_uid":"NIU2021_TAFM","material_system":"SiC/Ti6242","temperature_C":"model parameterized","time_h":"spectrum cycles","atmosphere":"not modeled explicitly","mode":"matrix crack growth","load_or_stress":"spectrum loading","surface_condition":"not applicable","topology":"unidirectional continuous fiber","observable":"da/dN","direction_of_risk":"bridging, closure and overload retardation reduce matrix-crack growth; interface debonding/load redistribution control evolution","quantitative_value":"","unit":"m/cycle","evidence_grade":"MODEL_DERIVED","support_status":"MECHANISM_PRIOR_NOT_LIFE_VALIDATION","provenance_ids":"P_NIU_MODEL","notes":"Do not mix modeled crack rate with observed fatigue life."},
        {"envelope_uid":"ENV_OX_800_1000","snapshot_id":snapshot_id,"paper_uid":"KIM2019_MMI","material_system":"Ti/(TiB+TiC)","temperature_C":"800-1000","time_h":"isothermal curves; 40h cyclic at 800 C","atmosphere":"air","mode":"oxidation","load_or_stress":"none","surface_condition":"1000 grit","topology":"uniform particulates","observable":"apparent activation energy and mass-gain ordering","direction_of_risk":"dose raises apparent Q and lowers oxidation rate, but volatile B2O3/CO2, voids and spallation limit benefit","quantitative_value":"165/187/207/209","unit":"kJ mol-1","evidence_grade":"DIRECT_TEXT","support_status":"OBSERVED_SINGLE_PAPER","provenance_ids":"P_KIM_Q_*","notes":"No structural service qualification."}
    ]
    write_csv("SERVICE_DAMAGE_ENVELOPE.csv",envelope_fields,envelope)

    # Extra provenance for model/context
    add_prov("P_NIU_MODEL","NIU2021_TAFM","NIU_SIC_TI6242","SPECTRUM_MODEL","NIU_2021_TAFM.txt","Eqs. friction-slip/Dugdale/Willenborg/Forman","MODEL_DERIVED","Spectrum-loading crack growth model parameters and mechanism chain.")
    add_prov("P_TC17_CONTEXT","TC17_2023_IJF","TC17_NON_TMC","400C_2H_OXIDATION_FATIGUE","TC17_2023_IJF_COMPARATOR.txt","conclusion and Fig.12 caption","DATABASE_PRIOR","Non-TMC oxidation-fatigue comparator; excluded from TMC estimands.")
    add_prov("P_JIAO_REVIEW","JIAO2018_REVIEW","REVIEW","FATIGUE_OXIDATION_CONTEXT","JIAO_2018_JALCOM_REVIEW.txt","Sections 4.2-4.3","DATABASE_PRIOR_REVIEW","Review used to identify contradictory modes and source gaps, not pooled.")
    with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8") as f:
        for r in prov:
            f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")

    # Figure data
    write_csv("figure_data/thermal_exposure_retention_timeline.csv",["paper_uid","exposure_temp_C","exposure_time_h","property","retention_ratio","status","qualitative_change","independent_papers","evidence_grade"],
              [{k:r.get(k,"") for k in ["paper_uid","exposure_temp_C","exposure_time_h","property","retention_ratio","status","qualitative_change"]}|{"independent_papers":2,"evidence_grade":r["evidence_grade"]} for r in thermal_rows])
    ox_endpoint=[]
    for mat,mass in [("Ti-6Al-4V matrix",1.99),("TiC-containing TMC",1.57)]:
        ox_endpoint += [{"material":mat,"time_h":0,"mass_gain_mg_cm2":0,"mass_gain_squared":0,"apparent_kp_mg2_cm4_h":mass**2/20,"evidence_grade":"DERIVED_ORIGIN"},
                        {"material":mat,"time_h":20,"mass_gain_mg_cm2":mass,"mass_gain_squared":mass**2,"apparent_kp_mg2_cm4_h":mass**2/20,"evidence_grade":"DIRECT_TEXT_CAPTURE"}]
    write_csv("figure_data/oxidation_endpoint_kinetics.csv",list(ox_endpoint[0].keys()),ox_endpoint)
    qdata=[{"reinforcement_vol_pct":d,"activation_energy_kJ_mol":q,"paper_uid":"KIM2019_MMI","independent_papers":1,"evidence_grade":"DIRECT_TEXT"} for d,q in [(0,165),(5,187),(10,207),(20,209)]]
    write_csv("figure_data/oxidation_activation_energy_dose.csv",list(qdata[0].keys()),qdata)
    write_csv("figure_data/fatigue_sn.csv",["maximum_stress_MPa","cycles","event_observed","runout","regime","paper_uid","independent_papers","evidence_grade"],
              [{"maximum_stress_MPa":s,"cycles":n,"event_observed":1,"runout":0,"regime":"high/fiber-dominated" if s>=1400 else "lower/matrix-crack propagation","paper_uid":"KONG2021_IJLMM","independent_papers":1,"evidence_grade":"DIRECT_TABLE_TEXT"} for s,n,*_ in fatigue_data])
    write_csv("figure_data/creep_microstructure_effect.csv",list(creep_pair_effects[0].keys()),creep_pair_effects)
    coverage=[]
    for mode,temp,status,level,paper in [
        ("Fatigue",25,"observed_single_paper",2,"KONG2021"),("Oxidation",600,"matched_endpoint_identity_gap",2,"WEI_RECOVERY"),
        ("Thermal retention",550,"qualitative_only",1,"WANG2010"),("Thermal retention",600,"qualitative_only",1,"WANG2010/LI2013"),
        ("Thermal retention",650,"qualitative_only",1,"WANG2010/LI2013"),("Thermal retention",700,"qualitative_only",1,"LI2013"),
        ("Oxidation",800,"kinetics_single_paper",2,"KIM2019"),("Oxidation",900,"kinetics_single_paper",2,"KIM2019"),("Oxidation",1000,"kinetics_single_paper",2,"KIM2019"),
        ("Creep support",600,"table_single_paper",2,"WANG2010"),("Creep support",650,"table_single_paper",2,"WANG2010"),("Creep support",700,"table_single_paper",2,"WANG2010"),
        ("Damage tolerance",600,"data_gap",0,"none"),("Damage tolerance",650,"data_gap",0,"none"),("Damage tolerance",700,"data_gap",0,"none"),("Fatigue",800,"data_gap",0,"none")
    ]:
        coverage.append({"mode":mode,"temperature_C":temp,"evidence_level":level,"status":status,"paper_uid":paper,"physical_risk_score":"FORBIDDEN"})
    write_csv("figure_data/service_damage_envelope.csv",list(coverage[0].keys()),coverage)

    # Plot scripts
    common = """from pathlib import Path\nimport csv\nimport matplotlib.pyplot as plt\nROOT=Path(__file__).resolve().parents[1]\ndef save(fig,name):\n    (ROOT/'figures/png').mkdir(parents=True,exist_ok=True); (ROOT/'figures/svg').mkdir(parents=True,exist_ok=True); (ROOT/'figures/pdf').mkdir(parents=True,exist_ok=True)\n    fig.savefig(ROOT/'figures/png'/f'{name}.png',dpi=600,bbox_inches='tight')\n    fig.savefig(ROOT/'figures/svg'/f'{name}.svg',bbox_inches='tight')\n    fig.savefig(ROOT/'figures/pdf'/f'{name}.pdf',bbox_inches='tight')\n"""
    scripts={
    "plot_thermal_exposure_retention.py": common + """
rows=list(csv.DictReader(open(ROOT/'figure_data/thermal_exposure_retention_timeline.csv',encoding='utf-8')))
fig,ax=plt.subplots(figsize=(9,5.2))
ys={'UTS':1,'EL':0}
for i,r in enumerate(rows):
    x=float(r['exposure_time_h']); y=ys[r['property']] + (i%5-2)*0.025
    ax.scatter(x,y,marker='o' if r['paper_uid']=='LI2013_PHD' else 's')
    ax.annotate(f"{r['paper_uid'].split('2')[0]} {r['exposure_temp_C']} C",(x,y),xytext=(4,3),textcoords='offset points',fontsize=6,rotation=25)
ax.set_yticks([0,1],['Elongation retention','UTS retention'])
ax.set_xlim(90,130); ax.set_ylim(-0.25,1.25)
ax.set_xlabel('Exposure time (h)'); ax.set_title('Thermal-exposure retention evidence: exact ratios not identifiable')
ax.text(0.01,-0.19,'2 independent papers; 18 qualitative/figure-pending endpoints; no numeric curve was fabricated.',transform=ax.transAxes,fontsize=8)
ax.grid(True,alpha=.25); fig.tight_layout(); save(fig,'thermal_exposure_retention_timeline')
""",
    "plot_oxidation_endpoint_kinetics.py": common + """
rows=list(csv.DictReader(open(ROOT/'figure_data/oxidation_endpoint_kinetics.csv',encoding='utf-8')))
fig,ax=plt.subplots(figsize=(7.5,5.2))
for mat in sorted(set(r['material'] for r in rows)):
    z=[r for r in rows if r['material']==mat]; z=sorted(z,key=lambda r:float(r['time_h']))
    ax.plot([float(r['time_h']) for r in z],[float(r['mass_gain_squared']) for r in z],marker='o',label=mat)
ax.set_xlabel('Time (h)'); ax.set_ylabel(r'Squared mass gain (mg$^2$ cm$^{-4}$)')
ax.set_title('Two-point apparent parabolic oxidation diagnostic at 600 C')
ax.legend(); ax.grid(True,alpha=.25)
ax.text(0.01,-0.20,'1 matched recovery-grade paper; ΔW²/t only; not a validated kinetic law; original source identity pending.',transform=ax.transAxes,fontsize=8)
fig.tight_layout(); save(fig,'oxidation_endpoint_kinetics')
""",
    "plot_oxidation_activation_energy_dose.py": common + """
rows=list(csv.DictReader(open(ROOT/'figure_data/oxidation_activation_energy_dose.csv',encoding='utf-8')))
x=[float(r['reinforcement_vol_pct']) for r in rows]; y=[float(r['activation_energy_kJ_mol']) for r in rows]
fig,ax=plt.subplots(figsize=(7.5,5.2)); ax.plot(x,y,marker='o')
for a,b in zip(x,y): ax.annotate(f'{b:.0f}',(a,b),xytext=(4,4),textcoords='offset points')
ax.set_xlabel('(TiB + TiC) reinforcement (vol%)'); ax.set_ylabel('Apparent oxidation activation energy (kJ mol$^{-1}$)')
ax.set_title('Oxidation activation-energy dose series, 800-1000 C')
ax.grid(True,alpha=.25); ax.text(0.01,-0.18,'1 independent paper, n=4 doses; direct text values; condition-specific association, not a universal dose law.',transform=ax.transAxes,fontsize=8)
fig.tight_layout(); save(fig,'oxidation_activation_energy_dose')
""",
    "plot_fatigue_sn.py": common + """
import numpy as np
rows=list(csv.DictReader(open(ROOT/'figure_data/fatigue_sn.csv',encoding='utf-8')))
cycles=np.array([float(r['cycles']) for r in rows]); stress=np.array([float(r['maximum_stress_MPa']) for r in rows])
fig,ax=plt.subplots(figsize=(7.7,5.4)); ax.scatter(cycles,stress,label='Failure')
for mask,label in [(stress>=1400,'High-stress fit'),(stress<1400,'Lower-stress fit')]:
    X=np.column_stack([np.ones(mask.sum()),np.log10(stress[mask])]); b=np.linalg.lstsq(X,np.log10(cycles[mask]),rcond=None)[0]
    sg=np.linspace(stress[mask].min(),stress[mask].max(),100); ng=10**(b[0]+b[1]*np.log10(sg)); ax.plot(ng,sg,label=label)
ax.scatter([],[],marker='>',facecolors='none',edgecolors='black',label='Runout (none recovered)')
ax.set_xscale('log'); ax.set_xlabel('Cycles to failure, N'); ax.set_ylabel('Maximum stress (MPa)')
ax.set_title('LCF S-N response of 33 vol% continuous-SiC/Ti composite')
ax.legend(); ax.grid(True,which='both',alpha=.25)
ax.text(0.01,-0.19,'1 independent paper; 7 failures; R=0.1; 0.5 Hz; no matrix fatigue control; table value 52,338 used at 1100 MPa.',transform=ax.transAxes,fontsize=8)
fig.tight_layout(); save(fig,'fatigue_sn')
""",
    "plot_creep_microstructure_effect.py": common + """
import math
rows=list(csv.DictReader(open(ROOT/'figure_data/creep_microstructure_effect.csv',encoding='utf-8')))
fig,ax=plt.subplots(figsize=(7.7,5.2))
for tmc in sorted(set(r['tmc'] for r in rows)):
    z=sorted([r for r in rows if r['tmc']==tmc],key=lambda r:float(r['temperature_C']))
    ax.plot([float(r['temperature_C']) for r in z],[float(r['lnRR_lamellar_vs_equiaxed']) for r in z],marker='o',label=tmc)
ax.axhline(0,linewidth=.8); ax.set_xlabel('Temperature (C)'); ax.set_ylabel('lnRR steady creep rate (lamellar / equiaxed)')
ax.set_title('Microstructure-dependent creep-rate contrast at 150 MPa')
ax.legend(); ax.grid(True,alpha=.25)
ax.text(0.01,-0.18,'1 independent thesis; 9 matched condition pairs; lower values favor lamellar HT; supporting mode only.',transform=ax.transAxes,fontsize=8)
fig.tight_layout(); save(fig,'creep_microstructure_effect')
""",
    "plot_service_damage_envelope.py": common + """
rows=list(csv.DictReader(open(ROOT/'figure_data/service_damage_envelope.csv',encoding='utf-8')))
modes=['Fatigue','Thermal retention','Oxidation','Creep support','Damage tolerance']; ypos={m:i for i,m in enumerate(modes)}
fig,ax=plt.subplots(figsize=(9,5.6))
for r in rows:
    level=int(r['evidence_level']); marker='x' if level==0 else ('s' if level==1 else 'o')
    ax.scatter(float(r['temperature_C']),ypos[r['mode']],s=35+35*level,marker=marker)
    ax.annotate(r['status'],(float(r['temperature_C']),ypos[r['mode']]),xytext=(3,4),textcoords='offset points',fontsize=6,rotation=25)
ax.set_yticks(range(len(modes)),modes); ax.set_xlabel('Temperature (C)')
ax.set_title('Vector-valued service-damage evidence envelope (not a durability score)')
ax.grid(True,alpha=.25)
ax.text(0.01,-0.18,'Marker size denotes evidence availability only; modes remain physically separate. Crosses are explicit data gaps.',transform=ax.transAxes,fontsize=8)
fig.tight_layout(); save(fig,'service_damage_envelope')
"""
    }
    for name,code in scripts.items():
        write_text("plot_code/"+name,code)

    for name in scripts:
        subprocess.run([sys.executable,str(OUT/"plot_code"/name)],cwd=OUT,check=True)

    plot_specs=[]
    for stem,question in [
        ("thermal_exposure_retention_timeline","Time-dependent retention evidence and exact-ratio gap"),
        ("oxidation_endpoint_kinetics","Matched 600 C endpoint and apparent parabolic diagnostic"),
        ("oxidation_activation_energy_dose","Dose dependence of reported apparent activation energy"),
        ("fatigue_sn","LCF stress-life response with explicit censor state"),
        ("creep_microstructure_effect","Microstructure-temperature supporting risk contrast"),
        ("service_damage_envelope","Vector-valued multimode support envelope without scalar compression")
    ]:
        plot_specs.append({"figure_id":stem,"question":question,"data_file":f"figure_data/{stem}.csv","plot_code":f"plot_code/plot_{stem}.py","outputs":[f"figures/png/{stem}.png",f"figures/svg/{stem}.svg",f"figures/pdf/{stem}.pdf"],"language":"English","png_dpi":600,"independent_papers":"shown in figure/data","claim_ceiling":"descriptive/condition-specific"})
    write_json("PLOT_SPECS.json",plot_specs)

    source_coverage_fields=["source_class","source_count","opened_count","used_directly","used_as_reference","scientific_role","unresolved_gap"]
    source_coverage=[
        {"source_class":"project control package","source_count":1,"opened_count":1,"used_directly":1,"used_as_reference":0,"scientific_role":"integrity and source namespace","unresolved_gap":"canonical Q40 snapshot absent"},
        {"source_class":"platform/code packages","source_count":5,"opened_count":5,"used_directly":1,"used_as_reference":4,"scientific_role":"plot/validation/provenance conventions","unresolved_gap":"none for recovery build"},
        {"source_class":"S03 data/features/harness packages","source_count":10,"opened_count":10,"used_directly":0,"used_as_reference":10,"scientific_role":"quality/UQ/AD/firewall conventions","unresolved_gap":"canonical atomic QM15 matrix not exposed"},
        {"source_class":"V27 literature packages","source_count":10,"opened_count":10,"used_directly":10,"used_as_reference":0,"scientific_role":"primary literature and figure evidence","unresolved_gap":"exact raw curves/replicate uncertainty for selected papers"},
        {"source_class":"primary normalized captures","source_count":6,"opened_count":6,"used_directly":6,"used_as_reference":0,"scientific_role":"atomic rows/effects/mechanisms","unresolved_gap":"original byte hashes and canonical paper/sample/condition UIDs"},
        {"source_class":"review/comparator captures","source_count":2,"opened_count":2,"used_directly":0,"used_as_reference":2,"scientific_role":"negative cases and scope boundary","unresolved_gap":"primary papers underlying review statements"}
    ]
    write_csv("SOURCE_COVERAGE_MATRIX.csv",source_coverage_fields,source_coverage)

    # Core report files
    verdict=dedent(f"""
    # QM15 Executive Verdict — Time-Dependent Thermal, Oxidation, Fatigue and Damage Envelope

    **Snapshot:** `{snapshot_id}` (recovery snapshot; canonical `Q40_INPUT_SNAPSHOT` is missing)  
    **Maximum claim level:** 2 — same-work, condition-specific paired association.

    ## Quantitative results that survive the evidence gate

    1. A recovery-grade same-work oxidation endpoint at **600 C / 20 h in air** gives mass gain **1.57 mg cm⁻²** for the TiC-containing TMC versus **1.99 mg cm⁻²** for the Ti-6Al-4V matrix. The condition-specific estimands are **ΔW = {delta:.3f} mg cm⁻²**, **lnRR = {lnrr:.6f}**, and **{pct:.2f}%** lower mass gain. The origin-constrained two-point apparent parabolic-rate ratio is **{kp_t/kp_m:.6f}**, but it is a sensitivity diagnostic—not a validated kinetic law—because raw multi-time curves and replicate uncertainty are missing.

    2. In Kim et al.'s direct single-paper dose series, apparent oxidation activation energy rises from **165 kJ mol⁻¹** for pure Ti to **187, 207 and 209 kJ mol⁻¹** at **5, 10 and 20 vol% (TiB+TiC)**. This supports condition-specific oxidation-rate suppression, while the same source explicitly limits the benefit through semi-protective TiO₂, volatile B₂O₃/CO₂, voiding and scale spallation.

    3. The direct LCF series for **33 vol% continuous SiC/near-alpha Ti** spans **4 cycles at 1500 MPa** to **52,338 cycles at 1100 MPa** under **R=0.1, 0.5 Hz**. A bilinear stress-life response is descriptive of a high-stress fiber-dominated regime and a lower-stress matrix-crack-propagation regime. No condition-matched matrix fatigue control exists, so fatigue-life lnRR and a causal reinforcement benefit are **NOT_IDENTIFIABLE**.

    4. Two thermal-exposure sources consistently show that reinforcement/interface morphology may remain visually stable while **post-exposure ductility deteriorates sharply**. Exact UTS/EL retention ratios are **NOT_IDENTIFIABLE** from the recovered text because the post-exposure values are figure-only or qualitative. The package therefore provides an evidence timeline, not fabricated retention curves.

    5. Direct creep-rate pairs at 600–700 C show that the lamellar/equiaxed contrast is strongly material- and temperature-dependent; TMC1 even reverses direction. This is a direct counterexample to any universal microstructure durability constant.

    ## Service decision

    The admissible output is a **vector-valued envelope**: thermal retention, oxidation mass gain/kinetics, fatigue survival, crack-growth mechanism and creep support remain separate physical axes. Collapsing them into one dimensionless “durability score” is forbidden. Oxidation resistance at 800–1000 C does not establish load-bearing service qualification at those temperatures. No 800 C structural-service claim, Gold promotion, production-model registration or VALIDATED composition is made.

    ## Terminal state

    `CONTINUE_DATA_GAP`: the recovery analysis is complete and reproducible, but authoritative V29/Q40 atomic records, original publication byte hashes, exact thermal-retention values, raw oxidation curves/replicates, fatigue matrix controls/runouts, and direct fracture-toughness/crack-growth observations remain required.
    """).strip()
    write_text("00_EXECUTIVE_VERDICT.md",verdict)

    methods=dedent("""
    # METHODS

    ## Atomicity and source hierarchy
    One row is paper × sample × actual material state × processing/heat treatment × exposure/test condition × property. Primary tables/text outrank reviews and model priors. Review and TC17 comparator evidence are used only for contradiction discovery and scope control. Every scientific row and effect binds snapshot, paper, sample, condition and provenance identifiers.

    ## Estimands
    Continuous positive outcomes use ΔY, lnRR and percent change when a valid matched control exists. Oxidation mass gain is lower-is-better. The 600 C endpoint pair is evaluated directly; the apparent parabolic constant ΔW²/t is explicitly a one-endpoint, origin-constrained sensitivity diagnostic. Thermal-exposure retention ratios remain missing rather than inferred from adjectives.

    ## Fatigue and censoring
    FATIGUE_SURVIVAL.csv stores event_observed and runout separately. The recovered Kong series has seven failures and zero runouts, so no censor-aware survival curve is estimated. OLS fits log10(N)=a+b log10(σmax) for the full series and pre-specified high/lower stress regimes. Leave-one-row-out is a stability diagnostic; it is not paper-cluster uncertainty. A matrix tensile curve is never treated as a fatigue control.

    ## Oxidation
    Oxidation mode, atmosphere, temperature, time, reinforcement dose/topology and kinetic-law status remain explicit. Apparent activation energies are direct reported values. Parabolic behavior is not universal: regime changes, volatilization, scale breakage and spallation are retained as physical limitations.

    ## Thermal exposure and damage
    Pre/post traceability is required for numeric retention. Qualitative source statements are preserved with blank pre_value, post_value and retention_ratio fields and status NOT_IDENTIFIABLE_EXACT_RATIO. Model-derived crack-growth evidence is separated from observed fatigue life.

    ## Uncertainty, dependence and claim ceiling
    No pseudo-replication across atomic rows is used to claim independent sample size. By mode, quantitative estimands have only one independent paper; therefore paper-cluster bootstrap, random-effects heterogeneity, prediction intervals and LOPO pooled effects are not identifiable. The maximum claim is Level 2 for condition-specific same-work pairs and Level 1 for descriptive single-paper dose/S-N relations.

    ## Service envelope
    SERVICE_DAMAGE_ENVELOPE.csv is vector-valued. No normalization or weighted summation across mass gain, retention ratio, cycles, da/dN or creep rate is permitted.
    """).strip()
    write_text("METHODS.md",methods)
    limitations=dedent("""
    # LIMITATIONS

    - The canonical `Q40_INPUT_SNAPSHOT`, V29 atomic records, authoritative source registry and original-byte hashes were not available in this window.
    - The 600 C oxidation endpoint is recovery-grade because exact publication identity and raw curve/replicate uncertainty are unresolved.
    - Thermal-exposure post-values are qualitative or figure-only; exact retention curves are not recoverable without digitization/source tables.
    - The direct fatigue series is one material, one paper, one R and one frequency, with no runouts and no matched matrix fatigue control.
    - Kim's activation-energy series is a one-paper dose association; it does not establish a universal optimum or long-time kinetic law.
    - Review-reported coating/hybrid-oxidation comparisons are not promoted into primary effect estimates.
    - Crack-growth modeling is a mechanism prior, not independent experimental validation.
    - Damage tolerance is underdetermined: direct KIC/da-dN pre/post exposure data with exact sample identity are required.
    - No conclusion supports 800 C structural service, production registration or a validated formulation.
    """).strip()
    write_text("LIMITATIONS.md",limitations)

    request={
        "window_id":"QM15","snapshot_id":snapshot_id,"status":"CONTINUE_DATA_GAP",
        "required":[
            {"priority":1,"object":"canonical Q40_INPUT_SNAPSHOT and V29 ATOMIC_RECORDS/PROVENANCE/CONFLICT_LEDGER/EXCLUDED_RECORDS/source registry","reason":"bind canonical source_hash+paper_uid+sample_uid+condition_uid and enable authoritative paper clustering"},
            {"priority":2,"object":"original PDF/XML and raw tables/curves for WEI_RECOVERY_600C","reason":"resolve publication identity, exact reinforcement dose/topology, curve coordinates, replicates and uncertainty"},
            {"priority":3,"object":"raw/digitizable pre-post UTS/YS/EL values for Wang 2010 and Li 2013 thermal exposure","reason":"compute retention ratios and time/temperature response"},
            {"priority":4,"object":"condition-matched matrix/TMC specimen-level fatigue S-N data with runout flags, R, frequency, surface, orientation and temperature","reason":"censor-aware fatigue lnRR and paper-cluster uncertainty"},
            {"priority":5,"object":"direct fracture-toughness and crack-growth datasets before/after exposure with topology/interface observations","reason":"quantify damage-tolerance envelope"},
            {"priority":6,"object":"raw Kim 2019 oxidation mass-gain curves and replicate SD","reason":"fit and test parabolic/linear/mixed regimes rather than rely on apparent Q only"}
        ],
        "do_not_do":["do not synthesize missing values","do not auto-promote evidence","do not register an analysis model","do not collapse modes into a scalar score"]
    }
    write_json("WEB_TO_LOCAL_REQUEST.json",request)
    local_prompt=dedent(f"""
    # LOCAL_ABSORPTION_PROMPT — QM15

    Absorb the delivered QM15 recovery artifact without changing ACTIVE until every gate passes.

    1. Verify `CHECKSUMS.sha256`, `MANIFEST.json`, all CSV schemas, all SVG/PDF/600-dpi PNG triplets and independent recomputation.
    2. Resolve authoritative `Q40_INPUT_SNAPSHOT`; map every row to canonical `source_hash + paper_uid + sample_uid + condition_uid`.
    3. Re-open original PDF/XML for Kong 2021, Kim 2019, Wang 2010, Li 2013, Niu 2021 and the 600 C endpoint source. Resolve conflicts C001-C004.
    4. Restore exact thermal-exposure pre/post values and raw oxidation curves; retain atmosphere, surface, orientation, stress ratio, frequency and topology.
    5. Add specimen-level fatigue controls/runouts and direct KIC/da-dN evidence before fitting censor-aware or hierarchical models.
    6. Run `python analysis_code/recompute_qm15.py` and `python analysis_code/validate_package.py`; compare hashes and reported estimands.
    7. Never combine damage modes into one score. Never register these analysis fits as production SUP/SSL models, self-promote Gold or label a formulation VALIDATED.
    8. Return a signed receipt with old/new snapshot IDs, changed rows, closed/open conflicts, recomputation deltas, CRC/SHA results and ACTIVE decision.

    Recovery snapshot: `{snapshot_id}`.
    """).strip()
    write_text("LOCAL_ABSORPTION_PROMPT.md",local_prompt)

    # Empty-but-schema common outputs where pooled inference is inadmissible
    write_csv("EXCLUDED_RECORDS.csv",["record_uid","paper_uid","sample_uid","condition_uid","reason","provenance_id"],[
        {"record_uid":"EX_TC17","paper_uid":"TC17_2023_IJF","sample_uid":"TC17_NON_TMC","condition_uid":"400C_2H_OXIDATION_FATIGUE","reason":"non-composite comparator; context only","provenance_id":"P_TC17_CONTEXT"},
        {"record_uid":"EX_JIAO_REVIEW","paper_uid":"JIAO2018_REVIEW","sample_uid":"REVIEW","condition_uid":"FATIGUE_OXIDATION_CONTEXT","reason":"review; locator/context only","provenance_id":"P_JIAO_REVIEW"}
    ])

    # Recompute script
    recompute_code = r'''from pathlib import Path
import csv, math, json, numpy as np
R=Path(__file__).resolve().parents[1]
ox=list(csv.DictReader(open(R/'OXIDATION_KINETICS.csv',encoding='utf-8')))
w=[r for r in ox if r['paper_uid']=='WEI_RECOVERY_600C']
vals={r['sample_uid']:float(r['mass_gain_mg_cm2']) for r in w}
lnrr=math.log(vals['WEI_TMC']/vals['WEI_MATRIX'])
print(json.dumps({'lnRR_mass_gain':lnrr,'pct_change':100*(math.exp(lnrr)-1),'kp_ratio':(vals['WEI_TMC']/vals['WEI_MATRIX'])**2},indent=2))
fat=list(csv.DictReader(open(R/'FATIGUE_SURVIVAL.csv',encoding='utf-8')))
x=np.log10([float(r['maximum_stress_MPa']) for r in fat]); y=np.log10([float(r['cycles']) for r in fat])
X=np.column_stack([np.ones(len(x)),x]); b=np.linalg.lstsq(X,y,rcond=None)[0]
print(json.dumps({'fatigue_intercept':float(b[0]),'fatigue_slope':float(b[1]),'n':len(y)},indent=2))
assert len(w)==2 and len(fat)==7
'''
    write_text("analysis_code/recompute_qm15.py",recompute_code)
    run_all = r'''from pathlib import Path
import subprocess, sys
R=Path(__file__).resolve().parent
for p in sorted((R/'plot_code').glob('plot_*.py')):
    subprocess.run([sys.executable,str(p)],cwd=R,check=True)
subprocess.run([sys.executable,str(R/'analysis_code/recompute_qm15.py')],cwd=R,check=True)
subprocess.run([sys.executable,str(R/'analysis_code/validate_package.py')],cwd=R,check=True)
'''
    write_text("run_all.py",run_all)
    write_text("requirements.lock","numpy==2.1.1\nmatplotlib==3.9.2")

    status={
        "window_id":"QM15","snapshot_id":snapshot_id,"canonical_snapshot_status":"MISSING",
        "papers_seen":7,"papers_included":6,"independent_papers":6,"atomic_rows":len(cohort),
        "matched_pairs":sum(int(r["accepted"]) for r in pair_rows),"effect_estimates":len(effects),
        "plots_generated":len(plot_specs),"open_conflicts":len(conflicts),"claim_level_max":2,
        "status":"CONTINUE_DATA_GAP","next_action":"Resolve canonical snapshot/source identities and restore raw thermal/oxidation/fatigue/damage-tolerance data.",
        "production_model_registration":"FORBIDDEN","gold_promotion":"FORBIDDEN","validated_formulation":"NONE",
        "terminal_line":"STATUS: CONTINUE_DATA_GAP | WINDOW=QM15 | MISSING=CANONICAL_Q40_SNAPSHOT+RAW_PREPOST_CURVES+FATIGUE_CONTROLS_RUNOUTS+DIRECT_DAMAGE_TOLERANCE | NEXT=LOCAL_SOURCE_REBIND_AND_RECOMPUTE"
    }
    write_json("WINDOW_STATUS.json",status)
    write_json("SNAPSHOT_VALIDATION.json",{
        "snapshot_id":snapshot_id,"snapshot_basis":"26 project package hashes + recovery seed","canonical_snapshot_found":False,
        "all_project_packages_terminally_classified":True,"package_count":26,"source_captures":len(source_captures),
        "scientific_effects_do_not_use_production_models":True,"status":"RECOVERY_SNAPSHOT_ONLY"
    })

    # Tests and validator
    test_code = r'''from pathlib import Path
import csv, json, math, zipfile
R=Path(__file__).resolve().parents[1]
def rows(name): return list(csv.DictReader(open(R/name,encoding='utf-8')))
def test_required():
    req=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','THERMAL_EXPOSURE_EFFECTS.csv','OXIDATION_KINETICS.csv','FATIGUE_SURVIVAL.csv','SERVICE_DAMAGE_ENVELOPE.csv']
    assert all((R/p).exists() for p in req)
def test_atomic_ids(): assert all(r['paper_uid'] and r['sample_uid'] and r['condition_uid'] and r['provenance_id'] for r in rows('ANALYSIS_COHORT.csv'))
def test_fatigue():
    f=rows('FATIGUE_SURVIVAL.csv'); assert len(f)==7 and sum(int(r['runout']) for r in f)==0 and int(f[-1]['cycles'])==52338
def test_oxidation_effect():
    e={r['effect_uid']:r for r in rows('EFFECT_ESTIMATES.csv')}; assert abs(float(e['E_OX_LNRR_600C20H']['estimate'])-math.log(1.57/1.99))<1e-12
def test_no_fake_retention(): assert all(r['retention_ratio']=='' and r['status']=='NOT_IDENTIFIABLE_EXACT_RATIO' for r in rows('THERMAL_EXPOSURE_EFFECTS.csv'))
def test_vector_envelope(): assert all('score' not in k.lower() for k in rows('SERVICE_DAMAGE_ENVELOPE.csv')[0])
def test_figures():
    specs=json.load(open(R/'PLOT_SPECS.json',encoding='utf-8')); assert len(specs)>=4
    for s in specs:
        assert (R/s['data_file']).exists() and (R/s['plot_code']).exists()
        assert all((R/p).exists() and (R/p).stat().st_size>500 for p in s['outputs'])
def test_status(): assert json.load(open(R/'WINDOW_STATUS.json',encoding='utf-8'))['status']=='CONTINUE_DATA_GAP'
def test_no_nested_zip(): assert not list(R.rglob('*.zip'))
def test_terminal_ledger(): assert all(r['terminal_use_status'] in {'USED_DIRECTLY','USED_AS_REFERENCE','SUPERSEDED_BY_HASH','OUT_OF_SCOPE','BLOCKED_CORRUPT','NOT_RELEVANT_TO_WINDOW'} for r in rows('INPUT_LEDGER.csv'))
if __name__=='__main__':
    for n,v in sorted(globals().copy().items()):
        if n.startswith('test_') and callable(v): v(); print('PASS',n)
'''
    write_text("tests/test_qm15_outputs.py",test_code)
    validator_code = r'''from pathlib import Path
import csv, hashlib, json, subprocess, sys
R=Path(__file__).resolve().parents[1]
required=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','THERMAL_EXPOSURE_EFFECTS.csv','OXIDATION_KINETICS.csv','FATIGUE_SURVIVAL.csv','SERVICE_DAMAGE_ENVELOPE.csv']
errors=[]
for p in required:
    if not (R/p).exists(): errors.append('missing:'+p)
if list(R.rglob('*.zip')): errors.append('nested_zip_present')
for line in (R/'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines():
    h,rel=line.split('  ',1); q=R/rel
    if not q.exists(): errors.append('checksum_missing:'+rel); continue
    if hashlib.sha256(q.read_bytes()).hexdigest()!=h: errors.append('checksum_mismatch:'+rel)
subprocess.run([sys.executable,str(R/'tests/test_qm15_outputs.py')],cwd=R,check=True)
if errors: raise SystemExit('\n'.join(errors))
print(json.dumps({'pass':True,'required_files':len(required),'checked_checksums':len((R/'CHECKSUMS.sha256').read_text().splitlines())},indent=2))
'''
    write_text("analysis_code/validate_package.py",validator_code)

    # Preliminary test run before manifest/checksums
    test_run=subprocess.run([sys.executable,str(OUT/"tests/test_qm15_outputs.py")],cwd=OUT,text=True,capture_output=True,check=True)
    write_text("TEST_OUTPUT.txt",test_run.stdout)
    recompute_run=subprocess.run([sys.executable,str(OUT/"analysis_code/recompute_qm15.py")],cwd=OUT,text=True,capture_output=True,check=True)
    write_text("RECOMPUTE_OUTPUT.txt",recompute_run.stdout)

    visual=[]
    for p in sorted((OUT/"figures/png").glob("*.png")):
        size=png_size(p)
        visual.append({"file":str(p.relative_to(OUT)),"bytes":p.stat().st_size,"width_px":size[0] if size else None,"height_px":size[1] if size else None,"status":"PASS_NONEMPTY_PNG" if p.stat().st_size>500 else "FAIL"})
    for ext in ["svg","pdf"]:
        for p in sorted((OUT/f"figures/{ext}").glob(f"*.{ext}")):
            visual.append({"file":str(p.relative_to(OUT)),"bytes":p.stat().st_size,"status":"PASS_NONEMPTY" if p.stat().st_size>500 else "FAIL"})
    write_json("PDF_VISUAL_QA.json",{"figure_triplets":len(plot_specs),"checks":visual,"note":"Automated structural QA; scientific labels/data are defined in PLOT_SPECS and figure_data."})

    terminal=status["terminal_line"]
    write_text("RUN_LOG.txt",dedent(f"""
    WINDOW=QM15 | SNAPSHOT={snapshot_id} | INPUT_MODE=COHORT_BUILD
    Project packages terminally classified: 26
    Atomic cohort rows: {len(cohort)}
    Accepted matched pairs: {sum(int(r['accepted']) for r in pair_rows)}
    Effect rows: {len(effects)}
    Figure triplets: {len(plot_specs)}
    Production registration: FORBIDDEN
    {terminal}
    """))
    write_text("STATUS.txt",terminal)

    # Manifest excludes itself and checksums at creation time
    files=[]
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256"}:
            files.append({"path":str(p.relative_to(OUT)).replace(os.sep,"/"),"bytes":p.stat().st_size,"sha256":sha256_file(p)})
    manifest={
        "window_id":"QM15","snapshot_id":snapshot_id,"status":"CONTINUE_DATA_GAP","generated_by":"jobs/qm15/build.py",
        "file_count_excluding_manifest_and_checksums":len(files),"files":files,"required_common_files_present":True,
        "scope_files":["THERMAL_EXPOSURE_EFFECTS.csv","OXIDATION_KINETICS.csv","FATIGUE_SURVIVAL.csv","SERVICE_DAMAGE_ENVELOPE.csv"],
        "figure_triplets":len(plot_specs),"nested_zip_count":0,"production_model_registration":"FORBIDDEN"
    }
    write_json("MANIFEST.json",manifest)
    checksum_lines=[]
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name!="CHECKSUMS.sha256":
            checksum_lines.append(f"{sha256_file(p)}  {str(p.relative_to(OUT)).replace(os.sep,'/')}")
    write_text("CHECKSUMS.sha256","\n".join(checksum_lines))

    # Validator now sees final checksums
    val=subprocess.run([sys.executable,str(OUT/"analysis_code/validate_package.py")],cwd=OUT,text=True,capture_output=True,check=True)
    write_text("VALIDATION_REPORT.json",json.dumps({"pass":True,"validator_stdout":val.stdout,"file_count":sum(1 for p in OUT.rglob('*') if p.is_file()),"nested_zip_count":0},ensure_ascii=False,indent=2))
    # Refresh checksums after validation report only; validator report is included, CHECKSUMS self-excluded.
    checksum_lines=[]
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name!="CHECKSUMS.sha256":
            checksum_lines.append(f"{sha256_file(p)}  {str(p.relative_to(OUT)).replace(os.sep,'/')}")
    write_text("CHECKSUMS.sha256","\n".join(checksum_lines))

    print(json.dumps({"window_id":"QM15","snapshot_id":snapshot_id,"status":"CONTINUE_DATA_GAP","files":sum(1 for p in OUT.rglob('*') if p.is_file()),"atomic_rows":len(cohort),"matched_pairs":sum(int(r['accepted']) for r in pair_rows),"effects":len(effects),"plots":len(plot_specs)},ensure_ascii=False,indent=2))
    print(terminal)


if __name__ == "__main__":
    main()
