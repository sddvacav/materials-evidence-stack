from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json, os, subprocess, sys, zipfile

HERE=Path(__file__).resolve().parent
NAME='TIAI_G11_TABPFN_OVERNIGHT_WEB99_FINAL_20260718'
root=HERE/'seed'/NAME
outdir=HERE/'output'; outdir.mkdir(parents=True,exist_ok=True)
env=os.environ.copy(); env['PYTHONPATH']=str(root)
pytest_run=subprocess.run([sys.executable,'-m','pytest','-q','tests'],cwd=root,env=env,text=True,capture_output=True)
compile_run=subprocess.run([sys.executable,'-m','compileall','-q','modules'],cwd=root,env=env,text=True,capture_output=True)
(root/'EVIDENCE').mkdir(exist_ok=True)
(root/'EVIDENCE/pytest_stdout.txt').write_text(pytest_run.stdout+pytest_run.stderr,encoding='utf-8')
(root/'EVIDENCE/compileall_stdout.txt').write_text(compile_run.stdout+compile_run.stderr,encoding='utf-8')
passed=pytest_run.returncode==0 and compile_run.returncode==0
receipt={'schema':'tiai.g11.test-receipt.v1','runner':'github-actions/ubuntu-latest/python-'+sys.version.split()[0],'pytest_exit_code':pytest_run.returncode,'compileall_exit_code':compile_run.returncode,'passed':passed,'claim_effect':'implementation_verified_only' if passed else 'implementation_not_verified','scientific_metrics_verified':False}
(root/'EVIDENCE/test_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
manifest_path=root/'RETURN_MANIFEST.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8')); manifest['verification']=receipt; manifest['delivery_status']='COMPLETE_READY_FOR_LOCAL_APPLY' if passed else 'HONEST_PARTIAL'; manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(root/'WINDOW_STATUS.txt').write_text(manifest['delivery_status']+'\n',encoding='utf-8')
rows=[]
for p in sorted(root.rglob('*')):
    if p.is_file() and p.name!='SHA256SUMS.txt': rows.append(f'{sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}')
(root/'SHA256SUMS.txt').write_text('\n'.join(rows)+'\n',encoding='utf-8')
zip_path=outdir/(NAME+'.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(root.rglob('*')):
        if p.is_file(): z.write(p,p.relative_to(root.parent))
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert not [n for n in z.namelist() if n.lower().endswith('.zip')]
    entries=len(z.namelist())
digest=sha256(zip_path.read_bytes()).hexdigest()
(outdir/(zip_path.name+'.sha256')).write_text(f'{digest}  {zip_path.name}\n',encoding='utf-8')
delivery={'schema':'tiai.g11.delivery-receipt.v1','window_id':'G11','zip':zip_path.name,'zip_sha256':digest,'bytes':zip_path.stat().st_size,'entries':entries,'testzip':'PASS','nested_zip':False,'pytest_exit_code':pytest_run.returncode,'compileall_exit_code':compile_run.returncode,'implementation_tests_passed':passed,'scientific_claim_status':'HONEST_PARTIAL','claim_ceiling':'IMPLEMENTED_UNVALIDATED_CHALLENGER'}
(outdir/'G11_DELIVERY_RECEIPT.json').write_text(json.dumps(delivery,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(delivery,indent=2))
print(pytest_run.stdout); print(pytest_run.stderr,file=sys.stderr)
if not passed: raise SystemExit(1)
