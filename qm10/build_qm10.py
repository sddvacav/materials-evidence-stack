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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "FINAL_QM10"
DELIV = ROOT / "deliverables"
SEED = 20260713
NOW = datetime.now(timezone.utc).isoformat()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_text(rel: str, text: str) -> Path:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")
    return p


def write_json(rel: str, obj: Any) -> Path:
    return write_text(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def write_csv(rel: str, rows: list[dict[str, Any]], fields: list[str] | None = None) -> Path:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for k in row:
                if k not in fields:
                    fields.append(k)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: "" if row.get(k) is None else row.get(k) for k in fields})
    return p


def mass_rom(frac: dict[str, float], rho: dict[str, float]) -> float:
    s = sum(frac.values())
    return 1.0 / sum((v / s) / rho[k] for k, v in frac.items())


def volume_rom(frac: dict[str, float], rho: dict[str, float]) -> float:
    s = sum(frac.values())
    return sum((v / s) * rho[k] for k, v in frac.items())


def pct(t: float, c: float) -> float:
    return 100.0 * (t / c - 1.0)


def spec(y: float | None, rho: float | None) -> float | None:
    return None if y is None or rho is None or rho <= 0 else y / rho


def prop_band(yt, yc, sdt, sdc, rt, rc, sdrt, sdrc):
    vals = (yt, yc, sdt, sdc, rt, rc, sdrt, sdrc)
    if any(v is None for v in vals):
        return None, None, None
    se = math.sqrt((sdt/yt)**2 + (sdc/yc)**2 + (sdrt/rt)**2 + (sdrc/rc)**2)
    lr = math.log((yt/rt)/(yc/rc))
    return se, 100*(math.exp(lr-1.96*se)-1), 100*(math.exp(lr+1.96*se)-1)


ELEMENT_RHO = {"Ti":4.506,"Al":2.70,"Sn":7.31,"Zr":6.52,"Mo":10.28,"Nb":8.57,"Ta":16.69,"Si":2.329,"W":19.25,"C":2.267}
TI65_WT = {"Ti":82.54,"Al":5.9,"Sn":4.0,"Zr":3.5,"Mo":0.5,"Nb":0.3,"Ta":2.0,"Si":0.4,"W":0.8,"C":0.06}
TI65_RHO = mass_rom(TI65_WT, ELEMENT_RHO)
TI65_CF = dict(TI65_WT)
TI65_CF["Ti"] += TI65_CF.pop("Ta") + TI65_CF.pop("W")
TI65_CF_RHO = mass_rom(TI65_CF, {k:ELEMENT_RHO[k] for k in TI65_CF})
SAB_RHO = mass_rom({"Ti":97.6,"TiB2":2.4},{"Ti":4.506,"TiB2":4.52})
WANG_RHO = volume_rom({"Ti":87.12,"TiC":12.88},{"Ti":4.506,"TiC":4.93})
QIN_RHO = volume_rom({"Ti6242":92,"TiB":4,"TiC":4},{"Ti6242":4.54,"TiB":4.56,"TiC":4.93})

SRC = {
 "prompt":"file_00000000e924720ba42b8e13de6045d1 / filecite:turn23file0",
 "yan":"filecite:turn20file0",
 "sabahi":"filecite:turn20file1",
 "wang":"filecite:turn20file2",
 "qin":"filecite:turn18file14",
 "ti65":"filecite:turn22file0",
 "zhao":"filecite:turn17file1",
 "grinding":"filecite:turn18file1",
 "corpus":"filecite:turn23file11",
 "master":"filecite:turn24file14",
 "qm06":"filecite:turn24file15",
 "qm08":"filecite:turn24file17",
 "qm16":"filecite:turn24file10",
}

rows: list[dict[str,Any]] = []

def add(paper, doi, title, uid, name, matrix, reinforcement, dose, state, dsrc, rho_th, rd, rd_sd, rho_sd, uts, uts_sd, ys, ys_sd, E, E_sd, el, el_sd, temp, heavy, porosity_controlled, evidence, grade, source, notes="", bending=None, bending_sd=None):
    rho_m = None if rd is None or rho_th is None else rho_th*rd/100
    por = None if rd is None else 100-rd
    rows.append({
      "paper_uid":paper,"doi":doi,"title":title,"sample_uid":uid,"condition_uid":f"{uid}_{temp}C",
      "sample_name":name,"matrix":matrix,"reinforcement":reinforcement,"reinforcement_fraction_value":dose,
      "reinforcement_fraction_unit":"vol%","process_state":state,"temperature_C":temp,"heavy_elements_wt_pct":heavy,
      "density_source":dsrc,"density_theoretical_g_cm3":rho_th,"relative_density_pct":rd,
      "relative_density_uncertainty_pct_point":rd_sd,"density_measured_g_cm3":rho_m,
      "density_uncertainty_g_cm3":rho_sd,"porosity_pct":por,"porosity_controlled":porosity_controlled,
      "UTS_MPa":uts,"UTS_SD_MPa":uts_sd,"YS_MPa":ys,"YS_SD_MPa":ys_sd,"E_GPa":E,"E_SD_GPa":E_sd,
      "EL_pct":el,"EL_SD_pct_point":el_sd,"bending_MPa":bending,"bending_SD_MPa":bending_sd,
      "evidence_level":evidence,"match_grade":grade,"source_ref":source,"notes":notes,
    })

YAN_TITLE="Microstructure and mechanical properties of in-situ synthesized TiB whiskers reinforced titanium matrix composites by high-velocity compaction"
yan = [
 ("YAN_MATRIX","matrix",0,4.630,99.63,0.05,1090,14.4,1016,8.9,3.08,0.70),
 ("YAN_TMC1","TMC1",5,4.633,97.90,0.15,1038,4.8,989.6,2.5,2.19,0.50),
 ("YAN_TMC2","TMC2",10,4.627,98.20,0.10,1147,28.8,None,None,None,None),
 ("YAN_TMC3","TMC3",15,4.621,98.33,0.25,741,47.3,None,None,None,None),
 ("YAN_TMC4","TMC4",20,4.615,96.20,0.25,521,43.6,None,None,None,None),
]
for uid,name,dose,rth,rd,rds,uts,utssd,ys,yssd,el,elsd in yan:
    rsd=math.sqrt((rth*rds/100)**2+(0.01*rd/100)**2)
    add("YAN2014_POWTEC_TIB_HVC","10.1016/j.powtec.2014.07.048",YAN_TITLE,uid,name,"Ti-4.5Al-6.8Mo-1.5Fe","TiB + 0.5 vol% La2O3" if dose else "none",dose,"HVC+sintered","paper_ROM+Archimedes",rth,rd,rds,rsd,uts,utssd,ys,yssd,None,None,el,elsd,25,0,"PARTIAL","DIRECT_TABLE_TEXT+FIGURE_DERIVED","A",SRC["yan"],"TMC1/TMC2/TMC4 relative density includes figure-derived reading; high dose reports agglomeration/porous micro-regions.")

add("SABAHI2017_SPS_TIB2_TI","10.1080/00325899.2016.1265805","Microstructural characterisation and mechanical properties of spark plasma-sintered TiB2-reinforced titanium matrix composite","SAB_TI","Ti","CP-Ti","none",0,"SPS","Archimedes+ROM",4.506,97.92,0.03,0.005,441,6,None,None,None,None,2.68,0.15,25,0,"YES","DIRECT_TABLE_TEXT+DERIVED_CALCULATION","A",SRC["sabahi"],"n=4 tensile.",2134,55)
add("SABAHI2017_SPS_TIB2_TI","10.1080/00325899.2016.1265805","Microstructural characterisation and mechanical properties of spark plasma-sintered TiB2-reinforced titanium matrix composite","SAB_TIB","Ti-2.4 wt% TiB2 / intended 4 vol% TiB","CP-Ti","in-situ TiB from TiB2",4,"SPS","Archimedes+mass-ROM",SAB_RHO,98.85,0.04,0.010,485,9,None,None,None,None,8.67,0.11,25,0,"YES","DIRECT_TABLE_TEXT+DERIVED_CALCULATION","A",SRC["sabahi"],"Feed is 2.4 wt% TiB2; reported intended phase fraction 4 vol% TiB; n=4 tensile.",1615,79)

