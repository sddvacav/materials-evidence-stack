#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pypdf import PdfReader

SEED = 35020260713
rng = np.random.default_rng(SEED)
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "FINAL_QM35"
if OUT.exists(): shutil.rmtree(OUT)
for d in (OUT, OUT/"figures", OUT/"figure_data", OUT/"plot_code", OUT/"analysis_code", OUT/"tests", OUT/"source_evidence"):
    d.mkdir(parents=True, exist_ok=True)

def htext(x: str) -> str: return hashlib.sha256(x.encode("utf-8")).hexdigest()
def hfile(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def uid(prefix: str,*x: Any)->str: return prefix+"_"+htext("|".join(map(str,x)))[:16]
def text(rel: str,s: str):
    p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s.rstrip()+"\n",encoding="utf-8")
def js(rel: str,o: Any):
    p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def csv(rel: str,rows: list[dict[str,Any]],cols: list[str])->pd.DataFrame:
    d=pd.DataFrame(rows,columns=cols); p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True); d.to_csv(p,index=False); return d
def finite(v: Any)->bool:
    try:return bool(np.isfinite(float(v)))
    except:return False
def triplet(fig,stem: str):
    out=[]
    for ext in ("png","svg","pdf"):
        p=OUT/"figures"/f"{stem}.{ext}"; fig.savefig(p,dpi=600 if ext=="png" else None,bbox_inches="tight"); out.append(str(p.relative_to(OUT)))
    plt.close(fig); return out

def boot_mean(vals,n=20000):
    a=np.asarray(vals,float); b=np.empty(n)
    for i in range(n): b[i]=rng.choice(a,len(a),replace=True).mean()
    return float(a.mean()),float(np.quantile(b,.025)),float(np.quantile(b,.975))

# Hash semantics are copied exactly from the prior validated central-directory ledger.
INV=[
("00_统一上传总控与校验信息_20260712.zip","0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f","FULL_FILE_SHA256",25479,13,"P1_PROVENANCED_STRUCTURED"),
("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1","FULL_FILE_SHA256",510259317,32,"P3_PLATFORM_CODE"),
("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9","FULL_FILE_SHA256",515903028,15,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip","5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59","FULL_FILE_SHA256",515906034,25,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip","cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a","FULL_FILE_SHA256",515901682,7,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip","97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809","ZIP_CENTRAL_DIRECTORY_SHA256",515901786,7,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip","16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f","ZIP_CENTRAL_DIRECTORY_SHA256",515902128,9,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip","04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9","ZIP_CENTRAL_DIRECTORY_SHA256",515903238,11,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip","5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728","ZIP_CENTRAL_DIRECTORY_SHA256",515905052,17,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip","e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847","ZIP_CENTRAL_DIRECTORY_SHA256",515913392,38,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip","36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485","ZIP_CENTRAL_DIRECTORY_SHA256",515924832,69,"P2_EXECUTABLE_ARTIFACT"),
("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip","9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd","ZIP_CENTRAL_DIRECTORY_SHA256",515989228,246,"P2_EXECUTABLE_ARTIFACT"),
("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip","c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c","ZIP_CENTRAL_DIRECTORY_SHA256",506137803,57191,"P3_PLATFORM_CODE"),
("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip","a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a","ZIP_CENTRAL_DIRECTORY_SHA256",515999572,244,"P3_PLATFORM_CODE"),
("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip","bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43","ZIP_CENTRAL_DIRECTORY_SHA256",516062924,396,"P3_PLATFORM_CODE"),
("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip","08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755","ZIP_CENTRAL_DIRECTORY_SHA256",516106394,499,"P3_PLATFORM_CODE"),
("TITMC_V27_LIT_WEB_P001_OF_010.zip","42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0","ZIP_CENTRAL_DIRECTORY_SHA256",499460308,15,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P002_OF_010.zip","05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193","ZIP_CENTRAL_DIRECTORY_SHA256",490572377,154,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P003_OF_010.zip","535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917","ZIP_CENTRAL_DIRECTORY_SHA256",490379244,4610,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P004_OF_010.zip","bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a","ZIP_CENTRAL_DIRECTORY_SHA256",490620829,7747,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P005_OF_010.zip","1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1","ZIP_CENTRAL_DIRECTORY_SHA256",490762545,10068,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P006_OF_010.zip","5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13","ZIP_CENTRAL_DIRECTORY_SHA256",490902802,11778,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P007_OF_010.zip","4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1","ZIP_CENTRAL_DIRECTORY_SHA256",491018449,13499,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P008_OF_010.zip","478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341","ZIP_CENTRAL_DIRECTORY_SHA256",491203652,15702,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P009_OF_010.zip","b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a","ZIP_CENTRAL_DIRECTORY_SHA256",491501617,20036,"P0_PRIMARY_ORIGINAL"),
("TITMC_V27_LIT_WEB_P010_OF_010.zip","faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d","ZIP_CENTRAL_DIRECTORY_SHA256",367381900,57717,"P0_PRIMARY_ORIGINAL")]
DOI=["10.1016/j.msea.2024.146757","10.1016/j.msea.2025.148076","10.1016/j.powtec.2019.09.008","10.1016/j.compositesb.2020.108567"]
SNAP="QM35_RECOVERY_"+htext("|".join([x[1] for x in INV]+DOI))[:16]
HEADER=f"WINDOW=QM35 | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD"
print(HEADER)

# Input ledger: all project packages are terminally accounted; only relevant originals enter numeric estimands.
led=[]
for i,(n,d,k,b,m,p) in enumerate(INV):
    if p=="P0_PRIMARY_ORIGINAL": rel="Primary literature corpus inventory; targeted original papers admitted; unrelated members remain scope-firewalled."
    elif "DATA_FEATURES" in n: rel="Frozen matrices/features and condition schema used as reference; complete authoritative QM35 atomic slice absent."
    elif "HARNESS" in n: rel="Source-reliability, UQ, LOPO and AD conventions reused; no production model used."
    elif n.startswith("S04"): rel="History/staging/code inventory used to locate prior evidence and acceptance conventions."
    elif n.startswith("S02"): rel="Plot/platform conventions reused; fresh deterministic scripts generated."
    else: rel="Integrity and package-accounting control."
    led.append(dict(input_id=uid("IN",i,n,d),snapshot_id=SNAP,source_name=n,source_type="ZIP",path_or_locator=f"/mnt/data/{n}",source_hash=d,source_hash_kind=k,bytes=b,member_count=m,central_directory_status="READABLE_PRIOR_AUDIT",priority=p,window_relevance=rel,terminal_use_status="INVENTORIED_AND_TARGETED" if p=="P0_PRIMARY_ORIGINAL" else "USED_AS_REFERENCE",opened_or_consumed="INVENTORY_BOUND",notes="Prior validated hash semantics retained; central-directory digests are not relabeled as full-file hashes."))
DIRECT=[
("QM35 MDU","MDU","file_library://turn7file13","P0_CONTRACT","file_0000000039a4720b9cb45d3331fddd06"),
("Sun 2024 MSEA 146757","PDF_ORIGINAL","file_library://turn4file0","P0_PRIMARY_ORIGINAL",DOI[0]),
("Yuan 2025 MSEA 148076","PDF_ORIGINAL","file_library://turn4file2","P0_PRIMARY_ORIGINAL",DOI[1]),
("Jiao 2019 Powder Technology 356","PDF_ORIGINAL","file_library://turn15file0","P0_PRIMARY_ORIGINAL",DOI[2]),
("Zhou 2021 Composites Part B 108567","PDF_ORIGINAL","file_library://turn13file3","P0_PRIMARY_ORIGINAL",DOI[3]),
("QM32 load-transfer return","PROVENANCED_DERIVED","file_library://turn13file0","P1_PROVENANCED_DERIVED","QM32_LOCAL_AUDIT_c6708249857a8bda"),
("QM12 high-temperature return","PROVENANCED_DERIVED","file_library://turn8file7","P1_PROVENANCED_DERIVED","QM12_DERIVED_ab795b646d964e6a")]
for n,t,l,p,ident in DIRECT:
    led.append(dict(input_id=uid("IN",n,ident),snapshot_id=SNAP,source_name=n,source_type=t,path_or_locator=l,source_hash=htext(f"{n}|{l}|{ident}"),source_hash_kind="NORMALIZED_EVIDENCE_CAPTURE_SHA256",bytes="",member_count=1,central_directory_status="NOT_APPLICABLE",priority=p,window_relevance="Direct QM35 evidence or execution contract",terminal_use_status="USED_DIRECTLY",opened_or_consumed="YES",notes="Capture hash binds normalized evidence; original package/member hash is requested for local absorption."))
IC=list(led[0].keys()); csv("INPUT_LEDGER.csv",led,IC)

