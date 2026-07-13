#!/usr/bin/env python3
from __future__ import annotations

import csv, hashlib, json, math, os, statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path("FINAL_QM11"); FIG=ROOT/"figures"; FD=ROOT/"figure_data"; PC=ROOT/"plot_code"; AC=ROOT/"analysis_code"
for p in (ROOT,FIG,FD,PC,AC): p.mkdir(parents=True,exist_ok=True)
SNAPSHOT="RECOVERY_QM11_20260713_WEB"; RT=25.0

def uid(prefix,*x): return prefix+"_"+hashlib.sha256("|".join(map(str,x)).encode()).hexdigest()[:20]
def fnum(x):
    if x is None:return ""
    if isinstance(x,float):return f"{x:.10g}"
    return str(x)
def wc(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or (list(rows[0]) if rows else ["status","reason"])
    with path.open("w",encoding="utf-8-sig",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=fields,extrasaction="ignore");w.writeheader()
        for r in rows:w.writerow({k:fnum(r.get(k)) for k in fields})
def wj(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def wt(path,text):path.write_text(text.rstrip()+"\n",encoding="utf-8")

sources={
"YE2025":("叶沁 2025 原位TiC/Ti-5556硕士论文","0681 PDF, Tables 3.1–3.3, pp.19–35",""),
"QI2012":("Qi et al. 2012 TiC/TA15","primary PDF tensile table and 600/650C results","10.1016/j.msea.2012.05.092"),
"LI2023":("Li et al. 2023 DED (TiB+TiC)/Ti6Al4V","primary PDF Table 3","10.1016/j.msea.2022.144466"),
"QIU2021":("Qiu Peikun 2021 particulate/IMI834 PhD thesis","primary thesis high-temperature result summary",""),
"WANG2017":("Wang et al. 2017 network TMC creep","primary paper 873K/200MPa creep rates","10.1038/srep40823")}
archives=[
"00_统一上传总控与校验信息_20260712.zip","S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
"S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
* [f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1,9)],
"S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
* [f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1,4)],
* [f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1,11)]]
ledger=[]
for i,a in enumerate(archives,1):
    cat="P0_LITERATURE" if a.startswith("TITMC") else "P1_FROZEN_DATA_HARNESS" if a.startswith("S03") else "P2_PLATFORM_CODE_CONTROL"
    ledger.append(dict(index=i,input_id=uid("IN",a),snapshot_id=SNAPSHOT,source_name=a,source_type="PROJECT_ARCHIVE",path_or_locator=f"/mnt/data/{a}",source_hash="BIND_FROM_LOCAL_VERIFIED_LEDGER",source_hash_kind="LOCAL_BIND_REQUIRED",priority=cat,window_relevance="full corpus/frozen evidence/method governance",terminal_use_status="REGISTERED_AND_ROLE_CLASSIFIED",opened_or_consumed="LEDGER_AND_TARGETED_DISCOVERY",notes="The web return does not claim fresh decompression of every multi-GB member; authoritative package/member hashes remain a local absorption gate."))
for k,(title,loc,doi) in sources.items():
    ledger.append(dict(index=len(ledger)+1,input_id=uid("IN",k),snapshot_id=SNAPSHOT,source_name=title,source_type="PRIMARY_LITERATURE",path_or_locator=loc,source_hash="ORIGINAL_BYTE_HASH_LOCAL_BIND_REQUIRED",source_hash_kind="MISSING_IN_WEB_RETURN",priority="P0_PRIMARY_ORIGINAL",window_relevance="direct quantitative or claim-boundary evidence",terminal_use_status="USED_DIRECTLY" if k!="WANG2017" else "USED_FOR_SERVICE_CLAIM_CEILING",opened_or_consumed="YES",notes=f"DOI={doi}"))
wc(ROOT/"INPUT_LEDGER.csv",ledger)
wj(ROOT/"OPENED_SOURCES.json",{"window_id":"QM11","project_archives_registered":len(archives),"primary_full_text_objects_deep_read":list(sources),"corpus_horizon":{"elsevier_xml_count":78683,"uncompressed_GiB":24.1845},"archive_deep_parse_claim":False,"reason":"Targeted role-based use; no false claim that every broad-corpus object was scientifically relevant to QM11."})

records=[]
def add(paper,sample,matrix,reinf,dose,dose_unit,process,ht,state,temp,prop,val,unit,grade,loc,sd=None,n=None,speed=None,hold=None,scope="IN_SCOPE",note=""):
    su=uid("SMP",paper,sample,ht,state); cu=uid("COND",paper,su,temp,prop,speed); ru=uid("REC",paper,su,cu,prop,val)
    records.append(dict(record_uid=ru,snapshot_id=SNAPSHOT,paper_uid=paper,sample_uid=su,condition_uid=cu,source_title=sources[paper][0],doi=sources[paper][2],sample_label=sample,matrix_family=matrix,reinforcement_type=reinf,reinforcement_dose=dose,dose_unit=dose_unit,process=process,heat_treatment=ht,microstructure_state=state,test_mode="TENSION",temperature_C=temp,exposure_type="ROOM_TEMPERATURE_REFERENCE" if temp==RT else "IMMEDIATE_HIGH_T_TENSILE",exposure_time_min=hold,strain_rate_mode="CROSSHEAD_SPEED_REPORTED" if speed else "NOT_RECOVERED",test_speed_mm_min=speed,orientation="REPORTED_OR_UNSPECIFIED",property=prop,value=val,unit=unit,sd=sd,n=n,evidence_grade=grade,source_locator=loc,scope_status=scope,source_hash="LOCAL_BIND_REQUIRED",provenance_status="RECOVERY_NON_AUTHORITATIVE_UIDS",notes=note))

# Ye 2025 exact source-table means. Values are UTS,YS,EL where available.
ye={
("alpha+beta","700C/2h-AC"):{
"Matrix_0wtCr3C2":{25:(899,883,None),500:(875,677,34),600:(508,419,103.5),700:(181,146,173)},
"TMC1_3wtCr3C2":{25:(1000,986,None),500:(917,789,36.5),600:(536,464,75.5),700:(188,151,95)},
"TMC2_6wtCr3C2":{25:(974,962,None),500:(1025,892,25.5),600:(541,460,61),700:(192,166,116)}},
("beta","800C/2h-AC"):{
"Matrix_0wtCr3C2":{25:(831,824,None),500:(1020,538,42),600:(439,365,75.5),700:(168,168,157)},
"TMC1_3wtCr3C2":{25:(946,937,None),500:(1045,857,32),600:(513,419,63.5),700:(199,178,130)},
"TMC2_6wtCr3C2":{25:(985,975,None),500:(1081,912,20),600:(571,474,73),700:(216,178,140)}}}
for (state,ht),block in ye.items():
    for sample,temps in block.items():
        dose=0 if sample.startswith("Matrix") else 3 if "TMC1" in sample else 6; reinf="NONE" if dose==0 else "IN_SITU_TiC_FROM_Cr3C2"
        for temp,(uts,ys,el) in temps.items():
            for prop,val in (("UTS",uts),("YS",ys),("EL",el)):
                if val is None:continue
                note="Table 3.2 gives 168 MPa while nearby prose gives 169 MPa; table retained." if state=="beta" and sample.startswith("Matrix") and temp==700 and prop=="UTS" else ""
                add("YE2025",sample,"Ti-5Al-5Mo-5Zr-6Cr",reinf,dose,"wt.% Cr3C2 precursor","vacuum levitation melting + forging",ht,state,temp,prop,val,"MPa" if prop!="EL" else "%","DIRECT_TABLE_TEXT",f"Table {'3.1' if state=='alpha+beta' else '3.2'}",speed=1,hold=None if temp==25 else 15,scope="ADJACENT_700C_SENSITIVITY" if temp==700 else "IN_SCOPE",note=note)

