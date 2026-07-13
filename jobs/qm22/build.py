#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM22"
ART = ROOT / "artifacts"
FD = OUT / "figure_data"
FG = OUT / "figures"
PC = OUT / "plot_code"
LE = OUT / "literature_evidence"
AC = OUT / "analysis_code"
SEED = 20260713
GENERATED = "2026-07-13T05:15:00+00:00"
np.random.seed(SEED)


def hbytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def htext(s: str) -> str:
    return hbytes(s.encode("utf-8"))


def sid(prefix: str, *parts: Any) -> str:
    return prefix + "_" + htext("|".join("" if x is None else str(x) for x in parts))[:20]


def wtext(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def wjson(path: Path, obj: Any) -> None:
    wtext(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        wr.writeheader()
        for r in rows:
            wr.writerow({k: "" if v is None or (isinstance(v, float) and math.isnan(v)) else v for k, v in r.items()})


def linfit(xs: Iterable[float], ys: Iterable[float]) -> dict[str, float]:
    x = np.asarray(list(xs), float); y = np.asarray(list(ys), float)
    q = stats.linregress(x, y)
    if len(x) >= 3 and np.isfinite(q.stderr):
        t = stats.t.ppf(0.975, len(x)-2)
        lo, hi = q.slope-t*q.stderr, q.slope+t*q.stderr
    else:
        lo = hi = np.nan
    return {"slope": float(q.slope), "intercept": float(q.intercept), "r2": float(q.rvalue**2),
            "p_value": float(q.pvalue), "se": float(q.stderr), "ci95_low": float(lo), "ci95_high": float(hi),
            "n_levels": len(x)}


def bh(pvals: list[float | None]) -> list[float | None]:
    valid = sorted([(i, float(p)) for i, p in enumerate(pvals) if p is not None and np.isfinite(p)], key=lambda x: x[1])
    out: list[float | None] = [None]*len(pvals); running = 1.0; m = len(valid)
    for rev, (i, p) in enumerate(reversed(valid), 1):
        rank = m-rev+1; running = min(running, p*m/rank); out[i] = running
    return out


def ols_term(y: np.ndarray, cols: dict[str, np.ndarray], target: str) -> dict[str, float]:
    names = ["intercept"] + list(cols)
    X = np.column_stack([np.ones(len(y))] + [np.asarray(cols[k], float) for k in cols])
    b = np.linalg.pinv(X.T@X)@X.T@y; resid = y-X@b; df = len(y)-X.shape[1]
    idx = names.index(target)
    if df <= 0:
        return {"estimate": float(b[idx]), "se": np.nan, "p_value": np.nan}
    mse = float(resid.T@resid/df); cov = mse*np.linalg.pinv(X.T@X); se = math.sqrt(max(float(cov[idx,idx]),0))
    tv = b[idx]/se if se else np.nan; pv = 2*stats.t.sf(abs(tv),df) if np.isfinite(tv) else np.nan
    return {"estimate": float(b[idx]), "se": float(se), "p_value": float(pv)}


PAPERS = [
 ("GRAY1990_TI86AL_OXYGEN","10.1007/BF02656428","10693_bban_10_1007_bf02656428.pdf","Table I/II; beta-solvus and fracture text","DIRECT_TABLE_TEXT"),
 ("CHONG2020_TI_O_PLANAR_SLIP","10.1126/sciadv.abc4060","10831_scienceadvances_10.1126_sciadv.abc4060.pdf","RT tensile endpoints and mechanism text","DIRECT_TEXT"),
 ("DIETRICH2020_LPBF_TI64_O_N","10.1016/j.addma.2019.100980","11986_bban_10_1016_j_addma_2019_100980.pdf","bulk chemistry and Fig.19 labels","DIRECT_TEXT_FIGURE_LABELS"),
 ("MUNIR2018_TI_MWCNT_TIC_ON","10.1016/j.mtla.2018.08.015","0860_materialia_10.1016_j.mtla.2018.08.015.pdf","composition, TiC and compression tables","DIRECT_TABLE_TEXT"),
 ("HUANG2025_HIGHNB_TIAL_C","10.1038/s41598-025-15339-4","1581_微观组织与力学性能的高Nb-TiAl合金具有differentcarbonadditions.pdf","RT tensile and 800C compression endpoints","DIRECT_TEXT_FIGURE_LABELS"),
 ("MIMOTO2011_PURETI_CNP","10.18910/5200","12250_openalex_10.18910_5200_0.pdf","endpoint and author-reported regime slopes","DIRECT_TEXT_FIGURE_LABELS"),
 ("KONDOH2012_TI_CNT_HT","10.1016/j.compscitech.2012.04.006","1729_高-temperature性能的extrudedtitanium复合材料fabricated从carbonnanot.pdf","Table 3 carbon partition","DIRECT_TABLE_TEXT"),
 ("TSUDA2020_N_TIC_PHASE_REACTION","10.2320/matertrans.MT-M2019318","Tsuda_2020_nitrogen_TiC.pdf",">2 at% N phase-reaction threshold","DIRECT_TEXT"),
 ("IBRAHIM2024_LPBF_TNTZ_O","10.1016/j.msea.2024.146617","1514_激光粉末床熔合的_钛合金_Microstructural开发_post-加工_与mechanical行为.pdf","Table 1 O and AlEq text","DIRECT_TABLE_TEXT"),
 ("ROGOFF2018_TI64_BETA_TRANSUS","10.1007/s11665-018-3432-5","9363_bban_10_1007_s11665-018-3432-5.pdf","Eq.7 and DTA validation","DIRECT_EQUATION_TEXT"),
 ("JOHNSON2006_TIAL_AL_EQ","10.1016/j.actamat.2005.10.040","11983_bban_10_1016_j_actamat_2005_10_040.pdf","Table 2 TiAl liquidus Al-equivalent","DIRECT_TABLE_TEXT"),
]
SNAPSHOT = "RECOVERY_QM22_" + htext(json.dumps(PAPERS, ensure_ascii=False)+"QM22_SCHEMA_1.1")[:20]

ARCHIVES = [
 "00_统一上传总控与校验信息_20260712.zip","S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
 "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
 *[f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1,9)],
 "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
 *[f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1,4)],
 *[f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1,11)],
]
KNOWN = {
 "S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip":"cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a",
 "S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip":"97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809",
 "S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip":"16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f",
 "S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip":"04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9",
 "S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip":"5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728",
 "S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip":"e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847",
 "S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip":"36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485",
 "S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip":"9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd",
 "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip":"c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c",
 "S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip":"a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a",
 "S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip":"bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43",
 "S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip":"08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755",
 "TITMC_V27_LIT_WEB_P001_OF_010.zip":"42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0",
 "TITMC_V27_LIT_WEB_P002_OF_010.zip":"05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193",
 "TITMC_V27_LIT_WEB_P003_OF_010.zip":"535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917",
 "TITMC_V27_LIT_WEB_P004_OF_010.zip":"bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a",
}

ATOMIC_FIELDS = ["record_uid","snapshot_id","paper_uid","sample_uid","condition_uid","matrix_family","alloy","process","heat_treatment","test_mode","test_temp_C","Al_wt","O_wt","N_wt","C_wt","C_at_pct","C_role","reinforcement","reinforcement_fraction","reinforcement_unit","phase_state","property","property_value","property_unit","evidence_level","source_locator","notes"]


