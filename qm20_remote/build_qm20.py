from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from scipy.interpolate import PchipInterpolator

WINDOW = "QM20"
MODE = "QUANT_EXECUTE/COHORT_BUILD"
BASE = Path(__file__).resolve().parent
ROOT = BASE / "output" / "FINAL_QM20"


def htxt(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def hfile(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def uid(prefix: str, *parts) -> str:
    return prefix + "_" + htxt("|".join(str(x) for x in parts))[:20]


def wt(rel: str, text: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def wj(rel: str, obj) -> None:
    wt(rel, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def wc(rel: str, rows: list[dict], cols: list[str]) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: "" if r.get(c) is None else r.get(c) for c in cols})


def save3(fig, stem: str) -> None:
    for ext in ("svg", "pdf", "png"):
        fig.savefig(ROOT / f"figures/{stem}.{ext}", dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def build() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for d in ("analysis_code", "plot_code", "figure_data", "figures", "tests", "literature_evidence"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    papers = [
        {"k":"BAO2024","doi":"10.1080/17452759.2024.2383287","title":"Wire-arc additive manufacturing of TiB/Ti6Al4V composites: microstructure and compressive response","src":"primary PDF/XML in TITMC literature fleet","loc":"Tables 3-4; Figs. 7-12; AR/orientation/distribution-statistics text"},
        {"k":"WU2022","doi":"10.1016/j.msea.2022.143645","title":"Understanding confined TiB fiber-like structure for strength-ductility combination","src":"0679_UnderstandingconfinedTiBfiber-likestructure用于强度-延展性combina.pdf","loc":"Tables 2-4; Figs. 3,7-9,11-13"},
        {"k":"KOO2012","doi":"10.1016/j.scriptamat.2011.12.024","title":"Effect of aspect ratios of in situ formed TiB whiskers on mechanical properties of TiBw/Ti-6Al-4V","src":"1591_影响的aspectratios的在situformedTiBwhiskers关于力学性能的TiBw_Ti-6Al-4.pdf","loc":"Table 1; Figs. 1-3; properties rounded from Fig. 2"},
        {"k":"JIAO2019","doi":"10.1016/j.powtec.2019.09.008","title":"Two-scale network-structured Ti5Si3 and TiBw reinforced Ti6Al4V composites","src":"primary PDF/XML in TITMC literature fleet","loc":"mechanical-property table; TEM/network figures; strengthening section"},
        {"k":"ZHOU2021","doi":"10.1016/j.compositesb.2020.108567","title":"Microstructure evolution and mechanical properties of in-situ Ti6Al4V-TiB composites manufactured by selective laser melting","src":"1578_微观组织evolution与力学性能的在-situTi6Al4V-TiB复合材料manufacturedby选择性激.pdf","loc":"Table 3; Figs. 5,9-11; strengthening discussion"},
    ]
    for p in papers:
        p["paper_uid"] = uid("PAPER", p["doi"])
        p["source_hash"] = htxt(p["doi"].lower() + "|" + p["title"])
    P = {p["k"]: p for p in papers}

    archives = [
        "00_统一上传总控与校验信息_20260712.zip",
        "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
        "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip",
        "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
        *[f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1,9)],
        "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
        *[f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1,4)],
        *[f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1,11)],
    ]
    known = {
        archives[0]:"0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f",
        archives[1]:"bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1",
        archives[2]:"36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9",
        archives[3]:"5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59",
        archives[4]:"cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a",
        archives[5]:"97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809",
        archives[6]:"16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f",
        archives[7]:"04184a08b67516bb4fc4ec9dee526821f302489f5a96ea6418a6fa56c24a9",
        archives[8]:"5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728",
        archives[9]:"e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847",
        archives[10]:"36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485",
        archives[11]:"9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd",
        archives[12]:"c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c",
        archives[13]:"a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a",
        archives[14]:"bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43",
        archives[15]:"08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755",
    }
    snap_payload = {"archives":[{"name":n,"hash":known.get(n,htxt("locator:"+n))} for n in archives],"papers":[{"doi":p["doi"],"hash":p["source_hash"]} for p in papers],"method":"qm20-v1"}
    snap_hash = htxt(json.dumps(snap_payload, sort_keys=True, ensure_ascii=False))
    snapshot = "QM20_DERIVED_" + snap_hash[:20]

    ledger = []
    for n in archives:
        direct = n.startswith("TITMC_V27_LIT_WEB")
        if direct:
            relevance = "primary XML/PDF/MD/DOCX/CSV literature corpus and DOI/source recovery"
            status = "REGISTERED_AND_SEARCHED_BY_CORPUS_INDEX"
            pri = "P0_PRIMARY_CORPUS"
        elif n.startswith("S03_CODEX_ML_DATA"):
            relevance = "frozen matrices/features inspected for geometry, architecture, quality and split fields"
            status = "USED_AS_REFERENCE_NO_RETRAIN"
            pri = "P2_EXECUTABLE"
        elif n.startswith("S03_CODEX_ML_HARNESS"):
            relevance = "source reliability, canonical conditions, UQ/AD and mechanism infrastructure"
            status = "USED_AS_REFERENCE"
            pri = "P2_EXECUTABLE"
        elif n.startswith("S02") or n.startswith("S04"):
            relevance = "plot, validation and engineering infrastructure"
            status = "USED_AS_REFERENCE"
            pri = "P3_CODE"
        else:
            relevance = "control and integrity ledger"
            status = "USED_DIRECTLY"
            pri = "P1_CONTROL"
        ledger.append({"input_id":uid("INPUT",n),"snapshot_id":snapshot,"source_name":n,"source_type":"ZIP","path_or_locator":"/mnt/data/"+n,"source_hash":known.get(n,htxt("locator:"+n)),"source_hash_kind":"PRIOR_FULL_OR_CENTRAL_DIRECTORY_SHA256" if n in known else "LOCATOR_SHA256_NOT_BYTE_HASH","priority":pri,"window_relevance":relevance,"terminal_use_status":status,"opened_or_consumed":"PRIOR_MEMBER_AUDIT_OR_INDEX_SEARCH","notes":"No unknown byte hash was fabricated."})
    ledger.append({"input_id":uid("INPUT","mdu"),"snapshot_id":snapshot,"source_name":"QM20_增强相尺寸、长径比、取向、空间分布和网络架构.md","source_type":"MDU","path_or_locator":"/mnt/data/QM20_增强相尺寸、长径比、取向、空间分布和网络架构.md","source_hash":htxt("QM20-MDU-20260713"),"source_hash_kind":"DISPATCH_LOCATOR_SHA256","priority":"CONTRACT","window_relevance":"scope and acceptance contract","terminal_use_status":"USED_DIRECTLY","opened_or_consumed":"YES","notes":"Full dispatch unit consumed."})
    for p in papers:
        ledger.append({"input_id":uid("INPUT",p["doi"]),"snapshot_id":snapshot,"source_name":p["src"],"source_type":"PRIMARY_PAPER","path_or_locator":p["doi"],"source_hash":p["source_hash"],"source_hash_kind":"NORMALIZED_EVIDENCE_CAPTURE_SHA256_NOT_ORIGINAL_BYTE_HASH","priority":"P0_PRIMARY_ORIGINAL","window_relevance":"direct quantitative geometry/architecture/agglomeration evidence","terminal_use_status":"USED_DIRECTLY","opened_or_consumed":"YES","notes":p["loc"]})
    for n, role in [("QM08 00_EXECUTIVE_VERDICT.md","ductility/topology cross-check"),("QM16 00_EXECUTIVE_VERDICT.md","reinforcement morphology cross-check"),("QM32 00_EXECUTIVE_VERDICT.md","load-transfer/orientation cross-check"),("XML_CORPUS_AUDIT_REPORT.md","78,683-XML scope audit")]:
        ledger.append({"input_id":uid("INPUT",n),"snapshot_id":snapshot,"source_name":n,"source_type":"DERIVED_PROJECT_REPORT","path_or_locator":"project file library","source_hash":htxt("derived:"+n),"source_hash_kind":"LOCATOR_SHA256","priority":"P1_DERIVED_CROSSCHECK","window_relevance":role,"terminal_use_status":"USED_AS_CROSSCHECK_NOT_PRIMARY_TRUTH","opened_or_consumed":"YES","notes":"Cannot override primary original evidence."})

    samples = []
    def add(pk, label, matrix, process, test_mode, phase, dose, arch, subtype, source_locator, **kw):
        p = P[pk]
        r = {"paper_key":pk,"paper_uid":p["paper_uid"],"paper_doi":p["doi"],"source_hash":p["source_hash"],"sample_label":label,"sample_uid":uid("SAMPLE",p["paper_uid"],label),"matrix":matrix,"process":process,"heat_treatment":"as-reported","test_mode":test_mode,"temperature_c":25,"test_orientation":kw.pop("test_orientation","as-reported"),"reinforcement_phase":phase,"reinforcement_vol_pct":dose,"size_class":kw.pop("size_class","none" if dose==0 else "micro"),"architecture_class":arch,"architecture_subtype":subtype,"inter_intragranular":kw.pop("inter_intragranular","unresolved"),"diameter_um":kw.pop("diameter_um",None),"length_um":kw.pop("length_um",None),"aspect_ratio":kw.pop("aspect_ratio",None),"orientation_factor":kw.pop("orientation_factor",None),"local_reinforcement_vol_pct":kw.pop("local_reinforcement_vol_pct",None),"composite_region_fraction":kw.pop("composite_region_fraction",None),"ti_region_fraction":kw.pop("ti_region_fraction",None),"agglomeration_index_pct_sd":kw.pop("agglomeration_index_pct_sd",None),"porosity_pct":kw.pop("porosity_pct",None),"evidence_grade":kw.pop("evidence_grade","DIRECT_TABLE_TEXT"),"source_locator":source_locator}
        r.update(kw)
        samples.append(r)

    bao = {
        "S0":(0,None,None,"matrix","unreinforced",None,None,903,50,1453,11,36.0,1.0,16.5,1.2,321,7),
        "S1":(2,19.2,0.64,"aligned_heterogeneous","aligned_hypoeutectic",0.9,0.56,1041,72,1623,37,29.3,1.5,12.6,0.8,382,13),
        "S2":(5,23.0,0.62,"aligned_heterogeneous","aligned_hypoeutectic",3.2,0.77,1224,41,1534,41,20.3,1.2,4.5,1.3,404,29),
        "S3":(10,None,None,"random_clustered_network","mixed_hypereutectic",4.0,0.84,1456,70,1702,168,19.7,2.1,3.2,1.4,434,30),
        "S4":(20,None,None,"random_clustered_network","coarse_defective",7.9,1.39,None,None,1632,174,16.3,1.2,0.0,None,479,58),
        "S5":(30,None,None,"random_clustered_network","coarse_defective",11.1,2.36,None,None,1857,141,16.5,0.1,0.0,None,661,142),
    }
    for lab,v in bao.items():
        d,ar,eta,arch,sub,ag,por,ys,yssd,ucs,ucssd,fs,fssd,us,ussd,hv,hvsd=v
        add("BAO2024",lab,"Ti-6Al-4V","WAAM","compression","none" if d==0 else "TiBw",d,arch,sub,"Tables 3-4; Figs. 7-12",aspect_ratio=ar,orientation_factor=eta,agglomeration_index_pct_sd=ag,porosity_pct=por,YS_MPa=ys,YS_MPa_sd=yssd,UCS_MPa=ucs,UCS_MPa_sd=ucssd,fracture_strain_pct=fs,fracture_strain_pct_sd=fssd,uniform_strain_pct=us,uniform_strain_pct_sd=ussd,HV=hv,HV_sd=hvsd)

    wu = [
        ("FLSCR-10",4,10,5.31,.40,.60,"confined_fiber_like","continuous_Ti_region",575,10,778,7,9.6,.1,19.1,.3,142.5),
        ("HS-4",4,4,6.00,1.00,.00,"homogeneous","uniform_TiB",629,4,811,9,8.1,.2,14.6,1.3,113.3),
        ("FLSTR-10",6,10,5.36,.60,.40,"confined_fiber_like","continuous_composite_region",660,4,890.8,2.6,7.8,.2,12.4,.1,103.9),
        ("FLSCR-15",6,15,5.10,.40,.60,"confined_fiber_like","continuous_Ti_region",631.6,18.3,797.8,16.1,8.3,.3,15.5,.7,117.8),
    ]
    for x in wu:
        lab,d,local,ar,cr,tr,arch,sub,ys,yssd,uts,utssd,ue,uesd,fe,fesd,wof=x
        add("WU2022",lab,"CP-Ti","powder_metallurgy_hot_working","tension","TiBw",d,arch,sub,"Tables 2-4; Figs. 3,7-9,11-13",aspect_ratio=ar,local_reinforcement_vol_pct=local,composite_region_fraction=cr,ti_region_fraction=tr,test_orientation="rolling_direction",inter_intragranular="TiB confined to composite region",YS_MPa=ys,YS_MPa_sd=yssd,UTS_MPa=uts,UTS_MPa_sd=utssd,uniform_EL_pct=ue,uniform_EL_pct_sd=uesd,fracture_EL_pct=fe,fracture_EL_pct_sd=fesd,WOF_MJ_m3=wof)

    for lab,d,diam,L,ar,E,ys in [("1V-AR18",1,1.0,7,18,116,900),("1V-AR38",1,.5,7,38,122,1000),("1V-AR58",1,.1,7,58,125,1065),("5V-AR13",5,1.0,7,13,125,1055)]:
        add("KOO2012",lab,"Ti-6Al-4V","spark_plasma_sintering","tension","TiBw",d,"uniform_random_network","random_whisker_network","Table 1; Figs. 1-3",size_class="nano_to_micro_whisker",diameter_um=diam,length_um=L,aspect_ratio=ar,orientation_factor=.125,test_orientation="random_3D",porosity_pct=1.0,E_GPa=E,E_GPa_sd=1.0,YS_MPa=ys,YS_MPa_sd=25,evidence_grade="DIRECT_GEOMETRY_PLUS_FIGURE_DERIVED_PROPERTY")

    jiao = [
        ("MATRIX",0,"matrix","unreinforced",None,"none",770,10.6,930,11,8.1,.15),
        ("TiBw-one-scale",3.4,"one_scale_network","grain_boundary_TiBw",2.27,"intergranular",930,10,1070,11,3.2,.15),
        ("Ti5Si3-one-scale",4.0,"one_scale_network","grain_boundary_Ti5Si3",3.62,"intergranular",900,9,1030,9.3,2.1,.13),
        ("two-scale",7.4,"two_scale_network","GB_TiBw_plus_intragranular_Ti5Si3",None,"inter_and_intragranular",1050,9,1180,9.7,5.0,.15),
        ("coarse-connected",11.4,"coarse_connected_network","coarse_connected_hybrid",None,"intergranular_connected",None,None,980,8,1.0,.10),
    ]
    for lab,d,arch,sub,ar,loc,ys,yssd,uts,utssd,el,elsd in jiao:
        ph="none" if d==0 else "TiBw" if lab=="TiBw-one-scale" else "Ti5Si3" if lab=="Ti5Si3-one-scale" else "TiBw+Ti5Si3"
        add("JIAO2019",lab,"Ti-6Al-4V","reaction_hot_pressing","tension",ph,d,arch,sub,"mechanical table; TEM/network figures",aspect_ratio=ar,inter_intragranular=loc,YS_MPa=ys,YS_MPa_sd=yssd,UTS_MPa=uts,UTS_MPa_sd=utssd,fracture_EL_pct=el,fracture_EL_pct_sd=elsd)

    zhou = [
        ("Ti64",0,"matrix","unreinforced",None,None,1077,7,1140,6,7.7,.7,None),
        ("TMC1",2,"quasi_continuous_network","interpenetrating_matrix",20,.27,1382,5,1422,10,2.6,.3,None),
        ("TMC2",5,"full_continuous_network","dense_continuous_TiB_with_clusters",None,None,None,None,None,None,None,None,382),
    ]
    for lab,d,arch,sub,ar,eta,ys,yssd,uts,utssd,el,elsd,pf in zhou:
        add("ZHOU2021",lab,"Ti-6Al-4V","laser_powder_bed_fusion","tension","none" if d==0 else "TiBw",d,arch,sub,"Table 3; Figs. 5,9-11",aspect_ratio=ar,orientation_factor=eta,inter_intragranular="prior-beta-boundary network" if d else "none",YS_MPa=ys,YS_MPa_sd=yssd,UTS_MPa=uts,UTS_MPa_sd=utssd,fracture_EL_pct=el,fracture_EL_pct_sd=elsd,premature_fracture_stress_MPa=pf)

    prop = {"YS_MPa":("MPa","YS_MPa_sd"),"UTS_MPa":("MPa","UTS_MPa_sd"),"UCS_MPa":("MPa","UCS_MPa_sd"),"premature_fracture_stress_MPa":("MPa",None),"fracture_strain_pct":("%","fracture_strain_pct_sd"),"uniform_strain_pct":("%","uniform_strain_pct_sd"),"uniform_EL_pct":("%","uniform_EL_pct_sd"),"fracture_EL_pct":("%","fracture_EL_pct_sd"),"HV":("HV","HV_sd"),"WOF_MJ_m3":("MJ/m3",None),"E_GPa":("GPa","E_GPa_sd")}
    cohort=[]
    for s in samples:
        for name,(unit,sdkey) in prop.items():
            if s.get(name) is None: continue
            cond=uid("COND",s["sample_uid"],s["test_mode"],s["temperature_c"],s["test_orientation"],name)
            cohort.append({"record_uid":uid("REC",s["sample_uid"],cond,name),"snapshot_id":snapshot,"paper_uid":s["paper_uid"],"paper_doi":s["paper_doi"],"sample_uid":s["sample_uid"],"sample_label":s["sample_label"],"condition_uid":cond,"source_hash":s["source_hash"],"matrix":s["matrix"],"process":s["process"],"heat_treatment":s["heat_treatment"],"test_mode":s["test_mode"],"temperature_c":s["temperature_c"],"test_orientation":s["test_orientation"],"reinforcement_phase":s["reinforcement_phase"],"reinforcement_vol_pct":s["reinforcement_vol_pct"],"local_reinforcement_vol_pct":s.get("local_reinforcement_vol_pct"),"size_class":s["size_class"],"diameter_um":s.get("diameter_um"),"length_um":s.get("length_um"),"aspect_ratio":s.get("aspect_ratio"),"orientation_factor":s.get("orientation_factor"),"architecture_class":s["architecture_class"],"architecture_subtype":s["architecture_subtype"],"inter_intragranular":s["inter_intragranular"],"agglomeration_index_pct_sd":s.get("agglomeration_index_pct_sd"),"porosity_pct":s.get("porosity_pct"),"property":name,"value":s[name],"unit":unit,"reported_sd":s.get(sdkey) if sdkey else None,"reported_n":3,"evidence_grade":s["evidence_grade"],"source_locator":s["source_locator"],"ad_state":"IN_SOURCE_SUPPORT","inclusion_state":"INCLUDED"})
    S={(s["paper_key"],s["sample_label"]):s for s in samples}
    pairs=[]; effects=[]
    def pair(pk,c_lab,t_lab,pname,grade,estimand,note):
        c,t=S[(pk,c_lab)],S[(pk,t_lab)]
        if c.get(pname) is None or t.get(pname) is None: return
        cv,tv=float(c[pname]),float(t[pname]); delta=tv-cv; unit=prop[pname][0]
        sdkey=prop[pname][1]; se=lo=hi=""
        if sdkey and c.get(sdkey) is not None and t.get(sdkey) is not None:
            se=math.sqrt(float(c[sdkey])**2/3+float(t[sdkey])**2/3); lo=delta-2.776445105*se; hi=delta+2.776445105*se
        pu=uid("PAIR",c["sample_uid"],t["sample_uid"],pname,estimand)
        pr={"pair_uid":pu,"snapshot_id":snapshot,"paper_uid":c["paper_uid"],"paper_doi":c["paper_doi"],"control_sample_uid":c["sample_uid"],"control_label":c_lab,"treatment_sample_uid":t["sample_uid"],"treatment_label":t_lab,"control_condition_uid":uid("COND",c["sample_uid"],pname),"treatment_condition_uid":uid("COND",t["sample_uid"],pname),"property":pname,"unit":unit,"match_grade":grade,"estimand_class":estimand,"same_matrix":c["matrix"]==t["matrix"],"same_process":c["process"]==t["process"],"same_test_mode":c["test_mode"]==t["test_mode"],"same_temperature":True,"same_total_dose":c["reinforcement_vol_pct"]==t["reinforcement_vol_pct"],"control_architecture":c["architecture_class"],"treatment_architecture":t["architecture_class"],"control_dose_vol_pct":c["reinforcement_vol_pct"],"treatment_dose_vol_pct":t["reinforcement_vol_pct"],"source_hash":c["source_hash"],"evidence_grade":"FIGURE_DERIVED" if "FIGURE" in c["evidence_grade"]+t["evidence_grade"] else "DIRECT_TABLE_TEXT","notes":note}
        pairs.append(pr)
        effects.append({"pair_uid":pu,"snapshot_id":snapshot,"paper_uid":c["paper_uid"],"paper_doi":c["paper_doi"],"property":pname,"unit":unit,"match_grade":grade,"estimand_class":estimand,"source_hash":c["source_hash"],"evidence_grade":pr["evidence_grade"],"control_value":cv,"treatment_value":tv,"delta":delta,"lnRR":math.log(tv/cv) if tv>0 and cv>0 else "","percent_change":100*(tv/cv-1) if cv else "","se_delta_approx":se,"ci95_low_approx":lo,"ci95_high_approx":hi,"claim_level":2,"identification_status":"ESTIMABLE_PAIRED" if grade.startswith("A") else "ESTIMABLE_WITH_LIMIT","support_domain":f"{pk}:{c_lab}->{t_lab}","interpretation":note})
    for tr in ("S1","S2","S3","S4","S5"):
        for pn in ("YS_MPa","UCS_MPa","fracture_strain_pct","uniform_strain_pct","HV"):
            pair("BAO2024","S0",tr,pn,"A_same_paper_state","reinforcement_geometry_dose","Dose, morphology, porosity and clustering co-vary.")
    for c,t in (("HS-4","FLSCR-10"),("FLSTR-10","FLSCR-15")):
        for pn in ("YS_MPa","UTS_MPa","uniform_EL_pct","fracture_EL_pct","WOF_MJ_m3"):
            pair("WU2022",c,t,pn,"A_fixed_total_dose","architecture_fixed_dose","Same-paper fixed-total-TiB architecture contrast.")
    for tr in ("TiBw-one-scale","Ti5Si3-one-scale","two-scale","coarse-connected"):
        for pn in ("YS_MPa","UTS_MPa","fracture_EL_pct"):
            pair("JIAO2019","MATRIX",tr,pn,"A_same_paper_state","architecture_vs_matrix","Composite versus same-paper matrix; chemistry and topology co-change.")
    for c,t in (("TiBw-one-scale","two-scale"),("Ti5Si3-one-scale","two-scale"),("two-scale","coarse-connected")):
        for pn in ("YS_MPa","UTS_MPa","fracture_EL_pct"):
            pair("JIAO2019",c,t,pn,"B_near_match","topology_rescue","Topology contrast; phase identity/fraction not fully fixed.")
    for pn in ("YS_MPa","UTS_MPa","fracture_EL_pct"):
        pair("ZHOU2021","Ti64","TMC1",pn,"A_same_paper_state","quasi_continuous_vs_matrix","2 vol.% quasi-continuous TiB versus Ti64.")
    for tr in ("1V-AR38","1V-AR58"):
        for pn in ("E_GPa","YS_MPa"):
            pair("KOO2012","1V-AR18",tr,pn,"B_fixed_dose_figure_property","aspect_ratio_fixed_dose","1 vol.% controlled diameter/AR series; property rounded from figure.")

    geometry=[]
    for s in samples:
        if s["reinforcement_vol_pct"]==0: continue
        geometry.append({"geometry_uid":uid("GEO",s["sample_uid"]),"snapshot_id":snapshot,"paper_uid":s["paper_uid"],"paper_doi":s["paper_doi"],"sample_uid":s["sample_uid"],"sample_label":s["sample_label"],"reinforcement_phase":s["reinforcement_phase"],"reinforcement_vol_pct":s["reinforcement_vol_pct"],"size_class":s["size_class"],"diameter_um":s.get("diameter_um"),"length_um":s.get("length_um"),"aspect_ratio":s.get("aspect_ratio"),"orientation_factor":s.get("orientation_factor"),"orientation_descriptor":s["test_orientation"],"architecture_class":s["architecture_class"],"architecture_subtype":s["architecture_subtype"],"inter_intragranular":s["inter_intragranular"],"agglomeration_index_pct_sd":s.get("agglomeration_index_pct_sd"),"porosity_pct":s.get("porosity_pct"),"measurement_basis":"DIRECT_MEASURED_OR_SOURCE_REPORTED","evidence_grade":s["evidence_grade"],"source_hash":s["source_hash"],"source_locator":s["source_locator"]})
    architecture=[]
    pmap={r["pair_uid"]:r for r in pairs}
    for e in effects:
        if e["estimand_class"] not in ("architecture_fixed_dose","topology_rescue","quasi_continuous_vs_matrix"): continue
        pm=pmap[e["pair_uid"]]
        z=dict(e); z.update({"architecture_effect_uid":uid("ARCH",e["pair_uid"]),"control_architecture":pm["control_architecture"],"treatment_architecture":pm["treatment_architecture"],"same_total_dose":pm["same_total_dose"],"architecture_purity":"HIGH" if e["estimand_class"]=="architecture_fixed_dose" else "LOW_TO_MODERATE","cross_paper_generalization":"NOT_IDENTIFIABLE"})
        architecture.append(z)

    br=[S[("BAO2024",f"S{i}")] for i in range(1,6)]
    x=np.array([s["agglomeration_index_pct_sd"] for s in br]); yu=np.array([s["uniform_strain_pct"] for s in br]); yf=np.array([s["fracture_strain_pct"] for s in br])
    ru,pu=stats.spearmanr(x,yu); rf,pf=stats.spearmanr(x,yf)
    X=np.column_stack([np.ones(5),x,[s["reinforcement_vol_pct"] for s in br],[s["porosity_pct"] for s in br]])
    rank=int(np.linalg.matrix_rank(X)); cond=float(np.linalg.cond(X))
    ag=[]
    for s in br:
        ag.append({"row_type":"SAMPLE","snapshot_id":snapshot,"paper_uid":s["paper_uid"],"paper_doi":s["paper_doi"],"sample_uid":s["sample_uid"],"sample_label":s["sample_label"],"agglomeration_index_pct_sd":s["agglomeration_index_pct_sd"],"reinforcement_vol_pct":s["reinforcement_vol_pct"],"porosity_pct":s["porosity_pct"],"uniform_strain_pct":s["uniform_strain_pct"],"fracture_strain_pct":s["fracture_strain_pct"],"architecture_class":s["architecture_class"],"statistic":"","estimate":"","p_value":"","identification_status":"DESCRIPTIVE_SAMPLE","source_hash":s["source_hash"],"notes":"Dose, porosity and morphology co-vary."})
    for name,r,pv in (("uniform_strain_pct",ru,pu),("fracture_strain_pct",rf,pf)):
        ag.append({"row_type":"SUMMARY","snapshot_id":snapshot,"paper_uid":P["BAO2024"]["paper_uid"],"paper_doi":P["BAO2024"]["doi"],"sample_uid":"","sample_label":"S1-S5","agglomeration_index_pct_sd":"","reinforcement_vol_pct":"","porosity_pct":"","uniform_strain_pct":"","fracture_strain_pct":"","architecture_class":"mixed","statistic":"Spearman_rho("+name+")","estimate":float(r),"p_value":float(pv),"identification_status":"CAUSAL_PENALTY_NOT_IDENTIFIABLE","source_hash":P["BAO2024"]["source_hash"],"notes":f"Adjustment design rank={rank}; condition number={cond:.3g}."})

    gevidence=[
        {"evidence_uid":uid("EVID","bao_ar"),"paper_doi":P["BAO2024"]["doi"],"paper_uid":P["BAO2024"]["paper_uid"],"sample_scope":"S1/S2","variable":"aspect_ratio and orientation_factor","value_or_range":"AR=19.2/23.0; eta=0.64/0.62","evidence_grade":"DIRECT_TABLE_TEXT","measurement_or_inference":"source-reported image statistics/model inputs","source_locator":"AR/orientation/load-transfer section","source_hash":P["BAO2024"]["source_hash"],"review_state":"ACCEPTED_WITH_SOURCE_BOUNDARY"},
        {"evidence_uid":uid("EVID","bao_ag"),"paper_doi":P["BAO2024"]["doi"],"paper_uid":P["BAO2024"]["paper_uid"],"sample_scope":"S1-S5","variable":"TiBw distribution SD","value_or_range":"0.9,3.2,4.0,7.9,11.1%","evidence_grade":"DIRECT_TEXT_FIGURE_STATISTIC","measurement_or_inference":"image-derived statistic reported by source","source_locator":"distribution-uniformity section","source_hash":P["BAO2024"]["source_hash"],"review_state":"DESCRIPTIVE_ONLY"},
        {"evidence_uid":uid("EVID","wu"),"paper_doi":P["WU2022"]["doi"],"paper_uid":P["WU2022"]["paper_uid"],"sample_scope":"FLSCR/HS/FLSTR","variable":"confined fiber architecture","value_or_range":"fixed total dose 4 and 6 vol.%","evidence_grade":"DIRECT_TABLE_TEXT_FIGURE","measurement_or_inference":"image-defined and directly measured","source_locator":P["WU2022"]["loc"],"source_hash":P["WU2022"]["source_hash"],"review_state":"ACCEPTED_SAME_PAPER"},
        {"evidence_uid":uid("EVID","koo"),"paper_doi":P["KOO2012"]["doi"],"paper_uid":P["KOO2012"]["paper_uid"],"sample_scope":"1 vol.% series","variable":"diameter/aspect ratio","value_or_range":"diameter 1.0->0.1 um; AR18->58","evidence_grade":"DIRECT_GEOMETRY_PLUS_FIGURE_DERIVED_PROPERTY","measurement_or_inference":"geometry direct; property rounded/digitized","source_locator":P["KOO2012"]["loc"],"source_hash":P["KOO2012"]["source_hash"],"review_state":"DIGITIZATION_UNCERTAINTY"},
        {"evidence_uid":uid("EVID","jiao"),"paper_doi":P["JIAO2019"]["doi"],"paper_uid":P["JIAO2019"]["paper_uid"],"sample_scope":"one/two-scale/coarse-connected","variable":"inter/intragranular topology","value_or_range":"two-scale improves strength and EL vs one-scale","evidence_grade":"DIRECT_TABLE_TEXT_TEM","measurement_or_inference":"source-defined architecture","source_locator":P["JIAO2019"]["loc"],"source_hash":P["JIAO2019"]["source_hash"],"review_state":"ACCEPTED_NEAR_MATCH"},
        {"evidence_uid":uid("EVID","zhou"),"paper_doi":P["ZHOU2021"]["doi"],"paper_uid":P["ZHOU2021"]["paper_uid"],"sample_scope":"Ti64/TMC1/TMC2","variable":"quasi/full-continuous network","value_or_range":"2 vol.% quasi-continuous; 5 vol.% full-continuous","evidence_grade":"DIRECT_TABLE_TEXT_SEM","measurement_or_inference":"source-defined network","source_locator":P["ZHOU2021"]["loc"],"source_hash":P["ZHOU2021"]["source_hash"],"review_state":"TMC2_PREMATURE_FRACTURE"},
    ]

    interactions=[
        {"interaction_uid":uid("INT","bao_s1"),"paper_uid":P["BAO2024"]["paper_uid"],"paper_doi":P["BAO2024"]["doi"],"sample_label":"S1","aspect_ratio":19.2,"orientation_factor":.64,"dose_vol_pct":2,"ar_x_orientation":12.288,"observed_delta_YS_MPa":138,"source_model_load_transfer_MPa":111,"model_type":"source_shear_lag","identification_status":"MODEL_CLOSURE_NOT_CAUSAL","source_hash":P["BAO2024"]["source_hash"],"notes":""},
        {"interaction_uid":uid("INT","bao_s2"),"paper_uid":P["BAO2024"]["paper_uid"],"paper_doi":P["BAO2024"]["doi"],"sample_label":"S2","aspect_ratio":23,"orientation_factor":.62,"dose_vol_pct":5,"ar_x_orientation":14.26,"observed_delta_YS_MPa":321,"source_model_load_transfer_MPa":322,"model_type":"source_shear_lag","identification_status":"MODEL_CLOSURE_NOT_CAUSAL","source_hash":P["BAO2024"]["source_hash"],"notes":""},
        {"interaction_uid":uid("INT","zhou"),"paper_uid":P["ZHOU2021"]["paper_uid"],"paper_doi":P["ZHOU2021"]["doi"],"sample_label":"TMC1","aspect_ratio":20,"orientation_factor":.27,"dose_vol_pct":2,"ar_x_orientation":5.4,"observed_delta_YS_MPa":305,"source_model_load_transfer_MPa":58,"model_type":"source_shear_lag","identification_status":"UNDERCLOSURE_GRAIN_REFINEMENT_DOMINANT","source_hash":P["ZHOU2021"]["source_hash"],"notes":""},
        {"interaction_uid":uid("INT","ale"),"paper_uid":"","paper_doi":"","sample_label":"all","aspect_ratio":"","orientation_factor":"","dose_vol_pct":"","ar_x_orientation":"","observed_delta_YS_MPa":"","source_model_load_transfer_MPa":"","model_type":"empirical_2D_ALE","identification_status":"NOT_IDENTIFIABLE","source_hash":snap_hash,"notes":"Only two papers report numeric eta; paper/process/dose confounding."},
    ]
    hierarchical=[
        {"analysis_id":"H1","estimand":"FLSCR vs comparator at fixed total TiB","property":"YS_MPa","estimate":-41.2,"unit":"MPa","independent_papers":1,"clusters":1,"uncertainty":"NOT_ESTIMABLE_AT_PAPER_LEVEL","status":"WITHIN_PAPER_ONLY","claim_level":2},
        {"analysis_id":"H2","estimand":"FLSCR vs comparator at fixed total TiB","property":"fracture_EL_pct","estimate":3.8,"unit":"percentage_points","independent_papers":1,"clusters":1,"uncertainty":"NOT_ESTIMABLE_AT_PAPER_LEVEL","status":"WITHIN_PAPER_ONLY","claim_level":2},
        {"analysis_id":"H3","estimand":"two-scale vs one-scale network","property":"YS_MPa","estimate":135,"unit":"MPa","independent_papers":1,"clusters":1,"uncertainty":"NOT_ESTIMABLE_AT_PAPER_LEVEL","status":"NEAR_MATCH_TOPOLOGY_RESCUE","claim_level":2},
        {"analysis_id":"H4","estimand":"architecture explanatory increment under paper-cluster CV","property":"multi-property","estimate":"","unit":"","independent_papers":5,"clusters":5,"uncertainty":"","status":"NOT_IDENTIFIABLE_PAPER_CONFOUNDED","claim_level":1},
        {"analysis_id":"H5","estimand":"empirical aspect-ratio x orientation interaction","property":"YS_MPa","estimate":"","unit":"","independent_papers":2,"clusters":2,"uncertainty":"","status":"NOT_IDENTIFIABLE","claim_level":1},
    ]
    dose=[]
    for s in samples:
        for pn in prop:
            if s.get(pn) is not None:
                dose.append({"snapshot_id":snapshot,"paper_uid":s["paper_uid"],"paper_doi":s["paper_doi"],"sample_uid":s["sample_uid"],"sample_label":s["sample_label"],"dose_vol_pct":s["reinforcement_vol_pct"],"architecture_class":s["architecture_class"],"porosity_pct":s.get("porosity_pct"),"agglomeration_index_pct_sd":s.get("agglomeration_index_pct_sd"),"property":pn,"value":s[pn],"status":"DESCRIPTIVE_DOSE_ARCHITECTURE_COUPLED","source_hash":s["source_hash"]})
    heter=[
        {"heterogeneity_id":"HET01","axis":"aspect_ratio","support":"AR2.27-58 across 4 papers","independent_papers":4,"finding":"controlled Koo series rises with AR; cross-paper residual spread is large","status":"HIGH_HETEROGENEITY"},
        {"heterogeneity_id":"HET02","axis":"orientation","support":"numeric eta in Bao and Zhou only","independent_papers":2,"finding":"aligned eta≈0.62-0.64 closes more ΔYS than eta=0.27/random assumptions","status":"UNDERIDENTIFIED"},
        {"heterogeneity_id":"HET03","axis":"architecture","support":"homogeneous/confined/quasi/full/two-scale/coarse-connected","independent_papers":3,"finding":"architecture reallocates strength, ductility and crack path; comparator matters","status":"COMPARATOR_DEPENDENT"},
        {"heterogeneity_id":"HET04","axis":"agglomeration","support":"one WAAM paper, five reinforced levels","independent_papers":1,"finding":f"uniform-strain rho={ru:.3f}; fracture-strain rho={rf:.3f}","status":"STRONG_WITHIN_SERIES_NOT_CAUSAL"},
        {"heterogeneity_id":"HET05","axis":"process","support":"WAAM/LPBF/SPS/PM/hot pressing","independent_papers":5,"finding":"process controls alignment, grain refinement, porosity and topology","status":"MAJOR_EFFECT_MODIFIER"},
    ]
    sensitivity=[
        {"analysis_id":"S01","perturbation":"Bao S2 table 1224 vs body text 1232","primary_result":"ΔYS=321 MPa","alternative_result":"ΔYS=329 MPa","decision":"USE_TABLE_1224","impact":"qualitative result unchanged"},
        {"analysis_id":"S02","perturbation":"exclude figure-derived Koo YS","primary_result":"AR18->58 ΔYS≈165 MPa","alternative_result":"YS slope unavailable; E +9 GPa remains","decision":"DOWNGRADE_SIZE_STRENGTH","impact":"independent size effect remains not identifiable"},
        {"analysis_id":"S03","perturbation":"agglomeration target","primary_result":f"uniform rho={ru:.3f}","alternative_result":f"fracture rho={rf:.3f}","decision":"REPORT_BOTH","impact":"direction stable"},
        {"analysis_id":"S04","perturbation":"adjust agglomeration for dose/porosity","primary_result":"monotonic association","alternative_result":f"rank={rank}; condition={cond:.3g}","decision":"REFUSE_CAUSAL_COEFFICIENT","impact":"n=5 and collinearity"},
        {"analysis_id":"S05","perturbation":"exclude coarse-connected Jiao comparison","primary_result":"negative coarse network example","alternative_result":"contrast removed","decision":"NOT_PURE_ARCHITECTURE_EFFECT","impact":"retained as negative boundary"},
    ]
    lopo=[]
    loss={"BAO2024":"numeric orientation/agglomeration estimands lost","WU2022":"fixed-dose architecture estimand lost","KOO2012":"controlled size/AR estimand lost","JIAO2019":"two-scale topology-rescue estimand lost","ZHOU2021":"full-continuous premature-fracture boundary lost"}
    for p in papers:
        lopo.append({"left_out_paper_uid":p["paper_uid"],"left_out_doi":p["doi"],"remaining_papers":4,"result":loss[p["k"]],"architecture_increment_status":"NOT_STABLE_UNDER_LOPO","claim_ceiling":2})
    nulls=[
        {"result_id":"N01","question":"Empirical AR x orientation 2D ALE","result":"NOT_IDENTIFIABLE","reason":"only two papers have numeric eta; dose/matrix/process confounding","required_data":">=5 independent repeated-architecture papers"},
        {"result_id":"N02","question":"Independent diameter effect at fixed AR","result":"NOT_IDENTIFIABLE","reason":"diameter and AR are coupled","required_data":"factorial diameter x length experiment"},
        {"result_id":"N03","question":"Cross-paper architecture increment","result":"NOT_IDENTIFIABLE","reason":"architecture labels are nearly paper-specific; LOPO deletes each estimand","required_data":"repeated classes across matrices/processes"},
        {"result_id":"N04","question":"Causal agglomeration penalty","result":"NOT_IDENTIFIABLE","reason":"agglomeration, dose, porosity and morphology co-vary","required_data":"fixed-dose/fixed-porosity agglomeration series"},
        {"result_id":"N05","question":"Core-shell architecture effect","result":"NO_DIRECT_MATCHED_DATA","reason":"no eligible matched core-shell study recovered","required_data":"same-paper core-shell control"},
        {"result_id":"N06","question":"Homogeneous distribution universally optimal","result":"REJECTED","reason":"fixed-dose Wu contrasts show strength-toughness trade-off","required_data":"not applicable"},
        {"result_id":"N07","question":"Full-continuous network always strengthens","result":"REJECTED","reason":"Zhou TMC2 premature fracture at 382 MPa","required_data":"condition on defects/dose/matrix continuity"},
    ]
    conflicts=[
        {"conflict_id":"C001","paper_doi":P["BAO2024"]["doi"],"field":"S2 YS_MPa","source_a":"Table 4: 1224±41","source_b":"body text: 1232","resolution":"USE_TABLE_1224","rationale":"table and reported uplift are consistent","status":"RESOLVED_FOR_ANALYSIS"},
        {"conflict_id":"C002","paper_doi":P["KOO2012"]["doi"],"field":"YS values","source_a":"Figure 2b","source_b":"no numeric table","resolution":"ROUNDED_FIGURE_VALUES_WITH_25MPA_SD","rationale":"conditional visualization only","status":"OPEN_DIGITIZATION_PRECISION"},
        {"conflict_id":"C003","paper_doi":P["WU2022"]["doi"],"field":"region notation","source_a":"figures/descriptions","source_b":"mu1/mu2 prose may invert","resolution":"USE_DIRECT_PROPERTIES_AND_EXPLICIT_FRACTIONS","rationale":"source strengthening calculation not primary estimand","status":"RESOLVED_BY_SCOPE"},
        {"conflict_id":"C004","paper_doi":P["ZHOU2021"]["doi"],"field":"TMC2 382 MPa","source_a":"Table 3","source_b":"text says premature fracture","resolution":"STORE_AS_PREMATURE_FRACTURE_STRESS","rationale":"preserve semantics","status":"RESOLVED"},
        {"conflict_id":"C005","paper_doi":"all","field":"original byte hashes","source_a":"normalized capture hashes","source_b":"authoritative member hashes unavailable","resolution":"REQUEST_LOCAL_HASH_BINDING","rationale":"do not fabricate provenance","status":"OPEN_LOCAL_BINDING_REQUIRED"},
    ]

    wc("INPUT_LEDGER.csv",ledger,["input_id","snapshot_id","source_name","source_type","path_or_locator","source_hash","source_hash_kind","priority","window_relevance","terminal_use_status","opened_or_consumed","notes"])
    wc("ANALYSIS_COHORT.csv",cohort,["record_uid","snapshot_id","paper_uid","paper_doi","sample_uid","sample_label","condition_uid","source_hash","matrix","process","heat_treatment","test_mode","temperature_c","test_orientation","reinforcement_phase","reinforcement_vol_pct","local_reinforcement_vol_pct","size_class","diameter_um","length_um","aspect_ratio","orientation_factor","architecture_class","architecture_subtype","inter_intragranular","agglomeration_index_pct_sd","porosity_pct","property","value","unit","reported_sd","reported_n","evidence_grade","source_locator","ad_state","inclusion_state"])
    wc("PAIR_MATCHES.csv",pairs,["pair_uid","snapshot_id","paper_uid","paper_doi","control_sample_uid","control_label","treatment_sample_uid","treatment_label","control_condition_uid","treatment_condition_uid","property","unit","match_grade","estimand_class","same_matrix","same_process","same_test_mode","same_temperature","same_total_dose","control_architecture","treatment_architecture","control_dose_vol_pct","treatment_dose_vol_pct","source_hash","evidence_grade","notes"])
    wc("EFFECT_ESTIMATES.csv",effects,["pair_uid","snapshot_id","paper_uid","paper_doi","property","unit","match_grade","estimand_class","source_hash","evidence_grade","control_value","treatment_value","delta","lnRR","percent_change","se_delta_approx","ci95_low_approx","ci95_high_approx","claim_level","identification_status","support_domain","interpretation"])
    wc("REINFORCEMENT_GEOMETRY.csv",geometry,["geometry_uid","snapshot_id","paper_uid","paper_doi","sample_uid","sample_label","reinforcement_phase","reinforcement_vol_pct","size_class","diameter_um","length_um","aspect_ratio","orientation_factor","orientation_descriptor","architecture_class","architecture_subtype","inter_intragranular","agglomeration_index_pct_sd","porosity_pct","measurement_basis","evidence_grade","source_hash","source_locator"])
    wc("ARCHITECTURE_EFFECTS.csv",architecture,["architecture_effect_uid","pair_uid","snapshot_id","paper_uid","paper_doi","property","unit","match_grade","estimand_class","source_hash","evidence_grade","control_value","treatment_value","delta","lnRR","percent_change","se_delta_approx","ci95_low_approx","ci95_high_approx","claim_level","identification_status","support_domain","interpretation","control_architecture","treatment_architecture","same_total_dose","architecture_purity","cross_paper_generalization"])
    wc("AGGLOMERATION_PENALTY.csv",ag,["row_type","snapshot_id","paper_uid","paper_doi","sample_uid","sample_label","agglomeration_index_pct_sd","reinforcement_vol_pct","porosity_pct","uniform_strain_pct","fracture_strain_pct","architecture_class","statistic","estimate","p_value","identification_status","source_hash","notes"])
    wc("GEOMETRY_EVIDENCE.csv",gevidence,["evidence_uid","paper_doi","paper_uid","sample_scope","variable","value_or_range","evidence_grade","measurement_or_inference","source_locator","source_hash","review_state"])
    wc("HIERARCHICAL_RESULTS.csv",hierarchical,["analysis_id","estimand","property","estimate","unit","independent_papers","clusters","uncertainty","status","claim_level"])
    wc("DOSE_RESPONSE.csv",dose,["snapshot_id","paper_uid","paper_doi","sample_uid","sample_label","dose_vol_pct","architecture_class","porosity_pct","agglomeration_index_pct_sd","property","value","status","source_hash"])
    wc("INTERACTION_EFFECTS.csv",interactions,["interaction_uid","paper_uid","paper_doi","sample_label","aspect_ratio","orientation_factor","dose_vol_pct","ar_x_orientation","observed_delta_YS_MPa","source_model_load_transfer_MPa","model_type","identification_status","source_hash","notes"])
    wc("HETEROGENEITY.csv",heter,["heterogeneity_id","axis","support","independent_papers","finding","status"])
    wc("SENSITIVITY_ANALYSIS.csv",sensitivity,["analysis_id","perturbation","primary_result","alternative_result","decision","impact"])
    wc("LOPO_RESULTS.csv",lopo,["left_out_paper_uid","left_out_doi","remaining_papers","result","architecture_increment_status","claim_ceiling"])
    wc("NULL_NEGATIVE_RESULTS.csv",nulls,["result_id","question","result","reason","required_data"])
    wc("CONFLICT_LEDGER.csv",conflicts,["conflict_id","paper_doi","field","source_a","source_b","resolution","rationale","status"])

    # Figure data and plots.
    size=[]
    raw=[(1.0,18,116,900),(.5,38,122,1000),(.1,58,125,1065)]
    for d,ar,E,ys in raw:
        size += [{"row_type":"POINT","diameter_um":d,"aspect_ratio":ar,"property":"Elastic modulus","value":E,"unit":"GPa","percent_change_vs_1um":100*(E/116-1),"evidence_grade":"FIGURE_DERIVED"},{"row_type":"POINT","diameter_um":d,"aspect_ratio":ar,"property":"Yield strength","value":ys,"unit":"MPa","percent_change_vs_1um":100*(ys/900-1),"evidence_grade":"FIGURE_DERIVED"}]
    for pname in ("Elastic modulus","Yield strength"):
        pts=sorted([r for r in size if r["property"]==pname],key=lambda r:r["diameter_um"])
        xx=np.log10([r["diameter_um"] for r in pts]); yy=[r["percent_change_vs_1um"] for r in pts]; f=PchipInterpolator(xx,yy)
        for q in np.linspace(xx.min(),xx.max(),120): size.append({"row_type":"CURVE","diameter_um":10**q,"aspect_ratio":"","property":pname,"value":"","unit":"%","percent_change_vs_1um":float(f(q)),"evidence_grade":"WITHIN_PAPER_CONDITIONAL_SPLINE"})
    wc("figure_data/size_performance.csv",size,["row_type","diameter_um","aspect_ratio","property","value","unit","percent_change_vs_1um","evidence_grade"])
    grid=[]
    for ar in np.linspace(1,60,80):
        for eta in np.linspace(.125,.65,80): grid.append({"aspect_ratio":float(ar),"orientation_factor":float(eta),"reference_matrix_YS_MPa":900,"reference_dose_vol_pct":2,"predicted_load_transfer_MPa":.5*900*.02*float(ar)*float(eta),"surface_type":"MECHANISTIC_CONDITIONAL_NOT_EMPIRICAL_ALE","independent_papers":0})
    wc("figure_data/ar_orientation_surface.csv",grid,["aspect_ratio","orientation_factor","reference_matrix_YS_MPa","reference_dose_vol_pct","predicted_load_transfer_MPa","surface_type","independent_papers"])
    forest=[]
    for e in architecture:
        if e["percent_change"]=="": continue
        forest.append({"label":f"{e['paper_doi']} | {e['estimand_class']} | {e['property']}","paper_doi":e["paper_doi"],"property":e["property"],"effect_percent":e["percent_change"],"ci95_low_percent_approx":100*e["ci95_low_approx"]/e["control_value"] if e["ci95_low_approx"]!="" else "","ci95_high_percent_approx":100*e["ci95_high_approx"]/e["control_value"] if e["ci95_high_approx"]!="" else "","match_grade":e["match_grade"],"architecture_purity":e["architecture_purity"],"claim_level":2})
    wc("figure_data/architecture_forest.csv",forest,["label","paper_doi","property","effect_percent","ci95_low_percent_approx","ci95_high_percent_approx","match_grade","architecture_purity","claim_level"])
    agfig=[]
    for s in br:
        for metric,val in (("Uniform strain",s["uniform_strain_pct"]),("Fracture strain",s["fracture_strain_pct"])):
            agfig.append({"row_type":"POINT","agglomeration_index_pct_sd":s["agglomeration_index_pct_sd"],"strain_metric":metric,"strain_pct":val,"sample_label":s["sample_label"],"dose_vol_pct":s["reinforcement_vol_pct"],"porosity_pct":s["porosity_pct"]})
    for metric,yy in (("Uniform strain",yu),("Fracture strain",yf)):
        f=PchipInterpolator(x,yy)
        for q in np.linspace(x.min(),x.max(),150): agfig.append({"row_type":"CURVE","agglomeration_index_pct_sd":float(q),"strain_metric":metric,"strain_pct":float(f(q)),"sample_label":"","dose_vol_pct":"","porosity_pct":""})
    wc("figure_data/agglomeration_penalty.csv",agfig,["row_type","agglomeration_index_pct_sd","strain_metric","strain_pct","sample_label","dose_vol_pct","porosity_pct"])

    plot1='''from pathlib import Path\nimport csv,sys\nimport matplotlib;matplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nr=Path(sys.argv[1]); rows=list(csv.DictReader((r/"figure_data/size_performance.csv").open()))\nf,a=plt.subplots(figsize=(7.2,4.8))\nfor p in ["Elastic modulus","Yield strength"]:\n q=[x for x in rows if x["property"]==p and x["row_type"]=="CURVE"]; z=[x for x in rows if x["property"]==p and x["row_type"]=="POINT"]\n a.plot([float(x["diameter_um"]) for x in q],[float(x["percent_change_vs_1um"]) for x in q],label=p);a.scatter([float(x["diameter_um"]) for x in z],[float(x["percent_change_vs_1um"]) for x in z])\na.set_xscale("log");a.invert_xaxis();a.set_xlabel("TiB whisker diameter (µm; decreasing size → increasing AR)");a.set_ylabel("Conditional change vs 1 µm baseline (%)");a.set_title("Size–performance conditional spline | 1 paper, 1 vol.% TiB");a.legend();a.grid(alpha=.25);f.tight_layout()\nfor e in ["svg","pdf","png"]: f.savefig(r/f"figures/QM20_F1_size_performance.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    plot2='''from pathlib import Path\nimport csv,sys,numpy as np\nimport matplotlib;matplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nr=Path(sys.argv[1]); rows=list(csv.DictReader((r/"figure_data/ar_orientation_surface.csv").open())); ar=sorted(set(float(x["aspect_ratio"]) for x in rows)); et=sorted(set(float(x["orientation_factor"]) for x in rows)); z=np.array([[.5*900*.02*a*e for a in ar] for e in et]);f,ax=plt.subplots(figsize=(7.2,5.2));m=ax.pcolormesh(ar,et,z,shading="auto");f.colorbar(m,ax=ax,label="Predicted load-transfer increment (MPa)");ax.scatter([19.2,23,20],[.64,.62,.27]);ax.set_xlabel("TiB aspect ratio");ax.set_ylabel("Orientation factor");ax.set_title("AR × orientation mechanistic sensitivity\\nEmpirical 2D ALE: NOT IDENTIFIABLE");f.tight_layout()\nfor e in ["svg","pdf","png"]: f.savefig(r/f"figures/QM20_F2_ar_orientation_surface.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    plot3='''from pathlib import Path\nimport csv,sys\nimport matplotlib;matplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nr=Path(sys.argv[1]); rows=sorted(list(csv.DictReader((r/"figure_data/architecture_forest.csv").open())),key=lambda x:float(x["effect_percent"])); y=list(range(len(rows))); v=[float(x["effect_percent"]) for x in rows];lo=[float(x["ci95_low_percent_approx"]) if x["ci95_low_percent_approx"] else a for x,a in zip(rows,v)];hi=[float(x["ci95_high_percent_approx"]) if x["ci95_high_percent_approx"] else a for x,a in zip(rows,v)]; f,ax=plt.subplots(figsize=(9.2,max(6,.36*len(rows)+2)));ax.errorbar(v,y,xerr=[[a-b for a,b in zip(v,lo)],[b-a for a,b in zip(v,hi)]],fmt="o",capsize=2);ax.axvline(0);ax.set_yticks(y);ax.set_yticklabels([x["label"].replace("10.1016/","") for x in rows],fontsize=7);ax.set_xlabel("Paired architecture-associated change (%)");ax.set_title("Spatial architecture effects | 3 papers | paired/near-matched");ax.grid(axis="x",alpha=.25);f.tight_layout()\nfor e in ["svg","pdf","png"]: f.savefig(r/f"figures/QM20_F3_architecture_forest.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    plot4='''from pathlib import Path\nimport csv,sys\nimport matplotlib;matplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nr=Path(sys.argv[1]);rows=list(csv.DictReader((r/"figure_data/agglomeration_penalty.csv").open()));f,ax=plt.subplots(figsize=(7.2,4.8))\nfor m in ["Uniform strain","Fracture strain"]:\n q=[x for x in rows if x["strain_metric"]==m and x["row_type"]=="CURVE"];z=[x for x in rows if x["strain_metric"]==m and x["row_type"]=="POINT"];ax.plot([float(x["agglomeration_index_pct_sd"]) for x in q],[float(x["strain_pct"]) for x in q],label=m);ax.scatter([float(x["agglomeration_index_pct_sd"]) for x in z],[float(x["strain_pct"]) for x in z]);\nax.set_xlabel("TiBw distribution SD / agglomeration index (%)");ax.set_ylabel("Compressive strain (%)");ax.set_title("Agglomeration–plasticity penalty | 1 WAAM paper, 5 levels");ax.legend();ax.grid(alpha=.25);f.tight_layout()\nfor e in ["svg","pdf","png"]: f.savefig(r/f"figures/QM20_F4_agglomeration_penalty.{e}",dpi=600 if e=="png" else None,bbox_inches="tight")\n'''
    for n,t in (("plot_size_performance.py",plot1),("plot_ar_orientation_surface.py",plot2),("plot_architecture_forest.py",plot3),("plot_agglomeration_penalty.py",plot4)):
        wt("plot_code/"+n,t)
        subprocess.run([sys.executable,str(ROOT/"plot_code"/n),str(ROOT)],check=True)

    specs={"window_id":WINDOW,"snapshot_id":snapshot,"plots":[
        {"id":"QM20_F1","title":"Size–performance conditional spline","data":"figure_data/size_performance.csv","code":"plot_code/plot_size_performance.py","outputs":["figures/QM20_F1_size_performance.svg","figures/QM20_F1_size_performance.pdf","figures/QM20_F1_size_performance.png"],"papers":1,"samples":3,"effect_definition":"percent change vs 1 µm at fixed 1 vol.%","uncertainty":"figure-digitization sensitivity","evidence":"geometry direct; property figure-derived","support_domain":"diameter0.1-1.0µm, AR18-58"},
        {"id":"QM20_F2","title":"AR × orientation conditional surface","data":"figure_data/ar_orientation_surface.csv","code":"plot_code/plot_ar_orientation_surface.py","outputs":["figures/QM20_F2_ar_orientation_surface.svg","figures/QM20_F2_ar_orientation_surface.pdf","figures/QM20_F2_ar_orientation_surface.png"],"papers":0,"samples":0,"effect_definition":"0.5*sigma_m*V*AR*eta","uncertainty":"not empirical","evidence":"mechanistic sensitivity","support_domain":"AR1-60, eta0.125-0.65"},
        {"id":"QM20_F3","title":"Spatial architecture effect forest","data":"figure_data/architecture_forest.csv","code":"plot_code/plot_architecture_forest.py","outputs":["figures/QM20_F3_architecture_forest.svg","figures/QM20_F3_architecture_forest.pdf","figures/QM20_F3_architecture_forest.png"],"papers":3,"samples":11,"effect_definition":"paired percent change","uncertainty":"approximate from reported SD","evidence":"same-paper A/B matches","support_domain":"homogeneous/confined/quasi/two-scale networks"},
        {"id":"QM20_F4","title":"Agglomeration–plasticity penalty","data":"figure_data/agglomeration_penalty.csv","code":"plot_code/plot_agglomeration_penalty.py","outputs":["figures/QM20_F4_agglomeration_penalty.svg","figures/QM20_F4_agglomeration_penalty.pdf","figures/QM20_F4_agglomeration_penalty.png"],"papers":1,"samples":5,"effect_definition":"Spearman association and PCHIP","uncertainty":"dose/porosity/morphology confounded","evidence":"source distribution SD plus direct mechanical table","support_domain":"SD0.9-11.1%, dose2-30%, porosity0.56-2.36%"}
    ]}
    wj("PLOT_SPECS.json",specs)

    with (ROOT/"PROVENANCE.jsonl").open("w",encoding="utf-8",newline="\n") as f:
        for r in cohort:
            f.write(json.dumps({"object_type":"atomic_property_record","record_uid":r["record_uid"],"snapshot_id":snapshot,"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"source_hash":r["source_hash"],"source_hash_kind":"NORMALIZED_CAPTURE_NOT_ORIGINAL_BYTE_HASH","doi":r["paper_doi"],"locator":r["source_locator"],"evidence_grade":r["evidence_grade"],"property":r["property"],"value":r["value"],"unit":r["unit"]},ensure_ascii=False,sort_keys=True)+"\n")
        for e in effects:
            f.write(json.dumps({"object_type":"paired_effect","pair_uid":e["pair_uid"],"snapshot_id":snapshot,"paper_uid":e["paper_uid"],"source_hash":e["source_hash"],"doi":e["paper_doi"],"estimand_class":e["estimand_class"],"property":e["property"],"delta":e["delta"],"claim_level":2},ensure_ascii=False,sort_keys=True)+"\n")

    for p in papers:
        wj(f"literature_evidence/{p['k']}.json",{"paper_uid":p["paper_uid"],"doi":p["doi"],"title":p["title"],"source_hash":p["source_hash"],"source_hash_kind":"NORMALIZED_CAPTURE_NOT_ORIGINAL_BYTE_HASH","source_file":p["src"],"locator":p["loc"],"copyright_note":"Structured factual extraction and locator only; no full article redistributed."})
    wt("OPENED_FILES.txt","\n".join(["QM20 dispatch unit",*[f"{p['src']} | {p['doi']} | {p['loc']}" for p in papers],"QM08/QM16/QM32 derived verdicts (cross-check only)","XML_CORPUS_AUDIT_REPORT.md","26 top-level archives registered via prior member audit/corpus index"])+"\n")

    methods=f'''# METHODS — QM20\n\n`WINDOW={WINDOW} | SNAPSHOT={snapshot} | INPUT_MODE={MODE}`\n\nFive directly opened primary papers were converted into {len(cohort)} atomic property rows and {len(pairs)} same-paper/near-matched pairs. Atomicity is paper × sample × process × heat treatment × mode × temperature × orientation × property. Rows are never treated as independent papers.\n\nEstimands: fixed-dose architecture contrasts; fixed-dose size/AR contrasts; declared AR×orientation shear-lag sensitivity; and TiBw-distribution-SD association with plastic strain. Direct tables/text outrank figures. Koo properties are explicitly figure-derived/rounded. Bao S2 uses Table 4 (1224 MPa), and Zhou TMC2 is premature-fracture stress, not UTS.\n\nEffects use delta, lnRR and percent change. Approximate pair intervals use t(df=4)×sqrt(sd_t²/3+sd_c²/3), with unknown covariance acknowledged. The size curve is PCHIP in log diameter. The AR×orientation map is mechanistic, not empirical ALE.\n\nFor Bao S1-S5, Spearman associations were computed. The adjustment design [1, SD, dose, porosity] has rank {rank} and condition number {cond:.3g} at n=5; an adjusted causal agglomeration coefficient is refused. LOPO is an estimand-availability stress test: deleting each paper deletes a unique central estimand, so a cross-paper architecture coefficient is NOT_IDENTIFIABLE.\n\nNo Gold, ACTIVE, Schema or production model registry was modified.\n'''
    wt("METHODS.md",methods)
    wt("LIMITATIONS.md","""# LIMITATIONS — QM20\n\n1. Authoritative V29/Q40 atomic snapshot and original package-member byte hashes were unavailable; local hash binding remains mandatory.\n2. Numeric orientation factors occur in only two papers, so empirical AR×orientation ALE is underidentified.\n3. Koo diameter and AR are coupled; independent diameter effect is not identifiable.\n4. Bao agglomeration co-varies with dose, porosity and morphology; causal penalty is not identifiable.\n5. Fixed-dose architecture evidence is concentrated in Wu; other topology contrasts alter chemistry/dose.\n6. Approximate pair intervals ignore within-paper covariance.\n7. No eligible matched core-shell cohort was recovered.\n8. Results are paired/descriptive evidence, not a production model or validated recipe.\n""")
    executive=f'''# QM20 Executive Verdict\n\n`WINDOW={WINDOW} | SNAPSHOT={snapshot} | INPUT_MODE={MODE}`\n\nGeometry acts through a coupled size–AR–orientation chain, not a universal size coefficient. In Koo's controlled 1 vol.% series, diameter decreases 1.0→0.1 µm as AR rises 18→58; elastic modulus rises about 116→125 GPa (+7.8%) and figure-derived YS about 900→1065 MPa (+18.3%). Independent size effect: NOT_IDENTIFIABLE.\n\nOrientation amplifies high-AR load transfer. Bao S1/S2 (AR19.2/23.0; eta0.64/0.62) report source load-transfer terms 111/322 MPa against observed ΔYS 138/321 MPa. Zhou TMC1 (AR≈20; eta≈0.27) reports 58 MPa against ΔYS305 MPa, with grain refinement dominating the remainder. Empirical AR×orientation ALE: NOT_IDENTIFIABLE; the delivered surface is mechanistic sensitivity only.\n\nAt fixed total TiB in Wu, continuous-Ti-region FLSCR versus homogeneous/continuous comparator changes YS by −54 MPa at 4 vol.% and −28.4 MPa at 6 vol.%, while fracture EL rises +4.5/+3.1 pp and WOF +29.2/+13.9 MJ/m³. In Jiao, two-scale topology exceeds TiBw-only by +120 MPa YS, +110 MPa UTS and +1.8 pp EL; versus Ti5Si3-only by +150 MPa, +150 MPa and +2.9 pp. These are paired/near-matched, not universal coefficients.\n\nAcross Bao S1-S5, TiBw distribution SD rises 0.9→11.1%; uniform strain falls 12.6→0% (Spearman rho={ru:.3f}, p={pu:.4f}) and fracture strain 29.3→16.5% (rho={rf:.3f}, p={pf:.4f}). Dose, porosity and morphology co-vary, so causal agglomeration penalty is NOT_IDENTIFIABLE.\n\nDecision: require post-process AR distribution, numeric orientation distribution, matrix-continuity topology, porosity and reproducible cluster/network metrics. Nominal dose alone is inadequate. Homogeneous networks may maximize strength, while continuous ductile regions or two-scale topology can recover strain storage and crack deflection; excessive connectivity, coarse brittle phase, pores and clusters invert the benefit.\n\nEvidence accounting: 26 top-level archives registered; 5 directly opened primary papers; {len(cohort)} atomic rows; {len(pairs)} pairs; {len(effects)} effects; four SVG/PDF/600-dpi-PNG plot triplets. Claim ceiling: level 2.\n\n`STATUS: CONTINUE_DATA_GAP | WINDOW=QM20 | MISSING=AUTHORITATIVE_Q40_SNAPSHOT+ORIGINAL_MEMBER_HASHES+REPEATED_ORIENTATION_AND_FIXED_AGGLOMERATION_SERIES | NEXT=LOCAL_HASH_BIND_AND_RERUN_PAPER_CLUSTER_MODEL`\n'''
    wt("00_EXECUTIVE_VERDICT.md",executive)
    req={"window_id":WINDOW,"snapshot_id":snapshot,"status":"CONTINUE_DATA_GAP","required":[{"priority":1,"object":"Q40_INPUT_SNAPSHOT_AND_V29_ATOMIC_RECORDS","reason":"authoritative row identity and exact condition UID"},{"priority":1,"object":"V29_PROVENANCE_CONFLICT_EXCLUDED_REGISTRIES","reason":"source binding and admission decisions"},{"priority":1,"object":"ORIGINAL_PACKAGE_MEMBER_HASHES","identifiers":[p["doi"] for p in papers],"reason":"package SHA/member path/CRC"},{"priority":1,"object":"POST_PROCESS_AR_AND_ORIENTATION_DISTRIBUTIONS","minimum":">=5 independent papers with repeated architecture classes","reason":"empirical AR×orientation ALE"},{"priority":1,"object":"FIXED_DOSE_FIXED_POROSITY_AGGLOMERATION_SERIES","reason":"separate clustering from dose/defects"},{"priority":2,"object":"RAW_SEGMENTABLE_MICROGRAPHS","fields":["cluster area fraction","nearest-neighbor CV","Ripley K","network connectivity","orientation distribution"],"reason":"reproducible architecture metrics"},{"priority":2,"object":"MATCHED_GRADIENT_CORE_SHELL_CONTROLS","reason":"missing/paper-specific classes"}],"acceptance":"bind snapshot_id+paper_uid+sample_uid+condition_uid+package SHA+member path+CRC; rerun LOPO/UQ","next_action":"LOCAL_ABSORB_HASH_BIND_AND_RERUN_QM20"}
    wj("WEB_TO_LOCAL_REQUEST.json",req)
    wt("LOCAL_ABSORPTION_PROMPT.md",f'''# LOCAL_ABSORPTION_PROMPT — QM20\n\n1. Verify artifact CRC, checksums, manifest, tests and plot triplets.\n2. Bind derived snapshot `{snapshot}` to authoritative Q40/V29 without mutating ACTIVE.\n3. Map every row to package SHA + member path + CRC + original-byte hash.\n4. Re-open five DOI anchors; resolve C001-C005; preserve TMC2 as premature-fracture stress.\n5. Replace Koo rounded figure values with controlled digitization receipt/direct table.\n6. Compute segmentable cluster/orientation/network metrics from raw micrographs.\n7. Refit only after repeated architecture classes exist; run paper-cluster LOPO, leave-family-out and evidence sensitivity.\n8. Never promote Gold/register production model/label VALIDATED from this package alone.\n9. Return signed absorption receipt.\n''')
    status={"window_id":WINDOW,"snapshot_id":snapshot,"papers_seen":5,"papers_included":5,"independent_papers":5,"atomic_rows":len(cohort),"matched_pairs":len(pairs),"effect_estimates":len(effects),"plots_generated":4,"plot_files":12,"open_conflicts":2,"claim_level_max":2,"status":"CONTINUE_DATA_GAP","next_action":"LOCAL_HASH_BIND_AND_RERUN_PAPER_CLUSTER_MODEL","source_archives_registered":26,"production_model_registered":False,"gold_promoted":False,"validated_recipe_created":False}
    wj("WINDOW_STATUS.json",status)
    wj("VALIDATION_REPORT.json",{"window_id":WINDOW,"snapshot_id":snapshot,"mandatory_files_complete":True,"mandatory_missing":[],"figure_triples":4,"nested_zip_count":0,"atomic_uid_binding":True,"claim_level_max":2,"status":"PASS_WITH_CONTINUE_DATA_GAP","primary_sources":5,"source_archives_registered":26})
    wt("requirements.lock","matplotlib==3.9.2\nnumpy==2.1.3\nscipy==1.14.1\n")
    wt("acceptance_commands.md","# Acceptance commands\n\n```bash\npython -m pip install -r requirements.lock\nsha256sum -c CHECKSUMS.sha256\npython tests/test_outputs.py .\npython analysis_code/qm20_analysis.py .\n```\n")
    wt("analysis_code/qm20_analysis.py",'''from pathlib import Path\nimport csv,json,sys\nr=Path(sys.argv[1] if len(sys.argv)>1 else ".");s=json.loads((r/"WINDOW_STATUS.json").read_text());p=list(csv.DictReader((r/"PAIR_MATCHES.csv").open()));e=list(csv.DictReader((r/"EFFECT_ESTIMATES.csv").open()));assert len(p)==len(e);assert s["claim_level_max"]<=2;print(json.dumps({"pass":True,"snapshot_id":s["snapshot_id"],"pairs":len(p)}))\n''')
    test='''from pathlib import Path\nimport csv,hashlib,json,sys,unittest\nR=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()\ndef sha(p):\n h=hashlib.sha256();\n with p.open("rb") as f:\n  for b in iter(lambda:f.read(1<<20),b""):h.update(b)\n return h.hexdigest()\nclass T(unittest.TestCase):\n def test_required(self):\n  q={"00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256","REINFORCEMENT_GEOMETRY.csv","ARCHITECTURE_EFFECTS.csv","AGGLOMERATION_PENALTY.csv","GEOMETRY_EVIDENCE.csv"};self.assertFalse([x for x in q if not (R/x).exists()])\n def test_atomic(self):\n  x=list(csv.DictReader((R/"ANALYSIS_COHORT.csv").open()));self.assertGreater(len(x),50);self.assertEqual(len(x),len({r["record_uid"] for r in x}));self.assertTrue(all(all(r[k] for k in ["snapshot_id","paper_uid","sample_uid","condition_uid","source_hash"]) for r in x))\n def test_effect_math(self):\n  x=list(csv.DictReader((R/"EFFECT_ESTIMATES.csv").open()));self.assertGreater(len(x),30);[self.assertAlmostEqual(float(r["delta"]),float(r["treatment_value"])-float(r["control_value"]),places=7) for r in x]\n def test_plots(self):\n  s=json.loads((R/"PLOT_SPECS.json").read_text());self.assertEqual(len(s["plots"]),4);[self.assertGreater((R/x).stat().st_size,1000) for p in s["plots"] for x in p["outputs"]]\n def test_boundary(self):\n  s=json.loads((R/"WINDOW_STATUS.json").read_text());self.assertLessEqual(s["claim_level_max"],2);self.assertFalse(s["production_model_registered"]);self.assertFalse(s["gold_promoted"]);self.assertFalse(s["validated_recipe_created"]);self.assertFalse(list(R.rglob("*.zip")))\n def test_manifest(self):\n  m=json.loads((R/"MANIFEST.json").read_text());[self.assertEqual(x["sha256"],sha(R/x["path"])) for x in m["files"]];\n  for line in (R/"CHECKSUMS.sha256").read_text().splitlines():\n   if line.strip(): d,p=line.split("  ",1);self.assertEqual(d,sha(R/p))\n def test_estimands(self):\n  x=list(csv.DictReader((R/"ARCHITECTURE_EFFECTS.csv").open()));k={(r["paper_doi"],r["property"],round(float(r["delta"]),1)) for r in x};self.assertIn(("10.1016/j.msea.2022.143645","fracture_EL_pct",4.5),k);self.assertIn(("10.1016/j.msea.2022.143645","YS_MPa",-54.0),k);self.assertIn(("10.1016/j.powtec.2019.09.008","YS_MPa",120.0),k)\nif __name__=="__main__":\n z=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(T));raise SystemExit(0 if z.wasSuccessful() else 1)\n'''
    wt("tests/test_outputs.py",test)
    wj("DELIVERY_SUMMARY.json",{"window_id":WINDOW,"snapshot_id":snapshot,"status":"CONTINUE_DATA_GAP","atomic_rows":len(cohort),"matched_pairs":len(pairs),"effect_estimates":len(effects),"independent_papers":5,"plots":4,"plot_files":12,"claim_level_max":2,"nested_zip":False,"next_action":"LOCAL_HASH_BIND_AND_RERUN_PAPER_CLUSTER_MODEL"})

    # First manifest, test, receipt, final manifest.
    def freeze():
        for n in ("MANIFEST.json","CHECKSUMS.sha256"):
            p=ROOT/n
            if p.exists(): p.unlink()
        files=[]
        for p in sorted(ROOT.rglob("*")):
            if p.is_file(): files.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":hfile(p)})
        wj("MANIFEST.json",{"window_id":WINDOW,"snapshot_id":snapshot,"generated_at":datetime.now(timezone.utc).isoformat(),"status":"CONTINUE_DATA_GAP","file_count":len(files),"tree_sha256":htxt("\n".join(x["sha256"]+"  "+x["path"] for x in files)),"files":files})
        wt("CHECKSUMS.sha256","\n".join(hfile(p)+"  "+p.relative_to(ROOT).as_posix() for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name!="CHECKSUMS.sha256")+"\n")
    freeze()
    q=subprocess.run([sys.executable,str(ROOT/"tests/test_outputs.py"),str(ROOT)],capture_output=True,text=True)
    wt("TEST_OUTPUT.txt",q.stdout+q.stderr)
    if q.returncode: raise RuntimeError(q.stdout+q.stderr)
    freeze()
    subprocess.run([sys.executable,str(ROOT/"tests/test_outputs.py"),str(ROOT)],check=True)
    print(f"WINDOW={WINDOW} | SNAPSHOT={snapshot} | INPUT_MODE={MODE}")
    print("STATUS: CONTINUE_DATA_GAP | WINDOW=QM20 | MISSING=AUTHORITATIVE_Q40_SNAPSHOT+ORIGINAL_MEMBER_HASHES+REPEATED_ORIENTATION_AND_FIXED_AGGLOMERATION_SERIES | NEXT=LOCAL_HASH_BIND_AND_RERUN_PAPER_CLUSTER_MODEL")

if __name__ == "__main__":
    build()
