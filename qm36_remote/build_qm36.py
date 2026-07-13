from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WINDOW = "QM36"
BASE = Path(__file__).resolve().parent
ROOT = BASE / "output" / "FINAL_QM36"
STATUS = "STATUS: CONTINUE_DATA_GAP | WINDOW=QM36 | MISSING=authoritative_V29_row_mapping_and_exact_offsite_EL_for_selected_synergy_samples | NEXT=local_absorb_and_recompute"


def uid(prefix: str, *parts: object) -> str:
    return prefix + "_" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:20]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def text(rel: str, value: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(value, encoding="utf-8", newline="\n")


def jwrite(rel: str, value: object) -> None:
    text(rel, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def cwrite(rel: str, rows: list[dict], fields: list[str]) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: "" if row.get(k) is None else row.get(k) for k in fields})


def finite(x: object) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


ARCHIVES = [
("00_统一上传总控与校验信息_20260712.zip","0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f",25479,13),
("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1",510259317,32),
("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9",515903028,15),
("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip","5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59",515906034,25),
("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip","cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a",515901682,7),
("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip","97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809",515901786,7),
("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip","16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f",515902128,9),
("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip","04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9",515903238,11),
("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip","5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728",515905052,17),
("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip","e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847",515913392,38),
("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip","36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485",515924832,69),
("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip","9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd",515989228,246),
("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip","c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c",506137803,57191),
("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip","a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a",515999572,244),
("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip","bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43",516062924,396),
("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip","08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755",516106394,499),
("TITMC_V27_LIT_WEB_P001_OF_010.zip","42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0",499460308,15),
("TITMC_V27_LIT_WEB_P002_OF_010.zip","05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193",490572377,154),
("TITMC_V27_LIT_WEB_P003_OF_010.zip","535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917",490379244,4610),
("TITMC_V27_LIT_WEB_P004_OF_010.zip","bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a",490620829,7747),
("TITMC_V27_LIT_WEB_P005_OF_010.zip","1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1",490762545,10068),
("TITMC_V27_LIT_WEB_P006_OF_010.zip","5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13",490902802,11778),
("TITMC_V27_LIT_WEB_P007_OF_010.zip","4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1",491018449,13499),
("TITMC_V27_LIT_WEB_P008_OF_010.zip","478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341",491203652,15702),
("TITMC_V27_LIT_WEB_P009_OF_010.zip","b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a",491501617,20036),
("TITMC_V27_LIT_WEB_P010_OF_010.zip","faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d",367381900,57717),
]

PAPERS = {
"JIAO":{"paper_uid":"PAPER_JIAO2019_POWTECH","doi":"10.1016/j.powtec.2019.09.008","locator":"file_library:turn34file0","hash":sha_bytes(b"turn34file0|JIAO")},
"LIU":{"paper_uid":"PAPER_LIU2023_CPB_111008","doi":"10.1016/j.compositesb.2023.111008","locator":"file_library:turn30file0","hash":"d2e138ab69d0c0e4b7c55143903338b6eae49a515a05435234238ea460073393"},
"BHUIYAN":{"paper_uid":"PAPER_BHUIYAN2017_JMR","doi":"10.1557/jmr.2017.345","locator":"file_library:turn35file14","hash":sha_bytes(b"turn35file14|BHUIYAN")},
"WANG":{"paper_uid":"PAPER_WANG2025_OLT_111836","doi":"10.1016/j.optlastec.2024.111836","locator":"file_library:turn32file0","hash":sha_bytes(b"turn32file0|WANG")},
"TA15":{"paper_uid":"PAPER_TA15_TIC_MSEA553_2012","doi":"UNRESOLVED_MSEA553_2012_59_66","locator":"file_library:turn7file14","hash":sha_bytes(b"turn7file14|TA15")},
}


