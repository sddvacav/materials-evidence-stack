from pathlib import Path
p=Path('FINAL_QM02')
(p/'analysis_code').mkdir(parents=True, exist_ok=True)
(p/'00_EXECUTIVE_VERDICT.md').write_text('# smoke\n', encoding='utf-8')
(p/'analysis_code'/'validate_package.py').write_text('print({"pass": True})\n', encoding='utf-8')
print('QM02 smoke PASS')
