#!/usr/bin/env python3
"""Compile and execute the QM10 builder after applying a narrowly scoped template fix.

The fix escapes a set-comprehension inside the generated validator template. It is
asserted exactly once so any future source drift fails closed instead of silently
rewriting unrelated code.
"""
from pathlib import Path

path = Path(__file__).resolve().with_name("build.py")
source = path.read_text(encoding="utf-8")
old = 'if len({r["record_uid"] for r in rows})!=len(rows):errors.append("duplicate record_uid")'
new = 'if len({{r["record_uid"] for r in rows}})!=len(rows):errors.append("duplicate record_uid")'
count = source.count(old)
if count != 1:
    raise RuntimeError(f"Expected exactly one validator-template target; found {count}")
source = source.replace(old, new)
code = compile(source, str(path), "exec")
namespace = {"__name__": "__main__", "__file__": str(path)}
exec(code, namespace, namespace)
