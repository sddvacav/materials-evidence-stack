from pathlib import Path
p = Path(__file__).resolve().parent / "output" / "FINAL_QM36" / "tests" / "test_qm36_outputs.py"
s = p.read_text(encoding="utf-8")
if "\\n" in s and "\n" not in s.strip():
    p.write_text(s.replace("\\n", "\n"), encoding="utf-8", newline="\n")
else:
    p.write_text(s.replace("\\n", "\n"), encoding="utf-8", newline="\n")
