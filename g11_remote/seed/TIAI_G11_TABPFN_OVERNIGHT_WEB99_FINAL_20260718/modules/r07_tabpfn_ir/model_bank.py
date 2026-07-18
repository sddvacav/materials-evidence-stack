from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import numpy as np
from sklearn.base import RegressorMixin
from sklearn.ensemble import ExtraTreesRegressor,HistGradientBoostingRegressor,RandomForestRegressor
from sklearn.model_selection import GroupKFold,LeaveOneGroupOut
from .stacking import SimplexStacker,fit_simplex_stacker
Factory=Callable[[],RegressorMixin]
@dataclass(frozen=True)
class FoldReceipt:
 fold_id:int;train_groups:tuple[str,...];test_groups:tuple[str,...];train_n:int;test_n:int
@dataclass
class BankResult:
 names:tuple[str,...];models:dict[str,RegressorMixin];oof_predictions:np.ndarray;stacker:SimplexStacker;folds:tuple[FoldReceipt,...]
 def predict(self,x):return self.stacker.predict(np.column_stack([self.models[n].predict(x) for n in self.names]))
def default_factories(seed=7):return {'extra_trees':lambda:ExtraTreesRegressor(n_estimators=192,min_samples_leaf=2,max_features=.8,n_jobs=1,random_state=seed),'random_forest':lambda:RandomForestRegressor(n_estimators=160,min_samples_leaf=2,max_features=.8,n_jobs=1,random_state=seed+1),'hist_gradient_boosting':lambda:HistGradientBoostingRegressor(max_iter=160,learning_rate=.05,l2_regularization=1e-3,random_state=seed+2)}
def group_oof_predictions(factories,x,y,groups,*,max_splits=5):
 x=np.asarray(x,float);y=np.asarray(y,float).reshape(-1);groups=np.asarray(groups).astype(str).reshape(-1)
 if x.ndim!=2 or x.shape[0]!=y.size or y.size!=groups.size:raise ValueError('x/y/groups shape mismatch')
 unique=np.unique(groups)
 if unique.size<2:raise ValueError('at least two independent groups are required')
 splitter=LeaveOneGroupOut() if unique.size<=max_splits else GroupKFold(n_splits=max_splits);names=tuple(factories);oof=np.full((y.size,len(names)),np.nan);receipts=[]
 for fid,(tr,te) in enumerate(splitter.split(x,y,groups)):
  tg=tuple(sorted(set(groups[tr])));vg=tuple(sorted(set(groups[te])))
  if set(tg)&set(vg):raise AssertionError('group leakage detected')
  receipts.append(FoldReceipt(fid,tg,vg,len(tr),len(te)))
  for c,n in enumerate(names):
   m=factories[n]();m.fit(x[tr],y[tr]);pred=np.asarray(m.predict(x[te]),float).reshape(-1)
   if pred.size!=len(te) or not np.all(np.isfinite(pred)):raise RuntimeError(f'invalid prediction from {n}')
   oof[te,c]=pred
 if np.isnan(oof).any():raise RuntimeError('OOF matrix incomplete')
 return names,oof,tuple(receipts)
def train_bank(x,y,groups,*,factories=None,max_splits=5):
 factories=factories or default_factories();names,oof,folds=group_oof_predictions(factories,x,y,groups,max_splits=max_splits);stacker=fit_simplex_stacker(oof,y);models={}
 for n in names:m=factories[n]();m.fit(x,y);models[n]=m
 return BankResult(names,models,oof,stacker,folds)