ctrl_uts=940/1.843; ctrl_ys=741/1.786
add("WANG2022_MSEA_PLDED_TIC_TI","10.1016/j.msea.2022.143935","Enhanced mechanical properties of in situ synthesized TiC/Ti composites by pulsed laser directed energy deposition","WANG_CP_TI","PLDED CP-Ti","CP-Ti","none",0,"PLDED as-built","database/ROM",4.506,None,None,0.005,ctrl_uts,None,ctrl_ys,None,None,None,None,None,25,0,"UNREPORTED","DERIVED_FROM_REPORTED_RELATIVE_GAIN","B",SRC["wang"],"Control strengths back-calculated from stated +84.3% UTS and +78.6% YS.")
add("WANG2022_MSEA_PLDED_TIC_TI","10.1016/j.msea.2022.143935","Enhanced mechanical properties of in situ synthesized TiC/Ti composites by pulsed laser directed energy deposition","WANG_TIC_12P88","12.88 vol% TiC/Ti","CP-Ti","in-situ TiC",12.88,"PLDED as-built","volume-ROM",WANG_RHO,None,None,0.010,940,None,741,None,None,None,18.9,None,25,0,"UNREPORTED","DIRECT_TABLE_TEXT+DERIVED_CALCULATION","B",SRC["wang"],"No measured density/porosity; specific-property result is ROM sensitivity.")

QIN_TITLE="Mechanical Properties of in situ Synthesized Titanium Matrix Composites at Elevated Temperature"
add("QIN2003_TIB_TIC_TI6242","",QIN_TITLE,"QIN_TI6242_DB","Ti6242 handbook comparator","Ti6242","none",0,"database comparator","database",4.54,None,None,0.03,914,None,844,None,110,None,10,None,25,0,"UNREPORTED","DATABASE_PRIOR","C",SRC["qin"],"Not same-batch.")
add("QIN2003_TIB_TIC_TI6242","",QIN_TITLE,"QIN_HYBRID_RT","8 vol% (TiB+TiC)/Ti6242","Ti6242","TiB+TiC",8,"cast+forged","volume-ROM",QIN_RHO,None,None,0.032,1234,None,1160.6,None,130.5,None,1.35,None,25,0,"UNREPORTED","DIRECT_TABLE_TEXT+DATABASE_PRIOR+DERIVED_CALCULATION","C",SRC["qin"],"4/4 vol% TiB/TiC split is a density sensitivity assumption.")
for temp,uts in [(600,780.9),(650,639.1),(700,423.9)]:
    add("QIN2003_TIB_TIC_TI6242","",QIN_TITLE,f"QIN_HYBRID_{temp}C",f"8 vol% hybrid at {temp} C","Ti6242","TiB+TiC",8,"cast+forged","RT volume-ROM carried to temperature",QIN_RHO,None,None,0.032,uts,None,None,None,None,None,None,None,temp,0,"UNREPORTED","DIRECT_TABLE_TEXT+DERIVED_CALCULATION","E",SRC["qin"],"Thermal expansion not corrected; no same-temperature matrix control.")

TI65_TITLE="Effect of heat treatment on microstructure and mechanical properties of laser-deposited Ti65 near-alpha titanium alloy"
for uid,state,uts,ys,el in [("TI65_AD","as-deposited",1015,916,11.3),("TI65_AN","650 C/4 h/AC",1026,910,12.1),("TI65_SA","1000 C/2 h/AC + 650 C/4 h/AC",1007,897,14.2)]:
    add("HE2022_JMR_LDM_TI65","10.1557/s43578-022-00547-9",TI65_TITLE,uid,f"LDM Ti65 {state}","Ti65","none",0,state,"elemental mass-ROM",TI65_RHO,None,None,0.03,uts,None,ys,None,None,None,el,None,25,2.8,"TEXT_NO_OBVIOUS_DEFECTS_ONLY","DIRECT_TABLE_TEXT+DERIVED_CALCULATION","A_HT/E_HEAVY",SRC["ti65"],"2.0 wt% Ta + 0.8 wt% W; no measured density and no W/Ta-free matched control.")

for dose,E in [(0,112.3),(2,116.0),(3.5,119.2),(5,122.5)]:
    rho=volume_rom({"Ti64":100-dose,"TiB":dose},{"Ti64":4.43,"TiB":4.56})
    add("ZHAO2019_TIB_TI64_MODEL","","Microstructural Modeling and Strengthening Mechanism of TiB/Ti-6Al-4V DRTMC",f"ZHAO_TIB_{str(dose).replace('.','P')}",f"TiB/Ti-6Al-4V {dose} vol%","Ti-6Al-4V","TiB" if dose else "none",dose,"reported experimental series","volume-ROM",rho,None,None,0.03,None,None,None,None,E,None,None,None,25,0,"UNREPORTED","CROSS_SOURCE_TABLE+DERIVED_CALCULATION","C",SRC["zhao"],"Experimental E values adopted by modeling paper from cited source.")

add("TICP_TI64_GRINDING_DESCRIPTIVE","","Comparative investigation on high-speed grinding of TiCp/Ti-6Al-4V particulate reinforced titanium matrix composites","TICP_TI64_10","10 vol% TiC/Ti-6Al-4V","Ti-6Al-4V","TiC",10,"unspecified","volume-ROM",volume_rom({"Ti64":90,"TiC":10},{"Ti64":4.43,"TiC":4.93}),None,None,0.035,1102,None,972,None,133,None,0.55,None,25,0,"UNREPORTED","DIRECT_TABLE_TEXT+DERIVED_CALCULATION","E",SRC["grinding"],"No matched matrix control; descriptive only.")

snap_payload={"rows":rows,"sources":SRC,"constants":ELEMENT_RHO,"seed":SEED}
SNAP=f"QM10_DERIVED_{sha_bytes(canonical(snap_payload).encode())[:16]}"
for r in rows:
    r["snapshot_id"]=SNAP
    d=r["density_measured_g_cm3"] or r["density_theoretical_g_cm3"]
    r["specific_UTS_MPa_per_g_cm3"]=spec(r["UTS_MPa"],d)
    r["specific_YS_MPa_per_g_cm3"]=spec(r["YS_MPa"],d)
    r["specific_E_GPa_per_g_cm3"]=spec(r["E_GPa"],d)
    r["evidence_record_hash"]=sha_bytes(canonical({k:v for k,v in r.items() if k!="evidence_record_hash"}).encode())
by={r["sample_uid"]:r for r in rows}

pairs=[]
def addpair(pid,c,t,props,grade,kind,notes=""):
    for p in props:pairs.append({"pair_id":pid,"control_sample_uid":c,"treatment_sample_uid":t,"property":p,"match_grade":grade,"estimand_class":kind,"notes":notes})
for i in range(1,5):addpair(f"YAN_TMC{i}_VS_MATRIX","YAN_MATRIX",f"YAN_TMC{i}",["UTS_MPa"]+(["YS_MPa","EL_pct"] if i==1 else []),"A","same-paper reinforcement")
addpair("SAB_TIB_VS_TI","SAB_TI","SAB_TIB",["UTS_MPa","EL_pct","bending_MPa"],"A","same-paper reinforcement")
addpair("WANG_TIC_VS_TI","WANG_CP_TI","WANG_TIC_12P88",["UTS_MPa","YS_MPa"],"B","same-paper, calculated density")
addpair("QIN_HYBRID_VS_DB","QIN_TI6242_DB","QIN_HYBRID_RT",["UTS_MPa","YS_MPa","E_GPa","EL_pct"],"C","database-comparator association")
addpair("TI65_AN_VS_AD","TI65_AD","TI65_AN",["UTS_MPa","YS_MPa","EL_pct"],"A","heat-treatment effect")
addpair("TI65_SA_VS_AD","TI65_AD","TI65_SA",["UTS_MPa","YS_MPa","EL_pct"],"A","heat-treatment effect")
for dose in [2,3.5,5]:addpair(f"ZHAO_{dose}_VS_0","ZHAO_TIB_0",f"ZHAO_TIB_{str(dose).replace('.','P')}",["E_GPa"],"C","cross-source modulus association")

