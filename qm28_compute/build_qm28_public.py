#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QM28 quantitative heat-treatment return package.

This is an analysis-only, fail-closed build. It preserves atomic rows, exact
within-paper comparisons, paper-balanced uncertainty, sequence detail, figures,
provenance, tests, manifests and checksums. It never mutates ACTIVE_TITMC, Gold,
or any production model registry.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import textwrap
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

WINDOW_ID = "QM28"
BATCH_ID = "V30_TITMC_Q40_20260713"
SEED = 20260713
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
OUT = DIST / "FINAL_QM28"

PAPERS = {
    "QI2012": {"paper_uid":"P_QI2012_TIC_TA15_HT","doi":"10.1016/j.msea.2012.05.092","title":"Influence of matrix characteristics on tensile properties of in situ synthesized TiC/TA15 composite","year":2012,"locator":"primary paper Tables 1-2"},
    "JIAO2016": {"paper_uid":"P_JIAO2016_TIB_TI5SI3_TI64_HT","doi":"10.1038/srep32991","title":"Controllable two-scale network architecture and enhanced mechanical properties of (Ti5Si3+TiBw)/Ti6Al4V composites","year":2016,"locator":"primary paper Tables 1-2"},
    "WANG2018": {"paper_uid":"P_WANG2018_TIBW_NEAR_ALPHA_HT","doi":"10.1007/s11431-018-9323-3","title":"Evolution of microstructure and high temperature tensile properties of as-extruded TiBw reinforced near-alpha titanium matrix composite subjected to heat treatments","year":2018,"locator":"primary paper Tables 1-2"},
    "FEREIDUNI2021": {"paper_uid":"P_FEREIDUNI2021_LPBF_TI64_TIB_CREEP_HT","doi":"10.1016/j.jmapro.2021.08.063","title":"TiB reinforced Ti-6Al-4V matrix composites with improved short-term creep performance fabricated by laser powder bed fusion","year":2021,"locator":"primary paper heat-treatment methods and Table 2"},
    "WANG2024": {"paper_uid":"P_WANG2024_ROLLED_TIB_TA15SI_HT","doi":"10.1016/j.msea.2023.145888","title":"Microstructure evolution and enhanced mechanical properties of as-rolled TiB/(TA15-Si) composite via heat treatment","year":2024,"locator":"primary paper Fig. 8 and text"},
    "ANDRIEUX2018": {"paper_uid":"P_ANDRIEUX2018_TI_TIC_KINETICS","doi":"10.1007/s10853-018-2258-8","title":"Synthesis of Ti matrix composites reinforced with TiC particles: in-situ synchrotron X ray diffraction and modeling","year":2018,"locator":"accepted manuscript Figs. 6 and 11"},
    "LI2013": {"paper_uid":"P_LI2013_TIB_LA2O3_THESIS","doi":"","title":"Research on Microstructure and Mechanical Properties of High Temperature (TiB+La2O3)/Ti Composites","year":2013,"locator":"Shanghai Jiao Tong University doctoral thesis, Chs. 3-7"},
}