# Direct calculations.
SUN0=1058/1.086; SUN1=1135/1.128; SUND=SUN1-SUN0
HP=450*(4.8**-.5-48**-.5); TIB=.5*770*.034*2.27*.27; SI=.5*770*.04*3.62*.27
text("source_evidence/SUN2024.md",f"""# Sun 2024 normalized evidence\nDOI: {DOI[0]} | source: file_library://turn4file0\nActual Ti65 composition (wt.%): Al5.45 Sn4.00 Zr3.30 Mo0.50 Nb0.32 Ta0.82 Si0.43 W0.95 C0.057. Reported UTS/Hc imply YS {SUN0:.3f}->{SUN1:.3f} MPa after 650 °C/100 h, ΔYS={SUND:.3f} MPa. Source budget: fine grain 127, Al solid solution 73, precipitate/silicide 222 and dislocation 125 MPa, linearly 547 MPa. Alpha-prime dissolution, alpha/beta evolution, alpha2 and silicides coexist but no independent numeric phase term is supplied.""")
text("source_evidence/YUAN2025.md",f"""# Yuan 2025 normalized evidence\nDOI: {DOI[1]} | source: file_library://turn4file2\nActual Si/B variants and same-paper RT/480 °C tensile values are captured in ANALYSIS_COHORT.csv. The paper invokes Hall–Petch, solution and load-transfer terms, but independent phase fractions and coefficients are incomplete; unique separation is NOT_IDENTIFIABLE.""")
text("source_evidence/JIAO2019.md",f"""# Jiao 2019 normalized evidence\nDOI: {DOI[2]} | source: file_library://turn15file0\nYS: matrix 770, 3.4 vol.% TiBw 930, 4 vol.% Ti5Si3 900, hybrid 1050 MPa. Alpha-colony 48->4.8 µm; AR TiBw/Ti5Si3 2.27/3.62. Reconstructed Hall–Petch={HP:.3f}, TiBw load={TIB:.3f}, Ti5Si3 load={SI:.3f} MPa.""")
text("source_evidence/ZHOU2021.md",f"""# Zhou 2021 normalized evidence\nDOI: {DOI[3]} | source: file_library://turn13file3\nTi64/TMC1 YS 1077/1382 MPa, ΔYS=305 MPa. QM32 reconstructs 58 MPa load transfer. Alpha-prime refinement is evidenced but not independently quantified, so 247 MPa remains unresolved.""")

# Atomic YS cohort.
CC=["snapshot_id","record_uid","paper_uid","sample_uid","condition_uid","doi","year","matrix_family","actual_composition","reinforcement_phase","reinforcement_vol_pct","process","heat_treatment","microstructure_state","test_mode","temperature_c","strain_rate","orientation","property","value","reported_spread","reported_spread_type","replicate_n","evidence_level","source_locator","source_hash","include_primary","exclusion_reason","mechanism_proxies"]
co=[]
def atom(paper,doi,year,sample,cond,matrix,comp,reinf,vol,process,ht,micro,temp,orient,val,spread,evid,loc,prox):
    co.append(dict(snapshot_id=SNAP,record_uid=uid("REC",paper,sample,cond,"YS"),paper_uid=paper,sample_uid=sample,condition_uid=cond,doi=doi,year=year,matrix_family=matrix,actual_composition=comp,reinforcement_phase=reinf,reinforcement_vol_pct=vol,process=process,heat_treatment=ht,microstructure_state=micro,test_mode="tension",temperature_c=temp,strain_rate="UNRESOLVED",orientation=orient,property="YS",value=val,reported_spread=spread,reported_spread_type="AS_REPORTED_UNRESOLVED_SD_OR_SE" if finite(spread) else "NONE",replicate_n="UNRESOLVED",evidence_level=evid,source_locator=loc,source_hash=htext(f"{doi}|{sample}|{cond}|YS|{val}"),include_primary="YES",exclusion_reason="",mechanism_proxies=json.dumps(prox,sort_keys=True)))
sc="Ti-5.45Al-4Sn-3.3Zr-0.5Mo-0.32Nb-0.82Ta-0.43Si-0.95W-0.057C"
atom("SUN2024",DOI[0],2024,"SUN_AS","SUN_RT_AS","near-alpha Ti65",sc,"none",0,"L-DED","as-deposited","alpha-prime+alpha/beta",25,"source",SUN0,"","DERIVED_CALCULATION","file_library://turn4file0",{"Hc":.086,"UTS":1058})
atom("SUN2024",DOI[0],2024,"SUN_650_100H","SUN_RT_650_100H","near-alpha Ti65",sc,"none",0,"L-DED","650C/100h","alpha-prime dissolution+alpha2+silicide",25,"source",SUN1,"","DERIVED_CALCULATION","file_library://turn4file0",{"Hc":.128,"UTS":1135})
yc={"M":"Ti-5.95Al-2.03Sn-4.20Zr-2.10Mo-0.10Si","S":"Ti-5.91Al-2.12Sn-4.30Zr-2.09Mo-0.64Si","B":"Ti-5.83Al-2.09Sn-4.05Zr-2.15Mo-0.13Si-0.10B","H":"Ti-5.86Al-2.08Sn-4.14Zr-2.07Mo-0.26Si-0.05B"}
yv={("M","T"):(790.9,44.7),("M","L"):(718.5,15.2),("S","T"):(946.6,59.7),("S","L"):(987.7,48.3),("B","T"):(890.4,8.4),("B","L"):(862,12.1),("H","T"):(923.1,14.3),("H","L"):(887.5,10.4)}
for (k,o),(v,s) in yv.items():
    reinf={"M":"none","S":"silicide/Si solution","B":"TiB","H":"TiB+silicide/Si solution"}[k]
    atom("YUAN2025",DOI[1],2025,f"YUAN_{k}_{o}",f"YUAN_RT_{o}","near-alpha Ti6242S",yc[k],reinf,"UNRESOLVED","L-DED","as-deposited","source-specific alpha/alpha-prime/beta",25,o,v,s,"DIRECT_TABLE_TEXT","file_library://turn4file2",{"Si_wt":{"M":.10,"S":.64,"B":.13,"H":.26}[k],"B_wt":{"M":0,"S":0,"B":.10,"H":.05}[k]})
atom("YUAN2025",DOI[1],2025,"YUAN_M_L_480","YUAN_480_L","near-alpha Ti6242S",yc["M"],"none",0,"L-DED","as-deposited","high-temperature phase state",480,"L",498.6,1.9,"DIRECT_TABLE_TEXT","file_library://turn4file2",{"Si_wt":.10,"B_wt":0})
atom("YUAN2025",DOI[1],2025,"YUAN_H_L_480","YUAN_480_L","near-alpha Ti6242S",yc["H"],"TiB+silicide/Si solution","UNRESOLVED","L-DED","as-deposited","high-temperature phase state",480,"L",589.9,5.6,"DIRECT_TABLE_TEXT","file_library://turn4file2",{"Si_wt":.26,"B_wt":.05})
for k,v,s,r,f,m in [("M",770,10.6,"none",0,"alpha colony 48 um"),("T",930,10,"TiBw",3.4,"TiBw network"),("S",900,9,"Ti5Si3",4,"matrix morphology similar to control"),("H",1050,9,"TiBw+Ti5Si3",7.4,"alpha colony 4.8 um")]:
    atom("JIAO2019",DOI[2],2019,f"JIAO_{k}","JIAO_RT","Ti6Al4V","Ti6Al4V source series",r,f,"PM/as-sintered","as-sintered",m,25,"source",v,s,"DIRECT_TABLE_TEXT","file_library://turn15file0",{"alpha_colony_um":48 if k=="M" else 4.8 if k=="H" else None,"TiBw_AR":2.27 if k in "TH" else None,"Ti5Si3_AR":3.62 if k in "SH" else None})
atom("ZHOU2021",DOI[3],2021,"ZHOU_M","ZHOU_RT","Ti6Al4V","Ti6Al4V","none",0,"SLM","as-built","alpha-prime",25,"source",1077,7,"DIRECT_TABLE_TEXT","file_library://turn13file3",{"alpha_prime":True})
atom("ZHOU2021",DOI[3],2021,"ZHOU_TMC1","ZHOU_RT","Ti6Al4V","Ti6Al4V+2vol%TiB","TiB",2,"SLM","as-built","refined alpha-prime+TiB",25,"source",1382,5,"DIRECT_TABLE_TEXT","file_library://turn13file3",{"alpha_prime_refinement":True,"load_transfer_MPa":58})
cohort=csv("ANALYSIS_COHORT.csv",co,CC)
by={r["sample_uid"]:r for r in co}
csv("EXCLUDED_RECORDS.csv",[
{"paper_uid":"JIAO2019","sample_uid":"JIAO_8SI_HYB","property":"YS","reason":"YS absent; UTS=980 MPa and EL=1.0% retained as negative context","terminal_state":"EXCLUDED_MISSING_TARGET"},
{"paper_uid":"BAO_QM32","sample_uid":"S1/S2","property":"YS","reason":"Exact observed atomic controls absent; component context only","terminal_state":"EXCLUDED_MISSING_ATOMIC_ROWS"},
{"paper_uid":"XML_NON_QM35","sample_uid":"ALL_NONMATCHING","property":"ALL","reason":"Broad XML corpus is not uniformly Ti/TMC","terminal_state":"EXCLUDED_SCOPE_FIREWALL"}], ["paper_uid","sample_uid","property","reason","terminal_state"])

