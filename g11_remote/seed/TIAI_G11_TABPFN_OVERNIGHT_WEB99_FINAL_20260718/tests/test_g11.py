from hashlib import sha256
import json
from pathlib import Path
import numpy as np,yaml
from sklearn.linear_model import LinearRegression,Ridge
from modules.r07_tabpfn_ir.contracts import *
from modules.r07_tabpfn_ir.model_bank import group_oof_predictions
from modules.r07_tabpfn_ir.stacking import fit_simplex_stacker,project_simplex
from modules.r11_dual_caliber.runtime import *
from modules.r11_dual_caliber.scorecard import *
from modules.r11_dual_caliber.lever_ladder import *
from modules.r11_dual_caliber.continuation import render_continuation_brief
ROOT=Path(__file__).resolve().parents[1]
class Inspector:
 def __init__(self,r):self.r=r
 def same_process(self,i):return self.r
def test_admission(tmp_path):
 p=tmp_path/'v2';p.write_bytes(b'x');r=TabPFNRequest('V2',str(p),sha256(p.read_bytes()).hexdigest(),'reviewed',10,2,'cuda',RuntimeResources(20,True,10));assert admit_tabpfn(r).admitted;assert admit_tabpfn(TabPFNRequest(**{**r.__dict__,'active_training':True})).status is AdmissionStatus.BLOCKED_ACTIVE_TRAINING
def test_runtime(tmp_path):
 new=ProcessIdentity('new',1,1.,'a'*64,'b'*64);old=ProcessIdentity('old',2,2.,'c'*64,'d'*64);lock=tmp_path/'l';lock.write_text(json.dumps(old.__dict__));g=LeaseGuard(lock);assert g.acquire(new,Inspector(True)) is LeaseDecision.BLOCKED_ACTIVE_OTHER;assert g.acquire(new,Inspector(None)) is LeaseDecision.BLOCKED_UNVERIFIED_OWNER;assert g.acquire(new,Inspector(False)) is LeaseDecision.RECOVERED_STALE_LOCK;e=EtaEstimator();assert e.update(0,100,0) is None;assert e.update(10,100,5)==45
def test_stack_oof():
 q=project_simplex(np.array([-2.,.4,2.]));assert np.all(q>=0) and np.isclose(q.sum(),1);rng=np.random.default_rng(7);p=rng.normal(size=(200,3));y=1.5+p@np.array([.7,.3,0]);s=fit_simplex_stacker(p,y);assert np.mean((s.predict(p)-y)**2)<1e-8;groups=np.repeat(['A','B','C','D'],10);x=rng.normal(size=(40,3));yt=2*x[:,0]-x[:,1];names,oof,receipts=group_oof_predictions({'lr':lambda:LinearRegression(),'ridge':lambda:Ridge(.1)},x,yt,groups,max_splits=4);assert oof.shape==(40,2) and np.isfinite(oof).all();assert all(not(set(r.train_groups)&set(r.test_groups)) for r in receipts)
def ev(overlap=False,hq=True):return FoldEvidence('f',('A',),('A' if overlap else 'B',),(1.,2.,3.),(1.,2.,3.),hq,'a'*64,'b'*64)
def test_score_data_scope():
 assert evaluate_caliber(Caliber.HQ_LOSO_TEST,[]).status is GateStatus.MISSING_RECEIPT;assert evaluate_caliber(Caliber.HQ_LOSO_TEST,[ev(True)]).status is GateStatus.INVALID_RECEIPT;tr=evaluate_caliber(Caliber.GE5_TRAINING,[ev()]);lo=evaluate_caliber(Caliber.HQ_LOSO_TEST,[ev()]);assert tr.status is GateStatus.PASS_CALIBER_GATE;assert not promotion_decision(tr,lo)['fullscore_allowed'];c=yaml.safe_load((ROOT/'DATA/g11/overnight_train_contract.yaml').read_text());assert c['process_policy']['kill_process'] is False;levers=json.loads((ROOT/'DATA/g11/lever_ladder.json').read_text());validate_ladder(levers);assert next_lever(levers,[])['stage']=='data';m=json.loads((ROOT/'RETURN_MANIFEST.json').read_text());assert m['write_scope']==['modules/r07_tabpfn_ir/**','modules/r11_dual_caliber/**','DATA/g11/**'];brief=render_continuation_brief({'run_id':'r','pid':1});assert 'UNKNOWN' in brief and 'do_not_stop_process' in brief