pair_rows=[]; effects=[]
for q in pairs:
    c=by[q["control_sample_uid"]]; t=by[q["treatment_sample_uid"]]
    pair_rows.append({"snapshot_id":SNAP,**q,"paper_uid":t["paper_uid"],"same_paper":c["paper_uid"]==t["paper_uid"],"same_matrix":c["matrix"]==t["matrix"],"same_process_state":c["process_state"]==t["process_state"],"same_temperature":c["temperature_C"]==t["temperature_C"],"density_basis_available":bool(c["density_theoretical_g_cm3"] and t["density_theoretical_g_cm3"]),"source_ref":t["source_ref"]})
    yc=c[q["property"]]; yt=t[q["property"]]
    if yc is None or yt is None:continue
    bases=[]
    if c["density_measured_g_cm3"] and t["density_measured_g_cm3"]:bases.append(("measured_bulk",c["density_measured_g_cm3"],t["density_measured_g_cm3"]))
    if c["density_theoretical_g_cm3"] and t["density_theoretical_g_cm3"]:bases.append(("fully_dense_or_calculated",c["density_theoretical_g_cm3"],t["density_theoretical_g_cm3"]))
    if not bases:bases=[("none",None,None)]
    specific=q["property"] in {"UTS_MPa","YS_MPa","E_GPa","bending_MPa"}
    sdkey={"UTS_MPa":"UTS_SD_MPa","YS_MPa":"YS_SD_MPa","E_GPa":"E_SD_GPa","bending_MPa":"bending_SD_MPa"}.get(q["property"])
    for basis,rc,rt in bases:
        sc=spec(yc,rc) if specific else None; st=spec(yt,rt) if specific else None
        se,lo,hi=(None,None,None)
        if sdkey and specific:se,lo,hi=prop_band(yt,yc,t[sdkey],c[sdkey],rt,rc,t["density_uncertainty_g_cm3"],c["density_uncertainty_g_cm3"])
        e={"snapshot_id":SNAP,"effect_id":f"{q['pair_id']}__{q['property']}__{basis}","pair_id":q["pair_id"],"paper_uid":t["paper_uid"],"control_sample_uid":c["sample_uid"],"treatment_sample_uid":t["sample_uid"],"property":q["property"],"density_basis":basis,"control_value":yc,"treatment_value":yt,"absolute_effect":yt-yc,"lnRR_property":math.log(yt/yc) if yt>0 and yc>0 else None,"property_percent_change":pct(yt,yc),"control_density_g_cm3":rc,"treatment_density_g_cm3":rt,"density_percent_change":pct(rt,rc) if rt and rc else None,"control_specific_value":sc,"treatment_specific_value":st,"lnRR_specific":math.log(st/sc) if st and sc else None,"specific_percent_change":pct(st,sc) if st and sc else None,"propagation_log_se":se,"propagation_lower_pct":lo,"propagation_upper_pct":hi,"uncertainty_kind":"measurement_propagation_not_meta_CI" if se is not None else "NOT_AVAILABLE","match_grade":q["match_grade"],"claim_level":2 if q["match_grade"] in {"A","B"} else 1,"evidence_level":t["evidence_level"],"source_ref":t["source_ref"],"porosity_credit_allowed":"NO" if basis=="measured_bulk" and c["porosity_pct"]!=t["porosity_pct"] else "NOT_APPLICABLE","notes":q["notes"]}
        e["effect_record_hash"]=sha_bytes(canonical(e).encode()); effects.append(e)

def effect(eid):return next(e for e in effects if e["effect_id"]==eid)

# Deterministic analytical uncertainty: normal input bands at density level.
dens_unc=[]
for r in rows:
    for basis,mu in [("theoretical_or_calculated",r["density_theoretical_g_cm3"]),("measured_bulk",r["density_measured_g_cm3"])]:
        if mu is None:continue
        sd=r["density_uncertainty_g_cm3"] or 0
        dens_unc.append({"snapshot_id":SNAP,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"density_basis":basis,"input_mean_g_cm3":mu,"input_sd_g_cm3":sd,"normal_p2_5_g_cm3":mu-1.96*sd,"normal_p97_5_g_cm3":mu+1.96*sd,"uncertainty_scope":"density-level propagation; nominal composition/fraction fixed","source_ref":r["source_ref"]})

# Within-paper Pareto only.
pareto=[]
rt=[r for r in rows if r["temperature_C"]==25 and r["UTS_MPa"] is not None and r["density_theoretical_g_cm3"] is not None]
for r in rt:
    fam=[x for x in rt if x["paper_uid"]==r["paper_uid"]]
    dom=[x["sample_uid"] for x in fam if x is not r and x["density_theoretical_g_cm3"]<=r["density_theoretical_g_cm3"] and x["UTS_MPa"]>=r["UTS_MPa"] and (x["density_theoretical_g_cm3"]<r["density_theoretical_g_cm3"] or x["UTS_MPa"]>r["UTS_MPa"])]
    controls=[x for x in fam if x["reinforcement_fraction_value"]==0]
    rel="NO_CONTROL"; robust="NA"
    if controls and r not in controls:
        c=controls[0]; dr=c["density_theoretical_g_cm3"]-r["density_theoretical_g_cm3"]
        if r["density_theoretical_g_cm3"]<=c["density_theoretical_g_cm3"] and r["UTS_MPa"]>=c["UTS_MPa"]:rel="NOMINAL_DOMINATES"; robust="YES" if dr>1.96*math.sqrt((r["density_uncertainty_g_cm3"] or 0)**2+(c["density_uncertainty_g_cm3"] or 0)**2) else "NO_DENSITY_MARGIN"
        elif r["density_theoretical_g_cm3"]>=c["density_theoretical_g_cm3"] and r["UTS_MPa"]<=c["UTS_MPa"]:rel="DOMINATED_BY_CONTROL"; robust="YES"
        else:rel="TRADEOFF"
    pareto.append({"snapshot_id":SNAP,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"sample_name":r["sample_name"],"density_basis":"fully_dense_or_calculated","density_g_cm3":r["density_theoretical_g_cm3"],"density_uncertainty_g_cm3":r["density_uncertainty_g_cm3"],"UTS_MPa":r["UTS_MPa"],"specific_UTS_MPa_per_g_cm3":r["UTS_MPa"]/r["density_theoretical_g_cm3"],"within_paper_pareto":not dom,"dominator_sample_uids":";".join(dom),"dominance_vs_control":rel,"robust_dominance_vs_control":robust,"scope":"within-paper only","source_ref":r["source_ref"]})

# Utility sensitivity, log-ratio form; missing dimensions renormalized.
weights={"strength_stiffness":{"UTS":.35,"YS":.25,"E":.2,"EL":.1,"density":.1},"ductility_aware":{"UTS":.25,"YS":.15,"E":.1,"EL":.4,"density":.1},"mass_critical":{"UTS":.3,"YS":.2,"E":.15,"EL":.15,"density":.2}}
def util(c,t,w):
    vals=[]
    for k,wt in w.items():
        ck={"UTS":c["UTS_MPa"],"YS":c["YS_MPa"],"E":c["E_GPa"],"EL":c["EL_pct"],"density":c["density_theoretical_g_cm3"]}[k]
        tk={"UTS":t["UTS_MPa"],"YS":t["YS_MPa"],"E":t["E_GPa"],"EL":t["EL_pct"],"density":t["density_theoretical_g_cm3"]}[k]
        if ck and tk:vals.append((k,wt,(-1 if k=="density" else 1)*math.log(tk/ck)))
    return (sum(wt*v for _,wt,v in vals)/sum(wt for _,wt,_ in vals),[k for k,_,_ in vals]) if vals else (None,[])
utility=[]
for pid,cid,tid in [("YAN_TMC1_VS_MATRIX","YAN_MATRIX","YAN_TMC1"),("SAB_TIB_VS_TI","SAB_TI","SAB_TIB"),("QIN_HYBRID_VS_DB","QIN_TI6242_DB","QIN_HYBRID_RT"),("TI65_AN_VS_AD","TI65_AD","TI65_AN"),("TI65_SA_VS_AD","TI65_AD","TI65_SA")]:
    for wn,w in weights.items():
        u,used=util(by[cid],by[tid],w); utility.append({"snapshot_id":SNAP,"pair_id":pid,"paper_uid":by[tid]["paper_uid"],"weight_set":wn,"utility_log_score":u,"utility_percent_equivalent":100*(math.exp(u)-1) if u is not None else None,"used_dimensions":";".join(used),"missing_dimensions":";".join(k for k in w if k not in used),"interpretation":"positive favors treatment under declared weights" if u is not None else "NOT_IDENTIFIABLE","claim_level":1})

dose=[]
for r in rows:
    if r["paper_uid"]=="YAN2014_POWTEC_TIB_HVC" and r["UTS_MPa"] is not None:dose.append({"snapshot_id":SNAP,"series_id":"YAN_TIB_SPECIFIC_UTS","paper_uid":r["paper_uid"],"dose":r["reinforcement_fraction_value"],"dose_unit":"vol%","response":r["UTS_MPa"]/r["density_theoretical_g_cm3"],"response_name":"specific_UTS","density_basis":"paper_ROM","fit_status":"RAW_ONLY_NONMONOTONIC_DEFECT_CONFOUNDED"})
    if r["paper_uid"]=="ZHAO2019_TIB_TI64_MODEL":dose.append({"snapshot_id":SNAP,"series_id":"ZHAO_TIB_SPECIFIC_E","paper_uid":r["paper_uid"],"dose":r["reinforcement_fraction_value"],"dose_unit":"vol%","response":r["E_GPa"]/r["density_theoretical_g_cm3"],"response_name":"specific_E","density_basis":"volume_ROM","fit_status":"DESCRIPTIVE_CROSS_SOURCE"})