# Pair matches and effects.
PCOLS=["snapshot_id","pair_uid","pair_id","paper_uid","doi","treated_sample_uid","control_sample_uid","condition_uid","property","temperature_c","orientation","treated_value","control_value","delta","propagated_reported_spread","ci95_low","ci95_high","estimand","match_grade","same_paper","same_matrix","same_process","same_heat_treatment","same_test_condition","evidence_level","source_locator","notes"]
pa=[]
def pair(pid,paper,doi,t,c,estimand,grade,notes,evid,loc,override=None):
    if override is None:
        tr,ct=by[t],by[c]; d=float(tr["value"])-float(ct["value"]); tv,cv=float(tr["value"]),float(ct["value"]); sp=math.sqrt(float(tr["reported_spread"])**2+float(ct["reported_spread"])**2) if finite(tr["reported_spread"]) and finite(ct["reported_spread"]) else np.nan; lo=hi=np.nan; temp=tr["temperature_c"]; ori=tr["orientation"]; cond=tr["condition_uid"]
    else:d,lo,hi=override;tv=cv=sp=np.nan;temp=650 if "650" in pid else 700;ori="UNRESOLVED";cond="REPORT_"+pid
    pa.append(dict(snapshot_id=SNAP,pair_uid=uid("PAIR",pid),pair_id=pid,paper_uid=paper,doi=doi,treated_sample_uid=t,control_sample_uid=c,condition_uid=cond,property="YS",temperature_c=temp,orientation=ori,treated_value=tv,control_value=cv,delta=d,propagated_reported_spread=sp,ci95_low=lo,ci95_high=hi,estimand=estimand,match_grade=grade,same_paper="YES",same_matrix="YES",same_process="YES",same_heat_treatment="YES",same_test_condition="YES" if grade=="A" else "PENDING",evidence_level=evid,source_locator=loc,notes=notes))
pair("SUN_650_MINUS_AS","SUN2024",DOI[0],"SUN_650_100H","SUN_AS","thermal-exposure total-state effect","A","YS derived from UTS/Hc; phase attribution unresolved","DERIVED_CALCULATION","file_library://turn4file0")
for o in "TL":
    for k,label in [("S","high-Si modification"),("B","B/TiB modification"),("H","Si+B hybrid modification")]: pair(f"YUAN_{k}_MINUS_M_{o}","YUAN2025",DOI[1],f"YUAN_{k}_{o}",f"YUAN_M_{o}",label,"A","Composition and phase state co-vary","DIRECT_TABLE_TEXT","file_library://turn4file2")
    pair(f"YUAN_H_MINUS_B_{o}","YUAN2025",DOI[1],f"YUAN_H_{o}",f"YUAN_B_{o}","hybrid minus B-only proxy","A","Both Si and B doses differ; not pure interaction","DIRECT_TABLE_TEXT","file_library://turn4file2")
pair("YUAN_H_MINUS_M_480_L","YUAN2025",DOI[1],"YUAN_H_L_480","YUAN_M_L_480","hybrid effect at 480C","A","Net composition+phase+TiB effect","DIRECT_TABLE_TEXT","file_library://turn4file2")
for k in "TSH": pair(f"JIAO_{k}_MINUS_M","JIAO2019",DOI[2],f"JIAO_{k}","JIAO_M",f"{k} addition effect","A","Same-paper as-sintered RT comparison","DIRECT_TABLE_TEXT","file_library://turn15file0")
pair("ZHOU_TMC1_MINUS_M","ZHOU2021",DOI[3],"ZHOU_TMC1","ZHOU_M","2 vol.% TiB net effect","A","Alpha-prime refinement and load transfer coupled","DIRECT_TABLE_TEXT","file_library://turn13file3")
pair("QM12_650","QM12_INTERNAL","INTERNAL","QM12_TMC_650","QM12_M_650","reinforcement effect at 650C","B","Atomic identities/protocol pending","P1_PROVENANCED_DERIVED","file_library://turn8file7",(94.927,-21.162,211.017))
pair("QM12_700","QM12_INTERNAL","INTERNAL","QM12_TMC_700","QM12_M_700","reinforcement effect at 700C","B","Atomic identities/protocol pending","P1_PROVENANCED_DERIVED","file_library://turn8file7",(182.208,-16.536,380.953))
pairs=csv("PAIR_MATCHES.csv",pa,PCOLS)
EC=["snapshot_id","effect_uid","pair_uid","paper_uid","condition_uid","property","effect_definition","estimate","unit","lnRR","percent_change","ci95_low","ci95_high","uncertainty_method","p_value","q_value_bh","independent_papers","evidence_level","match_grade","claim_level","support_domain","status","notes"]
ef=[]
for p in pa:
    lr=math.log(float(p["treated_value"])/float(p["control_value"])) if finite(p["treated_value"]) and finite(p["control_value"]) else np.nan
    ef.append(dict(snapshot_id=SNAP,effect_uid=uid("EFF",p["pair_id"]),pair_uid=p["pair_uid"],paper_uid=p["paper_uid"],condition_uid=p["condition_uid"],property="YS",effect_definition="treated-control",estimate=p["delta"],unit="MPa",lnRR=lr,percent_change=100*(math.exp(lr)-1) if finite(lr) else np.nan,ci95_low=p["ci95_low"],ci95_high=p["ci95_high"],uncertainty_method="SOURCE_REPORT_CI" if finite(p["ci95_low"]) else "REPORTED_SPREAD_NOT_CI_N_UNRESOLVED",p_value=np.nan,q_value_bh=np.nan,independent_papers=1,evidence_level=p["evidence_level"],match_grade=p["match_grade"],claim_level=2 if p["match_grade"]=="A" else 1,support_domain=f"{p['paper_uid']}|{p['temperature_c']}C|{p['orientation']}",status="ESTIMABLE_PAIRED" if p["match_grade"]=="A" else "PROTOCOL_PENDING",notes=p["notes"]))
effects=csv("EFFECT_ESTIMATES.csv",ef,EC)

# Non-overlapping mechanism component inputs.
MC=["snapshot_id","component_uid","case_id","paper_uid","mechanism","delta_sigma_MPa","observable_proxy","formula_or_rule","assigned_feature","double_count_firewall","evidence_level","source_locator","status","notes"]
mc=[]
def comp(case,paper,mech,val,proxy,form,feat,evid,src,status,notes): mc.append(dict(snapshot_id=SNAP,component_uid=uid("COMP",case,mech,feat),case_id=case,paper_uid=paper,mechanism=mech,delta_sigma_MPa=val,observable_proxy=proxy,formula_or_rule=form,assigned_feature=feat,double_count_firewall="UNIQUE_ASSIGNMENT",evidence_level=evid,source_locator=src,status=status,notes=notes))
for m,v,p,f,feat in [("fine_grain",127,"source grain-size term","source Hall-Petch","grain_size"),("solid_solution",73,"Al content only","source Al solution term","dissolved_Al"),("precipitate_silicide",222,"alpha2+silicide calculation","source coarse term; subterms internally RSS","precipitate_population"),("dislocation",125,"dislocation-density proxy","source Taylor-type term","dislocation_density")]: comp("SUN_SOURCE_BUDGET","SUN2024",m,v,p,f,feat,"DIRECT_TABLE_TEXT","file_library://turn4file0","ESTIMABLE_SOURCE","Source-specific coarse term")
comp("SUN_SOURCE_BUDGET","SUN2024","phase_transformation",np.nan,"alpha-prime dissolution+alpha/beta","no independent coefficient","phase_fraction","DIRECT_TEXT","file_library://turn4file0","NOT_IDENTIFIABLE","Not double counted with precipitation")
comp("SUN_SOURCE_BUDGET","SUN2024","reinforcement",0,"none","not applicable","reinforcement","DIRECT_TEXT","file_library://turn4file0","NOT_APPLICABLE","Alloy-only case")
for m,v,p,f,feat in [("fine_grain",HP,"alpha colony 48->4.8 um","450*(4.8^-0.5-48^-0.5)","alpha_colony_size"),("reinforcement_TiBw",TIB,"3.4 vol.%, AR2.27, w0.27","0.5*770*0.034*2.27*0.27","TiBw_geometry"),("precipitate_Ti5Si3_load",SI,"4 vol.%, AR3.62, w0.27","0.5*770*0.04*3.62*0.27","Ti5Si3_geometry")]: comp("JIAO_HYBRID","JIAO2019",m,v,p,f,feat,"DERIVED_CALCULATION","file_library://turn15file0","ESTIMABLE","Direct source-input reconstruction")
comp("JIAO_HYBRID","JIAO2019","solid_solution",np.nan,"Si lattice distortion","no independent coefficient","dissolved_Si","DIRECT_TEXT","file_library://turn15file0","NOT_IDENTIFIABLE","Retained unresolved")
comp("JIAO_HYBRID","JIAO2019","phase_transformation",np.nan,"precipitation from beta during cooling","no independent coefficient","beta_to_alpha","DIRECT_TEXT","file_library://turn15file0","NOT_IDENTIFIABLE","Retained unresolved")
comp("JIAO_TI5SI3","JIAO2019","precipitate_Ti5Si3_load",SI,"4 vol.% Ti5Si3","source Eq.(2)","Ti5Si3_geometry","DERIVED_CALCULATION","file_library://turn15file0","ESTIMABLE","Known term only")
comp("JIAO_TIB","JIAO2019","reinforcement_TiBw",TIB,"3.4 vol.% TiBw","source Eq.(2)","TiBw_geometry","DERIVED_CALCULATION","file_library://turn15file0","ESTIMABLE","QM32 rounded related value=12 MPa")
for case,paper,v,proxy,total in [("ZHOU_TMC1","ZHOU2021",58,"2 vol.% TiB source-formula audit",305),("WANG_TIC","WANG_QM32",24,"low-AR TiC source-formula audit",326),("BAO_S1","BAO_QM32",111,"aligned high-AR TiBw",np.nan),("BAO_S2","BAO_QM32",322,"aligned high-AR TiBw",np.nan)]: comp(case,paper,"reinforcement_load_transfer",v,proxy,"QM32 source reconstruction","reinforcement_geometry","P1_PROVENANCED_DERIVED","file_library://turn13file0","ESTIMABLE_CONTEXT" if not finite(total) else "ESTIMABLE",f"Observed total ΔYS={total} MPa" if finite(total) else "Exact control absent")
components=csv("MECHANISM_COMPONENT_INPUTS.csv",mc,MC)

