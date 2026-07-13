#!/usr/bin/env python3
from pathlib import Path

path = Path("tools/build_ssl04_return.py")
text = path.read_text(encoding="utf-8")
old = '''def fp(r): return hashlib.sha256(json.dumps({k:r.get(k) for k in FP},sort_keys=True,default=str).encode()).hexdigest()
def purge(rows,test):
    gs={group(r) for r in test}; fs={fp(r) for r in test}; keep=[]; removed=[]
    for r in rows:
        reason="IDENTITY_GROUP_OVERLAP" if group(r) in gs else ("NEAR_DUPLICATE_FINGERPRINT" if fp(r) in fs else "")
'''
new = '''def fp(r):
    payload={k:r.get(k) for k in FP}
    if not any(v not in (None,"") for v in payload.values()): return ""
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()
def purge(rows,test):
    gs={group(r) for r in test}; fs={x for r in test if (x:=fp(r))}; keep=[]; removed=[]
    for r in rows:
        x=fp(r)
        reason="IDENTITY_GROUP_OVERLAP" if group(r) in gs else ("NEAR_DUPLICATE_FINGERPRINT" if x and x in fs else "")
'''
if old not in text:
    raise SystemExit("expected leakage snippet not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched empty-fingerprint leakage guard")
