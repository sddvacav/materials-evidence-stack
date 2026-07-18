from __future__ import annotations
from dataclasses import asdict,dataclass
from enum import Enum
from hashlib import sha256
import json,os,tempfile,time
from pathlib import Path
from typing import Protocol
class LeaseDecision(str,Enum):START_NEW='START_NEW';RESUME_OWNED='RESUME_OWNED';BLOCKED_ACTIVE_OTHER='BLOCKED_ACTIVE_OTHER';BLOCKED_UNVERIFIED_OWNER='BLOCKED_UNVERIFIED_OWNER';RECOVERED_STALE_LOCK='RECOVERED_STALE_LOCK'
@dataclass(frozen=True)
class ProcessIdentity:run_id:str;pid:int;create_time:float;command_sha256:str;config_sha256:str
class ProcessInspector(Protocol):
 def same_process(self,identity:ProcessIdentity)->bool|None:...
def write_atomic_json(path,payload):
 d=Path(path);d.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(payload,indent=2,sort_keys=True)+'\n').encode();fd,tmp=tempfile.mkstemp(prefix=f'.{d.name}.',suffix='.tmp',dir=d.parent)
 try:
  with os.fdopen(fd,'wb') as h:h.write(raw);h.flush();os.fsync(h.fileno())
  os.replace(tmp,d)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 return sha256(raw).hexdigest()
class LeaseGuard:
 def __init__(self,lock_path):self.lock_path=Path(lock_path)
 def _create(self,i):
  self.lock_path.parent.mkdir(parents=True,exist_ok=True);fd=os.open(self.lock_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as h:json.dump(asdict(i),h,sort_keys=True);h.write('\n');h.flush();os.fsync(h.fileno())
 def acquire(self,i,inspector):
  try:self._create(i);return LeaseDecision.START_NEW
  except FileExistsError:pass
  try:o=ProcessIdentity(**json.loads(self.lock_path.read_text()))
  except Exception:return LeaseDecision.BLOCKED_UNVERIFIED_OWNER
  live=inspector.same_process(o)
  if live is None:return LeaseDecision.BLOCKED_UNVERIFIED_OWNER
  if live:return LeaseDecision.RESUME_OWNED if o.run_id==i.run_id else LeaseDecision.BLOCKED_ACTIVE_OTHER
  archive=self.lock_path.with_name(f'{self.lock_path.name}.stale.{time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())}')
  try:os.replace(self.lock_path,archive);self._create(i)
  except OSError:return LeaseDecision.BLOCKED_UNVERIFIED_OWNER
  return LeaseDecision.RECOVERED_STALE_LOCK
@dataclass
class EtaEstimator:
 alpha:float=.25;previous_completed:int|None=None;previous_time:float|None=None;ewma_rate:float|None=None
 def update(self,completed,total,now):
  if total<=0 or completed<0 or completed>total:raise ValueError('invalid progress')
  if self.previous_completed is not None and self.previous_time is not None:
   dn=completed-self.previous_completed;dt=now-self.previous_time
   if dn>0 and dt>0:
    rate=dn/dt;self.ewma_rate=rate if self.ewma_rate is None else self.alpha*rate+(1-self.alpha)*self.ewma_rate
  self.previous_completed,self.previous_time=completed,now
  if completed>=total:return 0.
  if not self.ewma_rate or self.ewma_rate<=0:return None
  return (total-completed)/self.ewma_rate
@dataclass(frozen=True)
class Heartbeat:
 schema:str;run_id:str;pid:int;process_create_time:float;command_sha256:str;config_sha256:str;phase:str;completed:int;total:int;throughput_per_s:float|None;eta_seconds:float|None;checkpoint_path:str|None;checkpoint_sha256:str|None;last_progress_utc:str;ram_used_gb:float|None;gpu_used_gb:float|None;gpu_free_gb:float|None;last_error_category:str|None
 def validate(self):
  if self.schema!='tiai.g11.heartbeat.v1':raise ValueError('invalid heartbeat schema')
  if self.completed<0 or self.total<=0 or self.completed>self.total:raise ValueError('invalid heartbeat progress')
  if any(len(d)!=64 for d in (self.command_sha256,self.config_sha256)):raise ValueError('digest must be sha256')
 def write(self,path):self.validate();return write_atomic_json(path,asdict(self))
