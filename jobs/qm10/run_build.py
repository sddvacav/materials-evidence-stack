#!/usr/bin/env python3
"""Compile and execute the QM10 builder after applying a narrowly scoped template fix.

The fix escapes a set-comprehension inside the generated validator template. It is
asserted exactly once so any future source drift fails closed instead of silently
rewriting unrelated code. The launcher also injects the complete builder and launcher
into the final package before the manifest/checksum pass, making the delivery
self-contained and locally reproducible.
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

marker = "# Manifest and checksums. CHECKSUMS excludes itself; MANIFEST lists the pre-checksum payload."
injection = '''# Self-contained reproducibility sources, injected before manifest/checksum generation.
write_text("repro/build.py", Path(__file__).read_text(encoding="utf-8"))
write_text("repro/run_build.py", Path(__file__).with_name("run_build.py").read_text(encoding="utf-8"))
write_text("repro/README.md", """# Reproduce QM10\n\nFrom this directory run `python run_build.py`. The launcher applies one asserted template-escaping fix to `build.py`, executes the deterministic builder, recreates all tables/figures/tests, and emits a new `FINAL_QM10.zip` plus SHA-256. Exact dependencies are listed in the package root `requirements.lock`.\n""")

'''
if source.count(marker) != 1:
    raise RuntimeError("Manifest injection marker drifted")
source = source.replace(marker, injection + marker)

code = compile(source, str(path), "exec")
namespace = {"__name__": "__main__", "__file__": str(path)}
exec(code, namespace, namespace)
