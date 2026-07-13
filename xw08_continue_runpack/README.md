# XW08 continuation runpack

This archive is **not** `FINAL_XW08.zip` and does not contain fabricated scientific output. It is the fail-closed execution handoff for the only remaining valid path: run the existing private XW08 implementation on the workstation that holds the ten source ZIPs.

## One command

From PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\RUN_XW08_LOCAL.ps1
```

The launcher searches standard project/data roots for exactly one content-identical copy of each `P001..P010` shard, resolves the private repository, checks out `v29x/xw08-properties-20260713`, creates an isolated Python 3.12 environment, runs the 78,683-document pipeline with checkpoint/resume, invokes the independent validator, and writes the final ZIP SHA-256.

Use explicit paths only when automatic discovery cannot find the existing assets:

```powershell
.\RUN_XW08_LOCAL.ps1 `
  -SourceDir 'E:\Generated\tiai_project_source_packs' `
  -RepoDir 'D:\codex_project\tiai-full-state-private' `
  -OutputRoot 'E:\Generated\XW08_EXECUTION' `
  -Workers 6
```

## Hard completion gate

The launcher prints `TASK_COMPLETE` only after the private pipeline independently verifies:

- ten source ZIP parts `P001..P010`, package SHA-256 and ZIP CRC;
- exact frozen XML count `78,683`;
- exact `78,683` unique anchors and matching non-PENDING terminal rows;
- all seven required Parquet outputs;
- atomic record/provenance UID equality;
- parser tests, manifest and checksums;
- final ZIP CRC/SHA and no nested ZIP.

Any earlier error is a failure/continuation state. Do not rename this runpack to `FINAL_XW08.zip`, do not promote placeholder rows, and do not claim Gold.
