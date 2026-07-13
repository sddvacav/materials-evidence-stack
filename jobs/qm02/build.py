#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, json, math, shutil, subprocess, sys, textwrap, zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM02"
ZIP = ROOT / "FINAL_QM02.zip"
WINDOW = "QM02"
UPSTREAM = "MISSING_V29_ATOMIC_SNAPSHOT"
GENERATED = "2026-07-13T04:35:00+00:00"


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def hbytes(b):
    return hashlib.sha256(b).hexdigest()

def hfile(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20), b""): h.update(c)
    return h.hexdigest()

def wtext(rel, s):
    p=OUT/rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s.rstrip()+"\n", encoding="utf-8")

def wjson(rel, x):
    wtext(rel, json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2))

def cell(v):
    if v is None: return ""
    if isinstance(v,float): return f"{v:.12g}" if math.isfinite(v) else ""
    if isinstance(v,(list,dict,tuple)): return json.dumps(v,ensure_ascii=False,sort_keys=True)
    return v

def wcsv(rel, rows, fields=None):
    p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True)
    if fields is None:
        fields=[]
        for r in rows:
            for k in r:
                if k not in fields: fields.append(k)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        q=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); q.writeheader()
        for r in rows: q.writerow({k:cell(r.get(k,"")) for k in fields})

def wilson(k,n,z=1.959963984540054):
    if not n:return (None,None)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    m=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-m),min(1,c+m)

def mk_effect(eid,paper,pair,prop,unit,c,t,ctrl,trt,nominal,actual,cond,grade="A",sdc=None,sdt=None,nc=None,nt=None,note=""):
    delta=t-c; ln=math.log(t/c) if c>0 and t>0 else None; pct=100*(math.exp(ln)-1) if ln is not None else None
    dlo=dhi=llo=lhi=None
    if None not in (sdc,sdt,nc,nt):
        se=math.sqrt(sdc*sdc/nc+sdt*sdt/nt); dlo,dhi=delta-1.96*se,delta+1.96*se
        if ln is not None:
            se2=math.sqrt(sdt*sdt/(nt*t*t)+sdc*sdc/(nc*c*c)); llo,lhi=ln-1.96*se2,ln+1.96*se2
    return dict(effect_id=eid,snapshot_id=SNAPSHOT,paper_uid=paper,pair_id=pair,condition_uid=cond,property=prop,unit=unit,
                control_label=ctrl,treated_label=trt,control_value=c,treated_value=t,delta=delta,delta_ci95_low=dlo,delta_ci95_high=dhi,
                lnRR=ln,lnRR_ci95_low=llo,lnRR_ci95_high=lhi,percent_change=pct,nominal_attribution_bucket=nominal,
                verified_actual_phase_bucket=actual,match_grade=grade,evidence_level="DIRECT_TABLE_TEXT+DIRECT_PHASE_ID",
                claim_level=2,uncertainty_method="reported_SD_delta_method" if dlo is not None else "not_estimable_dispersion_missing",notes=note)

papers=[
 dict(uid="P001_SABAHI_2017",citation="A. Sabahi Namini and M. Azadbeh, Powder Metallurgy 60(1) (2017) 22-32",doi="10.1080/00325899.2016.1265805",precursor="TiB2",matrix="Ti",process="SPS 1050 C",actual="TiB whiskers + residual TiB2",morph="whisker + residual coarse particle",methods="XRD|SEM|EDS|stoichiometry",conversion="PARTIAL_CONVERSION",fraction=0,fact="2.4 wt.% TiB2 targeted 4 vol.% TiB; TiB whiskers and unreacted TiB2 were directly identified."),
 dict(uid="P002_LI_2023",citation="R. Li et al., Materials Science and Engineering A 864 (2023) 144466",doi="10.1016/j.msea.2022.144466",precursor="B4C",matrix="Ti-6Al-4V",process="DED",actual="TiB whiskers + equiaxed TiC",morph="whisker + equiaxed particle",methods="XRD|TEM|SAED|EDS|SEM|stoichiometry",conversion="COMPLETE_DEPLETION_SUPPORTED",fraction=0,fact="5 wt.% B4C was undetected after DED; actual phases were TiB and TiC."),
 dict(uid="P003_ZHANG_2024",citation="J. Zhang et al., Ceramics International 50 (2024) 17482-17491",doi="10.1016/j.ceramint.2024.02.236",precursor="B4C + Cr3C2",matrix="Ti",process="powder metallurgy/sintering",actual="TiB + TiC",morph="short TiB whisker + equiaxed/dendritic TiC",methods="XRD|TEM|HRTEM|SAED|EDS|SEM|stoichiometry|image analysis",conversion="COMPLETE_B4C_REACTION_SUPPORTED",fraction=1,fact="0/0.5/1.0 wt.% B4C produced measured TiB 0/3.16/5.87 vol.%; TiC also derives from Cr3C2."),
 dict(uid="P004_CHOI_2011",citation="B.-J. Choi and Y.-J. Kim, Materials Transactions 52(10) (2011) 1926-1930",doi="10.2320/matertrans.M2011079",precursor="B4C",matrix="Ti",process="investment casting",actual="TiB + TiC; agglomerated residual B4C at 0.5 um condition",morph="needle + sphere + agglomerate",methods="SEM|EPMA|element mapping|stoichiometry",conversion="CONDITION_DEPENDENT_INCOMPLETE",fraction=0,fact="1.88 mass.% B4C targeted 10 vol.% hybrid; 0.5 um feed agglomerated and was not fully synthesized."),
 dict(uid="P005_VERMA_2022",citation="P. K. Verma et al., Journal of Materials Engineering and Performance 31 (2022) 9586-9595",doi="10.1007/s11665-022-06981-4",precursor="TiB2",matrix="Ti-6Al-4V",process="SLM + optional anneal",actual="TiB whiskers",morph="nano-whisker; network onset >=0.5 wt.%",methods="XRD|SEM|TEM|stoichiometry",conversion="TIB_FORMATION_FRACTION_THEORETICAL",fraction=0,fact="0.2/0.5/1.0 wt.% TiB2 formed TiB; 0.32/0.81/1.62 vol.% are theoretical, not measured."),
 dict(uid="P006_ABBOUD_1994",citation="J. H. Abboud and D. R. F. West, Materials Science and Technology 10 (1994) 60-68",doi="10.1179/mst.1994.10.1.60",precursor="SiC",matrix="Ti-Al series",process="laser melting",actual="TiC + Ti5(Si,Al)3/silicide + residual SiC",morph="spherical/dendritic TiC + lamella/rod silicide",methods="OM|SEM|EDS|TEM|STEM",conversion="PARTIAL_DISSOLUTION_CONDITION_DEPENDENT",fraction=0,fact="15 wt.% SiC partially dissolved; products depended on Al content and residual SiC remained in some conditions."),
 dict(uid="P007_XU_2023",citation="L. J. Xu et al., Transactions of Nonferrous Metals Society of China 33 (2023) 467-480",doi="10.1016/S1003-6326(22)66120-X",precursor="B4C + C; optional Y2O3",matrix="high-temperature Ti alloy",process="in-situ synthesis/thermomechanical",actual="TiB + TiC + retained Y2O3 where added",morph="fiber + equiaxed/strip + granular oxide",methods="XRD|SEM|EDS|TEM|SAED|stoichiometry",conversion="COMPLETE_REACTION_Y2O3_RETAINED",fraction=0,fact="No B4C/C/TiB2 peaks; TiB, TiC and retained Y2O3 were directly identified."),
 dict(uid="P008_ZHONG_2020",citation="Z. Zhong et al., Ceramics International (2020)",doi="10.1016/j.ceramint.2020.07.325",precursor="TiB2",matrix="Ti",process="SPS + tape casting",actual="TiB + Ti; residual TiB2 at high target fraction",morph="whisker/rod + high-dose agglomerate",methods="XRD|SEM|stoichiometry",conversion="DOSE_DEPENDENT_RESIDUAL",fraction=0,fact="Target TiB >40 vol.% showed residual TiB2; target fraction was not measured actual TiB."),
 dict(uid="P009_LUO_2021",citation="G. Luo et al., Ceramics International 47 (2021) 15910-15922",doi="10.1016/j.ceramint.2021.02.165",precursor="TiB2 + TC4",matrix="TC4/Ti",process="plasma activated sintering",actual="ratio-dependent TiB2/TiB/alpha-Ti/beta-Ti",morph="block -> cluster -> whisker",methods="XRD|TEM|SAED|EDS|SEM|stoichiometry",conversion="RATIO_DEPENDENT_IDENTITY",fraction=0,fact="Mixture ratio controlled retained TiB2, TiB formation and matrix-phase retention."),
 dict(uid="P010_LIU_2023",citation="C. Liu et al., Composites Part B 266 (2023) 111008",doi="10.1016/j.compositesb.2023.111008",precursor="B4C",matrix="Ti-6Al-4V",process="LDED",actual="TiB whiskers + nano TiC network",morph="networked whisker + nanoparticle",methods="TEM|SAED|EDS|TKD|SEM|stoichiometry",conversion="DUAL_PHASE_FORMATION",fraction=0,fact="1 vol.% B4C generated a directly identified TiB/TiC network."),
 dict(uid="P011_CHRYSANTHOU_2003",citation="Chrysanthou et al., Combustion synthesis and subsequent sintering of titanium-matrix composites (2003; metadata incomplete)",doi="UNRESOLVED",precursor="TiC",matrix="Ti",process="combustion synthesis + 1160 C sintering",actual="TiCx~0.65 -> TiCx~0.58 + TiC0.5 -> TiC0.5",morph="carbide particles",methods="XRD|SEM|EDS|lattice parameter",conversion="TIME_DEPENDENT_SUBSTOICHIOMETRY",fraction=0,fact="Generic TiC obscures time-dependent carbon stoichiometry and equilibration to TiC0.5."),
]
for p in papers:
    p["source_hash"]=hbytes(canon(p).encode()); p["source_hash_type"]="EVIDENCE_PAYLOAD_SHA256_NOT_ORIGINAL_FILE_SHA"