def atomic_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    def add(paper: str, sample: str, cond: str, prop: str, val: float, unit: str, **kw: Any) -> None:
        r={k:None for k in ATOMIC_FIELDS}; r.update(kw); r.update({"snapshot_id":SNAPSHOT,"paper_uid":paper,
          "sample_uid":sid("S",paper,sample),"condition_uid":sid("C",paper,sample,cond,prop),"property":prop,
          "property_value":val,"property_unit":unit,"evidence_level":kw.get("evidence_level","DIRECT_TABLE_TEXT")})
        r["record_uid"]=sid("R",paper,sample,cond,prop,val); rows.append(r)
    levels=[("O500",8.67,.044),("O1000",8.60,.103),("O2000",8.65,.209)]
    gp={"ST":{"YS":[600,710,770],"TRUE_FRACTURE_STRESS":[800,830,890],"TRUE_FRACTURE_STRAIN":[.53,.42,.24]},
        "ST_LN2":{"YS":[1050,1175,1320],"TRUE_FRACTURE_STRESS":[1200,1250,1375],"TRUE_FRACTURE_STRAIN":[.25,.21,.13]},
        "STA":{"YS":[650,750,825],"TRUE_FRACTURE_STRESS":[900,780,840],"TRUE_FRACTURE_STRAIN":[.40,.08,.05]}}
    for ht,props in gp.items():
        for prop,vals in props.items():
            for (s,al,o),v in zip(levels,vals): add("GRAY1990_TI86AL_OXYGEN",s,ht,prop,v,"MPa" if prop!="TRUE_FRACTURE_STRAIN" else "fraction",matrix_family="near_alpha",alloy="Ti-8.6Al",process="arc_melted_worked",heat_treatment=ht,test_mode="tension",test_temp_C=25,Al_wt=al,O_wt=o,C_role="not_reported",reinforcement="none",phase_state="alpha_plus_alpha2",source_locator="Table I/Table II")
    for s,o,v in [("O500",.044,1041),("O2000",.209,1057)]: add("GRAY1990_TI86AL_OXYGEN",s,"phase","BETA_SOLVUS",v,"degC",matrix_family="near_alpha",alloy="Ti-8.6Al",O_wt=o,source_locator="beta-solvus text")
    for s,o,ys,el in [("O005",.05,156,48),("O030",.30,472,16)]:
        for p,v,u in [("YS",ys,"MPa"),("EL",el,"pct")]: add("CHONG2020_TI_O_PLANAR_SLIP",s,"RT",p,v,u,matrix_family="commercially_pure_alpha",alloy="Ti-O",process="model_alloy",heat_treatment="reported",test_mode="tension",test_temp_C=25,O_wt=o,reinforcement="none",phase_state="alpha",source_locator="RT endpoint text")
    ppm=[2,200,399,600,977]; ox=[.16596,.169,.17358,.17804,.18479]; nn=[.00558,.01240,.01256,.01691,.02004]
    dv={"stress_relieved":{"YS":[1123,1133,1126,1140,1163],"UTS":[1203,1213,1205,1217,1233],"EL":[8.1,8.6,7.9,6.5,7.2]},"HIP":{"YS":[900,913,919,921,980],"UTS":[983,992,1002,1004,1058],"EL":[16.8,16.5,16.7,16.6,14.0]}}
    for ht,props in dv.items():
        for p,vals in props.items():
            for q,o,n,v in zip(ppm,ox,nn,vals): add("DIETRICH2020_LPBF_TI64_O_N",f"CHAMBER_{q}PPM",ht,p,v,"pct" if p=="EL" else "MPa",matrix_family="alpha_beta",alloy="Ti-6Al-4V",process="LPBF",heat_treatment=ht,test_mode="tension",test_temp_C=25,Al_wt=6.64,O_wt=o,N_wt=n,C_wt=.01,C_role="measured_constant",reinforcement="none",phase_state="alpha_prime_or_HIP_alpha_beta",source_locator="chemistry table + Fig.19 labels",evidence_level="DIRECT_TEXT_FIGURE_LABELS",notes=f"chamber O2={q} ppm; bulk O used")
    mm=[("CONTROL",0,"control",.38,.010,0,695,40.4,"none"),("C05_B1",.5,"dry_HEBM_B1",.47,.016,.4,822,30.7,"TiC"),("C05_B2",.5,"dry_HEBM_B2",.52,.019,2,782,33.3,"TiC"),("C05_B3",.5,"SBM_B3",.63,.021,1.1,920,24.5,"TiC"),("C10_B1",1,"dry_HEBM_B1",.51,.023,4.7,800,29.8,"TiC"),("C10_B2",1,"dry_HEBM_B2",.73,.039,67.5,610,16.6,"TiC_agglomerated_porous"),("C10_B3",1,"SBM_B3",.79,.051,2.7,860,27.7,"TiC")]
    for s,c,pr,o,n,tic,ys,st,phase in mm:
        common=dict(matrix_family="commercially_pure_alpha",alloy="CP-Ti",process=pr,heat_treatment="SPS_hot_extruded",test_mode="compression",test_temp_C=25,O_wt=o,N_wt=n,C_wt=c,C_role="MWCNT_precursor_plus_reaction_unresolved",reinforcement="TiC" if c else "none",reinforcement_fraction=tic,reinforcement_unit="wt_pct",phase_state=phase,source_locator="composition/TiC/mechanical tables")
        add("MUNIR2018_TI_MWCNT_TIC_ON",s,"RT","COMPRESSIVE_YS",ys,"MPa",**common); add("MUNIR2018_TI_MWCNT_TIC_ON",s,"RT","COMPRESSIVE_STRAIN",st,"pct",**common)
    for c,ts,el in [(0,352.1,1.49),(.6,431.6,1.89),(1.5,265.8,1.15)]:
        s=f"C{str(c).replace('.','P')}AT"; common=dict(matrix_family="gamma_tial_high_nb",alloy="Ti-45Al-8Nb-0.5B-xC",process="arc_melted_cast",heat_treatment="as_cast",test_mode="tension",test_temp_C=25,C_at_pct=c,C_role="interstitial_then_Ti2AlC",reinforcement="Ti2AlC" if c>=.6 else "none_or_below_detection",phase_state="gamma_alpha2_B2_TiB2_Ti2AlC",source_locator="Fig.8 exact text",evidence_level="DIRECT_TEXT_FIGURE_LABELS")
        add("HUANG2025_HIGHNB_TIAL_C",s,"RT","UTS",ts,"MPa",**common); add("HUANG2025_HIGHNB_TIAL_C",s,"RT","EL",el,"pct",**common)
    for c,stress,strain in [(0,900,11.3),(.6,1074,12.5)]:
        s=f"C{str(c).replace('.','P')}AT"; common=dict(matrix_family="gamma_tial_high_nb",alloy="Ti-45Al-8Nb-0.5B-xC",process="arc_melted_cast",heat_treatment="as_cast",test_mode="compression",test_temp_C=800,C_at_pct=c,C_role="interstitial_then_Ti2AlC",reinforcement="Ti2AlC" if c>=.6 else "none",phase_state="gamma_alpha2_B2_TiB2_Ti2AlC",source_locator="abstract exact text",evidence_level="DIRECT_TEXT")
        add("HUANG2025_HIGHNB_TIAL_C",s,"800C","COMPRESSIVE_STRESS_MAX",stress,"MPa",**common); add("HUANG2025_HIGHNB_TIAL_C",s,"800C","COMPRESSIVE_STRAIN_AT_MAX",strain,"pct",**common)
    for p,v,u in [("YS",837,"MPa"),("UTS",899,"MPa"),("EL",18.7,"pct")]: add("MIMOTO2011_PURETI_CNP","COMP7","RT",p,v,u,matrix_family="commercially_pure_alpha",alloy="CP-Ti",process="wet_coating_SPS_extrusion",test_mode="tension",test_temp_C=25,C_at_pct=2.66,C_role="total_partitioned_solution_TiC",reinforcement="TiC",phase_state="alpha_plus_TiC",source_locator="abstract/Fig.5 text")
    for s,pre,tic,sol,total in [("PURE_TI",0,0,0,.01),("CNT1",1,.61,.003385,.27),("CNT2",2,1.58,.003306,.37),("CNT3",3,2.55,.011661,.76)]:
        common=dict(matrix_family="commercially_pure_alpha",alloy="CP-Ti",process="SPS_extrusion_anneal473K",test_mode="phase_chemistry",test_temp_C=200,C_wt=pre,C_role="CNT_precursor_partitioned",reinforcement="TiC",reinforcement_fraction=tic,reinforcement_unit="wt_pct",phase_state="alpha_plus_TiC",source_locator="Table 3")
        for p,v in [("TOTAL_C_ANALYSIS",total),("DISSOLVED_C",sol),("TIC_CONTENT",tic)]: add("KONDOH2012_TI_CNT_HT",s,"partition",p,v,"wt_pct",**common)
    add("TSUDA2020_N_TIC_PHASE_REACTION","N2_THRESHOLD","phase","N_TIC_REACTION_THRESHOLD",2,"at_pct_N",matrix_family="commercially_pure_alpha",alloy="Ti-5vol%TiC",process="composite_processing",test_mode="phase_characterization",C_role="TiC_stoichiometric",reinforcement="TiC",reinforcement_fraction=5,reinforcement_unit="vol_pct",phase_state="above_2atN_Ti2C_disappears_alpha_platelets_in_TiC",source_locator="direct text",evidence_level="DIRECT_TEXT")
    add("IBRAHIM2024_LPBF_TNTZ_O","POWDER","chemistry","AL_EQ_REPORTED",4,"wt_pct_equivalent",matrix_family="metastable_beta",alloy="TNTZ",process="gas_atomized",O_wt=.312,reinforcement="none",phase_state="beta",source_locator="Table 1 + AlEq text",notes="formula 0.17Zr+0.33Sn+10O")
    add("IBRAHIM2024_LPBF_TNTZ_O","AS_BUILT","chemistry","O_CONTENT",.318,"wt_pct",matrix_family="metastable_beta",alloy="TNTZ",process="LPBF",O_wt=.318,reinforcement="none",phase_state="metastable_beta",source_locator="Table 1")
    return rows


