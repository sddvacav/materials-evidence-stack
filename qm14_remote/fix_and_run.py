#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path

root = Path(__file__).resolve().parent
source = root / "build_qm14.py"
fixed = root / "build_qm14_fixed.py"
text = source.read_text(encoding="utf-8")

replacements = {
    "curve_df.steady_creep_rate_s-1.apply(finite)": "curve_df['steady_creep_rate_s-1'].apply(finite)",
    "c.steady_creep_rate_s-1": "c['steady_creep_rate_s-1']",
    "t.steady_creep_rate_s-1": "t['steady_creep_rate_s-1']",
    "condition = f\"{paper_uid}|{sample}|{heat_treatment}|{temp:g}C|{stress:g}MPa|tension\"": "condition = f\"{paper_uid}|{heat_treatment}|{temp:g}C|{stress:g}MPa|tension\"\n    record_key = f\"{condition}|{sample}\"",
    '"record_uid": "CR_" + sid(condition),': '"record_uid": "CR_" + sid(record_key),',
}

for old, new in replacements.items():
    if old not in text:
        raise RuntimeError(f"expected build-source token not found: {old}")
    text = text.replace(old, new)

compile(text, str(fixed), "exec")
fixed.write_text(text, encoding="utf-8")
runpy.run_path(str(fixed), run_name="__main__")
