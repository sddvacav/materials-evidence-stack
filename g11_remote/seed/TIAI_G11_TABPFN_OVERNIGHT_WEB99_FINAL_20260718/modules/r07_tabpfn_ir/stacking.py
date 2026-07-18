from __future__ import annotations
from dataclasses import dataclass
import numpy as np
def project_simplex(vector:np.ndarray)->np.ndarray:
 v=np.asarray(vector,dtype=float).reshape(-1)
 if v.size==0 or not np.all(np.isfinite(v)):raise ValueError('vector must be finite and non-empty')
 u=np.sort(v)[::-1];cssv=np.cumsum(u)-1.;idx=np.arange(1,v.size+1);positive=u-cssv/idx>0
 if not np.any(positive):return np.full(v.size,1./v.size)
 rho=np.nonzero(positive)[0][-1];theta=cssv[rho]/float(rho+1);w=np.maximum(v-theta,0.)
 return w/w.sum()
@dataclass(frozen=True)
class SimplexStacker:
 weights:np.ndarray;intercept:float;objective:float;iterations:int
 def predict(self,predictions:np.ndarray)->np.ndarray:
  p=np.asarray(predictions,dtype=float)
  if p.ndim!=2 or p.shape[1]!=self.weights.size:raise ValueError('prediction matrix shape mismatch')
  return self.intercept+p@self.weights
def fit_simplex_stacker(predictions:np.ndarray,target:np.ndarray,*,ridge:float=1e-8,max_iter:int=10000,tolerance:float=1e-10)->SimplexStacker:
 p=np.asarray(predictions,dtype=float);y=np.asarray(target,dtype=float).reshape(-1)
 if p.ndim!=2 or p.shape[0]!=y.size or p.shape[1]==0:raise ValueError('predictions must be n x m and align with target')
 if not np.all(np.isfinite(p)) or not np.all(np.isfinite(y)):raise ValueError('non-finite stacking input')
 pc=p-p.mean(0);yc=y-y.mean();L=2.*float(np.linalg.norm(pc,ord=2)**2)/max(1,y.size)+2.*ridge;step=1./max(L,1e-12);w=np.full(p.shape[1],1./p.shape[1]);used=0
 for used in range(1,max_iter+1):
  grad=(2./y.size)*(pc.T@(pc@w-yc))+2.*ridge*w;c=project_simplex(w-step*grad)
  if np.linalg.norm(c-w)<=tolerance:w=c;break
  w=c
 b=float(y.mean()-p.mean(0)@w);res=y-(b+p@w)
 return SimplexStacker(w,b,float(np.mean(res**2)+ridge*np.dot(w,w)),used)