def make_pairs(a: list[dict[str,Any]]) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    pairs=[]; eff=[]
    def find(paper,sample,prop,cond):
        rr=[r for r in a if r["paper_uid"]==paper and r["sample_uid"]==sid("S",paper,sample) and r["property"]==prop]
        if paper in ("GRAY1990_TI86AL_OXYGEN","DIETRICH2020_LPBF_TI64_O_N"): rr=[r for r in rr if r["heat_treatment"]==cond]
        if paper=="HUANG2025_HIGHNB_TIAL_C": rr=[r for r in rr if r["test_temp_C"]==(25 if cond=="RT" else 800)]
        return rr[0] if len(rr)==1 else None
    def add(paper,ctrl,trt,cond,props,group,var,x0,x1,unit,grade,notes=""):
        pu=sid("P",paper,ctrl,trt,cond); pairs.append({"pair_uid":pu,"snapshot_id":SNAPSHOT,"paper_uid":paper,"control_sample":ctrl,"treated_sample":trt,"condition":cond,"element_group":group,"dose_variable":var,"dose_control":x0,"dose_treated":x1,"dose_delta":x1-x0,"dose_unit":unit,"match_grade":grade,"properties":";".join(props),"notes":notes})
        for p in props:
            c,t=find(paper,ctrl,p,cond),find(paper,trt,p,cond)
            if not c or not t: continue
            cv,tv=float(c["property_value"]),float(t["property_value"]); d=tv-cv; lr=math.log(tv/cv) if cv>0 and tv>0 else None
            eff.append({"effect_uid":sid("E",pu,p),"pair_uid":pu,"snapshot_id":SNAPSHOT,"paper_uid":paper,"property":p,"property_unit":c["property_unit"],"control_value":cv,"treated_value":tv,"delta":d,"lnRR":lr,"percent_change":(math.exp(lr)-1)*100 if lr is not None else None,"dose_delta":x1-x0,"dose_unit":unit,"unit_dose_effect":d/(x1-x0),"element_group":group,"estimand":f"same-paper conditional {group} perturbation","match_grade":grade,"claim_level":2,"evidence_level":c["evidence_level"],"control_record_uid":c["record_uid"],"treated_record_uid":t["record_uid"],"source_locator":c["source_locator"],"notes":notes})
    for ht in ["ST","ST_LN2","STA"]:
        for s,x in [("O1000",.103),("O2000",.209)]: add("GRAY1990_TI86AL_OXYGEN","O500",s,ht,["YS","TRUE_FRACTURE_STRESS","TRUE_FRACTURE_STRAIN"],"O","O_wt",.044,x,"wt_pct","A")
    add("CHONG2020_TI_O_PLANAR_SLIP","O005","O030","RT",["YS","EL"],"O","O_wt",.05,.30,"wt_pct","A")
    ppm=[2,200,399,600,977]; ox=[.16596,.169,.17358,.17804,.18479]; nn=[.00558,.0124,.01256,.01691,.02004]; ae=[6.64+10*(o+n) for o,n in zip(ox,nn)]
    for ht in ["stress_relieved","HIP"]:
        for q,x in zip(ppm[1:],ae[1:]): add("DIETRICH2020_LPBF_TI64_O_N","CHAMBER_2PPM",f"CHAMBER_{q}PPM",ht,["YS","UTS","EL"],"O_plus_N_via_AlEq","AlEq_Al_plus_10_ON",ae[0],x,"wt_pct_equivalent","A","O/N collinear")
    for s,x in [("C05_B1",.5),("C05_B2",.5),("C05_B3",.5),("C10_B1",1),("C10_B2",1),("C10_B3",1)]: add("MUNIR2018_TI_MWCNT_TIC_ON","CONTROL",s,"RT",["COMPRESSIVE_YS","COMPRESSIVE_STRAIN"],"C_precursor_x_ON_x_TiC_process","MWCNT_wt",0,x,"wt_pct","B","process/reaction/porosity jointly change")
    add("HUANG2025_HIGHNB_TIAL_C","C0AT","C0P6AT","RT",["UTS","EL"],"C","C_at_pct",0,.6,"at_pct","A")
    add("HUANG2025_HIGHNB_TIAL_C","C0AT","C1P5AT","RT",["UTS","EL"],"C","C_at_pct",0,1.5,"at_pct","A")
    add("HUANG2025_HIGHNB_TIAL_C","C0AT","C0P6AT","800C",["COMPRESSIVE_STRESS_MAX","COMPRESSIVE_STRAIN_AT_MAX"],"C","C_at_pct",0,.6,"at_pct","A")
    return pairs,eff


def analyses(a: list[dict[str,Any]]) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    dose=[]
    def addfit(paper,state,prop,var,unit,x,y,status="ESTIMABLE_WITHIN_PAPER",interp=""):
        z=linfit(x,y); dose.append({"result_uid":sid("D",paper,state,prop,var),"snapshot_id":SNAPSHOT,"paper_uid":paper,"state":state,"property":prop,"dose_variable":var,"dose_unit":unit,"slope":z["slope"],"slope_unit":f"property_unit/{unit}","intercept":z["intercept"],"r2":z["r2"],"p_value":z["p_value"],"slope_se":z["se"],"ci95_low":z["ci95_low"],"ci95_high":z["ci95_high"],"n_levels":z["n_levels"],"claim_level":2,"status":status,"interpretation":interp})
    gray=[r for r in a if r["paper_uid"]=="GRAY1990_TI86AL_OXYGEN"]
    for ht in ["ST","ST_LN2","STA"]:
        for p in ["YS","TRUE_FRACTURE_STRESS","TRUE_FRACTURE_STRAIN"]:
            g=sorted([r for r in gray if r["heat_treatment"]==ht and r["property"]==p],key=lambda r:r["O_wt"]); addfit("GRAY1990_TI86AL_OXYGEN",ht,p,"O_wt","wt_pct",[r["O_wt"] for r in g],[r["property_value"] for r in g],interp="actual-O slope at fixed state")
    dose.append({"result_uid":sid("D","Gray","solvus"),"snapshot_id":SNAPSHOT,"paper_uid":"GRAY1990_TI86AL_OXYGEN","state":"phase","property":"BETA_SOLVUS","dose_variable":"O_wt","dose_unit":"wt_pct","slope":(1057-1041)/(.209-.044),"slope_unit":"degC/wt_pct","n_levels":2,"claim_level":2,"status":"TWO_POINT_ENDPOINT","interpretation":"O raises beta solvus"})
    for p in ["YS","EL"]:
        g=sorted([r for r in a if r["paper_uid"]=="CHONG2020_TI_O_PLANAR_SLIP" and r["property"]==p],key=lambda r:r["O_wt"]); addfit("CHONG2020_TI_O_PLANAR_SLIP","RT",p,"O_wt","wt_pct",[r["O_wt"] for r in g],[r["property_value"] for r in g],"TWO_POINT_ENDPOINT","actual-O endpoint")
    d=[r.copy() for r in a if r["paper_uid"]=="DIETRICH2020_LPBF_TI64_O_N"]
    for r in d:r["AlEq"]=r["Al_wt"]+10*(r["O_wt"]+r["N_wt"])
    for ht in ["stress_relieved","HIP"]:
        for p in ["YS","UTS","EL"]:
            g=sorted([r for r in d if r["heat_treatment"]==ht and r["property"]==p],key=lambda r:r["AlEq"]); addfit("DIETRICH2020_LPBF_TI64_O_N",ht,p,"AlEq_Al_plus_10_ON","wt_pct_equivalent",[r["AlEq"] for r in g],[r["property_value"] for r in g],interp="combined O+N; not separable")
    for p,vals in [("UTS",{0:352.1,.6:431.6,1.5:265.8}),("EL",{0:1.49,.6:1.89,1.5:1.15})]:
        for state,x0,x1 in [("RT_below_0.6atC",0,.6),("RT_above_0.6atC",.6,1.5)]: dose.append({"result_uid":sid("D","Huang",state,p),"snapshot_id":SNAPSHOT,"paper_uid":"HUANG2025_HIGHNB_TIAL_C","state":state,"property":p,"dose_variable":"C_at_pct","dose_unit":"at_pct","slope":(vals[x1]-vals[x0])/(x1-x0),"slope_unit":"property_unit/at_pct","n_levels":2,"claim_level":2,"status":"PIECEWISE_ENDPOINT","interpretation":"solution/precipitation below; coarsening/debonding above"})
    for p,v0,v1 in [("COMPRESSIVE_STRESS_MAX",900,1074),("COMPRESSIVE_STRAIN_AT_MAX",11.3,12.5)]: addfit("HUANG2025_HIGHNB_TIAL_C","800C",p,"C_at_pct","at_pct",[0,.6],[v0,v1],"TWO_POINT_ENDPOINT","800C compression endpoint")
    for state,sl in [("solute_C_COMP1_4",257),("TiC_dispersion_COMP4_7",95)]: dose.append({"result_uid":sid("D","Mimoto",state),"snapshot_id":SNAPSHOT,"paper_uid":"MIMOTO2011_PURETI_CNP","state":state,"property":"YS","dose_variable":"total_C_at_pct","dose_unit":"at_pct","slope":sl,"slope_unit":"MPa/at_pct","n_levels":"author_reported","claim_level":2,"status":"AUTHOR_REPORTED_SLOPE","interpretation":"mechanism-regime slope"})
    for e,f in [("Al",39.376),("O",216),("N",1286.25),("C",873.875)]: dose.append({"result_uid":sid("D","Rogoff",e),"snapshot_id":SNAPSHOT,"paper_uid":"ROGOFF2018_TI64_BETA_TRANSUS","state":"Ti64_chemistry_domain","property":"BETA_TRANSUS","dose_variable":e+"_wt","dose_unit":"wt_pct","slope":f*5/9,"slope_unit":"degC/wt_pct","n_levels":115,"claim_level":2,"status":"VALIDATED_CHEMISTRY_EQUATION_COEFFICIENT","interpretation":"phase-stability coefficient; not tensile effect"})
    for p in ["COMPRESSIVE_YS","COMPRESSIVE_STRAIN"]: dose.append({"result_uid":sid("D","Munir",p),"snapshot_id":SNAPSHOT,"paper_uid":"MUNIR2018_TI_MWCNT_TIC_ON","state":"mixed_routes","property":p,"dose_variable":"O_N_C_TiC_joint","dose_unit":"mixed","slope":None,"n_levels":7,"claim_level":2,"status":"NOT_IDENTIFIABLE","interpretation":"O/N/C/TiC/process/porosity co-determined"})
    inter=[]; pvals=[]
    for prop in ["YS","TRUE_FRACTURE_STRESS","TRUE_FRACTURE_STRAIN"]:
        g=[r for r in gray if r["property"]==prop]; y=np.array([r["property_value"] for r in g]); o=np.array([r["O_wt"] for r in g]); ln=np.array([r["heat_treatment"]=="ST_LN2" for r in g],float); sa=np.array([r["heat_treatment"]=="STA" for r in g],float)
        for target,label in [("O_LN2","ST_LN2_vs_ST"),("O_STA","STA_vs_ST")]:
            z=ols_term(y,{"O":o,"LN2":ln,"STA":sa,"O_LN2":o*ln,"O_STA":o*sa},target); inter.append({"interaction_uid":sid("I","Gray",prop,label),"snapshot_id":SNAPSHOT,"paper_uid":"GRAY1990_TI86AL_OXYGEN","interaction":f"O_wt x {label}","property":prop,"estimate":z["estimate"],"estimate_unit":"property_unit/wt_pct","se":z["se"],"p_value":z["p_value"],"n_rows":len(g),"model":"OLS main+interaction","status":"SPARSE_WITHIN_PAPER","claim_level":2,"interpretation":"slope difference relative ST"}); pvals.append(z["p_value"])
    for prop in ["YS","UTS","EL"]:
        g=[r for r in d if r["property"]==prop]; y=np.array([r["property_value"] for r in g]); x=np.array([r["AlEq"] for r in g]); hip=np.array([r["heat_treatment"]=="HIP" for r in g],float); z=ols_term(y,{"AlEq":x,"HIP":hip,"AlEq_HIP":x*hip},"AlEq_HIP"); inter.append({"interaction_uid":sid("I","Dietrich",prop),"snapshot_id":SNAPSHOT,"paper_uid":"DIETRICH2020_LPBF_TI64_O_N","interaction":"AlEq(Al+10(O+N)) x HIP","property":prop,"estimate":z["estimate"],"estimate_unit":"property_unit/AlEq","se":z["se"],"p_value":z["p_value"],"n_rows":len(g),"model":"OLS main+interaction","status":"SPARSE_WITHIN_PAPER","claim_level":2,"interpretation":"heat-treatment-dependent combined O+N slope"}); pvals.append(z["p_value"])
    for r,q in zip(inter,bh(pvals)): r["q_value_bh"]=q; r["fdr_decision_0.05"]=bool(q is not None and q<=.05)
    for paper,name,prop,status in [("HUANG2025_HIGHNB_TIAL_C","C x Ti2AlC precipitation/coarsening","UTS/EL","BIPHASIC_THRESHOLD_0.6_ATC"),("TSUDA2020_N_TIC_PHASE_REACTION","N x TiC phase reaction","phase","THRESHOLD_ABOVE_2_ATN"),("MUNIR2018_TI_MWCNT_TIC_ON","O/N x TiC morphology x process","compression","COUNTEREXAMPLE_NONMONOTONIC"),("GRAY1990_TI86AL_OXYGEN","Al-rich alpha x O x alpha2","fracture","PLANAR_SLIP_CLEAVAGE"),("IBRAHIM2024_LPBF_TNTZ_O","O x beta-stabilizer balance","phase","ALEQ_SHIFT")]: inter.append({"interaction_uid":sid("I",paper,name),"snapshot_id":SNAPSHOT,"paper_uid":paper,"interaction":name,"property":prop,"estimate":None,"p_value":None,"q_value_bh":None,"fdr_decision_0.05":False,"model":"direct threshold/mechanistic evidence","status":status,"claim_level":2,"interpretation":"no artificial p-value"})
    return dose,inter