# Qi 2012, 10 vol.% TiC/TA15, n=3; no unreinforced control.
qrt={"As-cast":{"UTS":(1048.3,4.6),"YS":(1023.1,6.2),"EL":(3.92,.56)},"HT1":{"UTS":(1119.7,7.3),"YS":(1045.8,4.5),"EL":(2.17,.31)},"HT2":{"UTS":(1130.6,5.1),"YS":(1056.5,4.7),"EL":(1.33,.20)},"HT3":{"UTS":(1159.4,3.3),"YS":(1076.6,5.5),"EL":(.65,.07)}}
qht={"As-cast":{600:{"UTS":(597.7,5.6),"EL":(5.53,1.34)},650:{"UTS":(494.8,6.2),"EL":(16.45,1.66)}},"HT1":{600:{"UTS":(652.5,7.7),"EL":(6.76,.82)},650:{"UTS":(505.6,2.4),"EL":(20.73,3.40)}},"HT2":{600:{"UTS":(687.7,2.6),"EL":(7.44,2.16)},650:{"UTS":(507.7,3.5),"EL":(19.89,2.57)}}}
for s,props in qrt.items():
    for prop,(v,sd) in props.items():add("QI2012",s,"TA15","TiC",10,"vol.% TiC","casting",s,s,25,prop,v,"MPa" if prop!="EL" else "%","DIRECT_TABLE_TEXT","primary tensile table",sd,3,.5)
for s,temps in qht.items():
    for t,props in temps.items():
        for prop,(v,sd) in props.items():add("QI2012",s,"TA15","TiC",10,"vol.% TiC","casting",s,s,t,prop,v,"MPa" if prop!="EL" else "%","DIRECT_TABLE_TEXT","primary high-temperature table/figure",sd,3,.5,scope="ADJACENT_650C_SENSITIVITY" if t==650 else "IN_SCOPE")

# Li 2023 exact Table 3 means.
li={"Ti6Al4V":{25:{"UTS":989.3,"EL":8.2},600:{"UTS":406.1,"EL":24.3}},"5wtB4C_TMC":{25:{"UTS":1126.1,"EL":4.2},600:{"UTS":506.4,"EL":14.1}}}
for s,temps in li.items():
    dose=0 if s=="Ti6Al4V" else 5; reinf="NONE" if dose==0 else "IN_SITU_TiB+TiC_FROM_B4C"
    for t,props in temps.items():
        for prop,v in props.items():add("LI2023",s,"Ti6Al4V",reinf,dose,"wt.% B4C feed","directed energy deposition","as-deposited","Widmanstatten/refined composite",t,prop,v,"MPa" if prop=="UTS" else "%","DIRECT_TABLE_TEXT","Table 3",speed=.5 if t==25 else 1)

# Qiu 2021 high-temperature adjacent/source anchors; no strict RT retention.
qiu=[("IMI834_matrix_derived","NONE",0,600,724.0506329,None,"DERIVED_CALCULATION","858/1.185"),("2.5volTiB","TiB",2.5,600,724,9,"DIRECT_TABLE_TEXT","600C anchor"),("2.5volTiC","TiC",2.5,600,858,19,"DIRECT_TABLE_TEXT","600C anchor"),("2.5volTiC","TiC",2.5,650,765,10,"DIRECT_TEXT_CONFLICT","Chinese/English summaries 765 vs 767"),("5volTiB+TiC","TiB+TiC",5,600,920,16,"DIRECT_TABLE_TEXT","600C anchor"),("5volTiB+TiC","TiB+TiC",5,650,747,12,"DIRECT_TABLE_TEXT","650C anchor")]
for s,r,d,t,v,sd,g,note in qiu:add("QIU2021",s,"IMI834",r,d,"vol.% reinforcement","casting + rolling","reported thesis condition","IMI834 alpha+beta/lamellar",t,"UTS",v,"MPa",g,"primary thesis result summary",sd=sd,scope="ADJACENT_650C_SENSITIVITY" if t==650 else "IN_SCOPE",note=note)
records.sort(key=lambda r:(r["paper_uid"],r["sample_label"],float(r["temperature_C"]),r["property"]))
wc(ROOT/"ANALYSIS_COHORT.csv",records)

# Index and strict same-paper controls.
idx={(r["paper_uid"],r["microstructure_state"],r["sample_label"],float(r["temperature_C"]),r["property"]):r for r in records}
pairs=[]
def pair(t,m):
    dy=float(t["value"])-float(m["value"]); lr=math.log(float(t["value"])/float(m["value"]))
    pairs.append(dict(pair_uid=uid("PAIR",t["record_uid"],m["record_uid"]),snapshot_id=SNAPSHOT,paper_uid=t["paper_uid"],tmc_record_uid=t["record_uid"],matrix_record_uid=m["record_uid"],tmc_sample_uid=t["sample_uid"],matrix_sample_uid=m["sample_uid"],tmc_condition_uid=t["condition_uid"],matrix_condition_uid=m["condition_uid"],matrix_family=t["matrix_family"],microstructure_state=t["microstructure_state"],reinforcement_type=t["reinforcement_type"],reinforcement_dose=t["reinforcement_dose"],dose_unit=t["dose_unit"],temperature_C=t["temperature_C"],property=t["property"],tmc_value=t["value"],matrix_value=m["value"],unit=t["unit"],delta_Y=dy,lnRR=lr,pct_change=100*(math.exp(lr)-1),match_grade="A",identification_level=2,evidence_grade=t["evidence_grade"],support_domain="same paper/matrix/process/heat treatment/test condition",notes=""))
for (state,ht),block in ye.items():
    for ts in ("TMC1_3wtCr3C2","TMC2_6wtCr3C2"):
        for temp,vals in block[ts].items():
            for prop,val in zip(("UTS","YS","EL"),vals):
                if val is not None:pair(idx[("YE2025",state,ts,float(temp),prop)],idx[("YE2025",state,"Matrix_0wtCr3C2",float(temp),prop)])
for t in (25.,600.):
    for prop in ("UTS","EL"):pair(idx[("LI2023","Widmanstatten/refined composite","5wtB4C_TMC",t,prop)],idx[("LI2023","Widmanstatten/refined composite","Ti6Al4V",t,prop)])
wc(ROOT/"PAIR_MATCHES.csv",pairs)

# Same-sample retention.
groups=defaultdict(list)
for r in records:groups[(r["paper_uid"],r["microstructure_state"],r["sample_label"],r["property"])].append(r)
ret=[]
for (paper,state,sample,prop),g in groups.items():
    rr=next((x for x in g if float(x["temperature_C"])==RT),None)
    if not rr:continue
    for h in g:
        if float(h["temperature_C"])==RT:continue
        R=float(h["value"])/float(rr["value"]);lo=hi=se=None
        if h.get("sd") not in (None,"") and rr.get("sd") not in (None,"") and h.get("n") and rr.get("n"):
            se=math.sqrt((float(h["sd"])/float(h["value"]))**2/int(h["n"])+(float(rr["sd"])/float(rr["value"]))**2/int(rr["n"]));lo=math.exp(math.log(R)-1.96*se);hi=math.exp(math.log(R)+1.96*se)
        ret.append(dict(retention_uid=uid("RET",h["record_uid"],rr["record_uid"]),snapshot_id=SNAPSHOT,paper_uid=paper,sample_uid=h["sample_uid"],condition_uid_HT=h["condition_uid"],condition_uid_RT=rr["condition_uid"],sample_label=sample,matrix_family=h["matrix_family"],microstructure_state=state,reinforcement_type=h["reinforcement_type"],reinforcement_dose=h["reinforcement_dose"],dose_unit=h["dose_unit"],temperature_C=h["temperature_C"],property=prop,Y_HT=h["value"],Y_RT=rr["value"],R_T=R,ln_R_T=math.log(R),CI95_low=lo,CI95_high=hi,SE_log_ratio=se,uncertainty_method="delta_method_log_ratio" if se is not None else "sampling_uncertainty_unavailable",evidence_grade=h["evidence_grade"],scope_status=h["scope_status"],support_domain="same sample/heat treatment/property; RT reference",claim_level=2,notes="EL ratios are denominator-sensitive; inspect absolute high-temperature EL." if prop=="EL" else ""))
