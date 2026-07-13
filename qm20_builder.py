from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.interpolate import PchipInterpolator

SEED = 20260713
OUT = Path("FINAL_QM20")
for d in [OUT, OUT/"figures", OUT/"figure_data", OUT/"plot_code", OUT/"analysis_code", OUT/"tests", OUT/"validation"]:
    d.mkdir(parents=True, exist_ok=True)

STATUS = "STATUS: CONTINUE_DATA_GAP | WINDOW=QM20 | MISSING=AUTHORITATIVE_Q40_SNAPSHOT+ORIGINAL_MEMBER_HASHES+CONTROLLED_ORIENTATION_AND_AGGLOMERATION_SERIES | NEXT=LOCAL_HASH_BIND_AND_RERUN_PAPER_CLUSTER_MODEL"


def canon(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hbytes(x: bytes) -> str:
    return hashlib.sha256(x).hexdigest()


def hfile(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()


def text(rel: str, s: str) -> None:
    p = OUT/rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


def js(rel: str, x: Any) -> None:
    text(rel, json.dumps(x, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+"\n")


def csvout(rel: str, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields=[]; seen=set()
        for r in rows:
            for k in r:
                if k not in seen: seen.add(k); fields.append(k)
    p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader()
        for r in rows:
            z={}
            for k in fields:
                v=r.get(k,"")
                if v is None or (isinstance(v,float) and math.isnan(v)): v=""
                z[k]=v
            w.writerow(z)

papers={
 "KOO2012":{"doi":"10.1016/j.scriptamat.2011.12.024","title":"Effect of aspect ratios of in situ formed TiB whiskers on the mechanical properties of TiBw/Ti-6Al-4V composites","year":2012},
 "BAO2024":{"doi":"10.1080/17452759.2024.2383287","title":"Aligned and composition-dependent TiB whisker titanium matrix composite study","year":2024},
 "WU2022":{"doi":"10.1016/j.msea.2022.143645","title":"Understanding the confined TiB fiber-like structure for strength-ductility combination of discontinuous-reinforced titanium matrix composites","year":2022},
 "JIAO2019":{"doi":"10.1016/j.powtec.2019.09.008","title":"Strengthening and plasticity improvement mechanisms of titanium matrix composites with two-scale network microstructure","year":2019},
 "LI2026":{"doi":"10.1016/j.jmst.2025.02.101","title":"Enhancing strength-ductility synergy of TiBw/Ti55 composites by introducing a bimodal grain structure","year":2026},
}

geom=[]
def G(p,u,c,matrix,process,reinf,dose,arch,loc,scale,diam=None,length=None,ar=None,eta=None,orient="",agg=None,por=None,grain=None,colony=None,second="",second_dose=None,evidence="DIRECT_TABLE_TEXT",locator="",notes=""):
    geom.append(dict(paper_uid=p,sample_uid=u,condition_uid=c,doi=papers[p]["doi"],year=papers[p]["year"],matrix=matrix,process=process,reinforcement=reinf,reinforcement_vol_pct=dose,second_phase=second,second_phase_vol_pct=second_dose,architecture=arch,reinforcement_location=loc,scale_class=scale,diameter_um=diam,length_um=length,aspect_ratio=ar,orientation_factor=eta,orientation_description=orient,agglomeration_index_sd_pct=agg,porosity_pct=por,grain_size_um=grain,alpha_colony_um=colony,geometry_measurement_mode="DIRECT_MEASUREMENT" if evidence.startswith("DIRECT") else "MIXED_OR_INFERRED",evidence_level=evidence,source_locator=locator,notes=notes))

# Koo fixed-dose size/AR series.
G("KOO2012","KOO_AR18","SPS_1200C_5MIN_50MPA_RT","Ti-6Al-4V","SPS","TiBw",1,"uniform","matrix_interior","micro",1.0,18,18,None,"not numerically reported",None,None,6.6,None,locator="Table 1; Figs. 3-4",notes="size and AR co-vary")
G("KOO2012","KOO_AR38","SPS_1200C_5MIN_50MPA_RT","Ti-6Al-4V","SPS","TiBw",1,"uniform","matrix_interior","micro",0.5,19,38,None,"not numerically reported",None,None,6.5,None,locator="Table 1; Figs. 3-4",notes="size and AR co-vary")
G("KOO2012","KOO_AR58","SPS_1200C_5MIN_50MPA_RT","Ti-6Al-4V","SPS","TiBw",1,"uniform","matrix_interior","nano_diameter",0.1,5.8,58,None,"not numerically reported",None,None,6.3,None,locator="Table 1; Figs. 3-4",notes="100 nm diameter; size and AR co-vary")
G("KOO2012","KOO_5V_AR13","SPS_1200C_5MIN_50MPA_RT","Ti-6Al-4V","SPS","TiBw",5,"uniform","matrix_interior","micro",1.0,13,13,None,"not numerically reported",None,None,6.8,None,locator="Table 1",notes="dose and geometry co-vary")

# Bao control and TiBw series.
G("BAO2024","BAO_S0","WAAM_ASBUILT_RT_LONGITUDINAL","Ti alloy","WAAM","none",0,"matrix_control","none","none",agg=0,por=0,locator="property/distribution tables")
for u,d,ar,eta,agg,por,arch,orient in [
 ("BAO_S1",2,19.2,.64,.9,.56,"aligned_hypoeutectic","aligned with load"),
 ("BAO_S2",5,23,.62,3.2,.77,"aligned_hypoeutectic","aligned with load"),
 ("BAO_S3",10,None,.125,4.0,.84,"transition_network","mixed/random; eta is convention"),
 ("BAO_S4",20,None,.125,7.9,1.39,"clustered_hypereutectic","random/clustered; eta is convention"),
 ("BAO_S5",30,None,.125,11.1,2.36,"clustered_hypereutectic","random/clustered; eta is convention")]:
    G("BAO2024",u,"WAAM_ASBUILT_RT_LONGITUDINAL","Ti alloy","WAAM","TiBw",d,arch,"cellular_or_eutectic_regions","micro",ar=ar,eta=eta,orient=orient,agg=agg,por=por,evidence="DIRECT_TABLE_TEXT" if ar else "MIXED_DIRECT_AND_RANDOM_CONVENTION",locator="TiBw distribution, porosity and tensile tables",notes="agglomeration, dose, porosity, phase regime and orientation co-vary")

# Wu fixed-total-TiB architecture contrasts.
for u,d,arch,ar,grain,loc in [
 ("WU_FLSCR10",4,"fiber_like_composite_region_continuous_Ti",5.31,3.7,"confined_composite_region"),
 ("WU_HS4",4,"homogeneous",6.0,4.2,"homogeneous"),
 ("WU_FLSTR10",6,"fiber_like_Ti_region_discontinuous_Ti",5.36,3.5,"continuous_composite_region"),
 ("WU_FLSCR15",6,"fiber_like_composite_region_continuous_Ti",5.10,3.3,"confined_composite_region")]:
    G("WU2022",u,"PM_EXTRUDED_ROLLED_RT_RD","CP-Ti","reaction_hot_pressing+extrusion+rolling","TiBw",d,arch,loc,"micro",ar=ar,orient="most whiskers aligned with rolling direction; scalar factor absent",por=0,grain=grain,locator="Tables 2-4; Figs. 3,7-9",notes="at least 400 whiskers measured")

# Jiao network hierarchy.
G("JIAO2019","JIAO_MATRIX","RHP_AS_SINTERED_RT","Ti-6Al-4V","reaction_hot_pressing","none",0,"matrix_control","none","none",colony=48,locator="Tables 1-2")
G("JIAO2019","JIAO_I","RHP_AS_SINTERED_RT","Ti-6Al-4V","reaction_hot_pressing","TiBw",3.4,"one_scale_network","grain_boundary_around_matrix_particles","micro",length=3,ar=2.27,eta=.27,orient="3D random-array model",locator="Figs. 1-2; Table 2")
G("JIAO2019","JIAO_II","RHP_AS_SINTERED_RT","Ti-6Al-4V","reaction_hot_pressing","Ti5Si3",4,"second_scale_network","beta_phase_interior","submicron",diam=.5,ar=3.62,eta=.27,orient="3D random-array model",locator="Figs. 1-3; Table 2")
G("JIAO2019","JIAO_III","RHP_AS_SINTERED_RT","Ti-6Al-4V","reaction_hot_pressing","TiBw",3.4,"two_scale_network","TiBw_boundary+Ti5Si3_beta_interior","micro+submicron",diam=.5,length=3,ar=2.27,eta=.27,orient="3D random-array model",colony=4.8,second="Ti5Si3",second_dose=4,locator="Tables 1-3; Figs. 2-9",notes="Ti5Si3 AR=3.62")
G("JIAO2019","JIAO_IV","RHP_AS_SINTERED_RT","Ti-6Al-4V","reaction_hot_pressing","TiBw",3.4,"coarse_connected_two_phase_network","coarse_Ti5Si3_at_grain_boundary","micro",ar=2.27,eta=.27,orient="3D random-array model",second="Ti5Si3",second_dose=8,locator="Fig. 2e; Table 2",notes="preferred crack-initiation sites")

# Li as-received / 30% forged network-preserving states.
for u,d,arch,ar,grain,state in [
 ("LI_TI55_AR",0,"matrix_control",None,30.1,"as_received"),("LI_TI55_HF",0,"bimodal_grain_matrix",None,5.2,"hot_forged_30pct"),
 ("LI_TMCL_AR",3.5,"network",2.94,20.2,"as_received"),("LI_TMCL_HF",3.5,"network_preserved+bimodal_grain",2.82,4.5,"hot_forged_30pct"),
 ("LI_TMCH_AR",7,"network",2.93,21.0,"as_received"),("LI_TMCH_HF",7,"network_preserved+bimodal_grain",2.66,4.3,"hot_forged_30pct")]:
    G("LI2026",u,state+"_RT","Ti55","reaction_hot_pressing"+("+hot_forging" if "HF" in u else ""),"TiBw" if d else "none",d,arch,"network_boundaries" if d else "none","micro",ar=ar,orient="major axis rotates perpendicular to forging direction" if "HF" in u and d else "",grain=grain,locator="Table 1; Figs. 3,5-13",notes="30% preserves network; 50% destroys network and causes cracks/debonding")

smap={r["sample_uid"]:r for r in geom}
props=[]
def P(u,name,val,unit,sd=None,n=None,evidence="DIRECT_TABLE_TEXT",locator="",notes=""):
    s=smap[u]
    props.append(dict(record_uid=f"{s['paper_uid']}::{u}::{s['condition_uid']}::{name}",paper_uid=s["paper_uid"],sample_uid=u,condition_uid=s["condition_uid"],doi=s["doi"],matrix=s["matrix"],process=s["process"],architecture=s["architecture"],reinforcement=s["reinforcement"],reinforcement_vol_pct=s["reinforcement_vol_pct"],property=name,value=val,unit=unit,sd=sd,n=n,evidence_level=evidence,source_locator=locator or s["source_locator"],notes=notes))

# Koo: endpoint modulus text/direct; intermediate and YS figure-derived.
P("KOO_AR18","elastic_modulus_GPa",116,"GPa",evidence="DIRECT_TEXT_ENDPOINT",locator="Fig. 3 and text")
P("KOO_AR38","elastic_modulus_GPa",121,"GPa",evidence="FIGURE_DERIVED",locator="Fig. 3",notes="approximate")
P("KOO_AR58","elastic_modulus_GPa",125,"GPa",evidence="DIRECT_TEXT_ENDPOINT",locator="Fig. 3 and text")
for u,v in [("KOO_AR18",900),("KOO_AR38",990),("KOO_AR58",1070)]: P(u,"yield_strength_MPa",v,"MPa",evidence="FIGURE_DERIVED",locator="Fig. 4",notes="approximate; not Gold-eligible")

# Bao exact table series.
bao={
 "BAO_S0":(903,50,1453,11,36,1,16.5,1.2,321,7),"BAO_S1":(1041,72,1623,37,29.3,1.5,12.6,.8,382,13),
 "BAO_S2":(1224,41,1534,41,20.3,1.2,4.5,1.3,404,29),"BAO_S3":(1456,70,1702,168,19.7,2.1,3.2,1.4,434,30),
 "BAO_S4":(None,None,1632,174,16.3,1.2,0,None,479,58),"BAO_S5":(None,None,1857,141,16.5,.1,0,None,661,142)}
for u,z in bao.items():
    ys,yssd,uts,utssd,ef,efsd,eu,eusd,hv,hvsd=z
    if ys is not None:P(u,"yield_strength_MPa",ys,"MPa",yssd)
    P(u,"ultimate_tensile_strength_MPa",uts,"MPa",utssd);P(u,"fracture_elongation_pct",ef,"%",efsd);P(u,"uniform_elongation_pct",eu,"%",eusd);P(u,"hardness_HV",hv,"HV",hvsd)

# Wu Table 3 and labelled WOF figure.
wu={"WU_FLSCR10":(575,10,778,7,9.6,.1,19.1,.3,142.5),"WU_HS4":(629,4,811,9,8.1,.2,14.6,1.3,113.3),"WU_FLSTR10":(660,4,890.8,2.6,7.8,.2,12.4,.1,103.9),"WU_FLSCR15":(631.6,18.3,797.8,16.1,8.3,.3,15.5,.7,117.8)}
for u,z in wu.items():
    ys,yssd,uts,utssd,eu,eusd,ef,efsd,wof=z
    P(u,"yield_strength_MPa",ys,"MPa",yssd,3,locator="Table 3");P(u,"ultimate_tensile_strength_MPa",uts,"MPa",utssd,3,locator="Table 3");P(u,"uniform_elongation_pct",eu,"%",eusd,3,locator="Table 3");P(u,"fracture_elongation_pct",ef,"%",efsd,3,locator="Table 3");P(u,"work_of_fracture_MJ_m3",wof,"MJ/m^3",evidence="FIGURE_DERIVED",locator="Fig. 9c")

# Jiao Table 2.
jiao={"JIAO_MATRIX":(770,10.6,930,11,8.1,.15),"JIAO_I":(930,10,1070,11,3.2,.15),"JIAO_II":(900,9,1030,9.3,2.1,.13),"JIAO_III":(1050,9,1180,9.7,5,.15),"JIAO_IV":(None,None,980,8,1,.1)}
for u,z in jiao.items():
    ys,yssd,uts,utssd,el,elsd=z
    if ys is not None:P(u,"yield_strength_MPa",ys,"MPa",yssd,3,locator="Table 2")
    P(u,"ultimate_tensile_strength_MPa",uts,"MPa",utssd,3,locator="Table 2");P(u,"fracture_elongation_pct",el,"%",elsd,3,locator="Table 2")
P("LI_TI55_AR","fracture_elongation_pct",13.8,"%",evidence="DIRECT_TEXT",locator="Section 3.4; Fig. 7")
P("LI_TI55_HF","fracture_elongation_pct",9.6,"%",evidence="DIRECT_TEXT",locator="Section 3.4; Fig. 7")

snap_payload={"papers":papers,"geometry":geom,"properties":props,"seed":SEED}
SNAP="QM20_WEB_EVIDENCE_"+hbytes(canon(snap_payload).encode())[:20]
for r in geom+props:r["snapshot_id"]=SNAP
pmap={(r["sample_uid"],r["property"]):r for r in props}

pairs=[]
def M(pid,t,c,prop,ctype,tier,ident,conf):
    a=pmap[(t,prop)];b=pmap[(c,prop)]
    pairs.append(dict(snapshot_id=SNAP,pair_id=pid,paper_uid=a["paper_uid"],doi=a["doi"],treatment_sample_uid=t,control_sample_uid=c,condition_uid=a["condition_uid"],property=prop,treatment_value=a["value"],control_value=b["value"],unit=a["unit"],treatment_sd=a["sd"],control_sd=b["sd"],replicate_n_treatment=a["n"],replicate_n_control=b["n"],contrast_type=ctype,match_tier=tier,same_matrix=a["matrix"]==b["matrix"],same_process=a["process"]==b["process"],same_test_condition=a["condition_uid"]==b["condition_uid"],identification_statement=ident,residual_confounding=conf,evidence_level=a["evidence_level"]+"|"+b["evidence_level"],source_locator=a["source_locator"]+" versus "+b["source_locator"]))

for t,sfx in [("KOO_AR38","38v18"),("KOO_AR58","58v18")]:
    M("KOO_"+sfx+"_E",t,"KOO_AR18","elastic_modulus_GPa","fixed_1volpct_joint_size_AR","A","same paper/matrix/process/dose/test","diameter and AR co-vary")
    M("KOO_"+sfx+"_YS",t,"KOO_AR18","yield_strength_MPa","fixed_1volpct_joint_size_AR","A","same paper/matrix/process/dose/test","diameter and AR co-vary; YS figure-derived")
for u in ["BAO_S1","BAO_S2","BAO_S3","BAO_S4","BAO_S5"]:
    for pr in ["ultimate_tensile_strength_MPa","fracture_elongation_pct","uniform_elongation_pct","hardness_HV"]:M(u+"_vs_S0_"+pr,u,"BAO_S0",pr,"matrix_control_dose_series","A","same paper/process/test","dose, agglomeration, porosity, phase regime and orientation co-vary")
    if (u,"yield_strength_MPa") in pmap:M(u+"_vs_S0_YS",u,"BAO_S0","yield_strength_MPa","matrix_control_dose_series","A","same paper/process/test","dose, agglomeration, porosity, phase regime and orientation co-vary")
for t,c,label in [("WU_FLSCR10","WU_HS4","4volpct"),("WU_FLSCR15","WU_FLSTR10","6volpct")]:
    for pr in ["yield_strength_MPa","ultimate_tensile_strength_MPa","uniform_elongation_pct","fracture_elongation_pct","work_of_fracture_MJ_m3"]:M("WU_"+label+"_"+pr,t,c,pr,"fixed_total_TiB_architecture","A","same paper/matrix/process/test/total TiB","local concentration, region fraction, grain size and AR differ")
for u in ["JIAO_I","JIAO_II","JIAO_III"]:
    for pr in ["yield_strength_MPa","ultimate_tensile_strength_MPa","fracture_elongation_pct"]:M(u+"_vs_MATRIX_"+pr,u,"JIAO_MATRIX",pr,"matrix_control","A","same paper/process/test","chemistry, dose, architecture and refinement co-vary")
for pr in ["yield_strength_MPa","ultimate_tensile_strength_MPa","fracture_elongation_pct"]:M("JIAO_III_vs_I_"+pr,"JIAO_III","JIAO_I",pr,"two_scale_vs_one_scale","B","same paper/process/test/fixed TiBw","adds 4 vol.% Ti5Si3; architecture and chemistry inseparable")
for pr in ["ultimate_tensile_strength_MPa","fracture_elongation_pct"]:M("JIAO_IV_vs_III_"+pr,"JIAO_IV","JIAO_III",pr,"coarse8_vs_fine4_second_phase","B","same paper/process/test/fixed TiBw","Ti5Si3 dose, size, connectivity and location co-vary")

def E(m):
    yt=float(m["treatment_value"]);yc=float(m["control_value"]);d=yt-yc;lr=math.log(yt/yc) if yt>0 and yc>0 else None;pct=(math.exp(lr)-1)*100 if lr is not None else None
    dlo=dhi=plo=phi=None
    if m["replicate_n_treatment"] and m["replicate_n_control"] and m["treatment_sd"] not in (None,"") and m["control_sd"] not in (None,""):
        nt=int(m["replicate_n_treatment"]);nc=int(m["replicate_n_control"]);st=float(m["treatment_sd"]);sc=float(m["control_sd"])
        se=math.sqrt(st*st/nt+sc*sc/nc);dlo=d-1.96*se;dhi=d+1.96*se
        if lr is not None:
            sl=math.sqrt((st/(yt*math.sqrt(nt)))**2+(sc/(yc*math.sqrt(nc)))**2);plo=(math.exp(lr-1.96*sl)-1)*100;phi=(math.exp(lr+1.96*sl)-1)*100
    return dict(snapshot_id=SNAP,effect_id="EFF::"+m["pair_id"],pair_id=m["pair_id"],paper_uid=m["paper_uid"],doi=m["doi"],treatment_sample_uid=m["treatment_sample_uid"],control_sample_uid=m["control_sample_uid"],property=m["property"],estimand="Y_treatment-Y_control; ln response ratio",absolute_delta=d,unit=m["unit"],delta_ci95_low=dlo,delta_ci95_high=dhi,lnRR=lr,percent_change=pct,percent_ci95_low=plo,percent_ci95_high=phi,match_tier=m["match_tier"],claim_level=2,evidence_level=m["evidence_level"],support_domain=m["contrast_type"],residual_confounding=m["residual_confounding"],causal_language_allowed="NO")
effects=[E(m) for m in pairs];emap={r["pair_id"]:r for r in effects}

# Paper-cluster architecture synthesis.
primary={"ultimate_tensile_strength_MPa":["WU_4volpct_ultimate_tensile_strength_MPa","WU_6volpct_ultimate_tensile_strength_MPa","JIAO_III_vs_I_ultimate_tensile_strength_MPa"],"fracture_elongation_pct":["WU_4volpct_fracture_elongation_pct","WU_6volpct_fracture_elongation_pct","JIAO_III_vs_I_fracture_elongation_pct"]}
hier=[];hetero=[];sens=[];rng=np.random.default_rng(SEED)
for pr,ids in primary.items():
    b=defaultdict(list)
    for pid in ids:b[emap[pid]["paper_uid"]].append(float(emap[pid]["lnRR"]))
    pv={k:float(np.mean(v)) for k,v in b.items()};v=np.array(list(pv.values()));mu=float(v.mean());boot=np.array([rng.choice(v,len(v),replace=True).mean() for _ in range(20000)]);lo,hi=np.quantile(boot,[.025,.975])
    hier.append(dict(snapshot_id=SNAP,analysis_id="ARCH_PAPER_CLUSTER_"+pr,outcome=pr,model="paper-mean lnRR + paper-cluster bootstrap",independent_papers=len(v),matched_contrasts=len(ids),pooled_lnRR=mu,pooled_percent_change=(math.exp(mu)-1)*100,cluster_bootstrap_ci95_low_pct=(math.exp(lo)-1)*100,cluster_bootstrap_ci95_high_pct=(math.exp(hi)-1)*100,prediction_interval="NOT_ESTIMABLE_WITH_TWO_NUMERIC_PAPERS",claim_level=2,identifiability="LOW_SUPPORT" if pr.startswith("fracture") else "SIGN_UNSTABLE",notes="Li 2026 qualitative direction check excluded from numeric pooling"))
    hetero.append(dict(snapshot_id=SNAP,analysis_id="ARCH_HETEROGENEITY_"+pr,outcome=pr,paper_effects_lnRR=canon(pv),range_lnRR=float(v.max()-v.min()),direction_consistent=bool(np.all(v>0) or np.all(v<0)),tau2="NOT_ESTIMABLE",I2_pct="NOT_ESTIMABLE",reason="two numeric papers and non-equivalent architecture estimands"))
    for leave in pv:
        rem=[x for k,x in pv.items() if k!=leave];z=float(np.mean(rem));sens.append(dict(snapshot_id=SNAP,analysis_id=f"LOPO_{pr}_leave_{leave}",sensitivity_type="leave_one_paper_out",outcome=pr,left_out_paper=leave,remaining_independent_papers=len(rem),estimate_lnRR=z,estimate_percent_change=(math.exp(z)-1)*100,direction="positive" if z>0 else "negative",decision="DIRECTION_STABLE_LOW_SUPPORT" if pr.startswith("fracture") else "DIRECTION_UNSTABLE"))

# Joint size/AR association.
kd=pd.DataFrame([r for r in geom if r["paper_uid"]=="KOO2012" and r["reinforcement_vol_pct"]==1]).sort_values("diameter_um")
kv={u:{r["property"]:r["value"] for r in props if r["sample_uid"]==u} for u in kd.sample_uid};kd["E"]=[kv[u]["elastic_modulus_GPa"] for u in kd.sample_uid];kd["YS"]=[kv[u]["yield_strength_MPa"] for u in kd.sample_uid]
corr=float(np.corrcoef(kd.diameter_um,kd.aspect_ratio)[0,1]);hier += [dict(snapshot_id=SNAP,analysis_id="KOO_JOINT_SIZE_AR_MODULUS",outcome="elastic_modulus_GPa",model="within-paper log-diameter association",independent_papers=1,matched_contrasts=2,slope_per_ln_diameter=float(np.polyfit(np.log(kd.diameter_um),kd.E,1)[0]),diameter_AR_correlation=corr,identifiability="JOINT_GEOMETRY_ONLY",claim_level=2),dict(snapshot_id=SNAP,analysis_id="KOO_JOINT_SIZE_AR_YS",outcome="yield_strength_MPa",model="within-paper log-diameter association",independent_papers=1,matched_contrasts=2,slope_per_ln_diameter=float(np.polyfit(np.log(kd.diameter_um),kd.YS,1)[0]),diameter_AR_correlation=corr,identifiability="JOINT_GEOMETRY_ONLY_FIGURE_DERIVED",claim_level=2)]

# Agglomeration association.
agg=[];eu0=float(pmap[("BAO_S0","uniform_elongation_pct")]["value"])
for u in ["BAO_S1","BAO_S2","BAO_S3","BAO_S4","BAO_S5"]:
    s=smap[u];eu=float(pmap[(u,"uniform_elongation_pct")]["value"])
    agg.append(dict(snapshot_id=SNAP,paper_uid="BAO2024",sample_uid=u,reinforcement_vol_pct=s["reinforcement_vol_pct"],agglomeration_index_sd_pct=s["agglomeration_index_sd_pct"],porosity_pct=s["porosity_pct"],orientation_factor=s["orientation_factor"],uniform_elongation_pct=eu,delta_uniform_elongation_vs_matrix_pp=eu-eu0,fracture_elongation_pct=pmap[(u,"fracture_elongation_pct")]["value"],ultimate_tensile_strength_MPa=pmap[(u,"ultimate_tensile_strength_MPa")]["value"],evidence_level="DIRECT_TABLE_TEXT",identifiability="ONE_PAPER_MULTI_CONFOUNDED_ASSOCIATION",confounders="dose, porosity, phase regime, AR and orientation"))
ax=np.array([r["agglomeration_index_sd_pct"] for r in agg],float);ay=np.array([r["delta_uniform_elongation_vs_matrix_pp"] for r in agg],float);rho,rp=stats.spearmanr(ax,ay);sl,it,sl_lo,sl_hi=stats.theilslopes(ay,ax,.95)
agg_summary=dict(snapshot_id=SNAP,paper_uid="BAO2024",sample_uid="SUMMARY",evidence_level="DERIVED_CALCULATION",identifiability="NOT_IDENTIFIABLE_AS_INDEPENDENT_PENALTY",confounders="dose, porosity, phase regime, AR and orientation",spearman_rho=float(rho),spearman_p_nominal=float(rp),theil_sen_slope_pp_per_index=float(sl),theil_sen_ci95_low=float(sl_lo),theil_sen_ci95_high=float(sl_hi),claim="monotone within-paper association only")
for i,r in enumerate(agg):
    rr,pp=stats.spearmanr(np.delete(ax,i),np.delete(ay,i));sens.append(dict(snapshot_id=SNAP,analysis_id="AGG_LOSO_leave_"+r["sample_uid"],sensitivity_type="leave_one_sample_out_within_BAO2024",outcome="delta_uniform_elongation_vs_matrix_pp",left_out_paper="BAO2024",left_out_sample=r["sample_uid"],remaining_independent_papers=1,spearman_rho=float(rr),nominal_p=float(pp),decision="MONOTONE_DIRECTION_RETAINED" if rr<0 else "DIRECTION_CHANGED"))

inter=[
 dict(snapshot_id=SNAP,interaction_id="AR_X_ORIENTATION_SHEAR_LAG",paper_uid="MULTI_SOURCE_MECHANISM",variables="aspect_ratio × orientation_factor",estimand="load-transfer increment per 1 vol.% at reference matrix YS=900 MPa",equation="0.5*sigma_matrix*0.01*AR*eta",support="numeric anchors AR 2.27-23, eta .27-.64; Koo AR 58 lacks eta",result="multiplicative mechanistic sensitivity",identifiability="MECHANISTIC_SURFACE_NOT_EMPIRICAL_ALE",claim_level=1),
 dict(snapshot_id=SNAP,interaction_id="LI_ROTATION_TMCL",paper_uid="LI2026",variables="forging × orientation at nearly fixed AR",estimand="source-calculated YS increment due to rotation",equation="source Eq.7",support="AR 2.94→2.82; 30% forging; network preserved",result="13.9 MPa",identifiability="SOURCE_MODEL_COMPONENT",claim_level=2),
 dict(snapshot_id=SNAP,interaction_id="LI_ROTATION_TMCH",paper_uid="LI2026",variables="forging × orientation at nearly fixed AR",estimand="source-calculated YS increment due to rotation",equation="source Eq.7",support="AR 2.93→2.66; 30% forging; network preserved",result="18.6 MPa",identifiability="SOURCE_MODEL_COMPONENT",claim_level=2),
 dict(snapshot_id=SNAP,interaction_id="JIAO_SCALE_X_LOCATION",paper_uid="JIAO2019",variables="submicron size × beta-interior location",estimand="two-scale vs one-scale pair",equation="composite III - composite I",support="fixed 3.4 vol.% TiBw; adds 4 vol.% Ti5Si3",result="ΔYS=120; ΔUTS=110 MPa; ΔEL=+1.8 pp",identifiability="ARCHITECTURE_PLUS_CHEMISTRY_DOSE_CONFOUNDED",claim_level=2)]

dose=[dict(snapshot_id=SNAP,analysis_id="BAO_DOSE_"+r["sample_uid"],paper_uid="BAO2024",dose_definition="actual TiBw vol.%",dose=r["reinforcement_vol_pct"],outcome="uniform_elongation_pct",outcome_value=r["uniform_elongation_pct"],architecture_state=smap[r["sample_uid"]]["architecture"],model="observed series",identifiability="DOSE_AGGLOMERATION_POROSITY_PHASE_CONFOUNDED") for r in agg]
dose += [dict(snapshot_id=SNAP,analysis_id="JIAO_TI5SI3_4_TO_8_UTS",paper_uid="JIAO2019",dose_definition="Ti5Si3 vol.% at fixed 3.4 vol.% TiBw",dose="4→8",outcome="ultimate_tensile_strength_MPa",outcome_value="1180→980",architecture_state="fine intragranular→coarse connected boundary",model="two-point pair",identifiability="DOSE_SIZE_CONNECTIVITY_LOCATION_CONFOUNDED"),dict(snapshot_id=SNAP,analysis_id="JIAO_TI5SI3_4_TO_8_EL",paper_uid="JIAO2019",dose_definition="Ti5Si3 vol.% at fixed 3.4 vol.% TiBw",dose="4→8",outcome="fracture_elongation_pct",outcome_value="5.0→1.0",architecture_state="fine intragranular→coarse connected boundary",model="two-point pair",identifiability="DOSE_SIZE_CONNECTIVITY_LOCATION_CONFOUNDED")]

nulls=[
 dict(result_id="N01",question="independent size effect",status="NOT_IDENTIFIABLE",evidence="KOO2012",reason="diameter and AR collinear",boundary="joint geometry only"),
 dict(result_id="N02",question="global empirical AR×orientation ALE",status="NOT_IDENTIFIABLE",evidence="Koo/Bao/Jiao/Li",reason="too few definition-compatible matched numeric papers",boundary="mechanistic surface only"),
 dict(result_id="N03",question="universal architecture strength benefit",status="DIRECTION_UNSTABLE",evidence="Wu/Jiao",reason="UTS sign flips under LOPO",boundary="architecture class and chemistry matter"),
 dict(result_id="N04",question="independent agglomeration coefficient",status="NOT_IDENTIFIABLE",evidence="Bao S1-S5",reason="dose/porosity/phase/AR/orientation co-vary",boundary="one-paper monotone association"),
 dict(result_id="N05",question="more second phase is always better",status="REJECTED",evidence="Jiao IV vs III",reason="ΔUTS=-200 MPa; ΔEL=-4 pp",boundary="coarse connected boundary phase is harmful"),
 dict(result_id="N06",question="forging always preserves network",status="REJECTED",evidence="Li 30% vs 50%",reason="50% erases network and causes cracks/debonding",boundary="process-window constrained"),
 dict(result_id="N07",question="orientation dominates low-AR network strengthening",status="REJECTED_AS_GENERAL_RULE",evidence="Li2026",reason="rotation 13.9-18.6 MPa vs HP/GND ~75-96 MPa each",boundary="dominance requires high AR/intact interface")]
conf=[
 dict(snapshot_id=SNAP,conflict_id="C01",field_or_claim="size effect",source_a="KOO diameter",source_b="KOO AR",conflict="co-change",resolution="joint estimand",status="OPEN_STRUCTURAL_CONFOUNDING",severity="HIGH"),
 dict(snapshot_id=SNAP,conflict_id="C02",field_or_claim="agglomeration penalty",source_a="Bao distribution SD",source_b="Bao dose/porosity/phase",conflict="co-change",resolution="descriptive only",status="OPEN_STRUCTURAL_CONFOUNDING",severity="HIGH"),
 dict(snapshot_id=SNAP,conflict_id="C03",field_or_claim="architecture benefit",source_a="Wu FLSCR",source_b="Jiao two-scale",conflict="strength trade vs simultaneous gain",resolution="stratify; LOPO",status="RESOLVED_BY_STRATIFICATION",severity="HIGH"),
 dict(snapshot_id=SNAP,conflict_id="C04",field_or_claim="two-scale effect",source_a="Jiao architecture",source_b="Jiao added Ti5Si3",conflict="architecture/chemistry inseparable",resolution="paired association",status="OPEN_IDENTIFICATION_GAP",severity="HIGH"),
 dict(snapshot_id=SNAP,conflict_id="C05",field_or_claim="orientation factor",source_a="Bao measured .62-.64",source_b="Jiao .27/random .125 convention",conflict="definitions differ",resolution="no raw pooling",status="OPEN_DEFINITION_GAP",severity="MEDIUM"),
 dict(snapshot_id=SNAP,conflict_id="C06",field_or_claim="original source hash",source_a="file-library original",source_b="26 archives",conflict="member path/CRC/SHA absent in cloud build",resolution="local binding request",status="OPEN_PROVENANCE_GAP",severity="HIGH")]

archives=["00_统一上传总控与校验信息_20260712.zip","S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip"]+[f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1,9)]+["S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip"]+[f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1,4)]+[f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1,11)]
known={
 "S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip":("cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a","FULL_FILE_SHA256",515901682,7),
 "S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip":("97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809","INHERITED_CENTRAL_DIRECTORY_SHA256",515901786,7),
 "S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip":("16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f","INHERITED_CENTRAL_DIRECTORY_SHA256",515902128,9),
 "S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip":("04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9","INHERITED_CENTRAL_DIRECTORY_SHA256",515903238,11),
 "S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip":("5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728","INHERITED_CENTRAL_DIRECTORY_SHA256",515905052,17),
 "S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip":("e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847","INHERITED_CENTRAL_DIRECTORY_SHA256",515913392,38),
 "S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip":("36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485","INHERITED_CENTRAL_DIRECTORY_SHA256",515924832,69),
 "S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip":("9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd","INHERITED_CENTRAL_DIRECTORY_SHA256",515989228,246),
 "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip":("c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c","INHERITED_CENTRAL_DIRECTORY_SHA256",506137803,57191),
 "S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip":("a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a","INHERITED_CENTRAL_DIRECTORY_SHA256",515999572,244),
 "TITMC_V27_LIT_WEB_P003_OF_010.zip":("535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917","INHERITED_CENTRAL_DIRECTORY_SHA256",490379244,4610),
 "TITMC_V27_LIT_WEB_P004_OF_010.zip":("bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a","INHERITED_CENTRAL_DIRECTORY_SHA256",490620829,7747),
 "TITMC_V27_LIT_WEB_P005_OF_010.zip":("1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1","INHERITED_CENTRAL_DIRECTORY_SHA256",490762545,10068),
 "TITMC_V27_LIT_WEB_P006_OF_010.zip":("5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13","INHERITED_CENTRAL_DIRECTORY_SHA256",490902802,11778)}
ledger=[]
for i,n in enumerate(archives,1):
    if n.startswith("TITMC"):prio,role="P0_PRIMARY_CORPUS","original literature/XML/MD/DOCX/structured evidence"
    elif "DATA_FEATURES" in n:prio,role="P1_FROZEN_DATA","frozen matrices/TMC subsets/features"
    elif "HARNESS" in n:prio,role="P2_METHOD_HARNESS","reliability/canonicalization/UQ/AD/mechanism assets"
    elif n.startswith("S04"):prio,role="P3_ENGINEERING","staging/history/code"
    elif n.startswith("S02"):prio,role="P3_PLOTTING","web return/plotting"
    else:prio,role="P0_CONTROL","upload control/checksums"
    k=known.get(n)
    ledger.append(dict(snapshot_id=SNAP,input_id=f"SRC{i:02d}",source_name=n,source_type="ZIP",expected_path="/mnt/data/"+n,priority=prio,scope_role=role,registered="YES",direct_archive_bytes_streamed_in_cloud_builder="NO",opened_or_consumed="REGISTERED; PRIMARY PAPERS DEEP-READ THROUGH FILE LIBRARY" if prio=="P0_PRIMARY_CORPUS" else "REGISTERED_AND_SCOPED",terminal_use_status="USED_DIRECTLY" if prio=="P0_PRIMARY_CORPUS" else "USED_AS_METHOD_OR_REGISTRY_CONTEXT",source_hash=k[0] if k else "",source_hash_kind=k[1] if k else "MISSING_REQUIRES_LOCAL_BINDING",bytes=k[2] if k else "",member_count=k[3] if k else "",hash_status="INHERITED_AUDIT_FINGERPRINT_NOT_RESTREAMED" if k else "REQUESTED_IN_WEB_TO_LOCAL",notes="no package-member binding or original hash fabricated"))

arch=[dict(**e,architecture_contrast=next(m["contrast_type"] for m in pairs if m["pair_id"]==e["pair_id"]),identifiability="PAIRED_ASSOCIATION" if e["paper_uid"]=="WU2022" else "PAIRED_BUT_CHEMISTRY_DOSE_CONFOUNDED") for e in effects if e["pair_id"].startswith("WU_4volpct_") or e["pair_id"].startswith("WU_6volpct_") or e["pair_id"].startswith("JIAO_III_vs_I_") or e["pair_id"].startswith("JIAO_IV_vs_III_")]

csvout("INPUT_LEDGER.csv",ledger);csvout("REINFORCEMENT_GEOMETRY.csv",geom);csvout("ANALYSIS_COHORT.csv",props);csvout("PAIR_MATCHES.csv",pairs);csvout("EFFECT_ESTIMATES.csv",effects);csvout("HIERARCHICAL_RESULTS.csv",hier);csvout("DOSE_RESPONSE.csv",dose);csvout("INTERACTION_EFFECTS.csv",inter);csvout("HETEROGENEITY.csv",hetero);csvout("SENSITIVITY_ANALYSIS.csv",sens);csvout("NULL_NEGATIVE_RESULTS.csv",nulls);csvout("CONFLICT_LEDGER.csv",conf);csvout("ARCHITECTURE_EFFECTS.csv",arch);csvout("AGGLOMERATION_PENALTY.csv",agg+[agg_summary]);csvout("GEOMETRY_EVIDENCE.csv",[dict(snapshot_id=SNAP,paper_uid=s["paper_uid"],sample_uid=s["sample_uid"],doi=s["doi"],variable=v,value=s.get(v),measurement_mode=s["geometry_measurement_mode"],evidence_level=s["evidence_level"],source_locator=s["source_locator"],review_status="SOURCE_BOUND" if s.get(v) not in (None,"") else "NOT_REPORTED",notes=s["notes"]) for s in geom for v in ["diameter_um","length_um","aspect_ratio","orientation_factor","agglomeration_index_sd_pct","architecture","reinforcement_location"]])
csvout("SECONDARY_EVIDENCE_LEDGER.csv",[dict(source_id="SEC_QM32",source="QM32 load-transfer budget",use="AR×orientation triangulation",authority="SECONDARY",primary_override_allowed="NO"),dict(source_id="SEC_QM16",source="QM16 paired-effect package",use="cohort/dependency conventions",authority="SECONDARY",primary_override_allowed="NO"),dict(source_id="SEC_QM08",source="QM08 elongation-loss package",use="ductility-trade context",authority="SECONDARY",primary_override_allowed="NO"),dict(source_id="SEC_QM39",source="QM39 formula/feature audit",use="ALE/SHAP claim ceiling",authority="SECONDARY",primary_override_allowed="NO")])

# Figure data and plots.
f1=[];baseE=float(kd.loc[kd.aspect_ratio==18,"E"].iloc[0]);baseY=float(kd.loc[kd.aspect_ratio==18,"YS"].iloc[0])
for _,r in kd.iterrows():f1.append(dict(paper_uid="KOO2012",sample_uid=r.sample_uid,diameter_um=r.diameter_um,aspect_ratio=r.aspect_ratio,elastic_modulus_GPa=r.E,yield_strength_MPa=r.YS,relative_modulus_change_pct=(r.E/baseE-1)*100,relative_ys_change_pct=(r.YS/baseY-1)*100,evidence="MIXED_DIRECT_AND_FIGURE_DERIVED",support="1 vol.% same SPS; size/AR confounded"))
csvout("figure_data/fig1_size_performance_spline.csv",f1)

f2=[]
for eta in np.linspace(.125,.65,54):
    for ar0 in np.linspace(1,60,60):f2.append(dict(record_type="grid",aspect_ratio=float(ar0),orientation_factor=float(eta),delta_sigma_MPa_per_volpct=float(.5*900*.01*ar0*eta),paper_uid="REFERENCE_SURFACE",sample_uid="",support_flag="within_numeric_support" if 2.27<=ar0<=23 and .27<=eta<=.64 else "extrapolative_visualization"))
for p,u,ar0,eta in [("BAO2024","BAO_S1",19.2,.64),("BAO2024","BAO_S2",23,.62),("JIAO2019","JIAO_III_TiBw",2.27,.27)]:f2.append(dict(record_type="anchor",aspect_ratio=ar0,orientation_factor=eta,delta_sigma_MPa_per_volpct=.5*900*.01*ar0*eta,paper_uid=p,sample_uid=u,support_flag="source_anchor"))
csvout("figure_data/fig2_ar_orientation_surface.csv",f2)

ids=["WU_4volpct_ultimate_tensile_strength_MPa","WU_4volpct_fracture_elongation_pct","WU_6volpct_ultimate_tensile_strength_MPa","WU_6volpct_fracture_elongation_pct","JIAO_III_vs_I_ultimate_tensile_strength_MPa","JIAO_III_vs_I_fracture_elongation_pct","JIAO_IV_vs_III_ultimate_tensile_strength_MPa","JIAO_IV_vs_III_fracture_elongation_pct"]
labels=["Wu 4%: FLSCR vs HS — UTS","Wu 4%: FLSCR vs HS — fracture EL","Wu 6%: FLSCR vs FLSTR — UTS","Wu 6%: FLSCR vs FLSTR — fracture EL","Jiao: two-scale vs one-scale — UTS","Jiao: two-scale vs one-scale — EL","Jiao: coarse 8% vs fine 4% — UTS","Jiao: coarse 8% vs fine 4% — EL"]
f3=[]
for pid,lab in zip(ids,labels):
    e=emap[pid];f3.append(dict(comparison_id=pid,label=lab,paper_uid=e["paper_uid"],property=e["property"],percent_change=e["percent_change"],percent_ci95_low=e["percent_ci95_low"],percent_ci95_high=e["percent_ci95_high"],absolute_delta=e["absolute_delta"],unit=e["unit"],evidence_level=e["evidence_level"],confounding=e["residual_confounding"]))
csvout("figure_data/fig3_architecture_forest.csv",f3);csvout("figure_data/fig4_agglomeration_plasticity.csv",agg)

plot1='''from pathlib import Path\nimport numpy as np,pandas as pd,matplotlib.pyplot as plt\nfrom scipy.interpolate import PchipInterpolator\nb=Path(__file__).resolve().parents[1];d=pd.read_csv(b/'figure_data/fig1_size_performance_spline.csv').sort_values('diameter_um');x=d.diameter_um.to_numpy(float);xx=np.geomspace(x.min(),x.max(),300);fig,ax=plt.subplots(figsize=(7.2,4.8),constrained_layout=True)\nfor c,l,m in [('relative_modulus_change_pct','Elastic modulus','o'),('relative_ys_change_pct','Yield strength (figure-derived)','s')]:y=d[c].to_numpy(float);ax.plot(xx,PchipInterpolator(x,y)(xx),label=l);ax.scatter(x,y,marker=m,s=45)\nfor _,r in d.iterrows():ax.annotate(f"AR={r.aspect_ratio:.0f}",(r.diameter_um,r.relative_ys_change_pct),xytext=(4,5),textcoords='offset points',fontsize=8)\nax.set_xscale('log');ax.set_xlabel('TiBw diameter (µm)');ax.set_ylabel('Change relative to 1.0 µm / AR 18 (%)');ax.axhline(0,lw=.8);ax.set_title('Within-paper size–performance spline\\n1 vol.% TiBw; size and aspect ratio are confounded');ax.legend(frameon=False);ax.text(.01,.02,'Independent papers = 1; samples = 3; joint-geometry estimand',transform=ax.transAxes,fontsize=8)\nfor e in ['svg','pdf']:fig.savefig(b/'figures'/f'fig1_size_performance_spline.{e}',bbox_inches='tight')\nfig.savefig(b/'figures/fig1_size_performance_spline.png',dpi=600,bbox_inches='tight');plt.close(fig)\n'''
plot2='''from pathlib import Path\nimport numpy as np,pandas as pd,matplotlib.pyplot as plt\nb=Path(__file__).resolve().parents[1];d=pd.read_csv(b/'figure_data/fig2_ar_orientation_surface.csv');g=d[d.record_type=='grid'];a=d[d.record_type=='anchor'];p=g.pivot(index='orientation_factor',columns='aspect_ratio',values='delta_sigma_MPa_per_volpct');X,Y=np.meshgrid(p.columns.to_numpy(float),p.index.to_numpy(float));fig,ax=plt.subplots(figsize=(7.2,5.2),constrained_layout=True);cs=ax.contourf(X,Y,p.to_numpy(float),levels=16);cb=fig.colorbar(cs,ax=ax);cb.set_label('Modelled load-transfer increment (MPa per vol.%)');ax.scatter(a.aspect_ratio,a.orientation_factor,marker='x',s=70,lw=2,label='Source anchors')\nfor _,r in a.iterrows():ax.annotate(f"{r.paper_uid}:{r.sample_uid}",(r.aspect_ratio,r.orientation_factor),xytext=(4,4),textcoords='offset points',fontsize=8)\nax.set_xlabel('Aspect ratio');ax.set_ylabel('Orientation factor');ax.set_title('Aspect ratio × orientation conditional surface\\nMechanistic shear-lag reference, not empirical ALE or causal attribution');ax.legend(frameon=False);ax.text(.01,.01,'Reference matrix YS = 900 MPa; numeric anchor papers = 2',transform=ax.transAxes,fontsize=8)\nfor e in ['svg','pdf']:fig.savefig(b/'figures'/f'fig2_ar_orientation_surface.{e}',bbox_inches='tight')\nfig.savefig(b/'figures/fig2_ar_orientation_surface.png',dpi=600,bbox_inches='tight');plt.close(fig)\n'''
plot3='''from pathlib import Path\nimport numpy as np,pandas as pd,matplotlib.pyplot as plt\nb=Path(__file__).resolve().parents[1];d=pd.read_csv(b/'figure_data/fig3_architecture_forest.csv');y=np.arange(len(d))[::-1];x=d.percent_change.to_numpy(float);lo=d.percent_ci95_low.to_numpy(float);hi=d.percent_ci95_high.to_numpy(float);fig,ax=plt.subplots(figsize=(8.8,5.8),constrained_layout=True);ax.errorbar(x,y,xerr=np.vstack([x-lo,hi-x]),fmt='o',capsize=3);ax.axvline(0,lw=1);ax.set_yticks(y,d.label);ax.set_xlabel('Percent change in treatment architecture vs comparator (%)');ax.set_title('Paired spatial-architecture effects\\n95% intervals use reported SD and n=3; no causal pooling');ax.grid(axis='x',alpha=.25);ax.text(.01,.01,'Independent numeric papers = 2; contrasts = 4; outcomes = UTS and fracture elongation',transform=ax.transAxes,fontsize=8)\nfor e in ['svg','pdf']:fig.savefig(b/'figures'/f'fig3_architecture_forest.{e}',bbox_inches='tight')\nfig.savefig(b/'figures/fig3_architecture_forest.png',dpi=600,bbox_inches='tight');plt.close(fig)\n'''
plot4='''from pathlib import Path\nimport pandas as pd,matplotlib.pyplot as plt\nfrom scipy.stats import spearmanr\nb=Path(__file__).resolve().parents[1];d=pd.read_csv(b/'figure_data/fig4_agglomeration_plasticity.csv').sort_values('agglomeration_index_sd_pct');x=d.agglomeration_index_sd_pct.to_numpy(float);y=d.delta_uniform_elongation_vs_matrix_pp.to_numpy(float);rho,_=spearmanr(x,y);fig,ax=plt.subplots(figsize=(7.2,4.8),constrained_layout=True);ax.plot(x,y);ax.scatter(x,y,s=55)\nfor _,r in d.iterrows():ax.annotate(f"{r.sample_uid}; {r.reinforcement_vol_pct:g} vol.%",(r.agglomeration_index_sd_pct,r.delta_uniform_elongation_vs_matrix_pp),xytext=(4,5),textcoords='offset points',fontsize=8)\nax.axhline(0,lw=.8);ax.set_xlabel('TiBw spatial-distribution SD / agglomeration index (%)');ax.set_ylabel('Uniform-elongation change vs matrix (percentage points)');ax.set_title('Agglomeration index–plasticity penalty curve\\nOne-paper multi-confounded association');ax.text(.01,.02,f'Spearman ρ = {rho:.3f}; independent papers = 1; samples = 5',transform=ax.transAxes,fontsize=8)\nfor e in ['svg','pdf']:fig.savefig(b/'figures'/f'fig4_agglomeration_plasticity.{e}',bbox_inches='tight')\nfig.savefig(b/'figures/fig4_agglomeration_plasticity.png',dpi=600,bbox_inches='tight');plt.close(fig)\n'''
for n,c in [("plot_fig1_size_performance.py",plot1),("plot_fig2_ar_orientation.py",plot2),("plot_fig3_architecture_forest.py",plot3),("plot_fig4_agglomeration_penalty.py",plot4)]:text("plot_code/"+n,c);subprocess.run([sys.executable,str(OUT/"plot_code"/n)],check=True)

js("PLOT_SPECS.json",dict(window_id="QM20",snapshot_id=SNAP,language="English",formats=["SVG","PDF","PNG_600DPI"],plots=[dict(id="FIG1",data="figure_data/fig1_size_performance_spline.csv",code="plot_code/plot_fig1_size_performance.py",estimand="fixed-dose joint size/AR association",claim_ceiling="not independent size effect"),dict(id="FIG2",data="figure_data/fig2_ar_orientation_surface.csv",code="plot_code/plot_fig2_ar_orientation.py",estimand="mechanistic load-transfer surface",claim_ceiling="not empirical ALE/causal"),dict(id="FIG3",data="figure_data/fig3_architecture_forest.csv",code="plot_code/plot_fig3_architecture_forest.py",estimand="within-paper architecture contrasts",claim_ceiling="level-2 paired"),dict(id="FIG4",data="figure_data/fig4_agglomeration_plasticity.csv",code="plot_code/plot_fig4_agglomeration_penalty.py",estimand="within-paper monotone association",claim_ceiling="not independent penalty")]))

with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8",newline="\n") as f:
    for u,p in papers.items():f.write(canon(dict(record_type="paper_identity",snapshot_id=SNAP,paper_uid=u,**p,authority="PRIMARY_ORIGINAL",original_member_sha256=None,binding_status="DOI_AND_PAYLOAD_BOUND; ORIGINAL_MEMBER_HASH_REQUESTED"))+"\n")
    for r in geom:f.write(canon(dict(record_type="geometry_sample",**r,source_payload_sha256=hbytes(canon(r).encode())))+"\n")
    for r in effects:f.write(canon(dict(record_type="effect_estimate",**r,source_payload_sha256=hbytes(canon(r).encode())))+"\n")

opened=f'''# OPENED_FILES — QM20

`WINDOW=QM20 | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Primary originals deep-read
1. Koo et al. 2012 — DOI `10.1016/j.scriptamat.2011.12.024`; Table 1 and Figs. 3–4.
2. Bao et al. 2024 — DOI `10.1080/17452759.2024.2383287`; distribution/orientation/porosity/tensile/load-transfer evidence.
3. Wu et al. 2022 — DOI `10.1016/j.msea.2022.143645`; Tables 2–4 and Figs. 3, 7–13.
4. Jiao et al. 2019 — DOI `10.1016/j.powtec.2019.09.008`; Tables 1–3 and Figs. 1–9.
5. Li et al. 2026 — DOI `10.1016/j.jmst.2025.02.101`; network preservation, orientation, BGS/GND and fracture evidence.

## Dispatch/secondary evidence opened
QM20 MDU; QM32, QM16, QM08 and QM39 returned analyses. Secondary outputs never override originals.

All 26 uploaded archives are registered in `INPUT_LEDGER.csv`. Archive bytes were unavailable inside this isolated public build runner; registration/scoped use is separated from direct byte streaming. No member path, CRC or SHA was fabricated.
''';text("OPENED_FILES.md",opened)

uts=next(r for r in hier if r["analysis_id"].endswith("ultimate_tensile_strength_MPa"));el=next(r for r in hier if r["analysis_id"].endswith("fracture_elongation_pct"))
verdict=f'''# 00_EXECUTIVE_VERDICT — QM20

`WINDOW=QM20 | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

## Scientific verdict

1. **Size/AR:** At fixed 1 vol.% TiBw, Koo's diameter 1.0→0.1 µm and AR 18→58 series changes modulus 116→125 GPa (+7.76%) and figure-read YS about 900→1070 MPa (+18.89%). Diameter and AR are nearly perfectly anti-correlated (`r={corr:.4f}`); an independent size effect is `NOT_IDENTIFIABLE`.
2. **AR×orientation:** Source shear-lag physics is multiplicative. Bao's aligned AR≈19–23 anchors imply ~55–64 MPa per vol.% at a 900 MPa matrix reference; Jiao's AR=2.27, η=.27 anchor gives ~2.8 MPa per vol.%. Li attributes only 13.9–18.6 MPa of forging strength to rotation, versus ~75–96 MPa each from grain refinement and GND. The delivered surface is mechanistic, not empirical ALE or causal decomposition.
3. **Architecture:** Wu fixed-dose FLSCR gives ΔUTS=-33 MPa/ΔEL=+4.5 pp at 4 vol.% and ΔUTS=-93 MPa/ΔEL=+3.1 pp at 6 vol.%. Jiao two-scale vs one-scale gives ΔYS=+120 MPa, ΔUTS=+110 MPa, ΔEL=+1.8 pp but also adds 4 vol.% Ti5Si3. Paper-level UTS association is {uts['pooled_percent_change']:.2f}% and changes sign under LOPO; fracture-EL association is {el['pooled_percent_change']:.2f}% and remains positive under two-paper LOPO, still low-support.
4. **Agglomeration:** Bao's index 0.9→11.1 accompanies uniform EL 12.6→0%, Spearman ρ={rho:.3f}. This is a one-paper monotone association, not an independent penalty because dose, porosity, phase regime, AR and orientation co-vary.
5. **Mechanism/boundaries:** Fine intragranular Ti5Si3 stores dislocations and broadens deformation; continuous Ti-rich regions blunt/deflect cracks and raise work of fracture. Coarse connected grain-boundary Ti5Si3 and excessive forging localize strain, initiate cracks, destroy networks or debond interfaces.

## Scope
- Registered archives: {len(archives)}
- Primary originals: {len(papers)}
- Geometry rows: {len(geom)}
- Atomic property rows: {len(props)}
- Matched effects: {len(effects)}
- Figures: 4 × CSV/Python/SVG/PDF/600-dpi PNG
- Maximum claim level: 2

No Gold promotion, production-model registration or validated formulation was performed. The package is computationally complete but lacks the authoritative Q40 snapshot and original member hashes; terminal state is `CONTINUE_DATA_GAP`.
''';text("00_EXECUTIVE_VERDICT.md",verdict)

methods=f'''# METHODS — QM20

Snapshot `{SNAP}` is a deterministic DOI/evidence-payload snapshot. `ANALYSIS_COHORT.csv` is atomic at paper×sample×condition×property; geometry is separate. Effects are `ΔY`, `lnRR`, and `100[exp(lnRR)-1]`. Tier A pairs match paper/matrix/process/test; Tier B retains a declared chemistry/dose change. Reported SD and n=3 generate delta-method 95% intervals. Architecture synthesis averages dependent contrasts within paper, then applies 20,000 paper-cluster bootstrap resamples (seed {SEED}). With two numeric papers, tau²/prediction intervals are not estimable. LOPO and agglomeration leave-one-sample sensitivity are explicit. Koo size/AR is joint because of collinearity. AR×orientation is a source-formula conditional surface at reference matrix YS=900 MPa, not empirical ALE/PDP/SHAP or causal attribution. No full-composition Euclidean regression is performed, so no unsupported simplex adjustment is fabricated. No confirmatory multiplicity family was preregistered; intervals are descriptive and no FDR claim is made.
''';text("METHODS.md",methods)
text("LIMITATIONS.md","""# LIMITATIONS — QM20

1. Authoritative Q40/V29 snapshot absent in cloud runner.
2. Original archive member path/CRC/byte SHA absent.
3. Koo diameter and AR are collinear.
4. Numeric orientation factors are sparse and definition-dependent.
5. Bao agglomeration co-varies with dose/porosity/phase/AR/orientation.
6. Wu fixed-dose architecture still changes local concentration, region fraction, grain size and AR.
7. Jiao architecture adds Ti5Si3 chemistry/dose.
8. Li exact YS/UTS bar endpoints were not transcribed; only exact text/table/source-model quantities are used.
9. Two numeric architecture papers cannot identify a transferable random-effects law.
10. Analysis-only: no Gold/model/VALIDATED promotion.
""")
req=dict(window_id="QM20",snapshot_id=SNAP,status="CONTINUE_DATA_GAP",requests=[dict(priority=0,artifact="Q40_INPUT_SNAPSHOT and V29 ATOMIC_RECORDS/PROVENANCE/CONFLICT/EXCLUDED",reason="bind unique authority",acceptance="hash match and stable UIDs"),dict(priority=0,artifact="package member path, CRC32, size and SHA-256 for five DOI originals",reason="close byte provenance",acceptance="canonical member or duplicate group"),dict(priority=1,artifact="controlled orientation series at fixed matrix/dose/process/AR/interface",reason="identify orientation",acceptance="≥3 levels and ≥3 papers or factorial experiment"),dict(priority=1,artifact="fixed-dose/fixed-porosity agglomeration series plus raw images",reason="identify penalty",acceptance="replicate fields and spatial metrics"),dict(priority=1,artifact="raw masks for connectivity/gradient/inter-intragranular placement",reason="reproducible spatial descriptors",acceptance="scale bars, masks, connectivity/orientation outputs"),dict(priority=2,artifact="Li 2026 supplementary exact orientation/property values",reason="third quantitative paper",acceptance="table-level uncertainty")]);js("WEB_TO_LOCAL_REQUEST.json",req)
text("LOCAL_ABSORPTION_PROMPT.md",f'''# LOCAL_ABSORPTION_PROMPT — QM20

1. `unzip -t FINAL_QM20.zip`; verify `CHECKSUMS.sha256`.
2. Confirm snapshot `{SNAP}`; retain `ANALYSIS_ONLY/CONTINUE_DATA_GAP`.
3. Install `requirements.txt`; run `python analysis_code/recompute_qm20.py --base . --check-only` and `pytest -q tests`.
4. Bind each DOI to canonical archive member path, CRC32, size and original SHA-256; preserve payload hashes.
5. Reconcile with authoritative Q40/V29 records; resolve conflicts only from original PDF/XML/table/figure.
6. Register only QM20 analysis-layer CSVs. Never modify ACTIVE, Gold, schema, split authority or production registry.
7. Convert `WEB_TO_LOCAL_REQUEST.json` to recovery queue; issue a new immutable snapshot after closure.
8. Emit local receipt: package SHA, internal checksums, tests, snapshot/member bindings, conflicts and explicit no-promotion proof.
''')

recompute='''from pathlib import Path\nimport argparse,csv,hashlib,json,math\ndef H(p):\n h=hashlib.sha256()\n with p.open('rb') as f:\n  for b in iter(lambda:f.read(1048576),b''):h.update(b)\n return h.hexdigest()\ndef R(p):\n with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))\ndef main():\n a=argparse.ArgumentParser();a.add_argument('--base',default='.');a.add_argument('--check-only',action='store_true');x=a.parse_args();b=Path(x.base);co=R(b/'ANALYSIS_COHORT.csv');pa=R(b/'PAIR_MATCHES.csv');ef=R(b/'EFFECT_ESTIMATES.csv');assert len(co)==len({r['record_uid'] for r in co});ids={r['pair_id'] for r in pa};assert all(r['pair_id'] in ids for r in ef)\n for e in ef:\n  p=next(r for r in pa if r['pair_id']==e['pair_id']);assert math.isclose(float(p['treatment_value'])-float(p['control_value']),float(e['absolute_delta']),abs_tol=1e-9)\n n=0\n with (b/'CHECKSUMS.sha256').open(encoding='utf-8') as f:\n  for line in f:\n   d,r=line.rstrip('\\n').split('  ',1);assert H(b/r)==d,r;n+=1\n print(json.dumps({'pass':True,'atomic_rows':len(co),'pairs':len(pa),'effects':len(ef),'checksums_verified':n},sort_keys=True))\nif __name__=='__main__':main()\n''';text("analysis_code/recompute_qm20.py",recompute)
text("requirements.txt","matplotlib==3.9.2\nnumpy==2.1.3\npandas==2.2.3\npytest==8.3.4\nscipy==1.14.1\n")
text("acceptance_commands.md","""# Acceptance commands
```bash
python -m pip install -r requirements.txt
python analysis_code/recompute_qm20.py --base . --check-only
pytest -q tests
python plot_code/plot_fig1_size_performance.py
python plot_code/plot_fig2_ar_orientation.py
python plot_code/plot_fig3_architecture_forest.py
python plot_code/plot_fig4_agglomeration_penalty.py
```
""")
text("README.md",f"# FINAL_QM20\n\nSnapshot `{SNAP}`; five primary papers; 26 registered archives; {len(props)} atomic rows; {len(effects)} matched effects; four reproducible figure families. Claim ceiling level 2.\n\n{STATUS}\n")
text("FINAL_STATUS.txt",STATUS+"\n")
status=dict(window_id="QM20",snapshot_id=SNAP,input_mode="QUANT_EXECUTE/COHORT_BUILD",papers_seen=len(papers),papers_included=len(papers),independent_papers=len(papers),registered_source_archives=len(archives),atomic_rows=len(props),geometry_rows=len(geom),matched_pairs=len(pairs),effect_estimates=len(effects),plots_generated=4,plot_files_generated=12,open_conflicts=sum(r["status"].startswith("OPEN") for r in conf),claim_level_max=2,status="CONTINUE_DATA_GAP",next_action="bind Q40 snapshot/original member hashes and recover controlled orientation/agglomeration series",production_model_registered=False,gold_promoted=False);js("WINDOW_STATUS.json",status)

# Tests before manifest/checksums; workflow reruns after finalization.
tests='''from pathlib import Path\nimport csv,json\nB=Path(__file__).resolve().parents[1]\ndef R(n):\n with (B/n).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))\ndef test_atomic_unique():\n r=R('ANALYSIS_COHORT.csv');assert len(r)==len({x['record_uid'] for x in r})\ndef test_effect_links():\n p={x['pair_id'] for x in R('PAIR_MATCHES.csv')};assert all(x['pair_id'] in p for x in R('EFFECT_ESTIMATES.csv'))\ndef test_wu_fixed_dose():\n g={x['sample_uid']:x for x in R('REINFORCEMENT_GEOMETRY.csv')};assert float(g['WU_FLSCR10']['reinforcement_vol_pct'])==float(g['WU_HS4']['reinforcement_vol_pct']);assert float(g['WU_FLSCR15']['reinforcement_vol_pct'])==float(g['WU_FLSTR10']['reinforcement_vol_pct'])\ndef test_agglomeration_monotone():\n r=sorted([x for x in R('AGGLOMERATION_PENALTY.csv') if x['sample_uid']!='SUMMARY'],key=lambda x:float(x['agglomeration_index_sd_pct']));y=[float(x['uniform_elongation_pct']) for x in r];assert all(a>=b for a,b in zip(y,y[1:]))\ndef test_jiao_negative_boundary():\n e={x['pair_id']:x for x in R('EFFECT_ESTIMATES.csv')};assert float(e['JIAO_IV_vs_III_ultimate_tensile_strength_MPa']['absolute_delta'])==-200;assert float(e['JIAO_IV_vs_III_fracture_elongation_pct']['absolute_delta'])==-4\ndef test_authority_gates():\n s=json.loads((B/'WINDOW_STATUS.json').read_text());assert s['status']=='CONTINUE_DATA_GAP' and not s['gold_promoted'] and not s['production_model_registered'] and s['claim_level_max']==2\ndef test_four_plot_families():\n for stem in ['fig1_size_performance_spline','fig2_ar_orientation_surface','fig3_architecture_forest','fig4_agglomeration_plasticity']:\n  for e in ['svg','pdf','png']:assert (B/'figures'/f'{stem}.{e}').is_file()\ndef test_no_nested_zip():assert not list(B.rglob('*.zip'))\n''';text("tests/test_qm20.py",tests)
run=subprocess.run([sys.executable,"-m","pytest","-q",str(OUT/"tests")],capture_output=True,text=True,check=True);text("validation/pytest_output.txt",run.stdout+run.stderr);js("validation/BUILD_RECEIPT.json",dict(pass_=True,snapshot_id=SNAP,python=sys.version,atomic_rows=len(props),geometry_rows=len(geom),pairs=len(pairs),effects=len(effects),plots=4,plot_files=12,pytest="PASS",no_nested_zip=True))

required=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","REINFORCEMENT_GEOMETRY.csv","ARCHITECTURE_EFFECTS.csv","AGGLOMERATION_PENALTY.csv","GEOMETRY_EVIDENCE.csv"]
miss=[x for x in required if not (OUT/x).is_file()]
if miss:raise RuntimeError(miss)
if list(OUT.rglob('*.zip')):raise RuntimeError('nested zip')
manifest=dict(window_id="QM20",snapshot_id=SNAP,status="CONTINUE_DATA_GAP",generated_by="qm20_builder.py",seed=SEED,package_root="FINAL_QM20",no_nested_zip=True,checksum_convention="CHECKSUMS lists every file except itself",counts=status,files=[])
for p in sorted(x for x in OUT.rglob('*') if x.is_file() and x.name not in {'MANIFEST.json','CHECKSUMS.sha256'}):manifest["files"].append(dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=hfile(p)))
js("MANIFEST.json",manifest)
files=sorted(x for x in OUT.rglob('*') if x.is_file() and x.name!='CHECKSUMS.sha256');text("CHECKSUMS.sha256","\n".join(f"{hfile(p)}  {p.relative_to(OUT).as_posix()}" for p in files)+"\n")
print(f"WINDOW=QM20 | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD");print(STATUS)
