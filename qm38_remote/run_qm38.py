#!/usr/bin/env python3
from pathlib import Path
p = Path(__file__).with_name('build_qm38.py')
src = p.read_text(encoding='utf-8')
src = src.replace("specs={'figures':[", "specs=dict(figures=[")
src = src.replace("],style='English labels; code-generated quantitative figures; no generative imagery or version labels'}", "],style='English labels; code-generated quantitative figures; no generative imagery or version labels')")
ns = {'__name__':'__main__','__file__':str(p)}
exec(compile(src, str(p), 'exec'), ns, ns)