ret.sort(key=lambda r:(r["paper_uid"],r["property"],r["sample_label"],float(r["temperature_C"])))
wc(ROOT/"MIDTEMP_RETENTION.csv",ret)
ri={(r["paper_uid"],r["microstructure_state"],r["sample_label"],float(r["temperature_C"]),r["property"]):r for r in ret}
dret=[]
for p in pairs:
    if float(p["temperature_C"])==RT:continue
    tr=next(r for r in records if r["record_uid"]==p["tmc_record_uid"]);mr=next(r for r in records if r["record_uid"]==p["matrix_record_uid"])
    kt=(p["paper_uid"],p["microstructure_state"],tr["sample_label"],float(p["temperature_C"]),p["property"]);km=(p["paper_uid"],p["microstructure_state"],mr["sample_label"],float(p["temperature_C"]),p["property"])
    if kt not in ri or km not in ri:continue
    a,b=ri[kt],ri[km];d=float(a["R_T"])-float(b["R_T"])
    dret.append(dict(effect_uid=uid("DRET",a["retention_uid"],b["retention_uid"]),snapshot_id=SNAPSHOT,paper_uid=p["paper_uid"],tmc_sample_uid=a["sample_uid"],matrix_sample_uid=b["sample_uid"],microstructure_state=p["microstructure_state"],matrix_family=p["matrix_family"],reinforcement_type=p["reinforcement_type"],reinforcement_dose=p["reinforcement_dose"],dose_unit=p["dose_unit"],temperature_C=p["temperature_C"],property=p["property"],R_T_TMC=a["R_T"],R_T_matrix=b["R_T"],delta_R_T=d,relative_retention_gain_pct_of_matrix_R=100*d/float(b["R_T"]),match_grade="A",evidence_grade=p["evidence_grade"],uncertainty_status="sampling_CI_unavailable" if a["CI95_low"] is None or b["CI95_low"] is None else "component_ratio_CIs_available",support_domain=p["support_domain"],claim_level=2,scope_status="ADJACENT_700C_SENSITIVITY" if float(p["temperature_C"])==700 else "IN_SCOPE",notes="Positive absolute high-temperature strength does not imply positive RT-referenced retention."))

effects=[]
for p in pairs:effects.append(dict(effect_uid=uid("EFF",p["pair_uid"]),snapshot_id=SNAPSHOT,estimand="DELTA_Y_AND_LNRR",paper_uid=p["paper_uid"],microstructure_state=p["microstructure_state"],matrix_family=p["matrix_family"],reinforcement_type=p["reinforcement_type"],reinforcement_dose=p["reinforcement_dose"],dose_unit=p["dose_unit"],temperature_C=p["temperature_C"],property=p["property"],estimate=p["delta_Y"],estimate_unit=p["unit"],lnRR=p["lnRR"],pct_change=p["pct_change"],CI95_low=None,CI95_high=None,prediction_interval_low=None,prediction_interval_high=None,uncertainty_status="replicate_variance_not_recovered",match_grade="A",independent_papers=1,claim_level=2,evidence_grade=p["evidence_grade"],support_domain=p["support_domain"],source_uids=p["tmc_record_uid"]+"|"+p["matrix_record_uid"],notes=""))
for d in dret:effects.append(dict(effect_uid=d["effect_uid"],snapshot_id=SNAPSHOT,estimand="DELTA_R_T",paper_uid=d["paper_uid"],microstructure_state=d["microstructure_state"],matrix_family=d["matrix_family"],reinforcement_type=d["reinforcement_type"],reinforcement_dose=d["reinforcement_dose"],dose_unit=d["dose_unit"],temperature_C=d["temperature_C"],property=d["property"],estimate=d["delta_R_T"],estimate_unit="ratio difference",lnRR=None,pct_change=d["relative_retention_gain_pct_of_matrix_R"],CI95_low=None,CI95_high=None,prediction_interval_low=None,prediction_interval_high=None,uncertainty_status=d["uncertainty_status"],match_grade="A",independent_papers=1,claim_level=2,evidence_grade=d["evidence_grade"],support_domain=d["support_domain"],source_uids=d["tmc_sample_uid"]+"|"+d["matrix_sample_uid"],notes=d["notes"]))
wc(ROOT/"EFFECT_ESTIMATES.csv",effects)

# Adjacent slopes.
slopes=[]
for key,g in groups.items():
    paper,state,sample,prop=key;g=sorted(g,key=lambda x:float(x["temperature_C"]));rr=next((x for x in g if float(x["temperature_C"])==RT),None)
    for a,b in zip(g,g[1:]):
        t1,t2=float(a["temperature_C"]),float(b["temperature_C"]);s=(float(b["value"])-float(a["value"]))/(t2-t1)
        slopes.append(dict(slope_uid=uid("SLOPE",a["record_uid"],b["record_uid"]),snapshot_id=SNAPSHOT,paper_uid=paper,sample_uid=a["sample_uid"],sample_label=sample,matrix_family=a["matrix_family"],microstructure_state=state,reinforcement_type=a["reinforcement_type"],temperature_start_C=t1,temperature_end_C=t2,property=prop,dY_dT=s,dY_dT_unit=f"{a['unit']}/C",dR_dT=s/float(rr["value"]) if rr else None,slope_method="adjacent_secant",uncertainty_status="not_estimable_from_single_mean_per_condition",scope_status="PRIMARY_400_600" if t2<=600 else "ADJACENT_SENSITIVITY",claim_level=1))
wc(ROOT/"TEMPERATURE_SLOPES.csv",slopes)

bps=[dict(breakpoint_uid=uid("BP","YE"),snapshot_id=SNAPSHOT,paper_uid="YE2025",property="UTS/YS",matrix_family="Ti-5556",reinforcement_type="TiC",breakpoint_central_C=550,interval_low_C=500,interval_high_C=600,method="largest adjacent slope-change interval across RT/500/600/700 grid",evidence_type="DIRECT_TABLE_GRID",independent_papers=1,status="INTERVAL_IDENTIFIED_NOT_POINT_IDENTIFIED",mechanistic_interpretation="matrix softening and rapid loss of particle/grain-strengthening leverage",claim_level=2),dict(breakpoint_uid=uid("BP","QI"),snapshot_id=SNAPSHOT,paper_uid="QI2012",property="UTS/EL",matrix_family="TA15",reinforcement_type="TiC",breakpoint_central_C=625,interval_low_C=600,interval_high_C=650,method="adjacent high-temperature grid",evidence_type="DIRECT_TABLE_GRID",independent_papers=1,status="ADJACENT_WINDOW_SENSITIVITY",mechanistic_interpretation="strength convergence while ductility rises",claim_level=1),dict(breakpoint_uid=uid("BP","QIU"),snapshot_id=SNAPSHOT,paper_uid="QIU2021",property="fracture mechanism",matrix_family="IMI834",reinforcement_type="TiB/TiC",breakpoint_central_C=625,interval_low_C=600,interval_high_C=650,method="source-reported fracture-mode transition",evidence_type="DIRECT_TEXT_MICROSTRUCTURE",independent_papers=1,status="MECHANISM_INTERVAL_ONLY",mechanistic_interpretation="particle fracture/load transfer transitions toward mixed debonding",claim_level=1)]
wc(ROOT/"MIDTEMP_BREAKPOINTS.csv",bps)