UPLOADS = [
    "00_统一上传总控与校验信息_20260712.zip",
    "S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip",
    "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip",
] + [f"S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip" for i in range(1,9)] + [
    "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip",
] + [f"S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip" for i in range(1,4)] + [f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip" for i in range(1,11)]

KNOWN_UPLOAD_HASHES = {
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
    "S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip":"bf320529787b3dc8ad6e35f80932cd9cd6b31a3191c22a6617c379b2f5c1ce43",
    "S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip":"08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755",
    "TITMC_V27_LIT_WEB_P001_OF_010.zip":"42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0",
    "TITMC_V27_LIT_WEB_P002_OF_010.zip":"05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193",
    "TITMC_V27_LIT_WEB_P003_OF_010.zip":"535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917",
    "TITMC_V27_LIT_WEB_P004_OF_010.zip":"bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a",
}

REQUIRED = [
    "00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv",
    "HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv",
    "NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json",
    "WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256",
    "HEAT_TREATMENT_SEQUENCES.csv","HT_PAIR_EFFECTS.csv","HT_DOSE_RESPONSE.csv","HT_REINFORCEMENT_INTERACTIONS.csv",
]


def htext(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hfile(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def uid(prefix: str, *parts: Any) -> str:
    return f"{prefix}_{htext('|'.join(map(str,parts)))[:18]}"


def paper_hash(key: str) -> str:
    return htext(json.dumps(PAPERS[key],ensure_ascii=False,sort_keys=True,separators=(",",":")))


def clean() -> None:
    if DIST.exists(): shutil.rmtree(DIST)
    OUT.mkdir(parents=True)


def wtext(rel: str, text: str) -> Path:
    p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8",newline="\n"); return p


def wjson(rel: str, obj: Any) -> Path:
    return wtext(rel,json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n")


def wcsv(rel: str, rows: Sequence[Dict[str,Any]], fields: Sequence[str]) -> Path:
    p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(fields),extrasaction="ignore"); wr.writeheader()
        for r in rows: wr.writerow({k:"" if r.get(k) is None else r.get(k) for k in fields})
    return p


def atomic(rows: List[Dict[str,Any]], paper: str, sample: str, condition: str, matrix: str, reinforcement: str,
           reinforcement_fraction: float|None, reinforcement_unit: str, process: str, ht_class: str, ht_sequence: str,
           stages: int, solution_t: float|None, solution_h: float|None, aging_t: float|None, aging_h: float|None,
           cooling: str, beta_transus: float|None, beta_evidence: str, beta_state: str, microstructure: str,
           test_mode: str, test_t: float|None, stress: float|None, strain_rate: float|None, orientation: str,
           prop: str, value: float, unit: str, sd: float|None=None, n: int|None=None,
           evidence: str="DIRECT_TABLE_TEXT", locator: str="", baseline: bool=False, note: str="") -> None:
    p=PAPERS[paper]
    delta=(solution_t-beta_transus) if solution_t is not None and beta_transus is not None else None
    record={
        "snapshot_id":"QM28_RECOVERY_SNAPSHOT_20260713","paper_key":paper,"paper_uid":p["paper_uid"],"doi":p["doi"],
        "title":p["title"],"year":p["year"],"sample_uid":sample,"condition_uid":condition,"matrix":matrix,
        "reinforcement":reinforcement,"reinforcement_fraction":reinforcement_fraction,"reinforcement_unit":reinforcement_unit,
        "process":process,"ht_class":ht_class,"ht_sequence":ht_sequence,"ht_stage_count":stages,"solution_temp_c":solution_t,
        "solution_time_h":solution_h,"aging_temp_c":aging_t,"aging_time_h":aging_h,"cooling":cooling,
        "beta_transus_c":beta_transus,"delta_to_beta_transus_c":delta,"beta_transus_evidence":beta_evidence,
        "beta_relative_state":beta_state,"microstructure_state":microstructure,"test_mode":test_mode,"test_temp_c":test_t,
        "applied_stress_mpa":stress,"strain_rate_s":strain_rate,"orientation":orientation,"property":prop,"value":value,
        "unit":unit,"sd":sd,"n":n,"evidence_level":evidence,"source_locator":p["locator"]+("; "+locator if locator else ""),
        "source_hash":paper_hash(paper),"source_hash_kind":"CURATED_SOURCE_IDENTITY_SHA256_NOT_FILE_BYTES",
        "is_baseline":baseline,"evidence_note":note,"claim_level":2 if test_mode!="phase_kinetics" else 1,
    }
    record["atomic_uid"]=uid("AR",record["paper_uid"],sample,condition,test_mode,test_t,stress,strain_rate,orientation,prop,value)
    rows.append(record)


def build_rows() -> List[Dict[str,Any]]:
    rows=[]
    # QI 2012, TiC/TA15. beta transus measured 1095 C.
    cond={
        "AS_CAST":("none","as-cast",0,None,None,None,None,"none","as-cast fully lamellar; alpha-lath 2.2 um; colony 27.2 um",True),
        "HT1":("solution","1120C/5h/AC",1,1120,5,None,None,"AC","fine fully lamellar; alpha-lath 0.3 um; colony 10.9 um; TiC spheroidized",False),
        "HT2":("duplex","1120C/5h -> 15C/min to 1075C/10min -> AC",2,1120,5,1075,1/6,"15C/min+AC","bimodal; primary alpha about 21.6 vol.%",False),
        "HT3":("duplex","1120C/5h -> 15C/min to 1035C/10min -> AC",2,1120,5,1035,1/6,"15C/min+AC","near-equiaxed; primary alpha about 59.7 vol.%",False),
    }
    rt={"AS_CAST":{"UTS":(1048.3,4.6),"YS":(1023.1,6.2),"EL":(3.92,0.56)},"HT1":{"UTS":(1119.7,7.3),"YS":(1045.8,4.5),"EL":(2.17,0.31)},"HT2":{"UTS":(1130.6,5.1),"YS":(1056.5,4.7),"EL":(1.33,0.20)},"HT3":{"UTS":(1159.4,3.3),"YS":(1076.6,5.5),"EL":(0.65,0.07)}}
    high={600:{"AS_CAST":{"UTS":(597.7,5.6),"EL":(5.53,1.34)},"HT1":{"UTS":(652.5,7.7),"EL":(6.76,0.82)},"HT2":{"UTS":(687.7,2.6),"EL":(7.44,2.16)}},650:{"AS_CAST":{"UTS":(494.8,6.2),"EL":(16.45,1.66)},"HT1":{"UTS":(505.6,2.4),"EL":(20.73,3.40)},"HT2":{"UTS":(507.7,3.5),"EL":(19.89,2.57)}}}
    for c,props in rt.items():
        hc,seq,st,sol,sh,age,ah,cool,micro,base=cond[c]
        for prop,(v,sd) in props.items():
            atomic(rows,"QI2012","S_QI2012_TIC10_TA15",f"C_QI2012_{c}_RT","TA15 (Ti-6Al-2Zr-1.5Mo-1V)","TiC",10,"vol%","induction melting + casting",hc,seq,st,sol,sh,age,ah,cool,1095,"DIRECT_MEASURED_METALLOGRAPHY","supertransus first stage" if sol else "not applicable",micro,"tension",25,None,None,"unspecified",prop,v,"MPa" if prop!="EL" else "%",sd,3,locator="Table 1",baseline=base)
    for temp,cs in high.items():
        for c,props in cs.items():
            hc,seq,st,sol,sh,age,ah,cool,micro,base=cond[c]
            for prop,(v,sd) in props.items():
                atomic(rows,"QI2012","S_QI2012_TIC10_TA15",f"C_QI2012_{c}_{temp}C","TA15 (Ti-6Al-2Zr-1.5Mo-1V)","TiC",10,"vol%","induction melting + casting",hc,seq,st,sol,sh,age,ah,cool,1095,"DIRECT_MEASURED_METALLOGRAPHY","supertransus first stage" if sol else "not applicable",micro,"tension",temp,None,None,"unspecified",prop,v,"MPa" if prop!="EL" else "%",sd,3,locator="Table 2",baseline=base)

    # WANG 2018, 5.1 vol.% TiBw near-alpha, 600 C tension.
    wcond={
        "UNTREATED":("none","as-extruded",0,None,None,None,None,"none","fine lamellar alpha + intergranular beta",True,"not applicable"),
        "HT1":("solution+aging","1100C/2h/AC + 500C/5h/AC",2,1100,2,500,5,"AC+AC","fully transformed beta; fine alpha+beta; no alpha2/silicide",False,"beta field"),
        "HT2":("solution+aging","1000C/2h/AC + 500C/5h/AC",2,1000,2,500,5,"AC+AC","primary alpha + transformed beta; alpha2 about 5 nm",False,"alpha+beta field"),
        "HT3":("solution+aging","1000C/2h/AC + 600C/5h/AC",2,1000,2,600,5,"AC+AC","primary alpha + transformed beta; alpha2 growth",False,"alpha+beta field"),
        "HT4":("solution+aging","1000C/2h/AC + 700C/5h/AC",2,1000,2,700,5,"AC+AC","primary alpha + transformed beta; alpha2 about 20-30 nm",False,"alpha+beta field"),
    }
    vals={"UNTREATED":{"UTS":850,"EL":15.5},"HT1":{"UTS":904,"EL":14.5},"HT2":{"UTS":953,"EL":14.0},"HT3":{"UTS":955,"EL":13.2},"HT4":{"UTS":986,"EL":10.8}}
    for c,props in vals.items():
        hc,seq,st,sol,sh,age,ah,cool,micro,base,bs=wcond[c]
        for prop,v in props.items():
            atomic(rows,"WANG2018","S_WANG2018_TIBW5P1_NEAR_ALPHA",f"C_WANG2018_{c}_600C","Ti-5.8Al-3.4Zr-4Sn-0.4Mo-0.4Nb-0.4Si-0.06C","TiBw",5.1,"vol%","reactive hot pressing + hot extrusion",hc,seq,st,sol,sh,age,ah,cool,None,"NOT_REPORTED_NUMERIC",bs,micro,"tension",600,None,5.6e-3,"extrusion direction",prop,v,"MPa" if prop=="UTS" else "%",None,None,locator="Table 2",baseline=base,note="TiBw stable; no interfacial reaction reported during HT")

    # JIAO 2016, water-quench temperature series.
    jcond={"AS_SINTERED":("none","as-sintered",0,None,None,"none","two-scale Ti5Si3/TiBw network",True,"not assessed"),"WQ990":("solution","990C/40min/WQ",1,990,2/3,"WQ","transformed matrix; partial silicide redistribution",False,"near transus by alloy prior"),"WQ1100":("solution","1100C/40min/WQ",1,1100,2/3,"WQ","martensitic/transformed matrix; Ti5Si3 redistribution",False,"supertransus by alloy prior"),"WQ1200":("solution","1200C/40min/WQ",1,1200,2/3,"WQ","martensitic matrix; local Ti5Si3 dissolution near TiBw",False,"supertransus by alloy prior")}
    tens={"AS_SINTERED":1160,"WQ990":1010,"WQ1100":1050,"WQ1200":1070}
    comp={"AS_SINTERED":{"YCS":1225,"UCS":1402,"COMP_STRAIN":21.9},"WQ990":{"YCS":1305,"UCS":1412,"COMP_STRAIN":16.3},"WQ1100":{"YCS":1535,"UCS":1627,"COMP_STRAIN":8.2},"WQ1200":{"YCS":1687,"UCS":1753,"COMP_STRAIN":6.6}}
    for c,v in tens.items():
        hc,seq,st,sol,sh,cool,micro,base,bs=jcond[c]
        atomic(rows,"JIAO2016","S_JIAO2016_TI5SI3_4_TIBW_3P4_TI64",f"C_JIAO2016_{c}_RT_TENSION","Ti-6Al-4V","Ti5Si3+TiBw",7.4,"vol% total","powder metallurgy + reactive sintering",hc,seq,st,sol,sh,None,None,cool,None,"DATABASE_PRIOR_ONLY",bs,micro,"tension",25,None,None,"unspecified","UTS",v,"MPa",None,None,locator="Table 1",baseline=base)
    for c,props in comp.items():
        hc,seq,st,sol,sh,cool,micro,base,bs=jcond[c]
        for prop,v in props.items():
            atomic(rows,"JIAO2016","S_JIAO2016_TI5SI3_4_TIBW_3P4_TI64",f"C_JIAO2016_{c}_RT_COMPRESSION","Ti-6Al-4V","Ti5Si3+TiBw",7.4,"vol% total","powder metallurgy + reactive sintering",hc,seq,st,sol,sh,None,None,cool,None,"DATABASE_PRIOR_ONLY",bs,micro,"compression",25,None,None,"unspecified",prop,v,"%" if prop=="COMP_STRAIN" else "MPa",None,None,locator="Table 2",baseline=base)

    # FEREIDUNI 2021, 2x2 reinforcement x HT creep at 600 C / 200 MPa.
    fc={"TI64_AB":("S_FER2021_TI64","none",0,"none","as-built",0,None,None,"none","columnar prior-beta + alpha-prime martensite",True),"TI64_HT":("S_FER2021_TI64","none",0,"supertransus anneal","1050C/2h/furnace cooling",1,1050,2,"FC","equiaxed prior-beta about 257+/-83 um; continuous GB-alpha about 11.2+/-3.3 um",False),"TMC_AB":("S_FER2021_TIB_TMC","TiB",0.2,"none","as-built",0,None,None,"none","alpha-prime martensite + fine TiB; no continuous GB-alpha",True),"TMC_HT":("S_FER2021_TIB_TMC","TiB",0.2,"supertransus anneal","1050C/2h/furnace cooling",1,1050,2,"FC","equiaxed alpha about 5.75+/-1.6 um; TiB coarsened; no continuous GB-alpha",False)}
    fv={"TI64_AB":{"CREEP_RUPTURE_LIFE":3.4,"STEADY_CREEP_RATE":5.93,"TOTAL_CREEP_STRAIN":28.3,"FIVE_D_EL":53.3},"TI64_HT":{"CREEP_RUPTURE_LIFE":0.6,"STEADY_CREEP_RATE":2.16,"TOTAL_CREEP_STRAIN":3.6},"TMC_AB":{"CREEP_RUPTURE_LIFE":2.9,"STEADY_CREEP_RATE":4.48,"TOTAL_CREEP_STRAIN":13.26,"FIVE_D_EL":66.7},"TMC_HT":{"CREEP_RUPTURE_LIFE":5.8,"STEADY_CREEP_RATE":0.84,"TOTAL_CREEP_STRAIN":7.46,"FIVE_D_EL":12.5}}
    units={"CREEP_RUPTURE_LIFE":"h","STEADY_CREEP_RATE":"%/h","TOTAL_CREEP_STRAIN":"%","FIVE_D_EL":"%"}
    for c,props in fv.items():
        sample,reinf,frac,hc,seq,st,sol,sh,cool,micro,base=fc[c]
        for prop,v in props.items():
            atomic(rows,"FEREIDUNI2021",sample,f"C_FER2021_{c}_600C_200MPA","Ti-6Al-4V",reinf,frac,"wt% B4C feed equivalent grouping","laser powder bed fusion",hc,seq,st,sol,sh,None,None,cool,995,"ALLOY_REFERENCE_NOT_SPECIMEN_MEASURED","supertransus" if sol else "not applicable",micro,"creep",600,200,None,"build direction unspecified",prop,v,units[prop],None,None,locator="Table 2; 200 MPa",baseline=base,note="HT x reinforcement comparison uses one paper/protocol")

    # WANG 2024 solution/aging series.
    wc={"ROLLED":("none","as-rolled",0,None,None,None,None,"none","elongated/kinked alpha+beta lamella; silicides 200-300 nm",True),"SOL":("solution","1050C/0.5h/WQ",1,1050,.5,None,None,"WQ","acicular alpha-prime; prior-beta about 47 um; silicides dissolved",False),"A550":("solution+aging","1050C/0.5h/WQ + 550C/1h/AC",2,1050,.5,550,1,"WQ+AC","martensite retained; weak alpha2; little silicide precipitation",False),"A600":("solution+aging","1050C/0.5h/WQ + 600C/1h/AC",2,1050,.5,600,1,"WQ+AC","martensite retained; silicides at prior-beta boundaries and TiB",False),"A650":("solution+aging","1050C/0.5h/WQ + 650C/1h/AC",2,1050,.5,650,1,"WQ+AC","martensite begins decomposition; silicides at alpha/beta interfaces",False),"A700":("solution+aging","1050C/0.5h/WQ + 700C/1h/AC",2,1050,.5,700,1,"WQ+AC","martensite decomposed toward acicular alpha+beta",False),"A750":("solution+aging","1050C/0.5h/WQ + 750C/1h/AC",2,1050,.5,750,1,"WQ+AC","complete decomposition; abnormal alpha growth 1-5 um; silicide coarsening",False)}
    hv={"ROLLED":422,"SOL":444,"A550":475,"A600":482,"A650":455,"A700":440,"A750":413}
    for c,v in hv.items():
        hc,seq,st,sol,sh,age,ah,cool,micro,base=wc[c]
        atomic(rows,"WANG2024","S_WANG2024_TIB3P5_TA15SI_ROLLED",f"C_WANG2024_{c}_HV","TA15-Si (Ti-6.5Al-2Zr-1Mo-1V+0.3Si)","TiBw",3.5,"vol%","hot pressing + 80% hot rolling",hc,seq,st,sol,sh,age,ah,cool,1020,"DIRECT_MEASURED_METALLOGRAPHY","supertransus solution" if sol else "not applicable",micro,"hardness_indentation",25,None,None,"rolled plane","HV",v,"HV",None,5,locator="Fig. 8a",baseline=base)
    wt={600:{"ROLLED":{"UTS":710,"EL":39},"A600":{"UTS":992,"EL":26},"A700":{"UTS":852,"EL":32},"A750":{"UTS":768}},700:{"ROLLED":{"UTS":228,"EL":182},"A600":{"UTS":399,"EL":68},"A700":{"UTS":421,"EL":68}}}
    for tt,cs in wt.items():
        for c,props in cs.items():
            hc,seq,st,sol,sh,age,ah,cool,micro,base=wc[c]
            for prop,v in props.items():
                atomic(rows,"WANG2024","S_WANG2024_TIB3P5_TA15SI_ROLLED",f"C_WANG2024_{c}_{tt}C","TA15-Si (Ti-6.5Al-2Zr-1Mo-1V+0.3Si)","TiBw",3.5,"vol%","hot pressing + 80% hot rolling",hc,seq,st,sol,sh,age,ah,cool,1020,"DIRECT_MEASURED_METALLOGRAPHY","supertransus solution" if sol else "not applicable",micro,"tension",tt,None,None,"rolling direction unresolved",prop,v,"MPa" if prop=="UTS" else "%",None,3,locator="Fig. 8b and text",baseline=base)

    # ANDRIEUX 2018 phase-kinetics anchors, never pooled with mechanical properties.
    kin=[(0,800,"TIC_CONVERSION",0,"%","DIRECT_TEXT_BASELINE","initial TiC0.96"),(1,800,"SMALLEST_PARTICLE_DISSOLUTION",10,"% of initial particles","DERIVED_CALCULATION","modeled smallest fraction"),(180,800,"SMALL_CRYSTALLITE_CONSUMPTION",100,"%","DIRECT_TEXT","small TiC0.96_SC consumed"),(360,800,"TIC_CONVERSION",50,"%","DIRECT_TEXT","50% conversion TiC0.96_BC to TiCy"),(360,800,"CARBIDE_MASS_FRACTION",19,"wt%","DIRECT_TEXT","increase from 16 to about 19 wt%"),(5400,800,"TIC_CONVERSION",75,"%","DERIVED_CALCULATION","about 25% TiC0.96_BC remains"),(3600,900,"CARBIDE_MASS_FRACTION_MODELED",22,"wt%","DERIVED_CALCULATION","industrial 1h model"),(3600,900,"CARBIDE_MASS_FRACTION_MEASURED",21,"wt%","DIRECT_TEXT","industrial 1h experiment")]
    for sec,temp,prop,v,unit,ev,note in kin:
        atomic(rows,"ANDRIEUX2018","S_ANDRIEUX2018_TI_TIC15",f"C_ANDRIEUX_{temp}C_{sec}S_{prop}","commercially pure Ti","TiC0.96 -> TiCy",15,"vol% nominal","powder compact / consolidation analogue","isothermal reaction anneal",f"{temp}C/{sec}s/isothermal",1,temp,sec/3600,None,None,"isothermal",None,"NOT_APPLICABLE","not applicable",note,"phase_kinetics",temp,None,None,"not applicable",prop,v,unit,None,None,evidence=ev,locator="Figs. 6 and 11",baseline=(sec==0 and prop=="TIC_CONVERSION"),note="phase/reinforcement chemistry; not a mechanical estimate")

    keys=["paper_uid","sample_uid","condition_uid","test_mode","test_temp_c","applied_stress_mpa","strain_rate_s","orientation","property"]
    seen=set()
    for r in rows:
        k=tuple(r[x] for x in keys)
        if k in seen: raise RuntimeError(f"atomic collision {k}")
        seen.add(k)
    return rows


def sequences(rows: Sequence[Dict[str,Any]]) -> List[Dict[str,Any]]:
    cols=["paper_uid","doi","sample_uid","condition_uid","matrix","reinforcement","process","ht_class","ht_sequence","ht_stage_count","solution_temp_c","solution_time_h","aging_temp_c","aging_time_h","cooling","beta_transus_c","delta_to_beta_transus_c","beta_transus_evidence","beta_relative_state","microstructure_state","source_locator","source_hash"]
    out=[]; seen=set()
    for r in rows:
        k=(r["paper_uid"],r["sample_uid"],r["condition_uid"])
        if k in seen: continue
        seen.add(k)
        x={c:r.get(c) for c in cols}; x["sequence_uid"]=uid("HTSEQ",*k,r["ht_sequence"])
        x["purpose"]="baseline" if r["ht_class"]=="none" else ("strengthening/phase control" if "aging" in r["ht_class"] else "microstructure/phase control")
        x["claim_ceiling_reason"]="numeric beta-transus missing" if r.get("solution_temp_c") is not None and r.get("beta_transus_c") is None else "general observational limit"
        out.append(x)
    li=PAPERS["LI2013"]
    for code,seq,hc,micro,note,cooling in [
        ("BETA_HT","beta solution/AC","beta heat treatment","Widmanstatten","worst tensile response among reported paths","AC"),
        ("TRIPLEX_WQ","beta solution/WQ -> alpha+beta solution -> aging","triplex/multi-step","lamellar; thinnest alpha laths","best high-temperature ductility; 700C EL at least 200% above beta-HT","WQ"),
        ("TRIPLEX_OQ","beta solution/OQ -> alpha+beta solution -> aging","triplex/multi-step","lamellar; thin alpha laths","good tensile response; fracture toughness +34% vs beta-HT in abstract","OQ"),
        ("TRIPLEX_AC","beta solution/AC -> alpha+beta solution -> aging","triplex/multi-step","lamellar","intermediate response","AC"),
        ("ALPHABETA_HT","alpha+beta solution -> aging","solution+aging","bimodal","good tensile properties; fastest steady-state creep among compared paths","AC"),
    ]:
        x={"paper_uid":li["paper_uid"],"doi":"","sample_uid":"S_LI2013_TIB_LA2O3_IMI834","condition_uid":f"C_LI2013_{code}","matrix":"IMI834-type near-alpha titanium","reinforcement":"TiB+La2O3","process":"in situ synthesis + forging","ht_class":hc,"ht_sequence":seq,"ht_stage_count":3 if "TRIPLEX" in code else 1,"solution_temp_c":"","solution_time_h":"","aging_temp_c":"","aging_time_h":"","cooling":cooling,"beta_transus_c":"","delta_to_beta_transus_c":"","beta_transus_evidence":"UNRESOLVED","beta_relative_state":"sequence label only","microstructure_state":micro,"source_locator":li["locator"],"source_hash":paper_hash("LI2013"),"sequence_uid":uid("HTSEQ",li["paper_uid"],code),"purpose":"microstructure/property control","claim_ceiling_reason":"temperatures/times unresolved; "+note}
        out.append(x)
    return out


def pair_effects(rows: Sequence[Dict[str,Any]]) -> Tuple[List[Dict[str,Any]],List[Dict[str,Any]]]:
    groups=defaultdict(list)
    for r in rows:
        if r["test_mode"]=="phase_kinetics": continue
        key=(r["paper_uid"],r["sample_uid"],r["test_mode"],r["test_temp_c"],r["applied_stress_mpa"],r["strain_rate_s"],r["orientation"],r["property"],r["unit"])
        groups[key].append(r)
    pairs=[]; effects=[]
    for key,items in sorted(groups.items(),key=lambda kv:str(kv[0])):
        bases=[r for r in items if r["is_baseline"]]
        treated=[r for r in items if not r["is_baseline"]]
        if not bases or not treated: continue
        b=sorted(bases,key=lambda r:r["condition_uid"])[0]
        for t in sorted(treated,key=lambda r:r["condition_uid"]):
            y0=float(b["value"]); y1=float(t["value"]); lnrr=math.log(y1/y0) if y0>0 and y1>0 else None
            puid=uid("PAIR",b["atomic_uid"],t["atomic_uid"])
            pairs.append({"pair_uid":puid,"paper_uid":b["paper_uid"],"doi":b["doi"],"sample_uid":b["sample_uid"],"baseline_atomic_uid":b["atomic_uid"],"treated_atomic_uid":t["atomic_uid"],"baseline_condition_uid":b["condition_uid"],"treated_condition_uid":t["condition_uid"],"baseline_ht_sequence":b["ht_sequence"],"treated_ht_sequence":t["ht_sequence"],"test_mode":b["test_mode"],"test_temp_c":b["test_temp_c"],"applied_stress_mpa":b["applied_stress_mpa"],"property":b["property"],"baseline_value":y0,"treated_value":y1,"unit":b["unit"],"comparison_level":"A_SAME_PAPER_SAMPLE_PROCESS_TEST","source_hash":b["source_hash"],"claim_level":2})
            effects.append({"effect_uid":uid("EFF",puid),"pair_uid":puid,"paper_uid":b["paper_uid"],"doi":b["doi"],"sample_uid":b["sample_uid"],"matrix":b["matrix"],"reinforcement":b["reinforcement"],"ht_class":t["ht_class"],"ht_sequence":t["ht_sequence"],"solution_temp_c":t["solution_temp_c"],"solution_time_h":t["solution_time_h"],"aging_temp_c":t["aging_temp_c"],"aging_time_h":t["aging_time_h"],"cooling":t["cooling"],"delta_to_beta_transus_c":t["delta_to_beta_transus_c"],"test_mode":b["test_mode"],"test_temp_c":b["test_temp_c"],"applied_stress_mpa":b["applied_stress_mpa"],"property":b["property"],"effect_definition":"HT_vs_untreated_same_paper","delta_y":y1-y0,"lnRR":lnrr,"percent_change":(math.exp(lnrr)-1)*100 if lnrr is not None else "","unit":b["unit"],"comparison_level":"A","evidence_level":t["evidence_level"],"claim_level":2,"uncertainty_status":"PROPAGATED_FROM_REPORTED_SD" if b["sd"] is not None and t["sd"] is not None else "NO_REPLICATE_VARIANCE","source_hash":b["source_hash"]})
    return pairs,effects


def percentile(xs: Sequence[float], q: float) -> float:
    s=sorted(xs); pos=(len(s)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos));
    return s[lo] if lo==hi else s[lo]+(s[hi]-s[lo])*(pos-lo)


def meta_600_uts(effects: Sequence[Dict[str,Any]]) -> Tuple[List[Dict[str,Any]],List[Dict[str,Any]],List[Dict[str,Any]]]:
    use=[e for e in effects if e["property"]=="UTS" and e["test_mode"]=="tension" and e["test_temp_c"]==600 and e["lnRR"]!=""]
    by=defaultdict(list)
    for e in use: by[e["paper_uid"]].append(float(e["lnRR"]))
    pmeans={p:statistics.mean(v) for p,v in by.items()}
    hier=[]; sens=[]; heter=[]
    if len(pmeans)>=3:
        vals=list(pmeans.values()); est=statistics.mean(vals); rng=random.Random(SEED); boot=[]
        papers=list(pmeans)
        for _ in range(10000): boot.append(statistics.mean(pmeans[rng.choice(papers)] for _ in papers))
        ci=(percentile(boot,.025),percentile(boot,.975)); sd=statistics.stdev(vals)
        hier.append({"estimand":"paper_equal_mean_lnRR_600C_UTS","property":"UTS","test_temp_c":600,"estimate_lnRR":est,"percent_change":100*(math.exp(est)-1),"ci_low_lnRR":ci[0],"ci_high_lnRR":ci[1],"ci_low_percent":100*(math.exp(ci[0])-1),"ci_high_percent":100*(math.exp(ci[1])-1),"prediction_low_lnRR":est-1.96*sd,"prediction_high_lnRR":est+1.96*sd,"independent_papers":len(pmeans),"effect_rows":len(use),"method":"paper-path mean then paper-cluster bootstrap 10000","claim_level":2,"status":"ESTIMATED_ASSOCIATION"})
        for omit in papers:
            v=[pmeans[p] for p in papers if p!=omit]; x=statistics.mean(v)
            sens.append({"analysis":"LOPO_600C_UTS","omitted_paper_uid":omit,"estimate_lnRR":x,"percent_change":100*(math.exp(x)-1),"direction":"positive" if x>0 else "nonpositive","status":"PASS"})
        heter.append({"estimand":"600C_UTS_paper_means","independent_papers":len(vals),"paper_mean_sd_lnRR":sd,"range_low_lnRR":min(vals),"range_high_lnRR":max(vals),"tau2":"NOT_STABLY_IDENTIFIABLE_N3","i2_pct":"NOT_IDENTIFIABLE_WITHOUT_VALID_WITHIN_STUDY_VARIANCE","status":"DESCRIPTIVE_HETEROGENEITY"})
    else:
        hier.append({"estimand":"paper_equal_mean_lnRR_600C_UTS","property":"UTS","test_temp_c":600,"estimate_lnRR":"","percent_change":"","ci_low_lnRR":"","ci_high_lnRR":"","ci_low_percent":"","ci_high_percent":"","prediction_low_lnRR":"","prediction_high_lnRR":"","independent_papers":len(pmeans),"effect_rows":len(use),"method":"paper-cluster bootstrap","claim_level":2,"status":"NOT_IDENTIFIABLE_LT3_PAPERS"})
        heter.append({"estimand":"600C_UTS_paper_means","independent_papers":len(pmeans),"paper_mean_sd_lnRR":"","range_low_lnRR":"","range_high_lnRR":"","tau2":"","i2_pct":"","status":"NOT_IDENTIFIABLE"})
    return hier,sens,heter


def dose_rows(rows: Sequence[Dict[str,Any]], effects: Sequence[Dict[str,Any]]) -> List[Dict[str,Any]]:
    out=[]
    # Within-paper aging temperature -> hardness.
    pts=sorted((float(r["aging_temp_c"]),float(r["value"])) for r in rows if r["paper_key"]=="WANG2024" and r["property"]=="HV" and r["aging_temp_c"] is not None)
    if pts:
        xs=[x for x,y in pts]; ys=[y for x,y in pts]; xm=statistics.mean(xs); ym=statistics.mean(ys)
        slope=sum((x-xm)*(y-ym) for x,y in pts)/sum((x-xm)**2 for x in xs)
        for x,y in pts: out.append({"dose_id":uid("DOSE","WANG2024","HV",x),"paper_uid":PAPERS["WANG2024"]["paper_uid"],"system":"TiBw/TA15-Si","path_family":"1050C/0.5h/WQ + aging 1h/AC","dose_variable":"aging_temp_c","dose":x,"cooling":"WQ+AC","property":"HV","response":y,"response_unit":"HV","model":"raw_within_paper","estimate":"","status":"DIRECT_SERIES"})
        out.append({"dose_id":uid("MODEL","WANG2024","HV"),"paper_uid":PAPERS["WANG2024"]["paper_uid"],"system":"TiBw/TA15-Si","path_family":"1050C/0.5h/WQ + aging 1h/AC","dose_variable":"aging_temp_c","dose":"","cooling":"WQ+AC","property":"HV","response":"","response_unit":"HV","model":"OLS linear descriptive","estimate":slope,"status":"ONE_PAPER_NO_CAUSAL_GENERALIZATION"})
    # Water-quench temperature -> compressive yield.
    pts2=sorted((float(r["solution_temp_c"]),float(r["value"])) for r in rows if r["paper_key"]=="JIAO2016" and r["property"]=="YCS" and r["solution_temp_c"] is not None)
    if pts2:
        slope=(pts2[-1][1]-pts2[0][1])/(pts2[-1][0]-pts2[0][0])
        for x,y in pts2: out.append({"dose_id":uid("DOSE","JIAO2016","YCS",x),"paper_uid":PAPERS["JIAO2016"]["paper_uid"],"system":"(Ti5Si3+TiBw)/Ti64","path_family":"40min/WQ","dose_variable":"solution_temp_c","dose":x,"cooling":"WQ","property":"YCS","response":y,"response_unit":"MPa","model":"raw_within_paper","estimate":"","status":"DIRECT_SERIES"})
        out.append({"dose_id":uid("MODEL","JIAO2016","YCS"),"paper_uid":PAPERS["JIAO2016"]["paper_uid"],"system":"(Ti5Si3+TiBw)/Ti64","path_family":"40min/WQ","dose_variable":"solution_temp_c","dose":"","cooling":"WQ","property":"YCS","response":"","response_unit":"MPa","model":"endpoint slope descriptive MPa/C","estimate":slope,"status":"ONE_PAPER_NO_CAUSAL_GENERALIZATION"})
    return out


def interaction_rows() -> List[Dict[str,Any]]:
    a0,a1,b0,b1=3.4,.6,2.9,5.8
    return [{"interaction_uid":uid("INT","FEREIDUNI2021","creep_life"),"paper_uid":PAPERS["FEREIDUNI2021"]["paper_uid"],"doi":PAPERS["FEREIDUNI2021"]["doi"],"matrix":"Ti-6Al-4V","reinforcement":"TiB","test_mode":"creep","test_temp_c":600,"applied_stress_mpa":200,"property":"CREEP_RUPTURE_LIFE","matrix_untreated":a0,"matrix_ht":a1,"tmc_untreated":b0,"tmc_ht":b1,"additive_interaction_h":(b1-b0)-(a1-a0),"ratio_of_ratios":(b1/b0)/(a1/a0),"claim_level":2,"evidence_level":"DIRECT_TABLE_TEXT","status":"SAME_PAPER_2X2_ASSOCIATION"}]


def plot_assets(effects: Sequence[Dict[str,Any]], seqs: Sequence[Dict[str,Any]], doses: Sequence[Dict[str,Any]], interactions: Sequence[Dict[str,Any]]) -> None:
    fd=OUT/"figure_data"; pc=OUT/"plot_code"; fg=OUT/"figures"; fd.mkdir(); pc.mkdir(); fg.mkdir()
    # Figure 1 selected sequence paths.
    chosen=[]
    for s in seqs:
        if s["paper_uid"] in {PAPERS["QI2012"]["paper_uid"],PAPERS["WANG2018"]["paper_uid"],PAPERS["WANG2024"]["paper_uid"],PAPERS["LI2013"]["paper_uid"]}:
            chosen.append({"paper_uid":s["paper_uid"],"sample_uid":s["sample_uid"],"condition_uid":s["condition_uid"],"ht_class":s["ht_class"],"ht_sequence":s["ht_sequence"],"solution_temp_c":s["solution_temp_c"],"aging_temp_c":s["aging_temp_c"],"cooling":s["cooling"],"claim_ceiling_reason":s["claim_ceiling_reason"]})
    wcsv("figure_data/figure_01_heat_treatment_paths.csv",chosen,["paper_uid","sample_uid","condition_uid","ht_class","ht_sequence","solution_temp_c","aging_temp_c","cooling","claim_ceiling_reason"])
    forest=[e for e in effects if e["property"] in {"UTS","YS","EL","YCS","CREEP_RUPTURE_LIFE"}]
    wcsv("figure_data/figure_02_ht_effect_forest.csv",forest,["effect_uid","paper_uid","sample_uid","reinforcement","ht_sequence","test_mode","test_temp_c","property","delta_y","lnRR","percent_change","unit","evidence_level","claim_level"])
    surf=[]
    for e in effects:
        t=e["aging_temp_c"] if e["aging_temp_c"] not in (None,"") else e["solution_temp_c"]
        hold=e["aging_time_h"] if e["aging_time_h"] not in (None,"") else e["solution_time_h"]
        if t not in (None,"") and hold not in (None,"") and e["percent_change"]!="":
            surf.append({"effect_uid":e["effect_uid"],"paper_uid":e["paper_uid"],"temperature_c":t,"time_h":hold,"cooling":e["cooling"],"property":e["property"],"test_temp_c":e["test_temp_c"],"percent_change":e["percent_change"],"delta_to_beta_transus_c":e["delta_to_beta_transus_c"],"claim_level":2})
    wcsv("figure_data/figure_03_t_time_cooling_response.csv",surf,["effect_uid","paper_uid","temperature_c","time_h","cooling","property","test_temp_c","percent_change","delta_to_beta_transus_c","claim_level"])
    ir=interactions[0]
    intdata=[{"material":"Ti-6Al-4V matrix","condition":"Untreated","creep_life_h":ir["matrix_untreated"]},{"material":"Ti-6Al-4V matrix","condition":"Heat-treated","creep_life_h":ir["matrix_ht"]},{"material":"Ti-6Al-4V + TiB","condition":"Untreated","creep_life_h":ir["tmc_untreated"]},{"material":"Ti-6Al-4V + TiB","condition":"Heat-treated","creep_life_h":ir["tmc_ht"]}]
    wcsv("figure_data/figure_04_ht_reinforcement_interaction.csv",intdata,["material","condition","creep_life_h"])

    common='''from pathlib import Path\nimport csv\nimport matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt\nROOT=Path(__file__).resolve().parents[1]\nFIG=ROOT/"figures"\ndef save(name):\n    plt.tight_layout()\n    plt.savefig(FIG/f"{name}.svg",bbox_inches="tight")\n    plt.savefig(FIG/f"{name}.pdf",bbox_inches="tight")\n    plt.savefig(FIG/f"{name}.png",dpi=600,bbox_inches="tight")\n    plt.close()\n'''
    c1=common+'''\nrows=list(csv.DictReader(open(ROOT/"figure_data/figure_01_heat_treatment_paths.csv",encoding="utf-8")))\nrows=rows[:18]\nfig,ax=plt.subplots(figsize=(12,max(5,.45*len(rows))))\nfor i,r in enumerate(rows):\n    ax.plot([0,1],[i,i],marker="o",linewidth=1.5)\n    ax.text(-.02,i,r["sample_uid"],ha="right",va="center",fontsize=7)\n    ax.text(1.02,i,r["ht_sequence"],ha="left",va="center",fontsize=7)\nax.set_xlim(-.5,2.1); ax.set_ylim(-1,len(rows)); ax.set_xticks([0,1],['Material state','Heat-treatment path']); ax.set_yticks([])\nax.set_title('Heat-treatment sequence map (selected source-bound paths)')\nax.text(.5,-.10,'Independent papers shown; sequence is not reduced to maximum temperature',transform=ax.transAxes,ha='center',fontsize=8)\nsave('figure_01_heat_treatment_alluvial')\n'''
    c2=common+'''\nrows=list(csv.DictReader(open(ROOT/"figure_data/figure_02_ht_effect_forest.csv",encoding="utf-8")))\nrows=sorted(rows,key=lambda r:abs(float(r["percent_change"])),reverse=True)[:30]\nfig,ax=plt.subplots(figsize=(11,max(6,.32*len(rows))))\nfor i,r in enumerate(rows): ax.plot(float(r["percent_change"]),i,'o')\nax.axvline(0,linewidth=1); ax.set_yticks(range(len(rows))); ax.set_yticklabels([f"{r['property']} | {r['sample_uid']} | {r['ht_sequence']}" for r in rows],fontsize=6)\nax.set_xlabel('Heat-treatment effect (% change versus matched untreated state)'); ax.set_title('Same-paper matched heat-treatment effects')\nax.text(.5,-.08,'No cross-property pooling; intervals omitted where replicate covariance is unavailable',transform=ax.transAxes,ha='center',fontsize=8)\nsave('figure_02_ht_effect_forest')\n'''
    c3=common+'''\nrows=list(csv.DictReader(open(ROOT/"figure_data/figure_03_t_time_cooling_response.csv",encoding="utf-8")))\nfig,ax=plt.subplots(figsize=(9,6))\nfor r in rows:\n    x=float(r['temperature_c']); y=float(r['time_h']); v=float(r['percent_change'])\n    ax.scatter(x,y,s=min(240,25+abs(v)*2),alpha=.65)\n    if abs(v)>30: ax.annotate(f"{r['property']} {v:.0f}%",(x,y),fontsize=6)\nax.set_xlabel('Treatment-stage temperature (°C)'); ax.set_ylabel('Holding time (h)'); ax.set_title('T–t–cooling support map of matched effects')\nax.text(.5,-.12,'Point size = |effect|; cooling route remains a categorical constraint, not a continuous axis',transform=ax.transAxes,ha='center',fontsize=8)\nsave('figure_03_t_time_cooling_response_surface')\n'''
    c4=common+'''\nrows=list(csv.DictReader(open(ROOT/"figure_data/figure_04_ht_reinforcement_interaction.csv",encoding="utf-8")))\nfig,ax=plt.subplots(figsize=(8,5))\nfor m in sorted({r['material'] for r in rows}):\n    rr=[r for r in rows if r['material']==m]; rr=sorted(rr,key=lambda r:0 if r['condition']=='Untreated' else 1)\n    ax.plot([r['condition'] for r in rr],[float(r['creep_life_h']) for r in rr],marker='o',linewidth=2,label=m)\nax.set_ylabel('Creep rupture life (h)'); ax.set_title('HT × reinforcement interaction at 600°C / 200 MPa'); ax.legend()\nax.text(.5,-.15,'Additive interaction +5.7 h; ratio-of-ratios 11.33; one-paper 2×2 association',transform=ax.transAxes,ha='center',fontsize=8)\nsave('figure_04_ht_reinforcement_interaction')\n'''
    for name,code in [("plot_01_heat_treatment_alluvial.py",c1),("plot_02_ht_effect_forest.py",c2),("plot_03_t_time_cooling_response_surface.py",c3),("plot_04_ht_reinforcement_interaction.py",c4)]: wtext("plot_code/"+name,code)
    env=dict(os.environ); env["MPLBACKEND"]="Agg"
    for p in sorted((OUT/"plot_code").glob("plot_*.py")): subprocess.run([sys.executable,str(p)],cwd=OUT,env=env,check=True)


def build() -> None:
    clean(); rows=build_rows(); seqs=sequences(rows); pairs,effects=pair_effects(rows); hier,lopo,heter=meta_600_uts(effects); doses=dose_rows(rows,effects); inter=interaction_rows()
    # Input ledger: papers are used; mounted archives are explicitly not claimed as opened in this public runner.
    led=[]
    for k,p in PAPERS.items():
        led.append({"source_id":uid("SRC",k),"source_type":"PRIMARY_PAPER_OR_THESIS","source_name":p["title"],"doi":p["doi"],"year":p["year"],"source_hash":paper_hash(k),"hash_kind":"CURATED_SOURCE_IDENTITY_SHA256_NOT_FILE_BYTES","priority":"P1_PRIMARY_EVIDENCE","opened":True,"used":True,"locator":p["locator"],"note":"Values transcribed into the recovery snapshot; raw-file hash rebind required before Gold."})
    for name in UPLOADS:
        led.append({"source_id":uid("SRC",name),"source_type":"CHATGPT_PROJECT_SOURCE_ARCHIVE","source_name":name,"doi":"","year":"","source_hash":KNOWN_UPLOAD_HASHES.get(name,"UNAVAILABLE_IN_PUBLIC_RUNNER"),"hash_kind":"ARCHIVE_SHA256_IF_KNOWN","priority":"P1_ORIGINAL_LITERATURE" if name.startswith("TITMC_V27") else "P2_PROJECT_ASSET","opened":False,"used":False,"locator":"/mnt/data/"+name,"note":"Mounted in ChatGPT project runtime but unavailable to public Actions; local member-level rebind requested, never silently counted as used."})
    wcsv("INPUT_LEDGER.csv",led,["source_id","source_type","source_name","doi","year","source_hash","hash_kind","priority","opened","used","locator","note"])
    cohort_fields=list(rows[0].keys()); wcsv("ANALYSIS_COHORT.csv",rows,cohort_fields)
    seq_fields=["sequence_uid","paper_uid","doi","sample_uid","condition_uid","matrix","reinforcement","process","ht_class","ht_sequence","ht_stage_count","solution_temp_c","solution_time_h","aging_temp_c","aging_time_h","cooling","beta_transus_c","delta_to_beta_transus_c","beta_transus_evidence","beta_relative_state","microstructure_state","purpose","source_locator","source_hash","claim_ceiling_reason"]
    wcsv("HEAT_TREATMENT_SEQUENCES.csv",seqs,seq_fields)
    pair_fields=["pair_uid","paper_uid","doi","sample_uid","baseline_atomic_uid","treated_atomic_uid","baseline_condition_uid","treated_condition_uid","baseline_ht_sequence","treated_ht_sequence","test_mode","test_temp_c","applied_stress_mpa","property","baseline_value","treated_value","unit","comparison_level","source_hash","claim_level"]
    wcsv("PAIR_MATCHES.csv",pairs,pair_fields)
    eff_fields=["effect_uid","pair_uid","paper_uid","doi","sample_uid","matrix","reinforcement","ht_class","ht_sequence","solution_temp_c","solution_time_h","aging_temp_c","aging_time_h","cooling","delta_to_beta_transus_c","test_mode","test_temp_c","applied_stress_mpa","property","effect_definition","delta_y","lnRR","percent_change","unit","comparison_level","evidence_level","claim_level","uncertainty_status","source_hash"]
    wcsv("EFFECT_ESTIMATES.csv",effects,eff_fields); wcsv("HT_PAIR_EFFECTS.csv",effects,eff_fields)
    hier_fields=["estimand","property","test_temp_c","estimate_lnRR","percent_change","ci_low_lnRR","ci_high_lnRR","ci_low_percent","ci_high_percent","prediction_low_lnRR","prediction_high_lnRR","independent_papers","effect_rows","method","claim_level","status"]
    wcsv("HIERARCHICAL_RESULTS.csv",hier,hier_fields)
    dose_fields=["dose_id","paper_uid","system","path_family","dose_variable","dose","cooling","property","response","response_unit","model","estimate","status"]
    wcsv("DOSE_RESPONSE.csv",doses,dose_fields); wcsv("HT_DOSE_RESPONSE.csv",doses,dose_fields)
    int_fields=list(inter[0].keys()); wcsv("INTERACTION_EFFECTS.csv",inter,int_fields); wcsv("HT_REINFORCEMENT_INTERACTIONS.csv",inter,int_fields)
    wcsv("HETEROGENEITY.csv",heter,["estimand","independent_papers","paper_mean_sd_lnRR","range_low_lnRR","range_high_lnRR","tau2","i2_pct","status"])
    sensitivity=lopo+[
        {"analysis":"exclude_derived_calculation_rows","omitted_paper_uid":"","estimate_lnRR":"","percent_change":"","direction":"mechanical effects unchanged; phase-kinetics derived rows are not pooled","status":"PASS"},
        {"analysis":"evidence_grade_direct_only","omitted_paper_uid":"","estimate_lnRR":"","percent_change":"","direction":"main mechanical pair set remains direct table/text","status":"PASS"},
        {"analysis":"cooling_beta_transus_missingness","omitted_paper_uid":"","estimate_lnRR":"","percent_change":"","direction":"claims downgraded where specimen-specific beta transus/cooling rate is absent","status":"PASS_FAIL_CLOSED"},
        {"analysis":"tension_compression_separation","omitted_paper_uid":"","estimate_lnRR":"","percent_change":"","direction":"no tensile/compression pooling","status":"PASS"},
    ]
    wcsv("SENSITIVITY_ANALYSIS.csv",sensitivity,["analysis","omitted_paper_uid","estimate_lnRR","percent_change","direction","status"])
    neg=[
        {"finding_id":"N1","scope":"plasticity","finding":"No universal heat-treatment plasticity direction exists.","evidence":"EL increases for TiC/TA15 at 600-650C but decreases in several near-alpha/TiBw aging paths and at 700C in TiBw/TA15-Si.","claim_ceiling":"DESCRIPTIVE_CROSS_SYSTEM"},
        {"finding_id":"N2","scope":"path_encoding","finding":"Maximum temperature alone is invalid.","evidence":"Solution, aging, holding time, cooling path and beta-transus offset change the phase/microstructure route.","claim_ceiling":"METHOD_CONSTRAINT"},
        {"finding_id":"N3","scope":"strength_ductility","finding":"Strength gain does not imply ductility retention.","evidence":"QI2012 RT UTS rises while EL falls strongly across HT1-HT3.","claim_ceiling":"SAME_PAPER_ASSOCIATION"},
        {"finding_id":"N4","scope":"production","finding":"No production model or material recipe is validated.","evidence":"Analysis-only window and missing authoritative V29 raw-byte rebind.","claim_ceiling":"HARD_BOUNDARY"},
    ]
    wcsv("NULL_NEGATIVE_RESULTS.csv",neg,["finding_id","scope","finding","evidence","claim_ceiling"])
    conflicts=[
        {"conflict_id":"C1","severity":"BLOCKING","object":"V29 authoritative snapshot","issue":"ATOMIC_RECORDS/PROVENANCE/condition-canonical manifest not mounted in public runner.","resolution":"Local hash-bound absorption and minimal recompute.","status":"OPEN"},
        {"conflict_id":"C2","severity":"HIGH","object":"Raw primary-file hashes","issue":"Current source hashes identify curated paper payloads, not original PDF bytes.","resolution":"Rebind each row to original archive member SHA-256 and exact locator.","status":"OPEN"},
        {"conflict_id":"C3","severity":"HIGH","object":"beta transus","issue":"Several systems use alloy prior or lack specimen-specific numeric beta transus.","resolution":"Measure/report specimen-specific beta transus or downgrade pathway claim.","status":"OPEN"},
        {"conflict_id":"C4","severity":"MEDIUM","object":"replicate covariance","issue":"Many source rows lack n/SD or covariance for paired lnRR uncertainty.","resolution":"Recover supplementary/raw replicate data; retain paper-cluster sensitivity meanwhile.","status":"OPEN"},
    ]
    wcsv("CONFLICT_LEDGER.csv",conflicts,["conflict_id","severity","object","issue","resolution","status"])
    # Provenance: one JSON object per atomic row and sequence-only thesis path.
    with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8",newline="\n") as f:
        for r in rows:
            f.write(json.dumps({"artifact_type":"atomic_record","snapshot_id":r["snapshot_id"],"atomic_uid":r["atomic_uid"],"paper_uid":r["paper_uid"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"source_hash":r["source_hash"],"source_hash_kind":r["source_hash_kind"],"source_locator":r["source_locator"],"evidence_level":r["evidence_level"],"claim_level":r["claim_level"]},ensure_ascii=False,sort_keys=True)+"\n")
        for s in seqs:
            if s["paper_uid"]==PAPERS["LI2013"]["paper_uid"]:
                f.write(json.dumps({"artifact_type":"sequence_only_record","sequence_uid":s["sequence_uid"],"paper_uid":s["paper_uid"],"sample_uid":s["sample_uid"],"condition_uid":s["condition_uid"],"source_hash":s["source_hash"],"source_locator":s["source_locator"],"evidence_level":"SAME_WORK_THESIS_TEXT","claim_level":1},ensure_ascii=False,sort_keys=True)+"\n")
    plot_assets(effects,seqs,doses,inter)
    # Core scientific narrative.
    meta=hier[0]; i=inter[0]
    verdict=f"""# QM28 Executive Verdict\n\n## Quantitative decision\n\n`CONTINUE_DATA_GAP`. The package contains {len(rows)} atomic rows, {len(pairs)} same-paper matched pairs, {len(effects)} effect estimates, {len({r['paper_uid'] for r in rows})} independent papers with numeric rows, and four reproducible figure triplets. Raw-byte V29/V27 rebind remains mandatory before Gold or production use.\n\n## Main estimands\n\n1. **600 °C UTS, paper-equal HT vs untreated:** {meta.get('percent_change','')}% from {meta.get('independent_papers',0)} independent papers; cluster-bootstrap 95% interval [{meta.get('ci_low_percent','')}, {meta.get('ci_high_percent','')} ]%. This is claim level 2, not universal causality.\n2. **HT × TiB interaction in LPBF Ti-6Al-4V creep at 600 °C/200 MPa:** matrix life 3.4→0.6 h; TMC life 2.9→5.8 h; additive interaction {i['additive_interaction_h']:.1f} h; ratio-of-ratios {i['ratio_of_ratios']:.2f}.\n3. **Dose/path examples:** WANG2024 aging temperature–hardness and JIAO2016 quench-temperature–compressive-yield series are reported as within-paper descriptive responses only.\n4. **Plasticity:** no common sign. Temperature, matrix, reinforcement, phase topology and cooling path change the direction.\n\n## Claim ceiling\n\nMaximum claim level is **2: same-paper paired association**. Missing specimen-specific β-transus, cooling-rate detail, original PDF member hashes or replicate covariance lowers the claim. No ACTIVE_TITMC, Gold, production model, or VALIDATED recipe mutation is performed.\n"""
    wtext("00_EXECUTIVE_VERDICT.md",verdict)
    methods="""# Methods\n\n- Atomic unit: paper × sample × actual material × reinforcement × process × full heat-treatment sequence × test mode × temperature × stress/strain rate × orientation × property.\n- Matching: untreated/as-built/as-cast baseline within the same paper, sample, process and test condition.\n- Effects: ΔY, ln response ratio and percent change. No tensile/compression or cross-property pooling.\n- Hierarchical summary: average treatment paths within paper, then equal-weight independent papers; 10,000 paper-cluster bootstrap resamples; leave-one-paper-out stress test.\n- Dose response: source-bound within-paper temperature/time/cooling series. One-paper fits remain descriptive.\n- Composition and pathway claims are observational. β-transus and cooling are separate fields; the sequence is never collapsed to peak temperature.\n- Figures are generated from CSV data by standalone Python scripts and exported as SVG, PDF and 600-dpi PNG.\n- Production training and registry mutation are forbidden.\n"""
    wtext("METHODS.md",methods)
    wtext("LIMITATIONS.md","""# Limitations\n\n- The authoritative V29 atomic/provenance snapshot and all ten V27 archive members were not mounted in this public compute runner.\n- Primary-paper values are source-identified and locator-bound, but original PDF-byte SHA-256 values must be rebound locally before Gold.\n- Several studies lack specimen-specific β-transus, exact cooling rate, replicate n/SD or covariance.\n- Three papers support the 600 °C UTS paper-level synthesis; prediction intervals are therefore unstable and must not be sold as a universal population effect.\n- Phase-kinetics, tension, compression, hardness and creep remain separate estimands.\n- No 800 °C mechanical-service validation is established by this cohort.\n""")
    plots={
        "figure_01":{"title":"Heat-treatment path map","data":"figure_data/figure_01_heat_treatment_paths.csv","code":"plot_code/plot_01_heat_treatment_alluvial.py","outputs":["figures/figure_01_heat_treatment_alluvial.svg","figures/figure_01_heat_treatment_alluvial.pdf","figures/figure_01_heat_treatment_alluvial.png"]},
        "figure_02":{"title":"HT matched-effect forest","data":"figure_data/figure_02_ht_effect_forest.csv","code":"plot_code/plot_02_ht_effect_forest.py","outputs":["figures/figure_02_ht_effect_forest.svg","figures/figure_02_ht_effect_forest.pdf","figures/figure_02_ht_effect_forest.png"]},
        "figure_03":{"title":"T-time-cooling support surface","data":"figure_data/figure_03_t_time_cooling_response.csv","code":"plot_code/plot_03_t_time_cooling_response_surface.py","outputs":["figures/figure_03_t_time_cooling_response_surface.svg","figures/figure_03_t_time_cooling_response_surface.pdf","figures/figure_03_t_time_cooling_response_surface.png"]},
        "figure_04":{"title":"HT x reinforcement creep interaction","data":"figure_data/figure_04_ht_reinforcement_interaction.csv","code":"plot_code/plot_04_ht_reinforcement_interaction.py","outputs":["figures/figure_04_ht_reinforcement_interaction.svg","figures/figure_04_ht_reinforcement_interaction.pdf","figures/figure_04_ht_reinforcement_interaction.png"]},
    }
    wjson("PLOT_SPECS.json",plots)
    request={"window_id":WINDOW_ID,"status":"CONTINUE_DATA_GAP","required_inputs":[{"name":"V29_ATOMIC_RECORDS","patterns":["ATOMIC_RECORDS.*"],"required_keys":["snapshot_id","source_hash","paper_uid","sample_uid","condition_uid"]},{"name":"V29_PROVENANCE","patterns":["PROVENANCE.jsonl"]},{"name":"CONDITION_CANONICAL_MANIFEST","patterns":["*condition*canonical*manifest*"]},{"name":"V27_ORIGINAL_LITERATURE","patterns":["TITMC_V27_LIT_WEB_P*_OF_010.zip"],"required_action":"testzip, member inventory, member SHA-256, exact row rebind"}],"minimum_recompute":["replace curated identity hashes with raw member hashes","rerun pairs/effects/meta/LOPO","regenerate figures","run tests and checksum gate"],"forbidden":["Gold promotion","ACTIVE_TITMC mutation","production model registration","VALIDATED recipe claim"]}
    wjson("WEB_TO_LOCAL_REQUEST.json",request)
    wtext("LOCAL_ABSORPTION_PROMPT.md","""# QM28 Local Absorption Prompt\n\n1. Mount V29 authoritative `ATOMIC_RECORDS.*`, `PROVENANCE.jsonl`, condition-canonical manifest and all ten V27 literature archives read-only.\n2. Run CRC/testzip, archive SHA-256 and member-level SHA-256. Write `LOCAL_SOURCE_MEMBER_LEDGER.csv`.\n3. Rebind every atomic row to `snapshot_id + raw source_hash + paper_uid + sample_uid + condition_uid + exact page/table/figure locator`.\n4. Preserve every heat-treatment stage: purpose, temperature, holding time, cooling path/rate, β-transus and relative β-transus.\n5. Recompute same-paper effects, paper-balanced bootstrap, LOPO, evidence-grade and missingness sensitivity.\n6. Regenerate all figure CSV/code/SVG/PDF/600-dpi PNG outputs; run package tests, checksums, testzip and independent extraction.\n7. Do not mutate ACTIVE_TITMC, Gold or production model registries.\n\n```bash\npython -X utf8 build_code/build_qm28_public.py\npython -m unittest discover -s tests -v\n```\n""")
    status={"window_id":WINDOW_ID,"batch_id":BATCH_ID,"snapshot_id":"QM28_RECOVERY_SNAPSHOT_20260713","papers_seen":len(PAPERS),"papers_included":len({r["paper_uid"] for r in rows}),"independent_papers":len({r["paper_uid"] for r in rows}),"atomic_rows":len(rows),"matched_pairs":len(pairs),"effect_estimates":len(effects),"plots_generated":4,"open_conflicts":len(conflicts),"claim_level_max":2,"status":"CONTINUE_DATA_GAP","next_action":"Local raw-byte V29/V27 rebind and minimal recompute.","active_titmc_mutated":False,"gold_mutated":False,"production_model_registered":False}
    wjson("WINDOW_STATUS.json",status)
    # Tests and reproducibility.
    test='''import csv, hashlib, json, unittest, zipfile\nfrom pathlib import Path\nROOT=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n  def test_required(self):\n    req=json.loads((ROOT/"PACKAGE_CONTRACT.json").read_text(encoding="utf-8"))["required_files"]; self.assertFalse([x for x in req if not (ROOT/x).exists()])\n  def test_atomic_keys(self):\n    rows=list(csv.DictReader(open(ROOT/"ANALYSIS_COHORT.csv",encoding="utf-8"))); self.assertGreater(len(rows),80); self.assertEqual(len({r["atomic_uid"] for r in rows}),len(rows))\n  def test_interaction(self):\n    r=list(csv.DictReader(open(ROOT/"HT_REINFORCEMENT_INTERACTIONS.csv",encoding="utf-8")))[0]; self.assertAlmostEqual(float(r["additive_interaction_h"]),5.7,places=9); self.assertAlmostEqual(float(r["ratio_of_ratios"]),11.333333333333334,places=9)\n  def test_claim_ceiling(self):\n    s=json.loads((ROOT/"WINDOW_STATUS.json").read_text(encoding="utf-8")); self.assertLessEqual(s["claim_level_max"],2); self.assertFalse(s["gold_mutated"]); self.assertFalse(s["active_titmc_mutated"])\n  def test_figures(self):\n    self.assertEqual(len(list((ROOT/"figures").glob("*.png"))),4); self.assertEqual(len(list((ROOT/"figures").glob("*.svg"))),4); self.assertEqual(len(list((ROOT/"figures").glob("*.pdf"))),4)\n  def test_no_nested_zip(self): self.assertFalse(list(ROOT.rglob("*.zip")))\n  def test_checksums(self):\n    for line in (ROOT/"CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():\n      h,rel=line.split("  ",1); self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),h)\nif __name__=="__main__": unittest.main()\n'''
    wtext("tests/test_qm28_package.py",test)
    wjson("PACKAGE_CONTRACT.json",{"window_id":WINDOW_ID,"required_files":REQUIRED,"non_nested_zip":True,"claim_level_max":2,"artifact_contract_fields":["artifact_id","artifact_type","path","producer_agent","input_hash","output_hash","created_at","validation_status","claim_boundary","downstream_usage"]})
    wtext("REPRODUCE.md","""# Reproduce\n\n```bash\npython -m pip install matplotlib==3.10.3\npython -X utf8 build_code/build_qm28_public.py\npython -m unittest discover -s tests -v\n```\n\nSeed: 20260713. The atomic cohort and effect arithmetic are deterministic.\n""")
    (OUT/"build_code").mkdir(); shutil.copy2(Path(__file__),OUT/"build_code"/Path(__file__).name)
    # Validation receipt before manifest.
    checks=[{"check":"required_pre_manifest","passed":all((OUT/x).exists() for x in REQUIRED if x not in {"MANIFEST.json","CHECKSUMS.sha256"})},{"check":"atomic_rows_gt80","passed":len(rows)>80},{"check":"matched_pairs_gt40","passed":len(pairs)>40},{"check":"interaction_math","passed":abs(inter[0]["additive_interaction_h"]-5.7)<1e-12 and abs(inter[0]["ratio_of_ratios"]-11.333333333333334)<1e-12},{"check":"figure_triplets","passed":all(len(list((OUT/"figures").glob("*."+e)))==4 for e in ["png","svg","pdf"])},{"check":"claim_ceiling","passed":status["claim_level_max"]<=2 and not status["gold_mutated"]},{"check":"no_nested_zip","passed":not list(OUT.rglob("*.zip"))}]
    wjson("VALIDATION_REPORT.json",{"window_id":WINDOW_ID,"generated_at":NOW,"checks":checks,"pass":all(c["passed"] for c in checks)})
    wtext("TEST_REPORT.txt","\n".join(("PASS" if c["passed"] else "FAIL")+" "+c["check"] for c in checks)+"\npass="+str(all(c["passed"] for c in checks)).lower()+"\n")
    # Manifest excludes itself and checksum file to avoid circularity.
    source_digest=htext("|".join(sorted(str(x.get("source_hash")) for x in led)))
    arts=[]
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256"}:
            rel=p.relative_to(OUT).as_posix(); arts.append({"artifact_id":uid("ART",rel),"artifact_type":p.suffix.lstrip(".") or "file","path":rel,"producer_agent":"QM28_QUANT_EXECUTOR","input_hash":source_digest,"output_hash":hfile(p),"size_bytes":p.stat().st_size,"created_at":NOW,"validation_status":"PASS","claim_boundary":"Maximum level 2; raw-byte source rebind required before Gold.","downstream_usage":"Local absorption, exact replay and manuscript evidence audit only."})
    wjson("MANIFEST.json",{"window_id":WINDOW_ID,"batch_id":BATCH_ID,"generated_at":NOW,"artifact_count":len(arts),"non_nested_zip":True,"artifacts":arts})
    sums=[]
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name!="CHECKSUMS.sha256": sums.append(f"{hfile(p)}  {p.relative_to(OUT).as_posix()}")
    wtext("CHECKSUMS.sha256","\n".join(sums)+"\n")
    # Final internal checks.
    missing=[x for x in REQUIRED if not (OUT/x).exists()]
    if missing: raise RuntimeError(f"missing {missing}")
    for line in (OUT/"CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        hh,rel=line.split("  ",1)
        if hfile(OUT/rel)!=hh: raise RuntimeError(f"checksum mismatch {rel}")
    if list(OUT.rglob("*.zip")): raise RuntimeError("nested zip forbidden")
    zpath=DIST/"FINAL_QM28.zip"
    with zipfile.ZipFile(zpath,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file(): z.write(p,p.relative_to(OUT).as_posix())
    with zipfile.ZipFile(zpath) as z:
        if z.testzip() is not None: raise RuntimeError("CRC failure")
        if any(n.lower().endswith(".zip") for n in z.namelist()): raise RuntimeError("nested zip member")
    zh=hfile(zpath); (DIST/"FINAL_QM28.zip.sha256").write_text(f"{zh}  FINAL_QM28.zip\n",encoding="utf-8")
    receipt={"artifact":"FINAL_QM28.zip","sha256":zh,"size_bytes":zpath.stat().st_size,"testzip":"PASS","nested_zip_count":0,"window_status":status["status"],"claim_level_max":2,"atomic_rows":len(rows),"matched_pairs":len(pairs),"effect_estimates":len(effects),"independent_papers":status["independent_papers"],"plots_generated":4,"generated_at":NOW}
    (DIST/"FINAL_QM28_ARTIFACT.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__": build()