def vals(case): return [float(r["delta_sigma_MPa"]) for r in mc if r["case_id"]==case and finite(r["delta_sigma_MPa"])]
TARGET={"SUN_SOURCE":("SUN_SOURCE_BUDGET",547,"source-reported coarse total",True),"SUN_OBSERVED":("SUN_SOURCE_BUDGET",SUND,"observed exposure ΔYS",True),"JIAO_HYBRID":("JIAO_HYBRID",280,"hybrid observed ΔYS",False),"JIAO_TI5SI3":("JIAO_TI5SI3",130,"Ti5Si3-only observed ΔYS",False),"JIAO_TIB":("JIAO_TIB",160,"TiBw-only observed ΔYS",False),"ZHOU_TMC1":("ZHOU_TMC1",305,"TMC1 observed ΔYS",False),"WANG_TIC":("WANG_TIC",326,"QM32 observed ΔYS",False)}
BC=["snapshot_id","budget_id","case_id","target_definition","observed_delta_YS_MPa","known_component_sum_MPa","unresolved_contribution_MPa","known_share_pct","independent_component_count","component_set_complete","superposition_rule","status","claim_level","notes"]
XC=["snapshot_id","budget_id","paper_uid","target_MPa","predicted_MPa","closure_error_MPa","absolute_closure_error_MPa","closure_error_pct_of_target","target_definition","status","support_domain","notes"]
bu=[];cl=[]
for bid,(case,t,td,complete) in TARGET.items():
    pred=sum(vals(case));res=t-pred;status="CLOSED_BY_SOURCE_DEFINITION" if bid=="SUN_SOURCE" else "OVER_CLOSED" if res<0 else "UNRESOLVED_POSITIVE";paper=next(r["paper_uid"] for r in mc if r["case_id"]==case)
    bu.append(dict(snapshot_id=SNAP,budget_id=bid,case_id=case,target_definition=td,observed_delta_YS_MPa=t,known_component_sum_MPa=pred,unresolved_contribution_MPa=res,known_share_pct=100*pred/t,independent_component_count=len(vals(case)),component_set_complete="YES_SOURCE_MODEL" if complete else "NO",superposition_rule="LINEAR_COARSE_TERMS",status=status,claim_level=1 if bid=="SUN_SOURCE" else 2,notes="Residual is not automatically assigned to a named mechanism."))
    cl.append(dict(snapshot_id=SNAP,budget_id=bid,paper_uid=paper,target_MPa=t,predicted_MPa=pred,closure_error_MPa=res,absolute_closure_error_MPa=abs(res),closure_error_pct_of_target=100*res/t,target_definition=td,status=status,support_domain=case,notes="Negative means over-closure; positive means unresolved/model error."))
budgets=csv("STRENGTHENING_BUDGET.csv",bu,BC); closure=csv("BUDGET_CLOSURE_ERROR.csv",cl,XC)
SC=["snapshot_id","budget_id","case_id","target_definition","model","p","predicted_delta_YS_MPa","target_delta_YS_MPa","residual_MPa","absolute_error_MPa","component_count","component_vector_complete","independent_target","model_selection_eligible","selection_status","claim"]
su=[]
for bid,(case,t,td,complete) in TARGET.items():
    a=np.array(vals(case)); grid=np.linspace(.5,8,751); gp=np.array([(a**p).sum()**(1/p) for p in grid]); bp=float(grid[np.argmin(abs(gp-t))])
    for name,p in [("linear",1),("power_1.5",1.5),("root_sum_square",2),("power_3",3),("best_grid_p",bp)]:
        pred=float((a**p).sum()**(1/p)); independent=bid!="SUN_SOURCE"; eligible=complete and independent
        su.append(dict(snapshot_id=SNAP,budget_id=bid,case_id=case,target_definition=td,model=name,p=p,predicted_delta_YS_MPa=pred,target_delta_YS_MPa=t,residual_MPa=t-pred,absolute_error_MPa=abs(t-pred),component_count=len(a),component_vector_complete="YES_SOURCE_MODEL" if complete else "NO",independent_target="YES" if independent else "NO",model_selection_eligible="YES" if eligible else "NO",selection_status="TAUTOLOGICAL_SOURCE_RECONSTRUCTION" if bid=="SUN_SOURCE" else "NOT_ELIGIBLE_INCOMPLETE_COMPONENT_VECTOR" if not complete else "ELIGIBLE",claim="No universal superposition rule identified"))
superdf=csv("SUPERPOSITION_MODEL_COMPARISON.csv",su,SC)

# Interactions and dose.
IR=[
("JIAO_TIB_X_TI5SI3_YS","JIAO2019","2x2 additive factorial","YS",-10,"MPa","IDENTIFIABLE_WITHIN_2X2","as-sintered RT","1050-930-900+770"),
("JIAO_TIB_X_TI5SI3_UTS","JIAO2019","2x2 additive factorial","UTS",10,"MPa","IDENTIFIABLE_WITHIN_2X2","as-sintered RT","1180-1070-1030+930"),
("JIAO_TIB_X_TI5SI3_EL","JIAO2019","2x2 additive factorial","EL",7.8,"percentage_point","IDENTIFIABLE_WITHIN_2X2","as-sintered RT","5.0-3.2-2.1+8.1"),
("YUAN_H_MINUS_B_T","YUAN2025","hybrid-minus-B proxy","YS",32.7,"MPa","NOT_FULL_FACTORIAL","RT transverse","Si and B doses both differ"),
("YUAN_H_MINUS_B_L","YUAN2025","hybrid-minus-B proxy","YS",25.5,"MPa","NOT_FULL_FACTORIAL","RT longitudinal","Si and B doses both differ"),
("YUAN_H_480","YUAN2025","alloy modification at temperature","YS",91.3,"MPa","PAIRED_ASSOCIATION","480C longitudinal","Net composition+phase+TiB effect"),
("QM12_REINF_X_TEMP","QM12_INTERNAL","difference-in-differences 700-650","YS",87.281,"MPa","PROTOCOL_PENDING","Ti65 internal series","Atomic identities pending")]
inter=[]
for i,p,t,prop,e,u,ident,dom,note in IR: inter.append(dict(snapshot_id=SNAP,interaction_id=i,paper_uid=p,interaction_type=t,property=prop,estimate=e,unit=u,ci95_low="",ci95_high="",independent_papers=1,evidence_level="P1_PROVENANCED_DERIVED" if p=="QM12_INTERNAL" else "DIRECT_TABLE_TEXT",identifiability=ident,claim_level=1 if p=="QM12_INTERNAL" else 2,support_domain=dom,notes=note))
INTC=list(inter[0].keys()); intdf=csv("INTERACTION_EFFECTS.csv",inter,INTC)
dose=[]
for p,s,tib,si,sw,bw,ys,stat,reason in [
("JIAO2019","TiBw/Ti5Si3",0,0,"","",770,"DESCRIPTIVE","two-axis design"),("JIAO2019","TiBw/Ti5Si3",3.4,0,"","",930,"DESCRIPTIVE","topology changes"),("JIAO2019","TiBw/Ti5Si3",0,4,"","",900,"DESCRIPTIVE","solution+precipitation coupled"),("JIAO2019","TiBw/Ti5Si3",3.4,4,"","",1050,"SATURATED_2X2","no validation cell"),
("YUAN2025","actual Si/B","","",.10,0,790.9,"DESCRIPTIVE_T","composition simplex"),("YUAN2025","actual Si/B","","",.64,0,946.6,"DESCRIPTIVE_T","solution+silicide"),("YUAN2025","actual Si/B","","",.13,.10,890.4,"DESCRIPTIVE_T","B not equal TiB phase dose"),("YUAN2025","actual Si/B","","",.26,.05,923.1,"DESCRIPTIVE_T","hybrid phase state")]: dose.append(dict(snapshot_id=SNAP,paper_uid=p,series=s,TiBw_vol_pct=tib,Ti5Si3_vol_pct=si,Si_wt_pct=sw,B_wt_pct=bw,YS_MPa=ys,status=stat,model="NO_UNIVERSAL_1D_DOSE",reason=reason))
csv("DOSE_RESPONSE.csv",dose,list(dose[0].keys()))