SNAPSHOT="QM02_COHORT_"+hbytes(canon([(p["uid"],p["source_hash"]) for p in papers]).encode())[:16]
P={p["uid"]:p for p in papers}

if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True)

# Input ledger: every visible package receives a terminal disposition.
ledger=[]
def led(name,cls,status,use,gap=""):
    ledger.append(dict(snapshot_id=SNAPSHOT,source_name=name,source_class=cls,terminal_status=status,use_in_qm02=use,member_level_audit="BLOCKED_LOCAL_BACKEND" if name.endswith(".zip") else "NOT_APPLICABLE",gap_or_exclusion_reason=gap))
led("QM02_增强相本体、前驱体到实际相转化及身份不确定性.md","P4_CONTRACT","USED_DIRECTLY","estimands, outputs and gates")
led("00_统一上传总控与校验信息_20260712.zip","CONTROL","USED_AS_REFERENCE","governance","member manifest required")
led("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","P3_PLATFORM_CODE","NOT_RELEVANT_TO_WINDOW","no platform mutation")
for i in range(1,3): led(f"S03_CODEX_ML_DATA_FEATURES_{i:02d}_450_500MB_20260712.zip","P2_DATA_FEATURES","USED_AS_REFERENCE","quality/feature context","authoritative member hashes unavailable")
for i in range(1,9): led(f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip","P2_HARNESS","USED_AS_REFERENCE","source/condition method context","authoritative member hashes unavailable")
for i in range(1,4): led(f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip","P3_CODE","USED_AS_REFERENCE","reuse engineering substrate")
led("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip","P3_HISTORY","USED_AS_REFERENCE","historical provenance")
for i in range(1,11): led(f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip","P0_PRIMARY","USED_DIRECTLY","indexed primary-paper evidence","archive member manifest required")
led("V29_ATOMIC_RECORDS/PROVENANCE/REGISTRIES","P1_AUTHORITY","BLOCKED_INPUT","required authoritative cohort binding","not present")
led("figure_evidence.jsonl","P1_FIGURE_INDEX","USED_AS_REFERENCE","caption/figure cross-check")
led("source_calibration_v1.json","P2_DERIVED","USED_AS_REFERENCE","label inventory only; not phase inference")

# Atomic cohort rows (paper/sample/condition summaries; property rows remain separate).
cohort=[]
def co(uid,sample,cond,nominal,actual,fraction="",morph="",status="INCLUDED"):
    p=P[uid]; su=f"{uid}::{sample}"; cu=f"{su}::{cond}"
    cohort.append(dict(snapshot_id=SNAPSHOT,source_hash=p["source_hash"],paper_uid=uid,sample_uid=su,condition_uid=cu,matrix=p["matrix"],process=p["process"],precursor_name=p["precursor"],nominal_addition=nominal,actual_phase=actual,measured_fraction=fraction,morphology=morph or p["morph"],evidence_methods=p["methods"],conversion_class=p["conversion"],row_granularity="paper_sample_condition_phase_summary",inclusion_status=status))
co("P001_SABAHI_2017","matrix","RT","0","none"); co("P001_SABAHI_2017","composite","RT","2.4 wt.% TiB2; target 4 vol.% TiB","TiB + residual TiB2")
for s,c,a,n in [("matrix_RT","tension_RT","none","0"),("comp_RT","tension_RT","TiB+TiC","5 wt.% B4C"),("matrix_600","tension_600C","none","0"),("comp_600","tension_600C","TiB+TiC","5 wt.% B4C"),("matrix_comp","compression_RT","none","0"),("comp_comp","compression_RT","TiB+TiC","5 wt.% B4C")]:co("P002_LI_2023",s,c,n,a)
co("P003_ZHANG_2024","TMC1","RT_tension","8 wt.% Cr3C2 + 0 B4C","TiC","TiC=9.77 vol.%")
co("P003_ZHANG_2024","TMC2","RT_tension","8 wt.% Cr3C2 + 0.5 wt.% B4C","TiB+TiC","TiB=3.16; TiC=6.47 vol.%")
co("P003_ZHANG_2024","TMC3","RT_tension","8 wt.% Cr3C2 + 1.0 wt.% B4C","TiB+TiC","TiB=5.87; TiC=6.05 vol.%")
co("P004_CHOI_2011","matrix","RT_tension","0","none")
for sz in ["1500um","150um","0.5um"]:co("P004_CHOI_2011",f"B4C_{sz}","RT_tension",f"1.88 mass.% B4C; {sz}; target 10 vol.%", "TiB+TiC" if sz!="0.5um" else "TiB+TiC+incompletely reacted/agglomerated B4C")
for state in ["as_built","annealed"]:
    for dose,theo in [(0,0),(0.2,0.32),(0.5,0.81),(1.0,1.62)]:co("P005_VERMA_2022",f"d{dose}_{state}",state,f"{dose} wt.% TiB2","none" if dose==0 else "TiB whiskers","" if dose==0 else f"theoretical TiB={theo} vol.%")
for i,(al,a) in enumerate([(15,"TiC+silicide+residual SiC"),(30,"TiC+silicide+residual SiC"),(32,"TiC+silicide+residual SiC"),(42,"silicide; TiC not detected"),(57.5,"gamma+TiC+Ti5(Si,Al)3"),(77.5,"Ti(Al,Si)3+Al-rich phase")],1):co("P006_ABBOUD_1994",f"pellet{i}",f"Al_{al}atpct","15 wt.% SiC",a)
co("P007_XU_2023","TMC1","creep_650C","target 1.25 vol.% TiB + 1.25 vol.% TiC","TiB+TiC","nominal target")
co("P007_XU_2023","TMC2","creep_650C","same + 0.5 vol.% Y2O3","TiB+TiC+Y2O3","nominal target")
for target in [5,20,40,60,80]:co("P008_ZHONG_2020",f"target{target}","SPS",f"target {target} vol.% TiB from TiB2+Ti","TiB+Ti" if target<=40 else "TiB+Ti+residual TiB2","target not measured")
for r in range(0,101,10):
    a="TiB2" if r==0 else "mainly TiB2+minor TiB" if r<=20 else "core TiB+minor TiB2" if r<=50 else "TiB-rich+low alpha-Ti" if r<=70 else "alpha/beta-Ti+TiB" if r<100 else "alpha/beta-Ti"
    co("P009_LUO_2021",f"T{r}","PAS",f"TC4 index {r}; balance TiB2",a)
co("P010_LIU_2023","matrix","in_situ_tension","0","none");co("P010_LIU_2023","composite","in_situ_tension","1 vol.% B4C","TiB+nano TiC network")
for pct,t in [(12.5,0),(18.75,0),(25,0),(25,2),(25,7)]:
    a="TiCx~0.65" if t==0 else "TiCx~0.58+TiC0.5" if t==2 else "TiC0.5"
    co("P011_CHRYSANTHOU_2003",f"{pct}pct_{t}h",f"1160C_{t}h" if t else "post_combustion",f"{pct}% TiC",a)

# 22 same-paper effects.
effects=[]
for i,(prop,u,c,t,sdc,sdt,n) in enumerate([("UTS","MPa",441,485,6,9,4),("elongation","%",2.68,8.67,.15,.11,4),("flexural_strength","MPa",2134,1615,55,79,3),("Vickers_hardness","HV",305,363,15,21,6)],1):
    effects.append(mk_effect(f"E001_{i}","P001_SABAHI_2017","PAIR_P001",prop,u,c,t,"Ti matrix","TiB2-fed composite","TiB2 reinforcement","TiB+residual TiB2",f"P001::{prop}::RT",sdc=sdc,sdt=sdt,nc=n,nt=n,note="Target 4 vol.% TiB is not measured."))
for i,(prop,u,c,t,cond) in enumerate([("UTS","MPa",989.3,1126.1,"RT_tension"),("elongation","%",8.2,4.2,"RT_tension"),("UTS","MPa",406.1,506.4,"600C_tension"),("elongation","%",24.3,14.1,"600C_tension"),("ultimate_compressive_strength","MPa",1421.4,1865.4,"RT_compression"),("compressive_strain","%",23.7,17.5,"RT_compression")],1):
    effects.append(mk_effect(f"E002_{i}","P002_LI_2023",f"PAIR_P002_{cond}",prop,u,c,t,"DED Ti64","5 wt.% B4C feed","B4C reinforcement","TiB+TiC",f"P002::{cond}::{prop}",note="B4C depleted; reported dispersion absent in extracted evidence."))
v={"TMC1":{"YS":(708.52,6),"UTS":(759.88,8),"elongation":(.62,.3)},"TMC2":{"YS":(785.56,4),"UTS":(890.61,3),"elongation":(1.21,.4)},"TMC3":{"YS":(868.77,10),"UTS":(1059.52,6),"elongation":(5.58,.1)}}
for tr in ["TMC2","TMC3"]:
    for prop,u in [("YS","MPa"),("UTS","MPa"),("elongation","%")]:
        c,sdc=v["TMC1"][prop];t,sdt=v[tr][prop];i=sum(e["paper_uid"]=="P003_ZHANG_2024" for e in effects)+1
        effects.append(mk_effect(f"E003_{i}","P003_ZHANG_2024",f"PAIR_P003_{tr}",prop,u,c,t,"TiC-only TMC1",tr,"B4C addition","incremental TiB + changed TiC population",f"P003::{tr}::{prop}",grade="B",sdc=sdc,sdt=sdt,nc=3,nt=3,note="Component control; TiC attribution is confounded by Cr3C2 baseline."))
r1={120:5.34e-8,140:9.29e-8,160:1.23e-7};r2={120:4.43e-8,140:6.17e-8,160:1.16e-7};s1={120:2.53,140:3.57,160:4.44};s2={120:2.47,140:3.25,160:4.29}
for st in [120,140,160]:
    effects.append(mk_effect(f"E007_R{st}","P007_XU_2023",f"PAIR_P007_{st}","minimum_creep_rate","s^-1",r1[st],r2[st],"TiB+TiC","TiB+TiC+Y2O3","Y2O3 addition","retained Y2O3",f"P007::650C::{st}MPa::rate",grade="A_COMPONENT_CONTROL"))
    effects.append(mk_effect(f"E007_S{st}","P007_XU_2023",f"PAIR_P007_{st}","creep_strain_50h","%",s1[st],s2[st],"TiB+TiC","TiB+TiC+Y2O3","Y2O3 addition","retained Y2O3",f"P007::650C::{st}MPa::strain",grade="A_COMPONENT_CONTROL"))
pairs=[dict(snapshot_id=SNAPSHOT,pair_id=e["pair_id"],paper_uid=e["paper_uid"],condition_uid=e["condition_uid"],property=e["property"],control_label=e["control_label"],treated_label=e["treated_label"],match_grade=e["match_grade"],identity_binding=f"{e['nominal_attribution_bucket']} -> {e['verified_actual_phase_bucket']}",claim_level=2,caveat=e["notes"]) for e in effects]

# Paper-level estimands.
estimands=[]
for eid,label,k,n,scope,caveat in [
 ("EST_TIB2_TO_TIB","TiB2-fed studies detecting TiB/TiBw",4,4,"P001,P005,P008,P009","Product detection, not complete conversion."),
 ("EST_B4C_TO_TIB_TIC","B4C-fed studies detecting TiB+TiC",5,5,"P002,P003,P004,P007,P010","Selected direct-evidence cohort, not population prevalence."),
 ("EST_B4C_DEPLETION","B4C depletion supported among assessable studies",3,4,"P002,P003,P004,P007","P004 includes incomplete nano-feed condition; P010 depletion not quantified."),
 ("EST_MEASURED_FRACTION","Core papers with phase-resolved measured fractions",1,11,"P001-P011","Only P003 supplies directly measured phase fractions."),
 ("EST_SIC_COMPLETE","SiC studies with complete conversion",0,1,"P006","Single paper; conversion was partial and chemistry dependent.")]:
    lo,hi=wilson(k,n);estimands.append(dict(estimand_id=eid,snapshot_id=SNAPSHOT,estimand=label,successes=k,independent_papers=n,estimate=k/n,ci95_low_wilson=lo,ci95_high_wilson=hi,supporting_papers=scope,evidence_domain="direct phase identification",claim_level=1,caveat=caveat))
E={x["estimand_id"]:x for x in estimands}
rt=[e["lnRR"] for e in effects if e["property"]=="UTS" and "RT" in e["condition_uid"] and e["match_grade"]=="A"]
rtmean=sum(rt)/len(rt)
hier=[dict(analysis_id="H_RT_UTS",snapshot_id=SNAPSHOT,outcome="RT UTS matrix-control",independent_papers=2,effect_metric="lnRR",equal_paper_mean=rtmean,percent_change_equivalent=100*(math.exp(rtmean)-1),random_effects_estimate="NOT_IDENTIFIABLE",prediction_interval="NOT_IDENTIFIABLE",lopo_min=min(rt),lopo_max=max(rt),status="DESCRIPTIVE_EQUAL_PAPER_MEAN_ONLY",claim_level=2,reason="Two independent papers cannot support tau2 or a prediction interval."),dict(analysis_id="H_B4C_UTS",snapshot_id=SNAPSHOT,outcome="B4C-fed UTS",independent_papers=2,effect_metric="lnRR",equal_paper_mean="",percent_change_equivalent="",random_effects_estimate="NOT_IDENTIFIABLE",prediction_interval="NOT_IDENTIFIABLE",lopo_min="",lopo_max="",status="DO_NOT_POOL",claim_level=1,reason="Matrix-control DED and Cr3C2/TiC component-control estimands are nonexchangeable.")]

# Local measured calibration.
x=[0,.5,1];y=[0,3.16,5.87];xb=sum(x)/3;yb=sum(y)/3;slope=sum((a-xb)*(b-yb) for a,b in zip(x,y))/sum((a-xb)**2 for a in x);inter=yb-slope*xb
pred=[inter+slope*a for a in x];r2=1-sum((b-c)**2 for b,c in zip(y,pred))/sum((b-yb)**2 for b in y)
dose=[dict(dose_analysis_id="DR_P003_TIB",snapshot_id=SNAPSHOT,paper_uid="P003_ZHANG_2024",x="B4C nominal wt.%",y="measured TiB vol.%",n_doses=3,slope_volpct_per_wtpct=slope,intercept=inter,r2_in_sample=r2,status="LOCAL_DESCRIPTIVE_ONLY",claim_level=1,caveat="One paper; no cross-paper calibration."),dict(dose_analysis_id="DR_P005_THEORY",snapshot_id=SNAPSHOT,paper_uid="P005_VERMA_2022",x="TiB2 wt.%",y="theoretical TiB vol.%",n_doses=3,slope_volpct_per_wtpct="",intercept="",r2_in_sample="",status="THEORETICAL_NOT_MEASURED",claim_level=1,caveat="Excluded from measured calibration."),dict(dose_analysis_id="DR_GLOBAL",snapshot_id=SNAPSHOT,paper_uid="MULTI",x="nominal precursor",y="measured actual phase fraction",n_doses=3,slope_volpct_per_wtpct="NOT_IDENTIFIABLE",intercept="NOT_IDENTIFIABLE",r2_in_sample="NOT_IDENTIFIABLE",status="CONTINUE_DATA_GAP",claim_level=1,caveat="Only one paper has measured phase-resolved fractions.")]

interactions=[
 dict(interaction_id="I_B4C_SIZE",snapshot_id=SNAPSHOT,paper_uid="P004_CHOI_2011",factor_a="B4C size",factor_b="agglomeration/conversion",result="150 um was finer/more homogeneous; 0.5 um agglomerated and remained incomplete",quantitative_model="NOT_IDENTIFIABLE",claim_level=2),
 dict(interaction_id="I_TIB2_DOSE",snapshot_id=SNAPSHOT,paper_uid="P008_ZHONG_2020",factor_a="target TiB fraction",factor_b="residual TiB2",result="Residual TiB2 appeared in high-target regime",quantitative_model="NOT_IDENTIFIABLE",claim_level=2),
 dict(interaction_id="I_RATIO",snapshot_id=SNAPSHOT,paper_uid="P009_LUO_2021",factor_a="TC4/TiB2 ratio",factor_b="phase/morphology",result="Block/cluster TiB2-rich state transitioned to TiB whiskers and Ti-rich phases",quantitative_model="ORDINAL_MAP",claim_level=2),
 dict(interaction_id="I_AL_SIC",snapshot_id=SNAPSHOT,paper_uid="P006_ABBOUD_1994",factor_a="Al content",factor_b="SiC products",result="TiC/silicide/residual-SiC assemblage changed across composition",quantitative_model="NOT_IDENTIFIABLE",claim_level=2),
 dict(interaction_id="I_STRESS_Y2O3",snapshot_id=SNAPSHOT,paper_uid="P007_XU_2023",factor_a="creep stress",factor_b="Y2O3",result="Rate reduction largest at 140 MPa and weak at 160 MPa",quantitative_model="THREE_POINT_DESCRIPTIVE",claim_level=2),
 dict(interaction_id="I_TIME_TICX",snapshot_id=SNAPSHOT,paper_uid="P011_CHRYSANTHOU_2003",factor_a="sintering time",factor_b="TiCx stoichiometry",result="TiCx~0.65 evolved to TiC0.5",quantitative_model="STATE_TRANSITION",claim_level=2)]
heter=[dict(heterogeneity_id="HET_RT_UTS",snapshot_id=SNAPSHOT,scope="matrix-control RT UTS",independent_papers=2,Q="NOT_IDENTIFIABLE",I2="NOT_IDENTIFIABLE",tau2="NOT_IDENTIFIABLE",observed_range=f"lnRR {min(rt):.6f}-{max(rt):.6f}",dominant_sources="matrix/process/phase set",decision="LOPO range only"),dict(heterogeneity_id="HET_TIB2",snapshot_id=SNAPSHOT,scope="TiB2 conversion",independent_papers=4,Q="not fitted",I2="not fitted",tau2="not fitted",observed_range="identity map",dominant_sources="Ti availability, dose, size, time, route",decision="stratify; no complete-conversion pool"),dict(heterogeneity_id="HET_B4C",snapshot_id=SNAPSHOT,scope="B4C conversion",independent_papers=5,Q="not fitted",I2="not fitted",tau2="not fitted",observed_range="identity map",dominant_sources="particle size, carbon activity, matrix/process",decision="separate product detection and depletion"),dict(heterogeneity_id="HET_SIC",snapshot_id=SNAPSHOT,scope="SiC products",independent_papers=1,Q="NOT_IDENTIFIABLE",I2="NOT_IDENTIFIABLE",tau2="NOT_IDENTIFIABLE",observed_range="condition map",dominant_sources="Al chemistry",decision="single-paper map")]

identity=[]
for e in effects:
    changed=e["nominal_attribution_bucket"]!=e["verified_actual_phase_bucket"]
    identity.append(dict(snapshot_id=SNAPSHOT,effect_id=e["effect_id"],paper_uid=e["paper_uid"],property=e["property"],condition_uid=e["condition_uid"],nominal_bucket=e["nominal_attribution_bucket"],verified_bucket=e["verified_actual_phase_bucket"],lnRR_nominal_numeric=e["lnRR"],lnRR_verified_numeric=e["lnRR"],numeric_effect_shift=0.0,attribution_displacement_abs_lnRR=abs(e["lnRR"]) if changed else 0.0,identity_changed=int(changed),interpretation="Numeric effect unchanged; full effect moves to verified identity bucket." if changed else "Identity retained."))
sens=[dict(analysis_id="S_LOPO_P001",snapshot_id=SNAPSHOT,perturbation="leave P001 out",estimate_metric="lnRR",estimate=rt[1],independent_papers=1,conclusion="positive; no pooled inference"),dict(analysis_id="S_LOPO_P002",snapshot_id=SNAPSHOT,perturbation="leave P002 out",estimate_metric="lnRR",estimate=rt[0],independent_papers=1,conclusion="positive; no pooled inference"),dict(analysis_id="S_RECLASS",snapshot_id=SNAPSHOT,perturbation="nominal -> verified identity",estimate_metric="numeric endpoint shift",estimate=0,independent_papers=len(set(e["paper_uid"] for e in effects)),conclusion="numbers unchanged; attribution changed"),dict(analysis_id="S_MEASURED_ONLY",snapshot_id=SNAPSHOT,perturbation="exclude target/theoretical fractions",estimate_metric="global calibration",estimate="NOT_IDENTIFIABLE",independent_papers=1,conclusion="P003 local line only"),dict(analysis_id="S_B4C_DENOM",snapshot_id=SNAPSHOT,perturbation="exclude P010 depletion-unknown",estimate_metric="depletion frequency",estimate=.75,independent_papers=4,conclusion="3/4 with wide interval")]
neg=[
 dict(result_id="N001",snapshot_id=SNAPSHOT,paper_uid="P001_SABAHI_2017",result="Flexural strength -519 MPa (-24.3%)",importance="TiB does not improve every mode"),
 dict(result_id="N002",snapshot_id=SNAPSHOT,paper_uid="P002_LI_2023",result="RT elongation -4.0 points (-48.8%)",importance="strength-ductility penalty"),
 dict(result_id="N003",snapshot_id=SNAPSHOT,paper_uid="P004_CHOI_2011",result="0.5 um B4C agglomerated and remained incomplete",importance="nano precursor not monotonically better"),
 dict(result_id="N004",snapshot_id=SNAPSHOT,paper_uid="P006_ABBOUD_1994",result="SiC partial dissolution; TiC absent in one condition",importance="feed name not a fixed phase set"),
 dict(result_id="N005",snapshot_id=SNAPSHOT,paper_uid="P008_ZHONG_2020",result="High target fraction retained TiB2 and degraded flexure/toughness",importance="target fraction not actual or monotonic benefit"),
 dict(result_id="N006",snapshot_id=SNAPSHOT,paper_uid="P007_XU_2023",result="Y2O3 rate benefit only ~5.7% at 160 MPa",importance="stress-dependent benefit"),
 dict(result_id="N007",snapshot_id=SNAPSHOT,paper_uid="P011_CHRYSANTHOU_2003",result="TiCx~0.65 -> TiC0.5",importance="generic TiC erases stoichiometry")]
conf=[
 dict(conflict_id="C001",snapshot_id=SNAPSHOT,paper_uid="P001_SABAHI_2017",field="identity",nominal_or_legacy="TiB2/Ti or target TiB",direct_evidence="TiB + residual TiB2",resolution="separate precursor/products/residual",status="OPEN_FRACTION_GAP"),
 dict(conflict_id="C002",snapshot_id=SNAPSHOT,paper_uid="P002_LI_2023",field="identity",nominal_or_legacy="B4C reinforcement",direct_evidence="B4C depleted; TiB+TiC",resolution="dual-phase attribution",status="RESOLVED_IDENTITY"),
 dict(conflict_id="C003",snapshot_id=SNAPSHOT,paper_uid="P003_ZHANG_2024",field="TiC attribution",nominal_or_legacy="B4C effect",direct_evidence="Cr3C2 is baseline carbon source",resolution="do not attribute all TiC/change to B4C",status="OPEN_CONFOUNDED_ATTRIBUTION"),
 dict(conflict_id="C004",snapshot_id=SNAPSHOT,paper_uid="P004_CHOI_2011",field="completion",nominal_or_legacy="target 10 vol.% TiB+TiC",direct_evidence="nano condition incomplete",resolution="condition-specific state",status="RESOLVED_CONDITIONAL"),
 dict(conflict_id="C005",snapshot_id=SNAPSHOT,paper_uid="P005_VERMA_2022",field="fraction",nominal_or_legacy="0.32/0.81/1.62 vol.% TiB",direct_evidence="theoretical values",resolution="exclude from measured calibration",status="RESOLVED_LEVEL"),
 dict(conflict_id="C006",snapshot_id=SNAPSHOT,paper_uid="P008_ZHONG_2020",field="fraction",nominal_or_legacy="target 5-80 vol.% TiB",direct_evidence="residual TiB2 at high target",resolution="target != actual",status="OPEN_FRACTION_GAP"),
 dict(conflict_id="C007",snapshot_id=SNAPSHOT,paper_uid="P011_CHRYSANTHOU_2003",field="carbide identity",nominal_or_legacy="TiC",direct_evidence="TiCx trajectory",resolution="encode x and thermal state",status="RESOLVED_STATE_DEPENDENT"),
 dict(conflict_id="C008",snapshot_id=SNAPSHOT,paper_uid="MULTI",field="duplicate objects",nominal_or_legacy="multiple PDF/index copies",direct_evidence="same DOI/title/SHA",resolution="deduplicate by paper_uid",status="RESOLVED_DEDUP"),
 dict(conflict_id="C009",snapshot_id=SNAPSHOT,paper_uid="UPSTREAM",field="snapshot",nominal_or_legacy="V29 authority required",direct_evidence="not accessible",resolution="cohort build only",status="BLOCKED_INPUT")]

ontology=[
 ("PRE_TIB2","precursor","TiB2","titanium diboride","Never infer TiB or retention from feed name"),("PRE_B4C","precursor","B4C","boron carbide","Require direct depletion/product evidence"),("PRE_SIC","precursor","SiC","silicon carbide","Represent partial dissolution and residual"),("PRE_TIC","precursor","TiC","TiCx","Store carbon stoichiometry where resolved"),("PRE_CR3C2","precursor","Cr3C2","chromium carbide","Confounds B4C-to-TiC attribution"),("PRE_Y2O3","precursor","Y2O3","yttria","TEM/EDS can confirm below XRD detection"),("PH_TIB","actual_phase","TiB","TiBw; monoboride","Upgrade with XRD/TEM/EDS and reaction consistency"),("PH_TIC","actual_phase","TiC","TiCp","Do not collapse TiC/TiCx/TiC0.5"),("PH_TICX","actual_phase","TiCx","non-stoichiometric TiC","Store x and condition"),("PH_TIC05","actual_phase","TiC0.5","carbon-deficient carbide","Keep distinct from generic TiC"),("PH_SIL","actual_phase","Ti5Si3/Ti3Si","silicide","Keep phase-specific identity"),("PH_Y2O3","actual_phase","Y2O3","retained yttria","Use direct local evidence"),("M_WHISKER","morphology","whisker/fiber","needle; rod","Store length/diameter/aspect ratio"),("M_PARTICLE","morphology","particle","equiaxed; spherical","Morphology is not phase identity"),("M_NETWORK","morphology","network","quasi-continuous","Requires spatial evidence"),("A_NOM","ambiguity","NOMINAL_ONLY","feed-name-only","actual_phase=unknown"),("A_PART","ambiguity","PARTIAL_CONVERSION","residual precursor","Store products and residual"),("A_STOICH","ambiguity","SUBSTOICHIOMETRIC","TiCx","Store x and state"),("A_TARGET","ambiguity","TARGET_NOT_MEASURED","theoretical fraction","Exclude from measured calibration")]
ontology=[dict(entity_id=a,entity_type=b,canonical_name=c,synonyms=d,identity_rule=e) for a,b,c,d,e in ontology]
amb={"PARTIAL_CONVERSION":"PARTIAL_CONVERSION","CONDITION_DEPENDENT_INCOMPLETE":"PARTIAL_CONVERSION|SIZE_DEPENDENT","TIB_FORMATION_FRACTION_THEORETICAL":"TARGET_NOT_MEASURED","PARTIAL_DISSOLUTION_CONDITION_DEPENDENT":"PARTIAL_CONVERSION|CHEMISTRY_DEPENDENT","DOSE_DEPENDENT_RESIDUAL":"PARTIAL_CONVERSION|DOSE_DEPENDENT|TARGET_NOT_MEASURED","RATIO_DEPENDENT_IDENTITY":"PARTIAL_CONVERSION|RATIO_DEPENDENT","TIME_DEPENDENT_SUBSTOICHIOMETRY":"SUBSTOICHIOMETRIC|TIME_DEPENDENT"}
cross=[]
for p in papers:
    nominal=next((r["nominal_addition"] for r in cohort if r["paper_uid"]==p["uid"] and r["nominal_addition"]!="0"),"varied")
    cross.append(dict(snapshot_id=SNAPSHOT,source_hash=p["source_hash"],paper_uid=p["uid"],doi=p["doi"],matrix=p["matrix"],process=p["process"],precursor_name=p["precursor"],nominal_addition=nominal,actual_phase=p["actual"],morphology=p["morph"],measured_fraction_available=p["fraction"],conversion_class=p["conversion"],ambiguity_code=amb.get(p["conversion"],"DIRECT_PHASE_SET_FRACTION_UNMEASURED"),evidence_methods=p["methods"],evidence_level="DIRECT_PHASE_IDENTIFICATION",claim_ceiling="actual phase permitted; fraction unknown unless measured"))
edges=[
 dict(source="TiB2",reaction="Ti-rich conversion",target="TiB/TiBw",paper_count=4,papers="P001;P005;P008;P009",conditionality="dose, Ti availability, time, size"),dict(source="TiB2",reaction="incomplete conversion",target="residual TiB2",paper_count=3,papers="P001;P008;P009",conditionality="coarse/high-dose/Ti-poor"),dict(source="B4C",reaction="5Ti+B4C -> 4TiB+TiC",target="TiB+TiC",paper_count=5,papers="P002;P003;P004;P007;P010",conditionality="size, carbon activity, matrix/process"),dict(source="B4C",reaction="agglomeration-limited",target="residual/incomplete B4C",paper_count=1,papers="P004",conditionality="0.5 um feed"),dict(source="Cr3C2",reaction="2Ti+Cr3C2 -> 2TiC+3Cr",target="TiC",paper_count=1,papers="P003",conditionality="confounds B4C attribution"),dict(source="SiC",reaction="partial dissolution",target="TiC+silicide+residual SiC",paper_count=1,papers="P006",conditionality="Al chemistry"),dict(source="Y2O3",reaction="retained addition",target="Y2O3",paper_count=1,papers="P007",conditionality="TEM/EDS-visible"),dict(source="TiC",reaction="sintering equilibration",target="TiCx -> TiC0.5",paper_count=1,papers="P011",conditionality="time")]
graph=dict(window_id=WINDOW,snapshot_id=SNAPSHOT,graph_semantics="edge counts are independent-paper support, not probabilities",nodes=sorted(set(sum(([e["source"],e["reaction"],e["target"]] for e in edges),[]))),edges=edges,ambiguity_codes=sorted(set(x["ambiguity_code"] for x in cross)))

# Figure data.
cal=[
 dict(paper_uid="P003",precursor="B4C",nominal_wt_pct=0,actual_phase="TiB",phase_vol_pct=0,fraction_status="MEASURED",note="baseline"),dict(paper_uid="P003",precursor="B4C",nominal_wt_pct=.5,actual_phase="TiB",phase_vol_pct=3.16,fraction_status="MEASURED",note="TMC2"),dict(paper_uid="P003",precursor="B4C",nominal_wt_pct=1,actual_phase="TiB",phase_vol_pct=5.87,fraction_status="MEASURED",note="TMC3"),dict(paper_uid="P003",precursor="B4C+Cr3C2",nominal_wt_pct=0,actual_phase="TiC",phase_vol_pct=9.77,fraction_status="MEASURED_CONFOUNDED",note="Cr3C2 baseline"),dict(paper_uid="P003",precursor="B4C+Cr3C2",nominal_wt_pct=.5,actual_phase="TiC",phase_vol_pct=6.47,fraction_status="MEASURED_CONFOUNDED",note="not B4C-only"),dict(paper_uid="P003",precursor="B4C+Cr3C2",nominal_wt_pct=1,actual_phase="TiC",phase_vol_pct=6.05,fraction_status="MEASURED_CONFOUNDED",note="not B4C-only"),dict(paper_uid="P005",precursor="TiB2",nominal_wt_pct=.2,actual_phase="TiB",phase_vol_pct=.32,fraction_status="THEORETICAL",note="not measured"),dict(paper_uid="P005",precursor="TiB2",nominal_wt_pct=.5,actual_phase="TiB",phase_vol_pct=.81,fraction_status="THEORETICAL",note="not measured"),dict(paper_uid="P005",precursor="TiB2",nominal_wt_pct=1,actual_phase="TiB",phase_vol_pct=1.62,fraction_status="THEORETICAL",note="not measured"),dict(paper_uid="P001",precursor="TiB2",nominal_wt_pct=2.4,actual_phase="TiB",phase_vol_pct=4,fraction_status="TARGET_NOT_MEASURED",note="residual TiB2"),dict(paper_uid="P004",precursor="B4C",nominal_wt_pct=1.88,actual_phase="TiB+TiC",phase_vol_pct=10,fraction_status="TARGET_NOT_MEASURED",note="nano condition incomplete")]
up=[
 ("P001",1,0,1,1,1,0),("P002",1,1,1,1,1,0),("P003",1,1,1,1,1,1),("P004",0,0,1,1,1,0),("P005",1,1,0,1,1,0),("P006",0,1,1,1,0,0),("P007",1,1,1,1,1,0),("P008",1,0,0,1,1,0),("P009",1,1,1,1,1,0),("P010",0,1,1,1,1,0),("P011",1,0,1,1,1,0)]
up=[dict(paper_uid=a,XRD=b,TEM=c,EDS=d,SEM=e,Stoichiometry=f,MeasuredFraction=g) for a,b,c,d,e,f,g in up]
tornado=sorted(identity,key=lambda r:r["attribution_displacement_abs_lnRR"],reverse=True)[:12]
for r in tornado:r["display_label"]=f"{r['paper_uid'].split('_')[0]} | {r['property']}"

# Provenance.
prov=[]
for p in papers:prov.append(dict(snapshot_id=SNAPSHOT,source_hash=p["source_hash"],source_hash_type=p["source_hash_type"],paper_uid=p["uid"],sample_uid="MULTIPLE",condition_uid="SEE_ANALYSIS_COHORT",doi=p["doi"],citation=p["citation"],evidence_methods=p["methods"],fact=p["fact"],evidence_level="DIRECT_PRIMARY",locator="project File Library indexed primary PDF/figure evidence; exact publisher-file SHA unavailable in this run",promotion_authority="NONE"))
for e in estimands:prov.append(dict(snapshot_id=SNAPSHOT,source_hash=hbytes(canon(e).encode()),source_hash_type="DERIVED_ROW_SHA256",paper_uid="MULTI",sample_uid="MULTI",condition_uid=e["estimand_id"],doi="MULTI",citation="Derived from direct-primary cohort",evidence_methods="paper deduplication + Wilson interval",fact=e["estimand"],evidence_level="DERIVED_CALCULATION",locator=e["supporting_papers"],promotion_authority="NONE"))

# Required and scope-specific tables.
wcsv("INPUT_LEDGER.csv",ledger);wcsv("SOURCE_MEMBER_AUDIT.csv",ledger);wcsv("ANALYSIS_COHORT.csv",cohort);wcsv("PAIR_MATCHES.csv",pairs);wcsv("EFFECT_ESTIMATES.csv",effects);wcsv("HIERARCHICAL_RESULTS.csv",hier);wcsv("DOSE_RESPONSE.csv",dose);wcsv("INTERACTION_EFFECTS.csv",interactions);wcsv("HETEROGENEITY.csv",heter);wcsv("SENSITIVITY_ANALYSIS.csv",sens);wcsv("NULL_NEGATIVE_RESULTS.csv",neg);wcsv("CONFLICT_LEDGER.csv",conf);wcsv("REINFORCEMENT_ONTOLOGY.csv",ontology);wcsv("PRECURSOR_PHASE_CROSSWALK.csv",cross);wcsv("IDENTITY_SENSITIVITY.csv",identity);wcsv("CONVERSION_ESTIMANDS.csv",estimands);wjson("PHASE_IDENTITY_GRAPH.json",graph);wtext("PROVENANCE.jsonl","\n".join(canon(x) for x in prov))
wcsv("figure_data/01_phase_flow.csv",edges);wcsv("figure_data/02_fraction_calibration.csv",cal);wcsv("figure_data/03_evidence_upset.csv",up);wcsv("figure_data/04_identity_tornado.csv",tornado)

# Plot implementation and one executable per figure.
plots=r'''from pathlib import Path
import csv
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch
B=Path(__file__).resolve().parents[1]
def rows(n):return list(csv.DictReader((B/'figure_data'/n).open(encoding='utf-8-sig')))
def save(fig,name):
 for ext,dpi in [('svg',None),('pdf',None),('png',600)]:fig.savefig(B/'figures'/f'{name}.{ext}',bbox_inches='tight',dpi=dpi)
 plt.close(fig)
def phase():
 r=rows('01_phase_flow.csv');fig,ax=plt.subplots(figsize=(14,8));ax.set_xlim(-.05,2.05);ax.set_ylim(0,1);ax.axis('off');pos={}
 for c,k in enumerate(['source','reaction','target']):
  vals=[]
  for x in r:
   if x[k] not in vals:vals.append(x[k])
  ys=[.92-i*(.84/max(1,len(vals)-1)) for i in range(len(vals))] if len(vals)>1 else [.5]
  for v,y in zip(vals,ys):pos[c,v]=y;ax.text(c,y,v,ha='center',va='center',fontsize=8,bbox=dict(boxstyle='round,pad=.3',facecolor='white',edgecolor='black',linewidth=.8))
 for x in r:
  for c,a,b in [(0,x['source'],x['reaction']),(1,x['reaction'],x['target'])]:
   y0,y1=pos[c,a],pos[c+1,b];path=MP([(c+.08,y0),(c+.38,y0),(c+.62,y1),(c+.92,y1)],[MP.MOVETO,MP.CURVE4,MP.CURVE4,MP.CURVE4]);ax.add_patch(PathPatch(path,fill=False,linewidth=1+2.1*float(x['paper_count']),alpha=.35,capstyle='round'))
 for c,t in enumerate(['Precursor','Reaction / conversion state','Verified actual phase set']):ax.text(c,.985,t,ha='center',va='top',fontweight='bold')
 ax.set_title('Precursor → Reaction Path → Actual Phase (direct evidence; n=11 papers)',pad=20);ax.text(1,.01,'Band width = independent-paper support; pathways are conditional, not probabilities.',ha='center',fontsize=8);save(fig,'01_phase_flow_sankey')
def calibration():
 r=rows('02_fraction_calibration.csv');fig,ax=plt.subplots(figsize=(10,7));m={'MEASURED':'o','MEASURED_CONFOUNDED':'s','THEORETICAL':'^','TARGET_NOT_MEASURED':'x'}
 for st,ma in m.items():
  q=[x for x in r if x['fraction_status']==st]
  if q:ax.scatter([float(x['nominal_wt_pct']) for x in q],[float(x['phase_vol_pct']) for x in q],marker=ma,s=70,label=st.replace('_',' '))
 q=[x for x in r if x['fraction_status']=='MEASURED' and x['actual_phase']=='TiB'];x=np.array([float(a['nominal_wt_pct']) for a in q]);y=np.array([float(a['phase_vol_pct']) for a in q]);c=np.polyfit(x,y,1);xx=np.linspace(0,1.05,100);ax.plot(xx,c[0]*xx+c[1],'--',label=f'P003 local TiB fit: y={c[0]:.2f}x{c[1]:+.2f}')
 ax.set(xlabel='Nominal precursor addition (wt.%)',ylabel='Actual / target reinforcement fraction (vol.%)',title='Measured, Theoretical and Target Phase Fractions');ax.legend(fontsize=8);ax.grid(alpha=.25);ax.text(.01,-.16,'Only P003 has phase-resolved measured fractions; the fit is local, not a cross-paper calibration.',transform=ax.transAxes,fontsize=8);save(fig,'02_fraction_calibration')
def upset():
 r=rows('03_evidence_upset.csv');ms=['XRD','TEM','EDS','SEM','Stoichiometry','MeasuredFraction'];c=Counter(tuple(int(x[m]) for m in ms) for x in r);it=sorted(c.items(),key=lambda z:(-z[1],z[0]));fig=plt.figure(figsize=(12,8));a=fig.add_axes([.12,.48,.82,.42]);d=fig.add_axes([.12,.1,.82,.32],sharex=a);xs=range(len(it));a.bar(list(xs),[n for _,n in it]);a.set_ylabel('Independent papers');a.set_title('Evidence-method intersections for phase identity (n=11 papers)');a.set_xticks([])
 for i,(co,n) in enumerate(it):
  on=[j for j,v in enumerate(co) if v]
  if on:d.plot([i,i],[min(on),max(on)],linewidth=1)
  for j,v in enumerate(co):d.scatter(i,j,s=45 if v else 12,alpha=1 if v else .25)
 d.set_yticks(range(len(ms)));d.set_yticklabels(ms);d.invert_yaxis();d.set_xlabel('Evidence-method combination');d.grid(axis='y',alpha=.2);save(fig,'03_evidence_upset')
def tornado():
 r=sorted(rows('04_identity_tornado.csv'),key=lambda x:float(x['attribution_displacement_abs_lnRR']));fig,ax=plt.subplots(figsize=(12,8));v=[float(x['attribution_displacement_abs_lnRR']) for x in r];ax.barh([x['display_label'] for x in r],v);ax.set_xlabel('Absolute lnRR reattributed from nominal precursor bucket');ax.set_title('Identity Misclassification: Effect Attribution Displacement')
 for i,x in enumerate(r):ax.text(v[i]+max(v or [1])*.01,i,f"{x['nominal_bucket']} → {x['verified_bucket']}",va='center',fontsize=7)
 ax.grid(axis='x',alpha=.25);ax.text(.01,-.12,'Numeric paired effects do not change; the full effect moves to a different identity bucket.',transform=ax.transAxes,fontsize=8);save(fig,'04_identity_tornado')
'''
wtext("plot_code/qm02_plots.py",plots)
for name,fn in [("01_phase_flow_sankey","phase"),("02_fraction_calibration","calibration"),("03_evidence_upset","upset"),("04_identity_tornado","tornado")]:wtext(f"plot_code/{name}.py",f"#!/usr/bin/env python3\nfrom qm02_plots import {fn}\n{fn}()")
wtext("requirements.txt","matplotlib==3.9.2\nnumpy==2.1.1")
(OUT/"figures").mkdir(exist_ok=True)
for s in sorted((OUT/"plot_code").glob("0*.py")):subprocess.run([sys.executable,str(s)],cwd=s.parent,check=True)

# Narrative.
verdict=f'''# QM02 Executive Verdict

`WINDOW={WINDOW} | SNAPSHOT={SNAPSHOT} | UPSTREAM={UPSTREAM} | MODE=COHORT_BUILD`

## Decision

The phase-identity question is answered at **claim level 2**, but this is not the authoritative V29-bound terminal synthesis because the V29 atomic/provenance snapshot was absent. Status: `CONTINUE_DATA_GAP`.

## Quantitative findings

1. **TiB2 is a precursor, not a final-phase synonym.** 4/4 direct studies detected TiB/TiBw (Wilson 95% CI {E['EST_TIB2_TO_TIB']['ci95_low_wilson']:.3f}-{E['EST_TIB2_TO_TIB']['ci95_high_wilson']:.3f}), yet three studies also show residual TiB2 or dose/ratio-dependent incomplete conversion.
2. **B4C usually maps to a dual actual phase set.** 5/5 direct studies detected TiB+TiC (Wilson 95% CI {E['EST_B4C_TO_TIB_TIC']['ci95_low_wilson']:.3f}-{E['EST_B4C_TO_TIB_TIC']['ci95_high_wilson']:.3f}). Complete depletion was supported in 3/4 assessable studies (75%; Wilson 95% CI {E['EST_B4C_DEPLETION']['ci95_low_wilson']:.3f}-{E['EST_B4C_DEPLETION']['ci95_high_wilson']:.3f}); nano-B4C agglomeration is a direct counterexample.
3. **Measured actual fractions are the bottleneck.** Only 1/11 core papers reports phase-resolved measured volume fractions (9.1%; Wilson 95% CI {E['EST_MEASURED_FRACTION']['ci95_low_wilson']:.3f}-{E['EST_MEASURED_FRACTION']['ci95_high_wilson']:.3f}). Target/theoretical fractions are firewalled from measured values.
4. **Identity relabeling changes attribution, not the same-pair number.** The largest selected attribution displacement is |lnRR|={max(x['attribution_displacement_abs_lnRR'] for x in identity):.3f}. Numeric Δ and lnRR remain unchanged; the full observed effect moves from a nominal precursor bucket to a verified actual-phase bucket.
5. **A general cross-paper phase-effect model is not identifiable.** The strict matrix-control RT-UTS subset contains two papers: equal-paper mean lnRR={rtmean:.3f} ({100*(math.exp(rtmean)-1):.1f}% equivalent), LOPO {min(rt):.3f}-{max(rt):.3f}; tau2 and prediction interval are not defensible.

## Counterexamples that control the conclusion

- 2.4 wt.% TiB2 after SPS produced TiB whiskers **plus residual TiB2**.
- 5 wt.% B4C after DED disappeared and produced TiB whiskers + equiaxed TiC.
- 0.5 um B4C agglomerated and was not fully synthesized.
- SiC conversion was partial and Al-chemistry dependent, with TiC/silicides/residual SiC.
- Nominal TiC evolved from TiCx~0.65 to TiC0.5 with sintering time.

## Claim ceiling

Actual-phase claims require direct XRD/TEM/SAED/EDS/EPMA or reaction-consistent evidence. Feed names, targets and theoretical fractions are not upgraded to measured actual fractions. No Gold, ACTIVE, schema or production-model mutation occurred.
'''
wtext("00_EXECUTIVE_VERDICT.md",verdict)
wtext("METHODS.md",'''# Methods

Independent papers were deduplicated by DOI/paper_uid. Rows preserve paper × sample × process/condition × actual phase. Actual phases were upgraded only from direct XRD, TEM/HRTEM/SAED, EDS/EPMA/phase mapping or reaction-consistent evidence. Effects are ΔY and lnRR=ln(Yt/Yc); reported SDs and replicate counts support delta-method intervals where available. Frequencies use Wilson 95% intervals and are conditional on this purpose-selected direct-evidence cohort. Identity sensitivity is attribution displacement: numeric paired effects remain fixed while |lnRR| moves between identity buckets. Measured, theoretical and target fractions are separate evidence classes. Random-effects inference is marked NOT_IDENTIFIABLE where independent papers are insufficient. All plots read figure_data CSV and export SVG/PDF/600 dpi PNG.''')
wtext("LIMITATIONS.md",f'''# Limitations

1. V29 ATOMIC_RECORDS, PROVENANCE, registries and authoritative snapshot hashes were absent; `{SNAPSHOT}` is a transparent cohort-build snapshot.
2. Uploaded ZIP members could not be enumerated in the failed local backend; top-level packages have terminal dispositions, but member-level audit remains requested.
3. Only one core paper has phase-resolved measured fractions; global nominal-to-actual calibration is NOT_IDENTIFIABLE.
4. The corpus is enriched for conversion evidence; 100% product-detection values are not population prevalence.
5. Matrix controls, component controls, temperatures, load modes and processes are not pooled when nonexchangeable.
6. XRD non-detection is not treated as absence when TEM/EDS confirms a minor phase.
7. Maximum claim level is 2; no process-independent causal phase effect is claimed.
8. This package is not Gold, VALIDATED, a production model or an ACTIVE promotion request.''')
plotspec=dict(window_id=WINDOW,snapshot_id=SNAPSHOT,plots=[dict(id="01_phase_flow_sankey",data="figure_data/01_phase_flow.csv",code="plot_code/01_phase_flow_sankey.py",outputs=[f"figures/01_phase_flow_sankey.{e}" for e in ["svg","pdf","png"]],denominator="11 independent papers"),dict(id="02_fraction_calibration",data="figure_data/02_fraction_calibration.csv",code="plot_code/02_fraction_calibration.py",outputs=[f"figures/02_fraction_calibration.{e}" for e in ["svg","pdf","png"]],denominator="1 measured-fraction paper; others flagged"),dict(id="03_evidence_upset",data="figure_data/03_evidence_upset.csv",code="plot_code/03_evidence_upset.py",outputs=[f"figures/03_evidence_upset.{e}" for e in ["svg","pdf","png"]],denominator="11 independent papers"),dict(id="04_identity_tornado",data="figure_data/04_identity_tornado.csv",code="plot_code/04_identity_tornado.py",outputs=[f"figures/04_identity_tornado.{e}" for e in ["svg","pdf","png"]],denominator=f"top 12 of {len(identity)} paired effects")])
wjson("PLOT_SPECS.json",plotspec)
request=dict(window_id=WINDOW,current_snapshot_id=SNAPSHOT,status="CONTINUE_DATA_GAP",required_assets=[dict(priority=1,asset="V29/ATOMIC_RECORDS.*",reason="authoritative exhaustive cohort"),dict(priority=1,asset="V29/PROVENANCE.jsonl + paper/source registry",reason="original hashes and exact locators"),dict(priority=1,asset="V29/CONFLICT_LEDGER.csv + EXCLUDED_RECORDS.csv",reason="merge prior decisions"),dict(priority=2,asset="phase-resolved measured fractions",preferred_methods=["Rietveld","quantitative image analysis","EBSD phase fraction","mass balance with uncertainty"],reason="general nominal-to-actual bias"),dict(priority=2,asset="exact metadata for P011 and related TiCx paper",reason="resolve identity and duplicates"),dict(priority=2,asset="member manifests + SHA256 for all top-level packages",reason="complete source audit"),dict(priority=3,asset="raw table/figure data",reason="cluster bootstrap and uncertainty")],acceptance="Preserve paper/sample/condition IDs and package/member SHA256; independent validation before promotion.")
wjson("WEB_TO_LOCAL_REQUEST.json",request)
wtext("LOCAL_ABSORPTION_PROMPT.md",f'''# Local Absorption Prompt

1. Verify checksums, manifest, ZIP CRC and independent extraction.
2. Absorb only into `q40/QM02`; do not modify ACTIVE_TITMC, Gold, unified Schema or production registry.
3. Resolve WEB_TO_LOCAL_REQUEST.json, rebind every row to the authoritative V29 snapshot/hash/registry and rerun.
4. Manually inspect every high-influence effect, residual-precursor claim and measured fraction.
5. Promote nothing beyond SCREENED_EVIDENCE before original-source hashes and locators pass independent verification.

Current snapshot: `{SNAPSHOT}`; state: `CONTINUE_DATA_GAP`.''')
wtext("README.md",f'''# FINAL_QM02

- Snapshot: `{SNAPSHOT}`
- Core papers: 11
- Cohort rows: {len(cohort)}
- Matched effects: {len(effects)}
- Figures: 4 × SVG/PDF/600 dpi PNG
- Claim ceiling: 2
- State: `CONTINUE_DATA_GAP`

Start with 00_EXECUTIVE_VERDICT.md, PRECURSOR_PHASE_CROSSWALK.csv, CONVERSION_ESTIMANDS.csv, IDENTITY_SENSITIVITY.csv and WEB_TO_LOCAL_REQUEST.json.''')
status=dict(window_id=WINDOW,snapshot_id=SNAPSHOT,upstream_snapshot=UPSTREAM,papers_seen=11,papers_included=11,independent_papers=11,atomic_rows=len(cohort),matched_pairs=len(pairs),effect_estimates=len(effects),plots_generated=4,open_conflicts=sum(x["status"].startswith("OPEN") or x["status"]=="BLOCKED_INPUT" for x in conf),claim_level_max=2,status="CONTINUE_DATA_GAP",next_action="Absorb V29 atomic/provenance registries and phase-resolved measured fractions; rerun.",production_model_registration="FORBIDDEN_NOT_ATTEMPTED",active_or_gold_mutation="NONE",generated_at=GENERATED)
wjson("WINDOW_STATUS.json",status)

# Self-contained code and validator.
(OUT/"analysis_code").mkdir(exist_ok=True);shutil.copy2(Path(__file__),OUT/"analysis_code"/"build_qm02.py")
validator='''#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
b=Path(__file__).resolve().parents[1]
req=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256","REINFORCEMENT_ONTOLOGY.csv","PRECURSOR_PHASE_CROSSWALK.csv","PHASE_IDENTITY_GRAPH.json","IDENTITY_SENSITIVITY.csv"]
missing=[x for x in req if not (b/x).exists()];bad=[];n=0
for line in (b/'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines():
 if not line.strip():continue
 d,r=line.split('  ',1);n+=1
 if hashlib.sha256((b/r).read_bytes()).hexdigest()!=d:bad.append(r)
print(json.dumps({'pass':not missing and not bad,'missing':missing,'checksum_mismatches':bad,'checked_files':n},indent=2));sys.exit(0 if not missing and not bad else 1)
'''
wtext("analysis_code/validate_package.py",validator)

# Validation report precedes manifest/checksums.
wjson("VALIDATION_REPORT.json",dict(pass_=True,window_id=WINDOW,snapshot_id=SNAPSHOT,required_missing=[],nested_zip_count=0,status="CONTINUE_DATA_GAP",note="Final checksum validation runs after manifest creation."))
files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in {'MANIFEST.json','CHECKSUMS.sha256'})
manifest=dict(window_id=WINDOW,snapshot_id=SNAPSHOT,upstream_snapshot=UPSTREAM,generated_at=GENERATED,file_count_excluding_manifest_and_checksums=len(files),nested_zip_count=0,contract_status="CONTINUE_DATA_GAP",entries=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=hfile(p)) for p in files])
wjson("MANIFEST.json",manifest)
files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='CHECKSUMS.sha256');wtext("CHECKSUMS.sha256","\n".join(f"{hfile(p)}  {p.relative_to(OUT).as_posix()}" for p in files))
subprocess.run([sys.executable,str(OUT/"analysis_code"/"validate_package.py")],check=True)
if ZIP.exists():ZIP.unlink()
with zipfile.ZipFile(ZIP,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(OUT).as_posix())
with zipfile.ZipFile(ZIP) as z:
    assert z.testzip() is None and not any(n.lower().endswith('.zip') for n in z.namelist())
print(json.dumps(dict(window=WINDOW,snapshot=SNAPSHOT,status="CONTINUE_DATA_GAP",papers=11,cohort_rows=len(cohort),effects=len(effects),files=sum(p.is_file() for p in OUT.rglob('*')),zip_sha256=hfile(ZIP),zip_bytes=ZIP.stat().st_size),indent=2))
print("STATUS: CONTINUE_DATA_GAP | WINDOW=QM02 | MISSING=V29_ATOMIC_SNAPSHOT,GENERALIZABLE_NOMINAL_TO_MEASURED_FRACTION_COHORT | NEXT=ABSORB_REQUESTED_FILES_AND_RECALCULATE")
