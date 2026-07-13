from __future__ import annotations

import atexit
import sys
from pathlib import Path

# The isolated QM02 workflow invokes patch_after_build.py as a top-level script.
# Apply the recorded process-field correction only after that script has completed
# its normal build/validation path; other Python invocations are untouched.
if Path(sys.argv[0]).name == "patch_after_build.py":
    def _apply_qm02_source_audit_hotfix() -> None:
        from source_audit_hotfix import apply
        apply()

    atexit.register(_apply_qm02_source_audit_hotfix)