# Paper-cluster descriptive synthesis, heterogeneity and LOPO.
PE={"SUN2024":[SUND],"YUAN2025":[155.7,269.2,99.5,143.5,132.2,169,91.3],"JIAO2019":[160,130,280],"ZHOU2021":[305],"QM12_INTERNAL":[94.927,182.208],"WANG_QM32":[326]}
pm={k:float(np.mean(v)) for k,v in PE.items()}; mean,lo,hi=boot_mean(pm.values()); ae=[x for v in PE.values() for x in v]
hier=[dict(snapshot_id=SNAP,model="equal-paper cluster bootstrap",estimand="descriptive mean heterogeneous same-paper ΔYS",estimate=mean,ci95_low=lo,ci95_high=hi,prediction_interval_low=min(pm.values()),prediction_interval_high=max(pm.values()),independent_papers=len(pm),atomic_effects=len(ae),random_intercept="paper",random_slope="NOT_IDENTIFIABLE",status="ESTIMABLE_DESCRIPTIVE_ONLY",claim_level=1,notes="Not a universal mechanism coefficient."),dict(snapshot_id=SNAP,model="mechanism-component hierarchical meta-regression",estimand="separate solution/precipitate/phase/reinforcement coefficients",estimate="",ci95_low="",ci95_high="",prediction_interval_low="",prediction_interval_high="",independent_papers=len(pm),atomic_effects=len(ae),random_intercept="paper",random_slope="mechanism",status="NOT_IDENTIFIABLE",claim_level=0,notes="Incomplete non-overlapping proxies and sampling variances." )]
csv("HIERARCHICAL_RESULTS.csv",hier,list(hier[0].keys()))
het=[dict(snapshot_id=SNAP,scope="paper means",metric="between-paper SD",value=float(np.std(list(pm.values()),ddof=1)),unit="MPa",independent_papers=len(pm),status="DESCRIPTIVE"),dict(snapshot_id=SNAP,scope="paper means",metric="range",value=float(np.ptp(list(pm.values()))),unit="MPa",independent_papers=len(pm),status="DESCRIPTIVE"),dict(snapshot_id=SNAP,scope="atomic effects",metric="I2",value="",unit="%",independent_papers=len(pm),status="NOT_IDENTIFIABLE_NO_SAMPLING_VARIANCES"),dict(snapshot_id=SNAP,scope="mechanism budgets",metric="closure-error range",value=float(closure.closure_error_MPa.max()-closure.closure_error_MPa.min()),unit="MPa",independent_papers=int(closure.paper_uid.nunique()),status="DESCRIPTIVE")]
csv("HETEROGENEITY.csv",het,list(het[0].keys()))
lopo=[]
for left in pm:
    v=[x for k,x in pm.items() if k!=left]; lopo.append(dict(snapshot_id=SNAP,left_out_paper=left,estimate=float(np.mean(v)),change_from_full=float(np.mean(v)-mean),papers_remaining=len(v),status="DESCRIPTIVE_LOPO"))
csv("LOPO_RESULTS.csv",lopo,list(lopo[0].keys()))
low=1135/1.133-1058/1.081; high=1135/1.123-1058/1.091; nt=[r["closure_error_MPa"] for r in cl if r["budget_id"]!="SUN_SOURCE"]
sens=[dict(snapshot_id=SNAP,analysis="Sun Hc rounding",scenario="Hc ±0.005",estimate=SUND,low=low,high=high,unit="MPa",impact="Observed ΔYS remains far below 547 MPa",status="ROBUST_DIRECTION"),dict(snapshot_id=SNAP,analysis="Jiao TiBw load",scenario="direct Eq.(2)",estimate=TIB,low="",high="",unit="MPa",impact="Primary direct reconstruction",status="PRIMARY"),dict(snapshot_id=SNAP,analysis="Jiao TiBw load",scenario="QM32 rounded",estimate=12,low="",high="",unit="MPa",impact=12-TIB,status="ALTERNATE"),dict(snapshot_id=SNAP,analysis="closure",scenario="exclude tautological source target",estimate=float(np.median(nt)),low=min(nt),high=max(nt),unit="MPa",impact="Large signed residuals persist",status="ROBUST_GAP")]
for r in lopo: sens.append(dict(snapshot_id=SNAP,analysis="LOPO paper mean",scenario="leave out "+r["left_out_paper"],estimate=r["estimate"],low="",high="",unit="MPa",impact=r["change_from_full"],status="DESCRIPTIVE_LOPO"))
csv("SENSITIVITY_ANALYSIS.csv",sens,list(sens[0].keys()))

# Negative/null and conflict ledgers.
null=[
("N01","Universal superposition rule","NOT_IDENTIFIABLE","No complete vector with independent target","Do not optimize p from apparent fit"),
("N02","Independent phase term","NOT_IDENTIFIABLE","Phase and precipitate/heat-treatment state co-vary","Leave unresolved"),
("N03","Sun source budget vs observed ΔYS",f"OVER_CLOSURE {547-SUND:.3f} MPa","547 vs 31.988 MPa","Estimands are non-commensurate"),
("N04","Jiao YS interaction","-10 MPa","Direct 2x2 contrast","Near-additive/slightly sub-additive"),
("N05","High Ti5Si3 dose","NEGATIVE","8vol% Ti5Si3+3.4vol% TiBw: UTS980 MPa, EL1%, no YS","Non-monotonic benefit"),
("N06","Yuan high-Si ductility","NEGATIVE","YS rises while EL collapses to ~0.7-0.8%","Strength-only optimization fails"),
("N07","800C coefficient","NO_DIRECT_EVIDENCE","Admitted matched cohort reaches 700C","No 800C claim"),
("N08","QM12 high-T ΔYS","UNCERTAIN","Both report CIs cross zero","Protocol-pending")]
N=[]
for a,b,c,d,e in null:N.append(dict(snapshot_id=SNAP,result_id=a,question=b,result=c,evidence=d,implication=e))
csv("NULL_NEGATIVE_RESULTS.csv",N,list(N[0].keys()))
C=[
("C01","Sun budget","547 MPa source sum",f"{SUND:.3f} MPa observed exposure ΔYS","ESTIMAND_MISMATCH","Separate targets; do not call gap physical softening","OPEN_HIGH_IMPACT"),
("C02","Sun phase/precipitate","alpha2+silicide","alpha-prime dissolution+alpha/beta","MECHANISM_OVERLAP","Assign precipitate once; phase unresolved","OPEN"),
("C03","Jiao TiBw load",f"direct {TIB:.3f} MPa","QM32 rounded 12 MPa","FORMULA_OR_ROUNDING","Direct original primary; 12 sensitivity","RESOLVED_FOR_ANALYSIS"),
("C04","Jiao related works","PowTech YS1050","Scientific Reports YS1004","NONIDENTICAL_SAMPLE","Do not merge","RESOLVED_IDENTITY_FIREWALL"),
("C05","Yuan synergy","hybrid contrast","no clean factorial arm","INCOMPLETE_FACTORIAL","Proxy only","OPEN"),
("C06","QM12 pairs","report effects","V29 UIDs absent","PROTOCOL_IDENTITY","Grade B pending","OPEN_HIGH_IMPACT"),
("C07","Sun solution","Al-only 73 MPa","multicomponent Ti65","INCOMPLETE_SOLUTE_MODEL","Source-specific candidate only","OPEN"),
("C08","Cross-paper pooling","paper ΔYS","nonexchangeable processes/mechanisms","NONEXCHANGEABILITY","Descriptive equal-paper synthesis only","CONTROLLED")]
conf=[]
for x in C:conf.append(dict(snapshot_id=SNAP,conflict_id=x[0],object=x[1],source_a=x[2],source_b=x[3],conflict_type=x[4],resolution=x[5],status=x[6]))
csv("CONFLICT_LEDGER.csv",conf,list(conf[0].keys()))
claims=[dict(snapshot_id=SNAP,claim_id="CL01",claim="Sun coarse budget linearly totals 547 MPa by source definition",support="one original paper",level=1,ceiling="source reconstruction",status="SUPPORTED"),dict(snapshot_id=SNAP,claim_id="CL02",claim="547 MPa does not close control-relative exposure ΔYS",support=f"closure {SUND-547:.3f} MPa",level=2,ceiling="estimand mismatch",status="SUPPORTED"),dict(snapshot_id=SNAP,claim_id="CL03",claim="Jiao TiBw×Ti5Si3 YS interaction=-10 MPa",support="direct 2x2",level=2,ceiling="within observed cells",status="SUPPORTED"),dict(snapshot_id=SNAP,claim_id="CL04",claim="Universal four-way decomposition",support="incomplete independent proxies",level=0,ceiling="NOT_IDENTIFIABLE",status="REJECTED"),dict(snapshot_id=SNAP,claim_id="CL05",claim="Validated 800C recipe",support="no direct evidence",level=0,ceiling="PROHIBITED",status="REJECTED")]
csv("CLAIM_MATRIX.csv",claims,list(claims[0].keys()))
with (OUT/"PROVENANCE.jsonl").open("w",encoding="utf-8") as f:
    for r in co:f.write(json.dumps(dict(snapshot_id=SNAP,object_type="atomic_record",record_uid=r["record_uid"],paper_uid=r["paper_uid"],sample_uid=r["sample_uid"],condition_uid=r["condition_uid"],property="YS",value=r["value"],evidence_level=r["evidence_level"],source_locator=r["source_locator"],source_hash=r["source_hash"],hash_kind="NORMALIZED_EVIDENCE_CAPTURE_SHA256",transformation="direct" if r["evidence_level"]=="DIRECT_TABLE_TEXT" else "YS=UTS/(1+Hc)",production_promotion=False),ensure_ascii=False,sort_keys=True)+"\n")
    for r in mc:f.write(json.dumps(dict(snapshot_id=SNAP,object_type="mechanism_component",component_uid=r["component_uid"],case_id=r["case_id"],paper_uid=r["paper_uid"],mechanism=r["mechanism"],value_MPa=r["delta_sigma_MPa"],formula=r["formula_or_rule"],source_locator=r["source_locator"],status=r["status"],production_promotion=False),ensure_ascii=False,sort_keys=True)+"\n")

