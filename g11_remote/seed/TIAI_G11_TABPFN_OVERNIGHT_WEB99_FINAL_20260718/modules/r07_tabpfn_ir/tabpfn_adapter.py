from __future__ import annotations
import inspect,os
from typing import Any
from .contracts import TabPFNRequest,admit_tabpfn
class TabPFNUnavailable(RuntimeError):pass
def build_tabpfn_v2_regressor(request:TabPFNRequest,**overrides:Any)->Any:
 d=admit_tabpfn(request)
 if not d.admitted:raise TabPFNUnavailable(f'TabPFN blocked: {d.status.value}: {d.reasons}')
 os.environ.setdefault('TABPFN_DISABLE_TELEMETRY','1')
 try:from tabpfn import TabPFNRegressor
 except Exception as e:raise TabPFNUnavailable('tabpfn optional dependency is not installed') from e
 sig=inspect.signature(TabPFNRegressor); kw=dict(overrides)
 for k,v in {'model_path':d.resolved_checkpoint,'device':request.device,'ignore_pretraining_limits':False}.items():
  if k in sig.parameters and k not in kw:kw[k]=v
 if 'model_path' not in sig.parameters:raise TabPFNUnavailable('installed TabPFN API cannot bind an exact local checkpoint')
 return TabPFNRegressor(**kw)
