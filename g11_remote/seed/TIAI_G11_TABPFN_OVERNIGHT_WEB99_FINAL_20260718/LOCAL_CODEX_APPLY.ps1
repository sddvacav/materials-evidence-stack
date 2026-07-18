param([string]$Repo='E:\Generated\tiai-agent-os',[Parameter(Mandatory=$true)][string]$Bundle)
$ErrorActionPreference='Stop';Set-Location $Repo
foreach($t in @('modules/r07_tabpfn_ir','modules/r11_dual_caliber','DATA/g11')){if(Test-Path $t){throw "Existing path $t: overwrite forbidden"}}
Set-Location $Bundle;python -m pytest -q tests;if($LASTEXITCODE-ne0){throw 'tests failed'};python -m compileall -q modules
Set-Location $Repo;Copy-Item "$Bundle\modules\r07_tabpfn_ir" modules\r07_tabpfn_ir -Recurse;Copy-Item "$Bundle\modules\r11_dual_caliber" modules\r11_dual_caliber -Recurse;Copy-Item "$Bundle\DATA\g11" DATA\g11 -Recurse
