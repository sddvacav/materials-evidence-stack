from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats

SEED = 20260713
SNAPSHOT = "QM22_RECOVERY_20260713_9f0d0e1a"
STATUS = (
    "STATUS: CONTINUE_DATA_GAP | WINDOW=QM22 | "
    "MISSING=CANONICAL_Q40_V29_ATOMIC_SNAPSHOT,N_ONLY_PRIMARY_SERIES,"
    "DISSOLVED_C_MASS_BALANCE,MATCHED_AL_PERTURBATION | "
    "NEXT=LOCAL_HASH_BIND_AND_TARGETED_SOURCE_RECOVERY"
)
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
PKG = OUT / "FINAL_QM22"


def uid(*x: Any, n: int = 24) -> str:
    return hashlib.sha256("|".join("" if v is None else str(v) for v in x).encode()).hexdigest()[:n]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def text(rel: str, s: str) -> Path:
    p = PKG / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s.rstrip() + "\n", encoding="utf-8")
    return p


def js(rel: str, obj: Any) -> Path:
    return text(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def frame(rel: str, df: pd.DataFrame) -> Path:
    p = PKG / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, lineterminator="\n")
    return p


def linfit(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    r = stats.linregress(x, y)
    dof = max(1, len(x) - 2)
    tc = stats.t.ppf(.975, dof)
    return dict(
        n=len(x), slope_per_wt_pct=float(r.slope), slope_per_0p1wt_pct=float(r.slope * .1),
        ci95_low_per_0p1wt_pct=float((r.slope - tc*r.stderr)*.1),
        ci95_high_per_0p1wt_pct=float((r.slope + tc*r.stderr)*.1),
        intercept=float(r.intercept), r2=float(r.rvalue**2), p_value=float(r.pvalue),
        stderr_per_wt_pct=float(r.stderr),
    )


def ols_interaction(x, g, y):
    x = np.asarray(x, float); g = np.asarray(g, float); y = np.asarray(y, float)
    xc = x - x.mean()
    X = np.column_stack([np.ones(len(x)), xc, g, xc*g])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X@b
    dof = max(1, len(y)-4)
    s2 = float(e@e/dof)
    cov = s2*np.linalg.pinv(X.T@X)
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    t = b/np.where(se>0,se,np.inf)
    p = 2*stats.t.sf(np.abs(t),dof)
    tc = stats.t.ppf(.975,dof)
    return b,se,p,b-tc*se,b+tc*se


def bh(p):
    out=[None]*len(p); idx=[i for i,v in enumerate(p) if v is not None and math.isfinite(float(v))]
    if not idx: return out
    vals=np.array([float(p[i]) for i in idx]); order=np.argsort(vals); rank=vals[order]
    q=np.minimum.accumulate((rank*len(rank)/np.arange(1,len(rank)+1))[::-1])[::-1]
    for k,o in enumerate(order): out[idx[o]]=float(min(1,q[k]))
    return out


def ilr(parts: dict[str,float]):
    names=list(parts); v=np.array([max(float(parts[k]),1e-8) for k in names]); v=v/v.sum(); z=[]; basis=[]
    for j in range(len(v)-1):
        right=v[j+1:]; c=math.sqrt(len(right)/(len(right)+1)); gm=float(np.exp(np.mean(np.log(right))))
        z.append(float(c*math.log(v[j]/gm)))
        basis.append(f"sqrt({len(right)}/{len(right)+1})*ln({names[j]}/gmean({'+'.join(names[j+1:])}))")
    return z,{k:float(x) for k,x in zip(names,v)},"; ".join(basis)


def reset():
    if OUT.exists(): shutil.rmtree(OUT)
    for d in [PKG, PKG/"source_evidence", PKG/"figure_data", PKG/"plot_code", PKG/"figures", PKG/"analysis_code", PKG/"tests"]:
        d.mkdir(parents=True, exist_ok=True)


def sources():
    d = {
      "OH2011": ("10.1007/s12540-011-1006-2", "DIRECT_TABLE_TEXT", "CP Ti and Ti-6Al-4V measured-O series; HV/UTS/EL table."),
      "XIANG2020": ("10.1016/j.matchar.2020.110681", "DIRECT_TABLE_TEXT", "Measured Ti-Zr-O composition, UTS/YS/EL, beta transus and lattice parameters."),
      "DIETRICH2020": ("10.1016/j.addma.2019.100980", "FIGURE_DERIVED_ANNOTATED", "LPBF Ti-6Al-4V O/N atmosphere series; stress-relieved and HIP values."),
      "WANG2025": ("10.1016/j.carbon.2024.119884", "DIRECT_TABLE_TEXT", "0.20 wt.% C-coated Ti precursor forming Ti8C5; tensile/compression/grain-size anchors."),
      "GARDNER2021": ("10.1557/s43578-020-00006-3", "DIRECT_TEXT_MECHANISM", "TIMETAL834 alpha-case O x microstructure/orientation hardening mechanism."),
      "JOHNSON2006": ("10.1016/j.actamat.2005.10.040", "DIRECT_TABLE_TEXT", "TiAl directional-solidification Al-equivalent coefficients; separate at.% domain."),
      "TNTZ2024": ("10.1016/j.msea.2024.146617", "DIRECT_TABLE_TEXT", "LPBF TNTZ O/Zr and O-only AlEq descriptor."),
      "RASTEGARI2013": ("MSEA_564_473_477", "DIRECT_TEXT_APPROXIMATE", "Ti64/TiC+TiB process/morphology interaction; approximate tensile anchor."),
    }
    result={}
    for k,(doi,level,note) in d.items():
        s=f"# {k} normalized evidence capture\n\nDOI/locator: {doi}\nEvidence: {level}\nRole: {note}\nOriginal publication byte hash must be re-bound locally.\n"
        p=text(f"source_evidence/{k}.md",s)
        result[k]={"doi":doi,"level":level,"note":note,"path":str(p.relative_to(PKG)),"hash":sha(p)}
    return result


def build_atomic(src):
    rows=[]
    def add(paper,sample,condition,matrix,process,ht,prop,val,unit,comp,mode="tension",reinforcement="NONE",dose_element="NONE",dose=None,notes=""):
        pu=uid(src[paper]["doi"]); su=uid(pu,sample); cu=uid(su,condition,prop,mode); ru=uid(cu,val,unit)
        rows.append(dict(snapshot_id=SNAPSHOT,row_uid=ru,paper_uid=pu,paper_key=paper,doi_or_locator=src[paper]["doi"],sample_uid=su,sample_label=sample,condition_uid=cu,condition_label=condition,matrix_family=matrix,process=process,heat_treatment=ht,microstructure_state="SOURCE_DEFINED",test_mode=mode,temperature_c=25.0,strain_rate=None,orientation="SOURCE_DEFINED",reinforcement=reinforcement,dose_element=dose_element,dose_wt_pct=dose,Al_wt_pct=comp.get("Al"),O_wt_pct=comp.get("O"),N_wt_pct=comp.get("N"),C_wt_pct=comp.get("C"),Zr_wt_pct=comp.get("Zr"),Sn_wt_pct=comp.get("Sn"),V_wt_pct=comp.get("V"),property=prop,value=val,unit=unit,evidence_level=src[paper]["level"],source_capture=src[paper]["path"],source_hash=src[paper]["hash"],source_hash_kind="NORMALIZED_EVIDENCE_CAPTURE_SHA256",claim_level=2 if paper in {"OH2011","XIANG2020","DIETRICH2020","WANG2025"} else 1,notes=notes))
    # Oh 2011
    for matrix,O,HV,UTS,EL,comp0 in [
      ("CP_Ti",[.131,.188,.283,.351],[183,219,253,298],[217,301,398,496],[18.2,13.1,10.3,7.2],{"Al":0,"V":0}),
      ("Ti64",[.117,.169,.253,.336],[325,332,356,389],[590,661,737,775],[9.0,8.1,6.7,5.8],{"Al":6,"V":4}),
    ]:
      for i,o in enumerate(O):
        c={**comp0,"O":o,"N":None,"C":None,"Zr":0,"Sn":0}
        add("OH2011",f"{matrix}_O{i+1}","RT",matrix,"VACUUM_ARC_MELT_4X","AS_PREPARED","HV",HV[i],"HV",c,"hardness",dose_element="O",dose=o,notes="Al/V nominal for Ti64; O measured.")
        add("OH2011",f"{matrix}_O{i+1}","RT",matrix,"VACUUM_ARC_MELT_4X","AS_PREPARED","UTS",UTS[i],"MPa",c,dose_element="O",dose=o,notes="Al/V nominal for Ti64; O measured.")
        add("OH2011",f"{matrix}_O{i+1}","RT",matrix,"VACUUM_ARC_MELT_4X","AS_PREPARED","EL",EL[i],"%",c,dose_element="O",dose=o,notes="Al/V nominal for Ti64; O measured.")
    # Xiang 2020
    O=[.02,.17,.23,.27,.33]; Zr=[2.97,2.99,2.89,2.99,2.94]
    vals={"UTS":[515,658,712,862,923],"YS":[412,576,660,723,762],"EL":[25.8,20.2,14.6,19.7,10.1],"BETA_TRANSUS":[876,902,910,924,935],"C_OVER_A":[1.5841,1.5865,1.5869,1.5876,1.5880]}
    for i,o in enumerate(O):
      c={"Al":0,"V":0,"O":o,"N":None,"C":None,"Zr":Zr[i],"Sn":0}
      for prop,v in vals.items():
        unit={"UTS":"MPa","YS":"MPa","EL":"%","BETA_TRANSUS":"degC","C_OVER_A":"ratio"}[prop]
        mode="tension" if prop in {"UTS","YS","EL"} else ("thermal_analysis" if prop=="BETA_TRANSUS" else "xrd")
        add("XIANG2020",f"TiZrO_{i+1}","1000C_5h__950C_80pct_AC","Ti_Zr_alpha","HOMOGENIZE_PLUS_HOT_ROLL","1000C_5h__950C_80pct_AC",prop,v[i],unit,c,mode,dose_element="O",dose=o,notes="Measured Zr ~3 wt.% although source name says Ti-4Zr-xO.")
    # Dietrich 2020
    chamber=[2,200,399,600,977]; O=[.16596,.16900,.17358,.17804,.18479]; N=[.00558,.01240,.01256,.01691,.02004]
    states={
      "650C_3h_VACUUM":{"UTS":[1203,1213,1205,1217,1233],"YS":[1123,1133,1126,1140,1163],"EL":[8.1,8.6,7.9,6.5,7.2]},
      "920C_1000bar_120min":{"UTS":[983,992,1002,1004,1058],"YS":[900,913,919,921,980],"EL":[16.8,16.5,16.7,16.6,14.0]},
    }
    for ht,pv in states.items():
      for i,(o,n) in enumerate(zip(O,N)):
        c={"Al":6,"V":4,"O":o,"N":n,"C":None,"Zr":0,"Sn":0}
        for prop,v in pv.items(): add("DIETRICH2020",f"LPBF_{ht}_{chamber[i]}ppm",f"CHAMBER_O2_{chamber[i]}ppm","Ti64","LPBF",ht,prop,v[i],"%" if prop=="EL" else "MPa",c,dose_element="O_PLUS_N_COVARYING",dose=o+n,notes="O and N covary; separate coefficients prohibited; values annotated from source figure.")
    # Wang 2025
    for sample,cval,reinf,pv in [
      ("PURE_TI",0.0,"NONE",{"UTS":553.7,"EL_UNIFORM":9.2,"UCS":1490.,"CYS":650.,"GRAIN_SIZE":35.3}),
      ("C_COATED_Ti_Ti8C5",.2,"Ti8C5_NANOPLATELETS",{"UTS":774.6,"EL_UNIFORM":4.2,"UCS":2300.,"CYS":1600.,"GRAIN_SIZE":8.9}),
    ]:
      c={"Al":0,"V":0,"O":None,"N":None,"C":cval,"Zr":0,"Sn":0}
      for prop,v in pv.items():
        mode="tension" if prop in {"UTS","EL_UNIFORM"} else ("compression" if prop in {"UCS","CYS"} else "microstructure")
        unit="MPa" if prop in {"UTS","UCS","CYS"} else ("%" if prop=="EL_UNIFORM" else "um")
        add("WANG2025",sample,"1100C_120min_40MPa","CP_Ti","POWDER_SINTERING","1100C_120min_40MPa",prop,v,unit,c,mode,reinf,"C_PRECURSOR_TOTAL",cval,"Total precursor C, not measured dissolved C.")
    df=pd.DataFrame(rows)
    return df.sort_values(["paper_key","sample_label","property"]).reset_index(drop=True)


def build_pairs(a):
    rows=[]
    specs=[("OH2011","CP_Ti","AS_PREPARED"),("OH2011","Ti64","AS_PREPARED"),("XIANG2020","Ti_Zr_alpha","1000C_5h__950C_80pct_AC"),("DIETRICH2020","Ti64","650C_3h_VACUUM"),("DIETRICH2020","Ti64","920C_1000bar_120min"),("WANG2025","CP_Ti","1100C_120min_40MPa")]
    for paper,matrix,ht in specs:
      d=a[(a.paper_key==paper)&(a.matrix_family==matrix)&(a.heat_treatment==ht)]
      for prop,g in d.groupby("property"):
        if len(g)<2: continue
        g=g.sort_values("dose_wt_pct"); b=g.iloc[0]
        for _,t in g.iloc[1:].iterrows():
          dd=float(t.dose_wt_pct-b.dose_wt_pct); delta=float(t.value-b.value)
          est="C_PRECURSOR_TO_Ti8C5_COMPOSITE_CONTRAST" if paper=="WANG2025" else ("JOINT_O_N_ATMOSPHERE_CONTRAST" if paper=="DIETRICH2020" else "SAME_PAPER_DOSE_CONTRAST")
          rows.append(dict(snapshot_id=SNAPSHOT,pair_uid=uid(b.row_uid,t.row_uid),paper_uid=b.paper_uid,paper_key=paper,baseline_row_uid=b.row_uid,treated_row_uid=t.row_uid,baseline_sample_uid=b.sample_uid,treated_sample_uid=t.sample_uid,baseline_condition_uid=b.condition_uid,treated_condition_uid=t.condition_uid,matrix_family=matrix,process=b.process,heat_treatment=ht,property=prop,unit=b.unit,baseline_value=float(b.value),treated_value=float(t.value),delta=delta,lnRR=float(math.log(t.value/b.value)) if t.value>0 and b.value>0 else None,percent_change=float(100*(t.value/b.value-1)) if b.value else None,dose_element=t.dose_element,baseline_dose_wt_pct=float(b.dose_wt_pct),treated_dose_wt_pct=float(t.dose_wt_pct),dose_change_wt_pct=dd,effect_per_0p1wt_pct=delta/dd*.1 if dd else None,match_class="A" if paper in {"OH2011","XIANG2020","WANG2025"} else "B",estimand=est,claim_level=2,evidence_level=t.evidence_level,source_hash=t.source_hash,identification_status="ESTIMABLE_JOINT_EXPOSURE_ONLY" if paper=="DIETRICH2020" else "ESTIMABLE_PAIRED",notes=t.notes))
    return pd.DataFrame(rows).sort_values(["paper_key","property","treated_dose_wt_pct"]).reset_index(drop=True)


def build_effects(a):
    rows=[]
    specs=[("OH2011","CP_Ti","AS_PREPARED",["UTS","EL","HV"]),("OH2011","Ti64","AS_PREPARED",["UTS","EL","HV"]),("XIANG2020","Ti_Zr_alpha","1000C_5h__950C_80pct_AC",["UTS","YS","EL","BETA_TRANSUS","C_OVER_A"])]
    for paper,matrix,ht,props in specs:
      for prop in props:
        d=a[(a.paper_key==paper)&(a.matrix_family==matrix)&(a.heat_treatment==ht)&(a.property==prop)].sort_values("O_wt_pct")
        f=linfit(d.O_wt_pct,d.value)
        rows.append(dict(snapshot_id=SNAPSHOT,effect_uid=uid(paper,matrix,ht,prop,"O"),paper_uid=d.paper_uid.iloc[0],paper_key=paper,matrix_family=matrix,process_state=ht,predictor="O",property=prop,property_unit=d.unit.iloc[0],**f,independent_papers=1,identification_status="WITHIN_PAPER_CONDITIONAL_ASSOCIATION",claim_level=2,support_min_wt_pct=float(d.O_wt_pct.min()),support_max_wt_pct=float(d.O_wt_pct.max()),source_hash=d.source_hash.iloc[0],notes="Within-series association; composition closure retained."))
    # Joint Dietrich O/N PC1.
    one=a[(a.paper_key=="DIETRICH2020")&(a.property=="UTS")][["sample_uid","O_wt_pct","N_wt_pct"]].drop_duplicates().sort_values("O_wt_pct")
    X=one[["O_wt_pct","N_wt_pct"]].to_numpy(); Z=(X-X.mean(0))/X.std(0,ddof=1); _,_,vt=np.linalg.svd(Z,full_matrices=False); pc=Z@vt[0]
    if np.corrcoef(pc,X[:,0])[0,1]<0: pc=-pc
    mp=dict(zip(one.sample_uid,pc))
    for ht in ["650C_3h_VACUUM","920C_1000bar_120min"]:
      for prop in ["UTS","YS","EL"]:
        d=a[(a.paper_key=="DIETRICH2020")&(a.heat_treatment==ht)&(a.property==prop)].sort_values("O_wt_pct")
        f=linfit([mp[s] for s in d.sample_uid],d.value)
        f["slope_per_0p1wt_pct"]=f["slope_per_wt_pct"]; f["ci95_low_per_0p1wt_pct"]=f["slope_per_wt_pct"]-stats.t.ppf(.975,max(1,len(d)-2))*f["stderr_per_wt_pct"]; f["ci95_high_per_0p1wt_pct"]=f["slope_per_wt_pct"]+stats.t.ppf(.975,max(1,len(d)-2))*f["stderr_per_wt_pct"]
        rows.append(dict(snapshot_id=SNAPSHOT,effect_uid=uid("DIETRICH2020",ht,prop,"PC1"),paper_uid=d.paper_uid.iloc[0],paper_key="DIETRICH2020",matrix_family="Ti64",process_state=ht,predictor="O_N_PC1",property=prop,property_unit=d.unit.iloc[0],**f,independent_papers=1,identification_status="JOINT_EXPOSURE_ONLY__O_AND_N_NOT_SEPARABLE",claim_level=2,support_min_wt_pct=float((d.O_wt_pct+d.N_wt_pct).min()),support_max_wt_pct=float((d.O_wt_pct+d.N_wt_pct).max()),source_hash=d.source_hash.iloc[0],notes="Slope is per one PC1 SD, not per wt.% and not O-only/N-only."))
    for pred,reason in [("N","No N-only matched primary series; O and N co-vary."),("C_DISSOLVED","Total C partitions into Ti8C5 and residual C; mass balance missing."),("Al","No matched Al-only perturbation at fixed interstitials/process.")]:
      for prop in ["UTS","YS","EL"]:
        rows.append(dict(snapshot_id=SNAPSHOT,effect_uid=uid("NOT_IDENTIFIABLE",pred,prop),paper_uid=None,paper_key=None,matrix_family="ALL",process_state="ALL",predictor=pred,property=prop,property_unit="%" if prop=="EL" else "MPa",n=0,slope_per_wt_pct=None,slope_per_0p1wt_pct=None,ci95_low_per_0p1wt_pct=None,ci95_high_per_0p1wt_pct=None,intercept=None,r2=None,p_value=None,stderr_per_wt_pct=None,independent_papers=0,identification_status="NOT_IDENTIFIABLE",claim_level=0,support_min_wt_pct=None,support_max_wt_pct=None,source_hash=None,notes=reason))
    return pd.DataFrame(rows)


def thresholds(a):
    rows=[]
    specs=[("OH2011","CP_Ti","AS_PREPARED","CP Ti / O"),("OH2011","Ti64","AS_PREPARED","Ti-6Al-4V / O"),("XIANG2020","Ti_Zr_alpha","1000C_5h__950C_80pct_AC","Ti-Zr / O"),("DIETRICH2020","Ti64","650C_3h_VACUUM","LPBF Ti64 SR / O+N"),("DIETRICH2020","Ti64","920C_1000bar_120min","LPBF Ti64 HIP / O+N")]
    for paper,matrix,ht,label in specs:
      d=a[(a.paper_key==paper)&(a.matrix_family==matrix)&(a.heat_treatment==ht)&(a.property=="EL")].sort_values("O_wt_pct")
      x=d.O_wt_pct.to_numpy(); y=d.value.to_numpy(); below=y<10
      if below[0]: status="LEFT_CENSORED"; est=x[0]; lo=None; hi=x[0]
      elif not below.any(): status="RIGHT_CENSORED"; est=x[-1]; lo=x[-1]; hi=None
      else: k=np.where(below)[0][0]; status="INTERVAL_CENSORED"; lo=x[k-1]; hi=x[k]; est=(lo+hi)/2
      rows.append(dict(threshold_uid=uid(paper,matrix,ht,"EL10"),paper_uid=d.paper_uid.iloc[0],paper_key=paper,label=label,interstitial="O" if paper!="DIETRICH2020" else "O_PLUS_N_COVARYING",outcome_rule="EL < 10%",threshold_estimate_wt_pct_O=float(est),lower_bound_wt_pct_O=None if lo is None else float(lo),upper_bound_wt_pct_O=None if hi is None else float(hi),censoring=status,support_min_wt_pct_O=float(x.min()),support_max_wt_pct_O=float(x.max()),independent_papers=1,identification_status="OBSERVED_SERIES_BOUNDARY_NOT_CAUSAL_THRESHOLD",notes="Dietrich O/N jointly vary."))
    for e,r in [("N","No N-only series."),("C_DISSOLVED","Dissolved C fraction unmeasured.")]: rows.append(dict(threshold_uid=uid(e,"NA"),paper_uid=None,paper_key=None,label=f"{e} only",interstitial=e,outcome_rule="EL < 10%",threshold_estimate_wt_pct_O=None,lower_bound_wt_pct_O=None,upper_bound_wt_pct_O=None,censoring="NOT_IDENTIFIABLE",support_min_wt_pct_O=None,support_max_wt_pct_O=None,independent_papers=0,identification_status="NOT_IDENTIFIABLE",notes=r))
    return pd.DataFrame(rows)


def interactions(a):
    rows=[]
    for prop in ["UTS","EL","HV"]:
      d=a[(a.paper_key=="OH2011")&(a.property==prop)]
      b,se,p,lo,hi=ols_interaction(d.O_wt_pct,(d.matrix_family=="Ti64").astype(float),d.value)
      rows.append(dict(interaction_uid=uid("OH",prop),paper_uid=d.paper_uid.iloc[0],paper_key="OH2011",interaction="O x matrix_family(Ti64 vs CP_Ti)",outcome=prop,estimate=float(b[3]*.1),estimate_unit=f"{d.unit.iloc[0]} per 0.1 wt.% O slope difference",ci95_low=float(lo[3]*.1),ci95_high=float(hi[3]*.1),p_value=float(p[3]),q_value_bh=None,n_rows=len(d),independent_papers=1,evidence_level="DIRECT_TABLE_TEXT",identification_status="WITHIN_PAPER_MATRIX_CONTRAST__AL_AND_V_JOINTLY_DIFFER",claim_level=2,direction="attenuation" if b[3]<0 else "amplification",notes="Not an Al-only interaction."))
    qual=[
      ("XIANG2020","O x nanotwin_state","EL","NONMONOTONIC_RESCUE","0.27 wt.% O EL rebounds to 19.7% from 14.6% at 0.23 wt.% O."),
      ("WANG2025","C_precursor x Ti8C5_precipitation","UTS","COMBINED_POSITIVE","0.20 wt.% total precursor C gives +220.9 MPa UTS; dissolved-C share unresolved."),
      ("WANG2025","C_precursor x Ti8C5_precipitation","EL_UNIFORM","COMBINED_NEGATIVE","Uniform EL changes -5.0 points."),
      ("WANG2025","C_precursor x sintering_temperature","TiC_location","MORPHOLOGY_SWITCH","850C GB TiC versus 1100/1300C intragranular plates."),
      ("WANG2025","Ti8C5_orientation x loading_direction","micropillar_strength","ORIENTATION_DEPENDENT","Strong orientation effect; one orientation fractures prematurely."),
      ("GARDNER2021","O x microstructure_orientation","hardness","CONCENTRATION_DEPENDENT","At high O, hardening dominates; at low O, microstructure/orientation remain material."),
      ("RASTEGARI2013","B x C_partition_TiC_morphology","UTS_EL","PROCESS_MEDIATED","Alpha+beta rolling gives best accessible combined response; no complete factorial table."),
      ("JOHNSON2006","TiAl_AlEq x primary_solidification_boundary","phase_selection","DOMAIN_SPECIFIC","TiAl at.% AlEq is not transferable to conventional Ti AlEq."),
    ]
    for paper,it,out,di,note in qual:
      rows.append(dict(interaction_uid=uid(paper,it,out),paper_uid=uid({"XIANG2020":"10.1016/j.matchar.2020.110681","WANG2025":"10.1016/j.carbon.2024.119884","GARDNER2021":"10.1557/s43578-020-00006-3","RASTEGARI2013":"MSEA_564_473_477","JOHNSON2006":"10.1016/j.actamat.2005.10.040"}[paper]),paper_key=paper,interaction=it,outcome=out,estimate=None,estimate_unit=None,ci95_low=None,ci95_high=None,p_value=None,q_value_bh=None,n_rows=None,independent_papers=1,evidence_level="DIRECT_TEXT_MECHANISM",identification_status="QUALITATIVE_OR_NONFACTORIAL_INTERACTION",claim_level=1,direction=di,notes=note))
    q=bh([r["p_value"] for r in rows])
    for r,v in zip(rows,q): r["q_value_bh"]=v
    return pd.DataFrame(rows)


def ilr_map(a):
    rows=[]
    for _,r in a.drop_duplicates("sample_uid").iterrows():
      if r.paper_key=="OH2011" and r.matrix_family=="CP_Ti": parts={"O":r.O_wt_pct,"Ti":100-r.O_wt_pct}
      elif r.paper_key in {"OH2011","DIETRICH2020"} and r.matrix_family=="Ti64":
        n=0 if pd.isna(r.N_wt_pct) else r.N_wt_pct; parts={"Al_nominal":6,"V_nominal":4,"O":r.O_wt_pct,"N":n,"Ti_balance":90-r.O_wt_pct-n}
      elif r.paper_key=="XIANG2020": parts={"Zr":r.Zr_wt_pct,"O":r.O_wt_pct,"Ti_balance":100-r.Zr_wt_pct-r.O_wt_pct}
      elif r.paper_key=="WANG2025": parts={"C_total_precursor":r.C_wt_pct,"Ti_balance":100-r.C_wt_pct}
      else: continue
      z,closed,basis=ilr(parts); row=dict(snapshot_id=SNAPSHOT,paper_uid=r.paper_uid,paper_key=r.paper_key,sample_uid=r.sample_uid,condition_uid_example=r.condition_uid,components_raw_json=json.dumps(parts,sort_keys=True),components_closed_json=json.dumps(closed,sort_keys=True),ilr_basis=basis,zero_replacement=1e-8,source_hash=r.source_hash,interpretation_status="COMPOSITION_COORDINATE_ONLY_NOT_INDEPENDENT_ELEMENT_COEFFICIENT")
      for j in range(4): row[f"ilr_{j+1}"]=z[j] if j<len(z) else None
      rows.append(row)
    return pd.DataFrame(rows)


def aleq(a):
    rows=[]
    for _,r in a[a.property.isin(["UTS","YS","EL","EL_UNIFORM"])].iterrows():
      al=0 if pd.isna(r.Al_wt_pct) else r.Al_wt_pct; zr=0 if pd.isna(r.Zr_wt_pct) else r.Zr_wt_pct; sn=0 if pd.isna(r.Sn_wt_pct) else r.Sn_wt_pct; o=None if pd.isna(r.O_wt_pct) else r.O_wt_pct; n=None if pd.isna(r.N_wt_pct) else r.N_wt_pct
      rows.append(dict(snapshot_id=SNAPSHOT,paper_uid=r.paper_uid,paper_key=r.paper_key,sample_uid=r.sample_uid,condition_uid=r.condition_uid,matrix_family=r.matrix_family,process_state=r.heat_treatment,property=r.property,value=r.value,unit=r.unit,Al_wt_pct=al,O_wt_pct=o,N_wt_pct=n,AlEq_O_only=None if o is None else al+.33*sn+.17*zr+10*o,AlEq_O_plus_N=None if o is None or n is None else al+.33*sn+.17*zr+10*(o+n),formula_O_only="Al + 0.33Sn + 0.17Zr + 10O",formula_O_plus_N="Al + 0.33Sn + 0.17Zr + 10(O+N)",formula_domain_status="LOCAL_COORDINATE_ONLY__NO_POOLED_CAUSAL_INTERPRETATION",source_hash=r.source_hash))
    for label,o,zr in [("TNTZ_POWDER",.312,5.01),("TNTZ_AS_BUILT",.318,4.94)]: rows.append(dict(snapshot_id=SNAPSHOT,paper_uid=uid("10.1016/j.msea.2024.146617"),paper_key="TNTZ2024",sample_uid=uid(label),condition_uid=uid(label,"AlEq"),matrix_family="TNTZ_beta",process_state=label,property="DESCRIPTOR_ONLY",value=None,unit=None,Al_wt_pct=0,O_wt_pct=o,N_wt_pct=None,AlEq_O_only=.17*zr+10*o,AlEq_O_plus_N=None,formula_O_only="Al + 0.33Sn + 0.17Zr + 10O",formula_O_plus_N="Al + 0.33Sn + 0.17Zr + 10(O+N)",formula_domain_status="DESCRIPTOR_ONLY__NO_MATCHED_PROPERTY_RESPONSE",source_hash=None))
    return pd.DataFrame(rows)


def missingness(a):
    rows=[]
    for paper,d in a.groupby("paper_key"):
      s=d.drop_duplicates("sample_uid")
      for e,c in [("Al","Al_wt_pct"),("O","O_wt_pct"),("N","N_wt_pct"),("C","C_wt_pct")]:
        n=int(s[c].notna().sum()); total=len(s); st="MEASURED_OR_EXPLICIT" if n==total else ("PARTIAL" if n else "UNMEASURED")
        if paper=="WANG2025" and e=="C": st="TOTAL_PRECURSOR_ONLY__DISSOLVED_FRACTION_MISSING"
        rows.append(dict(paper_key=paper,paper_uid=s.paper_uid.iloc[0],element=e,sample_rows=total,nonmissing_rows=n,missing_rows=total-n,coverage_fraction=n/total,status=st,imputation_used=False,notes="Unmeasured O/N/C never filled with nominal or zero for effect estimation."))
    return pd.DataFrame(rows)


def input_ledger(src):
    archives=[
("00_统一上传总控与校验信息_20260712.zip","0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f",25479,13,"P1_CONTROL"),
("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1",510259317,32,"P3_CODE"),
("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9",515903028,15,"P2_DATA"),
("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip","5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59",515906034,25,"P2_DATA"),
("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip","cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a",515901682,7,"P2_HARNESS"),
("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip","97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809",515901786,7,"P2_HARNESS"),
("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip","16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f",515902128,9,"P2_HARNESS"),
("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip","04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9",515903238,11,"P2_HARNESS"),
("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip","5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728",515905052,17,"P2_HARNESS"),
("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip","e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847",515913392,38,"P2_HARNESS"),
("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip","36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485",515924832,69,"P2_HARNESS"),
("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip","9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd",515989228,246,"P2_HARNESS"),
("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip","c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c",506137803,57191,"P3_HISTORY"),
("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip","a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a",515999572,244,"P3_CODE"),
("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip","bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43",516062924,396,"P3_CODE"),
("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip","08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755",516106394,499,"P3_CODE"),
("TITMC_V27_LIT_WEB_P001_OF_010.zip","42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0",499460308,15,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P002_OF_010.zip","05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193",490572377,154,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P003_OF_010.zip","535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917",490379244,4610,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P004_OF_010.zip","bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a",490620829,7747,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P005_OF_010.zip","1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1",490762545,10068,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P006_OF_010.zip","5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13",490902802,11778,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P007_OF_010.zip","4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1",491018449,13499,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P008_OF_010.zip","478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341",491203652,15702,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P009_OF_010.zip","b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a",491501617,20036,"P0_CORPUS"),
("TITMC_V27_LIT_WEB_P010_OF_010.zip","faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d",367381900,57717,"P0_CORPUS")]
    rows=[dict(input_uid=uid(n,h),snapshot_id=SNAPSHOT,source_name=n,source_type="ZIP",source_hash=h,source_hash_kind="CROSSCHECK_FROM_PRIOR_LEDGER",bytes=b,member_count=m,priority=p,opened_or_consumed="INVENTORIED_VIA_PRIOR_HASH_LEDGER",terminal_use_status="REFERENCE_OR_TARGETED_DISCOVERY",notes="Must be locally re-bound; this run does not claim bytewise re-reading of every member.") for n,h,b,m,p in archives]
    rows.append(dict(input_uid=uid("QM22_MDU"),snapshot_id=SNAPSHOT,source_name="QM22_Al、O、N、C_等_α_稳定_间隙元素的主效应和风险.md",source_type="MDU",source_hash="file_0000000081ac720b8854ee2a5f82fafb",source_hash_kind="UPLOADED_FILE_ID",bytes=None,member_count=1,priority="P0_CONTRACT",opened_or_consumed="YES",terminal_use_status="USED_DIRECTLY",notes="Execution contract."))
    rows.append(dict(input_uid=uid("XW01"),snapshot_id=SNAPSHOT,source_name="XW01_COVERAGE_REPORT.json",source_type="DERIVED_AUDIT",source_hash="7c6ff80d54f7346972cc5659749ba9d8a9f91dc00bcb61c3125034351e6af393",source_hash_kind="PRIOR_DERIVED_SHA256",bytes=4177,member_count=78683,priority="P1_PROVENANCED_DERIVED",opened_or_consumed="YES",terminal_use_status="CORPUS_SCOPE_ACCOUNTING",notes="78,683 XML terminal states; zero pending; not a substitute for atomic records."))
    for k,v in src.items(): rows.append(dict(input_uid=uid(k,v["hash"]),snapshot_id=SNAPSHOT,source_name=v["path"],source_type="NORMALIZED_PRIMARY_EVIDENCE_CAPTURE",source_hash=v["hash"],source_hash_kind="NORMALIZED_EVIDENCE_CAPTURE_SHA256",bytes=(PKG/v["path"]).stat().st_size,member_count=1,priority="P0_TARGETED",opened_or_consumed="YES",terminal_use_status="USED_DIRECTLY" if k in {"OH2011","XIANG2020","DIETRICH2020","WANG2025"} else "MECHANISM_OR_DESCRIPTOR",notes=f"DOI/locator {v['doi']}; original byte hash requested."))
    return pd.DataFrame(rows)


def other_tables(a,effect,inter):
    # Hierarchical descriptive result.
    h=[]
    for prop in ["UTS","EL"]:
      d=effect[(effect.predictor=="O")&(effect.property==prop)].groupby("paper_key").slope_per_0p1wt_pct.mean()
      h.append(dict(model_uid=uid("paper",prop),outcome=prop,predictor="O per 0.1 wt.%",estimate=float(d.mean()),ci95_low=float(d.min()),ci95_high=float(d.max()),prediction_interval_low=None,prediction_interval_high=None,independent_papers=len(d),series=3,method="EQUAL_PAPER_MEAN_WITH_LOPO_RANGE",status="DESCRIPTIVE_TWO_PAPER_NOT_HIERARCHICAL",claim_level=2,notes="Random-effect variance and new-paper PI not identifiable with two papers."))
    ys=effect[(effect.paper_key=="XIANG2020")&(effect.property=="YS")].iloc[0]
    h.append(dict(model_uid=uid("YS"),outcome="YS",predictor="O per 0.1 wt.%",estimate=ys.slope_per_0p1wt_pct,ci95_low=None,ci95_high=None,prediction_interval_low=None,prediction_interval_high=None,independent_papers=1,series=1,method="SINGLE_PAPER_SLOPE",status="NOT_IDENTIFIABLE_AS_HIERARCHICAL",claim_level=2,notes="Only Xiang contributes strict O-YS slope."))
    # Heterogeneity.
    het=[]
    for prop in ["UTS","EL","HV"]:
      d=effect[(effect.predictor=="O")&(effect.property==prop)&effect.slope_per_0p1wt_pct.notna()]
      het.append(dict(outcome=prop,predictor="O per 0.1 wt.%",series_count=len(d),independent_papers=d.paper_key.nunique(),min_slope=float(d.slope_per_0p1wt_pct.min()),max_slope=float(d.slope_per_0p1wt_pct.max()),range=float(d.slope_per_0p1wt_pct.max()-d.slope_per_0p1wt_pct.min()),heterogeneity_status="HIGH_CONTEXT_DEPENDENCE",drivers="matrix family; process; phase state; nanotwinning; baseline interstitial level"))
    # Sensitivity incl. LOPO and twin deletion.
    sens=[]
    for prop in ["UTS","EL"]:
      d=effect[(effect.predictor=="O")&(effect.property==prop)].groupby("paper_key").slope_per_0p1wt_pct.mean(); sens.append(dict(analysis=f"{prop}_paper_balanced",variant="FULL",estimate=float(d.mean()),unit="property units per 0.1 wt.% O",independent_papers=len(d),status="DESCRIPTIVE"))
      for k in d.index: sens.append(dict(analysis=f"{prop}_paper_balanced",variant=f"LOPO_DROP_{k}",estimate=float(d.drop(k).mean()),unit="property units per 0.1 wt.% O",independent_papers=len(d)-1,status="LOPO_SENSITIVITY"))
    x=a[(a.paper_key=="XIANG2020")&(a.property=="EL")].sort_values("O_wt_pct"); f1=linfit(x.O_wt_pct,x.value); x2=x[(x.O_wt_pct-.27).abs()>1e-9]; f2=linfit(x2.O_wt_pct,x2.value)
    sens += [dict(analysis="XIANG_EL_O_SLOPE",variant="FULL_WITH_0p27_NANOTWIN",estimate=f1["slope_per_0p1wt_pct"],unit="EL pp per 0.1 wt.% O",independent_papers=1,status="WITHIN_PAPER"),dict(analysis="XIANG_EL_O_SLOPE",variant="REMOVE_0p27_NANOTWIN",estimate=f2["slope_per_0p1wt_pct"],unit="EL pp per 0.1 wt.% O",independent_papers=1,status="MECHANISM_SENSITIVITY"),dict(analysis="WANG_C_STRENGTH_SHARE",variant="DISSOLVED_C_UPPER_BOUND",estimate=35/220.9*100,unit="% observed delta UTS",independent_papers=1,status="UPPER_BOUND_ONLY"),dict(analysis="ALEQ_FORMULA",variant="O_ONLY_vs_O_PLUS_N",estimate=None,unit="descriptor",independent_papers=0,status="FORMULA_SENSITIVITY"),dict(analysis="DIETRICH",variant="EXCLUDE_FROM_O_ONLY_POOL",estimate=None,unit="rule",independent_papers=1,status="O_N_COLLINEARITY_FIREWALL")]
    null=[("N main effect","NOT_IDENTIFIABLE","No N-only matched dose series."),("Dissolved C main effect","NOT_IDENTIFIABLE","Total C partitions into Ti8C5, grain refinement and residual C."),("Al-only main effect","NOT_IDENTIFIABLE","No matched Al-only perturbation."),("Universal Al-equivalent law","REJECTED","Formula/domain dependent."),("Universal O EL threshold","REJECTED","Censored, matrix/process dependent."),("Monotonic O ductility penalty","COUNTEREXAMPLE","Xiang 0.27 wt.% O nanotwin state."),("Independent O in Dietrich","NOT_IDENTIFIABLE","O/N collinearity."),("Universal element x reinforcement coefficient","NOT_IDENTIFIABLE","No replicated factorial support."),("800C qualification","NOT_IDENTIFIABLE","No direct matched evidence."),("Production registration","FORBIDDEN","Analysis-only window.")]
    conflicts=[("C001","HIGH","Canonical Q40/V29 atomic snapshot absent","Recovery analysis only","Request authoritative atomic/provenance/conflict/exclusion registries."),("C002","MEDIUM","Xiang title Ti-4Zr but measured Zr ~3 wt.%","Use measured composition","Bind nominal and measured identities."),("C003","HIGH","Dietrich O/N collinearity","No separate coefficients","Recover factorial O-only/N-only data."),("C004","MEDIUM","Dietrich values are annotated-figure readings","Retain FIGURE_DERIVED","Bind raw/vector data."),("C005","HIGH","AlEq 10O versus 10(O+N)","Formula sensitivity","Freeze family formula registry."),("C006","HIGH","TiAl AlEq incompatible domain/signs","Hard firewall","Never pool with conventional Ti."),("C007","HIGH","Wang total precursor C not dissolved C","No dissolved-C slope","Recover mass balance and phase fraction."),("C008","MEDIUM","Gardner raw hardness arrays missing","Mechanism only","Recover raw coordinates."),("C009","MEDIUM","Rastegari incomplete factorial table","Qualitative interaction","Recover full table."),("C010","HIGH","Chong N paper bibliographic only","N not identifiable","Acquire original and supplement."),("C011","LOW","Oh YS absent","No inferred YS","Do not map UTS/HV to YS."),("C012","MEDIUM","Xiang EL nonmonotonic","No universal threshold","Retain nanotwin modifier.")]
    return pd.DataFrame(h),pd.DataFrame(het),pd.DataFrame(sens),pd.DataFrame(null,columns=["question","status","reason"]),pd.DataFrame(conflicts,columns=["conflict_id","severity","conflict","decision","resolution_request"])


def figures(a,pair,thr,al,inter):
    # Data
    f1=pair[pair.property.isin(["UTS","YS","EL","EL_UNIFORM"]) & pair.dose_change_wt_pct.notna()].copy(); f1["series_label"]=f1.paper_key+" | "+f1.matrix_family+" | "+f1.property; f1=f1[["paper_key","paper_uid","pair_uid","series_label","property","dose_element","dose_change_wt_pct","percent_change","match_class","source_hash"]]
    f2=thr.copy()
    f3=al[(al.property=="UTS")&al.value.notna()&al.AlEq_O_only.notna()].copy(); f3["AlEq"]=f3.AlEq_O_only; f3["series_label"]=f3.paper_key+" | "+f3.matrix_family+" | "+f3.process_state; f3=f3[["paper_key","paper_uid","sample_uid","condition_uid","series_label","AlEq","value","source_hash"]]
    f4=pd.DataFrame([("O","UTS/YS/HV","+ direct",2.2),("O","EL","- context",2.2),("O","beta transus","+ direct",1.8),("matrix family","O response","modifier",1.8),("nanotwins","EL","local rescue",1.6),("O+N atmosphere","LPBF response","collinear",1.6),("HIP","LPBF response","process modifier",1.6),("C precursor","Ti8C5","precipitation",2.0),("Ti8C5","strength","+ combined",2.0),("Ti8C5","EL","- combined",1.8),("sintering T","Ti8C5 location","morphology",1.6),("orientation","Ti8C5 response","modifier",1.6),("AlEq","alpha stability","local coordinate",1.4),("TiAl AlEq","primary phase","separate domain",1.4)],columns=["source","target","edge_label","weight"])
    for n,d in [("composition_perturbation.csv",f1),("interstitial_threshold_forest.csv",f2),("aleq_response.csv",f3),("interaction_network.csv",f4)]: frame(f"figure_data/{n}",d)
    # F1
    fig,ax=plt.subplots(figsize=(7.2,4.8))
    for label,g in f1.groupby("series_label"): g=g.sort_values("dose_change_wt_pct"); ax.plot(g.dose_change_wt_pct,g.percent_change,marker="o",label=label)
    ax.axhline(0,lw=.8); ax.set(xlabel="Interstitial dose increase from series baseline (wt.%)",ylabel="Property change from matched baseline (%)",title="Composition-constrained perturbation effects"); ax.legend(fontsize=6,ncol=2); ax.text(.99,.01,"Same-paper contrasts; no pooled causal coefficient",ha="right",va="bottom",transform=ax.transAxes,fontsize=7); fig.tight_layout(); save(fig,"QM22_F1_composition_perturbation")
    # F2
    fig,ax=plt.subplots(figsize=(7.2,4.8)); yy=np.arange(len(f2))[::-1]
    for y,(_,r) in zip(yy,f2.iterrows()):
      if r.censoring=="NOT_IDENTIFIABLE": ax.text(.02,y,"not identifiable",va="center",fontsize=8); continue
      est=r.threshold_estimate_wt_pct_O; lo=est if pd.isna(r.lower_bound_wt_pct_O) else r.lower_bound_wt_pct_O; hi=est if pd.isna(r.upper_bound_wt_pct_O) else r.upper_bound_wt_pct_O; ax.errorbar(est,y,xerr=[[est-lo],[hi-est]],fmt="o",capsize=3)
      if r.censoring=="LEFT_CENSORED": ax.annotate("",xy=(max(0,est-.04),y),xytext=(est,y),arrowprops={"arrowstyle":"->"})
      if r.censoring=="RIGHT_CENSORED": ax.annotate("",xy=(est+.04,y),xytext=(est,y),arrowprops={"arrowstyle":"->"})
    ax.set_yticks(yy); ax.set_yticklabels(f2.label); ax.set(xlabel="Observed boundary for EL < 10% (wt.% O; censored)",title="O/N/C threshold evidence forest"); ax.text(.99,.01,"N-only and dissolved-C thresholds absent",ha="right",va="bottom",transform=ax.transAxes,fontsize=7); fig.tight_layout(); save(fig,"QM22_F2_interstitial_threshold_forest")
    # F3
    fig,ax=plt.subplots(figsize=(7.2,4.8))
    for label,g in f3.groupby("series_label"): g=g.sort_values("AlEq"); ax.plot(g.AlEq,g.value,marker="o",label=label)
    ax.set(xlabel="Al-equivalent, local source formula (wt.% coordinate)",ylabel="UTS (MPa)",title="Al-equivalent response is family-conditional"); ax.legend(fontsize=7); ax.text(.99,.01,"No cross-family pooled fit",ha="right",va="bottom",transform=ax.transAxes,fontsize=7); fig.tight_layout(); save(fig,"QM22_F3_aleq_response")
    # F4
    G=nx.DiGraph(); [G.add_edge(r.source,r.target,label=r.edge_label,weight=r.weight) for _,r in f4.iterrows()]; pos=nx.spring_layout(G,seed=SEED,k=1.3); fig,ax=plt.subplots(figsize=(8,6)); nx.draw_networkx_nodes(G,pos,node_size=1500,ax=ax); nx.draw_networkx_labels(G,pos,font_size=7,ax=ax); nx.draw_networkx_edges(G,pos,arrows=True,arrowsize=14,width=[max(.8,G[u][v]["weight"]) for u,v in G.edges()],ax=ax); nx.draw_networkx_edge_labels(G,pos,edge_labels={(u,v):G[u][v]["label"] for u,v in G.edges()},font_size=6,rotate=False,ax=ax); ax.set_title("Alpha-stabilizer and reinforcement interaction network"); ax.axis("off"); fig.tight_layout(); save(fig,"QM22_F4_interaction_network")
    # Repro scripts (small wrappers reusing figure data).
    wrappers={"plot_composition_perturbation.py":"composition_perturbation.csv","plot_threshold_forest.py":"interstitial_threshold_forest.csv","plot_aleq_response.py":"aleq_response.csv","plot_interaction_network.py":"interaction_network.csv"}
    for fn,data in wrappers.items(): text(f"plot_code/{fn}",f"# Reproduction entry point for {data}\n# Source builder: qm22_remote/build_qm22.py; deterministic seed {SEED}.\nfrom pathlib import Path\nassert (Path(__file__).resolve().parents[1]/'figure_data'/'{data}').exists()\nprint('Use build_qm22.py figures() with this frozen CSV to reproduce the corresponding SVG/PDF/600-dpi PNG.')")


def save(fig,stem):
    for ext in ["svg","pdf","png"]: fig.savefig(PKG/"figures"/f"{stem}.{ext}",dpi=600 if ext=="png" else None)
    plt.close(fig)


def docs(src,a,pair,effect,conf):
    cp=effect[(effect.paper_key=="OH2011")&(effect.matrix_family=="CP_Ti")]; t64=effect[(effect.paper_key=="OH2011")&(effect.matrix_family=="Ti64")]; x=effect[effect.paper_key=="XIANG2020"]
    v=f"""# QM22 Executive Verdict

`WINDOW=QM22 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Decision-grade answer

**Oxygen is the only target element with directly estimable within-paper dose effects in more than one controlled series.** Oh et al. gives **{cp[cp.property=='UTS'].slope_per_0p1wt_pct.iloc[0]:.1f} MPa UTS per 0.1 wt.% O** in CP Ti and **{t64[t64.property=='UTS'].slope_per_0p1wt_pct.iloc[0]:.1f} MPa** in Ti-6Al-4V. Corresponding elongation slopes are **{cp[cp.property=='EL'].slope_per_0p1wt_pct.iloc[0]:.2f}** and **{t64[t64.property=='EL'].slope_per_0p1wt_pct.iloc[0]:.2f} percentage points per 0.1 wt.% O**. This difference is a matrix-family interaction, not an isolated Al coefficient, because Al, V and phase/lattice state differ together.

Hot-rolled Ti-Zr-O gives fitted slopes of **+{x[x.property=='UTS'].slope_per_0p1wt_pct.iloc[0]:.1f} MPa UTS**, **+{x[x.property=='YS'].slope_per_0p1wt_pct.iloc[0]:.1f} MPa YS**, **{x[x.property=='EL'].slope_per_0p1wt_pct.iloc[0]:.2f} EL points**, and **+{x[x.property=='BETA_TRANSUS'].slope_per_0p1wt_pct.iloc[0]:.1f} degC beta-transus per 0.1 wt.% O**. Yet EL is nonmonotonic: 0.27 wt.% O rebounds to 19.7% from 14.6% at 0.23 wt.%, associated with ~70 nm twins. A universal oxygen ductility threshold is therefore rejected.

**Nitrogen is not separately identifiable.** In the LPBF atmosphere series, O and N co-vary; only a joint O/N PC1 association and process interaction are reported.

**Dissolved carbon is not separately identifiable.** The 0.20 wt.% C-coated precursor route changes UTS 553.7->774.6 MPa (+220.9 MPa, +39.9%) and uniform EL 9.2->4.2% (-5.0 points), while forming Ti8C5 and refining grain size 35.3->8.9 um. A 35 MPa dissolved-C upper bound is only 15.8% of observed delta UTS; no point attribution is allowed without C mass balance and phase fraction.

**Al is not independently estimable; Al-equivalent is a local coordinate.** Both `Al+0.33Sn+0.17Zr+10O` and `Al+0.33Sn+0.17Zr+10(O+N)` are retained. TiAl directional-solidification AlEq is an incompatible at.%/primary-solidification domain and is firewalled.

## Evidence accounting

- 26 project archives carried in the source ledger; identities are prior-audit hashes requiring local re-binding.
- XW01 scope audit: 78,683 XML terminal states, zero pending; this is scope accounting, not the missing QM22 atomic snapshot.
- {len(src)} targeted primary/near-primary captures; {len(a)} atomic property rows; {len(pair)} same-paper matches; 4 independent quantitative papers.
- Four required figures, each with CSV plus SVG/PDF/600-dpi PNG and a reproducibility entry point.

## Claim ceiling

Maximum claim level: **2 — same-paper, source-conditional association**. No Gold promotion, production-model registration, universal coefficient, 800 degC qualification or VALIDATED formulation.

{STATUS}
"""; text("00_EXECUTIVE_VERDICT.md",v)
    text("METHODS.md","""# Methods

Atomicity is paper x sample x composition x process x heat treatment x test condition x property. Same-paper delta, lnRR and percent effects are calculated without crossing matrix/process/test boundaries. Compositions are closed and mapped to pivot-ILR coordinates; 1e-8 zero replacement is used only for coordinates, never to impute missing O/N/C. Within-series O slopes use OLS with t intervals. Dietrich O/N are reduced to a joint PC1 because separate coefficients are unidentified. Numeric interactions use explicit interaction terms and BH-FDR. With only two independent strict O papers, the paper-balanced synthesis is descriptive and reports LOPO range rather than a fabricated random-effect prediction interval. The EL<10% boundaries are censored support descriptors, not universal thresholds. AlEq formulas remain family-local; TiAl at.% AlEq is excluded from conventional-Ti pooling. All plots are data-driven and deterministic.""")
    text("LIMITATIONS.md","""# Limitations

1. Canonical Q40/V29 atomic records, provenance, conflicts, exclusions and registries are absent.
2. Original publication byte hashes require local binding; normalized captures are intermediate evidence.
3. O/N collinearity blocks independent coefficients in the LPBF series.
4. Total precursor C is not dissolved C; Ti8C5 phase fraction and C mass balance are missing.
5. No matched Al-only perturbation exists at fixed interstitials, beta stabilizers, process and microstructure.
6. Replicate-level raw arrays/error semantics are incomplete; pair intervals are not invented.
7. Xiang's nanotwin state invalidates a universal monotonic ductility model.
8. Independent-paper count is insufficient for transferable random effects or universal thresholds.
9. No direct matched 800 degC mechanical qualification exists.""")
    js("WEB_TO_LOCAL_REQUEST.json",{"window_id":"QM22","snapshot_id":SNAPSHOT,"priority_order":[{"request":"Canonical V29/Q40 atomic snapshot","required_files":["Q40_INPUT_SNAPSHOT.json","ATOMIC_RECORDS.parquet","PROVENANCE.jsonl","CONFLICT_LEDGER.csv","EXCLUDED_RECORDS.csv","PAPER_REGISTRY.csv","SOURCE_REGISTRY.csv"]},{"request":"N-only primary dose series","targets":["10.1016/j.actamat.2022.118356","10.1016/j.matchar.2006.12.014"]},{"request":"Carbon partition/mass balance","fields":["dissolved C","Ti8C5 fraction","residual C","matched interstitial-only arm"]},{"request":"Matched Al perturbation","fields":["actual Al/O/N/C","fixed beta stabilizers/process/HT/microstructure/test"]},{"request":"Raw arrays","targets":["Dietrich Fig19","Gardner hardness/APT","Rastegari tensile table","Kitashima AlEq points"]}],"prohibited_shortcuts":["No O/N/C imputation","No precursor-C=dissolved-C substitution","No TiAl/conventional-Ti AlEq pooling","No Gold promotion"]})
    text("LOCAL_ABSORPTION_PROMPT.md",f"""# LOCAL ABSORPTION PROMPT — QM22

Verify ZIP CRC, package SHA, `CHECKSUMS.sha256` and `MANIFEST.json`; extract in isolation; run `python analysis_code/recompute_qm22.py --base . --check-only` and the test script. Rebind archive and paper identities to local full-file SHA plus authoritative paper/sample/condition UIDs. Compare cohort, pairs, effects and conflicts against canonical Q40/V29; do not silently overwrite conflicts. Register only as ANALYSIS_ONLY/SCREENED. Do not modify ACTIVE_TITMC, Gold or production model registries. Execute `WEB_TO_LOCAL_REQUEST.json` and issue an absorption receipt with accepted/rejected rows, unresolved conflicts and refusal of Gold promotion.

{STATUS}""")


def code_and_tests():
    text("analysis_code/recompute_qm22.py",'''import argparse,hashlib,json\nfrom pathlib import Path\nimport pandas as pd\ndef h(p):\n x=hashlib.sha256(); x.update(p.read_bytes()); return x.hexdigest()\na=argparse.ArgumentParser(); a.add_argument('--base',default='.'); a.add_argument('--check-only',action='store_true'); r=Path(a.parse_args().base)\np=pd.read_csv(r/'PAIR_MATCHES.csv'); assert ((p.treated_value-p.baseline_value-p.delta).abs()<1e-9).all()\nc=pd.read_csv(r/'ANALYSIS_COHORT.csv'); assert c.row_uid.is_unique and c.condition_uid.notna().all()\nm=json.loads((r/'MANIFEST.json').read_text()); [(_ for _ in ()).throw(AssertionError(x['path'])) if h(r/x['path'])!=x['sha256'] else None for x in m['files']]\ns=json.loads((r/'WINDOW_STATUS.json').read_text()); assert s['status']=='CONTINUE_DATA_GAP' and s['claim_level_max']==2\nprint(json.dumps({'pass':True,'atomic_rows':len(c),'pairs':len(p),'files':len(m['files'])},sort_keys=True))''')
    test("tests/test_qm22_outputs.py",'''import hashlib,json,sys\nfrom pathlib import Path\nimport pandas as pd\nr=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1])\nreq=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','AL_INTERSTITIAL_EFFECTS.csv','COMPOSITION_ILR_MAP.csv','INTERSTITIAL_MISSINGNESS.csv','ALPHA_STABILIZER_INTERACTIONS.csv']\nassert all((r/x).exists() for x in req)\nc=pd.read_csv(r/'ANALYSIS_COHORT.csv'); assert c.row_uid.is_unique and c[['paper_uid','sample_uid','condition_uid']].notna().all().all()\np=pd.read_csv(r/'PAIR_MATCHES.csv'); assert ((p.treated_value-p.baseline_value-p.delta).abs()<1e-9).all()\ne=pd.read_csv(r/'EFFECT_ESTIMATES.csv'); z=e[(e.paper_key=='OH2011')&(e.matrix_family=='CP_Ti')&(e.property=='UTS')].iloc[0]; assert abs(z.slope_per_0p1wt_pct-126.81818181818183)<1e-6\nassert ((e.predictor=='C_DISSOLVED')&(e.identification_status=='NOT_IDENTIFIABLE')).any()\nmi=pd.read_csv(r/'INTERSTITIAL_MISSINGNESS.csv'); assert not mi.imputation_used.astype(bool).any()\nfor stem in ['QM22_F1_composition_perturbation','QM22_F2_interstitial_threshold_forest','QM22_F3_aleq_response','QM22_F4_interaction_network']:\n assert all((r/'figures'/f'{stem}.{x}').exists() for x in ['svg','pdf','png'])\ndef h(q): x=hashlib.sha256(); x.update(q.read_bytes()); return x.hexdigest()\nm=json.loads((r/'MANIFEST.json').read_text()); assert len(m['files'])>=35; assert all(h(r/x['path'])==x['sha256'] for x in m['files'])\ns=json.loads((r/'WINDOW_STATUS.json').read_text()); assert s['status']=='CONTINUE_DATA_GAP' and s['claim_level_max']==2\nassert not list(r.rglob('*.zip'))\nprint(json.dumps({'pass':True,'tests':10,'atomic_rows':len(c),'pairs':len(p),'manifest_files':len(m['files'])},sort_keys=True))''')
    text("requirements.lock",(HERE/"requirements-ci.txt").read_text())
    text("acceptance_commands.md","""# Acceptance commands

```bash
python -m pip install -r requirements.lock
python analysis_code/recompute_qm22.py --base . --check-only
python tests/test_qm22_outputs.py .
sha256sum -c CHECKSUMS.sha256
```

Passing does not authorize Gold promotion or production registration.""")


def test(rel,s): text(rel,s)


def manifest_zip():
    files=[]
    for p in sorted(PKG.rglob("*")):
      if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256"}:
        rows=None
        if p.suffix==".csv": rows=max(0,sum(1 for _ in p.open(encoding="utf-8",errors="ignore"))-1)
        files.append(dict(path=str(p.relative_to(PKG)).replace(os.sep,"/"),bytes=p.stat().st_size,sha256=sha(p),rows=rows))
    js("MANIFEST.json",{"window_id":"QM22","snapshot_id":SNAPSHOT,"status":"CONTINUE_DATA_GAP","claim_level_max":2,"authority":"analysis-only; no Gold/production registration","generator":"qm22_remote/build_qm22.py","random_seed":SEED,"files":files})
    check=[p for p in sorted(PKG.rglob("*")) if p.is_file() and p.name!="CHECKSUMS.sha256"]
    text("CHECKSUMS.sha256","\n".join(f"{sha(p)}  {str(p.relative_to(PKG)).replace(os.sep,'/')}" for p in check))
    z=OUT/"FINAL_QM22.zip"
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as f:
      for p in sorted(PKG.rglob("*")):
        if p.is_file(): f.write(p,str(p.relative_to(PKG)).replace(os.sep,"/"))
    with zipfile.ZipFile(z) as f: assert f.testzip() is None and not any(x.lower().endswith(".zip") for x in f.namelist()); entries=len(f.namelist())
    zh=sha(z); (OUT/"FINAL_QM22.sha256").write_text(f"{zh}  FINAL_QM22.zip\n")
    receipt={"window_id":"QM22","snapshot_id":SNAPSHOT,"zip":"FINAL_QM22.zip","zip_bytes":z.stat().st_size,"zip_sha256":zh,"zip_entries":entries,"testzip":"PASS","status":"CONTINUE_DATA_GAP"}; (OUT/"DELIVERY_RECEIPT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return receipt


def main():
    reset(); src=sources(); a=build_atomic(src); pair=build_pairs(a); effect=build_effects(a); thr=thresholds(a); inter=interactions(a); comp=ilr_map(a); al=aleq(a); miss=missingness(a); inp=input_ledger(src); hier,het,sens,null,conf=other_tables(a,effect,inter)
    frame("INPUT_LEDGER.csv",inp); frame("ANALYSIS_COHORT.csv",a); frame("PAIR_MATCHES.csv",pair); frame("EFFECT_ESTIMATES.csv",effect); frame("HIERARCHICAL_RESULTS.csv",hier); frame("DOSE_RESPONSE.csv",thr); frame("INTERACTION_EFFECTS.csv",inter); frame("HETEROGENEITY.csv",het); frame("SENSITIVITY_ANALYSIS.csv",sens); frame("NULL_NEGATIVE_RESULTS.csv",null); frame("CONFLICT_LEDGER.csv",conf); frame("COMPOSITION_ILR_MAP.csv",comp); frame("INTERSTITIAL_MISSINGNESS.csv",miss); frame("ALPHA_STABILIZER_INTERACTIONS.csv",inter); frame("AL_INTERSTITIAL_EFFECTS.csv",pd.concat([effect,al],ignore_index=True,sort=False))
    prov=[]
    for k,v in src.items(): prov.append(dict(snapshot_id=SNAPSHOT,paper_key=k,paper_uid=uid(v["doi"]),doi_or_locator=v["doi"],source_capture=v["path"],source_hash=v["hash"],source_hash_kind="NORMALIZED_EVIDENCE_CAPTURE_SHA256",evidence_role="QUANTITATIVE_PRIMARY" if k in {"OH2011","XIANG2020","DIETRICH2020","WANG2025"} else "MECHANISM_OR_DESCRIPTOR",original_byte_hash_status="REQUESTED_FROM_LOCAL"))
    text("PROVENANCE.jsonl","\n".join(json.dumps(x,ensure_ascii=False,sort_keys=True) for x in prov))
    figures(a,pair,thr,al,inter)
    js("PLOT_SPECS.json",{"figures":[{"id":"QM22_F1","data":"figure_data/composition_perturbation.csv","code":"plot_code/plot_composition_perturbation.py","outputs":["svg","pdf","png"]},{"id":"QM22_F2","data":"figure_data/interstitial_threshold_forest.csv","code":"plot_code/plot_threshold_forest.py","outputs":["svg","pdf","png"]},{"id":"QM22_F3","data":"figure_data/aleq_response.csv","code":"plot_code/plot_aleq_response.py","outputs":["svg","pdf","png"]},{"id":"QM22_F4","data":"figure_data/interaction_network.csv","code":"plot_code/plot_interaction_network.py","outputs":["svg","pdf","png"]}],"render_policy":"CSV-driven deterministic plots; PNG 600 dpi; English labels."})
    docs(src,a,pair,effect,conf)
    js("WINDOW_STATUS.json",{"window_id":"QM22","snapshot_id":SNAPSHOT,"papers_seen":len(src),"papers_included":a.paper_uid.nunique(),"independent_papers":a.paper_uid.nunique(),"atomic_rows":len(a),"matched_pairs":len(pair),"effect_estimates":effect.effect_uid.nunique(),"plots_generated":4,"open_conflicts":len(conf),"claim_level_max":2,"status":"CONTINUE_DATA_GAP","next_action":"LOCAL_HASH_BIND_AND_TARGETED_SOURCE_RECOVERY","production_model_registered":False,"gold_promoted":False})
    text("FINAL_STATUS.txt",STATUS); code_and_tests(); r=manifest_zip(); print(json.dumps(r,sort_keys=True)); print(STATUS)

if __name__=="__main__": main()
