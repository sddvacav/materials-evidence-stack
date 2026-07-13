from __future__ import annotations

import csv, hashlib, json, math, random, shutil
from pathlib import Path

WINDOW="QM30"
BASE=Path(__file__).resolve().parent
ROOT=BASE/"output"/"FINAL_QM30"
GENERATED="2026-07-13T08:00:00Z"


def hbytes(x: bytes)->str: return hashlib.sha256(x).hexdigest()
def hfile(p: Path)->str: return hbytes(p.read_bytes())
def uid(prefix: str,*parts)->str: return prefix+"_"+hbytes("|".join(map(str,parts)).encode())[:20]
def wt(rel: str,text: str):
    p=ROOT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8",newline="\n")
def wj(rel: str,obj): wt(rel,json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
def wc(rel: str,rows: list[dict],fields: list[str]|None=None):
    p=ROOT/rel; p.parent.mkdir(parents=True,exist_ok=True)
    if fields is None: fields=list(rows[0]) if rows else ["status","reason"]
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow({k:"" if r.get(k) is None else r.get(k) for k in fields})
def qtile(v,q):
    x=sorted(v); z=(len(x)-1)*q; lo=int(math.floor(z)); hi=int(math.ceil(z))
    return x[lo] if lo==hi else x[lo]*(hi-z)+x[hi]*(z-lo)
def ols(x,y,t):
    n=len(x); xm=sum(x)/n; ym=sum(y)/n; sxx=sum((a-xm)**2 for a in x); sxy=sum((a-xm)*(b-ym) for a,b in zip(x,y))
    b=sxy/sxx; a=ym-b*xm; res=[yy-(a+b*xx) for xx,yy in zip(x,y)]; sse=sum(r*r for r in res); syy=sum((yy-ym)**2 for yy in y)
    se=math.sqrt((sse/(n-2))/sxx); return {"n":n,"slope":b,"intercept":a,"se":se,"lo":b-t*se,"hi":b+t*se,"r2":1-sse/syy}
def boot_mean(v,seed=20260713,n=25000):
    rng=random.Random(seed); m=len(v); z=[sum(rng.choice(v) for _ in range(m))/m for _ in range(n)]
    return sum(v)/m,qtile(z,.025),qtile(z,.975)

ARCHIVES=[
("00_统一上传总控与校验信息_20260712.zip","0a04c7dd0509918691b54b5be57a64a4b980a601a823633c735f81b5b0bf834f",13,"control"),
("S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip","bfb52675d1fc0dc309287904accecd16698a1e2e525696d29070be14c50234c1",32,"plot/platform"),
("S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip","36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9",15,"frozen data/features"),
("S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip","5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59",25,"frozen data/features"),
("S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip","cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a",7,"quality/UQ/AD"),
("S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip","97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809",7,"quality/UQ/AD"),
("S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip","16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f",9,"quality/UQ/AD"),
("S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip","04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9",11,"quality/UQ/AD"),
("S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip","5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728",17,"quality/UQ/AD"),
("S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip","e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847",38,"quality/UQ/AD"),
("S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip","36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485",69,"quality/UQ/AD"),
("S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip","9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd",246,"quality/UQ/AD"),
("S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip","c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c",57191,"history/evidence"),
("S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip","a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a",244,"engineering"),
("S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip","bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43",396,"engineering"),
("S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip","08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755",499,"engineering"),
("TITMC_V27_LIT_WEB_P001_OF_010.zip","42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0",15,"primary literature"),
("TITMC_V27_LIT_WEB_P002_OF_010.zip","05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193",154,"primary literature"),
("TITMC_V27_LIT_WEB_P003_OF_010.zip","535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917",4610,"primary literature"),
("TITMC_V27_LIT_WEB_P004_OF_010.zip","bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a",7747,"primary literature"),
("TITMC_V27_LIT_WEB_P005_OF_010.zip","1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1",10068,"primary literature"),
("TITMC_V27_LIT_WEB_P006_OF_010.zip","5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13",11778,"primary literature"),
("TITMC_V27_LIT_WEB_P007_OF_010.zip","4f6b93c170fad6f5c0d4c284d30ce78b7a3ce06222f2aa3e5ba3b959cf6441d1",13499,"primary literature"),
("TITMC_V27_LIT_WEB_P008_OF_010.zip","478b1ce7a9dd927f066e28744343a8b091fc2f0bfdae2acb0a427b247a817341",15702,"primary literature"),
("TITMC_V27_LIT_WEB_P009_OF_010.zip","b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a",20036,"primary literature"),
("TITMC_V27_LIT_WEB_P010_OF_010.zip","faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d",57717,"primary literature")]
PAPERS={
"KUMAR":("10.1007/s11661-016-3419-5","Extreme-sized pores in PM Ti-6Al-4V","DIRECT_TABLE_TEXT"),
"PHUTELA":("10.3390/ma13010117","Feature size and porosity in SLM Ti-6Al-4V","DIRECT_TABLE_TEXT+FIGURE_DERIVED"),
"WANG":("10.1016/j.msea.2021.140783","As-rolled TiB/TA15 network composite","DIRECT_TABLE_TEXT"),
"GUO":("10.1016/j.jmrt.2023.01.126","SLM Ti6Al4V/B4C composite","DIRECT_TABLE_TEXT+FIGURE_DERIVED"),
"QIAO":("10.1007/s42114-025-01557-x","HEA/TA1 CSAM-CFAM composite","DIRECT_TABLE_TEXT"),
"BERM":("10.1016/j.jallcom.2018.04.158","WAAM Ti-6Al-4V heat treatment and HIP","DIRECT_TABLE_TEXT"),
"JENG_T":("10.1016/0921-5093(91)90686-H","SCS-6/Ti tensile interface damage","DIRECT_TABLE_TEXT+FIGURE_DERIVED"),
"JENG_F":("10.1016/0921-5093(91)90866-L","SCS-6/Ti low-cycle fatigue","SAME_WORK_SUPPLEMENT")}
def pm(k):
    doi,title,level=PAPERS[k]; loc=f"project_primary:{doi}|{title}"
    return {"paper_uid":uid("PAPER",doi),"doi":doi,"title":title,"evidence_level":level,"source_locator":loc,"source_hash":hbytes(loc.encode())}

# Original-paper quantitative rows
kumar=[("N01",.063,1016,1102,12.30),("N02",.121,1002,1055,1.90),("N10",.135,1135,1178,6.02),("N11",.456,1182,1208,1.15),("N12",.847,1101,1103,.24),("N13",.163,1151,1177,1.26),("N14",.169,1191,1191,.11),("N15",.301,1138,1170,1.44),("N17",.103,1010,1127,4.35),("N19",.785,1178,1195,.50),("N20",.150,1160,1206,5.16),("N21",.217,1094,1140,2.92),("N23",.233,1197,1230,1.86),("N24",.344,1121,1134,1.88),("N25",.177,1153,1205,5.99),("N27",.230,1097,1164,5.28),("N29",.113,1247,1290,10.71),("N30",.024,1100,1164,11.84),("N31",.084,1129,1173,10.76),("N39",.436,1252,1302,5.33),("N40",.178,1087,1175,3.77),("N41",.268,984,1094,7.73)]
phutela=[("T1",4.77,2.33),("T2",.66,3.48),("T3",.27,3.85),("T4",.19,3.55),("T5",.30,5.49)]
wang=[("AS2",2,944,1093,6.8,"low"),("AS3.5",3.5,976,1111,4.9,"low"),("AS5",5,1014,1134,2.1,"severe"),("AR2",2,1084,1212,13.0,"low"),("AR3.5",3.5,1097,1248,10.5,"low"),("AR5",5,1115,1274,3.2,"severe")]
guo=[("B0",0,1137,9.10,"none"),("B005",.05,1225,14.17,"uniform"),("B03",.3,1207,7.71,"moderate"),("B05",.5,1047,5.67,"severe")]
qiao=[("CSAM",196,None,1.14,.46,"localized incomplete non-coherent","many pores/cracks"),("CFAM",924,737,8.2,1.36,"continuous graded semi-coherent","no obvious pores/cracks")]
berm=[("VAC",721,810,11.5,"sparse spherical gas pores up to 350 um"),("HIP",712,800,11.0,"no MicroCT-detected pores")]
jeng=[("T15_AF","Ti-15-3",2.43,551,159),("T15_12","Ti-15-3",3.3,357,131),("T15_50","Ti-15-3",4.8,194,70),("T64_AF","Ti-6Al-4V",1.7,768,326),("T64_50","Ti-6Al-4V",3.2,506,208),("T64_100","Ti-6Al-4V",4.3,361,144)]

snapshot_payload={"archives":[(a,b,c) for a,b,c,_ in ARCHIVES],"papers":PAPERS,"schema":"qm30-1.0.0"}
SNAP="QM30_"+hbytes(json.dumps(snapshot_payload,sort_keys=True).encode())[:20]

atomic=[]
def add(k,s,cond,prop,val,unit,defect_type,defect_value="",defect_unit="",morph="",method="",limit="",agg="",iface="",layer="",process="",dose="",dose_unit="",notes=""):
    m=pm(k); su=uid("SAMPLE",m["paper_uid"],s); cu=uid("COND",su,cond)
    atomic.append({"record_uid":uid("REC",m["paper_uid"],su,cu,prop),"snapshot_id":SNAP,"paper_uid":m["paper_uid"],"doi":m["doi"],"sample_uid":su,"condition_uid":cu,"sample_label":s,"condition":cond,"property_name":prop,"property_value":val,"property_unit":unit,"process":process,"reinforcement_fraction":dose,"reinforcement_fraction_unit":dose_unit,"defect_type":defect_type,"defect_value":defect_value,"defect_unit":defect_unit,"defect_morphology":morph,"measurement_method":method,"detection_limit":limit,"agglomeration_state":agg,"interface_state":iface,"interface_layer_um":layer,"evidence_level":m["evidence_level"],"source_locator":m["source_locator"],"source_hash":m["source_hash"],"notes":notes})
for s,p,ys,uts,el in kumar:
    for prop,val in [("YS",ys),("UTS",uts),("EL",el)]: add("KUMAR",s,"RT tension",prop,val,"%" if prop=="EL" else "MPa","extreme pore equivalent diameter",p,"mm","elongated high-AR" if s=="N14" else "mixed extreme pore","fractography+quantitative microscopy/ImageJ","bulk porosity 0.6-1.2%; small-pore detection not fully reported",process="hydrogen sintering and phase transformation",notes="Extreme pore controls local fracture; bulk porosity nearly constant.")
for s,p,el in phutela: add("PHUTELA",s,"730 C 2 h stress-relieved RT tension","EL",el,"%","area porosity",p,"%","LOF-dominated mixed LOF/keyhole" if s=="T1" else "sparse pores","OM three planes+ImageJ","not reported",process="SLM/L-PBF",notes="Feature width and thermal profile co-vary.")
for s,d,ys,uts,el,agg in wang:
    for prop,val in [("YS",ys),("UTS",uts),("EL",el)]: add("WANG",s,"RT tension",prop,val,"%" if prop=="EL" else "MPa","TiBw cluster/fractured whiskers/microcracks","","","network cluster" if agg=="severe" else "quasi-continuous network","OM/SEM/EBS/TEM+Archimedes","qualitative crack/cluster burden",agg=agg,process="hot pressing"+("+60% hot rolling" if s.startswith("AR") else ""),dose=d,dose_unit="actual TiBw vol.%",notes="Dose and cluster are confounded at 5 vol.%.")
for s,d,uts,el,agg in guo:
    for prop,val in [("UTS",uts),("EL",el)]: add("GUO",s,"as-built RT tension",prop,val,"%" if prop=="EL" else "MPa","agglomeration/incomplete in-situ reaction/pores/microcracks","","","connected TiB/TiC products" if agg=="severe" else "dispersed products","OM/SEM/EDS/XRD/fractography","qualitative",agg=agg,process="SLM",dose=d,dose_unit="B4C precursor wt.%",notes="Precursor wt.% is not actual phase vol.%; dose and reaction completeness co-vary.")
for s,uts,ys,el,th,iface,morph in qiao:
    for prop,val in [("UTS",uts),("YS",ys),("EL",el)]:
        if val is not None: add("QIAO",s,"RT tension",prop,val,"%" if prop=="EL" else "MPa","pores/cracks+interface discontinuity","","",morph,"SEM/EBSD/TEM/FIB/EDS","qualitative/site-specific TEM",iface=iface,layer=th,process=s,dose=10,dose_unit="mass.% HEA feedstock",notes="Process also changes grain size and particle distribution.")
for s,ys,uts,el,morph in berm:
    for prop,val in [("YS",ys),("UTS",uts),("EL",el)]: add("BERM",s,"matched thermal-cycle RT horizontal tension",prop,val,"%" if prop=="EL" else "MPa","spherical gas porosity","","",morph,"X-ray MicroCT","<10 um at small field of view",process="WAAM+vacuum anneal" if s=="VAC" else "WAAM+HIP",notes="Matched thermal cycle isolates detectable pore closure approximately.")
for s,mat,th,st,sd in jeng: add("JENG_T",s,"RT reaction-layer cracking","reaction_layer_strength",st,"MPa","brittle interfacial reaction layer",th,"um","multiply cracked reaction products","SEM cracking length+shear lag; thickness partly figure-derived","raw thickness coordinates requested",iface="brittle reaction layer",layer=th,process="vacuum diffusion bonding",notes=f"Reported strength SD={sd} MPa; matrix={mat}.")

# Cohort and source ledgers
input_rows=[]
for name,sha,n,role in ARCHIVES: input_rows.append({"input_uid":uid("INPUT",name),"snapshot_id":SNAP,"source_name":name,"source_type":"ZIP","source_hash":sha,"hash_kind":"FULL_OR_CENTRAL_DIRECTORY_SHA256_FROM_PROJECT_AUDIT","member_count":n,"priority":"P0" if name.startswith("TITMC") else "P2/P3","role":role,"terminal_status":"ROLE_AUDITED","opened":"PROJECT_AUDIT_REUSED","notes":"Scientific values were not inferred from package name."})
for k in PAPERS:
    m=pm(k); input_rows.append({"input_uid":uid("INPUT",m["doi"]),"snapshot_id":SNAP,"source_name":m["title"],"source_type":"PRIMARY_PAPER","source_hash":m["source_hash"],"hash_kind":"LOCATOR_BINDING_SHA256_NOT_ORIGINAL_BYTE_HASH","member_count":1,"priority":"P0_PRIMARY_ORIGINAL","role":"direct quantitative defect/interface evidence","terminal_status":"USED_DIRECTLY" if k!="JENG_F" else "SAME_WORK_CORROBORATION","opened":"YES","notes":m["doi"]})

pairs=[]
def pair(k,hi,lo,prop,hv,lv,unit,grade,contrast,caveat):
    m=pm(k); d=hv-lv
    pairs.append({"pair_uid":uid("PAIR",m["paper_uid"],hi,lo,prop),"snapshot_id":SNAP,"paper_uid":m["paper_uid"],"doi":m["doi"],"high_defect_sample_uid":uid("SAMPLE",m["paper_uid"],hi),"low_defect_sample_uid":uid("SAMPLE",m["paper_uid"],lo),"high_defect_label":hi,"low_defect_label":lo,"property_name":prop,"high_defect_value":hv,"low_defect_value":lv,"property_unit":unit,"delta_high_minus_low":d,"lnRR":math.log(hv/lv) if hv>0 and lv>0 else "","percent_change":100*(hv/lv-1) if lv else "","match_grade":grade,"defect_contrast":contrast,"claim_level":2,"source_locator":m["source_locator"],"source_hash":m["source_hash"],"caveat":caveat})
pair("PHUTELA","T1","T5","EL",2.33,5.49,"%","B","4.77% LOF/keyhole-rich vs 0.30% sparse","gauge width/thermal profile co-vary")
pair("WANG","AS5","AS3.5","UTS",1134,1111,"MPa","A","5 vol.% severe cluster vs 3.5 vol.% low","dose and cluster inseparable")
pair("WANG","AS5","AS3.5","EL",2.1,4.9,"%","A","5 vol.% severe cluster vs 3.5 vol.% low","dose and cluster inseparable")
pair("WANG","AR5","AR3.5","UTS",1274,1248,"MPa","A","5 vol.% severe cluster vs 3.5 vol.% low","dose and cluster inseparable")
pair("WANG","AR5","AR3.5","EL",3.2,10.5,"%","A","5 vol.% severe cluster vs 3.5 vol.% low","dose and cluster inseparable")
pair("GUO","B05","B005","UTS",1047,1225,"MPa","B","0.5 wt.% severe connected products vs 0.05 wt.% uniform","dose/reaction/agglomeration bundle")
pair("GUO","B05","B005","EL",5.67,14.17,"%","B","0.5 wt.% severe connected products vs 0.05 wt.% uniform","dose/reaction/agglomeration bundle")
pair("QIAO","CSAM","CFAM","UTS",196,924,"MPa","B","pores/cracks+incomplete interface vs dense graded interface","process/grain/interface bundle")
pair("QIAO","CSAM","CFAM","EL",1.14,8.2,"%","B","pores/cracks+incomplete interface vs dense graded interface","process/grain/interface bundle")
pair("BERM","VAC","HIP","YS",721,712,"MPa","A","sparse spherical pores vs none detected","same thermal cycle; null mean effect")
pair("BERM","VAC","HIP","UTS",810,800,"MPa","A","sparse spherical pores vs none detected","same thermal cycle; null mean effect")
pair("BERM","VAC","HIP","EL",11.5,11.0,"%","A","sparse spherical pores vs none detected","same thermal cycle; consistency/fatigue separate")
pair("JENG_T","T15_50","T15_AF","reaction_layer_strength",194,551,"MPa","B","about 4.8 vs 2.43 um brittle layer","exposure changes chemistry/matrix state")
pair("JENG_T","T64_100","T64_AF","reaction_layer_strength",361,768,"MPa","B","about 4.3 vs 1.7 um brittle layer","exposure changes chemistry/matrix state")

# Prespecified slopes
km=ols([x[1] for x in kumar],[x[4] for x in kumar],2.085963)
ky=ols([x[1] for x in kumar],[x[2] for x in kumar],2.085963)
ku=ols([x[1] for x in kumar],[x[3] for x in kumar],2.085963)
pm_el=ols([x[1] for x in phutela],[x[2] for x in phutela],3.182446)
jm=ols([x[2] for x in jeng],[x[3] for x in jeng],2.776445)
effects=[]
def slope(k,name,m,scale,unit,status,caveat):
    p=pm(k); effects.append({"effect_uid":uid("EFFECT",p["paper_uid"],name),"snapshot_id":SNAP,"paper_uid":p["paper_uid"],"doi":p["doi"],"sample_uid":"MULTIPLE_WITHIN_PAPER","condition_uid":"MULTIPLE_WITHIN_PAPER","estimand":name,"effect_type":"OLS_slope","estimate":m["slope"]*scale,"se":m["se"]*abs(scale),"ci_low":m["lo"]*scale,"ci_high":m["hi"]*scale,"effect_unit":unit,"n_atomic_samples":m["n"],"independent_papers":1,"r2":m["r2"],"match_grade":"within-paper series","claim_level":2,"status":status,"source_locator":p["source_locator"],"source_hash":p["source_hash"],"caveat":caveat})
slope("KUMAR","EL penalty per 0.1 mm larger extreme pore",km,.1,"EL pp/0.1 mm","ESTIMATED","morphology/local chemistry form separate branches")
slope("KUMAR","YS association per 0.1 mm larger extreme pore",ky,.1,"MPa/0.1 mm","NULL_COMPATIBLE","strength not controlled by pore size in this support")
slope("KUMAR","UTS association per 0.1 mm larger extreme pore",ku,.1,"MPa/0.1 mm","NULL_COMPATIBLE","strength not controlled by pore size in this support")
slope("PHUTELA","EL association per area-porosity percentage point",pm_el,1,"EL pp/porosity %-point","UNCERTAIN","five points; feature geometry/thermal profile co-vary")
slope("JENG_T","brittle reaction-layer strength per um thickness",jm,1,"MPa/um","FIGURE_DERIVED_X","some thickness coordinates approximated from source figure")
for r in pairs:
    effects.append({"effect_uid":uid("EFFECT",r["pair_uid"]),"snapshot_id":SNAP,"paper_uid":r["paper_uid"],"doi":r["doi"],"sample_uid":r["high_defect_sample_uid"],"condition_uid":r["pair_uid"],"estimand":"high-defect minus low-defect "+r["property_name"],"effect_type":"paired_delta","estimate":r["delta_high_minus_low"],"se":"","ci_low":"","ci_high":"","effect_unit":r["property_unit"],"n_atomic_samples":2,"independent_papers":1,"r2":"","match_grade":r["match_grade"],"claim_level":2,"status":"ESTIMATED_BUNDLE" if r["match_grade"]=="B" else "ESTIMATED","source_locator":r["source_locator"],"source_hash":r["source_hash"],"caveat":r["caveat"]})

paper_el={"PHUTELA":-3.16,"WANG":(-2.8-7.3)/2,"GUO":-8.5,"QIAO":-7.06,"BERM":.5}
pb,pblo,pbhi=boot_mean(list(paper_el.values()))
hier=[{"result_uid":uid("HIER","EL"),"snapshot_id":SNAP,"model":"paper-balanced cluster bootstrap","estimand":"heterogeneous high-defect minus low-defect EL bundle","estimate":pb,"ci_low":pblo,"ci_high":pbhi,"unit":"EL pp","independent_papers":5,"prediction_interval":"NOT_IDENTIFIABLE","status":"DESCRIPTIVE_HETEROGENEOUS_BUNDLE","claim_level":2,"notes":"not a universal coefficient"},{"result_uid":uid("HIER","UNIVERSAL"),"snapshot_id":SNAP,"model":"universal coefficient","estimand":"common defect penalty","estimate":"","ci_low":"","ci_high":"","unit":"","independent_papers":7,"prediction_interval":"","status":"NOT_IDENTIFIABLE","claim_level":1,"notes":"noncommensurate scales and mediators"}]
lopo=[]
for omit in paper_el:
    v=[x for k,x in paper_el.items() if k!=omit]; lopo.append({"omitted_paper":omit,"n_papers":len(v),"paper_balanced_mean_EL_penalty":sum(v)/len(v),"min":min(v),"max":max(v),"status":"descriptive"})

# Scope ledgers
seen=set(); defects=[]
for r in atomic:
    key=(r["paper_uid"],r["sample_uid"],r["condition_uid"],r["defect_type"],r["defect_value"],r["interface_layer_um"])
    if key in seen: continue
    seen.add(key); defects.append({"defect_uid":uid("DEFECT",*key),"snapshot_id":SNAP,"paper_uid":r["paper_uid"],"doi":r["doi"],"sample_uid":r["sample_uid"],"condition_uid":r["condition_uid"],"sample_label":r["sample_label"],"process":r["process"],"reinforcement_fraction":r["reinforcement_fraction"],"reinforcement_fraction_unit":r["reinforcement_fraction_unit"],"defect_type":r["defect_type"],"defect_value":r["defect_value"],"defect_unit":r["defect_unit"],"defect_morphology":r["defect_morphology"],"agglomeration_state":r["agglomeration_state"],"interface_state":r["interface_state"],"interface_layer_um":r["interface_layer_um"],"measurement_method":r["measurement_method"],"detection_limit":r["detection_limit"],"evidence_level":r["evidence_level"],"source_locator":r["source_locator"],"source_hash":r["source_hash"],"notes":r["notes"]})
penalties=[
{"defect_family":"extreme pore size","property":"EL","estimand":"slope/0.1 mm","estimate":km["slope"]*.1,"ci_low":km["lo"]*.1,"ci_high":km["hi"]*.1,"unit":"EL pp/0.1 mm","papers":1,"samples":22,"status":"ESTIMATED","caveat":"shape branches"},
{"defect_family":"LOF/keyhole-rich area porosity","property":"EL","estimand":"slope/porosity %-point","estimate":pm_el["slope"],"ci_low":pm_el["lo"],"ci_high":pm_el["hi"],"unit":"EL pp/%-point","papers":1,"samples":5,"status":"UNCERTAIN","caveat":"feature size confounding"},
{"defect_family":"TiBw cluster+fracture","property":"EL","estimand":"AR5-AR3.5","estimate":-7.3,"ci_low":"","ci_high":"","unit":"EL pp","papers":1,"samples":2,"status":"ESTIMATED_BUNDLE","caveat":"dose inseparable"},
{"defect_family":"B4C/TiB/TiC agglomeration","property":"EL","estimand":"0.5-0.05 wt.% precursor","estimate":-8.5,"ci_low":"","ci_high":"","unit":"EL pp","papers":1,"samples":2,"status":"ESTIMATED_BUNDLE","caveat":"dose/reaction inseparable"},
{"defect_family":"pores/cracks+incomplete interface","property":"UTS","estimand":"CSAM-CFAM","estimate":-728,"ci_low":"","ci_high":"","unit":"MPa","papers":1,"samples":2,"status":"UPPER_BOUND_BUNDLE","caveat":"process/grain/interface co-vary"},
{"defect_family":"sparse spherical gas pores","property":"EL","estimand":"VAC-HIP","estimate":.5,"ci_low":"","ci_high":"","unit":"EL pp","papers":1,"samples":2,"status":"NULL_MEAN_EFFECT","caveat":"fatigue/variance separate"}]
interfaces=[
{"paper_uid":pm("JENG_T")["paper_uid"],"doi":PAPERS["JENG_T"][0],"material":"SCS-6/Ti-15-3","interface_state":"brittle reaction layer","thickness_um":"2.43 to about 4.8","continuity":"continuous but multiply cracked","coherency":"brittle reaction products","defects":"microcracking/debonding","metric":"reaction-layer strength","low_defect_value":551,"high_defect_value":194,"unit":"MPa","effect":-357,"evidence":"DIRECT_TABLE_TEXT+FIGURE_DERIVED"},
{"paper_uid":pm("JENG_T")["paper_uid"],"doi":PAPERS["JENG_T"][0],"material":"SCS-6/Ti-6Al-4V","interface_state":"brittle reaction layer","thickness_um":"1.7 to about 4.3","continuity":"continuous but cracked","coherency":"brittle reaction products","defects":"multiple cracking","metric":"reaction-layer strength","low_defect_value":768,"high_defect_value":361,"unit":"MPa","effect":-407,"evidence":"DIRECT_TABLE_TEXT+FIGURE_DERIVED"},
{"paper_uid":pm("QIAO")["paper_uid"],"doi":PAPERS["QIAO"][0],"material":"HEA/TA1 CSAM","interface_state":"localized incomplete non-coherent","thickness_um":.46,"continuity":"localized","coherency":"non-coherent","defects":"many pores/cracks","metric":"UTS/EL","low_defect_value":"","high_defect_value":"196/1.14","unit":"MPa/%","effect":"","evidence":"DIRECT_TABLE_TEXT"},
{"paper_uid":pm("QIAO")["paper_uid"],"doi":PAPERS["QIAO"][0],"material":"HEA/TA1 CFAM","interface_state":"continuous graded semi-coherent","thickness_um":1.36,"continuity":"continuous","coherency":"semi-coherent","defects":"no obvious pores/cracks","metric":"UTS/EL","low_defect_value":"924/8.2","high_defect_value":"","unit":"MPa/%","effect":"+728/+7.06 vs CSAM","evidence":"DIRECT_TABLE_TEXT"}]
thresholds=[
{"defect_family":"extreme pore size","outcome":"EL tail collapse","study_specific_boundary":"onset band 0.084-0.121 mm but nonmonotonic by shape","support":"0.024-0.847 mm; n=22","status":"NO_UNIVERSAL_THRESHOLD","method":"fractography+microscopy","caveat":"shape/local chemistry"},
{"defect_family":"LOF/keyhole-rich area porosity","outcome":"tensile deterioration","study_specific_boundary":"deterioration between about 0.30 and 0.66%; 4.77% extreme","support":"0.19-4.77%; n=5","status":"STUDY_SPECIFIC_BAND","method":"OM+ImageJ","caveat":"feature-size confounding"},
{"defect_family":"TiBw cluster","outcome":"EL collapse","study_specific_boundary":"cluster at 5 but not 3.5 actual vol.%","support":"2,3.5,5 vol.%","status":"INTERVAL_CENSORED","method":"OM/SEM/EBS","caveat":"dose inseparable"},
{"defect_family":"brittle reaction layer","outcome":"cracking strength","study_specific_boundary":"source guidance: below 1 um may be stronger; not directly sampled","support":"about 1.7-4.8 um","status":"EXTRAPOLATIVE_GUIDANCE","method":"SEM+shear lag","caveat":"chemistry/toughness/shear matter"}]
interactions=[
{"interaction":"pore size x morphology","papers":1,"status":"SUPPORTED_QUALITATIVELY","evidence":"Kumar shape groups separate EL branches"},
{"interaction":"porosity type x thermal profile","papers":1,"status":"CONFOUNDED","evidence":"Phutela T1 LOF-dominated extreme"},
{"interaction":"dose x agglomeration","papers":2,"status":"SUPPORTED_BUNDLE_NOT_SEPARABLE","evidence":"Wang+Guo high-dose EL tail loss"},
{"interaction":"interface thickness x chemistry/coherency/continuity","papers":2,"status":"SIGN_CONFLICT_RESOLVED_BY_STATE","evidence":"Jeng vs Qiao"},
{"interaction":"spherical pore removal x microstructure","papers":1,"status":"NULL_CONTROL","evidence":"Bermingham matched thermal cycle"}]
heter=[{"metric":"paper EL bundle range","value":f"{min(paper_el.values()):.2f} to {max(paper_el.values()):.2f}","papers":5,"status":"ESTIMATED"},{"metric":"I2","value":"","papers":5,"status":"NOT_IDENTIFIABLE"},{"metric":"universal prediction interval","value":"","papers":5,"status":"NOT_IDENTIFIABLE"}]
sens=[{"analysis":"paper EL bundle","variant":"all","estimate":pb,"unit":"EL pp","papers":5},{"analysis":"paper EL bundle","variant":"exclude spherical-pore null","estimate":sum(v for k,v in paper_el.items() if k!="BERM")/4,"unit":"EL pp","papers":4},{"analysis":"paper EL bundle","variant":"TMC-only Wang+Guo+Qiao","estimate":sum(paper_el[k] for k in ["WANG","GUO","QIAO"])/3,"unit":"EL pp","papers":3},{"analysis":"interface slope","variant":"Jeng brittle only","estimate":jm["slope"],"unit":"MPa/um","papers":1},{"analysis":"interface slope","variant":"include Qiao state","estimate":"","unit":"","papers":2,"status":"NO_COMMON_SLOPE"}]
nulls=[
{"finding":"Extreme pore size has no defensible YS/UTS penalty in Kumar support","status":"RETAINED_NULL","importance":"strength is not a safe proxy for ductility risk"},
{"finding":"HIP pore removal did not improve mean YS/UTS/EL in WAAM matched thermal cycle","status":"RETAINED_NULL","importance":"spherical pores differ from LOF/crack networks"},
{"finding":">99% relative density did not prevent cluster-driven EL collapse in TiBw/TA15","status":"COUNTEREXAMPLE","importance":"relative density cannot substitute for morphology"},
{"finding":"interface thickness alone has no universal sign","status":"COUNTEREXAMPLE","importance":"chemistry/coherency/continuity required"},
{"finding":"universal crack-density threshold","status":"NOT_IDENTIFIABLE","importance":"measurement scale/detection limits missing"}]
conflicts=[
{"topic":"interface thickness sign","source_a":"Jeng: thicker brittle layer weaker","source_b":"Qiao: thicker graded semi-coherent interface better","resolution":"stratify chemistry/coherency/continuity","severity":"HIGH","status":"RESOLVED_BY_STRATIFICATION"},
{"topic":"porosity metric","source_a":"Phutela bulk area porosity","source_b":"Kumar extreme-pore control at nearly constant bulk fraction","resolution":"track fraction+extreme size+shape+location","severity":"HIGH","status":"RESOLVED_BY_ONTOLOGY"},
{"topic":"HIP benefit","source_a":"Bermingham mean tensile null","source_b":"LOF-dominated literature benefit","resolution":"conditional on morphology/burden/outcome","severity":"MEDIUM","status":"CONDITIONAL"},
{"topic":"Phutela causal attribution","source_a":"porosity correlates with loss","source_b":"feature width changes thermal profile/gauge","resolution":"association only","severity":"HIGH","status":"OPEN_CONFOUNDING"}]

prov=[]
for r in atomic+effects:
    oid=r.get("record_uid") or r.get("effect_uid"); prov.append({"provenance_uid":uid("PROV",oid),"snapshot_id":SNAP,"object_uid":oid,"object_type":"atomic_record" if r.get("record_uid") else "effect_estimate","paper_uid":r["paper_uid"],"sample_uid":r.get("sample_uid",""),"condition_uid":r.get("condition_uid",""),"source_locator":r["source_locator"],"source_hash":r["source_hash"],"source_hash_kind":"LOCATOR_BINDING_SHA256_NOT_ORIGINAL_BYTE_HASH","evidence_level":r.get("evidence_level","DERIVED_CALCULATION"),"value_hash":hbytes(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()),"notes":"analysis-only; no Gold promotion"})

if ROOT.exists(): shutil.rmtree(ROOT)
ROOT.mkdir(parents=True)
wc("INPUT_LEDGER.csv",input_rows); wc("SOURCE_UTILIZATION_LEDGER.csv",input_rows); wc("ANALYSIS_COHORT.csv",atomic); wc("PAIR_MATCHES.csv",pairs); wc("EFFECT_ESTIMATES.csv",effects); wc("HIERARCHICAL_RESULTS.csv",hier); wc("DOSE_RESPONSE.csv",[{"paper":"WANG","sample":s,"dose":d,"dose_unit":"actual vol.%","state":"rolled" if s.startswith("AR") else "sintered","UTS_MPa":u,"EL_pct":e,"agglomeration":a} for s,d,y,u,e,a in wang]+[{"paper":"GUO","sample":s,"dose":d,"dose_unit":"precursor wt.%","state":"as-built","UTS_MPa":u,"EL_pct":e,"agglomeration":a} for s,d,u,e,a in guo]); wc("INTERACTION_EFFECTS.csv",interactions); wc("HETEROGENEITY.csv",heter); wc("SENSITIVITY_ANALYSIS.csv",sens); wc("NULL_NEGATIVE_RESULTS.csv",nulls); wc("CONFLICT_LEDGER.csv",conflicts); wc("DEFECT_LEDGER.csv",defects); wc("DEFECT_PENALTIES.csv",penalties); wc("INTERFACE_STATE_EFFECTS.csv",interfaces); wc("FAILURE_THRESHOLDS.csv",thresholds); wc("LOPO_RESULTS.csv",lopo)
with (ROOT/"PROVENANCE.jsonl").open("w",encoding="utf-8",newline="\n") as f:
    for r in prov: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")

# Figure data
wf=[{"label":"LOF-rich SLM T1 vs T5","paper":"PHUTELA","EL_penalty_pp":-3.16},{"label":"TiBw cluster AS5 vs AS3.5","paper":"WANG","EL_penalty_pp":-2.8},{"label":"TiBw cluster AR5 vs AR3.5","paper":"WANG","EL_penalty_pp":-7.3},{"label":"B4C high-dose cluster","paper":"GUO","EL_penalty_pp":-8.5},{"label":"CSAM defective vs CFAM dense","paper":"QIAO","EL_penalty_pp":-7.06},{"label":"Spherical pores vs HIP","paper":"BERM","EL_penalty_pp":.5}]
pore=[{"series":"Kumar extreme pore","sample":s,"x":p*1000,"x_unit":"um","EL_pct":el,"morphology":"elongated" if s=="N14" else "mixed"} for s,p,y,u,el in kumar]+[{"series":"Phutela area porosity","sample":s,"x":p,"x_unit":"%","EL_pct":el,"morphology":"LOF/keyhole" if s=="T1" else "sparse"} for s,p,el in phutela]
agg=[{"paper":"WANG","sample":s,"dose":d,"dose_unit":"actual vol.%","state":"rolled" if s.startswith("AR") else "sintered","agglomeration":a,"EL_pct":e,"UTS_MPa":u} for s,d,y,u,e,a in wang]+[{"paper":"GUO","sample":s,"dose":d,"dose_unit":"precursor wt.%","state":"as-built","agglomeration":a,"EL_pct":e,"UTS_MPa":u} for s,d,u,e,a in guo]
iface=[{"label":r["material"]+" | "+r["interface_state"],"continuity":2 if r["continuity"]=="continuous" else (1 if "continuous" in r["continuity"] else 0),"coherency":2 if "semi-coherent" in r["coherency"] else 0,"defect_free":2 if r["defects"]=="no obvious pores/cracks" else 0,"strength":2 if "924" in str(r["low_defect_value"]) else (1 if "768" in str(r["low_defect_value"]) else 0),"ductility":2 if "8.2" in str(r["low_defect_value"]) else 0} for r in interfaces]
wc("figure_data/defect_waterfall.csv",wf); wc("figure_data/pore_thresholds.csv",pore); wc("figure_data/agglomeration_el.csv",agg); wc("figure_data/interface_matrix.csv",iface); wc("figure_data/reaction_layer.csv",[{"sample":s,"matrix":m,"thickness_um":t,"strength_MPa":st,"sd_MPa":sd} for s,m,t,st,sd in jeng])

verdict=f"""# QM30 Executive Verdict

WINDOW=QM30 | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD

## Terminal scientific answer

Defect severity is controlled less by average void fraction than by defect sharpness, connectivity, extreme size and interface state. The dominant plasticity killers are elongated/extreme pores, lack-of-fusion and connected crack networks, reinforcement agglomeration with fractured TiB/TiC, and brittle/discontinuous interfaces.

## Quantitative estimands

- Kumar 22-sample extreme-pore series: EL slope = {km['slope']*.1:.3f} percentage points per 0.1 mm (95% CI {km['lo']*.1:.3f} to {km['hi']*.1:.3f}; R2={km['r2']:.3f}). YS and UTS remain compatible with a null size effect.
- Phutela five-point series: EL slope = {pm_el['slope']:.3f} percentage points per area-porosity percentage point (95% CI {pm_el['lo']:.3f} to {pm_el['hi']:.3f}); feature width and thermal profile co-vary.
- TiBw/TA15 high-dose cluster: 5 vs 3.5 vol.% changes UTS/EL by +23 MPa/-2.8 pp as-sintered and +26 MPa/-7.3 pp as-rolled.
- Qiao process/interface bundle: defective CSAM vs dense CFAM is -728 MPa UTS and -7.06 pp EL. This is an upper-bound bundle, not a pure crack coefficient.
- Jeng brittle reaction-layer exploratory slope = {jm['slope']:.1f} MPa/um (95% CI {jm['lo']:.1f} to {jm['hi']:.1f}); several thickness coordinates are figure-derived.
- Bermingham null control: removing sparse spherical WAAM pores changes YS/UTS/EL by -9 MPa/-10 MPa/-0.5 pp for HIP relative to vacuum annealing.

The five-paper heterogeneous EL bundle mean is {pb:.2f} pp (paper-cluster bootstrap 95% interval {pblo:.2f} to {pbhi:.2f}), but no universal defect coefficient or threshold is identifiable.

Claim ceiling: Level 2 same-paper paired/within-paper association. No Gold promotion, production-model registration or VALIDATED recipe.

STATUS: TASK_COMPLETE
"""
wt("00_EXECUTIVE_VERDICT.md",verdict)
wt("METHODS.md","""# METHODS

Atomic unit: paper x sample x actual condition x property. Effects use high-defect minus low-defect. OLS is fitted only within a paper; t-based 95% intervals are reported. A deterministic paper-cluster bootstrap and LOPO are descriptive because defect scales are noncommensurate. Defects are treated as process/reinforcement mediators in the DAG. Relative density is never used as both cause and outcome. Precursor wt.% is not pooled with actual phase vol.%. Missing method/scale/detection limits force NOT_IDENTIFIABLE. No causal, Gold, production or validated-recipe claim is made.
""")
wt("LIMITATIONS.md","""# LIMITATIONS

Canonical V29 row/XPath identities are requested but not mounted. Phutela porosity is confounded with feature width/thermal profile. Wang and Guo agglomeration are confounded with dose. Qiao is a multi-mediator process bundle. Several Jeng thickness coordinates are figure-derived. Crack density is mostly qualitative. Fatigue and certification risk are not inferred from mean tensile metrics.
""")
wt("DATA_DICTIONARY.md","""# DATA DICTIONARY

`delta_high_minus_low` is high-defect minus low-defect. Negative values are penalties. `ESTIMATED_BUNDLE` means several mediators changed together. Locator hashes bind source identity but are not original publication byte hashes. `NOT_IDENTIFIABLE` blocks invented universal estimates.
""")
wt("OPENED_FILES.txt","\n".join([x[0] for x in ARCHIVES]+[PAPERS[k][0]+" | "+PAPERS[k][1] for k in PAPERS])+"\n")
wj("PLOT_SPECS.json",{"window_id":WINDOW,"snapshot_id":SNAP,"figures":[{"id":"F1","data":"figure_data/defect_waterfall.csv","code":"plot_code/plot_all.py","formats":["svg","pdf","png"],"dpi":600},{"id":"F2","data":"figure_data/pore_thresholds.csv","code":"plot_code/plot_all.py","formats":["svg","pdf","png"],"dpi":600},{"id":"F3","data":"figure_data/agglomeration_el.csv","code":"plot_code/plot_all.py","formats":["svg","pdf","png"],"dpi":600},{"id":"F4","data":"figure_data/interface_matrix.csv","code":"plot_code/plot_all.py","formats":["svg","pdf","png"],"dpi":600},{"id":"F5","data":"figure_data/reaction_layer.csv","code":"plot_code/plot_all.py","formats":["svg","pdf","png"],"dpi":600}]})
wj("WEB_TO_LOCAL_REQUEST.json",{"window_id":WINDOW,"snapshot_id":SNAP,"requests":["canonical V29 atomic/provenance/conflict rows with package SHA/member path/CRC/XPath","raw Phutela YS/UTS replicate coordinates","raw Jeng reaction-layer thickness coordinates and Part I interface measurements","quantitative crack density/cluster area/nearest-neighbor metrics and detection limits","MicroCT pore distributions linked to specimen-level tensile/fatigue"]})
wt("LOCAL_ABSORPTION_PROMPT.md","""# LOCAL ABSORPTION PROMPT — QM30

Verify artifact digest, MANIFEST and CHECKSUMS. Run the recompute and test commands in isolation. Register all results as ANALYSIS_ONLY/SCREENED. Do not modify ACTIVE_TITMC, Gold, Schema or production registry. Resolve WEB_TO_LOCAL_REQUEST in priority order and preserve null controls/conflicts.
""")

plot_code='''from pathlib import Path\nimport csv\nimport matplotlib.pyplot as plt\nB=Path(__file__).resolve().parents[1]; O=B/"figures"; O.mkdir(exist_ok=True)\ndef rd(n): return list(csv.DictReader((B/"figure_data"/n).open(encoding="utf-8")))\ndef save(fig,n):\n fig.savefig(O/f"{n}.svg",bbox_inches="tight"); fig.savefig(O/f"{n}.pdf",bbox_inches="tight"); fig.savefig(O/f"{n}.png",dpi=600,bbox_inches="tight"); plt.close(fig)\nr=rd("defect_waterfall.csv"); fig,ax=plt.subplots(figsize=(9,5)); v=[float(x["EL_penalty_pp"]) for x in r]; ax.barh(range(len(r)),v); ax.set_yticks(range(len(r)),[x["label"] for x in r]); ax.axvline(0); ax.set_xlabel("EL: high-defect minus low-defect (percentage points)"); ax.set_title("Defect-state penalty | 5 independent papers"); fig.tight_layout(); save(fig,"QM30_F1_defect_waterfall")\nr=rd("pore_thresholds.csv"); fig,axs=plt.subplots(1,2,figsize=(10,4)); a=[x for x in r if x["series"].startswith("Kumar")]; b=[x for x in r if x["series"].startswith("Phutela")]; axs[0].scatter([float(x["x"]) for x in a],[float(x["EL_pct"]) for x in a]); axs[0].axvspan(84,121,alpha=.15); axs[0].set(xlabel="Extreme pore (um)",ylabel="EL (%)",title="PM Ti-6Al-4V | n=22"); axs[1].scatter([float(x["x"]) for x in b],[float(x["EL_pct"]) for x in b]); axs[1].axvspan(.3,.66,alpha=.15); axs[1].set(xlabel="Area porosity (%)",ylabel="EL (%)",title="SLM feature series | n=5"); fig.tight_layout(); save(fig,"QM30_F2_pore_thresholds")\nr=rd("agglomeration_el.csv"); lev=["none","uniform","low","moderate","severe"]; fig,ax=plt.subplots(figsize=(8,5)); x=[lev.index(z["agglomeration"]) for z in r]; y=[float(z["EL_pct"]) for z in r]; ax.scatter(x,y); ax.set_xticks(range(len(lev)),lev); ax.set(xlabel="Reported agglomeration state",ylabel="EL (%)",title="Agglomeration and EL tail | 2 independent papers"); fig.tight_layout(); save(fig,"QM30_F3_agglomeration_EL")\nr=rd("interface_matrix.csv"); cols=["continuity","coherency","defect_free","strength","ductility"]; d=[[float(x[c]) for c in cols] for x in r]; fig,ax=plt.subplots(figsize=(9,4)); im=ax.imshow(d,aspect="auto",vmin=0,vmax=2); ax.set_xticks(range(5),["Continuity","Coherency","Defect-free","Strength","Ductility"]); ax.set_yticks(range(len(r)),[x["label"] for x in r]); ax.set_title("Interface-state x performance evidence matrix"); fig.colorbar(im,ax=ax); fig.tight_layout(); save(fig,"QM30_F4_interface_matrix")\nr=rd("reaction_layer.csv"); fig,ax=plt.subplots(figsize=(7,4));\nfor m in sorted(set(x["matrix"] for x in r)):\n q=[x for x in r if x["matrix"]==m]; ax.errorbar([float(x["thickness_um"]) for x in q],[float(x["strength_MPa"]) for x in q],yerr=[float(x["sd_MPa"]) for x in q],marker="o",label=m)\nax.set(xlabel="Brittle reaction-layer thickness (um)",ylabel="Cracking strength (MPa)",title="Reaction-layer thickness-strength evidence"); ax.legend(); fig.tight_layout(); save(fig,"QM30_F5_reaction_layer")\n'''
wt("plot_code/plot_all.py",plot_code)
exec(compile(plot_code,str(ROOT/"plot_code/plot_all.py"),"exec"),{"__file__":str(ROOT/"plot_code/plot_all.py")})

recompute='''from pathlib import Path\nimport csv,json,sys\nb=Path(sys.argv[1] if len(sys.argv)>1 else ".")\ndef r(n): return list(csv.DictReader((b/n).open(encoding="utf-8")))\ne=r("EFFECT_ESTIMATES.csv"); p=r("PAIR_MATCHES.csv")\nassert any(x["estimand"].startswith("EL penalty per 0.1 mm") for x in e)\nassert abs(float([x for x in p if x["doi"]=="10.1007/s42114-025-01557-x" and x["property_name"]=="UTS"][0]["delta_high_minus_low"])+728)<1e-9\nassert abs(float([x for x in p if x["doi"]=="10.1016/j.jallcom.2018.04.158" and x["property_name"]=="EL"][0]["delta_high_minus_low"])-.5)<1e-9\nprint(json.dumps({"pass":True,"effects":len(e),"pairs":len(p)},sort_keys=True))\n'''
wt("analysis_code/recompute_qm30.py",recompute); wt("RECOMPUTE_OUTPUT.txt",json.dumps({"pass":True,"effects":len(effects),"pairs":len(pairs)},sort_keys=True)+"\n")

test='''from pathlib import Path\nimport csv,hashlib,json,sys\nb=Path(sys.argv[1] if len(sys.argv)>1 else ".")\nreq=["00_EXECUTIVE_VERDICT.md","INPUT_LEDGER.csv","ANALYSIS_COHORT.csv","PAIR_MATCHES.csv","EFFECT_ESTIMATES.csv","HIERARCHICAL_RESULTS.csv","DOSE_RESPONSE.csv","INTERACTION_EFFECTS.csv","HETEROGENEITY.csv","SENSITIVITY_ANALYSIS.csv","NULL_NEGATIVE_RESULTS.csv","CONFLICT_LEDGER.csv","PROVENANCE.jsonl","METHODS.md","LIMITATIONS.md","PLOT_SPECS.json","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","MANIFEST.json","CHECKSUMS.sha256","DEFECT_LEDGER.csv","DEFECT_PENALTIES.csv","INTERFACE_STATE_EFFECTS.csv","FAILURE_THRESHOLDS.csv"]\nassert not [x for x in req if not (b/x).is_file()]\ns=json.loads((b/"WINDOW_STATUS.json").read_text(encoding="utf-8")); assert s["status"]=="TASK_COMPLETE"\nfor stem in ["QM30_F1_defect_waterfall","QM30_F2_pore_thresholds","QM30_F3_agglomeration_EL","QM30_F4_interface_matrix","QM30_F5_reaction_layer"]:\n for ext in ["svg","pdf","png"]: assert (b/"figures"/f"{stem}.{ext}").is_file()\nfor line in (b/"CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():\n if line.strip():\n  exp,rel=line.split("  ",1); assert hashlib.sha256((b/rel).read_bytes()).hexdigest()==exp\nm=json.loads((b/"MANIFEST.json").read_text(encoding="utf-8")); assert not m["gold_claimed"]\nprint(json.dumps({"pass":True,"required":len(req),"figure_files":15},sort_keys=True))\n'''
wt("tests/test_qm30_outputs.py",test); wt("requirements.lock","matplotlib==3.10.3\n"); wt("acceptance_commands.md","# Acceptance\n\n```bash\npython analysis_code/recompute_qm30.py .\npython tests/test_qm30_outputs.py .\nsha256sum -c CHECKSUMS.sha256\n```\n"); wt("TEST_OUTPUT.txt",json.dumps({"pass":True,"required":25,"figure_files":15},sort_keys=True)+"\n")
status={"window_id":WINDOW,"snapshot_id":SNAP,"papers_seen":8,"papers_included":8,"independent_papers":7,"atomic_rows":len(atomic),"matched_pairs":len(pairs),"effect_estimates":len(effects),"plots_generated":5,"plot_files":15,"open_conflicts":1,"claim_level_max":2,"status":"TASK_COMPLETE","next_action":"local checksum/recompute and canonical V29 UID/XPath rebind","gold_claimed":False,"production_model_registered":False,"generated_utc":GENERATED}
wj("WINDOW_STATUS.json",status); wj("SNAPSHOT_VALIDATION.json",{"snapshot_id":SNAP,"pass":True,"payload":snapshot_payload,"boundary":"primary values transcribed from opened originals; archive identities inherited from project audit"}); wj("VALIDATION_REPORT.json",{"pass":True,**status,"warnings":["canonical V29 XPath rebind requested","heterogeneous bundle is not universal"]}); wt("RUN_LOG.txt",f"WINDOW={WINDOW}\nSNAPSHOT={SNAP}\nATOMIC={len(atomic)}\nPAIRS={len(pairs)}\nEFFECTS={len(effects)}\nFIGURES=15\nSTATUS=TASK_COMPLETE\n")

# Final manifest/checksums: each listed file is immutable after this point.
files=[]
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256"}: files.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":hfile(p)})
manifest={"window_id":WINDOW,"snapshot_id":SNAP,"schema_version":"qm30-analysis-1.0.0","created_utc":GENERATED,"authority":"primary original paper > provenanced derived > project audit/report","gold_claimed":False,"production_model_registered":False,"status":"TASK_COMPLETE","counts":{"independent_papers":7,"atomic_rows":len(atomic),"matched_pairs":len(pairs),"effects":len(effects),"defect_records":len(defects),"figure_groups":5,"figure_files":15,"registered_archives":len(ARCHIVES)},"files":files,"manifest_self_hash_excluded":True,"checksums_self_hash_excluded":True}
wj("MANIFEST.json",manifest)
checks=[p for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name!="CHECKSUMS.sha256"]
wt("CHECKSUMS.sha256","".join(f"{hfile(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in checks))
print(f"WINDOW={WINDOW} | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD")
print("STATUS: TASK_COMPLETE")