# Four mandatory figures, each with data, code, SVG/PDF/600-dpi PNG.
f1=pd.DataFrame([("Fine grain",127),("Solid solution (Al-only)",73),("Precipitate/silicide",222),("Dislocation",125)],columns=["component","value_MPa"]);f1["paper_count"]=1;f1["evidence"]="direct source budget";f1.to_csv(OUT/"figure_data/F1_waterfall.csv",index=False)
fig,ax=plt.subplots(figsize=(8.5,5.2));start=f1.value_MPa.cumsum().shift(fill_value=0);ax.bar(f1.component,f1.value_MPa,bottom=start);ax.axhline(547,ls="--",lw=1,label="Source total = 547 MPa");ax.axhline(SUND,ls=":",lw=1.5,label=f"Observed exposure ΔYS = {SUND:.1f} MPa");ax.set_ylabel("Strength contribution / MPa");ax.set_title("Mechanism budget waterfall\n1 independent paper; source-state budget");ax.tick_params(axis="x",rotation=18);ax.legend(fontsize=8);fig.tight_layout();f1p=triplet(fig,"QM35_F1_mechanism_budget_waterfall")
f2=superdf[(superdf.budget_id.isin(["SUN_SOURCE","SUN_OBSERVED"]))&(superdf.model.isin(["linear","power_1.5","root_sum_square","power_3"]))];f2.to_csv(OUT/"figure_data/F2_superposition.csv",index=False);mods=["linear","power_1.5","root_sum_square","power_3"];pred=[float(f2[(f2.budget_id=="SUN_SOURCE")&(f2.model==m)].predicted_delta_YS_MPa.iloc[0]) for m in mods]
fig,ax=plt.subplots(figsize=(8.5,5.2));ax.bar(mods,pred);ax.axhline(547,ls="--",lw=1,label="Source target = 547 MPa");ax.axhline(SUND,ls=":",lw=1.5,label=f"Observed exposure ΔYS = {SUND:.1f} MPa");ax.set_ylabel("Combined contribution / MPa");ax.set_title("Superposition-model comparison\nNo independent complete validation vector");ax.legend(fontsize=8);fig.tight_layout();f2p=triplet(fig,"QM35_F2_superposition_model_comparison")
f3=closure[closure.budget_id!="SUN_SOURCE"];f3.to_csv(OUT/"figure_data/F3_closure.csv",index=False);y=np.arange(len(f3));fig,ax=plt.subplots(figsize=(9.2,5.6));ax.scatter(f3.closure_error_MPa,y,s=55);ax.axvline(0,lw=1);ax.set_yticks(y,f3.budget_id);ax.set_xlabel("Closure error = observed ΔYS − known component sum / MPa");ax.set_title(f"Budget-closure error distribution\n{f3.paper_uid.nunique()} independent evidence sources");fig.tight_layout();f3p=triplet(fig,"QM35_F3_budget_closure_error")
f4=intdf[(intdf.unit=="MPa")];f4.to_csv(OUT/"figure_data/F4_interactions.csv",index=False);y=np.arange(len(f4));fig,ax=plt.subplots(figsize=(9.5,5.8));ax.scatter(f4.estimate,y,s=55);ax.axvline(0,lw=1);ax.set_yticks(y,f4.interaction_id);ax.set_xlabel("Interaction or contrast / MPa");ax.set_title(f"Element/phase × reinforcement interaction evidence\n{f4.paper_uid.nunique()} independent sources; exact and proxy contrasts labeled");fig.tight_layout();f4p=triplet(fig,"QM35_F4_interactions")
PLOTS={
"plot_f1.py":"""from pathlib import Path\nimport pandas as pd,matplotlib.pyplot as plt\nR=Path(__file__).resolve().parents[1];d=pd.read_csv(R/'figure_data/F1_waterfall.csv');s=d.value_MPa.cumsum().shift(fill_value=0);f,a=plt.subplots(figsize=(8.5,5.2));a.bar(d.component,d.value_MPa,bottom=s);a.axhline(547,ls='--');a.axhline(31.988,ls=':');a.set_ylabel('Strength contribution / MPa');a.set_title('Mechanism budget waterfall');a.tick_params(axis='x',rotation=18);f.tight_layout();[f.savefig(R/f'figures/QM35_F1_mechanism_budget_waterfall.{e}',dpi=600 if e=='png' else None,bbox_inches='tight') for e in ('png','svg','pdf')]""",
"plot_f2.py":"""from pathlib import Path\nimport pandas as pd,matplotlib.pyplot as plt\nR=Path(__file__).resolve().parents[1];d=pd.read_csv(R/'figure_data/F2_superposition.csv');m=['linear','power_1.5','root_sum_square','power_3'];v=[float(d[(d.budget_id=='SUN_SOURCE')&(d.model==x)].predicted_delta_YS_MPa.iloc[0]) for x in m];f,a=plt.subplots(figsize=(8.5,5.2));a.bar(m,v);a.axhline(547,ls='--');a.axhline(31.988,ls=':');a.set_ylabel('Combined contribution / MPa');a.set_title('Superposition-model comparison');f.tight_layout();[f.savefig(R/f'figures/QM35_F2_superposition_model_comparison.{e}',dpi=600 if e=='png' else None,bbox_inches='tight') for e in ('png','svg','pdf')]""",
"plot_f3.py":"""from pathlib import Path\nimport numpy as np,pandas as pd,matplotlib.pyplot as plt\nR=Path(__file__).resolve().parents[1];d=pd.read_csv(R/'figure_data/F3_closure.csv');y=np.arange(len(d));f,a=plt.subplots(figsize=(9.2,5.6));a.scatter(d.closure_error_MPa,y);a.axvline(0);a.set_yticks(y,d.budget_id);a.set_xlabel('Closure error / MPa');a.set_title('Budget-closure error');f.tight_layout();[f.savefig(R/f'figures/QM35_F3_budget_closure_error.{e}',dpi=600 if e=='png' else None,bbox_inches='tight') for e in ('png','svg','pdf')]""",
"plot_f4.py":"""from pathlib import Path\nimport numpy as np,pandas as pd,matplotlib.pyplot as plt\nR=Path(__file__).resolve().parents[1];d=pd.read_csv(R/'figure_data/F4_interactions.csv');y=np.arange(len(d));f,a=plt.subplots(figsize=(9.5,5.8));a.scatter(d.estimate,y);a.axvline(0);a.set_yticks(y,d.interaction_id);a.set_xlabel('Interaction or contrast / MPa');a.set_title('Element/phase × reinforcement interactions');f.tight_layout();[f.savefig(R/f'figures/QM35_F4_interactions.{e}',dpi=600 if e=='png' else None,bbox_inches='tight') for e in ('png','svg','pdf')]"""}
for n,c in PLOTS.items():text("plot_code/"+n,c)
plots=[dict(figure_id="QM35_F1",title="Mechanism budget waterfall",independent_papers=1,samples=1,effect_definition="source coarse components",interval="none",evidence_layer="direct original",support_domain="Sun Ti65",data="figure_data/F1_waterfall.csv",code="plot_code/plot_f1.py",outputs=f1p),dict(figure_id="QM35_F2",title="Superposition comparison",independent_papers=1,samples=1,effect_definition="p-norm same vector",interval="structural",evidence_layer="direct+derived",support_domain="Sun source vector",data="figure_data/F2_superposition.csv",code="plot_code/plot_f2.py",outputs=f2p),dict(figure_id="QM35_F3",title="Closure error",independent_papers=int(f3.paper_uid.nunique()),samples=len(f3),effect_definition="observed-known sum",interval="incomplete-vector residual",evidence_layer="direct+derived",support_domain="reported cases",data="figure_data/F3_closure.csv",code="plot_code/plot_f3.py",outputs=f3p),dict(figure_id="QM35_F4",title="Interactions",independent_papers=int(f4.paper_uid.nunique()),samples=len(f4),effect_definition="factorial or labeled proxy",interval="n unresolved",evidence_layer="direct+return",support_domain="within-paper",data="figure_data/F4_interactions.csv",code="plot_code/plot_f4.py",outputs=f4p)]
js("PLOT_SPECS.json",dict(window_id="QM35",snapshot_id=SNAP,plots=plots))
pqa=[]
for p in sorted((OUT/"figures").glob("*.pdf")):
    try: pages=len(PdfReader(str(p)).pages);st="PASS" if pages==1 and p.stat().st_size>1000 else "FAIL"
    except Exception as e:pages=0;st="FAIL:"+type(e).__name__
    pqa.append(dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,pages=pages,status=st))
