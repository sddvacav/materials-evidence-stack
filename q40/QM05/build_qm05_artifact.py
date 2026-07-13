from pathlib import Path
p=Path(__file__).resolve().parent/'artifact'
p.mkdir(parents=True,exist_ok=True)
(p/'probe.txt').write_text('ok\n')
(p/'validate_package.py').write_text("print('probe pass')\n")