# Three-point Ye precursor dose response.
dose=[]
for (state,ht),block in ye.items():
    for temp in (25,500,600,700):
        common=set.intersection(*(set(k for k,v in zip(("UTS","YS","EL"),block[s][temp]) if v is not None) for s in block))
        for prop in sorted(common):
            pi=("UTS","YS","EL").index(prop);ys=[float(block[s][temp][pi]) for s in ("Matrix_0wtCr3C2","TMC1_3wtCr3C2","TMC2_6wtCr3C2")];s=(ys[2]-ys[0])/6;i=statistics.mean(ys)-3*s;pred=[i+s*x for x in (0,3,6)];sst=sum((y-statistics.mean(ys))**2 for y in ys);r2=1-sum((y-p)**2 for y,p in zip(ys,pred))/sst if sst else 1;qa=(ys[2]-2*ys[1]+ys[0])/18;qb=(ys[1]-ys[0]-9*qa)/3
            dose.append(dict(dose_response_uid=uid("DOSE",state,temp,prop),snapshot_id=SNAPSHOT,paper_uid="YE2025",matrix_family="Ti-5556",microstructure_state=state,temperature_C=temp,property=prop,dose_variable="Cr3C2 precursor",dose_unit="wt.%",dose_points="0|3|6",values="|".join(map(str,ys)),linear_slope_per_wt_pct=s,linear_intercept=i,linear_R2=r2,quadratic_a=qa,quadratic_b=qb,quadratic_c=ys[0],actual_reinforcement_efficiency_status="NOT_IDENTIFIABLE_ACTUAL_TiC_VOL_FRACTION_MISSING",model_status="DESCRIPTIVE_THREE_POINT_INTERPOLATION",claim_level=1,notes="Do not interpret precursor coefficient as intrinsic TiC coefficient."))
wc(ROOT/"DOSE_RESPONSE.csv",dose)

# Interactions.
di={(d["paper_uid"],d["microstructure_state"],float(d["reinforcement_dose"]),float(d["temperature_C"]),d["property"]):d for d in dret};inter=[]
for state in ("alpha+beta","beta"):
    for ds in (3.,6.):
        for prop in ("UTS","YS"):
            a=("YE2025",state,ds,500.,prop);b=("YE2025",state,ds,600.,prop)
            if a in di and b in di:inter.append(dict(interaction_uid=uid("INT",state,ds,prop),snapshot_id=SNAPSHOT,interaction="temperature_600_vs_500_x_reinforcement",paper_uid="YE2025",matrix_family="Ti-5556",microstructure_state=state,reinforcement_dose=ds,property=prop,estimate=float(di[b]["delta_R_T"])-float(di[a]["delta_R_T"]),estimate_definition="delta_R_T(600C)-delta_R_T(500C)",CI95_low=None,CI95_high=None,status="DESCRIPTIVE_WITHIN_PAPER_INTERACTION",claim_level=2))
for ds in (3.,6.):
    for temp in (500.,600.):
        for prop in ("UTS","YS"):
            a=("YE2025","alpha+beta",ds,temp,prop);b=("YE2025","beta",ds,temp,prop)
            if a in di and b in di:inter.append(dict(interaction_uid=uid("INT","state",ds,temp,prop),snapshot_id=SNAPSHOT,interaction="beta_vs_alpha+beta_x_reinforcement",paper_uid="YE2025",matrix_family="Ti-5556",microstructure_state="beta minus alpha+beta",reinforcement_dose=ds,property=prop,estimate=float(di[b]["delta_R_T"])-float(di[a]["delta_R_T"]),estimate_definition=f"delta_R_T(beta)-delta_R_T(alpha+beta) at {int(temp)}C",CI95_low=None,CI95_high=None,status="DESCRIPTIVE_WITHIN_PAPER_INTERACTION",claim_level=2))
wc(ROOT/"INTERACTION_EFFECTS.csv",inter)

# Pareto.
rm={(r["paper_uid"],r["sample_label"],float(r["temperature_C"]),r["property"]):r for r in ret};pareto=[]
for paper in ("QI2012","LI2023"):
    for s in sorted({r["sample_label"] for r in ret if r["paper_uid"]==paper}):
        for t in sorted({float(r["temperature_C"]) for r in ret if r["paper_uid"]==paper and r["sample_label"]==s}):
            ku=(paper,s,t,"UTS");ke=(paper,s,t,"EL")
            if ku in rm and ke in rm:
                u,e=rm[ku],rm[ke];pareto.append(dict(pareto_uid=uid("PAR",paper,s,t),snapshot_id=SNAPSHOT,paper_uid=paper,sample_label=s,matrix_family=u["matrix_family"],reinforcement_type=u["reinforcement_type"],temperature_C=t,UTS_retention=u["R_T"],EL_retention=e["R_T"],UTS_HT_MPa=u["Y_HT"],EL_HT_pct=e["Y_HT"],strict_scope="YES" if t<=600 else "ADJACENT_650C",pareto_status="PENDING",notes="EL retention can be inflated by low RT elongation; inspect EL_HT_pct."))
for r in pareto:r["pareto_status"]="DOMINATED" if any(float(o["temperature_C"])==float(r["temperature_C"]) and float(o["UTS_retention"])>=float(r["UTS_retention"]) and float(o["EL_retention"])>=float(r["EL_retention"]) and (float(o["UTS_retention"])>float(r["UTS_retention"]) or float(o["EL_retention"])>float(r["EL_retention"])) for o in pareto) else "PARETO_NONDOMINATED_WITHIN_TEMPERATURE"
wc(ROOT/"MIDTEMP_PARETO.csv",pareto)

# Paper-equal 600C UTS retention effect and honest non-identifiability.
p600=[d for d in dret if d["property"]=="UTS" and float(d["temperature_C"])==600 and d["scope_status"]=="IN_SCOPE"]
pm=defaultdict(list)
for d in p600:pm[d["paper_uid"]].append(float(d["delta_R_T"]))
pm={k:statistics.mean(v) for k,v in pm.items()};pmean=statistics.mean(pm.values());prange=(min(pm.values()),max(pm.values()))
hier=[dict(result_uid=uid("HIER","600UTS"),snapshot_id=SNAPSHOT,estimand="paper-equal mean delta_R_T at 600C, UTS",estimate=pmean,CI95_low=None,CI95_high=None,prediction_interval_low=prange[0],prediction_interval_high=prange[1],independent_papers=len(pm),paper_clusters="|".join(f"{k}:{v:.8f}" for k,v in sorted(pm.items())),model="descriptive paper-equal aggregation; random-effects model not fit",status="NOT_IDENTIFIABLE_FOR_POPULATION_GENERALIZATION",claim_level=2,notes="Range is descriptive support, not a 95% CI.")]
wc(ROOT/"HIERARCHICAL_RESULTS.csv",hier)
het=[]
for prop in ("UTS","YS","EL"):
    for t in (500.,600.):
        vals=[float(d["delta_R_T"]) for d in dret if d["property"]==prop and float(d["temperature_C"])==t];papers={d["paper_uid"] for d in dret if d["property"]==prop and float(d["temperature_C"])==t}
        if vals:het.append(dict(heterogeneity_uid=uid("HET",prop,t),snapshot_id=SNAPSHOT,estimand="delta_R_T",property=prop,temperature_C=t,effect_count=len(vals),independent_papers=len(papers),mean_effect_descriptive=statistics.mean(vals),min_effect=min(vals),max_effect=max(vals),sd_across_effects_descriptive=statistics.stdev(vals) if len(vals)>1 else None,tau2=None,I2_pct=None,status="TAU2_I2_NOT_IDENTIFIABLE",notes="Rows share papers/controls; raw effect SD is not a meta-analytic SE."))
