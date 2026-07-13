#!/usr/bin/env python3
from pathlib import Path

path = Path("tools/build_ssl04_return.py")
text = path.read_text(encoding="utf-8")
replacements = [
    (
        'def fp(r): return hashlib.sha256(json.dumps({k:r.get(k) for k in FP},sort_keys=True,default=str).encode()).hexdigest()',
        'def fp(r):\n    payload={k:r.get(k) for k in FP}\n    if not any(v not in (None,"") for v in payload.values()): return ""\n    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()',
    ),
    (
        'gs={group(r) for r in test}; fs={fp(r) for r in test}; keep=[]; removed=[]',
        'gs={group(r) for r in test}; fs={x for r in test if (x:=fp(r))}; keep=[]; removed=[]',
    ),
    (
        'reason="IDENTITY_GROUP_OVERLAP" if group(r) in gs else ("NEAR_DUPLICATE_FINGERPRINT" if fp(r) in fs else "")',
        'x=fp(r)\n        reason="IDENTITY_GROUP_OVERLAP" if group(r) in gs else ("NEAR_DUPLICATE_FINGERPRINT" if x and x in fs else "")',
    ),
    ('"tests":"9/9"', '"tests":"11/11"'),
]
for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one occurrence, found {count}: {old[:80]}")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched empty-fingerprint leakage guard and test-count receipt")