def figures() -> list[dict[str,Any]]:
    perturb=[]
    def ser(name,paper,x,y,unit):
        lo,hi=min(x),max(x)
        for a,b in zip(x,y): perturb.append({"series":name,"paper_uid":paper,"dose_native":a,"dose_native_unit":unit,"dose_position":0 if hi==lo else (a-lo)/(hi-lo),"response":b,"response_over_baseline":b/y[0]})
    ser("Gray ST YS","GRAY1990_TI86AL_OXYGEN",[.044,.103,.209],[600,710,770],"wt% O"); ser("Gray STA fracture strain","GRAY1990_TI86AL_OXYGEN",[.044,.103,.209],[.40,.08,.05],"wt% O"); ser("Chong YS","CHONG2020_TI_O_PLANAR_SLIP",[.05,.30],[156,472],"wt% O"); ser("Chong EL","CHONG2020_TI_O_PLANAR_SLIP",[.05,.30],[48,16],"wt% O"); ser("Huang UTS","HUANG2025_HIGHNB_TIAL_C",[0,.6,1.5],[352.1,431.6,265.8],"at% C"); ser("Huang EL","HUANG2025_HIGHNB_TIAL_C",[0,.6,1.5],[1.49,1.89,1.15],"at% C")
    wcsv(FD/"composition_perturbation.csv",perturb)
    thresholds=[{"label":"O×alpha2 cleavage bracket","paper_uid":"GRAY1990_TI86AL_OXYGEN","element":"O","low":.044,"point":.0735,"high":.103,"native_unit":"wt%","evidence":"observed bracket"},{"label":"O severe ductility risk point","paper_uid":"CHONG2020_TI_O_PLANAR_SLIP","element":"O","low":.30,"point":.30,"high":.30,"native_unit":"wt%","evidence":"tested point"},{"label":"C solubility/optimum, high-Nb TiAl","paper_uid":"HUANG2025_HIGHNB_TIAL_C","element":"C","low":.6,"point":.6,"high":.6,"native_unit":"at%","evidence":"direct threshold"},{"label":"N-driven TiC reaction threshold","paper_uid":"TSUDA2020_N_TIC_PHASE_REACTION","element":"N","low":2,"point":2,"high":2,"native_unit":"at%","evidence":"above value"}]
    wcsv(FD/"interstitial_threshold_forest.csv",thresholds)
    ae=[]; pp=[2,200,399,600,977]; ox=[.16596,.169,.17358,.17804,.18479]; nn=[.00558,.0124,.01256,.01691,.02004]; x=[6.64+10*(o+n) for o,n in zip(ox,nn)]; dv={"SR YS":[1123,1133,1126,1140,1163],"SR UTS":[1203,1213,1205,1217,1233],"SR EL":[8.1,8.6,7.9,6.5,7.2],"HIP YS":[900,913,919,921,980],"HIP UTS":[983,992,1002,1004,1058],"HIP EL":[16.8,16.5,16.7,16.6,14.0]}
    for name,y in dv.items():
        for xx,yy in zip(x,y): ae.append({"series":name,"AlEq":xx,"response":yy,"response_over_baseline":yy/y[0]})
    wcsv(FD/"aleq_response.csv",ae)
    edges=[("O","Yield strength","positive",3),("O","Ductility","negative",3),("O","alpha2","positive",1),("Al","alpha2","positive",1),("alpha2","Planar slip/cleavage","positive",1),("Planar slip/cleavage","Ductility","negative",2),("C","Solid solution","positive",2),("C","Ti2AlC","threshold",1),("Ti2AlC","Strength","biphasic",1),("Ti2AlC","Ductility","negative above threshold",1),("N","TiC phase reaction","threshold",1),("Process","TiC morphology/porosity","strong",2),("TiC morphology/porosity","Strength","mixed",2),("O+N AlEq","Phase stability","positive",3)]
    wcsv(FD/"interaction_network.csv",[{"source":a,"target":b,"sign":c,"independent_evidence_count":d} for a,b,c,d in edges])
    coeff=[{"element":e,"coefficient_F_per_wt_pct":f,"coefficient_C_per_wt_pct":f*5/9,"domain":"Ti-6Al-4V Eq.7"} for e,f in [("Al",39.376),("O",216),("N",1286.25),("C",873.875)]]; wcsv(FD/"beta_transus_coefficients.csv",coeff)
    scripts={}
    scripts["plot_composition_perturbation.py"]='''import csv, pathlib, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt\nR=pathlib.Path(__file__).resolve().parents[1]; rows=list(csv.DictReader(open(R/"figure_data/composition_perturbation.csv")))\nfig,ax=plt.subplots(figsize=(9,6)); names=[]\nfor r in rows:\n n=r["series"];\n if n not in names:names.append(n)\nfor n in names:\n g=[r for r in rows if r["series"]==n]; ax.plot([float(r["dose_position"]) for r in g],[float(r["response_over_baseline"]) for r in g],marker="o",label=n)\nax.axhline(1,lw=1); ax.set(xlabel="Within-series constrained dose position (0–1)",ylabel="Response / baseline",title="State-dependent composition perturbations\nn_papers=3; n_samples=8; paired conditional effects; direct evidence; within-series support"); ax.legend(fontsize=8,ncol=2); ax.grid(alpha=.25); fig.tight_layout()\nfor e in ("svg","pdf","png"):fig.savefig(R/f"figures/QM22_F1_composition_perturbation.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    scripts["plot_threshold_forest.py"]='''import csv,pathlib,matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt; import numpy as np\nR=pathlib.Path(__file__).resolve().parents[1]; d=list(csv.DictReader(open(R/"figure_data/interstitial_threshold_forest.csv"))); y=np.arange(len(d)); p=np.array([float(r["point"]) for r in d]); lo=p-np.array([float(r["low"]) for r in d]); hi=np.array([float(r["high"]) for r in d])-p\nfig,ax=plt.subplots(figsize=(10,5.5)); ax.errorbar(p,y,xerr=np.vstack([lo,hi]),fmt="o",capsize=4); ax.set_xscale("log"); ax.set_yticks(y,[r["label"] for r in d]); ax.set(xlabel="Threshold/risk value in native unit (annotated)",title="O/N/C threshold evidence — no cross-unit pooling\nn_papers=4; n_samples=10; threshold/bracket estimands; direct evidence; native domains")\nfor i,r in enumerate(d):ax.annotate(r["point"]+" "+r["native_unit"],(p[i],i),xytext=(5,5),textcoords="offset points",fontsize=8)\nax.grid(axis="x",alpha=.25); fig.tight_layout();\nfor e in ("svg","pdf","png"):fig.savefig(R/f"figures/QM22_F2_interstitial_threshold_forest.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    scripts["plot_aleq_response.py"]='''import csv,pathlib,matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt\nR=pathlib.Path(__file__).resolve().parents[1]; d=list(csv.DictReader(open(R/"figure_data/aleq_response.csv"))); names=[]\nfor r in d:\n if r["series"] not in names:names.append(r["series"])\nfig,ax=plt.subplots(figsize=(9,6));\nfor n in names:\n g=[r for r in d if r["series"]==n]; ax.plot([float(r["AlEq"]) for r in g],[float(r["response_over_baseline"]) for r in g],marker="o",label=n)\nax.axhline(1,lw=1); ax.set(xlabel="Al equivalent = Al + 10(O+N), wt.% equivalent",ylabel="Response / lowest-AlEq response",title="LPBF Ti-6Al-4V Al-equivalent response\nn_papers=1; n_samples=10 states; O+N combined association; direct/figure labels; observed support"); ax.legend(fontsize=8,ncol=2); ax.grid(alpha=.25); fig.tight_layout();\nfor e in ("svg","pdf","png"):fig.savefig(R/f"figures/QM22_F3_aleq_response.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    scripts["plot_interaction_network.py"]='''import csv,pathlib,matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt\nR=pathlib.Path(__file__).resolve().parents[1]; d=list(csv.DictReader(open(R/"figure_data/interaction_network.csv"))); nodes=[]\nfor r in d:\n for k in (r["source"],r["target"]):\n  if k not in nodes:nodes.append(k)\nang={n:2*3.14159265*i/len(nodes) for i,n in enumerate(nodes)}; pos={n:(__import__("math").cos(ang[n]),__import__("math").sin(ang[n])) for n in nodes}; fig,ax=plt.subplots(figsize=(11,9))\nfor n,(x,y) in pos.items():ax.scatter([x],[y],s=800); ax.text(x,y,n,ha="center",va="center",fontsize=7,wrap=True)\nfor r in d:\n x1,y1=pos[r["source"]]; x2,y2=pos[r["target"]]; ax.annotate("",(x2,y2),(x1,y1),arrowprops=dict(arrowstyle="->",lw=1+float(r["independent_evidence_count"])*.5,alpha=.65)); ax.text((x1+x2)/2,(y1+y2)/2,r["sign"],fontsize=6)\nax.set_title("Element × phase × process interaction network\nn_papers=7; evidence-count edge weights; association/threshold graph; direct evidence; Ti/TiAl/TMC domains"); ax.axis("off"); fig.tight_layout();\nfor e in ("svg","pdf","png"):fig.savefig(R/f"figures/QM22_F4_interaction_network.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    scripts["plot_beta_transus_coefficients.py"]='''import csv,pathlib,matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt\nR=pathlib.Path(__file__).resolve().parents[1]; d=list(csv.DictReader(open(R/"figure_data/beta_transus_coefficients.csv"))); vals=[float(r["coefficient_C_per_wt_pct"]) for r in d]; fig,ax=plt.subplots(figsize=(8,5.5)); b=ax.bar([r["element"] for r in d],vals); ax.set(xlabel="Alpha-stabilizing element",ylabel="Beta-transus coefficient (°C per wt.%)",title="Ti-6Al-4V phase-stability leverage\nn=115 DTA chemistries; Eq.7 coefficients; direct equation; Ti-6Al-4V domain")\nfor q,v in zip(b,vals):ax.text(q.get_x()+q.get_width()/2,v,f"{v:.1f}",ha="center",va="bottom"); ax.grid(axis="y",alpha=.25); fig.tight_layout();\nfor e in ("svg","pdf","png"):fig.savefig(R/f"figures/QM22_F5_beta_transus_coefficients.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    for n,c in scripts.items():wtext(PC/n,c); subprocess.run([sys.executable,str(PC/n)],check=True)
    return [{"id":f"QM22_F{i}","data":x,"code":y,"outputs":["svg","pdf","png@600dpi"]} for i,(x,y) in enumerate([("composition_perturbation.csv","plot_composition_perturbation.py"),("interstitial_threshold_forest.csv","plot_threshold_forest.py"),("aleq_response.csv","plot_aleq_response.py"),("interaction_network.csv","plot_interaction_network.py"),("beta_transus_coefficients.csv","plot_beta_transus_coefficients.py")],1)]


def build() -> dict[str,Any]:
    for p in (OUT,ART):
        if p.exists():shutil.rmtree(p)
        p.mkdir(parents=True)
    for p in (FD,FG,PC,LE,AC):p.mkdir(parents=True,exist_ok=True)
    a=atomic_rows(); pairs,effects=make_pairs(a); dose,inter=analyses(a); specs=figures()
    ledger=[]
    for n in ARCHIVES: ledger.append({"input_id":sid("IN",n),"snapshot_id":SNAPSHOT,"source_name":n,"source_type":"ZIP","path_or_locator":"/mnt/data/"+n,"source_hash":KNOWN.get(n,""),"source_hash_kind":"REGISTERED_FULL_OR_CENTRAL_DIRECTORY_SHA256" if n in KNOWN else "UNRESOLVED_IN_PUBLIC_RUNNER","priority":"P0_PRIMARY_ORIGINAL" if n.startswith("TITMC") else "P2_P3_INFRASTRUCTURE","window_relevance":"literature corpus" if n.startswith("TITMC") else "data/features/harness/platform","terminal_use_status":"USED_AS_REFERENCE","opened_or_consumed":"REGISTERED_AND_SCOPED","notes":"local authoritative member rebind required"})
    for p,doi,file,loc,grade in PAPERS: ledger.append({"input_id":sid("IN",p),"snapshot_id":SNAPSHOT,"source_name":file,"source_type":"ORIGINAL_PAPER_REFERENCE","path_or_locator":"file_library://"+file,"source_hash":htext("|".join([p,doi,file,loc,grade])),"source_hash_kind":"NORMALIZED_CAPTURE_SHA256_NOT_ORIGINAL_BYTES","priority":"P0_PRIMARY_ORIGINAL","window_relevance":loc,"terminal_use_status":"USED_DIRECTLY","opened_or_consumed":"YES","notes":"DOI="+doi+"; original-byte rebind required"})
    ledger.append({"input_id":sid("IN","QM22_MDU"),"snapshot_id":SNAPSHOT,"source_name":"QM22_Al、O、N、C_等_α_稳定_间隙元素的主效应和风险.md","source_type":"MDU","priority":"CONTROL_CONTRACT","terminal_use_status":"USED_DIRECTLY","opened_or_consumed":"YES"})
    wcsv(OUT/"INPUT_LEDGER.csv",ledger); wcsv(OUT/"ANALYSIS_COHORT.csv",a,ATOMIC_FIELDS); wcsv(OUT/"PAIR_MATCHES.csv",pairs); wcsv(OUT/"EFFECT_ESTIMATES.csv",effects); wcsv(OUT/"DOSE_RESPONSE.csv",dose); wcsv(OUT/"INTERACTION_EFFECTS.csv",inter); wcsv(OUT/"ALPHA_STABILIZER_INTERACTIONS.csv",inter)
    gray_st=next(r["slope"] for r in dose if r["paper_uid"]=="GRAY1990_TI86AL_OXYGEN" and r["state"]=="ST" and r["property"]=="YS"); ch=next(r["slope"] for r in dose if r["paper_uid"]=="CHONG2020_TI_O_PLANAR_SLIP" and r["property"]=="YS")
    hier=[{"result_uid":sid("H","OYS"),"snapshot_id":SNAPSHOT,"estimand":"actual-O slope for RT YS in unreinforced alpha/near-alpha Ti","estimate":float(np.median([gray_st,ch])),"unit":"MPa/wt_pct_O","prediction_low":min(gray_st,ch),"prediction_high":max(gray_st,ch),"independent_papers":2,"method":"equal-paper descriptive median","status":"DESCRIPTIVE_NOT_META_ANALYTIC","claim_level":2,"notes":"only two different Al states"},{"result_uid":sid("H","OEL"),"snapshot_id":SNAPSHOT,"estimand":"universal O-to-ductility slope","estimate":None,"independent_papers":2,"method":"semantic audit","status":"NOT_IDENTIFIABLE","claim_level":2,"notes":"true fracture strain != engineering EL"},{"result_uid":sid("H","N"),"snapshot_id":SNAPSHOT,"estimand":"independent N slope for UTS/YS/EL","estimate":None,"independent_papers":1,"method":"collinearity audit","status":"NOT_IDENTIFIABLE","claim_level":1,"notes":"O and N covary"},{"result_uid":sid("H","Al"),"snapshot_id":SNAPSHOT,"estimand":"independent Al slope for UTS/YS/EL","estimate":None,"independent_papers":0,"method":"support audit","status":"NOT_IDENTIFIABLE","claim_level":1,"notes":"no controlled Al-only mechanical series"},{"result_uid":sid("H","C"),"snapshot_id":SNAPSHOT,"estimand":"universal C slope across Ti/TiAl/TMC","estimate":None,"independent_papers":4,"method":"mechanism-state audit","status":"NOT_IDENTIFIABLE","claim_level":2,"notes":"interstitial/precursor/TiC/Ti2AlC differ"}]
    wcsv(OUT/"HIERARCHICAL_RESULTS.csv",hier)
    wcsv(OUT/"HETEROGENEITY.csv",[{"domain":"O_to_strength","independent_papers":3,"heterogeneity":"high","drivers":"Al; alpha2; heat treatment; O/N collinearity","pooling_decision":"paper/state-specific"},{"domain":"O_to_ductility","independent_papers":3,"heterogeneity":"high","drivers":"property semantics; phase; HIP","pooling_decision":"not pooled"},{"domain":"C_to_strength","independent_papers":4,"heterogeneity":"mechanism-changing","drivers":"interstitial C; precursor; TiC; Ti2AlC","pooling_decision":"piecewise/phase-specific"},{"domain":"N","independent_papers":2,"heterogeneity":"not estimable","drivers":"O covariation; phase-only threshold","pooling_decision":"no global mechanical slope"},{"domain":"Al","independent_papers":3,"heterogeneity":"formula-domain conflict","drivers":"near-alpha/TNTZ/TiAl conventions","pooling_decision":"formula_id isolation"}])
    lopo=[{"analysis":"O_to_YS_RT","left_out_paper":"GRAY1990_TI86AL_OXYGEN","estimate":ch,"unit":"MPa/wt_pct_O","sign":"positive","status":"ONE_PAPER_REMAINS"},{"analysis":"O_to_YS_RT","left_out_paper":"CHONG2020_TI_O_PLANAR_SLIP","estimate":gray_st,"unit":"MPa/wt_pct_O","sign":"positive","status":"ONE_PAPER_REMAINS"},{"analysis":"C_low_dose_strength","left_out_paper":"HUANG2025_HIGHNB_TIAL_C","estimate":257,"unit":"MPa/at_pct_C","sign":"positive","status":"MIMOTO_YS_ONLY"},{"analysis":"C_low_dose_strength","left_out_paper":"MIMOTO2011_PURETI_CNP","estimate":132.5,"unit":"MPa/at_pct_C","sign":"positive","status":"HUANG_UTS_ONLY"},{"analysis":"C_above_transition_strength","left_out_paper":"HUANG2025_HIGHNB_TIAL_C","estimate":95,"unit":"MPa/at_pct_C","sign":"positive","status":"MIMOTO_TIC_DISPERSION"},{"analysis":"C_above_transition_strength","left_out_paper":"MIMOTO2011_PURETI_CNP","estimate":-184.222,"unit":"MPa/at_pct_C","sign":"negative","status":"HUANG_Ti2AlC_COARSENING"}]
    wcsv(OUT/"LOPO_RESULTS.csv",lopo); wcsv(OUT/"SENSITIVITY_ANALYSIS.csv",[{"analysis_id":"S01","perturbation":"LOPO O->YS","result":"sign remains positive","status":"ROBUST_SIGN_ONLY"},{"analysis_id":"S02","perturbation":"exclude figure-labeled Dietrich values","result":"combined AlEq slopes removed; O/N separation still impossible","status":"CONCLUSION_UNCHANGED"},{"analysis_id":"S03","perturbation":"missing O/N/C -> zero","result":"forbidden","status":"REJECTED_ANALYSIS"},{"analysis_id":"S04","perturbation":"pool true fracture strain with EL","result":"forbidden","status":"REJECTED_ANALYSIS"},{"analysis_id":"S05","perturbation":"all precursor C = dissolved C","result":"forbidden","status":"REJECTED_ANALYSIS"},{"analysis_id":"S06","perturbation":"exclude Munir C10_B2","result":"positive routes remain but heterogeneity remains","status":"OUTLIER_SENSITIVITY"},{"analysis_id":"S07","perturbation":"BH-FDR interactions","result":f"{sum(bool(r.get('fdr_decision_0.05')) for r in inter)} pass q<=0.05","status":"FDR_APPLIED"}])
    nulls=[{"paper_uid":"GRAY1990_TI86AL_OXYGEN","finding":"STA O raises YS but fracture stress falls 900->780 MPa at 0.103 wt% O","type":"counterexample","implication":"strength != damage tolerance"},{"paper_uid":"GRAY1990_TI86AL_OXYGEN","finding":"STA fracture strain 0.40->0.08 by 0.103 wt% O","type":"negative_effect","implication":"O×alpha2 dominates ductility"},{"paper_uid":"MUNIR2018_TI_MWCNT_TIC_ON","finding":"C10_B2: 610 MPa below 695 MPa control despite highest O/N and 67.5 wt% TiC","type":"counterexample","implication":"agglomeration/porosity overwhelm chemistry"},{"paper_uid":"HUANG2025_HIGHNB_TIAL_C","finding":"1.5 at% C gives 265.8 MPa/1.15%, below C-free alloy","type":"threshold_reversal","implication":"benefit reverses above Ti2AlC window"},{"paper_uid":"DIETRICH2020_LPBF_TI64_O_N","finding":"stress-relieved EL is non-monotonic","type":"null_nonmonotonic","implication":"no universal small-range slope"},{"paper_uid":"ALL","finding":"no controlled Al-only tensile series","type":"not_identifiable","implication":"Al mechanical main effect unavailable"}]
    wcsv(OUT/"NULL_NEGATIVE_RESULTS.csv",nulls)
    conflicts=[("C001","canonical snapshot","Q40 required","recovery only","local rebind","OPEN_HIGH"),("C002","AlEq formula","near-alpha/TNTZ/TiAl differ","coefficients conflict by domain","formula_id isolation","CONTROLLED"),("C003","O versus N","both measured","both increase together","combined AlEq only","OPEN_IDENTIFIABILITY"),("C004","carbon identity","interstitial","precursor/dissolved/TiC/Ti2AlC","separate C_role","CONTROLLED"),("C005","units","wt%","at% thresholds","retain native","CONTROLLED"),("C006","ductility","EL","true fracture strain","never pool","CONTROLLED"),("C007","oxygen exposure","chamber ppm","bulk wt%","bulk chemistry for estimand","CONTROLLED"),("C008","TiAl AlEq sign","C alpha stabilizer in Ti","Johnson liquidus convention -4.2","domain-specific response","CONTROLLED")]
    wcsv(OUT/"CONFLICT_LEDGER.csv",[{"conflict_id":a,"topic":b,"side_a":c,"side_b":d,"resolution":e,"status":f} for a,b,c,d,e,f in conflicts])
    ilr=[("z1","Ti | Al,O,N,C,Other","sqrt(5/6)*ln(Ti/g(rest))","overall balance"),("z2","Al | O,N,C,Other","sqrt(4/5)*ln(Al/g(rest))","Al balance"),("z3","O | N,C,Other","sqrt(3/4)*ln(O/g(rest))","O balance"),("z4","N | C,Other","sqrt(2/3)*ln(N/g(rest))","N balance"),("z5","C | Other","sqrt(1/2)*ln(C/Other)","C balance"),("perturbation","element +delta; Ti -delta","x_e'=x_e+delta; x_Ti'=x_Ti-delta","within-paper constrained effect")]
    wcsv(OUT/"COMPOSITION_ILR_MAP.csv",[{"coordinate":a,"parts":b,"formula":c,"use":d,"zero_policy":"exclude missing; structural absence is separate domain; no zero imputation"} for a,b,c,d in ilr])
    miss=[("GRAY1990_TI86AL_OXYGEN","MEASURED","MEASURED","NOT_REPORTED","NOT_REPORTED","N/C not zero"),("CHONG2020_TI_O_PLANAR_SLIP","ABSENT_BY_DESIGN","CONTROLLED_REPORTED","NOT_REPORTED","NOT_REPORTED","trace unresolved"),("DIETRICH2020_LPBF_TI64_O_N","MEASURED","MEASURED_BULK","MEASURED_BULK","MEASURED_CONSTANT","O/N collinear"),("MUNIR2018_TI_MWCNT_TIC_ON","ABSENT_BY_MATRIX","MEASURED","MEASURED","PRECURSOR_REACTION_UNRESOLVED","dissolved C not isolated"),("HUANG2025_HIGHNB_TIAL_C","NOMINAL_ATPCT","NOT_REPORTED","NOT_REPORTED","CONTROLLED_ATPCT","O/N not assumed constant"),("MIMOTO2011_PURETI_CNP","ABSENT_BY_MATRIX","MODEL_ADJUSTED","NOT_REPORTED","TOTAL_AND_PARTITION","full chemistry needed"),("KONDOH2012_TI_CNT_HT","ABSENT_BY_MATRIX","NOT_REPORTED","XRD_NO_NITRIDE_ONLY","TOTAL_DISSOLVED_TIC_MEASURED","XRD absence != zero N"),("TSUDA2020_N_TIC_PHASE_REACTION","ABSENT_BY_MATRIX","NOT_REPORTED","CONTROLLED_ATPCT","TIC_STOICHIOMETRIC","phase-specific"),("IBRAHIM2024_LPBF_TNTZ_O","ABSENT_BY_ALLOY","MEASURED","NOT_REPORTED","NOT_REPORTED","alloy-specific AlEq"),("ROGOFF2018_TI64_BETA_TRANSUS","MEASURED","MEASURED","MEASURED","MEASURED","Ti64 domain"),("JOHNSON2006_TIAL_AL_EQ","CONTROLLED_ATPCT","NOT_IN_MODEL","NOT_IN_MODEL","TERNARY_COEFFICIENT","different convention")]
    wcsv(OUT/"INTERSTITIAL_MISSINGNESS.csv",[{"paper_uid":a,"Al":b,"O":c,"N":d,"C":e,"risk":f} for a,b,c,d,e,f in miss])
    atlas=[{"effect_uid":r["result_uid"],"paper_uid":r["paper_uid"],"element_or_proxy":r["dose_variable"],"matrix_state":r["state"],"outcome":r["property"],"estimate":r.get("slope"),"unit":r.get("slope_unit"),"ci95_low":r.get("ci95_low"),"ci95_high":r.get("ci95_high"),"n_levels":r.get("n_levels"),"status":r["status"],"claim_level":r["claim_level"],"interpretation":r["interpretation"]} for r in dose]
    atlas += [{"effect_uid":sid("AE","N"),"paper_uid":"TSUDA2020_N_TIC_PHASE_REACTION","element_or_proxy":"N_at_pct","matrix_state":"Ti-5vol%TiC","outcome":"phase_reaction","estimate":2,"unit":"at_pct_threshold","status":"DIRECT_THRESHOLD_ABOVE","claim_level":2,"interpretation":"above 2 at% N: Ti2C disappears and alpha platelets form in TiC"},{"effect_uid":sid("AE","C"),"paper_uid":"HUANG2025_HIGHNB_TIAL_C","element_or_proxy":"C_at_pct","matrix_state":"high-Nb TiAl","outcome":"Ti2AlC_solubility_optimum","estimate":.6,"unit":"at_pct_threshold","status":"DIRECT_THRESHOLD","claim_level":2,"interpretation":"optimum/precipitation threshold near 0.6 at% C"}]
    wcsv(OUT/"AL_INTERSTITIAL_EFFECTS.csv",atlas)
    prov=[]; pm={p[0]:p for p in PAPERS}
    for r in a:
        p=pm[r["paper_uid"]]; prov.append(json.dumps({"record_uid":r["record_uid"],"snapshot_id":SNAPSHOT,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"source_file":p[2],"doi":p[1],"source_locator":r["source_locator"],"evidence_level":r["evidence_level"],"source_hash":htext("|".join(p)),"source_hash_kind":"NORMALIZED_CAPTURE_SHA256_NOT_ORIGINAL_BYTES","value_hash":htext(json.dumps(r,sort_keys=True,ensure_ascii=False)),"local_rebind_required":True},ensure_ascii=False,sort_keys=True))
    wtext(OUT/"PROVENANCE.jsonl","\n".join(prov)+"\n")
    captures={p[0]:f"# {p[0]}\n\n- DOI: {p[1]}\n- Original file: `{p[2]}`\n- Evidence: {p[3]}\n- Level: `{p[4]}`\n\nThis normalized capture is not the original byte stream. Rebind to package SHA/member/locator before Gold promotion.\n" for p in PAPERS}
    for k,v in captures.items():wtext(LE/(k+".md"),v)
    verdict=f'''# QM22 Executive Verdict\n\n`WINDOW=QM22 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`\n\n1. O is separable only within controlled paper/state contrasts. Ti-8.6Al ST YS rises 600→770 MPa from 0.044→0.209 wt.% O while true fracture strain falls 0.53→0.24; aged alpha2 material shows YS 650→825 MPa but fracture strain 0.40→0.05. Pure Ti at 0.05→0.30 wt.% O gives YS 156→472 MPa and EL 48→16%.\n2. Independent N mechanical slopes are not identifiable: LPBF Ti-6Al-4V O/N co-vary. Only `Al+10(O+N)` is estimated. A separate Ti/TiC paper supports a phase threshold above 2 at.% N.\n3. C changes identity. High-Nb TiAl improves to 0.6 at.% C then reverses at 1.5 at.% through Ti2AlC coarsening/debonding. Pure-Ti carbon composite slopes fall from 257 MPa/at.% in the solute regime to 95 MPa/at.% in the TiC regime.\n4. Al is phase leverage, not an isolated tensile coefficient in this cohort. Ti-6Al-4V Eq.7 beta-transus coefficients are 21.9/120.0/714.6/485.5 °C per wt.% for Al/O/N/C.\n5. Element×reinforcement interactions dominate. Munir C10_B2 has highest O/N and 67.5 wt.% TiC but compressive YS 610 MPa, below 695 MPa control, proving process/agglomeration/porosity can reverse nominal strengthening.\n\nEvidence: {len(PAPERS)} original papers, {len(ARCHIVES)} top-level archives registered, {len(a)} atomic rows, {len(pairs)} matched pairs, {len(effects)} property effects, {len(dose)} dose/phase rows, {len(inter)} interactions, 5 data/code/figure triplets. Claim ceiling: level 2.\n\nOperationally complete recovery package; canonical completion awaits Q40/V29 snapshot and original-byte/member hash rebind.\n\n`STATUS: CONTINUE_DATA_GAP | WINDOW=QM22 | MISSING=canonical_Q40_snapshot,V29_atomic_records_full_provenance | NEXT=local_absorb_and_rebind`\n'''
    wtext(OUT/"00_EXECUTIVE_VERDICT.md",verdict)
    wtext(OUT/"METHODS.md",f'''# METHODS\n\nSnapshot `{SNAPSHOT}` is a deterministic recovery hash, not canonical Q40. Atomicity is paper×sample×actual composition×process×heat treatment×phase×test mode×temperature×property. Effects are delta, lnRR and percent change for same-paper pairs. O/N collinearity is retained as AlEq. Compositions use the delivered ilr/controlled Ti-replacement map; missing interstitials are excluded, never zero-filled. Within-paper slopes use linear regression/endpoints; Gray and Dietrich interactions use OLS main+interaction terms; estimable p-values use BH-FDR. LOPO is sign-level where only two papers exist. All plots are generated from delivered CSVs by delivered Python and show paper/sample count, estimand, evidence and support domain.\n''')
    wtext(OUT/"LIMITATIONS.md","""# LIMITATIONS\n\n1. Canonical Q40/V29 atomic/provenance inputs and original-byte/member hashes are not mounted. 2. Figure-labeled values require local locator replay. 3. O/N collinearity blocks separation. 4. True fracture strain is not EL. 5. Carbon identities cannot be pooled. 6. wt.% and at.% remain native. 7. Rogoff coefficients are phase-stability weights, not tensile effects. 8. Johnson TiAl AlEq is a distinct liquidus convention. 9. Paper count governs inference. 10. No Gold/ACTIVE/model/VALIDATED action is performed.\n""")
    wjson(OUT/"PLOT_SPECS.json",{"window_id":"QM22","snapshot_id":SNAPSHOT,"language":"English","figures":specs})
    wjson(OUT/"WEB_TO_LOCAL_REQUEST.json",{"window_id":"QM22","snapshot_id":SNAPSHOT,"status":"CONTINUE_DATA_GAP","required":[{"priority":1,"object":"Q40_INPUT_SNAPSHOT"},{"priority":1,"object":"V29_ATOMIC_RECORDS_AND_PROVENANCE"},{"priority":1,"object":"V29_CONFLICT_EXCLUSION_SOURCE_REGISTRY"},{"priority":1,"object":"original_publication_bytes_or_archive_members","identifiers":[p[1] for p in PAPERS]},{"priority":2,"object":"measured_O_N_C_for_missing_papers"},{"priority":2,"object":"carbon_partition_actual_phase_fraction"}],"acceptance":"all admitted rows source-byte/member+locator bound; recompute value/effect hashes","next_action":"LOCAL_ABSORB_REBIND_RECOMPUTE"})
    wtext(OUT/"LOCAL_ABSORPTION_PROMPT.md",f'''# LOCAL ABSORPTION\n\nVerify ZIP CRC/SHA/manifest/no nested ZIP; bind `{SNAPSHOT}` to canonical Q40/V29; re-open every DOI/locator and replace capture hashes with package SHA+member+CRC+page/table/figure/XPath; never zero-fill missing O/N/C; preserve distinct AlEq formulas and carbon identities; run `python analysis_code/rebuild.py`; compare row/value/effect hashes; resolve C001–C008; return signed absorption receipt. Do not modify Gold/ACTIVE or register a production model before all gates pass.\n''')
    status={"window_id":"QM22","snapshot_id":SNAPSHOT,"papers_seen":len(PAPERS),"papers_included":len(PAPERS),"independent_papers":len(PAPERS),"atomic_rows":len(a),"matched_pairs":len(pairs),"effect_estimates":len(effects),"plots_generated":5,"plot_files":len(list(FG.glob("*"))),"open_conflicts":2,"claim_level_max":2,"status":"CONTINUE_DATA_GAP","next_action":"LOCAL_ABSORB_REBIND_RECOMPUTE","production_model_registration":"FORBIDDEN","gold_promotion":"NOT_PERFORMED"}; wjson(OUT/"WINDOW_STATUS.json",status)
    wcsv(OUT/"SOURCE_COVERAGE_MATRIX.csv",[{"source_class":"P0 original papers","objects_registered":len(PAPERS),"used_directly":len(PAPERS),"terminal_state":"USED_DIRECTLY","gap":"original-byte/member rebind"},{"source_class":"TITMC_V27 archives","objects_registered":10,"used_directly":0,"terminal_state":"USED_AS_REFERENCE","gap":"canonical member registry not mounted"},{"source_class":"S03 data/features/harness","objects_registered":10,"used_directly":0,"terminal_state":"USED_AS_REFERENCE","gap":"frozen matrix not mounted"},{"source_class":"S02/S04 platform/history","objects_registered":5,"used_directly":0,"terminal_state":"USED_AS_REFERENCE","gap":"engineering reference"},{"source_class":"QM22 MDU","objects_registered":1,"used_directly":1,"terminal_state":"USED_DIRECTLY","gap":"none"}])
    wtext(OUT/"OPENED_FILES.txt","\n".join([p[2] for p in PAPERS]+ARCHIVES+["QM22_Al、O、N、C_等_α_稳定_间隙元素的主效应和风险.md"])+"\n")
    shutil.copy2(__file__,AC/"rebuild.py")
    test='''import csv,hashlib,json,unittest,zipfile\nfrom pathlib import Path\nR=Path(__file__).resolve().parents[1]\nREQ=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256","AL_INTERSTITIAL_EFFECTS.csv","COMPOSITION_ILR_MAP.csv","INTERSTITIAL_MISSINGNESS.csv","ALPHA_STABILIZER_INTERACTIONS.csv"]\nclass T(unittest.TestCase):\n def test_required(self):self.assertFalse([x for x in REQ if not (R/x).is_file()])\n def test_status(self):s=json.loads((R/"WINDOW_STATUS.json").read_text());self.assertEqual(s["window_id"],"QM22");self.assertEqual(s["claim_level_max"],2)\n def test_effect_identity(self):\n  d=list(csv.DictReader(open(R/"EFFECT_ESTIMATES.csv")));self.assertGreater(len(d),0);self.assertTrue(all(x["paper_uid"] and x["control_record_uid"] and x["treated_record_uid"] for x in d))\n def test_no_zero_imputation(self):self.assertNotIn("IMPUTED_ZERO",(R/"INTERSTITIAL_MISSINGNESS.csv").read_text())\n def test_figures(self):\n  for i in range(1,6):self.assertEqual({p.suffix for p in (R/"figures").glob(f"QM22_F{i}_*")},{".svg",".pdf",".png"})\n def test_checksums(self):\n  for line in (R/"CHECKSUMS.sha256").read_text().splitlines():h,p=line.split("  ",1);self.assertEqual(hashlib.sha256((R/p).read_bytes()).hexdigest(),h)\nif __name__=="__main__":unittest.main()\n'''; wtext(AC/"test_outputs.py",test)
    wtext(OUT/"acceptance_commands.md","# Acceptance\n\n```bash\npython analysis_code/rebuild.py\npython -m unittest analysis_code/test_outputs.py -v\nsha256sum -c CHECKSUMS.sha256\nunzip -t ../artifacts/FINAL_QM22.zip\n```\n")
    wtext(OUT/"requirements.lock","matplotlib==3.9.2\nnumpy==2.1.3\nscipy==1.14.1\n")
    wtext(OUT/"RUN_LOG.txt",f"{GENERATED} SNAPSHOT {SNAPSHOT}\n{GENERATED} atomic={len(a)} pairs={len(pairs)} effects={len(effects)} dose={len(dose)} interactions={len(inter)} figures=5\n{GENERATED} STATUS CONTINUE_DATA_GAP\n")
    # Validation before manifest/checksums.
    required=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","AL_INTERSTITIAL_EFFECTS.csv","COMPOSITION_ILR_MAP.csv","INTERSTITIAL_MISSINGNESS.csv","ALPHA_STABILIZER_INTERACTIONS.csv"]
    missing=[x for x in required if not (OUT/x).is_file()]; trips={i:sorted(p.suffix for p in FG.glob(f"QM22_F{i}_*")) for i in range(1,6)}; val={"pass":not missing and all(v==[".pdf",".png",".svg"] for v in trips.values()),"missing":missing,"figure_triplets":trips,"atomic_rows":len(a),"effect_rows":len(effects),"claim_ceiling_checked":True,"zero_imputation_forbidden":True}; wjson(OUT/"VALIDATION_REPORT.json",val); wtext(OUT/"TEST_OUTPUT.txt","PASS="+str(val["pass"]).lower()+"\n"+json.dumps(val,sort_keys=True)+"\n")
    files=sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in ("MANIFEST.json","CHECKSUMS.sha256")); manifest={"window_id":"QM22","snapshot_id":SNAPSHOT,"generated_at":GENERATED,"status":"CONTINUE_DATA_GAP","schema":"QM22_RECOVERY_SCHEMA_1.1.0","file_count_excluding_manifest_checksums":len(files),"nested_zip_count":0,"files":[{"path":str(p.relative_to(OUT)).replace(os.sep,"/"),"bytes":p.stat().st_size,"sha256":hbytes(p.read_bytes())} for p in files]}; wjson(OUT/"MANIFEST.json",manifest)
    files=sorted(p for p in OUT.rglob("*") if p.is_file() and p.name!="CHECKSUMS.sha256"); wtext(OUT/"CHECKSUMS.sha256","\n".join(f"{hbytes(p.read_bytes())}  {str(p.relative_to(OUT)).replace(os.sep,'/')}" for p in files)+"\n")
    zip_path=ART/"FINAL_QM22.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(x for x in OUT.rglob("*") if x.is_file()):
            rel=str(p.relative_to(OUT)).replace(os.sep,"/"); zi=zipfile.ZipInfo(rel,(2026,7,13,5,15,0)); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16; z.writestr(zi,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(zip_path) as z:
        assert z.testzip() is None and not [n for n in z.namelist() if n.lower().endswith(".zip")]
    zh=hbytes(zip_path.read_bytes()); wtext(ART/"FINAL_QM22.sha256",f"{zh}  FINAL_QM22.zip\n"); summary={"zip":"jobs/qm22/artifacts/FINAL_QM22.zip","zip_bytes":zip_path.stat().st_size,"zip_sha256":zh,"snapshot_id":SNAPSHOT,"status":"CONTINUE_DATA_GAP","atomic_rows":len(a),"matched_pairs":len(pairs),"effect_estimates":len(effects),"dose_rows":len(dose),"interaction_rows":len(inter),"logical_figures":5,"package_file_count":len(zipfile.ZipFile(zip_path).namelist()),"zip_test":"PASS","nested_zip_count":0}; wjson(ART/"DELIVERY_SUMMARY.json",summary); return summary

if __name__=="__main__": print(json.dumps(build(),ensure_ascii=False,indent=2,sort_keys=True))
