from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
class AdmissionStatus(str,Enum):
 ADMITTED='ADMITTED'; BLOCKED_ACTIVE_TRAINING='BLOCKED_ACTIVE_TRAINING'; BLOCKED_LICENSE='BLOCKED_LICENSE'; BLOCKED_CHECKPOINT='BLOCKED_CHECKPOINT'; BLOCKED_RESOURCES='BLOCKED_RESOURCES'; BLOCKED_DATASET_LIMIT='BLOCKED_DATASET_LIMIT'; BLOCKED_VERSION='BLOCKED_VERSION'
@dataclass(frozen=True)
class RuntimeResources:
 ram_available_gb:float; gpu_available:bool; gpu_free_gb:float|None=None
@dataclass(frozen=True)
class TabPFNRequest:
 model_version:str; checkpoint_path:str; checkpoint_sha256:str; license_receipt:str|None; n_rows:int; n_features:int; device:str; resources:RuntimeResources; active_training:bool=False; max_rows:int=10000; max_features:int=500; min_ram_gb:float=12.0; min_gpu_free_gb:float=6.0
@dataclass(frozen=True)
class AdmissionDecision:
 status:AdmissionStatus; admitted:bool; reasons:tuple[str,...]; resolved_checkpoint:str|None=None
def _sha(p:Path)->str:
 h=sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def admit_tabpfn(r:TabPFNRequest)->AdmissionDecision:
 if r.active_training:return AdmissionDecision(AdmissionStatus.BLOCKED_ACTIVE_TRAINING,False,('live_training_lease_present',))
 if r.model_version!='V2':return AdmissionDecision(AdmissionStatus.BLOCKED_VERSION,False,('model_version_must_be_explicit_V2',))
 if not r.license_receipt or not r.license_receipt.strip():return AdmissionDecision(AdmissionStatus.BLOCKED_LICENSE,False,('license_receipt_missing',))
 p=Path(r.checkpoint_path).expanduser().resolve()
 if not p.is_file():return AdmissionDecision(AdmissionStatus.BLOCKED_CHECKPOINT,False,('checkpoint_missing',))
 if len(r.checkpoint_sha256)!=64 or _sha(p)!=r.checkpoint_sha256.lower():return AdmissionDecision(AdmissionStatus.BLOCKED_CHECKPOINT,False,('checkpoint_sha256_mismatch',))
 if r.n_rows<=0 or r.n_features<=0 or r.n_rows>r.max_rows or r.n_features>r.max_features:return AdmissionDecision(AdmissionStatus.BLOCKED_DATASET_LIMIT,False,('dataset_outside_admitted_shape',))
 reasons=[]
 if r.resources.ram_available_gb<r.min_ram_gb:reasons.append('insufficient_ram')
 if r.device.startswith('cuda'):
  if not r.resources.gpu_available:reasons.append('gpu_unavailable')
  elif r.resources.gpu_free_gb is None:reasons.append('gpu_free_memory_unknown')
  elif r.resources.gpu_free_gb<r.min_gpu_free_gb:reasons.append('insufficient_gpu_memory')
 if reasons:return AdmissionDecision(AdmissionStatus.BLOCKED_RESOURCES,False,tuple(reasons))
 return AdmissionDecision(AdmissionStatus.ADMITTED,True,(),str(p))