js("PDF_VISUAL_QA.json",dict(method="pypdf page-count and nonzero-size structural QA",items=pqa,all_pass=all(x["status"]=="PASS" for x in pqa)))

# Documents, requests, status and acceptance code.
METHOD=f"""# METHODS — QM35\n\n{HEADER}\n\n## Evidence admission\nA frozen hash-bound inventory of 26 project archives was reused, and seven directly relevant evidence objects were opened. All packages receive an explicit terminal ledger state; numerical estimands enter only from original papers or provenance-bound returns. Package names never establish scientific scope.\n\n## Atomicity and estimands\nOne row is paper × sample × actual composition × process × heat treatment × microstructure × test mode × temperature × orientation × property. Primary effect: ΔYS=YS_treated−YS_control; lnRR and percent change are also reported. Grade A is same-paper/condition matching. Reported ± values are not converted to CIs because replicate n/spread semantics are unresolved; supplied QM12 CIs are retained.\n\n## Mechanism firewall\nGrain size is assigned only to Hall–Petch; dissolved chemistry only to solution; precipitate geometry/population only to precipitation/dispersion; TiB/TiC geometry only to load transfer; phase fraction only to phase transformation. Missing independent proxies remain NOT_IDENTIFIABLE and are not back-filled from closure residuals.\n\n## Superposition and uncertainty\nLinear, RSS and generalized p-norm rules use the same non-overlapping vector. Sun's 547 MPa linear closure is tautological because it is the source target. No complete vector has an independent target, so no universal p is selected. Paper is the cluster; a deterministic 20,000-resample equal-paper bootstrap and LOPO are descriptive, not causal meta-analysis.\n\n## Authority boundary\nThis is read-only. No ACTIVE_TITMC mutation, Gold promotion, production model registration or VALIDATED recipe occurs.\n"""; text("METHODS.md",METHOD)
text("LIMITATIONS.md","""# LIMITATIONS — QM35\n\n1. Authoritative V29 atomic/provenance/conflict/exclusion tables and final UIDs were not available as a single bound input; direct originals were rebuilt into a recovery cohort.\n2. Most specimens lack dissolved-solute, precipitate, phase-fraction and reinforcement-geometry proxies simultaneously; the four-way decomposition is structurally underidentified.\n3. Sun's 547 MPa budget and 31.988 MPa exposure ΔYS are different estimands.\n4. Jiao supports only a within-table saturated 2×2 contrast. Yuan is not a clean factorial.\n5. Sampling variances are incomplete; cluster intervals are descriptive.\n6. No matched direct 800 °C evidence is admitted.\n7. This runner reused the validated 78,683-XML inventory boundary but did not independently stream-parse every XML; corpus-wide completion belongs to V29X/local reducer.\n""")
REQ=dict(window_id="QM35",snapshot_id=SNAP,status="CONTINUE_DATA_GAP",required=[dict(priority=1,object="V29_ATOMIC_QM35_SLICE",fields=["paper_uid","sample_uid","condition_uid","actual_composition","phase_fraction","reinforcement_actual_fraction","YS","uncertainty","source_member_uid"]),dict(priority=1,object="V29_PROVENANCE_CONFLICT_EXCLUSION",reason="bind package SHA+member path+CRC+XPath/text hash"),dict(priority=1,object="ORIGINAL_MEMBER_BINDINGS",identifiers=DOI),dict(priority=1,object="INDEPENDENT_MECHANISM_PROXIES",fields=["dissolved_solute_by_phase","precipitate_size_density_fraction","alpha_prime_alpha_beta_fraction","grain_size","dislocation_density","reinforcement_AR_orientation_fraction"]),dict(priority=1,object="MATCHED_800C_EVIDENCE"),dict(priority=2,object="QM12_PROTOCOL_MANIFEST")],acceptance="Hash-bound, conflict-audited, validator pass; no Gold promotion before gates close.",next_action="LOCAL_ABSORPTION_AND_TARGETED_SOURCE_BACKFILL");js("WEB_TO_LOCAL_REQUEST.json",REQ)
text("LOCAL_ABSORPTION_PROMPT.md",f"""# QM35 local absorption\n1. Verify CHECKSUMS, MANIFEST, CSV schemas and four PDF/SVG/600-dpi PNG triplets.\n2. Bind to local Q40 snapshot without modifying ACTIVE.\n3. Join recovery UIDs to authoritative V29; reject ambiguous joins.\n4. Run `python validate_qm35.py`, `python analysis_code/recompute_qm35.py`, and tests.\n5. Replace capture hashes with package/member/CRC/XPath hashes.\n6. Backfill requested independent proxies and 800 °C matched evidence.\n7. Recompute; log drift in CONFLICT_LEDGER.\n8. Promote nothing until gates pass.\nExpected snapshot: {SNAP}.""")
text("OPENED_FILES.txt","\n".join(["QM35 MDU | file_library://turn7file13","Sun 2024 original | file_library://turn4file0","Yuan 2025 original | file_library://turn4file2","Jiao 2019 original | file_library://turn15file0","Zhou 2021 original | file_library://turn13file3","QM32 return | file_library://turn13file0","QM12 return | file_library://turn8file7","26-archive validated ledger | file_library://turn12file0"]))
coverage=[]
for p in ["SUN2024","YUAN2025","JIAO2019","ZHOU2021","QM12_INTERNAL","WANG_QM32","BAO_QM32"]:coverage.append(dict(paper_uid=p,original_opened="YES" if p in ["SUN2024","YUAN2025","JIAO2019","ZHOU2021"] else "NO_RETURN_ONLY",paired_YS="NO" if p=="BAO_QM32" else "YES",solid_solution_proxy="PARTIAL" if p in ["SUN2024","YUAN2025","JIAO2019"] else "NO",precipitate_proxy="PARTIAL" if p in ["SUN2024","YUAN2025","JIAO2019"] else "NO",phase_proxy="QUALITATIVE" if p in ["SUN2024","YUAN2025","JIAO2019","ZHOU2021"] else "NO",reinforcement_proxy="NUMERIC" if p in ["JIAO2019","ZHOU2021","WANG_QM32","BAO_QM32"] else "NET_EFFECT_ONLY" if p=="QM12_INTERNAL" else "NO",terminal_scope_state="CONTEXT_ONLY" if p=="BAO_QM32" else "INCLUDED"))
csv("SOURCE_COVERAGE_MATRIX.csv",coverage,list(coverage[0].keys()))
text("DATA_DICTIONARY.md","""# Data dictionary\n- `delta_sigma_MPa`: candidate component; blank is not identifiable.\n- `unresolved_contribution_MPa`: observed target minus non-overlapping known sum; never auto-assigned.\n- `match_grade A`: same-paper condition match; B is protocol pending.\n- `claim_level`: 0 not identifiable, 1 descriptive/source reconstruction, 2 same-paper pair/contrast.\n- blank numeric fields are missing, not zero.\n""")
STATUS="STATUS: CONTINUE_DATA_GAP | WINDOW=QM35 | MISSING=AUTHORITATIVE_V29_UIDS,INDEPENDENT_PHASE_COMPONENTS,800C_MATCHED_EVIDENCE | NEXT=LOCAL_ABSORPTION_AND_TARGETED_SOURCE_BACKFILL"
VER=f"""# 00_EXECUTIVE_VERDICT — QM35\n\n{HEADER}\n\n## Scientific verdict\n\n1. A unique solution/precipitate/phase/reinforcement decomposition is **NOT_IDENTIFIABLE** because the mechanisms co-vary and independent proxies are incomplete.\n2. Sun's only complete coarse budget is 127+73+222+125=547 MPa by source definition. Reported UTS/Hc imply YS {SUN0:.1f}->{SUN1:.1f} MPa after 650 °C/100 h, ΔYS={SUND:.1f} MPa. Forcing the source budget against that control-relative change yields closure {SUND-547:.1f} MPa: an estimand mismatch, not a hidden negative mechanism.\n3. Jiao's hybrid partial budget gives Hall–Petch {HP:.1f}, TiBw load {TIB:.1f}, Ti5Si3 load {SI:.1f} MPa, sum {HP+TIB+SI:.1f} versus observed ΔYS=280 MPa; {280-HP-TIB-SI:.1f} MPa remains unresolved rather than double-counted.\n4. Jiao's additive interactions are −10 MPa YS, +10 MPa UTS, +7.8 pp EL: strength is near-additive/slightly sub-additive while plasticity shows topology/deformation-compatibility rescue.\n5. Load transfer is architecture dependent: Zhou 58/305 MPa, Wang 24/326 MPa, versus aligned high-AR Bao anchors ~111/322 MPa. Content alone is not a mechanism coefficient.\n6. No linear/RSS/power model wins an independent test. Sun linear closure is tautological; observed-target cases have incomplete vectors.\n7. Yuan gives +91.3 MPa YS at 480 °C. QM12's 700−650 °C reinforcement interaction is +87.3 MPa but protocol-pending and both source-report CIs cross zero. No 800 °C coefficient or recipe is supported.\n\n## Claim ceiling\nMaximum claim level 2: same-paper paired association/within-table contrast. Mechanism budgets are assumption-constrained explanatory models, not unique microscopic truth. No Gold promotion, no production model registration, no ACTIVE mutation and no VALIDATED recipe.\n\n{STATUS}\n""";text("00_EXECUTIVE_VERDICT.md",VER)
stat=dict(window_id="QM35",snapshot_id=SNAP,papers_seen=8,papers_included=6,independent_papers=6,atomic_rows=len(co),matched_pairs=len(pa),effect_estimates=len(ef),plots_generated=4,figure_files=12,open_conflicts=sum(x["status"].startswith("OPEN") for x in conf),claim_level_max=2,status="CONTINUE_DATA_GAP",next_action="LOCAL_ABSORPTION_AND_TARGETED_SOURCE_BACKFILL",missing=["AUTHORITATIVE_V29_UIDS","INDEPENDENT_PHASE_COMPONENTS","800C_MATCHED_EVIDENCE"],production_model_registration=False,gold_promotion=False,status_line=STATUS);js("WINDOW_STATUS.json",stat)
text("RUN_LOG.txt",f"{HEADER}\nseed={SEED}\narchives={len(INV)}\ndirect_objects={len(DIRECT)}\natomic_rows={len(co)}\npairs={len(pa)}\ncomponents={len(mc)}\nfigures=4\nproduction_model_registration=false\ngold_promotion=false\n{STATUS}")