wc(ROOT/"HETEROGENEITY.csv",het)
sens=[dict(analysis_id="LOPO_REMOVE_LI2023",snapshot_id=SNAPSHOT,estimand="600C UTS delta_R_T paper-equal mean",estimate=pm.get("YE2025"),reference_estimate=pmean,difference=pm.get("YE2025")-pmean,status="LOPO",interpretation="Ye-only mean is near zero; positive pooled direction is not robustly independent of Li2023."),dict(analysis_id="LOPO_REMOVE_YE2025",snapshot_id=SNAPSHOT,estimand="600C UTS delta_R_T paper-equal mean",estimate=pm.get("LI2023"),reference_estimate=pmean,difference=pm.get("LI2023")-pmean,status="LOPO",interpretation="One-paper Li estimate cannot establish universality."),dict(analysis_id="YE_BETA_700_TABLE_VS_PROSE",snapshot_id=SNAPSHOT,estimand="beta matrix UTS at 700C",estimate=168,reference_estimate=169,difference=-1,status="SOURCE_CONFLICT_SENSITIVITY",interpretation="Table retained; 400–600C results unaffected."),dict(analysis_id="EXCLUDE_650_700_ADJACENT",snapshot_id=SNAPSHOT,estimand="primary 400–600C scope",estimate=len([r for r in ret if float(r["temperature_C"])<=600]),reference_estimate=len(ret),difference=len([r for r in ret if float(r["temperature_C"])<=600])-len(ret),status="SCOPE_SENSITIVITY",interpretation="650/700C informs breakpoint/mechanism only."),dict(analysis_id="EL_RATIO_DENOMINATOR_WARNING",snapshot_id=SNAPSHOT,estimand="EL retention",estimate=None,reference_estimate=None,difference=None,status="ALTERNATIVE_DEFINITION_REQUIRED",interpretation="Always report absolute high-temperature EL beside the ratio.")]
wc(ROOT/"SENSITIVITY_ANALYSIS.csv",sens)
nulls=[("Universal reinforcement effect over 400–600C","NOT_IDENTIFIABLE","Only two independent papers provide strict matrix-controlled RT-referenced retention."),("Direct matched effects at 400C","NO_DATA","No exact 400C matched tensile table recovered."),("Direct matched effects at 550C","NO_DATA","No exact 550C matched tensile table recovered."),("Random-effects tau2/I2","NOT_IDENTIFIABLE","Within-study variance and >=3 independent controlled papers are absent."),("YS retention outside Ye2025","NOT_IDENTIFIABLE","No second independent controlled high-temperature YS source."),("Ye2025 EL retention","NOT_IDENTIFIABLE","Exact RT elongation values are not tabulated in recovered pages."),("Long-term 600C service reliability","NOT_IDENTIFIABLE","Immediate tensile does not establish creep/oxidation/fatigue life."),("Per-vol.% efficiency in Ye2025","NOT_IDENTIFIABLE","Actual TiC volume fraction missing."),("Sharp universal breakpoint","NOT_IDENTIFIABLE","Sparse grids only interval-identify 500–600C transition."),("Positive UTS retention for every TMC","REFUTED","Several Ye ΔR_T values are negative despite positive absolute high-temperature increments.")]
wc(ROOT/"NULL_NEGATIVE_RESULTS.csv",[dict(result_uid=uid("NULL",q),snapshot_id=SNAPSHOT,question=q,status=s,reason=r,claim_level=0 if s in ("NO_DATA","NOT_IDENTIFIABLE") else 2) for q,s,r in nulls])
conf=[dict(conflict_uid=uid("CON","YE700"),snapshot_id=SNAPSHOT,paper_uid="YE2025",field="beta matrix UTS at 700C",value_a="168 MPa",source_a="Table 3.2",value_b="169 MPa",source_b="nearby prose",resolution="retain table 168",severity="LOW_OUTSIDE_PRIMARY_SCOPE",status="RESOLVED_WITH_RULE",notes=""),dict(conflict_uid=uid("CON","QIU650"),snapshot_id=SNAPSHOT,paper_uid="QIU2021",field="2.5vol% TiC/IMI834 UTS 650C",value_a="765±10",source_a="Chinese summary",value_b="767±10",source_b="English summary",resolution="exclude from strict primary; local table arbitration",severity="MEDIUM",status="OPEN_REQUIRES_TABLE_XPATH",notes=""),dict(conflict_uid=uid("CON","V29"),snapshot_id=SNAPSHOT,paper_uid="ALL",field="authoritative snapshot/sample/condition identity",value_a=SNAPSHOT,source_a="web recovery",value_b="V29 canonical IDs unavailable",source_b="required frozen snapshot",resolution="do not promote; request local binding",severity="HIGH_GOVERNANCE",status="OPEN",notes=""),dict(conflict_uid=uid("CON","YEEL"),snapshot_id=SNAPSHOT,paper_uid="YE2025",field="RT elongation",value_a="qualitative only",source_a="prose",value_b="exact values absent",source_b="recovered tables",resolution="do not compute Ye EL retention",severity="HIGH_FOR_EL",status="OPEN",notes=""),dict(conflict_uid=uid("CON","RATE"),snapshot_id=SNAPSHOT,paper_uid="YE2025|QI2012|LI2023",field="strain rate",value_a="crosshead speed",source_a="methods",value_b="s^-1 unavailable",source_b="missing conversion details",resolution="do not fabricate",severity="MEDIUM",status="OPEN",notes="")]
wc(ROOT/"CONFLICT_LEDGER.csv",conf)

# Creep claim boundary only.
creep=[dict(paper_uid="WANG2017",temperature_C=600,stress_MPa=200,material="Ti6Al4V",reinforcement_vol_pct=0,steady_creep_rate_s_1=6.08e-6,use="claim ceiling only"),dict(paper_uid="WANG2017",temperature_C=600,stress_MPa=200,material="network TMC",reinforcement_vol_pct=3,steady_creep_rate_s_1=1.85e-6,use="claim ceiling only"),dict(paper_uid="WANG2017",temperature_C=600,stress_MPa=200,material="network TMC",reinforcement_vol_pct=5,steady_creep_rate_s_1=1.09e-6,use="claim ceiling only"),dict(paper_uid="WANG2017",temperature_C=600,stress_MPa=200,material="network TMC",reinforcement_vol_pct=8,steady_creep_rate_s_1=7.28e-7,use="claim ceiling only")]
wc(ROOT/"SERVICE_RELIABILITY_BOUNDARY.csv",creep)