def build() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for d in ["figure_data","plot_code","figures","tests"]:
        (ROOT/d).mkdir(parents=True, exist_ok=True)
    snapshot = "QM36_DERIVED_" + sha_bytes(json.dumps({"archives":[x[1] for x in ARCHIVES],"papers":PAPERS},sort_keys=True).encode())[:20]

    ledger=[]
    for i,(name,h,size,members) in enumerate(ARCHIVES):
        ledger.append({"index":i,"input_id":uid("INPUT",name),"snapshot_id":snapshot,"source_name":name,"source_type":"ZIP","path_or_locator":"/mnt/data/"+name,"source_hash":h,"source_hash_kind":"UPSTREAM_FULL_OR_CENTRAL_DIRECTORY_SHA256","bytes":size,"members":members,"priority":"P0_ORIGINAL" if name.startswith("TITMC") else "P1_P3_INFRASTRUCTURE","role":"original literature/XML corpus" if name.startswith("TITMC") else "frozen data/harness/code/control","consumption_state":"HASH_REGISTERED_AND_SCOPE_FILTERED","verification_state":"UPSTREAM_AUDIT_RECORDED_REMOTE_BUILDER_NO_REMOUNT"})
    for key,p in PAPERS.items():
        ledger.append({"index":len(ledger),"input_id":uid("INPUT",key),"snapshot_id":snapshot,"source_name":key,"source_type":"ORIGINAL_PAPER","path_or_locator":p["locator"],"source_hash":p["hash"],"source_hash_kind":"ORIGINAL_PDF_SHA256" if key=="LIU" else "LOCATOR_BINDING_SHA256_NOT_ORIGINAL_BYTE_HASH","bytes":"","members":"","priority":"P0_ORIGINAL","role":"condition-bound quantitative/mechanism evidence","consumption_state":"CONSUMED","verification_state":"DIRECT_FULL_TEXT"})
    ledger.append({"index":len(ledger),"input_id":uid("INPUT","QM36_MDU"),"snapshot_id":snapshot,"source_name":"QM36_塑性损失、损伤起始、裂纹路径和断裂模式预算.md","source_type":"MDU","path_or_locator":"/mnt/data/QM36_塑性损失、损伤起始、裂纹路径和断裂模式预算.md","source_hash":sha_bytes(b"QM36_MDU_20260713"),"source_hash_kind":"DISPATCH_LOCATOR_SHA256","bytes":"","members":"","priority":"P0_CONTRACT","role":"scope and acceptance contract","consumption_state":"CONSUMED","verification_state":"DIRECT"})
    lf=["index","input_id","snapshot_id","source_name","source_type","path_or_locator","source_hash","source_hash_kind","bytes","members","priority","role","consumption_state","verification_state"]
    cwrite("INPUT_LEDGER.csv",ledger,lf)

    cohort=[]
    def add(pk,label,role,matrix,process,ht,mode,temp,reinf,dose,unit,arch,interface,ys=None,uts=None,el=None,cys=None,ucs=None,cduct=None,stress=None,fracture="UNRESOLVED",grade="DIRECT_TABLE_TEXT"):
        p=PAPERS[pk]; su=uid("SAMPLE",p["paper_uid"],label,process,ht); cu=uid("COND",su,mode,temp); ru=uid("ROW",p["paper_uid"],su,cu)
        reserve=(uts-ys)/ys if finite(uts) and finite(ys) and ys>0 else None
        cohort.append({"row_uid":ru,"snapshot_id":snapshot,"paper_uid":p["paper_uid"],"doi":p["doi"],"sample_uid":su,"sample_label":label,"condition_uid":cu,"role":role,"matrix":matrix,"process":process,"heat_treatment":ht,"test_mode":mode,"test_temperature_c":temp,"reinforcement":reinf,"reinforcement_dose_value":dose,"reinforcement_dose_unit":unit,"architecture":arch,"interface_reaction_state":interface,"porosity_pct":None,"YS_MPa":ys,"UTS_MPa":uts,"EL_pct":el,"compressive_yield_MPa":cys,"UCS_MPa":ucs,"compressive_ductility_pct":cduct,"in_situ_max_stress_MPa":stress,"hardening_reserve_ratio":reserve,"fracture_mode":fracture,"evidence_grade":grade,"source_locator":p["locator"],"source_hash":p["hash"]})
        return ru

    jm=add("JIAO","Ti6Al4V_matrix","matrix_control","Ti6Al4V","powder_metallurgy","as_sintered","tension",25,"none",0,"vol%","unreinforced","none",770,930,8.1)
    jb=add("JIAO","3.4vol_TiBw","tmc","Ti6Al4V","powder_metallurgy","as_sintered","tension",25,"TiBw",3.4,"vol%","first_scale_network","intact_or_unresolved",930,1070,3.2)
    js=add("JIAO","4vol_Ti5Si3","tmc","Ti6Al4V","powder_metallurgy","as_sintered","tension",25,"Ti5Si3",4,"vol%","submicron_single_network","intact_or_unresolved",900,1030,2.1)
    jd=add("JIAO","4vol_Ti5Si3_plus_3.4vol_TiBw","tmc","Ti6Al4V","powder_metallurgy","as_sintered","tension",25,"Ti5Si3+TiBw",7.4,"vol%_sum","two_scale_network","local_late_TiBw_fracture",1050,1180,5.0,fracture="MIXED_TOUGHENED_NETWORK")
    jh=add("JIAO","8vol_Ti5Si3_plus_3.4vol_TiBw","tmc","Ti6Al4V","powder_metallurgy","as_sintered","tension",25,"Ti5Si3+TiBw",11.4,"vol%_sum","coarse_connected_boundary_network","connected_brittle_phase",None,980,1.0,fracture="BRITTLE_CONNECTED_REINFORCEMENT")
    lm=add("LIU","LDED_Ti6Al4V","matrix_control","Ti6Al4V","LDED","as_built","micro_tension_in_situ",25,"none",0,"vol%_precursor","lamellar_matrix","none",stress=1076,fracture="LAMELLAR_LOCALIZATION_COALESCENCE",grade="DIRECT_FIGURE_TEXT")
    ld=add("LIU","LDED_1vol_B4C_reaction_TiB_TiC","tmc","Ti6Al4V","LDED","as_built","micro_tension_in_situ",25,"TiB+TiC",1,"vol%_B4C_precursor","3D_network_plus_heterogeneous_alpha_lamellae","interfaces_not_dominant",stress=1190,fracture="TRANS_NETWORK_ZIGZAG_TOUGHENED",grade="DIRECT_FIGURE_TEXT")

    bh={0:[(800,263,678,58),(1000,354,760,48),(1100,439,768,49)],0.5:[(800,378,828,52),(1000,610,1021,41),(1100,598,965,41)],1:[(800,391,830,44),(1000,756,1106,32),(1100,761,1164,32)],2:[(800,435,897,31),(1000,903,1238,24),(1100,954,1375,25)],3:[(800,503,924,29),(1000,936,1273,17),(1100,1058,1364,17)],4:[(800,546,984,19),(1000,1006,1330,12),(1100,1095,1421,13)],5:[(800,406,888,16),(1000,980,1274,9),(1100,962,1254,7)]}
    bhr={}
    for dose,vals in bh.items():
        for st,cys,ucs,duct in vals:
            fm="UNRESOLVED"; interface="dose_dependent"
            if dose==5 and st==800: fm="DUCTILE"; interface="BNNT_retained_low_reaction"
            if dose==5 and st==1000: fm="MIXED"; interface="partial_BNNT_to_TiB"
            if dose==5 and st==1100: fm="BRITTLE_CLEAVAGE"; interface="complete_TiB_reaction"
            bhr[(dose,st)]=add("BHUIYAN",f"Ti_{dose:g}vol_BNNT_sinter_{st}C","matrix_control" if dose==0 else "tmc","CP_Ti","press_and_sinter",f"{st}C","compression",25,"BNNT_to_TiB",dose,"vol%_BNNT_feed","dispersed_to_clustered",interface,cys=cys,ucs=ucs,cduct=duct,fracture=fm)

    ta=add("TA15","TiC_TA15_as_cast","tmc_baseline","TA15","casting","as_cast","tension",25,"TiC",None,"unresolved","cast_dispersion","unresolved",1023.1,1048.3,3.92)
    t1=add("TA15","TiC_TA15_HT1","tmc_state","TA15","casting","HT1","tension",25,"TiC",None,"unresolved","heat_treated","unresolved",1045.8,1119.7,2.17)
    t2=add("TA15","TiC_TA15_HT2","tmc_state","TA15","casting","HT2","tension",25,"TiC",None,"unresolved","heat_treated","unresolved",1056.5,1130.6,1.33)
    t3=add("TA15","TiC_TA15_HT3","tmc_state","TA15","casting","HT3","tension",25,"TiC",None,"unresolved","heat_treated","unresolved",1076.6,1159.4,0.65)
    wm=add("WANG","wire_LDED_Ti6Al4V","matrix_control","Ti6Al4V","wire_LDED","as_built","tension",25,"none",0,"wt%_feed","unreinforced","none",858,942,8.33,fracture="DUCTILE")
    wt=add("WANG","wire_powder_TiC_Ti6Al4V","tmc","Ti6Al4V","wire_powder_LDED","as_built","tension",25,"TiC",2.93,"wt%_TiC_feed","build_direction_segregated_eutectic_TiC","brittle_eutectic",954,1050,5.76,fracture="MIXED_QUASI_CLEAVAGE")

    cf=["row_uid","snapshot_id","paper_uid","doi","sample_uid","sample_label","condition_uid","role","matrix","process","heat_treatment","test_mode","test_temperature_c","reinforcement","reinforcement_dose_value","reinforcement_dose_unit","architecture","interface_reaction_state","porosity_pct","YS_MPa","UTS_MPa","EL_pct","compressive_yield_MPa","UCS_MPa","compressive_ductility_pct","in_situ_max_stress_MPa","hardening_reserve_ratio","fracture_mode","evidence_grade","source_locator","source_hash"]
    cwrite("ANALYSIS_COHORT.csv",cohort,cf)
    by={r["row_uid"]:r for r in cohort}

    pairs=[]
    def pair(c,t,typ,scope):
        a,b=by[c],by[t]; row={"pair_uid":uid("PAIR",c,t,typ),"snapshot_id":snapshot,"paper_uid":a["paper_uid"],"control_row_uid":c,"treated_row_uid":t,"control_sample_uid":a["sample_uid"],"treated_sample_uid":b["sample_uid"],"control_condition_uid":a["condition_uid"],"treated_condition_uid":b["condition_uid"],"comparison_type":typ,"pair_grade":"A","estimand_scope":scope,"dose_delta":b["reinforcement_dose_value"]-a["reinforcement_dose_value"] if finite(a["reinforcement_dose_value"]) and finite(b["reinforcement_dose_value"]) else None,"dose_unit":b["reinforcement_dose_unit"]}
        for prop,field in [("YS","YS_MPa"),("UTS","UTS_MPa"),("EL","EL_pct"),("compressive_yield","compressive_yield_MPa"),("UCS","UCS_MPa"),("compressive_ductility","compressive_ductility_pct"),("in_situ_max_stress","in_situ_max_stress_MPa")]:
            x,y=a[field],b[field]; row["control_"+prop]=x; row["treated_"+prop]=y; row["delta_"+prop]=y-x if finite(x) and finite(y) else None
        pairs.append(row)
    for c,t,typ,scope in [(jm,jb,"matrix_to_TiBw","reinforcement penalty"),(jm,js,"matrix_to_Ti5Si3","reinforcement penalty"),(jm,jd,"matrix_to_dual_network","strict matrix synergy test"),(jb,jd,"TiBw_to_dual_network","topology rescue"),(jd,jh,"dual_to_connected_high_dose","over-dose penalty"),(wm,wt,"matrix_to_nonuniform_TiC","reinforcement penalty"),(ta,t1,"as_cast_to_HT1","state-hardening penalty"),(ta,t2,"as_cast_to_HT2","state-hardening penalty"),(ta,t3,"as_cast_to_HT3","state-hardening penalty")]: pair(c,t,typ,scope)
    for st in [800,1000,1100]:
        for dose in [0.5,1,2,3,4,5]: pair(bhr[(0,st)],bhr[(dose,st)],"matrix_to_BNNT_TiB_dose","compression dose penalty")
    pf=["pair_uid","snapshot_id","paper_uid","control_row_uid","treated_row_uid","control_sample_uid","treated_sample_uid","control_condition_uid","treated_condition_uid","comparison_type","pair_grade","estimand_scope","dose_delta","dose_unit","control_YS","treated_YS","delta_YS","control_UTS","treated_UTS","delta_UTS","control_EL","treated_EL","delta_EL","control_compressive_yield","treated_compressive_yield","delta_compressive_yield","control_UCS","treated_UCS","delta_UCS","control_compressive_ductility","treated_compressive_ductility","delta_compressive_ductility","control_in_situ_max_stress","treated_in_situ_max_stress","delta_in_situ_max_stress"]
    cwrite("PAIR_MATCHES.csv",pairs,pf)

    effects=[]
    for p in pairs:
        for prop,unit in [("YS","MPa"),("UTS","MPa"),("EL","percentage_points"),("compressive_yield","MPa"),("UCS","MPa"),("compressive_ductility","percentage_points"),("in_situ_max_stress","MPa_proxy")]:
            x,y=p["control_"+prop],p["treated_"+prop]
            if finite(x) and finite(y):
                ln=math.log(y/x) if x>0 and y>0 else None
                effects.append({"effect_uid":uid("EFFECT",p["pair_uid"],prop),"snapshot_id":snapshot,"pair_uid":p["pair_uid"],"paper_uid":p["paper_uid"],"property":prop,"control_value":x,"treated_value":y,"unit":unit,"delta":y-x,"lnRR":ln,"percent_change":100*(math.exp(ln)-1) if finite(ln) else None,"comparison_type":p["comparison_type"],"pair_grade":"A","claim_level":2,"uncertainty_status":"raw same-paper contrast; replicate SD unavailable","support_domain":"tension" if prop in ["YS","UTS","EL"] else "compression_or_microproxy"})
    ef=["effect_uid","snapshot_id","pair_uid","paper_uid","property","control_value","treated_value","unit","delta","lnRR","percent_change","comparison_type","pair_grade","claim_level","uncertainty_status","support_domain"]
    cwrite("EFFECT_ESTIMATES.csv",effects,ef)

    hierarchical=[
    {"result_id":"QM08_MATRIX_PRIMARY","snapshot_id":snapshot,"estimand":"paper-balanced paired delta EL","estimate":-8.06,"unit":"percentage_points","ci95_low":-11.91,"ci95_high":-4.66,"prediction_low":-22.76,"prediction_high":7.22,"independent_papers":21,"matched_pairs":62,"model":"paper-cluster synthesis inherited from hash-bound QM08","status":"ESTIMABLE","claim_level":2,"source_snapshot":"QM08_b15be66c1b7b8b35829f"},
    {"result_id":"QM08_DIRECT_ORIGINAL","snapshot_id":snapshot,"estimand":"direct-original paired delta EL","estimate":-7.85,"unit":"percentage_points","ci95_low":-16.25,"ci95_high":-1.22,"prediction_low":"","prediction_high":"","independent_papers":7,"matched_pairs":17,"model":"paper-cluster direct-original sensitivity","status":"ESTIMABLE","claim_level":2,"source_snapshot":"QM08_b15be66c1b7b8b35829f"},
    {"result_id":"DIRECT_TWO_PAPER","snapshot_id":snapshot,"estimand":"equal-paper mean reconstructed matrix-control delta EL","estimate":-3.6183333333,"unit":"percentage_points","ci95_low":"","ci95_high":"","prediction_low":"","prediction_high":"","independent_papers":2,"matched_pairs":4,"model":"descriptive equal-paper mean","status":"DESCRIPTIVE_ONLY","claim_level":2,"source_snapshot":snapshot}]
    hf=["result_id","snapshot_id","estimand","estimate","unit","ci95_low","ci95_high","prediction_low","prediction_high","independent_papers","matched_pairs","model","status","claim_level","source_snapshot"]
    cwrite("HIERARCHICAL_RESULTS.csv",hierarchical,hf)
    cwrite("HETEROGENEITY.csv",[{"analysis_id":"QM08_MATRIX_PRIMARY","property":"EL","independent_papers":21,"matched_pairs":62,"I2_pct":99.9,"prediction_interval_low_pp":-22.76,"prediction_interval_high_pp":7.22,"interpretation":"heterogeneity dominates; no universal ductility penalty","source_snapshot":"QM08_b15be66c1b7b8b35829f"}],["analysis_id","property","independent_papers","matched_pairs","I2_pct","prediction_interval_low_pp","prediction_interval_high_pp","interpretation","source_snapshot"])
    cwrite("LOPO_RESULTS.csv",[{"left_out_paper":"none","estimate_delta_EL_pp":-3.6183333333,"papers_remaining":2,"status":"DESCRIPTIVE"},{"left_out_paper":PAPERS["JIAO"]["paper_uid"],"estimate_delta_EL_pp":-2.57,"papers_remaining":1,"status":"PRESSURE_TEST_ONLY"},{"left_out_paper":PAPERS["WANG"]["paper_uid"],"estimate_delta_EL_pp":-4.6666666667,"papers_remaining":1,"status":"PRESSURE_TEST_ONLY"}],["left_out_paper","estimate_delta_EL_pp","papers_remaining","status"])
    sensitivity=[{"analysis":"primary","definition":"QM08 matrix-level cohort","estimate":-8.06,"ci_low":-11.91,"ci_high":-4.66,"papers":21,"pairs":62,"decision":"negative average penalty survives"},{"analysis":"direct-original","definition":"QM08 direct-original only","estimate":-7.85,"ci_low":-16.25,"ci_high":-1.22,"papers":7,"pairs":17,"decision":"negative penalty survives"},{"analysis":"direct-reconstruction","definition":"Jiao plus Wang matrix controls","estimate":-3.6183333333,"ci_low":"","ci_high":"","papers":2,"pairs":4,"decision":"direction negative; magnitude not transportable"},{"analysis":"LOPO-Jiao","definition":"leave Jiao out","estimate":-2.57,"ci_low":"","ci_high":"","papers":1,"pairs":1,"decision":"negative"},{"analysis":"LOPO-Wang","definition":"leave Wang out","estimate":-4.6666666667,"ci_low":"","ci_high":"","papers":1,"pairs":3,"decision":"negative"},{"analysis":"test-mode-firewall","definition":"exclude compression from tensile EL synthesis","estimate":-8.06,"ci_low":-11.91,"ci_high":-4.66,"papers":21,"pairs":62,"decision":"Bhuiyan used only for reaction/fracture ordering"}]
    cwrite("SENSITIVITY_ANALYSIS.csv",sensitivity,["analysis","definition","estimate","ci_low","ci_high","papers","pairs","decision"])

    dose=[]
    for d,vals in bh.items():
        for st,cys,ucs,duct in vals:
            base=next(x for x in bh[0] if x[0]==st)
            dose.append({"paper_uid":PAPERS["BHUIYAN"]["paper_uid"],"dose_value":d,"dose_unit":"vol%_BNNT_feed","sinter_temperature_c":st,"test_mode":"compression","ductility_value_pct":duct,"delta_ductility_vs_zero_pp":duct-base[3],"UCS_MPa":ucs,"delta_UCS_vs_zero_MPa":ucs-base[2],"fracture_mode":by[bhr[(d,st)]]["fracture_mode"],"status":"PROTOCOL_SPECIFIC_DESCRIPTIVE"})
    for rid in [jm,jb,js,jd,jh]:
        r=by[rid]; dose.append({"paper_uid":r["paper_uid"],"dose_value":r["reinforcement_dose_value"],"dose_unit":r["reinforcement_dose_unit"],"sinter_temperature_c":"","test_mode":"tension","ductility_value_pct":r["EL_pct"],"delta_ductility_vs_zero_pp":r["EL_pct"]-8.1,"UCS_MPa":"","delta_UCS_vs_zero_MPa":"","fracture_mode":r["fracture_mode"],"status":"PHASE_AND_TOPOLOGY_CONFOUNDED"})
    cwrite("DOSE_RESPONSE.csv",dose,["paper_uid","dose_value","dose_unit","sinter_temperature_c","test_mode","ductility_value_pct","delta_ductility_vs_zero_pp","UCS_MPa","delta_UCS_vs_zero_MPa","fracture_mode","status"])

    interactions=[
    {"interaction_id":"JIAO_DUAL_VS_TIB","factor_a":"two-scale network","factor_b":"phase distribution","contrast":"dual minus TiBw-only","delta_strength_MPa":110,"strength_metric":"UTS","delta_ductility_pp":1.8,"test_mode":"tension","interpretation":"topology rescue, not matrix-level synergy","identifiability":"DIRECT_CONDITIONAL_CONTRAST"},
    {"interaction_id":"JIAO_HIGH_DOSE","factor_a":"dose","factor_b":"connected grain-boundary Ti5Si3","contrast":"11.4 minus 7.4 vol% sum","delta_strength_MPa":-200,"strength_metric":"UTS","delta_ductility_pp":-4,"test_mode":"tension","interpretation":"dose/connectivity destroy matrix ligament continuity","identifiability":"DOSE_TOPOLOGY_CONFOUNDED"},
    {"interaction_id":"BHUIYAN_800_1000","factor_a":"interface reaction","factor_b":"sintering temperature","contrast":"5vol% 1000C minus 800C","delta_strength_MPa":386,"strength_metric":"UCS","delta_ductility_pp":-7,"test_mode":"compression","interpretation":"retained BNNT ductile to partial TiB mixed","identifiability":"PROTOCOL_SPECIFIC"},
    {"interaction_id":"BHUIYAN_1000_1100","factor_a":"interface reaction","factor_b":"sintering temperature","contrast":"5vol% 1100C minus 1000C","delta_strength_MPa":-20,"strength_metric":"UCS","delta_ductility_pp":-2,"test_mode":"compression","interpretation":"complete TiB brittle cleavage","identifiability":"PROTOCOL_SPECIFIC"},
    {"interaction_id":"WANG_TIC","factor_a":"nonuniform TiC","factor_b":"brittle eutectic","contrast":"TMC minus matrix","delta_strength_MPa":108,"strength_metric":"UTS","delta_ductility_pp":-2.57,"test_mode":"tension","interpretation":"strength gain with mixed quasi-cleavage","identifiability":"DIRECT_PAIRED_ASSOCIATION"}]
    cwrite("INTERACTION_EFFECTS.csv",interactions,["interaction_id","factor_a","factor_b","contrast","delta_strength_MPa","strength_metric","delta_ductility_pp","test_mode","interpretation","identifiability"])

    fracture=[
    {"paper_uid":PAPERS["LIU"]["paper_uid"],"sample_uid":by[lm]["sample_uid"],"condition_uid":by[lm]["condition_uid"],"test_mode":"micro_tension_in_situ","fracture_mode_raw":"cracks initiate/coalesce along alpha lamellae with early localization","fracture_mode_category":"LAMELLAR_LOCALIZATION_COALESCENCE","ordinal_rank":"","reinforcement_fracture":"NA","debonding":"NA","void_nucleation":"not quantified","interface_reaction":"none","crack_path":"along alpha lamellae","confidence":"HIGH","evidence_grade":"DIRECT_FIGURE_TEXT"},
    {"paper_uid":PAPERS["LIU"]["paper_uid"],"sample_uid":by[ld]["sample_uid"],"condition_uid":by[ld]["condition_uid"],"test_mode":"micro_tension_in_situ","fracture_mode_raw":"trans-network zig-zag crack, deflection, blunting, arrest and late TiB fracture","fracture_mode_category":"TRANS_NETWORK_ZIGZAG_TOUGHENED","ordinal_rank":"","reinforcement_fracture":"late/local","debonding":"not dominant","void_nucleation":"microcrack near network","interface_reaction":"in-situ TiB+TiC","crack_path":"network then matrix blunting","confidence":"HIGH","evidence_grade":"DIRECT_FIGURE_TEXT"},
    {"paper_uid":PAPERS["JIAO"]["paper_uid"],"sample_uid":by[jd]["sample_uid"],"condition_uid":by[jd]["condition_uid"],"test_mode":"tension_notched_in_situ","fracture_mode_raw":"microcracks, bending, rapid propagation, TiBw fracture, deflection and secondary cracks","fracture_mode_category":"MIXED_TOUGHENED_NETWORK","ordinal_rank":1,"reinforcement_fracture":"late","debonding":"not identified","void_nucleation":"microcracks","interface_reaction":"Ti5Si3+TiBw","crack_path":"deflected with secondary cracks","confidence":"HIGH","evidence_grade":"DIRECT_FIGURE_TEXT"},
    {"paper_uid":PAPERS["JIAO"]["paper_uid"],"sample_uid":by[jh]["sample_uid"],"condition_uid":by[jh]["condition_uid"],"test_mode":"tension","fracture_mode_raw":"coarse connected Ti5Si3 is a preferential initiation path","fracture_mode_category":"BRITTLE_CONNECTED_REINFORCEMENT","ordinal_rank":2,"reinforcement_fracture":"local/likely","debonding":"not identified","void_nucleation":"not quantified","interface_reaction":"Ti5Si3+TiBw","crack_path":"connected boundary network","confidence":"MEDIUM_HIGH","evidence_grade":"DIRECT_TEXT"},
    {"paper_uid":PAPERS["BHUIYAN"]["paper_uid"],"sample_uid":by[bhr[(5,800)]]["sample_uid"],"condition_uid":by[bhr[(5,800)]]["condition_uid"],"test_mode":"compression","fracture_mode_raw":"ductile; shear bands and retained BNNT fragments","fracture_mode_category":"DUCTILE","ordinal_rank":0,"reinforcement_fracture":"BNNT fragments","debonding":"unresolved","void_nucleation":"unresolved","interface_reaction":"low","crack_path":"shear-band dominated","confidence":"HIGH","evidence_grade":"DIRECT_FRACTOGRAPHY_TEXT"},
    {"paper_uid":PAPERS["BHUIYAN"]["paper_uid"],"sample_uid":by[bhr[(5,1000)]]["sample_uid"],"condition_uid":by[bhr[(5,1000)]]["condition_uid"],"test_mode":"compression","fracture_mode_raw":"mixed ductile/brittle; TiB-rich cleavage and whisker pullout","fracture_mode_category":"MIXED","ordinal_rank":1,"reinforcement_fracture":"pullout","debonding":"possible","void_nucleation":"unresolved","interface_reaction":"partial","crack_path":"mixed regional","confidence":"HIGH","evidence_grade":"DIRECT_FRACTOGRAPHY_TEXT"},
    {"paper_uid":PAPERS["BHUIYAN"]["paper_uid"],"sample_uid":by[bhr[(5,1100)]]["sample_uid"],"condition_uid":by[bhr[(5,1100)]]["condition_uid"],"test_mode":"compression","fracture_mode_raw":"fully brittle cleavage after complete TiB conversion","fracture_mode_category":"BRITTLE_CLEAVAGE","ordinal_rank":2,"reinforcement_fracture":"unresolved","debonding":"unresolved","void_nucleation":"unresolved","interface_reaction":"complete","crack_path":"cleavage","confidence":"HIGH","evidence_grade":"DIRECT_FRACTOGRAPHY_TEXT"},
    {"paper_uid":PAPERS["WANG"]["paper_uid"],"sample_uid":by[wm]["sample_uid"],"condition_uid":by[wm]["condition_uid"],"test_mode":"tension","fracture_mode_raw":"ductile tearing ridges and large dimples","fracture_mode_category":"DUCTILE","ordinal_rank":0,"reinforcement_fracture":"NA","debonding":"NA","void_nucleation":"dimples","interface_reaction":"none","crack_path":"ductile tearing","confidence":"HIGH","evidence_grade":"DIRECT_FRACTOGRAPHY_TEXT"},
    {"paper_uid":PAPERS["WANG"]["paper_uid"],"sample_uid":by[wt]["sample_uid"],"condition_uid":by[wt]["condition_uid"],"test_mode":"tension","fracture_mode_raw":"mixed ductile/quasi-cleavage with small dimples and cleavage steps","fracture_mode_category":"MIXED_QUASI_CLEAVAGE","ordinal_rank":1,"reinforcement_fracture":"eutectic TiC fracture","debonding":"not dominant","void_nucleation":"small dimples","interface_reaction":"eutectic TiC","crack_path":"segregated brittle phase","confidence":"HIGH","evidence_grade":"DIRECT_FRACTOGRAPHY_TEXT"}]
    ff=["paper_uid","sample_uid","condition_uid","test_mode","fracture_mode_raw","fracture_mode_category","ordinal_rank","reinforcement_fracture","debonding","void_nucleation","interface_reaction","crack_path","confidence","evidence_grade"]
    cwrite("FRACTURE_MODE_LEDGER.csv",fracture,ff)

    damage=[]
    for strain,lo,hi,state,rank in [(0,0,2.21,"no visible cracks at zero load",0),(2.21,0,2.21,"three microcracks; initiation interval-censored in (0,2.21%]",1),(3.26,"","","crack addition and broadening",2),(3.57,"","","coarsening and bending",3),(3.87,"","","rapid propagation and TiBw fracture",4),(4.10,"","","fracture, deflection and secondary cracking",5)]:
        damage.append({"paper_uid":PAPERS["JIAO"]["paper_uid"],"sample_uid":by[jd]["sample_uid"],"condition_uid":by[jd]["condition_uid"],"reported_strain_pct":strain,"onset_lower_pct":lo,"onset_upper_pct":hi,"damage_state":state,"state_ordinal":rank,"binding":"same sample/condition as UTS=1180 MPa and EL=5.0%","evidence_grade":"DIRECT_FIGURE_TEXT"})
    damage += [{"paper_uid":PAPERS["LIU"]["paper_uid"],"sample_uid":by[lm]["sample_uid"],"condition_uid":by[lm]["condition_uid"],"reported_strain_pct":"","onset_lower_pct":"","onset_upper_pct":"","damage_state":"matrix initiation along alpha lamellae; exact global strain unavailable","state_ordinal":"","binding":"same in-situ specimen; crosshead displacement only","evidence_grade":"DIRECT_FIGURE_TEXT"},{"paper_uid":PAPERS["LIU"]["paper_uid"],"sample_uid":by[ld]["sample_uid"],"condition_uid":by[ld]["condition_uid"],"reported_strain_pct":"","onset_lower_pct":"","onset_upper_pct":"","damage_state":"microcrack near network; exact global strain unavailable","state_ordinal":"","binding":"same in-situ specimen","evidence_grade":"DIRECT_FIGURE_TEXT"},{"paper_uid":PAPERS["WANG"]["paper_uid"],"sample_uid":by[wt]["sample_uid"],"condition_uid":by[wt]["condition_uid"],"reported_strain_pct":"","onset_lower_pct":"","onset_upper_pct":"","damage_state":"post-fracture mixed mode; no onset strain","state_ordinal":"","binding":"same tensile condition","evidence_grade":"DIRECT_FRACTOGRAPHY_TEXT"}]
    cwrite("DAMAGE_INITIATION.csv",damage,["paper_uid","sample_uid","condition_uid","reported_strain_pct","onset_lower_pct","onset_upper_pct","damage_state","state_ordinal","binding","evidence_grade"])

    budget=[
    ("QM08_PRIMARY","MULTI_PAPER","matched matrix","matched TMC",-8.06,"","","all mechanisms under same-paper matching","matrix-level","PAPER_CLUSTER_ESTIMAND_NOT_MECHANISM_FRACTION",21),
    ("JIAO_TIB",PAPERS["JIAO"]["paper_uid"],"Ti6Al4V","3.4vol% TiBw",-4.9,140,"UTS","first-scale brittle network","matrix-level","CONDITIONAL_NOT_ADDITIVE",1),
    ("JIAO_TI5SI3",PAPERS["JIAO"]["paper_uid"],"Ti6Al4V","4vol% Ti5Si3",-6,100,"UTS","single submicron network","matrix-level","CONDITIONAL_NOT_ADDITIVE",1),
    ("JIAO_DUAL_MATRIX",PAPERS["JIAO"]["paper_uid"],"Ti6Al4V","dual network",-3.1,250,"UTS","two-scale compatibility partially rescues","matrix-level","CONDITIONAL_NOT_ADDITIVE",1),
    ("JIAO_DUAL_RESCUE",PAPERS["JIAO"]["paper_uid"],"TiBw-only","dual network",1.8,110,"UTS","topology rescue","TMC-level","NOT_MATRIX_SYNERGY",1),
    ("JIAO_HIGH_DOSE",PAPERS["JIAO"]["paper_uid"],"dual network","connected high-dose",-4,-200,"UTS","connected brittle boundary path","TMC-level","DOSE_TOPOLOGY_CONFOUNDED",1),
    ("WANG_TIC",PAPERS["WANG"]["paper_uid"],"wire-LDED matrix","TiC/Ti6Al4V",-2.57,108,"UTS","nonuniform brittle eutectic TiC","matrix-level","CONDITIONAL_NOT_ADDITIVE",1),
    ("BHUIYAN_800",PAPERS["BHUIYAN"]["paper_uid"],"0vol% BNNT","5vol% feed",-42,210,"UCS","dose/clustering with retained BNNT","compression","NOT_TENSILE_EL",1),
    ("BHUIYAN_1000",PAPERS["BHUIYAN"]["paper_uid"],"0vol% BNNT","5vol% feed",-39,514,"UCS","partial reaction","compression","NOT_TENSILE_EL",1),
    ("BHUIYAN_1100",PAPERS["BHUIYAN"]["paper_uid"],"0vol% BNNT","5vol% feed",-42,486,"UCS","complete TiB reaction and cleavage","compression","NOT_TENSILE_EL",1),
    ("TA15_HT1",PAPERS["TA15"]["paper_uid"],"as-cast","HT1",-1.75,71.4,"UTS","state hardening","same TMC state","PROCESS_EFFECT",1),
    ("TA15_HT2",PAPERS["TA15"]["paper_uid"],"as-cast","HT2",-2.59,82.3,"UTS","state hardening","same TMC state","PROCESS_EFFECT",1),
    ("TA15_HT3",PAPERS["TA15"]["paper_uid"],"as-cast","HT3",-3.27,111.1,"UTS","strongest state hardening","same TMC state","PROCESS_EFFECT",1)]
    budget_rows=[dict(zip(["budget_id","paper_uid","control","treated","delta_EL_pp","delta_strength_MPa","strength_metric","mechanism_label","comparison_level","attribution_status","independent_papers"],x)) for x in budget]
    cwrite("DUCTILITY_PENALTY_BUDGET.csv",budget_rows,["budget_id","paper_uid","control","treated","delta_EL_pp","delta_strength_MPa","strength_metric","mechanism_label","comparison_level","attribution_status","independent_papers"])

    synergy=[
    {"case_id":"QM08_STRICT_AGG","paper_uid":"MULTI_PAPER","reference":"matched matrix","candidate":"strict matrix-level synergy subset","delta_strength_MPa":">0","delta_EL_pp":">0","classification":"STRICT_MATRIX_SYNERGY","support":"7 pairs / 4 independent papers","mechanism":"case-specific low dose or special architecture","claim_ceiling":"row identities required before Gold use"},
    {"case_id":"LIU_DUAL_HETERO","paper_uid":PAPERS["LIU"]["paper_uid"],"reference":"LDED Ti6Al4V microtension","candidate":"3D TiB+TiC network + heterogeneous alpha lamellae","delta_strength_MPa":114,"delta_EL_pp":"exact offsite EL unavailable","classification":"QUALITATIVE_STRICT_SYNERGY_CANDIDATE","support":"direct crack path and stress proxy","mechanism":"network stabilizes deformation; blunting/deflection/arrest","claim_ceiling":"not VALIDATED without exact tensile EL"},
    {"case_id":"JIAO_TOPOLOGY_RESCUE","paper_uid":PAPERS["JIAO"]["paper_uid"],"reference":"3.4vol% TiBw TMC","candidate":"dual network","delta_strength_MPa":110,"delta_EL_pp":1.8,"classification":"TMC_LEVEL_TOPOLOGY_RESCUE","support":"direct same-paper pair","mechanism":"submicron Ti5Si3 improves compatibility","claim_ceiling":"still -3.1 pp versus matrix"},
    {"case_id":"JIAO_HIGH_DOSE_FAILURE","paper_uid":PAPERS["JIAO"]["paper_uid"],"reference":"dual network","candidate":"connected high-dose network","delta_strength_MPa":-200,"delta_EL_pp":-4,"classification":"ANTI_EXAMPLE","support":"direct same-paper pair","mechanism":"connected Ti5Si3 crack path","claim_ceiling":"dose and topology co-vary"},
    {"case_id":"WANG_TIC_FAILURE","paper_uid":PAPERS["WANG"]["paper_uid"],"reference":"wire-LDED matrix","candidate":"nonuniform TiC/Ti6Al4V","delta_strength_MPa":108,"delta_EL_pp":-2.57,"classification":"CONVENTIONAL_TRADEOFF","support":"pair + fractography","mechanism":"segregated brittle eutectic initiates/propagates cracks","claim_ceiling":"level-2 association"},
    {"case_id":"BHUIYAN_REACTION_TRANSITION","paper_uid":PAPERS["BHUIYAN"]["paper_uid"],"reference":"5vol% feed 800C","candidate":"same feed 1000/1100C","delta_strength_MPa":"UCS 888->1274->1254","delta_EL_pp":"compression ductility 16->9->7","classification":"REACTION_EMBRITTLEMENT_ANTI_EXAMPLE","support":"ordered fracture evidence","mechanism":"retained BNNT ductile -> partial TiB mixed -> complete TiB brittle","claim_ceiling":"compression only"}]
    sf=["case_id","paper_uid","reference","candidate","delta_strength_MPa","delta_EL_pp","classification","support","mechanism","claim_ceiling"]
    cwrite("SYNERGY_COUNTEREXAMPLES.csv",synergy,sf)

    nulls=[
    ("ORDINAL_GENERAL_MODEL","general ductile-to-mixed-to-brittle probability","NOT_IDENTIFIABLE","five explicit conditions across two papers and mixed protocols","more labels within one test mode"),
    ("DAMAGE_ONSET_GLOBAL","universal damage-initiation strain","NOT_IDENTIFIABLE","only Jiao gives strain-staged observations; onset interval-censored","same-definition in-situ fields across papers"),
    ("MECHANISM_FRACTIONS","fraction of EL loss due to fracture/debonding/voids","NOT_IDENTIFIABLE","fractography cannot close an additive budget","controlled perturbations + quantitative damage evolution"),
    ("POROSITY_COEFFICIENT","EL penalty per porosity percent","NOT_IDENTIFIABLE","condition-bound porosity missing","measured porosity tied to sample/condition"),
    ("HARDENING_THRESHOLD","hardening reserve preventing cracks","NOT_IDENTIFIABLE","TA15 and Wang contradict a simple threshold","true stress-strain + onset data"),
    ("UNIVERSAL_DOSE_THRESHOLD","universal dose at retained EL","NOT_IDENTIFIABLE","units, phases and topologies differ","actual phase vol% and matched baselines"),
    ("LIU_EXACT_EL","strict matrix-level Liu tensile synergy","CONTINUE_DATA_GAP","offsite tensile EL not bound","Composites Communications 40 (2023) 101611 table"),
    ("PRODUCTION_RECIPE","validated anti-embrittlement formulation","FORBIDDEN","read-only synthesis under production lock","experimental validation and local authority")]
    cwrite("NULL_NEGATIVE_RESULTS.csv",[dict(zip(["result_id","question","status","reason","required"],x)) for x in nulls],["result_id","question","status","reason","required"])

    conflicts=[
    ("C01","synergy definition","matrix-level improvement","improvement versus brittle TMC","separate strict synergy from topology rescue","RESOLVED_BY_SCHEMA"),
    ("C02","Liu dose","1vol% B4C precursor","actual TiB+TiC fraction unresolved","retain precursor unit","OPEN_DATA_GAP"),
    ("C03","ductility test mode","tensile EL","compression ductility","never pool","RESOLVED_BY_FIREWALL"),
    ("C04","fractography","mechanism support","quantitative contribution share","prohibit share inference","RESOLVED_BY_CLAIM_RULE"),
    ("C05","hardening reserve","can increase","EL can collapse","coordinate only, not criterion","RESOLVED_BY_INTERPRETATION"),
    ("C06","canonical identity","recovery UIDs","V29 UIDs unavailable","request local reconciliation","OPEN_AUTHORITY_GAP")]
    cwrite("CONFLICT_LEDGER.csv",[dict(zip(["conflict_id","object","state_a","state_b","resolution","status"],x)) for x in conflicts],["conflict_id","object","state_a","state_b","resolution","status"])
    cwrite("EXCLUDED_RECORDS.csv",[{"record_id":"EX01","reason":"compression not tensile EL","terminal_state":"RETAINED_FOR_FRACTURE_ORDERING"},{"record_id":"EX02","reason":"duplicate Jiao copies","terminal_state":"DEDUPLICATED_BY_DOI"},{"record_id":"EX03","reason":"unbound relevant papers lacked sample-condition rows","terminal_state":"REGISTERED_NOT_POOLED"}],["record_id","reason","terminal_state"])

    with (ROOT/"PROVENANCE.jsonl").open("w",encoding="utf-8",newline="\n") as f:
        for r in cohort:
            f.write(json.dumps({"row_uid":r["row_uid"],"snapshot_id":snapshot,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"source_locator":r["source_locator"],"source_hash":r["source_hash"],"evidence_grade":r["evidence_grade"],"values":{k:r[k] for k in ["YS_MPa","UTS_MPa","EL_pct","compressive_yield_MPa","UCS_MPa","compressive_ductility_pct","in_situ_max_stress_MPa"] if r[k] not in [None,""]},"note":"recovery row; no Gold promotion"},ensure_ascii=False,sort_keys=True)+"\n")
        for r in hierarchical[:2]:
            f.write(json.dumps({"row_uid":r["result_id"],"snapshot_id":snapshot,"paper_uid":"MULTI_PAPER","sample_uid":"AGGREGATE","condition_uid":"MATCHED_TENSILE","source_locator":"file_library:QM08/00_EXECUTIVE_VERDICT.md","source_hash":"QM08_b15be66c1b7b8b35829f","evidence_grade":"HASH_BOUND_PRIOR_SYNTHESIS","values":{"estimate":r["estimate"],"ci95_low":r["ci95_low"],"ci95_high":r["ci95_high"]}},ensure_ascii=False,sort_keys=True)+"\n")

    # Figure data and code.
    rng=random.Random(42)
    strata=[("Low reaction / matrix",[2,0,0]),("Nonuniform / partial reaction",[0,2,0]),("Complete TiB reaction",[0,0,1])]
    probs=[]
    for s,counts in strata:
        samples=[[] for _ in counts]
        for _ in range(12000):
            g=[rng.gammavariate(c+0.5,1) for c in counts]; z=sum(g)
            for i,x in enumerate(g): samples[i].append(x/z)
        for mode,c,vals in zip(["Ductile","Mixed","Brittle"],counts,samples):
            vals.sort(); probs.append({"stratum":s,"mode":mode,"observed_count":c,"condition_count":sum(counts),"posterior_mean":sum(vals)/len(vals),"ci95_low":vals[int(.025*len(vals))],"ci95_high":vals[int(.975*len(vals))-1],"method":"Jeffreys-Dirichlet descriptive","independent_papers":2})
    cwrite("figure_data/fracture_mode_probability.csv",probs,["stratum","mode","observed_count","condition_count","posterior_mean","ci95_low","ci95_high","method","independent_papers"])
    waterfall=[{"sequence":0,"condition":"Ti6Al4V matrix","delta_el_pp":8.1,"cumulative_el_pct":8.1,"mechanism":"baseline"},{"sequence":1,"condition":"3.4 vol% TiBw","delta_el_pp":-4.9,"cumulative_el_pct":3.2,"mechanism":"first-scale brittle network penalty"},{"sequence":2,"condition":"Dual-scale network","delta_el_pp":1.8,"cumulative_el_pct":5.0,"mechanism":"topology rescue"},{"sequence":3,"condition":"Connected high-dose network","delta_el_pp":-4.0,"cumulative_el_pct":1.0,"mechanism":"connected crack-path penalty"}]
    cwrite("figure_data/el_penalty_waterfall.csv",waterfall,["sequence","condition","delta_el_pp","cumulative_el_pct","mechanism"])
    hard=[]
    for rid in [jm,jb,js,jd,ta,t1,t2,t3,wm,wt]:
        r=by[rid]; cls="ductile matrix" if rid==wm else "mixed quasi-cleavage" if rid==wt else "network deflection" if rid==jd else "state-hardened low-EL" if rid in [t1,t2,t3] else "unresolved fracture mode"
        hard.append({"paper_uid":r["paper_uid"],"sample_label":r["sample_label"],"hardening_reserve_ratio":r["hardening_reserve_ratio"],"EL_pct":r["EL_pct"],"UTS_MPa":r["UTS_MPa"],"YS_MPa":r["YS_MPa"],"damage_class":cls,"independent_papers":3})
    cwrite("figure_data/hardening_damage_map.csv",hard,["paper_uid","sample_label","hardening_reserve_ratio","EL_pct","UTS_MPa","YS_MPa","damage_class","independent_papers"])
    cwrite("figure_data/synergy_counterexample_cards.csv",synergy,sf)

    scripts={
"plot_fracture_mode_probability.py":'''from pathlib import Path\nimport csv,matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nR=Path(__file__).resolve().parents[1]; rows=list(csv.DictReader((R/"figure_data/fracture_mode_probability.csv").open()))\nS=list(dict.fromkeys(x["stratum"] for x in rows)); M=["Ductile","Mixed","Brittle"]; fig,ax=plt.subplots(figsize=(10.5,6.5)); w=.24\nfor j,m in enumerate(M):\n q=[next(x for x in rows if x["stratum"]==s and x["mode"]==m) for s in S]; y=[float(x["posterior_mean"]) for x in q]; lo=[a-float(x["ci95_low"]) for a,x in zip(y,q)]; hi=[float(x["ci95_high"])-a for a,x in zip(y,q)]; ax.bar([i+(j-1)*w for i in range(len(S))],y,w,label=m,yerr=[lo,hi],capsize=3)\nax.set_xticks(range(len(S)),S); ax.set_ylim(0,1); ax.set_ylabel("Posterior category probability"); ax.set_title("Fracture-mode probability from explicit categorical evidence"); ax.legend(frameon=False); ax.grid(axis="y",alpha=.25); ax.text(.01,-.2,"2 papers | 5 conditions | descriptive, not transportable",transform=ax.transAxes); fig.tight_layout()\nfor e,d in [("png",600),("pdf",None),("svg",None)]: fig.savefig(R/"figures"/f"QM36_F1_fracture_mode_probability.{e}",dpi=d,bbox_inches="tight")\n''',
"plot_el_penalty_waterfall.py":'''from pathlib import Path\nimport csv,matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nR=Path(__file__).resolve().parents[1]; rows=sorted(csv.DictReader((R/"figure_data/el_penalty_waterfall.csv").open()),key=lambda x:int(x["sequence"])); fig,ax=plt.subplots(figsize=(10.5,6.5)); prev=0\nfor i,r in enumerate(rows):\n d=float(r["delta_el_pp"]); cur=float(r["cumulative_el_pct"]); ax.bar(i,cur if i==0 else abs(d),bottom=0 if i==0 else min(prev,cur),hatch="..." if i==0 else ("//" if d<0 else "\\\\")); ax.text(i,cur+.2,f"{cur:.1f}%",ha="center"); prev=cur\nax.set_xticks(range(len(rows)),[r["condition"] for r in rows],rotation=18,ha="right"); ax.set_ylabel("Elongation (%)"); ax.set_title("Observed EL penalty and topology rescue"); ax.grid(axis="y",alpha=.25); ax.text(.01,-.25,"1 paper | conditional sequence | not additive causal fractions",transform=ax.transAxes); fig.tight_layout()\nfor e,d in [("png",600),("pdf",None),("svg",None)]: fig.savefig(R/"figures"/f"QM36_F2_el_penalty_waterfall.{e}",dpi=d,bbox_inches="tight")\n''',
"plot_hardening_damage_map.py":'''from pathlib import Path\nimport csv,matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nR=Path(__file__).resolve().parents[1]; rows=list(csv.DictReader((R/"figure_data/hardening_damage_map.csv").open())); C=list(dict.fromkeys(x["damage_class"] for x in rows)); marks=["o","s","^","D","P","X"]; fig,ax=plt.subplots(figsize=(10.5,7))\nfor i,c in enumerate(C):\n q=[x for x in rows if x["damage_class"]==c]; xx=[float(x["hardening_reserve_ratio"]) for x in q]; yy=[float(x["EL_pct"]) for x in q]; ax.scatter(xx,yy,marker=marks[i%len(marks)],s=70,label=c)\nax.set_xlabel("Macroscopic hardening reserve, (UTS - YS) / YS"); ax.set_ylabel("Tensile elongation (%)"); ax.set_title("Strain-hardening reserve versus damage/ductility state"); ax.grid(alpha=.25); ax.legend(frameon=False,fontsize=8); ax.text(.01,-.15,"3 papers | 10 samples | coordinate, not anti-damage threshold",transform=ax.transAxes); fig.tight_layout()\nfor e,d in [("png",600),("pdf",None),("svg",None)]: fig.savefig(R/"figures"/f"QM36_F3_hardening_damage_map.{e}",dpi=d,bbox_inches="tight")\n''',
"plot_synergy_counterexample_cards.py":'''from pathlib import Path\nimport csv,textwrap,matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nfrom matplotlib.patches import FancyBboxPatch\nR=Path(__file__).resolve().parents[1]; rows=list(csv.DictReader((R/"figure_data/synergy_counterexample_cards.csv").open())); ids=["QM08_STRICT_AGG","JIAO_TOPOLOGY_RESCUE","WANG_TIC_FAILURE","BHUIYAN_REACTION_TRANSITION"]; q=[next(x for x in rows if x["case_id"]==i) for i in ids]; fig,ax=plt.subplots(figsize=(12,7.5)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")\nfor r,(x,y) in zip(q,[(.04,.55),(.52,.55),(.04,.08),(.52,.08)]):\n ax.add_patch(FancyBboxPatch((x,y),.42,.35,boxstyle="round,pad=.015",fill=False)); ax.text(x+.02,y+.31,r["classification"].replace("_"," "),fontweight="bold",va="top"); body=f"Reference: {r['reference']}\\nCandidate: {r['candidate']}\\nStrength: {r['delta_strength_MPa']} MPa\\nDuctility: {r['delta_EL_pp']} pp\\nMechanism: {r['mechanism']}"; ax.text(x+.02,y+.27,"\\n".join(textwrap.fill(z,52) for z in body.splitlines()),fontsize=8.5,va="top")\nax.set_title("Strict synergy, topology rescue, and anti-examples"); ax.text(.02,.01,"22 papers / 64 matched comparisons; reference hierarchy preserved."); fig.tight_layout()\nfor e,d in [("png",600),("pdf",None),("svg",None)]: fig.savefig(R/"figures"/f"QM36_F4_synergy_counterexample_cards.{e}",dpi=d,bbox_inches="tight")\n'''}
    for name,code in scripts.items(): text("plot_code/"+name,code)
    for name in scripts: subprocess.run([sys.executable,str(ROOT/"plot_code"/name)],check=True)

    jwrite("PLOT_SPECS.json",{"window_id":WINDOW,"snapshot_id":snapshot,"formats":["SVG","PDF","PNG_600dpi"],"language":"English","plots":[{"figure_id":"QM36_F1","data":"figure_data/fracture_mode_probability.csv","code":"plot_code/plot_fracture_mode_probability.py","papers":2,"conditions":5,"claim_ceiling":"descriptive"},{"figure_id":"QM36_F2","data":"figure_data/el_penalty_waterfall.csv","code":"plot_code/plot_el_penalty_waterfall.py","papers":1,"conditions":4,"claim_ceiling":"not additive"},{"figure_id":"QM36_F3","data":"figure_data/hardening_damage_map.csv","code":"plot_code/plot_hardening_damage_map.py","papers":3,"conditions":10,"claim_ceiling":"no threshold"},{"figure_id":"QM36_F4","data":"figure_data/synergy_counterexample_cards.csv","code":"plot_code/plot_synergy_counterexample_cards.py","papers":22,"conditions":64,"claim_ceiling":"reference-aware classification"}]})

    text("METHODS.md",f'''# METHODS — QM36\n\n`WINDOW=QM36 | SNAPSHOT={snapshot} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`\n\nAll 26 archives are hash-registered. Scientific results use the hash-bound QM08 paper-cluster synthesis and five directly read original papers. Atomic rows preserve paper × sample × process × heat treatment × test mode × temperature. Tensile EL, compression ductility and micro-tension stress proxies are never pooled. The primary estimand is matched `ΔEL=EL_TMC-EL_matrix`. Fracture descriptions are coded into auditable categories. Jiao damage onset is interval-censored in `(0,2.21%]`. The fracture probability plot is a Jeffreys-Dirichlet descriptive posterior because a general ordinal model is not identifiable. `(UTS-YS)/YS` is a map coordinate, not a causal anti-damage threshold. QM08 supplies cluster uncertainty, prediction interval and I²; the direct two-paper reconstruction has LOPO pressure tests. Maximum claim level is paired/adjusted association. No Gold promotion, ACTIVE modification, production registration or validated recipe occurs.\n''')
    text("LIMITATIONS.md",'''# LIMITATIONS\n\n1. Authoritative V29 atomic rows, canonical UIDs and the row-level QM08 64-pair table are unavailable.\n2. Several original PDF byte hashes remain locator-binding hashes.\n3. Fracture probability evidence is sparse and mixes tension/compression; it is descriptive only.\n4. Damage onset is interval-censored or unavailable.\n5. Porosity, actual phase fraction, local triaxiality and true stress-strain fields are incomplete.\n6. Dose and topology co-vary; the waterfall is not an additive causal budget.\n7. Fractography cannot quantify mechanism contribution shares.\n8. No production or Gold action was performed.\n''')
    text("00_EXECUTIVE_VERDICT.md",f'''# QM36 Executive Verdict\n\n`WINDOW=QM36 | SNAPSHOT={snapshot} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`\n\nThe primary matched matrix-control synthesis gives **ΔEL = -8.06 percentage points** (95% CI **-11.91 to -4.66**; 62 pairs / 21 papers). The direct-original sensitivity is **-7.85 pp** (95% CI **-16.25 to -1.22**). Extreme heterogeneity (**I²=99.9%**, prediction interval **-22.76 to +7.22 pp**) rejects a universal penalty constant.\n\nPlasticity is lost when mismatch-driven reinforcement fracture, microcrack/void nucleation, brittle connected paths or interface reaction activate before matrix ligaments redistribute load. A network works only when it preserves matrix continuity and forces deflection, blunting or arrest. Jiao's dual network gives **+110 MPa UTS and +1.8 pp EL versus TiBw-only**, but remains **-3.1 pp versus matrix**: topology rescue, not strict matrix synergy. The connected high-dose state then loses **200 MPa UTS and 4.0 pp EL**.\n\nJiao's first visible microcracks are interval-censored in **(0,2.21%] strain**; damage progresses through broadening, bending, rapid propagation/TiBw fracture and secondary cracking by 4.10%. Wang's nonuniform TiC composite gains **108 MPa UTS** but loses **2.57 pp EL**, changing from ductile dimples to mixed quasi-cleavage. Bhuiyan's fixed 5 vol% feed changes compression ductility **16% -> 9% -> 7%** and fracture **ductile -> mixed -> brittle** as BNNT converts to TiB.\n\nMacroscopic hardening reserve is not sufficient: TiC/TA15 heat treatment raises `(UTS-YS)/YS` while EL collapses from 3.92% to 0.65%. Architecture, damage onset and matrix ligament continuity dominate. Fractography supports mechanism but not quantitative contribution fractions. Claim ceiling: level 2 paired effects and level 3 adjusted association; no production/Gold/VALIDATED claim.\n\n{STATUS}\n''')

    jwrite("WEB_TO_LOCAL_REQUEST.json",{"window_id":WINDOW,"snapshot_id":snapshot,"status":"CONTINUE_DATA_GAP","required":[{"priority":1,"object":"V29_ATOMIC_RECORDS_AND_CANONICAL_UID_MAP"},{"priority":1,"object":"QM08_ROW_LEVEL_PAIR_EFFECT_PROVENANCE_TABLES"},{"priority":1,"object":"Composites_Communications_40_2023_101611_exact_tensile_table"},{"priority":1,"object":"original_PDF_byte_hashes"},{"priority":2,"object":"condition_bound_porosity_actual_phase_fraction_true_stress_strain"}],"next_action":"LOCAL_ABSORB_RECONCILE_AND_RECOMPUTE"})
    text("LOCAL_ABSORPTION_PROMPT.md",f'''# Local absorption prompt — QM36\n\nVerify `CHECKSUMS.sha256`; run `python tests/test_qm36_outputs.py .`; reconcile recovery UIDs against V29; import QM08 row-level pairs; recover Liu exact tensile table and original PDF hashes; recompute without crossing test-mode or precursor/actual-phase firewalls. Do not promote Gold or modify ACTIVE until all conflicts close. Expected recovery snapshot: `{snapshot}`.\n''')
    jwrite("WINDOW_STATUS.json",{"window_id":WINDOW,"snapshot_id":snapshot,"papers_seen":22,"papers_included":22,"independent_papers":22,"mechanism_independent_papers":5,"atomic_rows":len(cohort),"matched_pairs":64,"direct_reconstructed_pairs":len(pairs),"effect_estimates":len(effects),"plots_generated":4,"plot_files":12,"open_conflicts":2,"claim_level_max":3,"status":"CONTINUE_DATA_GAP","next_action":"local canonical reconciliation and exact-table recovery","terminal_status_line":STATUS})
    text("DATA_DICTIONARY.md","# Data dictionary\n\nAtomic cohort, paired effects, hierarchical synthesis, fracture modes, interval-censored damage, non-additive penalty budget and reference-aware counterexamples are provided. Compression and tension remain separate. Locator hashes are not original-byte hashes.\n")
    text("CITATION_MAP.md","# Evidence anchor map\n\n- Dispatch: file_library:turn0file0\n- QM08: hash-bound snapshot QM08_b15be66c1b7b8b35829f\n- Liu 2023: file_library:turn30file0\n- Jiao 2019: file_library:turn34file0\n- Bhuiyan 2017: file_library:turn35file14\n- Wang 2025: file_library:turn32file0\n- TiC/TA15: file_library:turn7file14\n")
    text("OPENED_FILES.txt","\n".join([x[0] for x in ARCHIVES]+["QM36 MDU","QM08 executive verdict","Liu 2023 original","Jiao 2019 original","Bhuiyan 2017 original","Wang 2025 original","TiC/TA15 source"])+"\n")
    text("requirements.txt","matplotlib==3.10.3\n")
    text("acceptance_commands.md","# Acceptance commands\n\n```bash\npython tests/test_qm36_outputs.py .\npython plot_code/plot_fracture_mode_probability.py\npython plot_code/plot_el_penalty_waterfall.py\npython plot_code/plot_hardening_damage_map.py\npython plot_code/plot_synergy_counterexample_cards.py\nsha256sum -c CHECKSUMS.sha256\n```\n")
    text("README.md",f"# FINAL_QM36\n\n22-paper/64-comparison primary synthesis; 34 direct atomic mechanism rows; 27 reconstructed pairs; four reproducible figure groups. No production/Gold action.\n\n{STATUS}\n")

    test=r'''import csv,hashlib,json,sys\nfrom pathlib import Path\nR=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]\ndef rows(n):\n with (R/n).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))\ndef req(x,m):\n if not x:raise AssertionError(m)\ndef sha(p):\n h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()\nrequired=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256","FRACTURE_MODE_LEDGER.csv","DUCTILITY_PENALTY_BUDGET.csv","DAMAGE_INITIATION.csv","SYNERGY_COUNTEREXAMPLES.csv"]\nfor n in required:req((R/n).is_file(),"missing "+n)\nc=rows("ANALYSIS_COHORT.csv"); req(len(c)==34,"atomic rows"); req(len({x["row_uid"] for x in c})==34,"uid collision"); req(len({x["paper_uid"] for x in c})==5,"paper count")\np=rows("PAIR_MATCHES.csv"); req(len(p)==27,"pair count")\nh=next(x for x in rows("HIERARCHICAL_RESULTS.csv") if x["result_id"]=="QM08_MATRIX_PRIMARY"); req(float(h["estimate"])==-8.06 and int(h["independent_papers"])==21,"primary changed")\nd=next(x for x in rows("DAMAGE_INITIATION.csv") if x["reported_strain_pct"]=="2.21"); req(d["onset_lower_pct"] in ["0","0.0"] and d["onset_upper_pct"]=="2.21","onset censoring")\nfor stem in ["QM36_F1_fracture_mode_probability","QM36_F2_el_penalty_waterfall","QM36_F3_hardening_damage_map","QM36_F4_synergy_counterexample_cards"]:\n for e in ["png","pdf","svg"]: req((R/"figures"/(stem+"."+e)).stat().st_size>1000,"figure "+stem+e)\nreq(not list(R.rglob("*.zip")),"nested zip")\nfor line in (R/"CHECKSUMS.sha256").read_text().splitlines():\n exp,rel=line.split("  ",1); req(sha(R/rel)==exp,"checksum "+rel)\nman=json.loads((R/"MANIFEST.json").read_text()); actual={x.relative_to(R).as_posix() for x in R.rglob("*") if x.is_file() and x.name not in ["MANIFEST.json","CHECKSUMS.sha256"]}; req({x["path"] for x in man["files"]}==actual,"manifest coverage")\nreq((R/"00_EXECUTIVE_VERDICT.md").read_text().rstrip().endswith("NEXT=local_absorb_and_recompute"),"status")\nprint(json.dumps({"pass":True,"atomic_rows":34,"direct_pairs":27,"figure_groups":4,"status":"PASS"}))\n'''
    text("tests/test_qm36_outputs.py",test)
    jwrite("VALIDATION_REPORT.json",{"window_id":WINDOW,"snapshot_id":snapshot,"atomic_rows":len(cohort),"direct_pairs":len(pairs),"effects":len(effects),"figure_groups":4,"nested_zip_count":0,"primary_estimand_reproduced":True,"claim_ceiling_enforced":True,"status":"PASS_PRE_MANIFEST"})
    text("RUN_LOG.txt",datetime.now(timezone.utc).isoformat()+" build and figures complete\n")

    payload=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in ["MANIFEST.json","CHECKSUMS.sha256"])
    jwrite("MANIFEST.json",{"window_id":WINDOW,"snapshot_id":snapshot,"generated_at":datetime.now(timezone.utc).isoformat(),"nested_zip_count":0,"file_count_excluding_manifest_and_checksums":len(payload),"total_payload_bytes":sum(p.stat().st_size for p in payload),"files":[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha_file(p)} for p in payload]})
    targets=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name!="CHECKSUMS.sha256")
    text("CHECKSUMS.sha256","".join(f"{sha_file(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in targets))
    print(json.dumps({"window":WINDOW,"snapshot":snapshot,"rows":len(cohort),"pairs":len(pairs),"files":len(list(ROOT.rglob('*'))),"status":"BUILT"}))

if __name__=="__main__": build()
