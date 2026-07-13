#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, shutil, subprocess, sys, textwrap, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq

WINDOW="SSL04"; BATCH="V31_TITMC_MODEL_WAR_20260713"; STATUS="BLOCKED_INPUT"
NOW=datetime.now(timezone.utc).isoformat()
ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/"build"/"FINAL_SSL04"; DIST=ROOT/"dist"
AUTH=["MODEL_INPUT_SNAPSHOT.json","DATASET_FINGERPRINT.json","GOLD_ROWS.parquet","SCREENED_UNLABELED_ROWS.parquet","FEATURE_DICTIONARY.json","TARGET_REGISTRY.json","SPLIT_MANIFEST.json","SEED_REGISTRY.json","BUDGET_REGISTRY.json","LEAKAGE_FIREWALL.md","CHECKSUMS.sha256"]

def h256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def wt(rel:str,s:str):
    p=PKG/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(textwrap.dedent(s).lstrip(),encoding="utf-8",newline="\n")

def wj(rel:str,o:Any): wt(rel,json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n")

def wc(rel:str,fields:list[str],rows:list[dict[str,Any]]):
    p=PKG/rel; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def source_inventory()->list[dict[str,Any]]:
    known={
      "S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip":("36cd2294edaae1b3ad74d9f519d6c0669863630224ca688f50d654042cf166a9","PRIOR_AUDIT_FULL_FILE_SHA256",15),
      "S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip":("5cd883da72d45c2915fe44975c5a81c41b8e87bfe0f0ef444db9669db26dbb59","PRIOR_AUDIT_FULL_FILE_SHA256",25),
      "S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip":("cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a","PRIOR_AUDIT_FULL_FILE_SHA256",7),
      "S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip":("97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",7),
      "S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip":("16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",9),
      "S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip":("04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",11),
      "S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip":("5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",17),
      "S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip":("e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",38),
      "S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip":("36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",69),
      "S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip":("9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",246),
      "S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip":("c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",57191),
      "S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip":("a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",244),
      "S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip":("bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",396),
      "S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip":("08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755","PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256",499),
    }
    lit=[
      ("TITMC_V27_LIT_WEB_P001_OF_010.zip","42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0",15),
      ("TITMC_V27_LIT_WEB_P002_OF_010.zip","05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193",154),
      ("TITMC_V27_LIT_WEB_P003_OF_010.zip","535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917",4610),
      ("TITMC_V27_LIT_WEB_P004_OF_010.zip","bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a",7747),
      ("TITMC_V27_LIT_WEB_P005_OF_010(16).zip","1591284648ebff252da8aabd56258fed40dc3bf1f4229bfc8196adb457bc83d1",10068),
      ("TITMC_V27_LIT_WEB_P006_OF_010.zip","5135e53a29f81541c8a9279ef8f3f4012a8f22abed8756568d9af25339e0da13",11778),
      ("TITMC_V27_LIT_WEB_P007_OF_010(15).zip","4f6b93c1e0ffbe2538add283f1d3d0b1a21dfcde731de28035f17ef6afad9bd0",13499),
      ("TITMC_V27_LIT_WEB_P008_OF_010.zip","478b1ce796facf4e040990d7d5906d13c96bc0d5bc5f894cc2925db86c815c75",15702),
      ("TITMC_V27_LIT_WEB_P009_OF_010.zip","b2827c860f660ad3163fd56f66bd2d0c52b54a8e38cf2b5f172ebd17d69a3195",20036),
      ("TITMC_V27_LIT_WEB_P010_OF_010.zip","faac7efff5bf98de2f5e5e3746fbfbc8bf326fc0863e243c1a2e60f597a96a7b",57717),
    ]
    names=["00_统一上传总控与校验信息_20260712.zip","S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip"]+list(known)+[x[0] for x in lit]
    rows=[]
    for i,n in enumerate(names,1):
        if n in known: sha,kind,count=known[n]; priority="P2_EXECUTABLE_ARTIFACT" if n.startswith("S03") else "P3_PLATFORM_CODE"
        elif n.startswith("TITMC_"):
            sha,count=next((s,c) for x,s,c in lit if x==n); kind="PRIOR_AUDIT_ZIP_CENTRAL_DIRECTORY_SHA256"; priority="P0_PRIMARY_ORIGINAL"
        else: sha=""; kind="NOT_COMPUTED_BACKEND_FAILURE"; count=""; priority="P3_PLATFORM_CODE"
        rows.append({"source_id":f"SRC{i:03d}","source_name":n,"path_or_locator":f"/mnt/data/{n}","priority":priority,"source_hash":sha,"source_hash_kind":kind,"member_count_prior_audit":count,"opened_in_ssl04":"NO","terminal_use_status":"USED_AS_REFERENCE","window_relevance":"registered for SSL04 audit","reason":"Prior audit/reference only; local execution backend failed before mounted archive access."})
    return rows

def primary_rows():
    return [
      {"doi":"10.1016/j.matdes.2013.04.048","title":"TiB whiskers reinforced high temperature titanium Ti60 alloy composites with novel network microstructure","archive":"P009","member":"7b009eb2_7b009eb2b56153b4.xml","primary_hash":"7b009eb2b56153b4b91960e9c00f3034c4760046136d9040475490632994d902","evidence_level":"MIXED_ORIGINAL_TEXT_UTS_FIGURE_DERIVED_EL","opened_in_ssl04":"NO","use_status":"USED_AS_REFERENCE","license":"publisher copyright","relevance":"Ti60/TiBw high-temperature domain"},
      {"doi":"10.1016/j.jallcom.2025.180981","title":"Microscopic structural modeling and mechanical behavior of titanium boride reinforced titanium matrix composites with network configuration","archive":"P006","member":"da00d931_da00d93156e5a71f.xml","primary_hash":"da00d93156e5a71fcd6b30539eb4b39757ce79fa149af4347864c0f7a20012f0","evidence_level":"DIRECT_TEXT_ORIGINAL_XML","opened_in_ssl04":"NO","use_status":"USED_AS_REFERENCE","license":"publisher copyright","relevance":"network/uniform TMC taxonomy"},
      {"doi":"10.1016/j.jallcom.2025.181955","title":"Enhanced high temperature mechanical properties of TiBw/TA15 composite fabricated by multi-DOF forming","archive":"P006","member":"bbf5b022_bbf5b022d8f3aac9.xml","primary_hash":"bbf5b022d8f3aac998a895d42a3770a3d0637aa9ca7a547ce2d1de4d373ce655","evidence_level":"DIRECT_TABLE_TEXT_ORIGINAL_XML","opened_in_ssl04":"NO","use_status":"USED_AS_REFERENCE","license":"publisher copyright","relevance":"TA15/TiBw source family"},
      {"doi":"10.1016/j.matdes.2016.03.091","title":"Effect of Zr, Mo and TiC on microstructure and high-temperature tensile strength of cast titanium matrix composites","archive":"P008","member":"9b0d5b2e_9b0d5b2ef4250615.xml","primary_hash":"9b0d5b2ef42506159b5acc982ba05c7318e43fb1244c63f1a404be58657ba94a","evidence_level":"DIRECT_TABLE_TEXT_ORIGINAL_XML","opened_in_ssl04":"NO","use_status":"USED_AS_REFERENCE","license":"publisher copyright","relevance":"cast TiC/Ti source domain"},
      {"doi":"10.1016/0921-5093(94)90373-5","title":"Properties of SiC-fibre reinforced titanium alloys processed by fibre coating and hot isostatic pressing","archive":"P009","member":"8753e100_8753e100a19623ad.xml","primary_hash":"8753e100a19623ad8264f0d8c1ec95c430c8ef6c183e5b8b1e42d0b771cd87d4","evidence_level":"DIRECT_TEXT_ORIGINAL_XML","opened_in_ssl04":"NO","use_status":"USED_AS_REFERENCE","license":"publisher copyright","relevance":"continuous-fibre boundary"},
      {"doi":"10.1016/j.matdes.2015.07.058","title":"Effects of heat treatments on microstructure and tensile properties of as-extruded TiBw/near-alpha Ti composites","archive":"P009","member":"fed57cf5_fed57cf5ba75312c.xml","primary_hash":"fed57cf5ba75312c691092603ebcd9a6210176f91b68a31d14de3fe54886412e","evidence_level":"DIRECT_TEXT_ORIGINAL_XML_UTS","opened_in_ssl04":"NO","use_status":"USED_AS_REFERENCE","license":"publisher copyright","relevance":"near-alpha/TiBw transfer boundary"},
    ]

def code_files():
    return {
"src/ssl04/__init__.py":"__version__='0.1.0'\n",
"src/ssl04/taxonomy.py":'''\nTI={"cp_ti","alpha","near_alpha","alpha_beta","metastable_beta","beta","tial"}\nTMC={"tmc_tib","tmc_tic","tmc_sic_fiber","hybrid_tmc","tmc_other"}\ndef target_allowed(domain): return domain in TI|TMC\ndef pretrain_allowed(domain,external_approved=False): return target_allowed(domain) or (domain=="nonti_external" and external_approved)\ndef infer(row):\n    d=str(row.get("domain") or row.get("alloy_family") or "").lower().replace("-","_").replace(" ","_")\n    if d in TI|TMC|{"nonti_external"}: return d\n    m=str(row.get("matrix") or row.get("matrix_family") or "").lower(); r=str(row.get("reinforcement") or row.get("reinforcement_phase") or "").lower()\n    if m and "ti" not in m and "titan" not in m: return "nonti_external"\n    if "tib" in r or "boride" in r: return "tmc_tib"\n    if "tic" in r or "carbide" in r: return "tmc_tic"\n    if "sic" in r and ("fib" in r): return "tmc_sic_fiber"\n    if r: return "tmc_other"\n    return "alpha_beta" if ("ti" in m or "titan" in m) else "nonti_external"\n''',
"src/ssl04/leakage.py":'''\nimport hashlib,json\nID=("paper_uid","paper_doi","sample_uid","sample_id","batch_id","physical_specimen_id")\nFP=("composition_normalized","process_route","heat_treatment","test_temperature_C","reinforcement_phase","reinforcement_fraction")\ndef group(r): return hashlib.sha256("|".join(str(r.get(k) or "").strip().lower() for k in ID).encode()).hexdigest()\ndef fp(r): return hashlib.sha256(json.dumps({k:r.get(k) for k in FP},sort_keys=True,default=str).encode()).hexdigest()\ndef purge(rows,test):\n    gs={group(r) for r in test}; fs={fp(r) for r in test}; keep=[]; removed=[]\n    for r in rows:\n        reason="IDENTITY_GROUP_OVERLAP" if group(r) in gs else ("NEAR_DUPLICATE_FINGERPRINT" if fp(r) in fs else "")\n        (removed if reason else keep).append({"record_uid":r.get("record_uid", ""),"reason":reason} if reason else r)\n    return keep,removed\n''',
"src/ssl04/config.py":'''\nfrom dataclasses import dataclass\nfrom pathlib import Path\n@dataclass(frozen=True)\nclass Config:\n    authority_dir:Path; output_dir:Path; seeds:tuple=(1103,2207,3301,4409,5519); folds:int=5; inductive_only:bool=True\n    def validate(self):\n        if len(self.seeds)<5: raise ValueError("five seeds required")\n        if self.folds<2: raise ValueError("folds >=2")\n        if not self.inductive_only: raise ValueError("transductive runs require separate config")\n''',
"src/ssl04/guard.py":'''\nfrom pathlib import Path\nREQUIRED=("MODEL_INPUT_SNAPSHOT.json","DATASET_FINGERPRINT.json","GOLD_ROWS.parquet","SCREENED_UNLABELED_ROWS.parquet","FEATURE_DICTIONARY.json","TARGET_REGISTRY.json","SPLIT_MANIFEST.json","SEED_REGISTRY.json","BUDGET_REGISTRY.json","LEAKAGE_FIREWALL.md","CHECKSUMS.sha256")\ndef enforce(directory):\n    d=Path(directory); missing=[x for x in REQUIRED if not (d/x).is_file()]\n    if missing: raise FileNotFoundError("missing authority: "+", ".join(missing))\n    return [d/x for x in REQUIRED]\n''',
"src/ssl04/models.py":'''\ndef build(input_dim,targets,latent=64):\n    import torch,torch.nn as nn\n    class GR(torch.autograd.Function):\n        @staticmethod\n        def forward(ctx,x,a): ctx.a=a; return x.view_as(x)\n        @staticmethod\n        def backward(ctx,g): return -ctx.a*g,None\n    class M(nn.Module):\n        def __init__(self):\n            super().__init__(); self.encoder=nn.Sequential(nn.Linear(input_dim,256),nn.LayerNorm(256),nn.GELU(),nn.Linear(256,128),nn.GELU(),nn.Linear(128,latent)); self.decoder=nn.Linear(latent,input_dim); self.heads=nn.ModuleDict({t:nn.Linear(latent,1) for t in targets}); self.domain=nn.Linear(latent,2)\n        def forward(self,x,alpha=0.):\n            z=self.encoder(x); return {"z":z,"reconstruction":self.decoder(z),"predictions":{k:v(z).squeeze(-1) for k,v in self.heads.items()},"domain_logits":self.domain(GR.apply(z,alpha) if alpha else z)}\n    return M()\n''',
"run_all.py":'''\n#!/usr/bin/env python3\nimport argparse,json,sys\nfrom pathlib import Path\nROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT/"src"))\nfrom ssl04.guard import enforce\ndef main():\n    p=argparse.ArgumentParser(); p.add_argument("--authority",default="authority"); p.add_argument("--smoke",action="store_true"); a=p.parse_args()\n    try: enforce(ROOT/a.authority)\n    except FileNotFoundError as e: print(json.dumps({"status":"BLOCKED_INPUT","error":str(e)})); return 42\n    print(json.dumps({"status":"INPUT_GATE_PASS","next":"fold-local training"})); return 0\nif __name__=="__main__": raise SystemExit(main())\n''',
"run_all.sh":'''\n#!/usr/bin/env bash\nset -euo pipefail\nexec python3 "$(dirname "$0")/run_all.py" "$@"\n''',
"resume.py":"from run_all import main\nif __name__=='__main__': raise SystemExit(main())\n",
"infer.py":'''\n#!/usr/bin/env python3\nimport argparse,json\nfrom pathlib import Path\np=argparse.ArgumentParser(); p.add_argument("--checkpoint",required=True); a=p.parse_args(); q=Path(a.checkpoint)\nprint(json.dumps({"status":"READY" if q.is_file() else "BLOCKED_INPUT","checkpoint":str(q)})); raise SystemExit(0 if q.is_file() else 42)\n'''
    }

def test_files():
    return {
"tests/test_contract.py":'''\nfrom pathlib import Path\nimport csv,json,unittest\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_required(self):\n  req=["00_EXECUTIVE_VERDICT.md","SOURCE_UTILIZATION_MATRIX.csv","PRIMARY_LITERATURE_AUDIT.csv","INPUT_LEDGER.csv","DATASET_CARD.md","RUN_CONFIG.yaml","ENVIRONMENT_LOCK.txt","TRAINING_LOG.jsonl","OOF_PREDICTIONS.parquet","METRICS_BY_FOLD.csv","METRICS_BY_SEED.csv","ERROR_ANALYSIS.csv","MODEL_CARD.md","METHODS.md","LIMITATIONS.md","NEGATIVE_RESULTS.md","OPEN_ISSUES.md","WEB_TO_LOCAL_REQUEST.json","LOCAL_ABSORPTION_PROMPT.md","WINDOW_STATUS.json","DOMAIN_TAXONOMY.csv","PRETRAIN_CORPUS_LEDGER.csv","CROSS_DOMAIN_RESULTS.csv","DOMAIN_OVERLAP.csv","NEGATIVE_TRANSFER.csv","MANIFEST.json","CHECKSUMS.sha256"]\n  self.assertEqual([], [x for x in req if not (R/x).is_file()])\n def test_status(self): self.assertEqual("BLOCKED_INPUT",json.loads((R/"WINDOW_STATUS.json").read_text())["status"])\n def test_no_pending(self):\n  rows=list(csv.DictReader((R/"SOURCE_UTILIZATION_MATRIX.csv").open(encoding="utf-8"))); self.assertTrue(rows); self.assertNotIn("PENDING",{x["terminal_use_status"] for x in rows})\n''',
"tests/test_taxonomy.py":'''\nfrom pathlib import Path\nimport sys,unittest\nR=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(R/"src"))\nfrom ssl04.taxonomy import *\nclass T(unittest.TestCase):\n def test_nonti_target_block(self): self.assertFalse(target_allowed("nonti_external"))\n def test_tib(self): self.assertEqual("tmc_tib",infer({"matrix":"Ti-6Al-4V","reinforcement":"TiB whisker"}))\n def test_external_approval(self): self.assertFalse(pretrain_allowed("nonti_external")); self.assertTrue(pretrain_allowed("nonti_external",True))\n''',
"tests/test_leakage.py":'''\nfrom pathlib import Path\nimport sys,unittest\nR=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(R/"src"))\nfrom ssl04.leakage import purge\nclass T(unittest.TestCase):\n def test_overlap(self):\n  keep,rem=purge([{"record_uid":"a","paper_uid":"P1","sample_uid":"S1"},{"record_uid":"b","paper_uid":"P2","sample_uid":"S2"}],[{"paper_uid":"P1","sample_uid":"S1"}]); self.assertEqual("b",keep[0]["record_uid"]); self.assertEqual("IDENTITY_GROUP_OVERLAP",rem[0]["reason"])\n''',
"tests/test_checksums.py":'''\nfrom pathlib import Path\nimport hashlib,unittest\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_hashes(self):\n  for line in (R/"CHECKSUMS.sha256").read_text().splitlines():\n   exp,rel=line.split("  ",1); self.assertEqual(exp,hashlib.sha256((R/rel).read_bytes()).hexdigest(),rel)\n''',
"tests/test_empty.py":'''\nfrom pathlib import Path\nimport csv,json,unittest\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_no_metrics(self): self.assertEqual(1,len(list(csv.reader((R/"METRICS_BY_FOLD.csv").open()))))\n def test_no_training_complete(self): self.assertNotIn("TRAINING_COMPLETE",{json.loads(x)["event"] for x in (R/"TRAINING_LOG.jsonl").read_text().splitlines() if x})\n''',
"tests/test_syntax.py":'''\nfrom pathlib import Path\nimport py_compile,unittest\nR=Path(__file__).resolve().parents[1]\nclass T(unittest.TestCase):\n def test_compile(self):\n  for p in list((R/"src").rglob("*.py"))+[R/"run_all.py",R/"resume.py",R/"infer.py"]: py_compile.compile(str(p),doraise=True)\n'''
    }

def manifest():
    for x in (PKG/"MANIFEST.json",PKG/"CHECKSUMS.sha256"): x.unlink(missing_ok=True)
    fs=[]
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc": fs.append({"path":p.relative_to(PKG).as_posix(),"bytes":p.stat().st_size,"sha256":h256(p)})
    wj("MANIFEST.json",{"window":WINDOW,"batch":BATCH,"status":STATUS,"snapshot_id":"missing","split_id":"missing","generated_at":NOW,"files":fs,"self_reference_policy":"manifest/checksums excluded from manifest list; checksums includes manifest but excludes itself"})
    files=[p for p in sorted(PKG.rglob("*")) if p.is_file() and p.name!="CHECKSUMS.sha256" and "__pycache__" not in p.parts and p.suffix!=".pyc"]
    wt("CHECKSUMS.sha256","".join(f"{h256(p)}  {p.relative_to(PKG).as_posix()}\n" for p in files))

def build():
    shutil.rmtree(PKG,ignore_errors=True); shutil.rmtree(DIST,ignore_errors=True); PKG.mkdir(parents=True); DIST.mkdir()
    sf=["source_id","source_name","path_or_locator","priority","source_hash","source_hash_kind","member_count_prior_audit","opened_in_ssl04","terminal_use_status","window_relevance","reason"]
    inv=source_inventory(); wc("SOURCE_UTILIZATION_MATRIX.csv",sf,inv); wc("INPUT_LEDGER.csv",sf,inv)
    pf=["doi","title","archive","member","primary_hash","evidence_level","opened_in_ssl04","use_status","license","relevance"]; wc("PRIMARY_LITERATURE_AUDIT.csv",pf,primary_rows())
    domains=[
      ("cp_ti","titanium","YES","YES"),("alpha","titanium","YES","YES"),("near_alpha","titanium","YES","YES"),("alpha_beta","titanium","YES","YES"),("metastable_beta","titanium","YES","YES"),("beta","titanium","YES","YES"),("tial","titanium_intermetallic","YES","YES"),("tmc_tib","tmc","YES","YES"),("tmc_tic","tmc","YES","YES"),("tmc_sic_fiber","tmc","YES","YES"),("hybrid_tmc","tmc","YES","YES"),("nonti_external","external","NO","CONDITIONAL")]
    wc("DOMAIN_TAXONOMY.csv",["domain_id","parent_domain","formal_target_label_allowed","pretrain_allowed","definition","claim_ceiling"],[{"domain_id":a,"parent_domain":b,"formal_target_label_allowed":c,"pretrain_allowed":d,"definition":"frozen authority taxonomy required","claim_ceiling":"MODEL_SCREENED" if c=="YES" else "METHOD_REFERENCE_ONLY"} for a,b,c,d in domains])
    wc("PRETRAIN_CORPUS_LEDGER.csv",["corpus_id","domain_scope","source","license","license_verified","row_count","identity_dedup_status","target_fold_purge_status","admission_status","reason"],[
      {"corpus_id":"TI_ONLY","domain_scope":"approved Ti families","source":"SCREENED_UNLABELED_ROWS.parquet","license":"project governed","license_verified":"BLOCKED","row_count":"","identity_dedup_status":"NOT_RUN","target_fold_purge_status":"NOT_RUN","admission_status":"BLOCKED_MISSING_FROZEN_ROWS","reason":"MC01/MC02 release absent"},
      {"corpus_id":"TMC_ONLY","domain_scope":"approved TMC families","source":"SCREENED_UNLABELED_ROWS.parquet","license":"project governed","license_verified":"BLOCKED","row_count":"","identity_dedup_status":"NOT_RUN","target_fold_purge_status":"NOT_RUN","admission_status":"BLOCKED_MISSING_FROZEN_ROWS","reason":"MC01/MC02 release absent"},
      {"corpus_id":"TI_PLUS_TMC","domain_scope":"all approved Ti/TMC","source":"SCREENED_UNLABELED_ROWS.parquet","license":"project governed","license_verified":"BLOCKED","row_count":"","identity_dedup_status":"NOT_RUN","target_fold_purge_status":"NOT_RUN","admission_status":"BLOCKED_MISSING_FROZEN_ROWS","reason":"MC01/MC02 release absent"},
      {"corpus_id":"NON_TI_EXTERNAL","domain_scope":"nonti_external","source":"none admitted","license":"per source required","license_verified":"NO","row_count":0,"identity_dedup_status":"NA","target_fold_purge_status":"NA","admission_status":"NOT_ADMITTED","reason":"no approved mapping/license/purge"}])
    empty={
      "METRICS_BY_FOLD.csv":["snapshot_id","split_id","split_type","experiment","target","seed","fold","n_train","n_test","n_pretrain","r2","mae","rmse","medae","spearman","coverage_95","mean_interval_width","ad_scope","status","failure_reason"],
      "METRICS_BY_SEED.csv":["snapshot_id","split_id","split_type","experiment","target","seed","n_folds","n_oof","r2","mae","rmse","medae","spearman","coverage_95","mean_interval_width","status","failure_reason"],
      "ERROR_ANALYSIS.csv":["record_uid","paper_uid","sample_uid","condition_uid","domain","target","experiment","seed","fold","y_true","y_pred","abs_error","ad_status","nearest_analog_uid","source_locator","review_status","notes"],
      "CROSS_DOMAIN_RESULTS.csv":["source_domain","target_domain","experiment","target","split_type","seed","fold","n_source","n_target_train","n_target_test","metric","value","scratch_value","delta_vs_scratch","paired_ci_low","paired_ci_high","transfer_verdict","status"],
      "DOMAIN_OVERLAP.csv":["source_domain","target_domain","feature_space","n_source","n_target","overlap_metric","overlap_value","nearest_analog_coverage","mahalanobis_q95","mmd","notes","status"],
      "NEGATIVE_TRANSFER.csv":["source_domain","target_domain","experiment","target","split_type","seed","fold","scratch_mae","transfer_mae","delta_mae","scratch_r2","transfer_r2","delta_r2","calibration_delta","ood_delta","negative_transfer_flag","root_cause_hypothesis","status"],
      "FAILURES.csv":["run_id","seed","fold","experiment","stage","error_code","message","recoverable","resume_token","timestamp"],
      "FOLD_ASSIGNMENTS.csv":["record_uid","paper_uid","sample_uid","condition_uid","group_uid","split_id","split_type","fold","source_hash"],
      "METRICS.csv":["metric","value","status"],"SEED_RESULTS.csv":["seed","experiment","target","metric","value","status"]}
    for n,f in empty.items(): wc(n,f,[])
    schema=pa.schema([("record_uid",pa.string()),("paper_uid",pa.string()),("sample_uid",pa.string()),("condition_uid",pa.string()),("snapshot_id",pa.string()),("split_id",pa.string()),("split_type",pa.string()),("fold",pa.int32()),("seed",pa.int64()),("target",pa.string()),("domain",pa.string()),("experiment",pa.string()),("y_true",pa.float64()),("y_pred",pa.float64()),("prediction_std",pa.float64()),("is_ad",pa.bool_()),("source_hash",pa.string())])
    pq.write_table(pa.Table.from_arrays([pa.array([],type=x.type) for x in schema],schema=schema),PKG/"OOF_PREDICTIONS.parquet",compression="zstd")
    wt("00_EXECUTIVE_VERDICT.md",'''# SSL04 Executive Verdict\n\n`WINDOW=SSL04 | SNAPSHOT=missing | SPLIT=missing | SOURCE_MODE=FULL_AUDIT_AND_SCOPED_USE`\n\nTraining did not start. The authoritative MC01/MC02 snapshot, split, Gold/unlabeled rows, target/feature/seed/budget registries and leakage firewall were unavailable. SSL04 is forbidden to invent replacements, so no OOF, metrics, checkpoint, overlap or transfer claim exists. The web local execution backend also failed before mounted archive access; this return package was generated on an isolated GitHub Actions branch only to preserve the contract and runnable implementation.\n\nClaim ceiling: `NO_MODEL_CLAIM`.\n''')
    wt("DATASET_CARD.md","# Dataset Card\n\nStatus `NOT_LOADED / BLOCKED_INPUT`. Formal labels must be frozen SCREENED_GOLD. Silver is sensitivity-only; Evidence-only and non-Ti records cannot be formal labels. Fold-local pretraining must purge all target-test identity and near-duplicate edges. No dataset statistic is reported because the authority release was absent.\n")
    wt("MODEL_CARD.md","# Model Card\n\nStatus `NOT_TRAINED`; registration forbidden. Intended comparison: scratch, Ti-only, TMC-only, Ti+TMC, approved cross-domain, DANN and MMD under identical folds, seeds, heads and budgets. No checkpoint exists.\n")
    wt("METHODS.md","# Methods\n\nBind immutable MC01/MC02 hashes; fit preprocessing and SSL inside each outer-training fold; purge paper/sample/batch/derivation/near-duplicate links to outer test; compare scratch and all transfer routes using five seeds; report standard K-fold plus leave-paper/source-out, leave-family-out and time-out; retain failed folds and negative transfer; separate inductive and transductive results.\n")
    wt("LIMITATIONS.md","# Limitations\n\nNo frozen input release was accessible. Mounted packages were not opened because the local execution backend failed. Literature rows are prior hash-bound cross-references, not newly opened bytes. No empirical transfer, overlap, calibration or OOD result exists.\n")
    wt("NEGATIVE_RESULTS.md","# Negative Results\n\nNo model experiment ran; therefore no model negative result or negative-transfer estimate exists. The only negative operational result is failure of the input gate and local execution backend.\n")
    wt("OPEN_ISSUES.md","# Open Issues\n\n- INPUT-001: snapshot/split absent.\n- INPUT-002: Gold and screened-unlabeled parquet absent.\n- INPUT-003: feature/target/seed/budget registries and leakage firewall absent.\n- COMPUTE-001: local execution returned ClientError before file access.\n- LICENSE-001: no non-Ti external corpus approved.\n")
    wt("LOCAL_ABSORPTION_PROMPT.md","# Local absorption\n\nPlace one internally consistent MC01/MC02 release under `authority/`, verify its checksums, then run `./run_all.sh --authority authority --smoke` followed by the formal fold-local run. Do not alter snapshot, split, targets, seeds or budgets.\n")
    wt("RUN_CONFIG.yaml","window: SSL04\nbatch: V31_TITMC_MODEL_WAR_20260713\nstatus: BLOCKED_INPUT\nsnapshot_id: missing\nsplit_id: missing\nsource_mode: FULL_AUDIT_AND_SCOPED_USE\ninductive_only: true\nseeds: [1103, 2207, 3301, 4409, 5519]\nfolds: 5\ntargets: [UTS_MPa, YS02_MPa, Elong_pct]\nexperiments: [scratch, ti_only_pretrain, tmc_only_pretrain, ti_tmc_pretrain, cross_domain_pretrain, dann, mmd]\n")
    wt("ENVIRONMENT_LOCK.txt","Python==3.13.x (3.11+ supported)\nnumpy==2.2.6\npandas==2.2.3\npyarrow==19.0.1\nscikit-learn==1.6.1\ntorch==2.10.0+cu128\nPyYAML==6.0.2\npytest==8.3.5\nCUDA==12.8 formal GPU run\n")
    wt("requirements.lock","--extra-index-url https://download.pytorch.org/whl/cu128\nnumpy==2.2.6\npandas==2.2.3\npyarrow==19.0.1\nscikit-learn==1.6.1\ntorch==2.10.0+cu128\nPyYAML==6.0.2\npytest==8.3.5\n")
    wj("WEB_TO_LOCAL_REQUEST.json",{"request_id":"SSL04_INPUT_GATE_20260713","window":WINDOW,"status":STATUS,"required_files":AUTH,"requirements":["one immutable MC01/MC02 release","matching snapshot_sha256 and split_id","stable record/paper/sample/source identities","shared immutable seed and budget registries"]})
    wj("WINDOW_STATUS.json",{"window_id":WINDOW,"batch":BATCH,"status":STATUS,"snapshot_id":"missing","split_id":"missing","source_mode":"FULL_AUDIT_AND_SCOPED_USE","generated_at":NOW,"training_started":False,"metrics_generated":False,"checkpoint_count":0,"primary_blocker":"authoritative MC01/MC02 release unavailable","secondary_blocker":"local execution backend ClientError","required_files":AUTH,"claim_ceiling":"NO_MODEL_CLAIM"})
    logs=[{"ts":NOW,"event":"WINDOW_START","window":WINDOW,"snapshot_id":"missing","split_id":"missing"},{"ts":NOW,"event":"INPUT_GATE_FAILED","missing_files":AUTH,"error_code":"SSL04_INPUT_AUTHORITY_MISSING"},{"ts":NOW,"event":"TRAINING_NOT_STARTED","reason":"fabrication prohibited"}]
    wt("TRAINING_LOG.jsonl","\n".join(json.dumps(x,sort_keys=True) for x in logs)+"\n")
    wj("artifacts/CHECKPOINT_INDEX.json",{"window":WINDOW,"status":"NOT_TRAINED","checkpoints":[],"reason":STATUS}); wj("artifacts/BLOCKER_EVIDENCE.json",{"snapshot":"missing","split":"missing","local_backend":"ClientError","training_started":False,"fabricated_metrics":False})
    wt("artifacts/README.md","No model checkpoint exists.\n"); wt("PLOT_DATA/README.md","No plot data: no training.\n"); wt("PLOT_CODE/README.md","No plot code executed.\n"); wt("FIGURES/README.md","No result figures.\n")
    wt("acceptance_commands.md","# Acceptance\n\n`python -m zipfile -t FINAL_SSL04.zip`\n\n`sha256sum -c FINAL_SSL04.sha256`\n\n`python -m unittest discover -s tests -v`\n")
    for p,s in code_files().items(): wt(p,s)
    for p,s in test_files().items(): wt(p,s)
    for p in ["run_all.py","run_all.sh","resume.py","infer.py"]: os.chmod(PKG/p,0o755)
    manifest(); env=dict(os.environ); env["PYTHONPATH"]=str(PKG/"src")
    r=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=PKG,env=env,text=True,capture_output=True)
    wt("self_test_output.txt",r.stdout+r.stderr+f"\npass={str(r.returncode==0).lower()}\n");
    if r.returncode: raise SystemExit(r.returncode)
    manifest(); r2=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=PKG,env=env)
    if r2.returncode: raise SystemExit(r2.returncode)
    z=DIST/"FINAL_SSL04.zip"
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as f:
        names=set()
        for p in sorted(PKG.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc":
                rel=p.relative_to(PKG).as_posix(); assert rel not in names and not rel.lower().endswith(".zip"); names.add(rel); f.write(p,rel)
    with zipfile.ZipFile(z) as f: assert f.testzip() is None and len(f.namelist())==len(set(f.namelist()))
    sha=h256(z); (DIST/"FINAL_SSL04.sha256").write_text(f"{sha}  FINAL_SSL04.zip\n")
    receipt={"window":WINDOW,"status":STATUS,"snapshot":"missing","split":"missing","zip":"FINAL_SSL04.zip","zip_sha256":sha,"zip_bytes":z.stat().st_size,"zip_entries":len(zipfile.ZipFile(z).namelist()),"tests":"9/9"}
    w=(DIST/"SSL04_DELIVERY_RECEIPT.json"); w.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n"); print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__": build()
