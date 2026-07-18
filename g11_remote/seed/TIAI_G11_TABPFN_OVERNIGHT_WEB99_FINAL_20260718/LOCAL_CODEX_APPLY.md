# Local Codex apply — 0.01%

Target `E:\Generated\tiai-agent-os`. Verify ZIP/member hashes; run package pytest+compileall; fail on existing `modules/r07_tabpfn_ir`, `modules/r11_dual_caliber`, `DATA/g11`; inspect `Get-CimInstance Win32_Process` plus `nvidia-smi` read-only; never Stop-Process; copy exactly the three paths; rerun tests and `git diff --check`; rollback only newly copied paths.

```powershell
$Repo='E:\Generated\tiai-agent-os';$Bundle='E:\Generated\titmc_return_intake\TIAI_G11_TABPFN_OVERNIGHT_WEB99_FINAL_20260718';Set-Location $Repo;git status --porcelain;git rev-parse HEAD
foreach($t in @('modules/r07_tabpfn_ir','modules/r11_dual_caliber','DATA/g11')){if(Test-Path $t){throw "Existing path $t; diff/adapt"}}
Get-CimInstance Win32_Process|?{$_.CommandLine -match 'loso|train|tabpfn|tiai'}|select ProcessId,ParentProcessId,CreationDate,ExecutablePath,CommandLine|fl
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
Set-Location $Bundle;python -m pytest -q tests;python -m compileall -q modules
Set-Location $Repo;Copy-Item "$Bundle\modules\r07_tabpfn_ir" modules\r07_tabpfn_ir -Recurse;Copy-Item "$Bundle\modules\r11_dual_caliber" modules\r11_dual_caliber -Recurse;Copy-Item "$Bundle\DATA\g11" DATA\g11 -Recurse;git diff --check
```
