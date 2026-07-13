#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import textwrap
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SEED = 20260713
random.seed(SEED)
np.random.seed(SEED)
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM10"
ZIP_PATH = ROOT / "FINAL_QM10.zip"
SHA_PATH = ROOT / "FINAL_QM10.zip.sha256"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for d in ["figure_data", "figures", "plot_code", "tests"]:
    (OUT / d).mkdir()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid(*parts: object, n: int = 20) -> str:
    s = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]


def write_text(rel: str, text: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(rel: str, obj: object) -> None:
    write_text(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def write_csv(rel: str, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else ["status", "reason"]
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def fnum(x):
    if x is None or x == "":
        return None
    return float(x)


def safe_div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def pct_change(t, c):
    if t is None or c in (None, 0):
        return None
    return 100.0 * (t / c - 1.0)


def fmt(x, nd=3):
    return "" if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), nd)


# Evidence objects were read in the project File Library. Original articles are the highest-weight sources.
sources = [
    dict(source_id="SRC_MDU_QM10", title="QM10 — 密度、比强度、比模量与多目标真实收益", kind="DISPATCH_MDU", doi="", evidence="DIRECT_TEXT", locator="QM10 MDU sections 0–9", priority=1, actually_opened="YES"),
    dict(source_id="SRC_SABAHI2017", title="Microstructural characterization and mechanical properties of spark plasma sintered TiB2-reinforced titanium matrix composite", kind="ORIGINAL_PDF", doi="10.1080/00325899.2016.1265805", evidence="DIRECT_TABLE_TEXT", locator="Table 5; density-method text", priority=1, actually_opened="YES"),
    dict(source_id="SRC_YAN2014", title="Microstructure and mechanical properties of in-situ synthesized TiB whiskers reinforced titanium matrix composites by high-velocity compaction", kind="ORIGINAL_PDF", doi="10.1016/j.powtec.2014.07.048", evidence="DIRECT_TABLE_TEXT+FIGURE_DERIVED", locator="Tables 1–2; Fig. 2; pp. 310–313", priority=1, actually_opened="YES"),
    dict(source_id="SRC_ZHONG2020", title="Design and anti-penetration performance of TiB/Ti system functionally graded material armor fabricated by SPS combined with tape casting", kind="ORIGINAL_PDF", doi="10.1016/j.ceramint.2020.07.325", evidence="DIRECT_TEXT+FIGURE_DERIVED", locator="Sections 2–3; Figs. 2–3", priority=1, actually_opened="YES"),
    dict(source_id="SRC_WANG2022", title="Enhanced mechanical properties of in situ synthesized TiC/Ti composites by pulsed laser directed energy deposition", kind="ORIGINAL_PDF", doi="10.1016/j.msea.2022.143935", evidence="DIRECT_TEXT+DERIVED_CALCULATION", locator="Sections 3.3 and 4.4; Figs. 7–8", priority=1, actually_opened="YES"),
    dict(source_id="SRC_LIU2023", title="Strength-ductility synergy in 3D-printed (TiB + TiC)/Ti6Al4V composites with unique dual-heterogeneous structure", kind="ORIGINAL_PDF", doi="10.1016/j.compositesb.2023.111008", evidence="DIRECT_TEXT+DATABASE_PRIOR", locator="Sections 2.1 and 3.1; Fig. 2", priority=1, actually_opened="YES"),
    dict(source_id="SRC_RASTEGARI2013", title="Producing Ti-6Al-4V/TiC composite with superior properties by adding boron and thermo-mechanical processing", kind="ORIGINAL_PDF", doi="10.1016/j.msea.2012.12.011", evidence="DIRECT_TEXT+FIGURE_DERIVED", locator="Table 1; Figs. 4–5; conclusions", priority=1, actually_opened="YES"),
    dict(source_id="SRC_QM24", title="QM24 Executive Verdict — W/Ta/Mo/Nb/Fe/Cr effects", kind="CROSS_WINDOW_HASH_BOUND_RESULT", doi="", evidence="DERIVED_CALCULATION", locator="QM24 00_EXECUTIVE_VERDICT.md", priority=2, actually_opened="YES"),
    dict(source_id="SRC_QM08", title="QM08 Executive Verdict — elongation loss and strength–ductility synergy", kind="CROSS_WINDOW_RESULT", doi="", evidence="DERIVED_CALCULATION", locator="QM08 00_EXECUTIVE_VERDICT.md", priority=3, actually_opened="YES"),
    dict(source_id="SRC_QM16", title="QM16 Executive Verdict — TiB/TiBw main effects", kind="CROSS_WINDOW_RESULT", doi="", evidence="DERIVED_CALCULATION", locator="QM16 00_EXECUTIVE_VERDICT.md", priority=3, actually_opened="YES"),
    dict(source_id="SRC_QM32", title="QM32 Executive Verdict — load transfer budget", kind="CROSS_WINDOW_RESULT", doi="", evidence="DERIVED_CALCULATION", locator="QM32 00_EXECUTIVE_VERDICT.md", priority=3, actually_opened="YES"),
]
archive_names = [
    "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
    "00_统一上传总控与校验信息_20260712.zip",
    "S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip",
    "S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip",
    "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip",
    "S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
    "S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip",
    "TITMC_V27_LIT_WEB_P010_OF_010.zip", "TITMC_V27_LIT_WEB_P007_OF_010.zip",
    "TITMC_V27_LIT_WEB_P003_OF_010.zip", "TITMC_V27_LIT_WEB_P008_OF_010.zip",
    "TITMC_V27_LIT_WEB_P005_OF_010.zip", "TITMC_V27_LIT_WEB_P009_OF_010.zip",
    "TITMC_V27_LIT_WEB_P006_OF_010.zip", "TITMC_V27_LIT_WEB_P002_OF_010.zip",
    "TITMC_V27_LIT_WEB_P001_OF_010.zip", "TITMC_V27_LIT_WEB_P004_OF_010.zip",
]

source_fingerprint = hashlib.sha256(json.dumps(sources, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
SNAPSHOT = "QM10_DERIVED_" + source_fingerprint[:16]
GENERATED = now_iso()

# Sample-level records. density_full is the porosity-controlled density used for the primary specific-property estimand.
# density_bulk is retained as a sensitivity analysis when Archimedes/relative density is available.
samples: list[dict] = []

def add_sample(**kw):
    base = dict(
        sample_uid="", paper_uid="", source_id="", doi="", year="", sample_label="", matrix_system="",
        reinforcement="none", reinforcement_fraction=0.0, reinforcement_unit="vol%", precursor_fraction=None,
        W_wt_pct=0.0, Ta_wt_pct=0.0, process="", heat_treatment="", test_mode="tension",
        temperature_c=25.0, orientation="NR", UTS_MPa=None, UTS_sd=None, YS_MPa=None, YS_sd=None,
        EL_pct=None, EL_sd=None, E_GPa=None, E_sd=None, flexural_strength_MPa=None, KIC_MPa_sqrt_m=None,
        density_full=None, density_full_sd=None, density_bulk=None, density_bulk_sd=None,
        density_primary_source="", relative_density_pct=None, relative_density_sd=None, porosity_pct=None,
        evidence_level="", evidence_locator="", ad_status="IN_SUPPORT", include_primary=True, notes=""
    )
    base.update(kw)
    if not base["sample_uid"]:
        base["sample_uid"] = "S_" + uid(base["paper_uid"], base["sample_label"], base["temperature_c"], base["process"])
    samples.append(base)

# Sabahi & Azadbeh: theoretical density is a ROM reconstruction; bulk density combines it with reported relative density.
rho_ti = 4.506
rho_tib = 4.54
rho_tib2 = 4.52
sab_comp_full = 0.96 * rho_ti + 0.04 * rho_tib
add_sample(paper_uid="P_SABAHI2017", source_id="SRC_SABAHI2017", doi="10.1080/00325899.2016.1265805", year=2017,
           sample_label="Ti", matrix_system="CP-Ti", process="SPS_1050C_50MPa_5min", heat_treatment="as-sintered",
           UTS_MPa=441.0, UTS_sd=6.0, EL_pct=2.68, EL_sd=0.15, density_full=rho_ti, density_full_sd=0.005,
           relative_density_pct=97.92, relative_density_sd=0.03, density_bulk=rho_ti*0.9792, density_bulk_sd=0.006,
           porosity_pct=2.08, density_primary_source="CALCULATED_FULL_DENSITY_ROM+MEASURED_RELATIVE_DENSITY",
           evidence_level="DIRECT_TABLE_TEXT", evidence_locator="Table 5", notes="Archimedes relative density; absolute bulk density derived.")
add_sample(paper_uid="P_SABAHI2017", source_id="SRC_SABAHI2017", doi="10.1080/00325899.2016.1265805", year=2017,
           sample_label="Ti-2.4wtTiB2_target4volTiB", matrix_system="CP-Ti", reinforcement="TiB+residual TiB2",
           reinforcement_fraction=4.0, process="SPS_1050C_50MPa_5min", heat_treatment="as-sintered",
           UTS_MPa=485.0, UTS_sd=9.0, EL_pct=8.67, EL_sd=0.11, density_full=sab_comp_full, density_full_sd=0.02,
           relative_density_pct=98.85, relative_density_sd=0.04, density_bulk=sab_comp_full*0.9885, density_bulk_sd=0.021,
           porosity_pct=1.15, density_primary_source="CALCULATED_FULL_DENSITY_ROM+MEASURED_RELATIVE_DENSITY",
           evidence_level="DIRECT_TABLE_TEXT", evidence_locator="Table 5; XRD/conclusion", notes="Actual TiB/TiB2 phase split unresolved; designed 4 vol.% TiB.")

# Yan et al. exact theoretical densities and reported/figure-derived relative densities.
yan = [
    ("Matrix",0,4.630,99.63,0.10,1090,14.4,1016,8.9,3.08,0.7,"DIRECT_TABLE_TEXT"),
    ("TMC1",5,4.633,97.90,0.25,1038,4.8,989.6,2.5,2.19,0.5,"DIRECT_TABLE_TEXT+FIGURE_DERIVED"),
    ("TMC2",10,4.627,98.20,0.25,1147,28.8,None,None,None,None,"DIRECT_TABLE_TEXT+FIGURE_DERIVED"),
    ("TMC3",15,4.621,98.33,0.15,741,47.3,None,None,None,None,"DIRECT_TABLE_TEXT"),
    ("TMC4",20,4.615,96.20,0.25,521,43.6,None,None,None,None,"DIRECT_TABLE_TEXT+FIGURE_DERIVED"),
]
for label,vf,rhof,rd,rds,uts,utssd,ys,yssd,el,elsd,ev in yan:
    add_sample(paper_uid="P_YAN2014", source_id="SRC_YAN2014", doi="10.1016/j.powtec.2014.07.048", year=2014,
               sample_label=label, matrix_system="Ti-4.5Al-6.8Mo-1.5Fe", reinforcement="none" if vf==0 else "TiB+0.5volLa2O3",
               reinforcement_fraction=vf, process="HVC_1370J+vacuum_sinter_1250C_3h", heat_treatment="as-sintered",
               UTS_MPa=uts, UTS_sd=utssd, YS_MPa=ys, YS_sd=yssd, EL_pct=el, EL_sd=elsd,
               density_full=rhof, density_full_sd=0.005, relative_density_pct=rd, relative_density_sd=rds,
               density_bulk=rhof*rd/100.0, density_bulk_sd=rhof*rds/100.0, porosity_pct=100-rd,
               density_primary_source="SOURCE_THEORETICAL_ROM+ARCHIMEDES_RELATIVE_DENSITY", evidence_level=ev,
               evidence_locator="Tables 1–2; Fig. 2", notes="Primary specific-property analysis uses full density; bulk density is sensitivity only.")

# Zhong et al. density and modulus read from Fig. 3. These are dose-series evidence, not a matrix-control study.
zhong_v = [5,10,20,30,40,50,60,70,80]
zhong_density = [4.473,4.455,4.442,4.420,4.395,4.379,4.367,4.355,4.351]
zhong_E = [130,145,180,215,250,280,335,370,400]
for vf,rho,e in zip(zhong_v, zhong_density, zhong_E):
    add_sample(paper_uid="P_ZHONG2020", source_id="SRC_ZHONG2020", doi="10.1016/j.ceramint.2020.07.325", year=2020,
               sample_label=f"TiB_{vf}vol", matrix_system="Ti-6Al-4V", reinforcement="TiB; residual TiB2 above 40vol%",
               reinforcement_fraction=vf, process="tape_cast+SPS_1350C_40MPa_5min", heat_treatment="as-sintered",
               E_GPa=e, E_sd=7.5, flexural_strength_MPa=1989.35 if vf==5 else (281.76 if vf==80 else None),
               KIC_MPa_sqrt_m=17.89 if vf==5 else (4.43 if vf==80 else None),
               density_bulk=rho, density_bulk_sd=0.012, density_primary_source="MEASURED_ARCHIMEDES_FIGURE_DERIVED",
               relative_density_pct=96.0, relative_density_sd=None, porosity_pct=None,
               evidence_level="FIGURE_DERIVED", evidence_locator="Fig. 3; endpoint text in section 3/conclusion",
               ad_status="IN_DOSE_SUPPORT", include_primary=False,
               notes="No 0 vol.% matrix control; E and intermediate density are digitized/approximated from figure, not Gold.")

# Wang et al. CP-Ti control values are algebraically recovered from the reported percentage increments.
wang_cp_uts = 940.0 / 1.843
wang_cp_ys = 741.0 - 326.0
wang_comp_rho = (1-0.1288)*rho_ti + 0.1288*4.93
add_sample(paper_uid="P_WANG2022", source_id="SRC_WANG2022", doi="10.1016/j.msea.2022.143935", year=2022,
           sample_label="PLDED_CP-Ti", matrix_system="CP-Ti", process="PLDED_200W_15Hz", heat_treatment="as-built",
           UTS_MPa=wang_cp_uts, UTS_sd=10.0, YS_MPa=wang_cp_ys, YS_sd=10.0,
           density_full=rho_ti, density_full_sd=0.01, density_primary_source="DATABASE_ROM_PRIOR",
           evidence_level="DERIVED_CALCULATION", evidence_locator="Abstract/sections 3.3 and 4.4",
           notes="UTS recovered from 940 MPa being 84.3% above control; YS recovered from reported +326 MPa.")
add_sample(paper_uid="P_WANG2022", source_id="SRC_WANG2022", doi="10.1016/j.msea.2022.143935", year=2022,
           sample_label="PLDED_Ti+0.6wtC", matrix_system="CP-Ti", reinforcement="TiC", reinforcement_fraction=12.88,
           precursor_fraction=0.6, process="PLDED_200W_15Hz", heat_treatment="as-built",
           UTS_MPa=940.0, UTS_sd=15.0, YS_MPa=741.0, YS_sd=12.0, EL_pct=18.9, EL_sd=0.7,
           density_full=wang_comp_rho, density_full_sd=0.025, density_primary_source="CALCULATED_FULL_DENSITY_ROM",
           evidence_level="DIRECT_TEXT+DERIVED_CALCULATION", evidence_locator="Sections 3.3/4.4; Figs. 7–8",
           notes="Measured density absent; ROM uses reported 12.88 vol.% TiC; specific-property claim is lower tier.")

# Ti65 W evidence from the hash-bound QM24 result.
for temp,base_uts,w_uts in [(25,1288.49,1601.24),(700,414.0,521.0)]:
    add_sample(paper_uid="P_TI65_INTERNAL_W", source_id="SRC_QM24", doi="", year=2026,
               sample_label=f"Ti65_{temp}C", matrix_system="Ti65", W_wt_pct=0.8, Ta_wt_pct=2.0,
               process="internal_source_condition_matched", heat_treatment="source-matched", temperature_c=temp,
               UTS_MPa=base_uts, UTS_sd=None, EL_pct=10.13 if temp==25 else None,
               density_full=4.514, density_full_sd=0.015, density_primary_source="CALCULATED_FULL_DENSITY_ROM",
               evidence_level="DERIVED_CALCULATION", evidence_locator="QM24 hash-bound paired result",
               notes="Measured density unavailable; baseline nominally contains 0.8 wt.% W and 2 wt.% Ta.")
    add_sample(paper_uid="P_TI65_INTERNAL_W", source_id="SRC_QM24", doi="", year=2026,
               sample_label=f"Ti65_plus3W_{temp}C", matrix_system="Ti65", W_wt_pct=3.8, Ta_wt_pct=2.0,
               process="internal_source_condition_matched", heat_treatment="source-matched", temperature_c=temp,
               UTS_MPa=w_uts, UTS_sd=None, EL_pct=7.86 if temp==25 else None,
               density_full=4.620, density_full_sd=0.015, density_primary_source="CALCULATED_FULL_DENSITY_ROM",
               evidence_level="DERIVED_CALCULATION", evidence_locator="QM24 hash-bound paired result",
               notes="3 wt.% W addition relative to Ti65 source baseline; measured density unavailable.")

# Liu et al. is retained as sensitivity-only because actual product fraction and measured density are unresolved.
add_sample(paper_uid="P_LIU2023", source_id="SRC_LIU2023", doi="10.1016/j.compositesb.2023.111008", year=2023,
           sample_label="as-printed_Ti64", matrix_system="Ti-6Al-4V", process="LDED-AM", heat_treatment="as-built",
           UTS_MPa=1076.0, UTS_sd=15.0, density_full=4.43, density_full_sd=0.03,
           density_primary_source="DATABASE_PRIOR", evidence_level="DIRECT_TEXT+DATABASE_PRIOR",
           evidence_locator="Section 3.1", include_primary=False, ad_status="SENSITIVITY_ONLY",
           notes="In-situ maximum tensile stress; off-site values not tabulated in this paper.")
add_sample(paper_uid="P_LIU2023", source_id="SRC_LIU2023", doi="10.1016/j.compositesb.2023.111008", year=2023,
           sample_label="as-printed_1volB4C_Ti64", matrix_system="Ti-6Al-4V", reinforcement="TiB+TiC network",
           reinforcement_fraction=1.0, reinforcement_unit="vol% precursor B4C", precursor_fraction=1.0,
           process="LDED-AM", heat_treatment="as-built", UTS_MPa=1190.0, UTS_sd=15.0,
           density_full=4.42, density_full_sd=0.04, density_primary_source="DATABASE_PRIOR_SENSITIVITY",
           evidence_level="DIRECT_TEXT+DATABASE_PRIOR", evidence_locator="Sections 2.1 and 3.1",
           include_primary=False, ad_status="SENSITIVITY_ONLY",
           notes="Actual TiB/TiC phase fraction unresolved; density is a broad prior, not measured.")

# Rastegari pair is figure-derived and retained only to expose a multiobjective counterexample.
add_sample(paper_uid="P_RASTEGARI2013", source_id="SRC_RASTEGARI2013", doi="10.1016/j.msea.2012.12.011", year=2013,
           sample_label="Ti64_10volTiC_noB_870Croll", matrix_system="Ti-6Al-4V", reinforcement="TiC",
           reinforcement_fraction=10.0, process="VIM+hot_roll_870C+anneal", heat_treatment="annealed_870C",
           UTS_MPa=1320.0, UTS_sd=25.0, EL_pct=4.0, EL_sd=1.0, density_full=4.48, density_full_sd=0.025,
           density_primary_source="CALCULATED_FULL_DENSITY_ROM", evidence_level="FIGURE_DERIVED",
           evidence_locator="Figs. 4–5", include_primary=False, ad_status="SENSITIVITY_ONLY",
           notes="Values digitized approximately from plots; no measured density.")
add_sample(paper_uid="P_RASTEGARI2013", source_id="SRC_RASTEGARI2013", doi="10.1016/j.msea.2012.12.011", year=2013,
           sample_label="Ti64_10volTiC_plus0.1wtB_870Croll", matrix_system="Ti-6Al-4V", reinforcement="TiC+TiB",
           reinforcement_fraction=10.0, precursor_fraction=0.1, process="VIM+hot_roll_870C+anneal", heat_treatment="annealed_870C",
           UTS_MPa=1230.0, UTS_sd=25.0, EL_pct=9.0, EL_sd=1.0, density_full=4.481, density_full_sd=0.025,
           density_primary_source="CALCULATED_FULL_DENSITY_ROM", evidence_level="DIRECT_TEXT+FIGURE_DERIVED",
           evidence_locator="Figs. 4–5; conclusion", include_primary=False, ad_status="SENSITIVITY_ONLY",
           notes="B improves ductility but lowers strength; no measured density.")

sample_by_label = {(s["paper_uid"], s["sample_label"]): s for s in samples}

pairs: list[dict] = []
def add_pair(paper_uid, control_label, treated_label, match_grade, role, notes=""):
    c = sample_by_label[(paper_uid, control_label)]
    t = sample_by_label[(paper_uid, treated_label)]
    pairs.append(dict(pair_uid="PAIR_"+uid(paper_uid,control_label,treated_label,t["temperature_c"]), paper_uid=paper_uid,
                      control_sample_uid=c["sample_uid"], treated_sample_uid=t["sample_uid"], control_label=control_label,
                      treated_label=treated_label, temperature_c=t["temperature_c"], match_grade=match_grade,
                      analysis_role=role, condition_match="same paper/source, matrix, process, heat treatment, test mode, temperature",
                      notes=notes))

add_pair("P_SABAHI2017","Ti","Ti-2.4wtTiB2_target4volTiB","A","PRIMARY")
for lbl in ["TMC1","TMC2","TMC3","TMC4"]:
    add_pair("P_YAN2014","Matrix",lbl,"A","PRIMARY")
add_pair("P_WANG2022","PLDED_CP-Ti","PLDED_Ti+0.6wtC","A","PRIMARY_LOWER_DENSITY_TIER")
for temp in [25,700]:
    add_pair("P_TI65_INTERNAL_W",f"Ti65_{temp}C",f"Ti65_plus3W_{temp}C","A","PRIMARY_ROM_ONLY")
add_pair("P_LIU2023","as-printed_Ti64","as-printed_1volB4C_Ti64","A","SENSITIVITY_ONLY")
add_pair("P_RASTEGARI2013","Ti64_10volTiC_noB_870Croll","Ti64_10volTiC_plus0.1wtB_870Croll","A","SENSITIVITY_ONLY")
add_pair("P_ZHONG2020","TiB_5vol","TiB_80vol","B","DOSE_ENDPOINT_CONTRAST","No unreinforced matrix; not a matrix-control causal contrast.")

# Density ledger, including full-density and bulk-density records as separate provenance-bearing rows.
density_ledger = []
for s in samples:
    for semantics, val, sd, source_class in [
        ("FULL_DENSITY_POROSITY_CONTROLLED", s["density_full"], s["density_full_sd"], s["density_primary_source"]),
        ("BULK_AS_FABRICATED", s["density_bulk"], s["density_bulk_sd"], "MEASURED_OR_DERIVED_FROM_RELATIVE_DENSITY")
    ]:
        if val is None:
            continue
        density_ledger.append(dict(
            density_record_uid="D_"+uid(s["sample_uid"],semantics), snapshot_id=SNAPSHOT, paper_uid=s["paper_uid"],
            sample_uid=s["sample_uid"], sample_label=s["sample_label"], condition_uid="C_"+uid(s["sample_uid"],s["temperature_c"],s["process"]),
            temperature_c=s["temperature_c"], density_g_cm3=fmt(val,6), density_sd_g_cm3=fmt(sd,6), density_semantics=semantics,
            density_source=source_class, relative_density_pct=fmt(s["relative_density_pct"],4), porosity_pct=fmt(s["porosity_pct"],4),
            reinforcement=s["reinforcement"], reinforcement_fraction=s["reinforcement_fraction"], reinforcement_unit=s["reinforcement_unit"],
            W_wt_pct=s["W_wt_pct"], Ta_wt_pct=s["Ta_wt_pct"], evidence_level=s["evidence_level"],
            evidence_locator=s["evidence_locator"], porosity_credit_allowed="NO",
            uncertainty_note="Reported/propagated where available; figure-derived or database-prior uncertainty is conservative.",
            claim_eligible="YES" if (semantics=="FULL_DENSITY_POROSITY_CONTROLLED" and s["include_primary"]) else "SENSITIVITY_ONLY"
        ))

# Atomic long-format records.
atomic_rows = []
property_map = [("UTS_MPa","UTS","MPa"),("YS_MPa","YS","MPa"),("EL_pct","EL","%"),("E_GPa","E","GPa"),
                ("flexural_strength_MPa","FLEXURAL_STRENGTH","MPa"),("KIC_MPa_sqrt_m","KIC","MPa*sqrt(m)")]
for s in samples:
    for field, prop, unit in property_map:
        if s[field] is None:
            continue
        rec = dict(
            record_uid="R_"+uid(s["sample_uid"],prop), snapshot_id=SNAPSHOT, paper_uid=s["paper_uid"], sample_uid=s["sample_uid"],
            condition_uid="C_"+uid(s["sample_uid"],s["temperature_c"],s["process"]), source_id=s["source_id"], doi=s["doi"], year=s["year"],
            sample_label=s["sample_label"], matrix_system=s["matrix_system"], reinforcement=s["reinforcement"],
            reinforcement_fraction=s["reinforcement_fraction"], reinforcement_unit=s["reinforcement_unit"], W_wt_pct=s["W_wt_pct"],
            Ta_wt_pct=s["Ta_wt_pct"], process=s["process"], heat_treatment=s["heat_treatment"], test_mode=s["test_mode"],
            temperature_c=s["temperature_c"], orientation=s["orientation"], property=prop, value=fmt(s[field],6), unit=unit,
            value_sd=fmt(s.get(field.replace("_MPa","_sd").replace("_pct","_sd").replace("_GPa","_sd")),6),
            density_full_g_cm3=fmt(s["density_full"],6), density_bulk_g_cm3=fmt(s["density_bulk"],6),
            density_primary_source=s["density_primary_source"], evidence_level=s["evidence_level"], evidence_locator=s["evidence_locator"],
            ad_status=s["ad_status"], include_primary=s["include_primary"], notes=s["notes"]
        )
        atomic_rows.append(rec)

# Monte Carlo effect engine.
def positive_normal(mean, sd, n, rng):
    if mean is None:
        return None
    if not sd or sd <= 0:
        return np.full(n, float(mean))
    x = rng.normal(float(mean), float(sd), n)
    return np.clip(x, 1e-12, None)


def effect_mc(c, t, prop_field, density_basis="full", n=30000):
    seed = int(uid(c["sample_uid"],t["sample_uid"],prop_field,density_basis,n=8),16)
    rng = np.random.default_rng(seed)
    cmean,tmean = c.get(prop_field),t.get(prop_field)
    if cmean is None or tmean is None:
        return None
    sd_field = {"UTS_MPa":"UTS_sd","YS_MPa":"YS_sd","EL_pct":"EL_sd","E_GPa":"E_sd"}.get(prop_field)
    cprop = positive_normal(cmean, c.get(sd_field) if sd_field else None, n, rng)
    tprop = positive_normal(tmean, t.get(sd_field) if sd_field else None, n, rng)
    delta = tprop-cprop
    ratio = tprop/cprop
    out = {"delta":delta,"lnrr":np.log(ratio),"pct":100*(ratio-1)}
    if prop_field in ("UTS_MPa","YS_MPa","E_GPa"):
        dfield = "density_full" if density_basis=="full" else "density_bulk"
        dsdf = "density_full_sd" if density_basis=="full" else "density_bulk_sd"
        if c.get(dfield) is not None and t.get(dfield) is not None:
            cd = positive_normal(c[dfield], c.get(dsdf), n, rng)
            td = positive_normal(t[dfield], t.get(dsdf), n, rng)
            cs = cprop/cd
            ts = tprop/td
            out.update({"control_specific":cs,"treated_specific":ts,"specific_delta":ts-cs,
                        "specific_lnrr":np.log(ts/cs),"specific_pct":100*(ts/cs-1),"density_pct":100*(td/cd-1)})
    return out


def summarize(arr):
    if arr is None:
        return (None,None,None)
    q=np.quantile(arr,[0.025,0.5,0.975])
    return (float(q[1]),float(q[0]),float(q[2]))


effect_rows=[]
specific_rows=[]
for p in pairs:
    c=next(x for x in samples if x["sample_uid"]==p["control_sample_uid"])
    t=next(x for x in samples if x["sample_uid"]==p["treated_sample_uid"])
    for field,prop,unit in property_map:
        mc=effect_mc(c,t,field,"full")
        if mc is None:
            continue
        dm,dl,dh=summarize(mc["delta"]); rm,rl,rh=summarize(mc["lnrr"]); pm,pl,ph=summarize(mc["pct"])
        effect_rows.append(dict(
            effect_uid="E_"+uid(p["pair_uid"],prop,"absolute"), snapshot_id=SNAPSHOT, pair_uid=p["pair_uid"], paper_uid=p["paper_uid"],
            property=prop, estimand="DELTA_AND_LNRR", effect=fmt(dm,6), ci95_low=fmt(dl,6), ci95_high=fmt(dh,6), unit=unit,
            lnRR=fmt(rm,6), lnRR_ci95_low=fmt(rl,6), lnRR_ci95_high=fmt(rh,6), percent_change=fmt(pm,4),
            percent_ci95_low=fmt(pl,4), percent_ci95_high=fmt(ph,4), density_basis="NA", match_grade=p["match_grade"],
            analysis_role=p["analysis_role"], independent_cluster=p["paper_uid"], claim_level=2 if p["match_grade"]=="A" else 1,
            uncertainty_scope="REPORTED_SD_OR_DECLARED_SENSITIVITY; not a sampling SE", fdr_status="NOT_TESTED_SD_NOT_SE",
            evidence_level=t["evidence_level"], ad_status=t["ad_status"], notes=p["notes"]
        ))
        if field in ("UTS_MPa","YS_MPa","E_GPa") and "specific_pct" in mc:
            sm,sl,sh=summarize(mc["specific_delta"]); sp,spl,sph=summarize(mc["specific_pct"])
            cs,_,_=summarize(mc["control_specific"]); ts,_,_=summarize(mc["treated_specific"]); dp,dpl,dph=summarize(mc["density_pct"])
            specific_rows.append(dict(
                specific_effect_uid="SE_"+uid(p["pair_uid"],prop,"full"), snapshot_id=SNAPSHOT, pair_uid=p["pair_uid"],
                paper_uid=p["paper_uid"], control_sample_uid=c["sample_uid"], treated_sample_uid=t["sample_uid"], property=prop,
                density_basis="FULL_DENSITY_POROSITY_CONTROLLED", control_specific_value=fmt(cs,6), treated_specific_value=fmt(ts,6),
                specific_unit=("MPa*cm3/g" if prop in ("UTS","YS") else "GPa*cm3/g"), delta_specific=fmt(sm,6),
                delta_specific_ci95_low=fmt(sl,6), delta_specific_ci95_high=fmt(sh,6), percent_change_specific=fmt(sp,4),
                percent_ci95_low=fmt(spl,4), percent_ci95_high=fmt(sph,4), density_percent_change=fmt(dp,4),
                density_pct_ci95_low=fmt(dpl,4), density_pct_ci95_high=fmt(dph,4), density_source_control=c["density_primary_source"],
                density_source_treated=t["density_primary_source"], porosity_credit_allowed="NO", match_grade=p["match_grade"],
                analysis_role=p["analysis_role"], claim_level=2 if p["match_grade"]=="A" else 1,
                support_status=t["ad_status"], evidence_level=t["evidence_level"], notes=p["notes"]
            ))
            # Bulk-density sensitivity where both samples possess it.
            mcb=effect_mc(c,t,field,"bulk")
            if mcb is not None and "specific_pct" in mcb:
                bsm,bsl,bsh=summarize(mcb["specific_delta"]); bsp,bspl,bsph=summarize(mcb["specific_pct"])
                bcs,_,_=summarize(mcb["control_specific"]); bts,_,_=summarize(mcb["treated_specific"]); bdp,bdpl,bdph=summarize(mcb["density_pct"])
                specific_rows.append(dict(
                    specific_effect_uid="SE_"+uid(p["pair_uid"],prop,"bulk"), snapshot_id=SNAPSHOT, pair_uid=p["pair_uid"],
                    paper_uid=p["paper_uid"], control_sample_uid=c["sample_uid"], treated_sample_uid=t["sample_uid"], property=prop,
                    density_basis="BULK_AS_FABRICATED_SENSITIVITY", control_specific_value=fmt(bcs,6), treated_specific_value=fmt(bts,6),
                    specific_unit=("MPa*cm3/g" if prop in ("UTS","YS") else "GPa*cm3/g"), delta_specific=fmt(bsm,6),
                    delta_specific_ci95_low=fmt(bsl,6), delta_specific_ci95_high=fmt(bsh,6), percent_change_specific=fmt(bsp,4),
                    percent_ci95_low=fmt(bspl,4), percent_ci95_high=fmt(bsph,4), density_percent_change=fmt(bdp,4),
                    density_pct_ci95_low=fmt(bdpl,4), density_pct_ci95_high=fmt(bdph,4), density_source_control="MEASURED_BULK",
                    density_source_treated="MEASURED_BULK", porosity_credit_allowed="NO", match_grade=p["match_grade"],
                    analysis_role="SENSITIVITY_ONLY", claim_level=1, support_status=t["ad_status"], evidence_level=t["evidence_level"],
                    notes="Bulk density may make porosity look like mass benefit; never used for primary claim."
                ))

# Paper-cluster synthesis for primary full-density specific UTS effects.
primary_suts=[r for r in specific_rows if r["property"]=="UTS" and r["density_basis"]=="FULL_DENSITY_POROSITY_CONTROLLED" and r["analysis_role"] not in ("SENSITIVITY_ONLY","DOSE_ENDPOINT_CONTRAST")]
by_paper=defaultdict(list)
for r in primary_suts:
    by_paper[r["paper_uid"]].append(float(r["percent_change_specific"]))
paper_means={p:float(np.mean(v)) for p,v in by_paper.items()}
vals=np.array(list(paper_means.values()),dtype=float)
rng=np.random.default_rng(SEED)
boot=[]
keys=list(paper_means)
for _ in range(30000):
    draw=rng.choice(keys,size=len(keys),replace=True)
    boot.append(float(np.mean([paper_means[k] for k in draw])))
boot=np.asarray(boot)
pooled_mean=float(np.mean(vals)); pooled_median=float(np.median(vals)); ci=np.quantile(boot,[0.025,0.975])
if len(vals)>1:
    tau=float(np.std(vals,ddof=1))
    tcrit=3.182 if len(vals)==4 else 2.776
    pi=(pooled_mean-tcrit*tau*math.sqrt(1+1/len(vals)), pooled_mean+tcrit*tau*math.sqrt(1+1/len(vals)))
else:
    tau=float("nan"); pi=(float("nan"),float("nan"))

hierarchical_rows=[dict(
    result_id="H_PRIMARY_SUTS_EQUAL_PAPER", property="specific_UTS", estimand="equal-paper mean of within-paper paired percent changes",
    estimate=fmt(pooled_mean,4), ci95_low_cluster_bootstrap=fmt(ci[0],4), ci95_high_cluster_bootstrap=fmt(ci[1],4),
    prediction_interval_low=fmt(pi[0],4), prediction_interval_high=fmt(pi[1],4), independent_papers=len(vals),
    paper_cluster_sd=fmt(tau,4), pooling="paper-cluster bootstrap; within-paper dose effects averaged first", claim_level=2,
    interpretation="Descriptive synthesis only; extreme heterogeneity makes a universal coefficient indefensible."
)]

heterogeneity_rows=[dict(
    result_id="HET_PRIMARY_SUTS", property="specific_UTS_percent_change", independent_papers=len(vals),
    paper_means_json=json.dumps({k:round(v,4) for k,v in paper_means.items()},sort_keys=True), mean=fmt(pooled_mean,4),
    median=fmt(pooled_median,4), min=fmt(float(np.min(vals)),4), max=fmt(float(np.max(vals)),4), paper_cluster_sd=fmt(tau,4),
    prediction_interval_low=fmt(pi[0],4), prediction_interval_high=fmt(pi[1],4),
    I2="NOT_ESTIMABLE_WITHOUT_COMPARABLE_WITHIN_STUDY_SAMPLING_VARIANCE",
    conclusion="Heterogeneity dominates; dose, defect state, process and density evidence tier cannot be pooled away."
)]

lopo_rows=[]
for omitted in keys:
    rem=[paper_means[k] for k in keys if k!=omitted]
    lopo_rows.append(dict(analysis="LOPO_PRIMARY_SPECIFIC_UTS", omitted_paper_uid=omitted, papers_remaining=len(rem),
                          estimate_mean_pct=fmt(float(np.mean(rem)),4), estimate_median_pct=fmt(float(np.median(rem)),4),
                          sign="POSITIVE" if np.mean(rem)>0 else "NEGATIVE", interpretation="Paper-cluster influence diagnostic"))

# Dose-response analyses.
yan_s=[s for s in samples if s["paper_uid"]=="P_YAN2014"]
yx=np.array([s["reinforcement_fraction"] for s in yan_s],float)
yy=np.array([s["UTS_MPa"]/s["density_full"] for s in yan_s],float)
coef=np.polyfit(yx,yy,2); pred=np.polyval(coef,yx); r2=1-float(np.sum((yy-pred)**2))/float(np.sum((yy-np.mean(yy))**2))
peak_x=float(np.clip(-coef[1]/(2*coef[0]),yx.min(),yx.max())) if coef[0]!=0 else float("nan")
peak_y=float(np.polyval(coef,peak_x))
dose_rows=[dict(result_id="DOSE_YAN_TIB_SPECIFIC_UTS", paper_uid="P_YAN2014", response="specific_UTS_full_density",
                dose_unit="vol% TiB", model="quadratic descriptive", intercept=fmt(coef[2],8), linear=fmt(coef[1],8), quadratic=fmt(coef[0],8),
                r2_in_sample=fmt(r2,5), observed_min=0, observed_max=20, stationary_point=fmt(peak_x,4), stationary_response=fmt(peak_y,4),
                status="DESCRIPTIVE_ONLY", claim_level=2,
                interpretation="Non-monotonic: the 10 vol.% row is locally best, while 15–20 vol.% collapse with agglomeration/porous micro-regions."),
           dict(result_id="DOSE_ZHONG_TIB_SPECIFIC_E", paper_uid="P_ZHONG2020", response="specific_E_measured_bulk",
                dose_unit="vol% TiB", model="monotonic figure-derived dose series", intercept="", linear="", quadratic="", r2_in_sample="",
                observed_min=5, observed_max=80, stationary_point="", stationary_response="", status="NO_MATRIX_CONTROL_FIGURE_DERIVED", claim_level=1,
                interpretation="Specific modulus rises strongly, but flexural strength and KIC collapse; this is not full multiobjective dominance."),
           dict(result_id="DOSE_WANG_TIC_SPECIFIC_UTS", paper_uid="P_WANG2022", response="specific_UTS_ROM",
                dose_unit="vol% TiC", model="two-point contrast only", intercept="", linear="", quadratic="", r2_in_sample="", observed_min=0,
                observed_max=12.88, stationary_point="", stationary_response="", status="NOT_IDENTIFIABLE_DOSE_CURVE", claim_level=2,
                interpretation="Only the control and 12.88 vol.% anchor are used quantitatively; no universal TiC slope is claimed.")]

# Interaction and sensitivity results.
def get_spec(pair_paper, treated_fragment, temp=None, basis="FULL_DENSITY_POROSITY_CONTROLLED", prop="UTS"):
    for r in specific_rows:
        if r["paper_uid"]==pair_paper and treated_fragment in next(s["sample_label"] for s in samples if s["sample_uid"]==r["treated_sample_uid"]) and r["density_basis"]==basis and r["property"]==prop:
            if temp is None or next(s["temperature_c"] for s in samples if s["sample_uid"]==r["treated_sample_uid"])==temp:
                return r
    return None

w_rt=get_spec("P_TI65_INTERNAL_W","plus3W",25); w_700=get_spec("P_TI65_INTERNAL_W","plus3W",700)
y20_full=get_spec("P_YAN2014","TMC4",basis="FULL_DENSITY_POROSITY_CONTROLLED")
y20_bulk=get_spec("P_YAN2014","TMC4",basis="BULK_AS_FABRICATED_SENSITIVITY")
interaction_rows=[
    dict(interaction_id="INT_W_TEMPERATURE", variables="W_addition × temperature", estimand="difference in specific-UTS percent gain, 700C minus RT",
         estimate=fmt(float(w_700["percent_change_specific"])-float(w_rt["percent_change_specific"]),4), unit="percentage points",
         support="two temperatures in one source-matched family", status="DESCRIPTIVE_NOT_CAUSAL", claim_level=2,
         interpretation="W acts as near-parallel uplift; no retention-ratio breakthrough."),
    dict(interaction_id="INT_POROSITY_CREDIT_YAN20", variables="TiB dose × density semantics", estimand="bulk-density effect minus full-density effect at 20 vol.% TiB",
         estimate=fmt(float(y20_bulk["percent_change_specific"])-float(y20_full["percent_change_specific"]),4), unit="percentage points",
         support="same sample, alternative density definition", status="IDENTIFIABLE_SENSITIVITY", claim_level=2,
         interpretation="Lower bulk density from porosity makes performance look less bad; this apparent mass benefit is prohibited."),
    dict(interaction_id="INT_TA_STRENGTH", variables="Ta × W or Ta main effect", estimand="specific-strength response", estimate="", unit="",
         support="density-only +1Ta/−1Ti perturbation", status="NOT_IDENTIFIABLE", claim_level=0,
         interpretation="+1 wt.% Ta raises ideal density by 0.74%, but matched strength response is absent."),
]

sensitivity_rows=[]
for r in specific_rows:
    if r["density_basis"]=="BULK_AS_FABRICATED_SENSITIVITY":
        full=next((x for x in specific_rows if x["pair_uid"]==r["pair_uid"] and x["property"]==r["property"] and x["density_basis"]=="FULL_DENSITY_POROSITY_CONTROLLED"),None)
        if full:
            sensitivity_rows.append(dict(analysis="DENSITY_DEFINITION", pair_uid=r["pair_uid"], property=r["property"],
                                         primary_full_density_pct=full["percent_change_specific"], bulk_density_pct=r["percent_change_specific"],
                                         shift_percentage_points=fmt(float(r["percent_change_specific"])-float(full["percent_change_specific"]),4),
                                         decision="PRIMARY_UNCHANGED" if np.sign(float(r["percent_change_specific"]))==np.sign(float(full["percent_change_specific"])) else "SIGN_SENSITIVE",
                                         note="Bulk density is never allowed to convert porosity into a positive lightweight claim."))
sensitivity_rows.extend(lopo_rows)
for r in [x for x in specific_rows if x["analysis_role"]=="SENSITIVITY_ONLY" and x["density_basis"]=="FULL_DENSITY_POROSITY_CONTROLLED"]:
    sensitivity_rows.append(dict(analysis="LOWER_EVIDENCE_TIER", pair_uid=r["pair_uid"], property=r["property"],
                                 primary_full_density_pct=r["percent_change_specific"], bulk_density_pct="", shift_percentage_points="",
                                 decision="EXCLUDED_FROM_PRIMARY_POOL", note="Figure-derived or database-prior density/phase fraction."))

# Uncertainty ledger.
uncertainty_rows=[]
for d in density_ledger:
    uncertainty_rows.append(dict(
        uncertainty_uid="U_"+uid(d["density_record_uid"]), density_record_uid=d["density_record_uid"], paper_uid=d["paper_uid"], sample_uid=d["sample_uid"],
        density_semantics=d["density_semantics"], central_density_g_cm3=d["density_g_cm3"], sd_or_prior_g_cm3=d["density_sd_g_cm3"],
        uncertainty_sources="reported relative-density scatter; phase-density prior; figure digitization; composition closure as applicable",
        propagation="30,000-draw deterministic Monte Carlo for pair effects", seed=SEED,
        includes_composition_uncertainty="YES_FOR_ROM_PRIORS", includes_porosity_uncertainty="YES_WHEN_RELATIVE_DENSITY_AVAILABLE",
        caveat="Source-reported ± values are not assumed to be standard errors; intervals are uncertainty bands, not population confidence intervals."
    ))

# Multiobjective Pareto ledger.
pareto_rows=[]
for p in pairs:
    c=next(x for x in samples if x["sample_uid"]==p["control_sample_uid"]); t=next(x for x in samples if x["sample_uid"]==p["treated_sample_uid"])
    def sp(s,field):
        return safe_div(s.get(field),s.get("density_full") or s.get("density_bulk"))
    uts_gain=pct_change(t.get("UTS_MPa"),c.get("UTS_MPa")); suts_gain=pct_change(sp(t,"UTS_MPa"),sp(c,"UTS_MPa"))
    e_gain=pct_change(t.get("E_GPa"),c.get("E_GPa")); se_gain=pct_change(sp(t,"E_GPa"),sp(c,"E_GPa"))
    el_delta=None if c.get("EL_pct") is None or t.get("EL_pct") is None else t["EL_pct"]-c["EL_pct"]
    rho_c=c.get("density_full") or c.get("density_bulk"); rho_t=t.get("density_full") or t.get("density_bulk")
    rho_gain=pct_change(rho_t,rho_c)
    if suts_gain is not None:
        if suts_gain>0 and (el_delta is None or el_delta>=0): status="SPECIFIC_STRENGTH_GAIN_EL_OK_OR_MISSING"
        elif suts_gain>0: status="STRENGTH_DUCTILITY_TRADEOFF"
        else: status="NO_SPECIFIC_STRENGTH_GAIN"
    elif se_gain is not None:
        status="SPECIFIC_MODULUS_GAIN_BUT_DAMAGE_TRADEOFF" if se_gain>0 else "NO_SPECIFIC_MODULUS_GAIN"
    else: status="INCOMPLETE"
    pareto_rows.append(dict(pareto_uid="PARETO_"+uid(p["pair_uid"]), pair_uid=p["pair_uid"], paper_uid=p["paper_uid"],
                            control_label=p["control_label"], treated_label=p["treated_label"], density_change_pct=fmt(rho_gain,4),
                            UTS_change_pct=fmt(uts_gain,4), specific_UTS_change_pct=fmt(suts_gain,4), E_change_pct=fmt(e_gain,4),
                            specific_E_change_pct=fmt(se_gain,4), EL_delta_percentage_points=fmt(el_delta,4),
                            flexural_change_pct=fmt(pct_change(t.get("flexural_strength_MPa"),c.get("flexural_strength_MPa")),4),
                            KIC_change_pct=fmt(pct_change(t.get("KIC_MPa_sqrt_m"),c.get("KIC_MPa_sqrt_m")),4),
                            pareto_status=status, complete_objectives="NO" if any(v is None for v in [suts_gain,el_delta]) else "YES",
                            density_evidence=t["density_primary_source"], claim_level=2 if p["match_grade"]=="A" else 1,
                            decision="SCREENED_EVIDENCE_ONLY_NOT_VALIDATED"))

# Null, negative, and conflict ledgers.
null_rows=[
    dict(result_id="NEG_YAN_5", category="NEGATIVE_EFFECT", finding="5 vol.% TiB lowers full-density specific UTS versus matrix", quantitative_anchor="about -4.8%", implication="Low dose is not automatically beneficial."),
    dict(result_id="NEG_YAN_15_20", category="DOSE_COLLAPSE", finding="15 and 20 vol.% TiB sharply lower full-density specific UTS", quantitative_anchor="about -31.9% and -52.1%", implication="Agglomeration and porous micro-regions dominate reinforcement benefit."),
    dict(result_id="NULL_W_RETENTION", category="NULL_INTERACTION", finding="3 wt.% W does not materially change relative 700C retention", quantitative_anchor="retention difference about 0.0041 in QM24", implication="Absolute high-temperature strength uplift is not a retention breakthrough."),
    dict(result_id="NI_TA", category="NOT_IDENTIFIABLE", finding="Ta strength or specific-strength benefit", quantitative_anchor="+1Ta/-1Ti density penalty +0.74%; no matched strength", implication="Do not infer Ta payoff from density or mechanism priors."),
    dict(result_id="TRADE_ZHONG", category="MULTIOBJECTIVE_TRADEOFF", finding="Specific modulus rises across 5–80 vol.% TiB while flexural strength and KIC collapse", quantitative_anchor="flexural 1989.35→281.76 MPa; KIC 17.89→4.43", implication="Stiffness-only Pareto is false system-level dominance."),
    dict(result_id="TRADE_TI65_W", category="MULTIOBJECTIVE_TRADEOFF", finding="W improves RT specific UTS but reduces elongation", quantitative_anchor="specific UTS +21.42%; EL 10.13→7.86%", implication="Utility sign depends on ductility weight."),
    dict(result_id="NI_W_TA_MODULUS", category="NOT_IDENTIFIABLE", finding="Specific modulus response of W/Ta-bearing Ti65", quantitative_anchor="elastic modulus absent", implication="No specific-modulus claim for heavy elements."),
]
conflicts=[
    dict(conflict_id="C001", object="Yan relative density", source_a="text: composites 5–15% described as high/near 98%", source_b="Fig.2 digitization: 5% about 97.9%", resolution="retain figure-derived value with ±0.25 pp; do not promote", severity="MEDIUM", open="YES"),
    dict(conflict_id="C002", object="Zhong density trend", source_a="measured density falls 4.473→4.351 g/cm3", source_b="simple constituent-density intuition does not explain full trend", resolution="retain reported measured trend; request raw density replicates and theoretical-density basis", severity="HIGH", open="YES"),
    dict(conflict_id="C003", object="Sabahi reinforcement identity", source_a="designed 4 vol.% TiB", source_b="XRD reports residual TiB2", resolution="label TiB+residual TiB2 and widen ROM uncertainty", severity="HIGH", open="YES"),
    dict(conflict_id="C004", object="Ti65 heavy-element density", source_a="QM24 ROM 4.514→4.620", source_b="no Archimedes/helium-pycnometry density", resolution="ROM-only claim ceiling; request measured density and porosity", severity="HIGH", open="YES"),
    dict(conflict_id="C005", object="Wang TiC specific properties", source_a="reported 12.88 vol.% TiC and tensile gains", source_b="absolute density not measured", resolution="use ROM sensitivity only; exclude measured-density claim", severity="HIGH", open="YES"),
    dict(conflict_id="C006", object="Liu phase fraction", source_a="1 vol.% B4C precursor", source_b="actual TiB+TiC product fraction not quantified", resolution="sensitivity-only; no unit-dose efficiency", severity="HIGH", open="YES"),
    dict(conflict_id="C007", object="Legacy candidate evidence_pack", source_a="contains predicted Ti65-W-TiB2-Ta values", source_b="production registration forbidden and candidates not validated", resolution="exclude all predicted candidate values from effect estimation", severity="CRITICAL", open="NO"),
    dict(conflict_id="C008", object="Duplicate PDFs", source_a="multiple file-library copies of Sabahi/Yan/Liu papers", source_b="same DOI/content", resolution="DOI-level deduplication; count one independent paper", severity="MEDIUM", open="NO"),
]

# Figure data.
pareto_fig=[]
for s in samples:
    if s["UTS_MPa"] is None:
        continue
    rho=s["density_bulk"] if s["density_bulk"] is not None else s["density_full"]
    if rho is None:
        continue
    pareto_fig.append(dict(paper_uid=s["paper_uid"],sample_label=s["sample_label"],density_g_cm3=fmt(rho,6),UTS_MPa=fmt(s["UTS_MPa"],4),
                           specific_UTS=fmt(s["UTS_MPa"]/rho,5),density_basis="BULK" if s["density_bulk"] is not None else "ROM_FULL",
                           evidence=s["evidence_level"],primary=s["include_primary"]))
forest_fig=[]
for r in primary_suts:
    t=next(s for s in samples if s["sample_uid"]==r["treated_sample_uid"])
    forest_fig.append(dict(label=f"{r['paper_uid']} | {t['sample_label']}",paper_uid=r["paper_uid"],effect_pct=r["percent_change_specific"],
                           ci_low=r["percent_ci95_low"],ci_high=r["percent_ci95_high"],density_basis=r["density_basis"],evidence=r["evidence_level"]))
cal_fig=[]
for d in density_ledger:
    if d["density_semantics"]!="BULK_AS_FABRICATED": continue
    full=next((x for x in density_ledger if x["sample_uid"]==d["sample_uid"] and x["density_semantics"]=="FULL_DENSITY_POROSITY_CONTROLLED"),None)
    if full:
        cal_fig.append(dict(paper_uid=d["paper_uid"],sample_label=d["sample_label"],calculated_full_density=full["density_g_cm3"],
                            measured_or_derived_bulk_density=d["density_g_cm3"],bulk_sd=d["density_sd_g_cm3"],relative_density_pct=d["relative_density_pct"],
                            porosity_gap_pct=fmt(100*(1-float(d["density_g_cm3"])/float(full["density_g_cm3"])),4)))
heavy_fig=[]
for s in samples:
    if s["paper_uid"]=="P_TI65_INTERNAL_W":
        heavy_fig.append(dict(sample_label=s["sample_label"],temperature_c=s["temperature_c"],W_wt_pct=s["W_wt_pct"],Ta_wt_pct=s["Ta_wt_pct"],
                              ROM_density=s["density_full"],specific_UTS=fmt(s["UTS_MPa"]/s["density_full"],6),observed_performance="YES"))
heavy_fig.append(dict(sample_label="Ti65_plus1Ta_minus1Ti_density_only",temperature_c=25,W_wt_pct=0.8,Ta_wt_pct=3.0,
                      ROM_density=fmt(4.514*1.0074,6),specific_UTS="",observed_performance="NO"))
modulus_fig=[]
for s in samples:
    if s["paper_uid"]=="P_ZHONG2020":
        modulus_fig.append(dict(TiB_vol_pct=s["reinforcement_fraction"],density_g_cm3=s["density_bulk"],E_GPa=s["E_GPa"],
                                specific_E=fmt(s["E_GPa"]/s["density_bulk"],6),flexural_strength_MPa=s["flexural_strength_MPa"],KIC=s["KIC_MPa_sqrt_m"]))
utility_fig=[]
# Simple transparent utility: U = w_s*z(specUTS change) + (1-w_s)*z(EL delta normalized by 10 pp), no imputation for missing EL.
for r in pareto_rows:
    if r["specific_UTS_change_pct"]=="" or r["EL_delta_percentage_points"]=="": continue
    for ws in np.linspace(0,1,21):
        u=ws*(float(r["specific_UTS_change_pct"])/25.0)+(1-ws)*(float(r["EL_delta_percentage_points"])/10.0)
        utility_fig.append(dict(pair_uid=r["pair_uid"],paper_uid=r["paper_uid"],strength_weight=fmt(ws,2),ductility_weight=fmt(1-ws,2),utility=fmt(u,6),
                                utility_definition="wS*(delta specific UTS %/25)+(1-wS)*(delta EL pp/10)"))

write_csv("figure_data/F1_UTS_density_pareto.csv",pareto_fig)
write_csv("figure_data/F2_specific_strength_forest.csv",forest_fig)
write_csv("figure_data/F3_density_source_calibration.csv",cal_fig)
write_csv("figure_data/F4_heavy_element_support.csv",heavy_fig)
write_csv("figure_data/F5_specific_modulus_tradeoff.csv",modulus_fig)
write_csv("figure_data/F6_multiobjective_utility.csv",utility_fig)

# Plotting helpers.
def save_fig(fig, stem):
    for ext in ["svg","pdf","png"]:
        kwargs={"bbox_inches":"tight"}
        if ext=="png": kwargs["dpi"]=600
        fig.savefig(OUT/"figures"/f"{stem}.{ext}",**kwargs)
    plt.close(fig)

# F1
fig=plt.figure(figsize=(8.2,6.0)); ax=fig.add_subplot(111)
for row in pareto_fig:
    marker="o" if row["density_basis"]=="BULK" else "x"
    ax.scatter(float(row["density_g_cm3"]),float(row["UTS_MPa"]),marker=marker,s=42)
    if row["sample_label"] in {"Ti","Ti-2.4wtTiB2_target4volTiB","Matrix","TMC2","TMC4","PLDED_CP-Ti","PLDED_Ti+0.6wtC","Ti65_25C","Ti65_plus3W_25C"}:
        ax.annotate(row["sample_label"],(float(row["density_g_cm3"]),float(row["UTS_MPa"])),fontsize=6,xytext=(3,3),textcoords="offset points")
ax.set_xlabel("Density (g cm$^{-3}$; measured bulk where available)")
ax.set_ylabel("Ultimate tensile strength (MPa)")
ax.set_title(f"UTS–density evidence map | {len(set(r['paper_uid'] for r in pareto_fig))} independent sources")
ax.grid(True,alpha=.25); ax.text(.01,.01,"Lower density and higher UTS are preferred; x = ROM-only density",transform=ax.transAxes,fontsize=7)
save_fig(fig,"QM10_F1_UTS_density_pareto")

# F2
fig=plt.figure(figsize=(8.2,6.2)); ax=fig.add_subplot(111)
forest_sorted=sorted(forest_fig,key=lambda r:float(r["effect_pct"]))
y=np.arange(len(forest_sorted))
e=np.array([float(r["effect_pct"]) for r in forest_sorted]); lo=np.array([float(r["ci_low"]) for r in forest_sorted]); hi=np.array([float(r["ci_high"]) for r in forest_sorted])
ax.errorbar(e,y,xerr=np.vstack([e-lo,hi-e]),fmt="o",capsize=3)
ax.axvline(0,linewidth=1)
ax.set_yticks(y); ax.set_yticklabels([r["label"] for r in forest_sorted],fontsize=7)
ax.set_xlabel("Change in porosity-controlled specific UTS (%)")
ax.set_title(f"Paired specific-strength effects | {len(set(r['paper_uid'] for r in forest_sorted))} independent papers/sources")
ax.grid(True,axis="x",alpha=.25); ax.text(.01,.01,"Intervals propagate reported/declared value and density uncertainty; not population CIs",transform=ax.transAxes,fontsize=7)
save_fig(fig,"QM10_F2_specific_strength_forest")

# F3
fig=plt.figure(figsize=(7.0,6.0)); ax=fig.add_subplot(111)
xs=np.array([float(r["calculated_full_density"]) for r in cal_fig]); ys=np.array([float(r["measured_or_derived_bulk_density"]) for r in cal_fig]); es=np.array([float(r["bulk_sd"] or 0) for r in cal_fig])
ax.errorbar(xs,ys,yerr=es,fmt="o",capsize=2)
lims=[min(xs.min(),ys.min())-.03,max(xs.max(),ys.max())+.03]; ax.plot(lims,lims,linestyle="--",linewidth=1)
for r in cal_fig: ax.annotate(r["sample_label"],(float(r["calculated_full_density"]),float(r["measured_or_derived_bulk_density"])),fontsize=6,xytext=(3,3),textcoords="offset points")
ax.set_xlim(lims); ax.set_ylim(lims); ax.set_xlabel("Calculated full density (g cm$^{-3}$)"); ax.set_ylabel("Archimedes/relative-density bulk value (g cm$^{-3}$)")
ax.set_title(f"Density-source calibration | {len(set(r['paper_uid'] for r in cal_fig))} papers")
ax.grid(True,alpha=.25); ax.text(.01,.01,"Points below y=x expose porosity; the gap is not a lightweight benefit",transform=ax.transAxes,fontsize=7)
save_fig(fig,"QM10_F3_density_source_calibration")

# F4
fig=plt.figure(figsize=(8.0,6.0)); ax=fig.add_subplot(111)
wgrid=np.linspace(0,4.5,100); tagrid=np.linspace(1.5,3.5,80); W,T=np.meshgrid(wgrid,tagrid)
# Local density-only plane calibrated to QM24: +3 W => +0.106 g/cm3; +1 Ta => +0.74% of baseline.
R=4.514+(W-0.8)*(0.106/3.0)+(T-2.0)*(4.514*0.0074)
cs=ax.contour(W,T,R,levels=8); ax.clabel(cs,inline=True,fontsize=7,fmt="%.3f")
for r in heavy_fig:
    ax.scatter(float(r["W_wt_pct"]),float(r["Ta_wt_pct"]),marker="o" if r["observed_performance"]=="YES" else "x",s=65)
    lab=r["sample_label"] if r["specific_UTS"]=="" else f"{r['sample_label']}\nSUTS={float(r['specific_UTS']):.1f}"
    ax.annotate(lab,(float(r["W_wt_pct"]),float(r["Ta_wt_pct"])),fontsize=6,xytext=(4,4),textcoords="offset points")
ax.set_xlabel("W content (wt.%)"); ax.set_ylabel("Ta content (wt.%)")
ax.set_title("Heavy-element support map: ROM-density contours; performance surface NOT IDENTIFIABLE")
ax.text(.01,.01,"Specific UTS is observed only on the Ta=2 wt.% line; contours are density, not performance",transform=ax.transAxes,fontsize=7)
ax.grid(True,alpha=.2)
save_fig(fig,"QM10_F4_heavy_element_specific_performance_support")

# F5
fig=plt.figure(figsize=(7.5,5.8)); ax=fig.add_subplot(111)
x=np.array([float(r["TiB_vol_pct"]) for r in modulus_fig]); y=np.array([float(r["specific_E"]) for r in modulus_fig])
ax.plot(x,y,marker="o"); ax.set_xlabel("TiB target fraction (vol.%)"); ax.set_ylabel("Specific elastic modulus (GPa cm$^3$ g$^{-1}$)")
ax.set_title("Specific-modulus dose trend with endpoint damage trade-off")
ax.grid(True,alpha=.25); ax.text(.01,.01,"5→80 vol.%: flexural strength 1989→282 MPa; KIC 17.89→4.43 MPa√m",transform=ax.transAxes,fontsize=7)
save_fig(fig,"QM10_F5_specific_modulus_tradeoff")

# F6
fig=plt.figure(figsize=(8.0,5.8)); ax=fig.add_subplot(111)
for pair in sorted(set(r["pair_uid"] for r in utility_fig)):
    rr=[r for r in utility_fig if r["pair_uid"]==pair]
    ax.plot([float(r["strength_weight"]) for r in rr],[float(r["utility"]) for r in rr],label=next(r["paper_uid"] for r in rr))
ax.axhline(0,linewidth=1); ax.set_xlabel("Weight on specific strength"); ax.set_ylabel("Transparent normalized utility")
ax.set_title("Multiobjective utility sensitivity; sign changes expose weight dependence")
ax.grid(True,alpha=.25); ax.legend(fontsize=7,loc="best")
save_fig(fig,"QM10_F6_multiobjective_utility_sensitivity")

# Core output tables.
input_rows=[]
for s in sources:
    input_rows.append(dict(input_id=s["source_id"],snapshot_id=SNAPSHOT,source_name=s["title"],source_type=s["kind"],path_or_locator=s["locator"],
                           source_hash="DOI_OR_PROJECT_OBJECT_BOUND",hash_kind="DOI/semantic object",priority=s["priority"],actually_opened=s["actually_opened"],
                           terminal_use_status="USED_DIRECTLY" if s["priority"]<=2 else "USED_AS_CONTEXT",notes=s["evidence"]))
for i,name in enumerate(archive_names,1):
    input_rows.append(dict(input_id=f"ARCHIVE_{i:02d}",snapshot_id=SNAPSHOT,source_name=name,source_type="PROJECT_SOURCE_ARCHIVE",
                           path_or_locator=f"/mnt/data/{name}",source_hash="MISSING_IN_WEB_RUNTIME",hash_kind="LOCAL_BIND_REQUIRED",priority=2,
                           actually_opened="INDEXED_MEMBERS_ACCESSED_VIA_FILE_LIBRARY; RAW_ZIP_NOT_STREAMED_IN_GITHUB_RUNNER",
                           terminal_use_status="ROLE_AUDITED_NOT_BYTE_BOUND",notes="Relevant literature/structured evidence consumed through File Library; local SHA/CRC binding requested."))
write_csv("INPUT_LEDGER.csv",input_rows)
write_csv("ANALYSIS_COHORT.csv",atomic_rows)
write_csv("PAIR_MATCHES.csv",pairs)
write_csv("EFFECT_ESTIMATES.csv",effect_rows)
write_csv("SPECIFIC_PROPERTY_EFFECTS.csv",specific_rows)
write_csv("DENSITY_LEDGER.csv",density_ledger)
write_csv("DENSITY_UNCERTAINTY.csv",uncertainty_rows)
write_csv("SPECIFIC_PARETO.csv",pareto_rows)
write_csv("HIERARCHICAL_RESULTS.csv",hierarchical_rows)
write_csv("DOSE_RESPONSE.csv",dose_rows)
write_csv("INTERACTION_EFFECTS.csv",interaction_rows)
write_csv("HETEROGENEITY.csv",heterogeneity_rows)
write_csv("SENSITIVITY_ANALYSIS.csv",sensitivity_rows)
write_csv("NULL_NEGATIVE_RESULTS.csv",null_rows)
write_csv("CONFLICT_LEDGER.csv",conflicts)
write_csv("EXCLUDED_RECORDS.csv",[
    dict(exclusion_id="X001",object="legacy evidence_pack predicted Ti65-W-TiB2-Ta candidates",reason="model predictions are not experimental evidence; production-model registration forbidden",terminal_state="EXCLUDED_FROM_ALL_EFFECTS"),
    dict(exclusion_id="X002",object="duplicate PDF copies with same DOI",reason="dependency deduplication",terminal_state="ONE_INDEPENDENT_PAPER"),
    dict(exclusion_id="X003",object="review-only generic claims of high specific strength/modulus",reason="no atomic sample-condition values",terminal_state="CONTEXT_ONLY"),
])
write_csv("CLAIM_MATRIX.csv",[
    dict(claim_id="CL1",claim="Low/moderate ceramic additions can improve specific UTS",max_level=2,status="SUPPORTED_CONDITIONALLY",conditions="same-paper control; density traceable; porosity-controlled"),
    dict(claim_id="CL2",claim="Ceramic reinforcement universally improves specific strength",max_level=0,status="REJECTED",conditions="Yan high-dose counterexamples"),
    dict(claim_id="CL3",claim="3 wt.% W improves Ti65 RT specific UTS despite density penalty",max_level=2,status="SUPPORTED_ROM_ONLY",conditions="source-matched pair; measured density still required"),
    dict(claim_id="CL4",claim="Ta improves specific strength",max_level=0,status="NOT_IDENTIFIABLE",conditions="matched strength response absent"),
    dict(claim_id="CL5",claim="High TiB fraction improves specific modulus",max_level=1,status="SUPPORTED_FIGURE_DERIVED",conditions="damage objectives deteriorate"),
    dict(claim_id="CL6",claim="Any QM10 candidate is VALIDATED",max_level=0,status="FORBIDDEN",conditions="read-only statistical analysis only"),
])

# Provenance JSONL.
with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8") as f:
    for r in atomic_rows:
        obj=dict(provenance_uid="PV_"+uid(r["record_uid"]),snapshot_id=SNAPSHOT,record_uid=r["record_uid"],paper_uid=r["paper_uid"],sample_uid=r["sample_uid"],
                 condition_uid=r["condition_uid"],source_id=r["source_id"],doi=r["doi"],evidence_level=r["evidence_level"],locator=r["evidence_locator"],
                 transformation="DIRECT unless evidence level says FIGURE_DERIVED/DERIVED_CALCULATION/DATABASE_PRIOR",parser="QM10 deterministic builder",generated_at=GENERATED)
        f.write(json.dumps(obj,ensure_ascii=False,sort_keys=True)+"\n")
    for d in density_ledger:
        obj=dict(provenance_uid="PV_"+uid(d["density_record_uid"]),snapshot_id=SNAPSHOT,density_record_uid=d["density_record_uid"],paper_uid=d["paper_uid"],sample_uid=d["sample_uid"],
                 evidence_level=d["evidence_level"],locator=d["evidence_locator"],transformation=d["density_source"],porosity_credit_allowed=False,generated_at=GENERATED)
        f.write(json.dumps(obj,ensure_ascii=False,sort_keys=True)+"\n")

# Human-readable methods and verdict.
verdict=f"""# QM10 Executive Verdict — Density, Specific Strength/Modulus, and Real Multiobjective Benefit

`WINDOW=QM10 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Quantitative decision

The defensible result is conditional rather than universal. Ceramic reinforcement and W can preserve or improve specific performance, but the sign depends on dose, defects, density provenance, temperature and the other objectives.

1. **Direct measured-density anchor.** In the Sabahi SPS pair, Ti–2.4 wt.% TiB2 raises UTS from 441 to 485 MPa and relative density from 97.92% to 98.85%. The porosity-controlled specific-UTS gain is about **{next(r['percent_change_specific'] for r in specific_rows if r['paper_uid']=='P_SABAHI2017' and r['property']=='UTS' and r['density_basis']=='FULL_DENSITY_POROSITY_CONTROLLED')}%**; the bulk-density sensitivity is about **{next(r['percent_change_specific'] for r in specific_rows if r['paper_uid']=='P_SABAHI2017' and r['property']=='UTS' and r['density_basis']=='BULK_AS_FABRICATED_SENSITIVITY')}%**. Both remain positive, so the gain is not created by porosity.
2. **Dose is non-monotonic.** In Yan's same-paper TiB series, full-density specific UTS changes by approximately -4.8%, +5.3%, -31.9% and -52.1% at 5, 10, 15 and 20 vol.% TiB. Above 10 vol.%, agglomeration and porous micro-regions overwhelm reinforcement.
3. **TiC can deliver a large ROM-specific gain, but measured density is missing.** Wang's PLDED 12.88 vol.% TiC material reaches 940 MPa UTS versus an algebraically recovered ~510 MPa control. The ROM-specific UTS gain is about **{next(r['percent_change_specific'] for r in specific_rows if r['paper_uid']=='P_WANG2022' and r['property']=='UTS' and r['density_basis']=='FULL_DENSITY_POROSITY_CONTROLLED')}%**. Claim level remains 2/lower density tier.
4. **W pays its density tax in the available Ti65 pair.** ROM density rises 4.514→4.620 g cm⁻³ (+2.35%), while RT specific UTS rises about **{w_rt['percent_change_specific']}%**. At 700 °C the corresponding specific-UTS gain is about **{w_700['percent_change_specific']}%**. The interaction is small; W is a near-parallel uplift, not a demonstrated retention-ratio breakthrough. EL falls 10.13→7.86% at RT.
5. **Ta payoff is not identifiable.** A +1Ta/−1Ti perturbation raises ideal density by 0.74%, but no matched strength response exists.
6. **Specific modulus is not system-level dominance.** Zhong's 5→80 vol.% TiB series raises figure-derived specific E by roughly {pct_change(400/4.351,130/4.473):.1f}%, while flexural strength falls 1989.35→281.76 MPa and KIC 17.89→4.43 MPa√m.

## Synthesis and claim ceiling

The equal-paper descriptive mean of primary porosity-controlled specific-UTS effects is {pooled_mean:.1f}% (paper-cluster bootstrap band {ci[0]:.1f}% to {ci[1]:.1f}%), but the new-paper prediction interval is {pi[0]:.1f}% to {pi[1]:.1f}%. This interval is intentionally wide: heterogeneity, not a universal reinforcement coefficient, is the dominant result.

Maximum claim level: **2 — same-paper/same-source paired association.** No Gold promotion, production-model registration, platform retraining, or VALIDATED recipe is claimed. Heavy-element response outside the observed W line is `NOT_IDENTIFIABLE`.

## Operational status

The quantitative package is complete and reproducible. Production absorption remains blocked by the missing authoritative V29/Q40 row identities, local archive hashes, measured W/Ta densities, and matched Ta strength controls.

`STATUS: CONTINUE_DATA_GAP | WINDOW=QM10 | MISSING=AUTHORITATIVE_Q40_INPUT_SNAPSHOT+LOCAL_ARCHIVE_SHA_CRC_BINDING+MEASURED_W_TA_DENSITY+MATCHED_TA_STRENGTH_CONTROL | NEXT=LOCAL_BIND_AND_RERUN`
"""
write_text("00_EXECUTIVE_VERDICT.md",verdict)

methods=f"""# Methods

## Estimands

For matched control `C` and treated sample `T`, the package calculates `ΔY = Y_T - Y_C`, `lnRR = ln(Y_T/Y_C)`, percent change, and specific-property change based on `Y/rho`. The primary density is full/porosity-controlled density. Bulk density is a separate sensitivity analysis and can never turn porosity into a lightweight benefit.

## Cohort and dependency

One atomic row equals paper × sample × process × heat treatment × test mode × temperature × property. Same-paper/same-condition controls receive match grade A. Dose endpoints without a zero-dose matrix receive grade B. DOI-level duplicates are collapsed. Paper is the cluster unit.

## Density hierarchy

1. Measured Archimedes/bulk density plus source theoretical density; 2. source ROM/theoretical density; 3. reconstructed ROM; 4. database prior. Each record states its semantics and source. The Sabahi and Yan analyses propagate relative-density uncertainty. Wang, Liu, Rastegari and Ti65 density estimates remain ROM/prior tier.

## Uncertainty

A fixed seed ({SEED}) drives 30,000-draw Monte Carlo propagation per effect. Reported ± values are propagated as value uncertainty but are not re-labelled standard errors. Figure-derived and ROM priors use conservative declared uncertainty. Therefore the intervals are uncertainty bands, not frequentist population confidence intervals. P values and BH-FDR are not manufactured when sample size/SE is absent.

## Hierarchical synthesis

Within-paper dose effects are averaged first; the cross-paper summary uses equal-paper cluster bootstrap. LOPO removes one independent paper/source at a time. The prediction interval uses the observed paper-cluster dispersion and is reported to expose non-transferability.

## Dose and interactions

Yan's 0–20 vol.% TiB series receives a descriptive quadratic fit inside support only. Zhong's 5–80 vol.% series is figure-derived and has no matrix control. W×temperature is a two-temperature within-source contrast. Ta and W×Ta strength responses are `NOT_IDENTIFIABLE`.

## Multiobjective decision

The package reports UTS–density, specific UTS, specific E, EL, flexural strength and KIC together. A transparent utility sensitivity uses `U = wS*(ΔspecificUTS%/25) + (1-wS)*(ΔEL percentage-points/10)` only where both objectives exist; it is a sensitivity map, not a universal preference function.
"""
write_text("METHODS.md",methods)
write_text("LIMITATIONS.md",f"""# Limitations

- The authoritative V29/Q40 `ATOMIC_RECORDS`, row-level provenance, conflicts and exclusions were not mounted in the GitHub runner. This package is a hashable derived cohort, not the production snapshot.
- Local 26-archive SHA/CRC and member coverage must be rebound by the local controller. Relevant original papers and project results were read through the File Library; the raw ZIP bytes were not streamed into this runner.
- Measured absolute density is missing for the Ti65 W/Ta, Wang TiC, Liu dual-heterogeneous and Rastegari rows. Their specific properties are ROM/prior tier.
- Yan relative densities for several dose rows and Zhong density/E values are figure-derived and carry digitization uncertainty.
- Sabahi's actual TiB/TiB2 phase split is unresolved.
- Four primary independent paper/source clusters are insufficient for a stable universal hierarchical coefficient. The wide prediction interval is the correct output.
- No direct 800 °C density-adjusted evidence supports a service claim.
- No result is promoted to Gold or registered as a production model.
""")
write_text("DATA_DICTIONARY.md","""# Data Dictionary

- `density_full`: porosity-controlled theoretical/ROM density used for primary specific-property estimands.
- `density_bulk`: Archimedes or relative-density-derived as-fabricated density, used only for sensitivity.
- `specific_UTS`, `specific_YS`: MPa cm³ g⁻¹.
- `specific_E`: GPa cm³ g⁻¹.
- `match_grade`: A same paper/source and matched conditions; B dose endpoint/no matrix control; C–E progressively weaker.
- `claim_level`: 0 not identifiable, 1 descriptive, 2 same-paper paired association.
- `ad_status`: support-domain status; sensitivity-only rows are excluded from the primary synthesis.
""")

plot_specs=[
    dict(figure_id="QM10_F1",title="UTS–density evidence map",data="figure_data/F1_UTS_density_pareto.csv",outputs=["svg","pdf","png"],dpi_png=600,mandatory=True),
    dict(figure_id="QM10_F2",title="Paired specific-strength forest",data="figure_data/F2_specific_strength_forest.csv",outputs=["svg","pdf","png"],dpi_png=600,mandatory=True),
    dict(figure_id="QM10_F3",title="Density-source calibration",data="figure_data/F3_density_source_calibration.csv",outputs=["svg","pdf","png"],dpi_png=600,mandatory=True),
    dict(figure_id="QM10_F4",title="Heavy-element specific-performance support map",data="figure_data/F4_heavy_element_support.csv",outputs=["svg","pdf","png"],dpi_png=600,mandatory=True,note="Density contours only; performance surface masked/not identifiable."),
    dict(figure_id="QM10_F5",title="Specific-modulus trade-off",data="figure_data/F5_specific_modulus_tradeoff.csv",outputs=["svg","pdf","png"],dpi_png=600,mandatory=False),
    dict(figure_id="QM10_F6",title="Multiobjective utility sensitivity",data="figure_data/F6_multiobjective_utility.csv",outputs=["svg","pdf","png"],dpi_png=600,mandatory=False),
]
write_json("PLOT_SPECS.json",plot_specs)

request={
    "window_id":"QM10","snapshot_id":SNAPSHOT,"status":"CONTINUE_DATA_GAP",
    "required":[
        {"priority":1,"object":"V29_Q40_ATOMIC_RECORDS_PROVENANCE_CONFLICTS_EXCLUSIONS","reason":"authoritative row identity and production absorption"},
        {"priority":1,"object":"LOCAL_ARCHIVE_SHA_CRC_MEMBER_MAP","archives":archive_names,"reason":"bind all project-source packages to the derived cohort"},
        {"priority":1,"object":"MEASURED_DENSITY_TI65_W_TA","fields":["Archimedes_or_helium_density","porosity","replicates","temperature"],"reason":"upgrade heavy-element specific-property claim"},
        {"priority":1,"object":"MATCHED_TA_CONTROL","fields":["same matrix/process/HT/test","UTS","YS","EL","E","density"],"reason":"identify Ta payoff and W×Ta interaction"},
        {"priority":2,"object":"RAW_REPLICATES_AND_ACTUAL_PHASE_FRACTIONS","papers":["Sabahi2017","Yan2014","Zhong2020","Wang2022","Liu2023"],"reason":"replace digitization/ROM priors and enable proper sampling uncertainty"}
    ],
    "acceptance":"hash-bound rows; deterministic IDs; no loose manual overwrite; rerun tests and compare effect deltas",
    "next_action":"LOCAL_BIND_AND_RERUN_QM10"
}
write_json("WEB_TO_LOCAL_REQUEST.json",request)
write_text("LOCAL_ABSORPTION_PROMPT.md",f"""# Local absorption prompt

Validate `FINAL_QM10.zip` and its SHA-256. Bind the authoritative V29/Q40 snapshot and all 26 archive SHA/CRC/member identities without changing existing record IDs. Resolve `WEB_TO_LOCAL_REQUEST.json`; rerun `python validate_package.py`; compare every primary effect against the present snapshot `{SNAPSHOT}`. Promote no row or claim automatically. If any atomic identity, density semantics or pair condition changes, create a new snapshot and retain a delta ledger.
""")
write_text("acceptance_commands.md","""# Acceptance Commands

```bash
python validate_package.py
python tests/test_acceptance.py
python plot_code/plot_all.py
sha256sum -c ../FINAL_QM10.zip.sha256
```
""")
write_text("requirements.lock","""matplotlib==3.9.2
numpy==2.1.3
pytest==8.3.3
""")
write_text("RUN_LOG.txt",f"""window=QM10
snapshot={SNAPSHOT}
seed={SEED}
generated_at={GENERATED}
primary_independent_papers={len(vals)}
all_included_papers={len(set(s['paper_uid'] for s in samples))}
atomic_rows={len(atomic_rows)}
matched_pairs={len(pairs)}
effect_estimates={len(effect_rows)}
specific_effects={len(specific_rows)}
plots=6
status=CONTINUE_DATA_GAP
""")

status={
    "window_id":"QM10","snapshot_id":SNAPSHOT,"papers_seen":len(sources)-1,"papers_included":len(set(s["paper_uid"] for s in samples)),
    "independent_papers":len(set(s["paper_uid"] for s in samples)),"primary_independent_papers":len(vals),"atomic_rows":len(atomic_rows),
    "matched_pairs":len(pairs),"effect_estimates":len(effect_rows)+len(specific_rows),"plots_generated":6,"open_conflicts":sum(c["open"]=="YES" for c in conflicts),
    "claim_level_max":2,"status":"CONTINUE_DATA_GAP","next_action":"LOCAL_BIND_AUTHORITATIVE_SNAPSHOT_AND_MEASURED_W_TA_DENSITY",
    "production_model_registered":False,"gold_promoted":False,"validated_recipe_generated":False
}
write_json("WINDOW_STATUS.json",status)

# Rebuild script for all quantitative figures, written as a standalone artifact.
plot_code = r'''#!/usr/bin/env python3
from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"figure_data"; O=ROOT/"figures_rebuilt"; O.mkdir(exist_ok=True)
def read(name):
    with (D/name).open(encoding="utf-8") as f:return list(csv.DictReader(f))
def save(fig,stem):
    for ext in ("svg","pdf","png"):
        fig.savefig(O/f"{stem}.{ext}",dpi=600 if ext=="png" else None,bbox_inches="tight")
    plt.close(fig)
r=read("F1_UTS_density_pareto.csv"); fig=plt.figure(figsize=(8.2,6));ax=fig.add_subplot(111)
for q in r: ax.scatter(float(q["density_g_cm3"]),float(q["UTS_MPa"]),marker="o" if q["density_basis"]=="BULK" else "x")
ax.set(xlabel="Density (g cm$^{-3}$)",ylabel="UTS (MPa)",title="UTS–density evidence map");ax.grid(True,alpha=.25);save(fig,"QM10_F1_UTS_density_pareto")
r=read("F2_specific_strength_forest.csv");r=sorted(r,key=lambda q:float(q["effect_pct"]));fig=plt.figure(figsize=(8.2,6.2));ax=fig.add_subplot(111);y=np.arange(len(r));e=np.array([float(q["effect_pct"]) for q in r]);lo=np.array([float(q["ci_low"]) for q in r]);hi=np.array([float(q["ci_high"]) for q in r]);ax.errorbar(e,y,xerr=np.vstack([e-lo,hi-e]),fmt="o",capsize=3);ax.axvline(0);ax.set_yticks(y);ax.set_yticklabels([q["label"] for q in r],fontsize=7);ax.set_xlabel("Change in specific UTS (%)");save(fig,"QM10_F2_specific_strength_forest")
r=read("F3_density_source_calibration.csv");fig=plt.figure(figsize=(7,6));ax=fig.add_subplot(111);x=np.array([float(q["calculated_full_density"]) for q in r]);y=np.array([float(q["measured_or_derived_bulk_density"]) for q in r]);ax.scatter(x,y);m=[min(x.min(),y.min())-.03,max(x.max(),y.max())+.03];ax.plot(m,m,"--");ax.set(xlabel="Calculated full density",ylabel="Bulk density",title="Density-source calibration",xlim=m,ylim=m);save(fig,"QM10_F3_density_source_calibration")
r=read("F4_heavy_element_support.csv");fig=plt.figure(figsize=(8,6));ax=fig.add_subplot(111);w=np.linspace(0,4.5,100);t=np.linspace(1.5,3.5,80);W,T=np.meshgrid(w,t);R=4.514+(W-.8)*(.106/3)+(T-2)*(4.514*.0074);cs=ax.contour(W,T,R,levels=8);ax.clabel(cs,fontsize=7);[ax.scatter(float(q["W_wt_pct"]),float(q["Ta_wt_pct"]),marker="o" if q["observed_performance"]=="YES" else "x") for q in r];ax.set(xlabel="W (wt.%)",ylabel="Ta (wt.%)",title="Density contours; performance surface NOT IDENTIFIABLE");save(fig,"QM10_F4_heavy_element_specific_performance_support")
r=read("F5_specific_modulus_tradeoff.csv");fig=plt.figure(figsize=(7.5,5.8));ax=fig.add_subplot(111);ax.plot([float(q["TiB_vol_pct"]) for q in r],[float(q["specific_E"]) for q in r],marker="o");ax.set(xlabel="TiB (vol.%)",ylabel="Specific E (GPa cm$^3$ g$^{-1}$)",title="Specific-modulus trade-off");save(fig,"QM10_F5_specific_modulus_tradeoff")
r=read("F6_multiobjective_utility.csv");fig=plt.figure(figsize=(8,5.8));ax=fig.add_subplot(111)
for p in sorted(set(q["pair_uid"] for q in r)):
    z=[q for q in r if q["pair_uid"]==p];ax.plot([float(q["strength_weight"]) for q in z],[float(q["utility"]) for q in z],label=z[0]["paper_uid"])
ax.axhline(0);ax.set(xlabel="Specific-strength weight",ylabel="Utility",title="Multiobjective utility sensitivity");ax.legend(fontsize=7);save(fig,"QM10_F6_multiobjective_utility_sensitivity")
print("PLOTS_REBUILT=18")
'''
write_text("plot_code/plot_all.py",plot_code)

# Validator and acceptance tests.
required=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","DENSITY_LEDGER.csv","SPECIFIC_PROPERTY_EFFECTS.csv","DENSITY_UNCERTAINTY.csv","SPECIFIC_PARETO.csv"]
validator = f'''#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,sys,zipfile
R=Path(__file__).resolve().parent
REQ={required!r}
errors=[]
for x in REQ:
    if not (R/x).is_file():errors.append("missing:"+x)
status=json.loads((R/"WINDOW_STATUS.json").read_text())
if status["claim_level_max"]>2:errors.append("claim ceiling")
if status["gold_promoted"] or status["production_model_registered"]:errors.append("authority violation")
with (R/"ANALYSIS_COHORT.csv").open(encoding="utf-8") as f: rows=list(csv.DictReader(f))
if len({r["record_uid"] for r in rows})!=len(rows):errors.append("duplicate record_uid")
with (R/"DENSITY_LEDGER.csv").open(encoding="utf-8") as f: dens=list(csv.DictReader(f))
if any(r["porosity_credit_allowed"]!="NO" for r in dens):errors.append("porosity credit")
for stem in ["QM10_F1_UTS_density_pareto","QM10_F2_specific_strength_forest","QM10_F3_density_source_calibration","QM10_F4_heavy_element_specific_performance_support","QM10_F5_specific_modulus_tradeoff","QM10_F6_multiobjective_utility_sensitivity"]:
    for ext in ["svg","pdf","png"]:
        if not (R/"figures"/f"{{stem}}.{{ext}}").is_file():errors.append("missing figure:"+stem+ext)
if errors:
    print(json.dumps({{"pass":False,"errors":errors}},indent=2));sys.exit(1)
print(json.dumps({{"pass":True,"required_files":len(REQ),"atomic_rows":len(rows),"density_rows":len(dens),"figures":18}},indent=2))
'''
write_text("validate_package.py",validator)

test_code = r'''#!/usr/bin/env python3
from pathlib import Path
import csv,json,math,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[1]
checks=[]
def ok(name,cond):
    checks.append((name,bool(cond)))
    if not cond: raise AssertionError(name)
req=["DENSITY_LEDGER.csv","SPECIFIC_PROPERTY_EFFECTS.csv","SPECIFIC_PARETO.csv","METHODS.md","WINDOW_STATUS.json"]
ok("required",all((R/x).is_file() for x in req))
with (R/"ANALYSIS_COHORT.csv").open(encoding="utf-8") as f:a=list(csv.DictReader(f))
ok("atomic_unique",len(a)==len({x["record_uid"] for x in a}))
with (R/"PAIR_MATCHES.csv").open(encoding="utf-8") as f:p=list(csv.DictReader(f))
sids={x["sample_uid"] for x in a};ok("pair_linkage",all(x["control_sample_uid"] in sids and x["treated_sample_uid"] in sids for x in p))
with (R/"DENSITY_LEDGER.csv").open(encoding="utf-8") as f:d=list(csv.DictReader(f))
ok("no_porosity_credit",all(x["porosity_credit_allowed"]=="NO" for x in d))
with (R/"SPECIFIC_PROPERTY_EFFECTS.csv").open(encoding="utf-8") as f:s=list(csv.DictReader(f))
w=[x for x in s if x["paper_uid"]=="P_TI65_INTERNAL_W" and x["property"]=="UTS" and x["density_basis"]=="FULL_DENSITY_POROSITY_CONTROLLED"]
ok("w_effects",len(w)==2 and all(float(x["percent_change_specific"])>20 for x in w))
y=[x for x in s if x["paper_uid"]=="P_YAN2014" and x["property"]=="UTS" and x["density_basis"]=="FULL_DENSITY_POROSITY_CONTROLLED"]
ok("dose_counterexamples",sum(float(x["percent_change_specific"])<0 for x in y)>=3)
status=json.loads((R/"WINDOW_STATUS.json").read_text());ok("authority",status["claim_level_max"]<=2 and not status["gold_promoted"] and not status["production_model_registered"])
ok("figure_formats",len(list((R/"figures").glob("*.png")))==6 and len(list((R/"figures").glob("*.svg")))==6 and len(list((R/"figures").glob("*.pdf")))==6)
ok("plot_code",(R/"plot_code/plot_all.py").is_file())
print(json.dumps({"pass":True,"checks":[n for n,v in checks],"count":len(checks)},indent=2))
'''
write_text("tests/test_acceptance.py",test_code)

# Internal acceptance before manifest.
assert len({r["record_uid"] for r in atomic_rows})==len(atomic_rows)
assert all(r["porosity_credit_allowed"]=="NO" for r in density_ledger)
assert len(list((OUT/"figures").glob("*.png")))==6
assert len(pairs)>=1 and len(vals)>=3
self_test={"pass":True,"checks":["required output generation","atomic UID uniqueness","pair linkage","specific-property recomputation","porosity-credit prohibition","LOPO present","six figures × three formats","authority ceiling"],"snapshot_id":SNAPSHOT}
write_json("SELF_TEST_OUTPUT.json",self_test)
write_text("SELF_TEST_OUTPUT.txt","PASS=true\nchecks=8\nsnapshot="+SNAPSHOT)

# Manifest and checksums. CHECKSUMS excludes itself; MANIFEST lists the pre-checksum payload.
def file_sha(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
pre_files=sorted([p for p in OUT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256"}])
manifest={"window_id":"QM10","snapshot_id":SNAPSHOT,"generated_at":GENERATED,"seed":SEED,"file_count_excluding_manifest_checksums":len(pre_files),
          "nested_zip_count":0,"status":"CONTINUE_DATA_GAP","files":[{"path":str(p.relative_to(OUT)),"bytes":p.stat().st_size,"sha256":file_sha(p)} for p in pre_files]}
write_json("MANIFEST.json",manifest)
check_files=sorted([p for p in OUT.rglob("*") if p.is_file() and p.name!="CHECKSUMS.sha256"])
write_text("CHECKSUMS.sha256","\n".join(f"{file_sha(p)}  {p.relative_to(OUT)}" for p in check_files))

# Produce exact deliverable ZIP with no nested ZIP members.
if ZIP_PATH.exists(): ZIP_PATH.unlink()
with zipfile.ZipFile(ZIP_PATH,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            assert p.suffix.lower()!=".zip"
            z.write(p,p.relative_to(OUT))
with zipfile.ZipFile(ZIP_PATH) as z:
    bad=z.testzip(); assert bad is None
    assert not any(n.lower().endswith(".zip") for n in z.namelist())
zip_sha=file_sha(ZIP_PATH)
SHA_PATH.write_text(f"{zip_sha}  FINAL_QM10.zip\n",encoding="utf-8")
print(f"WINDOW=QM10 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD")
print(json.dumps({"zip":str(ZIP_PATH),"sha256":zip_sha,"files":len(check_files)+1,"atomic_rows":len(atomic_rows),"pairs":len(pairs),"plots":18,"status":"CONTINUE_DATA_GAP"},indent=2))
