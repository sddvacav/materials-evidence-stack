from __future__ import annotations
import csv, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent / "dist" / "FINAL_XW05"
EXPECTED = 78683
STAMP = "2026-07-13T08:30:00Z"

def wt(rel, text):
    p=ROOT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8",newline="\n")
def wc(rel, fields, rows=()):
    p=ROOT/rel; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def sh(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

a = '''from __future__ import annotations
import argparse,csv,hashlib,json,os,re,sqlite3,zipfile
from collections import Counter
from pathlib import Path
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree
EXPECTED_XML=78683
PARSER_VERSION="xw05-parser-1.0.0"
ONTOLOGY_VERSION="figures-objects-supplements-1.0.0"
SCHEMA_VERSION="xw05-schema-1.0.0"
FIG={"figure","fig"}; CAP={"caption","legend"}
OBJ={"graphic","inline-graphic","link","object","media","attachment","supplementary-material","supplement","dataset","data-object","file","resource","video","audio"}
ATT={"attachment","supplementary-material","supplement","dataset","data-object","file","resource","video","audio","media"}
LOC=("locator","href","{http://www.w3.org/1999/xlink}href","filename","file-name","src","uri","url","ref","rid","refid")
class SecurityError(ValueError): pass
def norm(x): return re.sub(r"\\s+"," ",x or "").strip()
def ln(n):
    try:return etree.QName(n).localname.lower()
    except:return str(n.tag).split("}")[-1].lower()
def text(n): return norm("".join(n.itertext())) if n is not None else ""
def htxt(x): return hashlib.sha256(norm(x).encode()).hexdigest()
def hel(n):
    try:b=etree.tostring(n,method="c14n",with_comments=False)
    except:b=etree.tostring(n,encoding="utf-8",with_tail=False)
    return hashlib.sha256(b).hexdigest()
def parser(recover=False): return etree.XMLParser(recover=recover,resolve_entities=False,no_network=True,load_dtd=False,huge_tree=True,strip_cdata=False)
def parse(data):
    head=data[:8192].lower()
    if b"<!entity" in head or b"system " in head or b"public " in head: raise SecurityError("external entity/DTD rejected")
    try:return etree.fromstring(data,parser(False)).getroottree(),"strict",[]
    except etree.XMLSyntaxError as e:return etree.fromstring(data,parser(True)).getroottree(),"recover",[norm(str(e))]
def attr(n,keys):
    low={k.split("}")[-1].lower() for k in keys}
    for k,v in n.attrib.items():
        if (k in keys or k.split("}")[-1].lower() in low) and v:return norm(v)
def xp(t,n):
    try:return t.getpath(n)
    except:return ""
def anc(n,names):
    p=n.getparent()
    while p is not None:
        if ln(p) in names:return True
        p=p.getparent()
    return False
def identity(root):
    zones=[n for n in root.iter() if ln(n) in {"coredata","article-head","head","item-info"}]+[root]
    out={"article_doi":None,"article_pii":None,"eid":None,"article_title_normalized":None,"article_type":attr(root,("article-type","type"))}
    for z in zones:
        for n in z.iter():
            if anc(n,{"bibliography","reference-list","references"}):continue
            l=ln(n);v=text(n)
            if not v:continue
            if out["article_title_normalized"] is None and l in {"title","article-title"}:out["article_title_normalized"]=v
            if out["article_doi"] is None and l in {"doi","identifier"}:
                m=re.search(r"10\\.\\d{4,9}/\\S+",v,re.I)
                if m:out["article_doi"]=m.group(0).rstrip(".,;)")
            if out["article_pii"] is None and l in {"pii","publisher-item-identifier"}:out["article_pii"]=v
            if out["eid"] is None and l in {"eid","scopus-id"}:out["eid"]=v
        if out["article_title_normalized"] and any(out[k] for k in ("article_doi","article_pii","eid")):break
    return out
def panels(c):
    r=[]
    for x in re.findall(r"\\(([A-Za-z0-9]{1,3})\\)",c):
        x=x.lower()
        if x not in r:r.append(x)
    return r
def ftype(c):
    q=c.lower()
    for k,terms in [("EBSD",("ebsd","inverse pole figure","kam","gnd")),("TEM",("tem ","hrtem","transmission electron")),("SEM",("sem ","scanning electron")),("XRD",("xrd","x-ray diffraction")),("stress_strain",("stress-strain","stress–strain")),("fractography",("fracture surface","fractograph")),("schematic",("schematic","workflow"))]:
        if any(t in q for t in terms):return k
    return "other"
def base(ctx,t,n):
    q=text(n);return {**{k:ctx[k] for k in ("member_uid","source_package","package_sha256","member_path","crc32")},"xpath":xp(t,n),"element_hash":hel(n),"text_hash":htxt(q),"parser_version":PARSER_VERSION,"ontology_version":ONTOLOGY_VERSION,"schema_version":SCHEMA_VERSION}
def extract(data,ctx):
    t,mode,errs=parse(data);r=t.getroot();els=list(r.iter());ids=identity(r);figs=[];caps=[];objs=[];atts=[];rels=[];fidset=set()
    fnodes=[n for n in els if ln(n) in FIG]
    for i,n in enumerate(fnodes,1):
        fid=attr(n,("id","xml:id","figure-id")) or f"generated-figure-{i}";fidset.add(fid)
        lab=next((text(x) for x in n if ln(x)=="label"),"");cn=next((x for x in n.iter() if ln(x) in CAP),None);c=text(cn)
        ons=[x for x in n.iter() if x is not n and ln(x) in OBJ];loc=attr(n,LOC) or next((attr(x,LOC) for x in ons if attr(x,LOC)),None)
        figs.append({**base(ctx,t,n),"figure_id":fid,"figure_ordinal":i,"figure_label":lab,"caption_text":c,"figure_type":ftype(c),"subpanel_labels_json":json.dumps(panels(c)),"object_count":len(ons),"primary_locator":loc,"missing_reason":"" if c else "caption_not_present_in_xml"})
        if cn is not None:caps.append({**base(ctx,t,cn),"figure_id":fid,"figure_label":lab,"caption_text":c,"caption_length":len(c),"subpanel_labels_json":json.dumps(panels(c)),"evidence_snippet":c[:500]})
        for j,o in enumerate(ons,1):
            ol=attr(o,LOC);objs.append({**base(ctx,t,o),"link_type":"figure_contains_object","source_id":fid,"target_id":attr(o,("id","xml:id")) or f"{fid}-object-{j}","target_locator":ol,"object_type":ln(o),"mime_type":attr(o,("mime-type","content-type","type")),"filename":attr(o,("filename","file-name","name")) or (Path(ol).name if ol else None),"size_bytes_reported":attr(o,("size","file-size","bytes")),"link_text":text(o)[:500],"missing_reason":"" if ol else "locator_not_present_in_xml"})
    for n in els:
        if ln(n) not in ATT or anc(n,FIG):continue
        loc=attr(n,LOC);name=attr(n,("filename","file-name","name")) or (Path(loc).name if loc else None);aid=attr(n,("id","xml:id")) or hashlib.sha256(f"{ctx['member_uid']}|{xp(t,n)}".encode()).hexdigest()[:20];sup=ln(n) in {"supplementary-material","supplement"} or bool(re.search(r"supp|mmc|data",name or "",re.I))
        rec={**base(ctx,t,n),"attachment_id":aid,"attachment_type":ln(n),"filename":name,"mime_type":attr(n,("mime-type","content-type","type")),"size_bytes_reported":attr(n,("size","file-size","bytes")),"url_or_locator":loc,"title_or_label":text(n)[:500],"is_supplement":sup,"missing_reason":"" if loc or name else "filename_and_locator_not_present_in_xml"};atts.append(rec)
        rels.append({**base(ctx,t,n),"relation_id":hashlib.sha256(f"{ctx['member_uid']}|{aid}".encode()).hexdigest()[:24],"article_doi":ids["article_doi"],"figure_id":None,"attachment_id":aid,"relation_type":"article_has_supplement" if sup else "article_has_attachment","relation_locator":loc,"relation_evidence":rec["title_or_label"],"missing_reason":"" if loc or name else "relation_target_not_resolved"})
    for n in els:
        if ln(n) not in {"xref","cross-ref","inter-ref","link"}:continue
        target=attr(n,("rid","refid","href","{http://www.w3.org/1999/xlink}href"))
        if target and target.lstrip("#") in fidset:objs.append({**base(ctx,t,n),"link_type":"body_references_figure","source_id":attr(n.getparent(),("id",)) if n.getparent() is not None else None,"target_id":target.lstrip("#"),"target_locator":target,"object_type":"xref","mime_type":None,"filename":None,"size_bytes_reported":None,"link_text":text(n)[:500],"missing_reason":""})
    c=Counter(ln(n) for n in els);title=ids["article_title_normalized"] or "";scope="TI_TMC_POSSIBLE" if re.search(r"titanium matrix composite|tibw|\\btmc\\b",(title+text(r)[:12000]).lower()) else ("TI_ALLOY_IN_SCOPE" if re.search(r"titanium|\\bti[-– ]?(?:alloy|6al)",title.lower()) else "NON_TITANIUM")
    anchor={**ctx,"xml_sha256":hashlib.sha256(data).hexdigest(),**ids,"scope_state":scope,"section_count":c["section"]+c["sec"],"table_count":c["table"]+c["tgroup"],"figure_count":len(fnodes),"formula_count":c["formula"]+c["math"],"reference_count":c["reference"]+c["ref"],"parser_version":PARSER_VERSION,"parse_mode":mode,"parse_status":"PARSED","terminal_state":"DOMAIN_EXTRACTED"}
    term={"member_uid":ctx["member_uid"],"scope_state":scope,"parse_mode":mode,"parse_status":"PARSED","domain_state":"FIGURES_OBJECTS_SUPPLEMENTS_EXTRACTED","figure_rows":len(figs),"object_link_rows":len(objs),"attachment_rows":len(atts),"supplement_relation_rows":len(rels),"terminal_state":"TERMINAL","missing_reason":"" if figs or atts else "no_figure_or_attachment_elements_in_xml"}
    return {"anchor":anchor,"terminal":term,"figures":figs,"captions":caps,"objects":objs,"attachments":atts,"supplements":rels,"errors":errs}
def package_sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()
def uid(ps,i):return hashlib.sha256(f"{ps}|{i.filename}|{i.CRC:08x}|{i.file_size}".encode()).hexdigest()
def discover(xs):
    out=[]
    for x in xs:
        p=Path(x);out+=sorted(p.glob("TITMC_V27_LIT_WEB_P*_OF_010*.zip")) if p.is_dir() else ([p] if p.is_file() else [])
    return sorted({p.resolve():p for p in out}.values(),key=lambda p:p.name)
def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument("inputs",nargs="+");ap.add_argument("--output",default="FINAL_XW05_RUNTIME");ap.add_argument("--checkpoint",default=".xw05_checkpoint.sqlite");ns=ap.parse_args(argv);packs=discover(ns.inputs)
    if not packs:ap.error("no corpus ZIPs found")
    out=Path(ns.output);out.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(ns.checkpoint);db.execute("create table if not exists done(uid text primary key,state text)");streams={k:(out/f"{k}.jsonl").open("a",encoding="utf-8") for k in ("anchor","terminal","figures","captions","objects","attachments","supplements","errors")}
    try:
        for p in packs:
            ps=package_sha(p)
            with zipfile.ZipFile(p) as z:
                bad=z.testzip()
                if bad:raise zipfile.BadZipFile(bad)
                for i in z.infolist():
                    if i.is_dir() or not i.filename.lower().endswith(".xml"):continue
                    u=uid(ps,i)
                    if db.execute("select 1 from done where uid=?",(u,)).fetchone():continue
                    ctx={"member_uid":u,"source_package":p.name,"package_sha256":ps,"member_path":i.filename,"crc32":f"{i.CRC:08x}","xml_uncompressed_bytes":i.file_size}
                    try:r=extract(z.read(i),ctx)
                    except Exception as e:r={"terminal":{"member_uid":u,"scope_state":"UNRESOLVED_PARSE_ERROR","parse_mode":"none","parse_status":"FAILED","domain_state":"EXCLUDED_PARSE_ERROR","figure_rows":0,"object_link_rows":0,"attachment_rows":0,"supplement_relation_rows":0,"terminal_state":"TERMINAL","missing_reason":f"{type(e).__name__}: {e}"},"errors":[{"member_uid":u,"source_package":p.name,"member_path":i.filename,"severity":"ERROR","message":f"{type(e).__name__}: {e}"}]}
                    for k,v in r.items():
                        if k not in streams:continue
                        rows=v if isinstance(v,list) else [v]
                        for row in rows:streams[k].write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\\n")
                    db.execute("insert into done values(?,?)",(u,"TERMINAL"));db.commit()
    finally:
        for f in streams.values():f.close()
        db.close()
    return 0
if __name__=="__main__":raise SystemExit(main())
'''

validator='''from pathlib import Path
import csv,hashlib,json,sys
import pyarrow.parquet as pq
r=Path(sys.argv[1]); req=["FIGURES.parquet","FIGURE_CAPTIONS.parquet","OBJECT_LINKS.parquet","ATTACHMENTS.parquet","SUPPLEMENT_RELATIONS.parquet","DOCUMENT_ANCHORS.csv","DOCUMENT_TERMINAL_STATES.csv","MANIFEST.json","CHECKSUMS.sha256","WINDOW_STATUS.json"]
assert all((r/x).exists() for x in req)
assert not list(r.rglob("*.zip"))
for line in (r/"CHECKSUMS.sha256").read_text().splitlines():
 e,p=line.split("  ",1);assert hashlib.sha256((r/p).read_bytes()).hexdigest()==e,p
s=json.loads((r/"WINDOW_STATUS.json").read_text());assert s["status"]=="CONTINUE" and s["pending"]==78683 and not s["task_complete_claimed"]
print("VALIDATION_PASS")
'''

tests={
"test_01_security.py":'''import pytest\nfrom PARSER_CODE.xw05 import parse,SecurityError\ndef test_xxe():\n with pytest.raises(SecurityError):parse(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')\n''',
"test_02_modes.py":'''from PARSER_CODE.xw05 import parse\ndef test_modes():\n assert parse(b'<r><a/></r>')[1]=='strict';assert parse(b'<r><a></r>')[1]=='recover'\n''',
"test_03_figure.py":'''from PARSER_CODE.xw05 import extract\ndef test_figure():\n x=b'<article><figure id="f1"><label>Fig. 1</label><caption>(a) SEM (b) TEM</caption><graphic href="x.jpg"/></figure></article>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};r=extract(x,c);assert r['figures'][0]['figure_id']=='f1';assert r['objects'][0]['target_locator']=='x.jpg'\n''',
"test_04_namespace.py":'''from PARSER_CODE.xw05 import extract\ndef test_ns():\n x=b'<r xmlns:ce="u" xmlns:xlink="http://www.w3.org/1999/xlink"><ce:figure id="f"><ce:caption>XRD patterns</ce:caption><ce:link xlink:href="a.png"/></ce:figure></r>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};r=extract(x,c);assert r['figures'][0]['figure_type']=='XRD'\n''',
"test_05_attachment.py":'''from PARSER_CODE.xw05 import extract\ndef test_att():\n x=b'<article><supplementary-material id="s" filename="mmc1.xlsx"><title>data</title></supplementary-material></article>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};r=extract(x,c);assert r['attachments'][0]['is_supplement'];assert r['supplements'][0]['relation_type']=='article_has_supplement'\n''',
"test_06_xref.py":'''from PARSER_CODE.xw05 import extract\ndef test_xref():\n x=b'<article><p><xref rid="f1">Fig 1</xref></p><figure id="f1"><caption>plot</caption></figure></article>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};r=extract(x,c);assert any(v['link_type']=='body_references_figure' for v in r['objects'])\n''',
"test_07_doi.py":'''from PARSER_CODE.xw05 import extract\ndef test_doi():\n x=b'<article><head><doi>10.1000/a</doi></head><bibliography><reference><doi>10.9999/b</doi></reference></bibliography></article>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};assert extract(x,c)['anchor']['article_doi']=='10.1000/a'\n''',
"test_08_terminal.py":'''from PARSER_CODE.xw05 import extract\ndef test_terminal():\n x=b'<article><title>steel</title></article>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};r=extract(x,c);assert r['terminal']['terminal_state']=='TERMINAL';assert r['terminal']['missing_reason']\n''',
"test_09_determinism.py":'''from PARSER_CODE.xw05 import extract\ndef test_det():\n x=b'<article><figure id="f"><caption>plot</caption></figure></article>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};assert extract(x,c)==extract(x,c)\n''',
"test_10_mixed.py":'''from PARSER_CODE.xw05 import extract\ndef test_mixed():\n x=b'<article><p>A<sup>2</sup><math><mi>x</mi></math></p></article>';c={'member_uid':'u','source_package':'p','package_sha256':'s','member_path':'m','crc32':'0','xml_uncompressed_bytes':len(x)};assert extract(x,c)['anchor']['formula_count']==1\n'''}

def schema(extra):
 common=[pa.field(x,pa.string()) for x in ("member_uid","source_package","package_sha256","member_path","crc32","xpath","element_hash","text_hash","parser_version","ontology_version","schema_version")]
 return pa.schema(common+extra)
fig=schema([pa.field("figure_id",pa.string()),pa.field("figure_ordinal",pa.int64()),pa.field("figure_label",pa.string()),pa.field("caption_text",pa.string()),pa.field("figure_type",pa.string()),pa.field("subpanel_labels_json",pa.string()),pa.field("object_count",pa.int64()),pa.field("primary_locator",pa.string()),pa.field("missing_reason",pa.string())])
cap=schema([pa.field("figure_id",pa.string()),pa.field("figure_label",pa.string()),pa.field("caption_text",pa.string()),pa.field("caption_length",pa.int64()),pa.field("subpanel_labels_json",pa.string()),pa.field("evidence_snippet",pa.string())])
obj=schema([pa.field(x,pa.string()) for x in ("link_type","source_id","target_id","target_locator","object_type","mime_type","filename","size_bytes_reported","link_text","missing_reason")])
att=schema([pa.field("attachment_id",pa.string()),pa.field("attachment_type",pa.string()),pa.field("filename",pa.string()),pa.field("mime_type",pa.string()),pa.field("size_bytes_reported",pa.string()),pa.field("url_or_locator",pa.string()),pa.field("title_or_label",pa.string()),pa.field("is_supplement",pa.bool_()),pa.field("missing_reason",pa.string())])
rel=schema([pa.field(x,pa.string()) for x in ("relation_id","article_doi","figure_id","attachment_id","relation_type","relation_locator","relation_evidence","missing_reason")])
dom=pa.schema([pa.field("member_uid",pa.string()),pa.field("scope_state",pa.string()),pa.field("domain_state",pa.string()),pa.field("figure_rows",pa.int64()),pa.field("object_link_rows",pa.int64()),pa.field("attachment_rows",pa.int64()),pa.field("supplement_relation_rows",pa.int64()),pa.field("terminal_state",pa.string()),pa.field("missing_reason",pa.string())])

def empty(name,s):pq.write_table(pa.Table.from_pylist([],schema=s),ROOT/name,compression="zstd")
def build():
 if ROOT.exists():shutil.rmtree(ROOT)
 ROOT.mkdir(parents=True);wt("PARSER_CODE/__init__.py","from .xw05 import *\n");wt("PARSER_CODE/xw05.py",a);wt("PARSER_CODE/validate.py",validator);wt("requirements.lock","lxml==5.4.0\npyarrow==20.0.0\npytest==8.4.1\n");wt("pytest.ini","[pytest]\ntestpaths=TESTS\naddopts=-q\n")
 for n,v in tests.items():wt("TESTS/"+n,v)
 for n,s in [("FIGURES.parquet",fig),("FIGURE_CAPTIONS.parquet",cap),("OBJECT_LINKS.parquet",obj),("ATTACHMENTS.parquet",att),("SUPPLEMENT_RELATIONS.parquet",rel),("DOMAIN_RECORDS.parquet",dom)]:empty(n,s)
 anchors=["member_uid","source_package","package_sha256","member_path","crc32","xml_uncompressed_bytes","xml_sha256","article_doi","article_pii","eid","article_title_normalized","article_type","scope_state","section_count","table_count","figure_count","formula_count","reference_count","parser_version","parse_mode","parse_status","terminal_state"]
 terms=["member_uid","scope_state","parse_mode","parse_status","domain_state","figure_rows","object_link_rows","attachment_rows","supplement_relation_rows","terminal_state","missing_reason"]
 wc("DOCUMENT_ANCHORS.csv",anchors);wc("DOCUMENT_TERMINAL_STATES.csv",terms);wc("CROSSCHECK_FIELDS.csv",["member_uid","field_name","xw05_value","other_source","other_value","agreement_state","resolution_state"]);wt("PROVENANCE.jsonl","");wc("PARSE_ERRORS.csv",["member_uid","source_package","member_path","severity","message"]);wc("CONFLICT_LEDGER.csv",["conflict_id","member_uid","field_name","xml_value","other_value","resolution_state","xml_xpath"]);wc("EXCLUDED_RECORDS.csv",["member_uid","scope_state","exclusion_reason","terminal_state"]);wc("MISSINGNESS_MATRIX.csv",["member_uid","field_name","is_missing","missing_reason"])
 rows=[]
 for i in range(1,11):rows.append({"source_id":f"P{i:03d}","source_name":f"TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip","priority":"P0","opened":"NO","terminal_use_state":"BLOCKED_SOURCE_BYTES_NOT_AVAILABLE_TO_GITHUB_RUNNER","records_emitted":0})
 wc("SOURCE_UTILIZATION_LEDGER.csv",["source_id","source_name","priority","opened","terminal_use_state","records_emitted"],rows)
 wt("COVERAGE_REPORT.json",json.dumps({"batch":"V29X_C10_XML_CROSS_EXTRACTION_20260713","window":"XW05","expected_xml":EXPECTED,"anchor_rows":0,"terminal_rows":0,"pending_rows":EXPECTED,"status":"CONTINUE","blocker":"ten uploaded source ZIP byte streams were unavailable to the public CI runner"},indent=2)+"\n")
 wt("FIELD_DICTIONARY.json",json.dumps({"authority":"publisher XML primary","common_provenance":["member_uid","source_package","package_sha256","member_path","crc32","xpath","element_hash","text_hash"],"schemas":{"FIGURES":fig.names,"FIGURE_CAPTIONS":cap.names,"OBJECT_LINKS":obj.names,"ATTACHMENTS":att.names,"SUPPLEMENT_RELATIONS":rel.names}},indent=2)+"\n")
 wt("LOCAL_CODEX_ABSORPTION_PROMPT.md","# XW05 local absorption\nRun `python -m PARSER_CODE.xw05 <directory-with-10-zips> --output FINAL_XW05_RUNTIME --checkpoint .xw05_checkpoint.sqlite`. Preserve checkpoints; validate exact 78,683 anchors and terminal states; rebuild MANIFEST and CHECKSUMS; never claim TASK_COMPLETE before pending=0.\n")
 wt("WINDOW_STATUS.json",json.dumps({"batch":"V29X_C10_XML_CROSS_EXTRACTION_20260713","window":"XW05","status":"CONTINUE","xml_terminal":0,"xml_expected":EXPECTED,"pending":EXPECTED,"task_complete_claimed":False,"gold_claimed":False,"next":"mount all ten exact source ZIPs and execute packaged parser"},indent=2)+"\n")
 wt("README.md","# FINAL_XW05\n\nAuditable CONTINUE package. It contains a secure streaming parser and ten tests, but no fabricated corpus rows. The producing runner did not have the ten uploaded ZIP byte streams.\n")
 sys.path.insert(0,str(ROOT));q=subprocess.run([sys.executable,"-m","pytest","-q","TESTS"],cwd=ROOT,text=True,capture_output=True);wt("TEST_RECEIPT.md",f"# TEST RECEIPT\n\n```text\n{q.stdout}{q.stderr}```\n\nexit_code={q.returncode}\n");
 if q.returncode:raise SystemExit(q.returncode)
 fs=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json","CHECKSUMS.sha256"});m={"batch":"V29X_C10_XML_CROSS_EXTRACTION_20260713","window":"XW05","status":"CONTINUE","expected_xml":EXPECTED,"terminal_xml":0,"pending":EXPECTED,"no_nested_zip":True,"task_complete_claimed":False,"gold_claimed":False,"created_utc":STAMP,"files":[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sh(p)} for p in fs]};wt("MANIFEST.json",json.dumps(m,indent=2)+"\n");fs=sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name!="CHECKSUMS.sha256");wt("CHECKSUMS.sha256","".join(f"{sh(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in fs));print(json.dumps({"status":"CONTINUE","files":len(fs)+1,"tests":len(tests)},indent=2))
if __name__=="__main__":build()