# Provenance JSONL.
with (ROOT/"PROVENANCE.jsonl").open("w",encoding="utf-8") as fh:
    for r in records:fh.write(json.dumps({"object_type":"ATOMIC_RECORD","object_uid":r["record_uid"],"snapshot_id":SNAPSHOT,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"source_title":r["source_title"],"doi":r["doi"],"source_locator":r["source_locator"],"source_hash":None,"source_hash_missing_reason":"canonical package/member hash not exposed to web return","evidence_grade":r["evidence_grade"],"provenance_status":r["provenance_status"]},ensure_ascii=False,sort_keys=True)+"\n")
    for e in effects:fh.write(json.dumps({"object_type":"EFFECT_ESTIMATE","object_uid":e["effect_uid"],"snapshot_id":SNAPSHOT,"paper_uid":e["paper_uid"],"source_uids":e["source_uids"],"estimand":e["estimand"],"claim_level":e["claim_level"],"provenance_status":"DERIVED_FROM_RECOVERY_ATOMIC_RECORDS"},ensure_ascii=False,sort_keys=True)+"\n")

# Figures and their data.
f1=[r for r in ret if r["property"]=="UTS" and float(r["temperature_C"])<=650];wc(FD/"F1_retention_temperature_UTS.csv",f1)
pg=defaultdict(list)
for r in f1:pg[(r["paper_uid"],r["microstructure_state"],r["sample_label"])].append(r)
plt.figure(figsize=(9,6))
for k,g in sorted(pg.items()):
    g=sorted(g,key=lambda x:float(x["temperature_C"]));plt.plot([25]+[float(x["temperature_C"]) for x in g],[1]+[float(x["R_T"]) for x in g],marker="o",linewidth=1.2,markersize=3.5,label=" | ".join(k))
plt.axhline(1,linewidth=.8,linestyle="--");plt.xlabel("Temperature (°C)");plt.ylabel("UTS retention, R_T");plt.title("UTS retention versus temperature\n4 independent tensile sources; direct means");plt.grid(True,linewidth=.4,alpha=.4);plt.legend(fontsize=6.2,bbox_to_anchor=(1.02,1),loc="upper left");plt.tight_layout()
for e in ("png","svg","pdf"):plt.savefig(FIG/f"F1_retention_temperature_UTS.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")
plt.close()
f1b=[r for r in ret if r["property"]=="YS" and r["paper_uid"]=="YE2025" and float(r["temperature_C"])<=600];wc(FD/"F1b_retention_temperature_YS.csv",f1b);pg=defaultdict(list)
for r in f1b:pg[(r["microstructure_state"],r["sample_label"])].append(r)
plt.figure(figsize=(8,5.5))
for k,g in sorted(pg.items()):g=sorted(g,key=lambda x:float(x["temperature_C"]));plt.plot([25]+[float(x["temperature_C"]) for x in g],[1]+[float(x["R_T"]) for x in g],marker="o",label=" | ".join(k))
plt.axhline(1,linewidth=.8,linestyle="--");plt.xlabel("Temperature (°C)");plt.ylabel("YS retention, R_T");plt.title("YS retention in TiC/Ti-5556\n1 independent paper");plt.grid(True,linewidth=.4,alpha=.4);plt.legend(fontsize=7,bbox_to_anchor=(1.02,1),loc="upper left");plt.tight_layout()
for e in ("png","svg","pdf"):plt.savefig(FIG/f"F1b_retention_temperature_YS.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")
plt.close()
f2=[dict(label=f"{d['paper_uid']} | {d['microstructure_state']} | {d['reinforcement_type']} {d['reinforcement_dose']}",paper_uid=d["paper_uid"],delta_R_T=d["delta_R_T"],CI95_low="",CI95_high="",uncertainty="sampling CI unavailable",evidence_grade=d["evidence_grade"]) for d in p600];f2.append(dict(label="Paper-equal descriptive mean",paper_uid="2 independent papers",delta_R_T=pmean,CI95_low=prange[0],CI95_high=prange[1],uncertainty="descriptive paper-support range, not 95% CI",evidence_grade="DIRECT_TABLE_TEXT"));wc(FD/"F2_delta_retention_forest.csv",f2)
plt.figure(figsize=(9,5.5))
for i,r in enumerate(f2):
    x=float(r["delta_R_T"])
    if r["CI95_low"]!="":lo,hi=float(r["CI95_low"]),float(r["CI95_high"]);plt.errorbar(x,i,xerr=[[x-lo],[hi-x]],fmt="o",capsize=3)
    else:plt.plot(x,i,"o")
plt.axvline(0,linewidth=.9,linestyle="--");plt.yticks(range(len(f2)),[r["label"] for r in f2],fontsize=7.2);plt.xlabel("Δ retention at 600°C, R_TMC − R_matrix");plt.title("600°C UTS retention effects\n2 independent papers; sampling CIs unavailable");plt.grid(True,axis="x",linewidth=.4,alpha=.4);plt.tight_layout()
for e in ("png","svg","pdf"):plt.savefig(FIG/f"F2_delta_retention_forest.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")
plt.close();wc(FD/"F3_breakpoint_intervals.csv",bps);plt.figure(figsize=(8.5,4.5))
for i,b in enumerate(bps):c=float(b["breakpoint_central_C"]);lo=float(b["interval_low_C"]);hi=float(b["interval_high_C"]);plt.errorbar(c,i,xerr=[[c-lo],[hi-c]],fmt="o",capsize=5)
plt.yticks(range(len(bps)),[f"{b['paper_uid']} | {b['property']}" for b in bps]);plt.xlabel("Transition temperature interval (°C)");plt.title("Temperature-transition intervals\nIntervals, not universal point estimates");plt.xlim(450,700);plt.grid(True,axis="x",linewidth=.4,alpha=.4);plt.tight_layout()
for e in ("png","svg","pdf"):plt.savefig(FIG/f"F3_breakpoint_intervals.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")
plt.close();f4=[r for r in pareto if float(r["temperature_C"])<=600];wc(FD/"F4_strength_ductility_pareto.csv",f4);plt.figure(figsize=(8.5,5.8))
for r in f4:
    x,y=float(r["UTS_retention"]),float(r["EL_retention"]);plt.scatter(x,y,marker="o" if r["pareto_status"].startswith("PARETO") else "x",s=45);plt.annotate(f"{r['paper_uid']}:{r['sample_label']}",(x,y),fontsize=7,xytext=(4,4),textcoords="offset points")
plt.xlabel("UTS retention at 600°C");plt.ylabel("Elongation retention at 600°C");plt.title("Strength–ductility retention Pareto\n2 independent papers; absolute EL retained in data");plt.grid(True,linewidth=.4,alpha=.4);plt.tight_layout()
for e in ("png","svg","pdf"):plt.savefig(FIG/f"F4_strength_ductility_pareto.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")
plt.close()