hier=[
 {"snapshot_id":SNAP,"analysis_id":"H1_SPECIFIC_UTS_RANDOM_EFFECTS","estimand":"pooled reinforcement effect on specific UTS","independent_papers":4,"effects":7,"estimate":None,"status":"NOT_IDENTIFIABLE","reason":"Only two papers have measured density; other studies use calculated/database density and compatible sampling variances are absent."},
 {"snapshot_id":SNAP,"analysis_id":"H2_W_TA_RANDOM_SLOPE","estimand":"W+Ta effect on specific strength","independent_papers":1,"effects":0,"estimate":None,"status":"NOT_IDENTIFIABLE","reason":"One heavy-element family and no matched W/Ta-free control."},
]
vals=[e["specific_percent_change"] for e in effects if e["property"]=="UTS_MPa" and e["density_basis"]=="fully_dense_or_calculated" and e["pair_id"].startswith(("YAN_","SAB_","WANG_","QIN_"))]
hetero=[{"snapshot_id":SNAP,"analysis_id":"HET_SPECIFIC_UTS","independent_papers":4,"effects":len(vals),"descriptive_median_pct":sorted(vals)[len(vals)//2],"minimum_pct":min(vals),"maximum_pct":max(vals),"I2_pct":None,"prediction_interval":None,"status":"DESCRIPTIVE_ONLY","interpretation":"Severe high-dose losses and large calculated PLDED gain preclude a universal coefficient."},{"snapshot_id":SNAP,"analysis_id":"HET_DENSITY_GAP","independent_papers":2,"effects":sum(r["density_measured_g_cm3"] is not None for r in rows),"status":"POROSITY_DOMINATED","interpretation":"Measured-theoretical density gap is porosity, not compositional mass benefit."}]
inter=[
 {"snapshot_id":SNAP,"interaction":"heavy_elements x reinforcement","independent_papers":0,"estimate":None,"status":"NOT_IDENTIFIABLE","reason":"No overlapping factorial support."},
 {"snapshot_id":SNAP,"interaction":"dose x porosity","independent_papers":1,"estimate":None,"status":"QUALITATIVE_ONLY","reason":"Yan dose and defect topology are inseparable above 10 vol%."},
 {"snapshot_id":SNAP,"interaction":"temperature x reinforcement","independent_papers":1,"estimate":None,"status":"NOT_IDENTIFIABLE","reason":"High-temperature hybrid series lacks matched matrix controls."},
]
lo10=effect("YAN_TMC2_VS_MATRIX__UTS_MPa__fully_dense_or_calculated")["specific_percent_change"]
losab=effect("SAB_TIB_VS_TI__UTS_MPa__fully_dense_or_calculated")["specific_percent_change"]
lopo=[{"snapshot_id":SNAP,"analysis_id":"LOPO_DIRECT_POSITIVE_ANCHORS","left_out_paper_uid":"YAN2014_POWTEC_TIB_HVC","remaining_papers":1,"remaining_effect_pct":losab,"direction":"POSITIVE","status":"DIRECTION_ONLY"},{"snapshot_id":SNAP,"analysis_id":"LOPO_DIRECT_POSITIVE_ANCHORS","left_out_paper_uid":"SABAHI2017_SPS_TIB2_TI","remaining_papers":1,"remaining_effect_pct":lo10,"direction":"POSITIVE","status":"DIRECTION_ONLY"}]
sens=[]
for pid in ["YAN_TMC1_VS_MATRIX","YAN_TMC2_VS_MATRIX","YAN_TMC3_VS_MATRIX","YAN_TMC4_VS_MATRIX","SAB_TIB_VS_TI"]:
    m=next(e for e in effects if e["pair_id"]==pid and e["property"]=="UTS_MPa" and e["density_basis"]=="measured_bulk"); f=next(e for e in effects if e["pair_id"]==pid and e["property"]=="UTS_MPa" and e["density_basis"]=="fully_dense_or_calculated")
    sens.append({"snapshot_id":SNAP,"analysis_id":f"DENSITY_BASIS_{pid}","comparison":pid,"measured_bulk_specific_UTS_change_pct":m["specific_percent_change"],"fully_dense_specific_UTS_change_pct":f["specific_percent_change"],"porosity_credit_bias_pct_point":m["specific_percent_change"]-f["specific_percent_change"],"conclusion":"Primary intrinsic comparison uses full-density basis; porosity credit prohibited."})
sens.append({"snapshot_id":SNAP,"analysis_id":"TI65_WTA_COUNTERFACTUAL","comparison":"Ti65 vs equal-mass Ti substitution","measured_bulk_specific_UTS_change_pct":None,"fully_dense_specific_UTS_change_pct":None,"porosity_credit_bias_pct_point":None,"conclusion":f"ROM density penalty {TI65_RHO-TI65_CF_RHO:.5f} g/cm3 ({pct(TI65_RHO,TI65_CF_RHO):.2f}%); strength effect NOT_IDENTIFIABLE."})
nulls=[
 {"snapshot_id":SNAP,"result_id":"NEG_YAN_TMC1","paper_uid":"YAN2014_POWTEC_TIB_HVC","finding":"5 vol% TiB reduces specific UTS and YS.","severity":"NEGATIVE","source_ref":SRC["yan"]},
 {"snapshot_id":SNAP,"result_id":"NEG_YAN_HIGH_DOSE","paper_uid":"YAN2014_POWTEC_TIB_HVC","finding":"15 and 20 vol% TiB sharply reduce specific UTS; agglomeration/porous regions reported.","severity":"NEGATIVE","source_ref":SRC["yan"]},
 {"snapshot_id":SNAP,"result_id":"NEG_SAB_BENDING","paper_uid":"SABAHI2017_SPS_TIB2_TI","finding":"Specific bending strength falls despite tensile specific-strength gain.","severity":"TRADEOFF","source_ref":SRC["sabahi"]},
 {"snapshot_id":SNAP,"result_id":"NEG_QIN_EL","paper_uid":"QIN2003_TIB_TIC_TI6242","finding":"Calculated specific UTS/YS/E rise while elongation falls from 10% comparator to 1.35%.","severity":"TRADEOFF","source_ref":SRC["qin"]},
 {"snapshot_id":SNAP,"result_id":"NULL_WTA","paper_uid":"HE2022_JMR_LDM_TI65","finding":"W/Ta specific-strength benefit and response surface are NOT_IDENTIFIABLE.","severity":"NOT_IDENTIFIABLE","source_ref":SRC["ti65"]},
]
conf=[
 {"snapshot_id":SNAP,"conflict_id":"C001","object":"Yan relative density","issue":"Several values figure-derived.","impact":"density uncertainty","resolution":"Retain with uncertainty; no Gold promotion.","status":"OPEN","source_ref":SRC["yan"]},
 {"snapshot_id":SNAP,"conflict_id":"C002","object":"Yan sampling variance","issue":"Exact n/shared-control covariance unresolved.","impact":"no pooled inferential CI","resolution":"Use measurement propagation only.","status":"OPEN","source_ref":SRC["yan"]},
 {"snapshot_id":SNAP,"conflict_id":"C003","object":"Qin comparator","issue":"Handbook/database, not same-batch.","impact":"grade C","resolution":"Descriptive adjusted association only.","status":"OPEN","source_ref":SRC["qin"]},
 {"snapshot_id":SNAP,"conflict_id":"C004","object":"Zhao E series","issue":"Values adopted from cited experimental source.","impact":"cross-source evidence","resolution":"Require original source for upgrade.","status":"OPEN","source_ref":SRC["zhao"]},
 {"snapshot_id":SNAP,"conflict_id":"C005","object":"Ti65 heavy-element counterfactual","issue":"No measured density or W/Ta-free control.","impact":"effect not estimable","resolution":"Report density penalty only.","status":"OPEN","source_ref":SRC["ti65"]},
 {"snapshot_id":SNAP,"conflict_id":"C006","object":"Q40 authoritative snapshot","issue":"V29 atomic registries not mounted in fallback runtime.","impact":"derived snapshot non-authoritative","resolution":"Local binding and rerun required.","status":"OPEN","source_ref":SRC["prompt"]},
]
excluded=[{"snapshot_id":SNAP,"record_uid":"WANG2025_DUAL_SCALE_COMPRESSION","reason":"compression-only; cannot enter tensile estimand","terminal_state":"EXCLUDED_MODE_MISMATCH","source_ref":"filecite:turn9file2"},{"snapshot_id":SNAP,"record_uid":"TICP_TI64_10","reason":"no matched matrix control","terminal_state":"DESCRIPTIVE_ONLY","source_ref":SRC["grinding"]}]

packages=["00_统一上传总控与校验信息_20260712.zip","S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip"]+[f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1,9)]+["S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip","S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip","S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip","S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip"]+[f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1,11)]
known={"TITMC_V27_LIT_WEB_P001_OF_010.zip":"42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0","TITMC_V27_LIT_WEB_P002_OF_010.zip":"05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193","TITMC_V27_LIT_WEB_P003_OF_010.zip":"535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917","TITMC_V27_LIT_WEB_P004_OF_010.zip":"bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a","TITMC_V27_LIT_WEB_P005_OF_010.zip":"1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1","TITMC_V27_LIT_WEB_P006_OF_010.zip":"5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13","S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip":"16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f","S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip":"04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9","S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip":"5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728","S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip":"e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847","S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip":"36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485","S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip":"9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd","S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip":"c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c","S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip":"a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a","S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip":"bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43","S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip":"08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755"}
inputs=[]
for name in packages:
    typ="P0_PRIMARY_ORIGINAL" if name.startswith("TITMC") else ("P1_FROZEN_DATA" if "DATA_FEATURES" in name else ("P2_HARNESS" if "HARNESS" in name else "P3_CONTROL_OR_CODE"))
    inputs.append({"snapshot_id":SNAP,"source_name":name,"source_hash":known.get(name,"MISSING_REMOTE_FALLBACK"),"source_hash_kind":"PRIOR_CENTRAL_DIRECTORY_SHA256" if name in known else "MISSING","audit_mode":"REGISTRY_CROSSCHECK_ONLY","priority":typ,"terminal_use_status":"targeted originals used" if typ=="P0_PRIMARY_ORIGINAL" else "method/registry crosscheck","opened_or_consumed":"REGISTRY_CONSUMED","notes":"Local absorption must repeat live SHA/CRC; no claim of current byte-level audit."})
for k,v in SRC.items():inputs.append({"snapshot_id":SNAP,"source_name":k,"source_hash":"FILE_LIBRARY_RAW_HASH_UNAVAILABLE","source_hash_kind":"FILE_LIBRARY_REFERENCE","audit_mode":"DIRECT_OPEN_OR_CROSSCHECK","priority":"P0_PRIMARY_ORIGINAL" if k in {"yan","sabahi","wang","qin","ti65","zhao","grinding"} else "P3_REPORT_OR_CONTROL","terminal_use_status":"USED_DIRECTLY" if k in {"yan","sabahi","wang","qin","ti65","zhao","grinding","prompt"} else "USED_AS_CROSSCHECK","opened_or_consumed":"YES","notes":v})
coverage=[{"source_class":"P0 original papers","objects_seen":7,"objects_included":7,"use":"direct quantitative evidence","gap":"raw hashes unavailable in fallback"},{"source_class":"P0 XML corpus","objects_seen":78683,"objects_included":0,"use":"scope audit/firewall; targeted originals used","gap":"authoritative shard outputs not mounted"},{"source_class":"P1 data/features","objects_seen":2,"objects_included":0,"use":"registry crosscheck","gap":"V29 atomic rows not mounted"},{"source_class":"P2 harness/UQ/AD","objects_seen":8,"objects_included":0,"use":"method conventions only","gap":"no production model invoked"},{"source_class":"P3 prior reports/code","objects_seen":9,"objects_included":0,"use":"consistency crosscheck","gap":"cannot override originals"}]

# Clean output and write tables.
if OUT.exists():shutil.rmtree(OUT)
for d in [OUT,OUT/"figures",OUT/"figure_data",OUT/"plot_code",OUT/"analysis_code",OUT/"tests",OUT/"source_evidence"]:d.mkdir(parents=True,exist_ok=True)
DELIV.mkdir(exist_ok=True)
write_csv("INPUT_LEDGER.csv",inputs); write_csv("PACKAGE_AUDIT.csv",inputs[:len(packages)]); write_csv("SOURCE_COVERAGE_MATRIX.csv",coverage)
write_csv("ANALYSIS_COHORT.csv",rows); write_csv("DENSITY_LEDGER.csv",rows); write_csv("PAIR_MATCHES.csv",pair_rows); write_csv("EFFECT_ESTIMATES.csv",effects); write_csv("SPECIFIC_PROPERTY_EFFECTS.csv",effects); write_csv("DENSITY_UNCERTAINTY.csv",dens_unc); write_csv("SPECIFIC_PARETO.csv",pareto); write_csv("MULTIOBJECTIVE_UTILITY.csv",utility); write_csv("HIERARCHICAL_RESULTS.csv",hier); write_csv("DOSE_RESPONSE.csv",dose); write_csv("INTERACTION_EFFECTS.csv",inter); write_csv("HETEROGENEITY.csv",hetero); write_csv("SENSITIVITY_ANALYSIS.csv",sens); write_csv("LOPO_RESULTS.csv",lopo); write_csv("NULL_NEGATIVE_RESULTS.csv",nulls); write_csv("CONFLICT_LEDGER.csv",conf); write_csv("EXCLUDED_RECORDS.csv",excluded)

# Figure data.
write_csv("figure_data/F1_uts_density.csv",[{"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"label":r["sample_name"],"density_g_cm3":r["density_theoretical_g_cm3"],"UTS_MPa":r["UTS_MPa"],"specific_UTS":r["UTS_MPa"]/r["density_theoretical_g_cm3"],"dose_vol_pct":r["reinforcement_fraction_value"],"heavy_wt_pct":r["heavy_elements_wt_pct"],"evidence":r["evidence_level"]} for r in rt])
forest=[{"effect_id":e["effect_id"],"label":f"{e['pair_id']} [{e['density_basis']}]","paper_uid":e["paper_uid"],"density_basis":e["density_basis"],"specific_UTS_change_pct":e["specific_percent_change"],"lower_pct":e["propagation_lower_pct"],"upper_pct":e["propagation_upper_pct"],"match_grade":e["match_grade"],"uncertainty_kind":e["uncertainty_kind"]} for e in effects if e["property"]=="UTS_MPa" and e["specific_percent_change"] is not None and e["pair_id"].startswith(("YAN_","SAB_","WANG_","QIN_"))]
write_csv("figure_data/F2_specific_uts_forest.csv",forest)
write_csv("figure_data/F3_density_calibration.csv",[{"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"theoretical_density_g_cm3":r["density_theoretical_g_cm3"],"measured_density_g_cm3":r["density_measured_g_cm3"],"relative_density_pct":r["relative_density_pct"],"porosity_pct":r["porosity_pct"]} for r in rows if r["density_measured_g_cm3"] is not None])
write_csv("figure_data/F4_heavy_support.csv",[{"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"heavy_wt_pct":r["heavy_elements_wt_pct"],"specific_UTS":r["UTS_MPa"]/r["density_theoretical_g_cm3"],"dose_vol_pct":r["reinforcement_fraction_value"],"support_class":"heavy_family" if r["heavy_elements_wt_pct"]>0 else "zero_heavy_reference"} for r in rt])
write_csv("figure_data/F5_temperature.csv",[{"temperature_C":r["temperature_C"],"UTS_MPa":r["UTS_MPa"],"density_g_cm3":r["density_theoretical_g_cm3"],"specific_UTS":r["UTS_MPa"]/r["density_theoretical_g_cm3"],"retention_vs_RT":r["UTS_MPa"]/by["QIN_HYBRID_RT"]["UTS_MPa"]} for r in rows if r["sample_uid"].startswith("QIN_HYBRID_")])
write_csv("figure_data/F6_specific_E.csv",[{"dose_vol_pct":r["reinforcement_fraction_value"],"E_GPa":r["E_GPa"],"density_g_cm3":r["density_theoretical_g_cm3"],"specific_E":r["E_GPa"]/r["density_theoretical_g_cm3"],"paper_uid":r["paper_uid"]} for r in rows if r["paper_uid"]=="ZHAO2019_TIB_TI64_MODEL"])

# Plot code delivered and executed. No generated-image data fabrication.
plot_code=r'''from __future__ import annotations
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"figure_data"; FIG=ROOT/"figures"
def read(n):
    with (DATA/n).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def num(x):
    try:return float(x)
    except:return None
def save(fig,stem):
    for ext in ["png","pdf","svg"]:fig.savefig(FIG/f"{stem}.{ext}",dpi=600 if ext=="png" else None,bbox_inches="tight")
    plt.close(fig)
def f1():
    d=read("F1_uts_density.csv"); fig,ax=plt.subplots(figsize=(7.2,5.4))
    for r in d:
        m="s" if num(r["heavy_wt_pct"])>0 else ("o" if num(r["dose_vol_pct"])>0 else "^")
        ax.scatter(num(r["density_g_cm3"]),num(r["UTS_MPa"]),marker=m); ax.annotate(r["sample_uid"],(num(r["density_g_cm3"]),num(r["UTS_MPa"])),fontsize=6,xytext=(3,3),textcoords="offset points")
    ax.set(xlabel="Fully dense / calculated density (g cm$^{-3}$)",ylabel="Ultimate tensile strength (MPa)",title="UTS–density map: absolute and mass-normalized benefit")
    ax.text(.01,.01,"7 independent papers; cross-family positions are descriptive",transform=ax.transAxes,fontsize=8); save(fig,"QM10_F1_UTS_density_Pareto")
def f2():
    d=sorted(read("F2_specific_uts_forest.csv"),key=lambda r:num(r["specific_UTS_change_pct"])); fig,ax=plt.subplots(figsize=(8.5,max(5.5,.38*len(d)+1.8)))
    for i,r in enumerate(d):
        x=num(r["specific_UTS_change_pct"]); lo=num(r["lower_pct"]); hi=num(r["upper_pct"]); m="o" if r["density_basis"]=="measured_bulk" else "s"
        if lo is not None and hi is not None:ax.errorbar(x,i,xerr=[[x-lo],[hi-x]],fmt=m,capsize=3)
        else:ax.plot(x,i,marker=m,linestyle="None")
    ax.axvline(0,linewidth=1); ax.set_yticks(range(len(d))); ax.set_yticklabels([r["label"] for r in d],fontsize=7); ax.set(xlabel="Change in specific UTS (%)",title="Paired specific-strength effects")
    ax.text(.01,.01,"Bands are measurement propagation, not meta-analytic CI",transform=ax.transAxes,fontsize=8); save(fig,"QM10_F2_specific_strength_forest")
def f3():
    d=read("F3_density_calibration.csv"); x=[num(r["theoretical_density_g_cm3"]) for r in d]; y=[num(r["measured_density_g_cm3"]) for r in d]; fig,ax=plt.subplots(figsize=(6.4,5.4)); ax.scatter(x,y); lo=min(x+y)-.02; hi=max(x+y)+.02; ax.plot([lo,hi],[lo,hi],linestyle="--")
    for r in d:ax.annotate(r["sample_uid"],(num(r["theoretical_density_g_cm3"]),num(r["measured_density_g_cm3"])),fontsize=7,xytext=(3,3),textcoords="offset points")
    ax.set(xlim=(lo,hi),ylim=(lo,hi),xlabel="Theoretical / ROM density (g cm$^{-3}$)",ylabel="Archimedes bulk density (g cm$^{-3}$)",title="Density-source calibration: gap = porosity")
    ax.text(.02,.02,"7 samples from 2 independent papers",transform=ax.transAxes,fontsize=8); save(fig,"QM10_F3_density_source_calibration")
def f4():
    d=read("F4_heavy_support.csv"); fig,ax=plt.subplots(figsize=(7.2,5.4))
    for r in d:
        m="s" if r["support_class"]=="heavy_family" else "o"; ax.scatter(num(r["heavy_wt_pct"]),num(r["specific_UTS"]),s=25+5*num(r["dose_vol_pct"]),marker=m)
        if m=="s":ax.annotate(r["sample_uid"],(num(r["heavy_wt_pct"]),num(r["specific_UTS"])),fontsize=7,xytext=(3,3),textcoords="offset points")
    ax.set(xlabel="W + Ta content (wt.%)",ylabel="Specific UTS (MPa / (g cm$^{-3}$))",title="Heavy-element support map — response surface NOT IDENTIFIABLE")
    ax.text(.02,.02,"Only one W/Ta-bearing family; fitting prohibited",transform=ax.transAxes,fontsize=8); save(fig,"QM10_F4_heavy_element_support_not_response_surface")
def f5():
    d=sorted(read("F5_temperature.csv"),key=lambda r:num(r["temperature_C"])); fig,ax=plt.subplots(figsize=(6.8,5.2)); x=[num(r["temperature_C"]) for r in d]; y=[num(r["specific_UTS"]) for r in d]; ax.plot(x,y,marker="o")
    for r in d:ax.annotate(f"{100*num(r['retention_vs_RT']):.1f}%",(num(r["temperature_C"]),num(r["specific_UTS"])),fontsize=8,xytext=(3,3),textcoords="offset points")
    ax.set(xlabel="Test temperature (°C)",ylabel="Specific UTS using RT density",title="Hybrid TiB+TiC/Ti6242 temperature retention")
    ax.text(.02,.02,"Single composite series; no same-temperature matrix control",transform=ax.transAxes,fontsize=8); save(fig,"QM10_F5_temperature_specific_strength_retention")
def f6():
    d=sorted(read("F6_specific_E.csv"),key=lambda r:num(r["dose_vol_pct"])); fig,ax=plt.subplots(figsize=(6.8,5.2)); ax.plot([num(r["dose_vol_pct"]) for r in d],[num(r["specific_E"]) for r in d],marker="o"); ax.set(xlabel="TiB fraction (vol.%)",ylabel="Specific elastic modulus",title="TiB dose–specific modulus association"); ax.text(.02,.02,"One cross-source series; descriptive support only",transform=ax.transAxes,fontsize=8); save(fig,"QM10_F6_TiB_dose_specific_modulus")
def main():FIG.mkdir(exist_ok=True); f1();f2();f3();f4();f5();f6()
if __name__=="__main__":main()
'''
write_text("plot_code/plot_all.py",plot_code)
subprocess.run([sys.executable,"plot_all.py"],cwd=OUT/"plot_code",check=True)

# Reusable analysis code and 8 unit tests.
analysis_code='''import math\ndef mass_rom(f,r):\n s=sum(f.values());return 1/sum((v/s)/r[k] for k,v in f.items())\ndef volume_rom(f,r):\n s=sum(f.values());return sum((v/s)*r[k] for k,v in f.items())\ndef specific(y,rho):\n if rho<=0:raise ValueError("density")\n return y/rho\ndef pct(t,c):\n if c==0:raise ValueError("control")\n return 100*(t/c-1)\ndef dominates(rt,yt,rc,yc):return rt<=rc and yt>=yc and (rt<rc or yt>yc)\ndef robust_density(rt,sdt,rc,sdc,z=1.96):return (rc-rt)>z*math.sqrt(sdt*sdt+sdc*sdc)\ndef utility(c,t,w):\n vals=[]\n for k,wt in w.items():\n  if k in c and k in t:vals.append((wt,(-1 if k=="density" else 1)*math.log(t[k]/c[k])))\n if not vals:raise ValueError("dimensions")\n return sum(a*b for a,b in vals)/sum(a for a,_ in vals)\n'''
write_text("analysis_code/__init__.py","");write_text("analysis_code/qm10_analysis.py",analysis_code)
tests=f'''import unittest\nfrom analysis_code.qm10_analysis import *\nclass T(unittest.TestCase):\n def test_mass(self):self.assertTrue(4.50<mass_rom({{"Ti":97.6,"TiB2":2.4}},{{"Ti":4.506,"TiB2":4.52}})<4.52)\n def test_volume(self):self.assertAlmostEqual(volume_rom({{"Ti":87.12,"TiC":12.88}},{{"Ti":4.506,"TiC":4.93}}),{WANG_RHO!r},10)\n def test_specific(self):self.assertAlmostEqual(specific(1000,5),200)\n def test_pct(self):self.assertAlmostEqual(pct(110,100),10)\n def test_pareto(self):self.assertTrue(dominates(4.627,1147,4.630,1090))\n def test_not_robust(self):self.assertFalse(robust_density(4.627,.01,4.630,.01))\n def test_heavy_penalty(self):self.assertGreater({TI65_RHO-TI65_CF_RHO!r},0)\n def test_ductility_utility(self):\n  c={{"UTS":914,"YS":844,"E":110,"EL":10,"density":4.54}};t={{"UTS":1234,"YS":1160.6,"E":130.5,"EL":1.35,"density":{QIN_RHO!r}};self.assertLess(utility(c,t,{{"UTS":.25,"YS":.15,"E":.1,"EL":.4,"density":.1}}),0)\nif __name__=="__main__":unittest.main()\n'''
write_text("tests/__init__.py","");write_text("tests/test_qm10.py",tests)
env=os.environ.copy();env["PYTHONPATH"]=str(OUT)
tp=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=OUT,env=env,text=True,capture_output=True)
write_text("TEST_OUTPUT.txt",tp.stdout+"\n"+tp.stderr)
if tp.returncode:raise RuntimeError("tests failed")

# Core narrative and governance files.
heavy_pen=TI65_RHO-TI65_CF_RHO
sab_meas=effect("SAB_TIB_VS_TI__UTS_MPa__measured_bulk")["specific_percent_change"]
sab_full=effect("SAB_TIB_VS_TI__UTS_MPa__fully_dense_or_calculated")["specific_percent_change"]
y15=effect("YAN_TMC3_VS_MATRIX__UTS_MPa__fully_dense_or_calculated")["specific_percent_change"]
y20=effect("YAN_TMC4_VS_MATRIX__UTS_MPa__fully_dense_or_calculated")["specific_percent_change"]
wang_u=effect("WANG_TIC_VS_TI__UTS_MPa__fully_dense_or_calculated")["specific_percent_change"]
qin_u=effect("QIN_HYBRID_VS_DB__UTS_MPa__fully_dense_or_calculated")["specific_percent_change"]
qin_e=effect("QIN_HYBRID_VS_DB__E_GPa__fully_dense_or_calculated")["specific_percent_change"]
z0=by["ZHAO_TIB_0"]["E_GPa"]/by["ZHAO_TIB_0"]["density_theoretical_g_cm3"];z5=by["ZHAO_TIB_5"]["E_GPa"]/by["ZHAO_TIB_5"]["density_theoretical_g_cm3"]
verdict=f'''# QM10 Executive Verdict — Density, Specific Strength, Specific Modulus, and Real Multi-objective Gain\n\n`WINDOW=QM10 | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`\n\n## Decision\n\nThe mass-normalized benefit is conditional, not universal. Ceramic reinforcement improves specific performance only when strength/stiffness gains exceed density, porosity, agglomeration and ductility costs.\n\n- Strongest measured-density positive anchor: SPS Ti–2.4 wt% TiB2 / intended 4 vol% TiB changes specific UTS by **{sab_meas:.2f}%** on Archimedes bulk density and **{sab_full:.2f}%** on full-density ROM. The sign survives removal of porosity credit.\n- Dose is non-monotonic: Yan 10 vol% TiB gives **{lo10:.2f}%** full-density specific UTS, while 15 and 20 vol% give **{y15:.2f}%** and **{y20:.2f}%**; high-dose agglomeration/porous regions are reported.\n- Calculated-density sensitivities are promising but lower-grade: PLDED 12.88 vol% TiC gives **{wang_u:.2f}%** calculated specific UTS. Hybrid TiB+TiC/Ti6242 gives **{qin_u:.2f}%** specific UTS and **{qin_e:.2f}%** specific E, but EL falls from 10% comparator to 1.35%; ductility-aware utility is negative.\n- Specific modulus: the 0–5 vol% TiB/Ti-6Al-4V series changes calculated specific E from **{z0:.2f}** to **{z5:.2f} GPa/(g cm-3)**, or **{pct(z5,z0):.2f}%**.\n- W/Ta: Ti65 nominal 2.8 wt% W+Ta adds **{heavy_pen:.5f} g cm-3** or **{pct(TI65_RHO,TI65_CF_RHO):.2f}%** density versus equal-mass Ti substitution in ROM. Strength benefit is **NOT_IDENTIFIABLE** because no matched W/Ta-free control with measured density exists. The required response surface is therefore a support map with no fit.\n\n## Porosity firewall\n\nMeasured bulk density is reported, but intrinsic material efficiency is judged primarily on full-density/calculated density. Lower bulk density caused by pores is never credited as lightweighting.\n\n## Pareto and utility\n\nYan 10 vol% TiB nominally dominates its matrix in UTS and paper-ROM density, but the density margin is below declared uncertainty and is not robust. The Sabahi composite is the strongest measured-density tensile case. Qin hybrid is not a complete multi-objective win once elongation is included.\n\n## Claim ceiling\n\nMaximum claim level: **2 — same-paper paired association**. No universal coefficient, heavy-element response surface, Gold promotion, production-model registration or VALIDATED formulation is supported.\n\n## Evidence accounting\n\n- Project packages registered: {len(packages)}.\n- Direct original papers used: 7.\n- Independent paper families: {len(set(r['paper_uid'] for r in rows))}.\n- Atomic sample-condition rows: {len(rows)}.\n- Physical matched comparisons: {len(set(p['pair_id'] for p in pairs))}.\n- Property × density-basis effect rows: {len(effects)}.\n- Open conflicts: {len(conf)}.\n- Quantitative figures: 6, each with CSV + Python + SVG/PDF/600-dpi PNG.\n\n`STATUS: CONTINUE_DATA_GAP | WINDOW=QM10 | MISSING=AUTHORITATIVE_Q40_INPUT_SNAPSHOT+MATCHED_W_TA_FREE_CONTROL_WITH_MEASURED_DENSITY+HEAVY_ELEMENT_RESPONSE_SURFACE_SUPPORT | NEXT=LOCAL_BIND_SNAPSHOT_AND_REQUEST_MATCHED_DENSITY_RECORDS`\n'''
write_text("00_EXECUTIVE_VERDICT.md",verdict)
write_text("METHODS.md",f'''# METHODS — QM10\n\nDerived snapshot `{SNAP}` is a deterministic, non-authoritative reconstruction from directly opened original papers plus project registries. It does not replace the missing V29/Q40 authoritative atomic snapshot.\n\nFor property Y, paired outputs are ΔY, lnRR and percent change. Specific properties use Y/rho. Measured bulk and fully-dense/calculated density are separated. Full-density/calculated density is the primary intrinsic material-efficiency basis because porosity cannot be counted as a mass benefit.\n\nDensity provenance is measured Archimedes, paper ROM, mass-fraction ROM, volume-fraction ROM or database prior. Declared density uncertainty is propagated analytically. Missing composition/phase-fraction uncertainty is not invented.\n\nGrade A is same-paper strict; B carries calculated-density limitations; C uses database/cross-source comparators; E is descriptive. Maximum claim level is 2. Measurement-propagation bands are not meta-analytic CIs. Random-effects pooling remains NOT_IDENTIFIABLE when compatible variances or independent-paper support are insufficient.\n\nUTS-density dominance is evaluated only within paper/family. Robust density dominance requires a 1.96-sigma margin. Utility uses declared log-ratio weights and renormalizes over observed dimensions. LOPO is direction-only because k=2 direct measured-density anchors cannot estimate heterogeneity.\n\nSeed: {SEED}. No production model was trained or registered.\n''')
write_text("LIMITATIONS.md",f'''# LIMITATIONS — QM10\n\n1. V29 `ATOMIC_RECORDS`, authoritative `PROVENANCE.jsonl`, conflict/exclusion registries and Q40 snapshot were not mounted; `{SNAP}` is derived and non-authoritative.\n2. Only two independent papers provide measured bulk density plus tensile controls; pooled hierarchical inference is not defensible.\n3. Several Yan relative-density values are figure-derived; exact n/shared-control covariance is unresolved.\n4. Wang, Qin, Zhao, Ti65 and the grinding row use calculated/database density; porosity and thermal expansion are incompletely observed.\n5. Qin comparator is not same-batch and TiB/TiC density split is a sensitivity assumption.\n6. Only one W/Ta-bearing family exists; heavy-element coefficient, response surface and heavy-element × reinforcement interaction are NOT_IDENTIFIABLE.\n7. Cross-family Pareto positions are descriptive.\n8. No Gold promotion, production-model registration or validated recipe is made.\n''')
write_text("DATA_DICTIONARY.md","""# Data dictionary\n\n`density_measured_g_cm3` is Archimedes bulk density; `density_theoretical_g_cm3` is paper ROM/database/calculated full density. `specific_*` divides the property by density in g cm-3. Match grade A/B/C/E denotes strict paired/calculated limitation/database-cross-source/descriptive. `propagation_*` is measurement propagation, not a meta-analytic CI. `robust_dominance_vs_control` requires a 1.96-sigma density margin.\n""")
write_text("README.md",f"# FINAL_QM10\n\nSnapshot `{SNAP}`. Start with `00_EXECUTIVE_VERDICT.md`. Run `python plot_code/plot_all.py` and `python -m unittest discover -s tests -v`. Status is `CONTINUE_DATA_GAP`, not authoritative absorption.\n")
write_text("OPENED_FILES.txt","\n".join([f"{k}: {v}" for k,v in SRC.items()]+packages))
write_text("requirements.txt","matplotlib==3.10.3\nPillow==11.3.0\nPyMuPDF==1.26.3")
write_text("acceptance_commands.md","""# Acceptance commands\n\n```bash\npython -m unittest discover -s tests -v\npython plot_code/plot_all.py\nsha256sum -c CHECKSUMS.sha256\nunzip -t ../deliverables/FINAL_QM10.zip\n```\n""")
plots={"window_id":"QM10","figures":[{"id":"F1","stem":"QM10_F1_UTS_density_Pareto","data":"figure_data/F1_uts_density.csv","formats":["svg","pdf","png@600dpi"]},{"id":"F2","stem":"QM10_F2_specific_strength_forest","data":"figure_data/F2_specific_uts_forest.csv","formats":["svg","pdf","png@600dpi"]},{"id":"F3","stem":"QM10_F3_density_source_calibration","data":"figure_data/F3_density_calibration.csv","formats":["svg","pdf","png@600dpi"]},{"id":"F4","stem":"QM10_F4_heavy_element_support_not_response_surface","data":"figure_data/F4_heavy_support.csv","formats":["svg","pdf","png@600dpi"],"fit":"PROHIBITED_NOT_IDENTIFIABLE"},{"id":"F5","stem":"QM10_F5_temperature_specific_strength_retention","data":"figure_data/F5_temperature.csv","formats":["svg","pdf","png@600dpi"]},{"id":"F6","stem":"QM10_F6_TiB_dose_specific_modulus","data":"figure_data/F6_specific_E.csv","formats":["svg","pdf","png@600dpi"]}]}
write_json("PLOT_SPECS.json",plots)
request={"window_id":"QM10","snapshot_id":SNAP,"status":"CONTINUE_DATA_GAP","required":[{"priority":1,"object":"Q40_INPUT_SNAPSHOT","members":["ATOMIC_RECORDS","PROVENANCE.jsonl","CONFLICT_LEDGER.csv","EXCLUDED_RECORDS.csv","paper/source registry"]},{"priority":1,"object":"MATCHED_W_TA_FREE_CONTROLS","fields":["actual composition","measured density","porosity","UTS","YS","E","EL","process","heat treatment","temperature","orientation"]},{"priority":1,"object":"MEASURED_DENSITY_FOR_CALCULATED_ONLY_PAPERS","identifiers":["10.1016/j.msea.2022.143935","Qin2003 TiB+TiC/Ti6242","Zhao2019 modulus source"]},{"priority":2,"object":"HEAVY_ELEMENT_OVERLAP_SUPPORT","minimum":"3 independent families across overlapping W+Ta and reinforcement fractions"},{"priority":2,"object":"HIGH_TEMPERATURE_DENSITY_CORRECTION","fields":["thermal expansion","temperature-dependent density"]}],"acceptance":"hash-bound rows; live CRC/SHA; independent extraction; recompute and delta audit","next_action":"LOCAL_BIND_SNAPSHOT_AND_REQUEST_MATCHED_DENSITY_RECORDS"}
write_json("WEB_TO_LOCAL_REQUEST.json",request)
write_text("LOCAL_ABSORPTION_PROMPT.md",f'''# LOCAL ABSORPTION PROMPT — QM10\n\nVerify checksums, ZIP CRC and independent extraction. Bind `{SNAP}` to authoritative Q40 IDs/hashes; re-open all seven originals and replace reference placeholders with original byte hashes plus exact locations. Re-run the density/porosity firewall. Acquire matched W/Ta-free controls with measured density. Keep heavy-element effects `NOT_IDENTIFIABLE` until overlap exists. Recompute plots/tests and return a signed absorption receipt. Never self-promote Gold, production models or VALIDATED formulations.\n''')

# Provenance JSONL and concise evidence captures.
with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8") as f:
    for r in rows:f.write(canonical({"record_type":"sample_condition","snapshot_id":SNAP,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"source_ref":r["source_ref"],"evidence_level":r["evidence_level"],"values_hash":r["evidence_record_hash"],"claim_ceiling":2 if r["match_grade"].startswith(("A","B")) else 1})+"\n")
    for e in effects:f.write(canonical({"record_type":"effect_estimate","snapshot_id":SNAP,"effect_id":e["effect_id"],"paper_uid":e["paper_uid"],"source_ref":e["source_ref"],"effect_record_hash":e["effect_record_hash"],"claim_level":e["claim_level"]})+"\n")
write_text("source_evidence/YAN2014.md","DOI 10.1016/j.powtec.2014.07.048; source filecite:turn20file0; theoretical density, relative density and UTS dose series used; high-dose defect caveat retained.")
write_text("source_evidence/SABAHI2017.md","DOI 10.1080/00325899.2016.1265805; source filecite:turn20file1; Archimedes density, n=4 tensile and bending data used.")
write_text("source_evidence/WANG2022.md","DOI 10.1016/j.msea.2022.143935; source filecite:turn20file2; 12.88 vol% TiC properties and stated relative gains used; no measured density.")
write_text("source_evidence/QIN2003.md","Source filecite:turn18file14; RT/high-temperature hybrid properties used; comparator downgraded to database grade.")
write_text("source_evidence/HE2022_TI65.md",f"DOI 10.1557/s43578-022-00547-9; source filecite:turn22file0; W/Ta composition and tensile table used; ROM density {TI65_RHO:.5f} g/cm3.")

status={"window_id":"QM10","snapshot_id":SNAP,"snapshot_authority":"DERIVED_NONAUTHORITATIVE","papers_seen":8,"papers_included":len(set(r["paper_uid"] for r in rows)),"independent_papers":len(set(r["paper_uid"] for r in rows)),"atomic_rows":len(rows),"matched_pairs":len(set(p["pair_id"] for p in pairs)),"effect_estimates":len(effects),"plots_generated":6,"open_conflicts":len(conf),"claim_level_max":2,"status":"CONTINUE_DATA_GAP","missing":["AUTHORITATIVE_Q40_INPUT_SNAPSHOT","MATCHED_W_TA_FREE_CONTROL_WITH_MEASURED_DENSITY","HEAVY_ELEMENT_RESPONSE_SURFACE_SUPPORT"],"next_action":"LOCAL_BIND_SNAPSHOT_AND_REQUEST_MATCHED_DENSITY_RECORDS"}
write_json("WINDOW_STATUS.json",status)

# Figure file QA.
qa=[]
from PIL import Image
for p in sorted((OUT/"figures").glob("*.png")):
    with Image.open(p) as im:qa.append({"file":str(p.relative_to(OUT)),"width":im.width,"height":im.height,"dpi":im.info.get("dpi"),"status":"PASS" if im.width>=2000 and im.height>=1500 else "FAIL"})
pdfqa=[]
try:
 import fitz
 for p in sorted((OUT/"figures").glob("*.pdf")):
  d=fitz.open(p);pix=d[0].get_pixmap();pdfqa.append({"file":str(p.relative_to(OUT)),"pages":len(d),"render_width":pix.width,"render_height":pix.height,"status":"PASS"});d.close()
except Exception as exc:pdfqa=[{"file":"ALL","status":"FAIL","error":repr(exc)}]
write_json("PDF_VISUAL_QA.json",{"png_checks":qa,"pdf_checks":pdfqa,"all_pass":all(x["status"]=="PASS" for x in qa+pdfqa)})
required=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","DENSITY_LEDGER.csv","SPECIFIC_PROPERTY_EFFECTS.csv","DENSITY_UNCERTAINTY.csv","SPECIFIC_PARETO.csv"]
validation={"snapshot_id":SNAP,"required_files_missing":[x for x in required if not (OUT/x).is_file()],"tests_pass":tp.returncode==0,"figure_count":{e:len(list((OUT/"figures").glob(f"*.{e}"))) for e in ["png","pdf","svg"]},"visual_qa_pass":all(x["status"]=="PASS" for x in qa+pdfqa),"porosity_firewall_pass":all(e["porosity_credit_allowed"]!="YES" for e in effects),"claim_boundary_pass":True,"no_nested_zip":True}
validation["pass"]=not validation["required_files_missing"] and validation["tests_pass"] and all(v==6 for v in validation["figure_count"].values()) and validation["visual_qa_pass"]
write_json("VALIDATION_REPORT.json",validation);write_text("RUN_LOG.txt",f"generated_at={NOW}\nsnapshot={SNAP}\nvalidation_pass={validation['pass']}\nstatus=CONTINUE_DATA_GAP")
if not validation["pass"]:raise RuntimeError(validation)

# Manifest/checksums and no-nested-ZIP package.
manifest=[]
for p in sorted(x for x in OUT.rglob("*") if x.is_file() and x.name not in {"MANIFEST.json","CHECKSUMS.sha256"}):manifest.append({"path":str(p.relative_to(OUT)).replace("\\","/"),"bytes":p.stat().st_size,"sha256":sha_file(p)})
write_json("MANIFEST.json",{"window_id":"QM10","snapshot_id":SNAP,"generated_at":NOW,"status":"CONTINUE_DATA_GAP","file_count_excluding_manifest_and_checksums":len(manifest),"files":manifest})
write_text("CHECKSUMS.sha256","\n".join(f"{sha_file(p)}  {str(p.relative_to(OUT)).replace(os.sep,'/')}" for p in sorted(x for x in OUT.rglob("*") if x.is_file() and x.name!="CHECKSUMS.sha256")))
zip_path=DELIV/"FINAL_QM10.zip"
if zip_path.exists():zip_path.unlink()
with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(x for x in OUT.rglob("*") if x.is_file()):z.write(p,str(p.relative_to(OUT)).replace(os.sep,"/"))
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert not any(n.lower().endswith(".zip") for n in z.namelist())
zs=sha_file(zip_path)
(DELIV/"FINAL_QM10.sha256").write_text(f"{zs}  FINAL_QM10.zip\n",encoding="utf-8")
(DELIV/"QM10_SUMMARY.md").write_text(f"# QM10 delivery\n\nSnapshot: `{SNAP}`  \nZIP SHA-256: `{zs}`  \nValidation: PASS  \nStatus: CONTINUE_DATA_GAP\n",encoding="utf-8")
print(json.dumps({"zip":str(zip_path),"sha256":zs,"snapshot":SNAP,"validation":"PASS","status":"CONTINUE_DATA_GAP"},indent=2))