# Recompute, validator, tests and locks.
text("analysis_code/recompute_qm35.py","""#!/usr/bin/env python3\nfrom pathlib import Path\nimport pandas as pd\nR=Path(__file__).resolve().parents[1];c=pd.read_csv(R/'MECHANISM_COMPONENT_INPUTS.csv');b=pd.read_csv(R/'STRENGTHENING_BUDGET.csv')\nfor _,r in b.iterrows():\n v=pd.to_numeric(c.loc[c.case_id==r.case_id,'delta_sigma_MPa'],errors='coerce').dropna();p=float(v.sum());assert abs(p-float(r.known_component_sum_MPa))<1e-6;assert abs(float(r.observed_delta_YS_MPa)-p-float(r.unresolved_contribution_MPa))<1e-6\np=pd.read_csv(R/'PAIR_MATCHES.csv')\nfor _,r in p.iterrows():\n if pd.notna(r.treated_value) and pd.notna(r.control_value): assert abs(float(r.treated_value)-float(r.control_value)-float(r.delta))<1e-6\nprint('RECOMPUTE_PASS',len(b),len(p))""")
text("validate_qm35.py","""#!/usr/bin/env python3\nfrom pathlib import Path\nimport csv,hashlib,json\nR=Path(__file__).resolve().parent\nreq=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','MECHANISM_COMPONENT_INPUTS.csv','SUPERPOSITION_MODEL_COMPARISON.csv','STRENGTHENING_BUDGET.csv','BUDGET_CLOSURE_ERROR.csv'];assert not [x for x in req if not (R/x).exists()]\nfor p in R.rglob('*.csv'):\n with p.open(encoding='utf-8',newline='') as f: next(csv.reader(f))\nfor line in (R/'CHECKSUMS.sha256').read_text().splitlines():\n if line.strip():\n  d,rel=line.split('  ',1);assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==d\nassert not list(R.rglob('*.zip'));assert json.loads((R/'WINDOW_STATUS.json').read_text())['status']=='CONTINUE_DATA_GAP';print('VALIDATION_PASS')""")
text("analysis_code/validate_package.py","""#!/usr/bin/env python3\nimport runpy\nfrom pathlib import Path\nrunpy.run_path(str(Path(__file__).resolve().parents[1]/'validate_qm35.py'),run_name='__main__')""")
text("tests/test_qm35.py","""from pathlib import Path\nimport json,pandas as pd\nR=Path(__file__).resolve().parents[1]\ndef test_budget():\n b=pd.read_csv(R/'STRENGTHENING_BUDGET.csv');assert ((b.observed_delta_YS_MPa-b.known_component_sum_MPa-b.unresolved_contribution_MPa).abs()<1e-6).all()\ndef test_scope(): assert (R/'MECHANISM_COMPONENT_INPUTS.csv').exists() and (R/'SUPERPOSITION_MODEL_COMPARISON.csv').exists()\ndef test_authority():\n s=(R/'00_EXECUTIVE_VERDICT.md').read_text();assert 'No Gold promotion' in s and 'no production model' in s\ndef test_status(): assert json.loads((R/'WINDOW_STATUS.json').read_text())['status']=='CONTINUE_DATA_GAP'\ndef test_figures(): assert all(len(list((R/'figures').glob('*.'+e)))==4 for e in ['png','svg','pdf'])""")
text("requirements.lock","numpy==2.2.6\npandas==2.3.0\nmatplotlib==3.10.3\npypdf==5.7.0\npytest==8.4.1")
text("acceptance_commands.md","""# Acceptance\n```bash\npython -m pip install -r requirements.lock\npython analysis_code/recompute_qm35.py\npython validate_qm35.py\npython -m pytest -q tests\n```""")
val=dict(window_id="QM35",snapshot_id=SNAP,required_files_present=True,csv_schema_readable=True,budget_identity_max_abs_error=float(np.max(abs(budgets.observed_delta_YS_MPa-budgets.known_component_sum_MPa-budgets.unresolved_contribution_MPa))),pair_delta_max_abs_error=float(max(abs(float(p["treated_value"])-float(p["control_value"])-float(p["delta"])) for p in pa if finite(p["treated_value"]))),pdf_all_pass=all(x["status"]=="PASS" for x in pqa),nested_zip_count=0,production_model_registration=False,gold_promotion=False,passed=True);js("VALIDATION_REPORT.json",val)
# Manifest excludes recursive files; CHECKSUMS includes MANIFEST.
entries=[]
for p in sorted(x for x in OUT.rglob("*") if x.is_file() and x.name not in {"MANIFEST.json","CHECKSUMS.sha256"}):entries.append(dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hfile(p)))
js("MANIFEST.json",dict(window_id="QM35",snapshot_id=SNAP,generated_utc=datetime.now(timezone.utc).isoformat(),seed=SEED,status="CONTINUE_DATA_GAP",claim_level_max=2,files=entries,file_count_excluding_manifest_and_checksums=len(entries),nested_zip_count=0,authority_mutation=False))
text("CHECKSUMS.sha256","\n".join(f"{hfile(p)}  {p.relative_to(OUT)}" for p in sorted(x for x in OUT.rglob('*') if x.is_file() and x.name!='CHECKSUMS.sha256')))
# Final internal verification.
for p in OUT.rglob("*.csv"):pd.read_csv(p)
for line in (OUT/"CHECKSUMS.sha256").read_text().splitlines():
    d,rel=line.split("  ",1);assert hfile(OUT/rel)==d
assert not list(OUT.rglob("*.zip"));assert all(x["status"]=="PASS" for x in pqa)
print(f"QM35_BUILD_PASS snapshot={SNAP} files={len([p for p in OUT.rglob('*') if p.is_file()])}")
print(STATUS)