common='''from pathlib import Path\nimport csv\nimport matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nROOT=Path(__file__).resolve().parent.parent;FD=ROOT/"figure_data";FIG=ROOT/"figures"\ndef read(n):\n with (FD/n).open(encoding="utf-8-sig") as f:return list(csv.DictReader(f))\n'''
wt(PC/"plot_F1_retention_temperature_UTS.py",common+'''from collections import defaultdict\nr=read("F1_retention_temperature_UTS.csv");g=defaultdict(list)\nfor x in r:g[(x["paper_uid"],x["microstructure_state"],x["sample_label"])].append(x)\nplt.figure(figsize=(9,6))\nfor k,v in sorted(g.items()):v=sorted(v,key=lambda x:float(x["temperature_C"]));plt.plot([25]+[float(x["temperature_C"]) for x in v],[1]+[float(x["R_T"]) for x in v],marker="o",label=" | ".join(k))\nplt.xlabel("Temperature (°C)");plt.ylabel("UTS retention, R_T");plt.legend(fontsize=6,bbox_to_anchor=(1.02,1),loc="upper left");plt.tight_layout()\nfor e in ("png","svg","pdf"):plt.savefig(FIG/f"F1_retention_temperature_UTS.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")''')
wt(PC/"plot_F1b_retention_temperature_YS.py",common+'''from collections import defaultdict\nr=read("F1b_retention_temperature_YS.csv");g=defaultdict(list)\nfor x in r:g[(x["microstructure_state"],x["sample_label"])].append(x)\nplt.figure(figsize=(8,5.5))\nfor k,v in sorted(g.items()):v=sorted(v,key=lambda x:float(x["temperature_C"]));plt.plot([25]+[float(x["temperature_C"]) for x in v],[1]+[float(x["R_T"]) for x in v],marker="o",label=" | ".join(k))\nplt.xlabel("Temperature (°C)");plt.ylabel("YS retention, R_T");plt.legend(fontsize=7,bbox_to_anchor=(1.02,1),loc="upper left");plt.tight_layout()\nfor e in ("png","svg","pdf"):plt.savefig(FIG/f"F1b_retention_temperature_YS.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")''')
wt(PC/"plot_F2_delta_retention_forest.py",common+'''r=read("F2_delta_retention_forest.csv");plt.figure(figsize=(9,5.5))\nfor i,x in enumerate(r):\n v=float(x["delta_R_T"]);plt.plot(v,i,"o") if not x["CI95_low"] else plt.errorbar(v,i,xerr=[[v-float(x["CI95_low"])],[float(x["CI95_high"])-v]],fmt="o")\nplt.axvline(0,linestyle="--");plt.yticks(range(len(r)),[x["label"] for x in r]);plt.tight_layout()\nfor e in ("png","svg","pdf"):plt.savefig(FIG/f"F2_delta_retention_forest.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")''')
wt(PC/"plot_F3_breakpoint_intervals.py",common+'''r=read("F3_breakpoint_intervals.csv");plt.figure(figsize=(8.5,4.5))\nfor i,x in enumerate(r):c=float(x["breakpoint_central_C"]);lo=float(x["interval_low_C"]);hi=float(x["interval_high_C"]);plt.errorbar(c,i,xerr=[[c-lo],[hi-c]],fmt="o")\nplt.yticks(range(len(r)),[f"{x['paper_uid']} | {x['property']}" for x in r]);plt.tight_layout()\nfor e in ("png","svg","pdf"):plt.savefig(FIG/f"F3_breakpoint_intervals.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")''')
wt(PC/"plot_F4_strength_ductility_pareto.py",common+'''r=read("F4_strength_ductility_pareto.csv");plt.figure(figsize=(8.5,5.8))\nfor x in r:\n a,b=float(x["UTS_retention"]),float(x["EL_retention"]);plt.scatter(a,b);plt.annotate(f"{x['paper_uid']}:{x['sample_label']}",(a,b),fontsize=7)\nplt.xlabel("UTS retention at 600°C");plt.ylabel("Elongation retention at 600°C");plt.tight_layout()\nfor e in ("png","svg","pdf"):plt.savefig(FIG/f"F4_strength_ductility_pareto.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")''')

# Core recompute test.
wt(AC/"recompute_qm11.py",'''#!/usr/bin/env python3\nfrom pathlib import Path\nimport csv,math\nr=Path(__file__).resolve().parent.parent\ndef read(n):\n with (r/n).open(encoding="utf-8-sig") as f:return list(csv.DictReader(f))\nret=read("MIDTEMP_RETENTION.csv")\nfor x in ret:assert math.isclose(float(x["R_T"]),float(x["Y_HT"])/float(x["Y_RT"]),rel_tol=1e-9)\np=read("PAIR_MATCHES.csv")\nfor x in p:assert math.isclose(float(x["delta_Y"]),float(x["tmc_value"])-float(x["matrix_value"]),rel_tol=1e-9)\nprint({"pass":True,"retention_rows":len(ret),"pair_rows":len(p)})''')

