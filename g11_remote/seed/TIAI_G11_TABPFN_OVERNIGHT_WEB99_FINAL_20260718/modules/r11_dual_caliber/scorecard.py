from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math,numpy as np
class Caliber(str,Enum):GE5_TRAINING='GE5_TRAINING';HQ_LOSO_TEST='HQ_LOSO_TEST'
class GateStatus(str,Enum):PASS_CALIBER_GATE='PASS_CALIBER_GATE';BELOW_GATE_CONTINUE_OPTIMIZATION='below_gate_continue_optimization';MISSING_RECEIPT='MISSING_RECEIPT';INVALID_RECEIPT='INVALID_RECEIPT'
@dataclass(frozen=True)
class FoldEvidence:
 fold_id:str;train_groups:tuple[str,...];test_groups:tuple[str,...];y_true:tuple[float,...];y_pred:tuple[float,...];hq:bool;prediction_sha256:str;split_sha256:str
 def validate(self,caliber):
  if not self.train_groups or not self.test_groups or set(self.train_groups)&set(self.test_groups):raise ValueError('train/test groups overlap or are empty')
  if not self.y_true or len(self.y_true)!=len(self.y_pred):raise ValueError('prediction length mismatch')
  if not all(math.isfinite(v) for v in (*self.y_true,*self.y_pred)):raise ValueError('non-finite prediction evidence')
  if len(self.prediction_sha256)!=64 or len(self.split_sha256)!=64:raise ValueError('receipt hashes must be sha256')
  if caliber is Caliber.HQ_LOSO_TEST and not self.hq:raise ValueError('LOSO receipt is not HQ')
@dataclass(frozen=True)
class GateResult:
 caliber:Caliber;status:GateStatus;r2:float|None;mae:float|None;rmse:float|None;n:int;fold_count:int;threshold:float;claim_ceiling:str;reasons:tuple[str,...]
def evaluate_caliber(caliber,folds,threshold=.9):
 if not folds:return GateResult(caliber,GateStatus.MISSING_RECEIPT,None,None,None,0,0,threshold,'NO_SCIENTIFIC_CLAIM',('fold_receipts_missing',))
 try:
  for f in folds:f.validate(caliber)
 except ValueError as e:return GateResult(caliber,GateStatus.INVALID_RECEIPT,None,None,None,0,len(folds),threshold,'NO_SCIENTIFIC_CLAIM',(str(e),))
 y=np.concatenate([np.asarray(f.y_true,float) for f in folds]);p=np.concatenate([np.asarray(f.y_pred,float) for f in folds]);r=y-p;den=float(np.sum((y-y.mean())**2));r2=float('nan') if den<=0 else 1-float(np.sum(r**2))/den;mae=float(np.mean(np.abs(r)));rmse=float(np.sqrt(np.mean(r**2)));passed=math.isfinite(r2) and r2>=threshold
 return GateResult(caliber,GateStatus.PASS_CALIBER_GATE if passed else GateStatus.BELOW_GATE_CONTINUE_OPTIMIZATION,r2,mae,rmse,y.size,len(folds),threshold,'CALIBER_LOCAL_CANDIDATE' if passed else 'DIAGNOSTIC_ONLY',())
def promotion_decision(training,loso):
 if training.caliber is not Caliber.GE5_TRAINING or loso.caliber is not Caliber.HQ_LOSO_TEST:return {'fullscore_allowed':False,'production_champion_allowed':False,'reason':'caliber_mismatch'}
 if loso.status is not GateStatus.PASS_CALIBER_GATE:return {'fullscore_allowed':False,'production_champion_allowed':False,'reason':'hq_loso_gate_not_passed'}
 if training.status is not GateStatus.PASS_CALIBER_GATE:return {'fullscore_allowed':False,'production_champion_allowed':False,'reason':'training_gate_not_passed'}
 return {'fullscore_allowed':False,'production_champion_allowed':False,'reason':'metrics_only_insufficient_requires_uq_ad_ood_nearest_and_current_sha_receipts'}
