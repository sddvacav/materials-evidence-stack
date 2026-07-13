[CmdletBinding()]
param(
    [string]$SourceDir = "",
    [string]$RepoDir = "",
    [string]$OutputRoot = "",
    [ValidateRange(1,16)][int]$Workers = 6,
    [switch]$Fresh
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Batch = 'V29X_C10_XML_CROSS_EXTRACTION_20260713'
$Window = 'XW08'
$ExpectedXml = 78683
$Repo = 'sddvacav/tiai-full-state-private'
$Branch = 'v29x/xw08-properties-20260713'

function Write-Stage([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
}

function Resolve-SourcePackages {
    param([string]$ExplicitDir)
    $roots = [System.Collections.Generic.List[string]]::new()
    if ($ExplicitDir) { $roots.Add((Resolve-Path -LiteralPath $ExplicitDir).Path) }
    foreach ($candidate in @(
        'E:\Generated',
        'E:\Generated\tiai_project_source_packs',
        'D:\Research',
        'D:\codex_project',
        "$env:USERPROFILE\Downloads",
        "$env:USERPROFILE\Desktop"
    )) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { $roots.Add($candidate) }
    }
    $roots = $roots | Select-Object -Unique
    if (-not $roots) { throw 'No searchable source root exists. Supply -SourceDir.' }

    $all = foreach ($root in $roots) {
        Get-ChildItem -LiteralPath $root -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^TITMC_V27_LIT_WEB_P(00[1-9]|010)_OF_010(?:\(\d+\))?\.zip$' }
    }
    if (-not $all) { throw 'No TITMC_V27_LIT_WEB P001..P010 source ZIPs found.' }

    $selected = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
    foreach ($part in 1..10) {
        $token = ('P{0:D3}_OF_010' -f $part)
        $matches = @($all | Where-Object { $_.Name -match [regex]::Escape($token) })
        if ($matches.Count -eq 0) { throw "Missing source package $token" }
        $hashGroups = $matches | ForEach-Object {
            [pscustomobject]@{ File = $_; Sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
        } | Group-Object Sha256
        if ($hashGroups.Count -ne 1) {
            $detail = $matches.FullName -join '; '
            throw "Ambiguous non-identical copies for ${token}: $detail"
        }
        $choice = $hashGroups[0].Group | Sort-Object { $_.File.Name.Length }, { $_.File.LastWriteTimeUtc } -Descending | Select-Object -First 1
        $selected.Add($choice.File)
    }
    return @($selected | Sort-Object Name)
}

function Resolve-PrivateRepo {
    param([string]$ExplicitRepo)
    if ($ExplicitRepo) {
        $resolved = (Resolve-Path -LiteralPath $ExplicitRepo).Path
        if (-not (Test-Path -LiteralPath (Join-Path $resolved '.git'))) { throw "Not a Git repository: $resolved" }
        return $resolved
    }
    foreach ($candidate in @(
        'D:\codex_project\tiai-full-state-private',
        'D:\Research\tiai-full-state-private',
        'E:\Generated\tiai-full-state-private',
        (Join-Path $PWD 'tiai-full-state-private')
    )) {
        if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate '.git'))) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Private repo absent and GitHub CLI (gh) is unavailable.' }
    $target = Join-Path $PWD 'tiai-full-state-private'
    Write-Stage "Cloning private repository $Repo"
    gh repo clone $Repo $target -- --filter=blob:none --no-checkout
    if ($LASTEXITCODE -ne 0) { throw 'gh repo clone failed. Authenticate with gh auth login.' }
    return (Resolve-Path -LiteralPath $target).Path
}

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory)
    Write-Stage ("EXEC: {0} {1}" -f $FilePath, ($Arguments -join ' '))
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code ${LASTEXITCODE}: $FilePath" }
    } finally { Pop-Location }
}

$packages = Resolve-SourcePackages -ExplicitDir $SourceDir
Write-Stage ("Resolved ten source packages: {0}" -f (($packages | ForEach-Object Name) -join ', '))

$repoPath = Resolve-PrivateRepo -ExplicitRepo $RepoDir
Invoke-Checked -FilePath 'git' -Arguments @('fetch','origin',$Branch,'--depth=1','--filter=blob:none') -WorkingDirectory $repoPath
Invoke-Checked -FilePath 'git' -Arguments @('checkout','--force','FETCH_HEAD') -WorkingDirectory $repoPath

$xw08Root = Join-Path $repoPath 'v29x\windows\XW08'
$runner = Join-Path $xw08Root 'PARSER_CODE\run_xw08.py'
if (-not (Test-Path -LiteralPath $runner)) { throw "Missing XW08 runner: $runner" }

if (-not $OutputRoot) { $OutputRoot = Join-Path (Split-Path $repoPath -Parent) 'XW08_EXECUTION' }
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$outputDir = Join-Path $OutputRoot 'FINAL_XW08'
$finalZip = Join-Path $OutputRoot 'FINAL_XW08.zip'
$venv = Join-Path $OutputRoot '.venv_xw08'

if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
    Write-Stage 'Creating isolated Python virtual environment'
    py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { python -m venv $venv }
}
$python = Join-Path $venv 'Scripts\python.exe'
Invoke-Checked -FilePath $python -Arguments @('-m','pip','install','--upgrade','pip') -WorkingDirectory $xw08Root
Invoke-Checked -FilePath $python -Arguments @('-m','pip','install','-r',(Join-Path $xw08Root 'PARSER_CODE\requirements.txt')) -WorkingDirectory $xw08Root

$args = [System.Collections.Generic.List[string]]::new()
$args.Add($runner)
foreach ($package in $packages) { $args.Add('--zip'); $args.Add($package.FullName) }
$args.Add('--output'); $args.Add($outputDir)
$args.Add('--final-zip'); $args.Add($finalZip)
$args.Add('--workers'); $args.Add([string]$Workers)
$args.Add('--expected-xml'); $args.Add([string]$ExpectedXml)
$args.Add('--resume')
if ($Fresh) { $args.Add('--fresh') }

Invoke-Checked -FilePath $python -Arguments $args.ToArray() -WorkingDirectory $xw08Root
$validator = Join-Path $outputDir 'PARSER_CODE\validate_delivery.py'
Invoke-Checked -FilePath $python -Arguments @($validator,'--delivery',$outputDir,'--expected-xml',[string]$ExpectedXml,'--zip',$finalZip) -WorkingDirectory $outputDir

if (-not (Test-Path -LiteralPath $finalZip)) { throw 'FINAL_XW08.zip was not produced.' }
$zipHash = (Get-FileHash -LiteralPath $finalZip -Algorithm SHA256).Hash.ToLowerInvariant()
$receipt = [ordered]@{
    batch = $Batch
    window = $Window
    status = 'TASK_COMPLETE'
    xml_terminal = $ExpectedXml
    pending = 0
    final_zip = $finalZip
    final_zip_bytes = (Get-Item -LiteralPath $finalZip).Length
    final_zip_sha256 = $zipHash
    completed_utc = [DateTime]::UtcNow.ToString('o')
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputRoot 'XW08_LOCAL_EXECUTION_RECEIPT.json') -Encoding utf8
Write-Host "STATUS: TASK_COMPLETE | WINDOW=XW08 | XML_TERMINAL=78683/78683 | PENDING=0"
Write-Host "FINAL_XW08.zip SHA-256: $zipHash"