# Narratives.
lo=min(float(d["delta_R_T"]) for d in p600);hi=max(float(d["delta_R_T"]) for d in p600)
get=lambda st,ds,t,pr:float(di[("YE2025",st,ds,float(t),pr)]["delta_R_T"])
wt(ROOT/"00_EXECUTIVE_VERDICT.md",f'''# QM11 Executive Verdict — 400–600 °C strength retention

## Quantitative answer

Reinforcement raises absolute high-temperature strength, but it does not create a universal improvement in room-temperature-referenced strength retention. Strict controlled retention evidence comes from two independent papers: Ye 2025 and Li 2023.

At 500 °C, Ye's TiC additions most clearly improve YS retention: ΔR_T spans {min(get(s,d,500,"YS") for s in ("alpha+beta","beta") for d in (3.,6.)):.3f} to {max(get(s,d,500,"YS") for s in ("alpha+beta","beta") for d in (3.,6.)):.3f}. UTS retention is mixed despite higher absolute UTS in every TMC.

At 600 °C, controlled UTS ΔR_T ranges from {lo:.3f} to {hi:.3f}. The paper-equal descriptive mean is {pmean:.3f}, with paper-support range [{prange[0]:.3f}, {prange[1]:.3f}]. This is not a meta-analytic confidence interval because only two independent papers and incomplete replicate variances are available.

The defensible temperature transition is an interval, [500,600] °C, not a sharp universal point. Adjacent 600–650 °C evidence supports convergence of strength differences and a mechanism shift toward matrix recovery/interface debonding.

## Strength–ductility price

- Li at 600 °C: +100.3 MPa UTS and −10.2 percentage points EL.
- Ye alpha+beta TMC2 at 600 °C: +33 MPa UTS, +41 MPa YS and −42.5 points EL.
- Ye beta TMC2 at 600 °C: +132 MPa UTS, +109 MPa YS and −2.5 points EL; best same-paper 600 °C balance in the recovered cohort.

## Mechanism and claim ceiling

Around 500 °C, load transfer, grain refinement, thermal-mismatch dislocations and matrix strengthening remain effective. Between 500 and 600 °C, matrix softening, dislocation climb/dynamic recovery and weakened interface constraint erode the relative-retention benefit. Immediate tensile retention is not long-term service reliability; creep, oxidation, fatigue and exposure-duration evidence must remain separate.

Maximum claim level: 2 — same-paper paired association. No Gold promotion, production-model registration or VALIDATED composition is asserted. Status remains CONTINUE_DATA_GAP pending canonical V29 hash/UID binding and data completion.''')
wt(ROOT/"METHODS.md",'''# Methods

Atomic row = paper × sample × composition/reinforcement × process × heat treatment × microstructure × tensile mode × temperature × property. Compression, flow stress and creep are excluded from tensile estimands. Creep is retained only as a service-claim boundary.

Estimands: ΔY=Y_TMC−Y_matrix; lnRR=ln(Y_TMC/Y_matrix); R_T=Y_T/Y_RT; ΔR_T=R_T,TMC−R_T,matrix; adjacent dY/dT. Grade A requires same paper, matrix, process, heat treatment, test temperature and property.

Qi ratio intervals use the log-ratio delta method from reported mean±SD, n=3. Ye/Li sampling intervals are not fabricated because condition-level SD/n were not recovered. A paper-equal 600 °C UTS ΔR_T mean and descriptive range are reported; tau²/I² and a population random-effects model are NOT_IDENTIFIABLE.

The primary breakpoint is interval-identified [500,600] °C from the sparse grid. Dose response in Ye is a three-point fit to Cr3C2 precursor wt.%, not measured TiC vol.%. Pareto analysis reports absolute high-temperature EL beside EL retention to avoid denominator deception.

No p-value fishing, SHAP/PDP causal claims or production ML is used. Run analysis_code/recompute_qm11.py and all plot_code scripts for replay.''')
wt(ROOT/"LIMITATIONS.md",'''# Limitations

1. Only two independent papers provide strict matrix-controlled RT-referenced retention.
2. Exact matched 400 and 550 °C tensile tables were not recovered.
3. Ye/Li condition-level variance and raw curves are missing; sampling and prediction intervals cannot be fabricated.
4. Crosshead speed is reported, but consistent engineering strain rate in s^-1 is unavailable.
5. Ye exact RT elongations are missing, blocking its EL retention.
6. Matrix/process/morphology heterogeneity blocks a universal reinforcement coefficient.
7. Ye dose is Cr3C2 precursor wt.%, not actual TiC vol.%.
8. EL ratios are denominator-sensitive; absolute high-temperature EL is mandatory.
9. Immediate tensile tests cannot establish creep, oxidation, fatigue or component reliability.
10. Recovery UIDs are not authoritative V29 identities; local package SHA/member CRC/XPath binding is required.
11. Qiu 650 °C value conflicts at 765 versus 767 MPa and is excluded from strict synthesis.
12. Archive registration is role-based and ledger-backed; this package does not falsely claim fresh deep parsing of every broad-corpus member.''')
wj(ROOT/"PLOT_SPECS.json",{"window_id":"QM11","language":"English","formats":["SVG","PDF","PNG_600_DPI"],"plots":[{"id":"F1","estimand":"UTS R_T","data":"figure_data/F1_retention_temperature_UTS.csv","code":"plot_code/plot_F1_retention_temperature_UTS.py"},{"id":"F1b","estimand":"YS R_T","data":"figure_data/F1b_retention_temperature_YS.csv","code":"plot_code/plot_F1b_retention_temperature_YS.py"},{"id":"F2","estimand":"600C UTS delta_R_T","data":"figure_data/F2_delta_retention_forest.csv","code":"plot_code/plot_F2_delta_retention_forest.py"},{"id":"F3","estimand":"transition interval","data":"figure_data/F3_breakpoint_intervals.csv","code":"plot_code/plot_F3_breakpoint_intervals.py"},{"id":"F4","estimand":"UTS/EL retention Pareto","data":"figure_data/F4_strength_ductility_pareto.csv","code":"plot_code/plot_F4_strength_ductility_pareto.py"}]})
req={"window_id":"QM11","snapshot_id":SNAPSHOT,"status":"CONTINUE_DATA_GAP","requests":[{"priority":1,"request":"Provide authoritative V29 ATOMIC_RECORDS, PROVENANCE, conflicts/exclusions, registry and exact snapshot hash.","acceptance":"Every row binds snapshot/source/paper/sample/condition IDs."},{"priority":1,"request":"Bind Ye/Qi/Li/Qiu values to package SHA, member path, CRC32, page/table/XPath or text hash.","acceptance":"High-impact values replay to original evidence."},{"priority":1,"request":"Recover replicate-level data/n/SD/raw curves and exact strain rate for Ye/Li.","acceptance":"Cluster-aware CIs and prediction intervals become estimable."},{"priority":2,"request":"Recover exact Ye RT elongation and scatter.","acceptance":"Ye EL retention becomes calculable."},{"priority":2,"request":"Add matched 400 and 550 °C controls plus exposure metadata.","acceptance":"Breakpoint is identified on a denser grid."},{"priority":2,"request":"Add matched long-duration 500–600 °C exposure, creep, oxidation and fatigue evidence.","acceptance":"Service reliability is analyzed separately."},{"priority":3,"request":"Resolve Qiu 765 versus 767 MPa from original table/figure.","acceptance":"Conflict closes by source arbitration."}]};wj(ROOT/"WEB_TO_LOCAL_REQUEST.json",req)
wt(ROOT/"LOCAL_ABSORPTION_PROMPT.md",f'''# Local absorption prompt — QM11

Verify checksums and schemas; bind recovery snapshot {SNAPSHOT} to canonical V29 only after row-level source replay. Preserve a recovery-to-canonical UID crosswalk. Attach package SHA, member path, CRC32 and page/table/XPath or text hashes. Re-run analysis_code/recompute_qm11.py and every plot script. Merge conflicts explicitly; never overwrite V29 silently. Keep claim ceiling at level 2 and do not promote Gold, a universal benefit, sharp breakpoint, VALIDATED recipe or production model. Execute WEB_TO_LOCAL_REQUEST.json before rerunning hierarchical uncertainty.''')
status={"window_id":"QM11","snapshot_id":SNAPSHOT,"papers_seen":5,"papers_included":4,"independent_papers":4,"independent_papers_strict_controlled_retention":len(pm),"atomic_rows":len(records),"matched_pairs":len(pairs),"effect_estimates":len(effects),"retention_estimates":len(ret),"controlled_delta_retention_estimates":len(dret),"plots_generated":5,"plot_files_generated":15,"open_conflicts":sum(c["status"].startswith("OPEN") for c in conf),"claim_level_max":2,"production_model_registration":"FORBIDDEN_NOT_PERFORMED","gold_promotion":"FORBIDDEN_NOT_PERFORMED","status":"CONTINUE_DATA_GAP","next_action":"local hash/UID binding, replicate uncertainty, 400/550C matched completion and long-term 600C evidence"};wj(ROOT/"WINDOW_STATUS.json",status)
wt(ROOT/"ACCEPTANCE_COMMANDS.md",'''# Acceptance commands

python analysis_code/recompute_qm11.py
python plot_code/plot_F1_retention_temperature_UTS.py
python plot_code/plot_F1b_retention_temperature_YS.py
python plot_code/plot_F2_delta_retention_forest.py
python plot_code/plot_F3_breakpoint_intervals.py
python plot_code/plot_F4_strength_ductility_pareto.py
sha256sum -c CHECKSUMS.sha256''')

# Required empty-schema-safe file already covered; finalize manifest and checksums.
required=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MIDTEMP_RETENTION.csv","TEMPERATURE_SLOPES.csv","MIDTEMP_BREAKPOINTS.csv","MIDTEMP_PARETO.csv"]
assert not [x for x in required if not (ROOT/x).is_file()]
assert not list(ROOT.rglob("*.zip"))
for stem in ("F1_retention_temperature_UTS","F1b_retention_temperature_YS","F2_delta_retention_forest","F3_breakpoint_intervals","F4_strength_ductility_pareto"):
    for ext in ("png","svg","pdf"):assert (FIG/f"{stem}.{ext}").stat().st_size>0
wj(ROOT/"VALIDATION_REPORT.json",{"pass":True,"required_missing":[],"atomic_rows":len(records),"matched_pairs":len(pairs),"effects":len(effects),"retention_rows":len(ret),"figures":15,"figure_data":5,"plot_code":5,"nested_zip_count":0,"status":"CONTINUE_DATA_GAP"})
entries=[]
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.name not in ("MANIFEST.json","CHECKSUMS.sha256"):
        role="figure" if p.parent==FIG else "figure_data" if p.parent==FD else "plot_code" if p.parent==PC else "analysis_code" if p.parent==AC else "root_deliverable";entries.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"role":role})
wj(ROOT/"MANIFEST.json",{"window_id":"QM11","snapshot_id":SNAPSHOT,"generated_by":"qm11_web_return/build_qm11.py","file_count_excluding_manifest_and_checksum":len(entries),"entries":entries,"nested_zip_count":0,"authority_status":"RECOVERY_READ_ONLY_NOT_GOLD"})
lines=[]
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.name!="CHECKSUMS.sha256":lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}")
wt(ROOT/"CHECKSUMS.sha256","\n".join(lines))
print(json.dumps(status,ensure_ascii=False,indent=2,sort_keys=True))
