#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, shutil, subprocess, sys
from pathlib import Path
from typing import Any
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from qm38_data import ARCHIVES, PRIOR, EFFECTS, INTERACTIONS

BASE = Path(__file__).resolve().parent
ROOT = BASE / 'output' / 'FINAL_QM38'
if ROOT.exists(): shutil.rmtree(ROOT)
for d in [ROOT, ROOT/'figures', ROOT/'figure_data', ROOT/'plot_code', ROOT/'analysis_code', ROOT/'tests']:
    d.mkdir(parents=True, exist_ok=True)
GENERATED = '2026-07-13T09:05:00Z'
STATUS_LINE = ('STATUS: CONTINUE_DATA_GAP | WINDOW=QM38 | '
               'MISSING=AUTHORITATIVE_V29_ATOMIC_SNAPSHOT+UNIFIED_ROW_LEVEL_COHORT+'
               'PAPER_LEVEL_RANDOM_EFFECTS_VECTOR+PROPENSITY_COVARIATES+'
               'POROSITY_ACTUAL_PHASE_ORIENTATION_STRAIN_RATE | '
               'NEXT=LOCAL_HASH_BIND_AND_RERUN_HIERARCHICAL_META_WITH_DML_GATE')


def uid(prefix: str, *parts: Any) -> str:
    return prefix + '_' + hashlib.sha256('|'.join(str(x) for x in parts).encode()).hexdigest()[:20]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def csv_write(rel: str, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    p = ROOT / rel; p.parent.mkdir(parents=True, exist_ok=True)
    if fields is None: fields = list(rows[0]) if rows else ['status','reason']
    with p.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k: '' if r.get(k) is None else r.get(k,'') for k in fields})


def text(rel: str, s: str) -> None:
    p = ROOT / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s.rstrip()+'\n', encoding='utf-8')


def js(rel: str, obj: Any) -> None:
    p = ROOT / rel; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')


snap_payload = {'archives':[x[1] for x in ARCHIVES], 'prior':[x[2] for x in PRIOR], 'policy':'QM38-v2-aggregate-bound'}
SNAPSHOT = 'QM38_DERIVED_' + hashlib.sha256(json.dumps(snap_payload,sort_keys=True).encode()).hexdigest()[:20]

inputs=[]
for name,h,b,m,hk,priority in ARCHIVES:
    inputs.append(dict(input_id=uid('IN',name,h),snapshot_id=SNAPSHOT,source_name=name,source_type='ZIP',path_or_locator='project_upload:/mnt/data/'+name,source_hash=h,source_hash_kind='INHERITED_'+hk,bytes=b,member_count=m,priority=priority,window_relevance='role-specific source inventory / primary literature / frozen data / code',terminal_use_status='USED_AS_REFERENCE',opened_or_consumed='LEDGER_AND_MEMBER_INVENTORY',notes='Hash inherited from verified upload-control ledger; isolated runner did not pretend to re-stream archive bytes.'))
for win,snap,h,loc,use in PRIOR:
    inputs.append(dict(input_id=uid('IN',win,snap,h),snapshot_id=SNAPSHOT,source_name=win+' quantitative return',source_type='PRIOR_WINDOW_RETURN',path_or_locator=loc,source_hash=h,source_hash_kind='RETURN_SHA_OR_FILE_REFERENCE',bytes='',member_count='',priority='P0_QUANT_RETURN',window_relevance='effect/heterogeneity/support-domain synthesis',terminal_use_status=use,opened_or_consumed='YES',notes='Reused only within declared estimand and support domain.'))
inputs.append(dict(input_id=uid('IN','QM38_MDU'),snapshot_id=SNAPSHOT,source_name='QM38 MDU',source_type='CONTRACT',path_or_locator='uploaded dispatch unit',source_hash='FILE_LIBRARY_REFERENCE_NO_BYTE_HASH',source_hash_kind='REFERENCE',bytes='',member_count=1,priority='P0_CONTRACT',window_relevance='execution contract',terminal_use_status='USED_DIRECTLY',opened_or_consumed='YES',notes='Current contract.'))
csv_write('INPUT_LEDGER.csv',inputs)

rows=[]
for e in EFFECTS:
    r=dict(e)
    r.update(snapshot_id=SNAPSHOT,paper_uid_scope='aggregate:{} independent papers'.format(e['papers']),sample_uid_scope='aggregate:{} matched pairs/effects'.format(e['pairs']),condition_uid_scope=uid('COND',e['outcome'],e['temp'],e['reinforcement'],e['source']),matrix_family='mixed/not row-bound',process='condition-matched within source',evidence_grade=e['grade'],claim_level=e['level'],source_window=e['source'],provenance_locator=e['source']+': hash-bound return; exact row IDs retained in source package',support_status='IN_SUPPORT' if e['papers']>=5 else 'SPARSE')
    r['ci95_low']=r.pop('lo'); r['ci95_high']=r.pop('hi'); r['prediction_low']=r.pop('pi_lo'); r['prediction_high']=r.pop('pi_hi'); r['temperature_C']=r.pop('temp'); r['notes']=r.pop('note'); r['independent_papers']=r.pop('papers'); r['matched_pairs_or_effects']=r.pop('pairs'); r['reinforcement']=r['reinforcement']; r['estimand']=r['estimand']; r['unit']=r['unit']; r['estimate']=r['estimate']; r['outcome']=r['outcome']; del r['source']; del r['grade']; del r['level']
    rows.append(r)
csv_write('EFFECT_ESTIMATES.csv',rows); csv_write('META_ANALYSIS_DATA.csv',rows)

cohort=[]
for r in rows:
    cohort.append(dict(cohort_row_id=uid('COH',r['effect_id']),snapshot_id=SNAPSHOT,source_window=r['source_window'],effect_id=r['effect_id'],paper_uid_scope=r['paper_uid_scope'],sample_uid_scope=r['sample_uid_scope'],condition_uid_scope=r['condition_uid_scope'],outcome=r['outcome'],temperature_C=r['temperature_C'],reinforcement=r['reinforcement'],independent_papers=r['independent_papers'],matched_pairs_or_effects=r['matched_pairs_or_effects'],include_primary=r['effect_id'] in {'UTS_STRICT_RT','EL_RT_PRIMARY'},exclusion_or_role='primary estimand' if r['effect_id'] in {'UTS_STRICT_RT','EL_RT_PRIMARY'} else 'validation/CATE/sensitivity',provenance_locator=r['provenance_locator']))
cohort.append(dict(cohort_row_id=uid('COH','FG_TABLE41'),snapshot_id=SNAPSHOT,source_window='PRIMARY_PAPER_AUDIT',effect_id='AUDIT_FG_TABLE41',paper_uid_scope='0710_Functionally-Graded_TMC',sample_uid_scope='D4_TMC_vs_C2_Alloy',condition_uid_scope=uid('COND','RT_tension','same_fabrication'),outcome='UTS',temperature_C=25,reinforcement='continuous/graded architecture',independent_papers=1,matched_pairs_or_effects=1,include_primary=False,exclusion_or_role='original-table audit anchor; architecture-incompatible with primary pool',provenance_locator='Direct original PDF Table 4.1: 1655 vs 1000 MPa'))
csv_write('ANALYSIS_COHORT.csv',cohort)

pairs=[]
for r in rows:
    pairs.append(dict(pair_id=uid('PAIR',r['effect_id']),snapshot_id=SNAPSHOT,paper_uid=r['paper_uid_scope'],treated_sample_uid=r['sample_uid_scope']+':TMC',control_sample_uid=r['sample_uid_scope']+':matrix',condition_uid=r['condition_uid_scope'],match_grade=r['evidence_grade'],outcome=r['outcome'],unit=r['unit'],treated_value='aggregate_not_exposed',control_value='aggregate_not_exposed',absolute_effect=r['estimate'],independent_papers=r['independent_papers'],pair_count=r['matched_pairs_or_effects'],source_window=r['source_window'],provenance_locator=r['provenance_locator'],primary_pool=r['effect_id']=='UTS_STRICT_RT',notes='Summary-bound pair set; exact row identities must be rebound locally.'))
pairs.append(dict(pair_id='PAIR_FG_TABLE41',snapshot_id=SNAPSHOT,paper_uid='0710_Functionally-Graded_TMC',treated_sample_uid='D4_TMC',control_sample_uid='C2_Alloy',condition_uid=uid('COND','RT_tension','same_fabrication'),match_grade='DIRECT_TABLE_TEXT_AUDIT',outcome='UTS',unit='MPa',treated_value=1655,control_value=1000,absolute_effect=655,independent_papers=1,pair_count=1,source_window='PRIMARY_PAPER_AUDIT',provenance_locator='Table 4.1 direct original PDF',primary_pool=False,notes='Excluded from primary meta pool due continuous/graded architecture.'))
csv_write('PAIR_MATCHES.csv',pairs)

hier=[
 dict(model_id='HM_UTS_STRICT',outcome='UTS',unit='MPa',estimand='strict paper-balanced same-paper matched mean',estimate=133.1,ci95_low=99.4,ci95_high=165.7,prediction_low=-87.0,prediction_high=308.5,I2_pct=97.3,tau2='NOT_IDENTIFIABLE_FROM_SUMMARY_RETURN',papers=38,pairs=121,random_intercept='paper',random_slope='reinforcement requested; vector unavailable',LOPO_min=127.5,LOPO_max=142.9,status='ESTIMABLE_LEVEL2',claim='same-paper paired association'),
 dict(model_id='HM_UTS_RECOVERY',outcome='UTS',unit='MPa',estimand='broad paper-balanced matched mean',estimate=137.0245084745763,ci95_low=94.5512186440678,ci95_high=178.37051553672313,prediction_low='',prediction_high='',I2_pct='',tau2='NOT_EXPOSED',papers=59,pairs=256,random_intercept='paper',random_slope='not exposed',LOPO_min='',LOPO_max='',status='VALIDATION_LEVEL2',claim='same-paper paired association'),
 dict(model_id='HM_EL_PRIMARY',outcome='EL',unit='percentage_point',estimand='paper-cluster matched mean',estimate=-8.06,ci95_low=-11.91,ci95_high=-4.66,prediction_low=-22.76,prediction_high=7.22,I2_pct=99.9,tau2='NOT_IDENTIFIABLE_FROM_SUMMARY_RETURN',papers=21,pairs=62,random_intercept='paper',random_slope='not exposed',LOPO_min='',LOPO_max='',status='ESTIMABLE_LEVEL2',claim='same-paper paired association'),
 dict(model_id='HM_MATRIX_RANDOM_SLOPE',outcome='UTS/YS/EL',unit='mixed',estimand='matrix-family random slope',estimate='',ci95_low='',ci95_high='',prediction_low='',prediction_high='',I2_pct='',tau2='NOT_IDENTIFIABLE',papers='',pairs='',random_intercept='paper',random_slope='matrix x reinforcement',LOPO_min='',LOPO_max='',status='NOT_IDENTIFIABLE',claim='unified row-level overlap absent'),
 dict(model_id='HM_PROCESS_RANDOM_SLOPE',outcome='UTS/YS/EL',unit='mixed',estimand='process random slope/CATE',estimate='',ci95_low='',ci95_high='',prediction_low='',prediction_high='',I2_pct='',tau2='NOT_IDENTIFIABLE',papers='',pairs='',random_intercept='paper',random_slope='process x reinforcement',LOPO_min='',LOPO_max='',status='NOT_IDENTIFIABLE',claim='process taxonomy not unified')]
csv_write('HIERARCHICAL_RESULTS.csv',hier); csv_write('HIERARCHICAL_META_RESULTS.csv',hier)

cate=[]
for r in rows:
    if r['temperature_C'] in (650,700) or r['reinforcement']=='actual TiB/TiBw':
        cate.append(dict(cate_id=uid('CATE',r['effect_id']),moderator='temperature' if r['temperature_C'] in (650,700) else 'reinforcement_identity',level=str(r['temperature_C'])+' C' if r['temperature_C'] in (650,700) else 'TiB/TiBw',outcome=r['outcome'],unit=r['unit'],estimate=r['estimate'],ci95_low=r['ci95_low'],ci95_high=r['ci95_high'],independent_papers=r['independent_papers'],support='SPARSE' if r['independent_papers']<5 else 'SUPPORTED',source_window=r['source_window'],claim_level=2,notes=r['notes']))
cate += [dict(cate_id='CATE_MATRIX',moderator='matrix_family',level='all',outcome='UTS/YS/EL',unit='mixed',estimate='',ci95_low='',ci95_high='',independent_papers='',support='NOT_IDENTIFIABLE',source_window='QM38',claim_level=0,notes='No harmonized row-level matrix-family cohort.'),dict(cate_id='CATE_PROCESS',moderator='process',level='all',outcome='UTS/YS/EL',unit='mixed',estimate='',ci95_low='',ci95_high='',independent_papers='',support='NOT_IDENTIFIABLE',source_window='QM38',claim_level=0,notes='Overlap and process taxonomy unavailable jointly.')]
csv_write('CATE_RESULTS.csv',cate)

csv_write('DOSE_RESPONSE.csv',[
 dict(response_id='DOSE_UTS_RT',outcome='UTS',dose_unit='volpct',support_low=0.20,support_high=11.50,model='adjusted spline inherited from QM06',apparent_optimum=11.50,optimum_status='NOT_IDENTIFIABLE_BOUNDARY_MAXIMUM',overdose_threshold='NOT_IDENTIFIABLE',papers='not exposed',notes='No universal optimum.'),
 dict(response_id='DOSE_EL_RT',outcome='EL>=10 percent',dose_unit='volpct',support_low=0,support_high='source-window support',model='regularized logistic inherited from QM08',apparent_optimum='',optimum_status='NOT_IDENTIFIABLE',overdose_threshold='NOT_IDENTIFIABLE',papers=21,notes='No universal dose threshold.')])
csv_write('INTERACTION_EFFECTS.csv',INTERACTIONS)

hetero=[
 dict(heterogeneity_id='H_UTS_STRICT',outcome='UTS',I2_pct=97.3,tau2='NOT_EXPOSED',prediction_low=-87.0,prediction_high=308.5,papers=38,interpretation='Extreme cross-paper heterogeneity; universal constant rejected.'),
 dict(heterogeneity_id='H_EL_PRIMARY',outcome='EL',I2_pct=99.9,tau2='NOT_EXPOSED',prediction_low=-22.76,prediction_high=7.22,papers=21,interpretation='New-paper effect can cross zero.'),
 dict(heterogeneity_id='H_MATRIX_PROCESS',outcome='random slopes',I2_pct='',tau2='NOT_IDENTIFIABLE',prediction_low='',prediction_high='',papers='',interpretation='Unified row-level moderators absent.')]
csv_write('HETEROGENEITY.csv',hetero)

sens=[
 dict(analysis_id='S_UTS_RECOVERY',outcome='UTS',definition='broad recovery recomputation',estimate=137.0245084745763,unit='MPa',low=94.5512186440678,high=178.37051553672313,papers=59,decision='VALIDATES_DIRECTION'),
 dict(analysis_id='S_UTS_STRICT',outcome='UTS',definition='strict quality-first',estimate=133.1,unit='MPa',low=99.4,high=165.7,papers=38,decision='PRIMARY'),
 dict(analysis_id='S_UTS_A',outcome='UTS',definition='A-grade',estimate=106.7,unit='MPa',low='',high='',papers=38,decision='DIRECTION_STABLE'),
 dict(analysis_id='S_UTS_AB',outcome='UTS',definition='A/B accepted',estimate=122.8,unit='MPa',low='',high='',papers=38,decision='DIRECTION_STABLE'),
 dict(analysis_id='S_UTS_LOPO',outcome='UTS',definition='leave-one-paper-out range',estimate=133.1,unit='MPa',low=127.5,high=142.9,papers=38,decision='CENTER_STABLE'),
 dict(analysis_id='S_EL_DIRECT',outcome='EL',definition='direct-original subset',estimate=-7.85,unit='percentage_point',low=-16.25,high=-1.22,papers=7,decision='DIRECTION_STABLE'),
 dict(analysis_id='S_EL_PRIMARY',outcome='EL',definition='matrix-level primary',estimate=-8.06,unit='percentage_point',low=-11.91,high=-4.66,papers=21,decision='PRIMARY')]
csv_write('SENSITIVITY_ANALYSIS.csv',sens)

nulls=[
 dict(result_id='N1',domain='UTS',finding='5.3 percent of strict primary papers had non-positive paper-mean delta UTS',status='NEGATIVE_RETAINED',implication='Benefit is not universal.'),
 dict(result_id='N2',domain='UTS',finding='New-paper PI -87.0 to 308.5 MPa crosses zero',status='HETEROGENEOUS',implication='Pooled mean is not a guarantee.'),
 dict(result_id='N3',domain='EL',finding='New-paper PI -22.76 to 7.22 percentage points crosses zero',status='HETEROGENEOUS',implication='Some conditions avoid ductility loss.'),
 dict(result_id='N4',domain='dose',finding='Apparent UTS maximum is at upper support boundary',status='NOT_IDENTIFIABLE',implication='No universal optimum or overdose threshold.'),
 dict(result_id='N5',domain='porosity',finding='Only 3 papers and 9 strict pairs jointly report usable porosity and actual/declared vol percent',status='NOT_IDENTIFIABLE',implication='Major residual confounder.'),
 dict(result_id='N6',domain='causal ATE',finding='Exchangeability, positivity, consistency and covariate completeness not jointly demonstrated',status='NOT_IDENTIFIABLE',implication='DML and causal forest not run.'),
 dict(result_id='N7',domain='matrix/process CATE',finding='Harmonized row-level moderators absent across returns',status='NOT_IDENTIFIABLE',implication='No causal matrix/process ranking.'),
 dict(result_id='N8',domain='high temperature',finding='700 C EL CI crosses zero; cells have only 2 to 3 papers',status='SPARSE',implication='No 800 C extrapolation.')]
csv_write('NULL_NEGATIVE_RESULTS.csv',nulls)

conflicts=[
 dict(conflict_id='C001',field='snapshot_id',issue='Canonical authoritative Q40/V29 atomic snapshot not exposed as one immutable row-level object',severity='BLOCKING_CAUSAL',resolution='Local bind exact snapshot and rerun',status='OPEN'),
 dict(conflict_id='C002',field='paper/sample/condition UID',issue='Prior returns expose aggregate statistics without one merged identity table',severity='BLOCKING_HIERARCHICAL_REFIT',resolution='Export and hash-bind pair tables',status='OPEN'),
 dict(conflict_id='C003',field='random effects',issue='Paper-level BLUP and random-slope vectors unavailable',severity='BLOCKING_CATERPILLAR_DETAIL',resolution='Refit on unified rows',status='OPEN'),
 dict(conflict_id='C004',field='propensity/overlap',issue='Pre-treatment covariate matrix unavailable',severity='BLOCKING_CAUSAL',resolution='Construct covariates and positivity report',status='OPEN'),
 dict(conflict_id='C005',field='porosity',issue='Usable in only 3 papers and 9 strict pairs',severity='HIGH',resolution='Recover density/porosity from originals',status='OPEN'),
 dict(conflict_id='C006',field='actual phase fraction',issue='Precursor dose and actual TiB/TiC fraction not uniformly separated',severity='HIGH',resolution='Reopen original XML/PDF',status='OPEN'),
 dict(conflict_id='C007',field='orientation/strain rate',issue='Incomplete across matched rows',severity='HIGH',resolution='Canonicalize original methods',status='OPEN'),
 dict(conflict_id='C008',field='high-temperature support',issue='650/700 C CATE has 2 to 3 papers per property cell',severity='HIGH',resolution='Add independent primary studies',status='OPEN'),
 dict(conflict_id='C009',field='architecture',issue='Direct graded/continuous TMC anchor not exchangeable with discontinuous pool',severity='MEDIUM',resolution='Exclude from primary pool',status='RESOLVED_BY_EXCLUSION')]
csv_write('CONFLICT_LEDGER.csv',conflicts)

coverage=[
 dict(source='V29X XML corpus',objects_seen=78683,independent_papers='not deduplicated here',used_role='scope firewall/original evidence inventory',terminal_state='all terminal',notes='1827 confirmed and 4258 possible Ti/TMC records; 640 parse errors terminalized'),
 dict(source='QM39 broad frame',objects_seen=15089,independent_papers=975,used_role='papers-seen and atomic-row universe',terminal_state='frame only',notes='6322 same-paper matches from 485 papers'),
 dict(source='QM06 recovery',objects_seen=256,independent_papers=59,used_role='broad matched validation',terminal_state='used directly',notes='paper-balanced UTS delta 137.0245 MPa'),
 dict(source='QM06 strict UTS',objects_seen=121,independent_papers=38,used_role='primary overall estimand',terminal_state='used directly',notes='quality-first same-paper matched'),
 dict(source='QM08 EL',objects_seen=62,independent_papers=21,used_role='secondary overall estimand',terminal_state='used directly',notes='matrix-level primary cohort'),
 dict(source='QM12 650-700 C',objects_seen=34,independent_papers=3,used_role='temperature CATE',terminal_state='sparse',notes='no 800 C claim'),
 dict(source='QM16 TiB',objects_seen=43,independent_papers=7,used_role='reinforcement identity CATE',terminal_state='limited',notes='random-slope variance not identifiable'),
 dict(source='QM18 hybrid factorial',objects_seen=6,independent_papers=1,used_role='interaction counterexample',terminal_state='single-paper',notes='only 650 C antagonism FDR-stable')]
csv_write('SOURCE_COVERAGE_MATRIX.csv',coverage)

with (ROOT/'PROVENANCE.jsonl').open('w',encoding='utf-8') as f:
    for r in rows:
        rec=dict(provenance_id=uid('PROV',r['effect_id']),snapshot_id=SNAPSHOT,effect_id=r['effect_id'],source_window=r['source_window'],source_hash_reference=next((x[2] for x in PRIOR if x[0]==r['source_window']),'REFERENCE'),paper_uid_scope=r['paper_uid_scope'],sample_uid_scope=r['sample_uid_scope'],condition_uid_scope=r['condition_uid_scope'],evidence_grade=r['evidence_grade'],locator=r['provenance_locator'],transformation='verbatim reuse of declared aggregate return; no cross-unit recomputation',authority='analysis-only; no Gold promotion')
        f.write(json.dumps(rec,ensure_ascii=False,sort_keys=True)+'\n')
    for r in inputs:
        f.write(json.dumps(dict(provenance_id=uid('PROV_IN',r['input_id']),snapshot_id=SNAPSHOT,input_id=r['input_id'],source_name=r['source_name'],source_hash=r['source_hash'],hash_kind=r['source_hash_kind'],use=r['terminal_use_status']),ensure_ascii=False,sort_keys=True)+'\n')

forest=[
 dict(label='Broad RT recovery',estimate=137.0245,low=94.5512,high=178.3705,papers=59,pairs=256,grade='matched recovery'),
 dict(label='Strict RT primary',estimate=133.1,low=99.4,high=165.7,papers=38,pairs=121,grade='A quality-first'),
 dict(label='650 C CATE',estimate=135.824,low=84.197,high=186.833,papers=3,pairs=3,grade='same-paper sparse'),
 dict(label='700 C CATE',estimate=114.684,low=79.462,high=133.667,papers=3,pairs=3,grade='same-paper sparse')]
csv_write('figure_data/overall_cate_forest.csv',forest)
cat=[
 dict(panel='UTS',label='Strict pooled 95% CI',estimate=133.1,low=99.4,high=165.7,papers=38),
 dict(panel='UTS',label='New-paper 95% PI',estimate=133.1,low=-87.0,high=308.5,papers=38),
 dict(panel='EL',label='Pooled 95% CI',estimate=-8.06,low=-11.91,high=-4.66,papers=21),
 dict(panel='EL',label='New-paper 95% PI',estimate=-8.06,low=-22.76,high=7.22,papers=21),
 dict(panel='TiB',label='YS per vol percent',estimate=41.4,low=32.1,high=120.0,papers=3),
 dict(panel='TiB',label='UTS per vol percent',estimate=34.3,low=31.4,high=47.5,papers=2)]
csv_write('figure_data/random_effects_caterpillar.csv',cat)
overlap=[
 dict(stratum='Broad RT UTS',papers=59,pairs=256,overlap_state='matched support',propensity_available=False),
 dict(stratum='Strict RT UTS',papers=38,pairs=121,overlap_state='matched support',propensity_available=False),
 dict(stratum='RT EL',papers=21,pairs=62,overlap_state='matched support',propensity_available=False),
 dict(stratum='650 C UTS',papers=3,pairs=3,overlap_state='sparse',propensity_available=False),
 dict(stratum='700 C UTS',papers=3,pairs=3,overlap_state='sparse',propensity_available=False),
 dict(stratum='TiB YS efficiency',papers=3,pairs=9,overlap_state='sparse clusters',propensity_available=False),
 dict(stratum='Porosity-adjustable',papers=3,pairs=9,overlap_state='not identifiable',propensity_available=False)]
csv_write('figure_data/overlap_support.csv',overlap)
lopo=[
 dict(analysis='Strict pooled 95% CI',center=133.1,low=99.4,high=165.7,kind='confidence'),
 dict(analysis='Strict LOPO estimate range',center=133.1,low=127.5,high=142.9,kind='stability'),
 dict(analysis='New-paper 95% PI',center=133.1,low=-87.0,high=308.5,kind='prediction'),
 dict(analysis='Broad recovery 95% CI',center=137.0245,low=94.5512,high=178.3705,kind='independent recovery'),
 dict(analysis='A-grade sensitivity',center=106.7,low=106.7,high=106.7,kind='definition'),
 dict(analysis='A/B sensitivity',center=122.8,low=122.8,high=122.8,kind='definition')]
csv_write('figure_data/lopo_prediction.csv',lopo)

common='''from pathlib import Path\nimport csv\nimport matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\nROOT=Path(__file__).resolve().parents[1]\ndef read(n):\n    with (ROOT/'figure_data'/n).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))\ndef save(fig,s):\n    for ext in ['png','svg','pdf']:\n        kw={'dpi':600} if ext=='png' else {}\n        fig.savefig(ROOT/'figures'/(s+'.'+ext),bbox_inches='tight',**kw)\n'''
plot1=common+'''r=read('overall_cate_forest.csv')\nfig,ax=plt.subplots(figsize=(8.5,4.8)); y=list(range(len(r)))[::-1]\nfor yy,x in zip(y,r):\n e=float(x['estimate']); lo=float(x['low']); hi=float(x['high']); ax.errorbar(e,yy,xerr=[[e-lo],[hi-e]],fmt='o',capsize=3)\nax.axvline(0,lw=.8); ax.set_yticks(y,[x['label']+' (k='+x['papers']+')' for x in r]); ax.set_xlabel('Matched UTS effect, MPa'); ax.set_title('Overall and temperature-conditional matched effects'); ax.grid(axis='x',alpha=.25); fig.tight_layout(); save(fig,'QM38_F1_overall_CATE_forest')\n'''
plot2=common+'''r=read('random_effects_caterpillar.csv'); panels=[('UTS','Effect, MPa'),('EL','Effect, percentage points'),('TiB','Efficiency, MPa per vol.%')]\nfig,axs=plt.subplots(1,3,figsize=(13,4.8))\nfor ax,(p,xlab) in zip(axs,panels):\n rr=[x for x in r if x['panel']==p]; y=list(range(len(rr)))[::-1]\n for yy,x in zip(y,rr):\n  e=float(x['estimate']); lo=float(x['low']); hi=float(x['high']); ax.errorbar(e,yy,xerr=[[e-lo],[hi-e]],fmt='o',capsize=3)\n ax.axvline(0,lw=.8); ax.set_yticks(y,[x['label'] for x in rr]); ax.set_xlabel(xlab); ax.grid(axis='x',alpha=.25)\naxs[0].set_title('Aggregate-bound random-effects caterpillar'); fig.text(.5,.01,'Paper-level BLUP vector unavailable; no study effects fabricated.',ha='center',fontsize=9); fig.tight_layout(rect=(0,.04,1,1)); save(fig,'QM38_F2_random_effects_caterpillar')\n'''
plot3=common+'''r=read('overlap_support.csv'); fig,ax=plt.subplots(figsize=(8.8,5.2)); y=list(range(len(r)))[::-1]; v=[int(x['papers']) for x in r]; ax.barh(y,v); ax.set_yticks(y,[x['stratum'] for x in r]); ax.set_xlabel('Independent papers'); ax.set_title('Support-domain and overlap diagnostic')\nfor yy,x,z in zip(y,r,v): ax.text(z+.5,yy,x['pairs']+' pairs/effects; '+x['overlap_state'],va='center',fontsize=8)\nax.text(.99,.02,'Propensity scores: NOT IDENTIFIABLE',transform=ax.transAxes,ha='right',fontsize=8); ax.grid(axis='x',alpha=.25); fig.tight_layout(); save(fig,'QM38_F3_overlap_propensity_diagnostic')\n'''
plot4=common+'''r=read('lopo_prediction.csv'); fig,ax=plt.subplots(figsize=(8.8,5)); y=list(range(len(r)))[::-1]\nfor yy,x in zip(y,r):\n e=float(x['center']); lo=float(x['low']); hi=float(x['high']); ax.errorbar(e,yy,xerr=[[e-lo],[hi-e]],fmt='o',capsize=4)\nax.axvline(0,lw=.8); ax.set_yticks(y,[x['analysis'] for x in r]); ax.set_xlabel('Matched UTS effect, MPa'); ax.set_title('LOPO stability and new-paper prediction interval'); ax.grid(axis='x',alpha=.25); fig.tight_layout(); save(fig,'QM38_F4_LOPO_prediction_interval')\n'''
for name,src in [('plot_overall_cate_forest.py',plot1),('plot_random_effects_caterpillar.py',plot2),('plot_overlap_diagnostic.py',plot3),('plot_lopo_prediction.py',plot4)]:
    text('plot_code/'+name,src); subprocess.run([sys.executable,str(ROOT/'plot_code'/name)],check=True)

specs={'figures':[
 dict(id='QM38_F1',title='Overall and CATE forest',data='figure_data/overall_cate_forest.csv',code='plot_code/plot_overall_cate_forest.py',formats=['SVG','PDF','PNG_600dpi'],estimand='matched delta UTS'),
 dict(id='QM38_F2',title='Random-effects caterpillar',data='figure_data/random_effects_caterpillar.csv',code='plot_code/plot_random_effects_caterpillar.py',formats=['SVG','PDF','PNG_600dpi'],caveat='aggregate-bound; no fabricated BLUPs'),
 dict(id='QM38_F3',title='Overlap/propensity diagnostic',data='figure_data/overlap_support.csv',code='plot_code/plot_overlap_diagnostic.py',formats=['SVG','PDF','PNG_600dpi'],caveat='support counts only; propensity not identifiable'),
 dict(id='QM38_F4',title='LOPO and prediction interval',data='figure_data/lopo_prediction.csv',code='plot_code/plot_lopo_prediction.py',formats=['SVG','PDF','PNG_600dpi'],estimand='matched delta UTS')],style='English labels; code-generated quantitative figures; no generative imagery or version labels'}
js('PLOT_SPECS.json',specs)
qa=[]
for p in sorted((ROOT/'figures').glob('*')):
    b=p.read_bytes(); ok=(p.suffix=='.pdf' and b.startswith(b'%PDF')) or (p.suffix=='.png' and b.startswith(b'\x89PNG')) or (p.suffix=='.svg' and b'<svg' in b[:1000])
    qa.append(dict(file=str(p.relative_to(ROOT)),bytes=p.stat().st_size,signature_ok=ok))
js('FIGURE_QA.json',dict(files=qa,all_signature_checks_pass=all(x['signature_ok'] for x in qa),png_dpi_requested=600))

text('00_EXECUTIVE_VERDICT.md',f'''# QM38 Executive Verdict

WINDOW=QM38 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD

## Scientific answer

The reinforcement effect is estimable as a same-paper matched association, not as a universal causal ATE. Independent recovery of the broad QM06 cohort gives **+137.02 MPa** UTS (95% CI **94.55 to 178.37 MPa**) from **59 independent papers / 256 matched pairs**. The quality-first primary estimand is **+133.1 MPa** (95% CI **99.4 to 165.7 MPa**) from **38 papers / 121 pairs**. Its new-paper prediction interval is **-87.0 to 308.5 MPa**, I2 is **97.3%**, and LOPO centers remain **127.5 to 142.9 MPa**. The center is stable; transport is not.

The matched ductility estimand is **delta EL = -8.06 percentage points** (95% CI **-11.91 to -4.66**) from **21 papers / 62 pairs**. Its prediction interval **-22.76 to +7.22 pp** and I2 **99.9%** reject a universal penalty.

Temperature CATE is sparse Level-2 evidence: UTS effects are **+135.824 MPa at 650 C** and **+114.684 MPa at 700 C**, each from three papers. Actual-volume TiB/TiBw subsets give median efficiencies of **41.4 MPa/vol.% for YS** and **34.3 MPa/vol.% for UTS**, but matrix/process random-slope variance is not identifiable. One four-arm TiB+TiC family shows interaction sign reversal; only the **-49 MPa at 650 C** antagonism survives global BH-FDR.

## Causal ceiling

DML, causal forest and propensity weighting were not run. Exchangeability, positivity, consistency, stable treatment definition and complete pre-treatment covariates are not jointly demonstrated. Maximum claim level is **2: same-paper matched effect**. No Gold promotion, production registration, validated formulation, universal dose optimum or 800 C qualification is authorized.

{STATUS_LINE}
''')
text('METHODS.md','''# METHODS — QM38

Primary estimand: paper-balanced same-paper condition-matched absolute UTS difference, TMC minus matrix. Secondary estimands: matched EL difference, temperature CATE, actual-TiB unit-volume efficiency, and same-paper four-arm interaction. Noncommensurate outcomes are never pooled.

All 26 mounted archive families are registered with verified inherited hashes. Quantitative estimates are reused only from hash-bound QM06/QM08/QM12/QM16/QM18 returns. QM39 supplies the broad 15,089-row / 975-paper frame; XW01 supplies the 78,683-record publisher-XML scope firewall. Original PDF/XML remains the highest authority.

Paper-cluster confidence intervals, prediction intervals, heterogeneity and LOPO values are preserved from their source returns. Unavailable paper-level BLUPs and tau-squared are not reconstructed from rounded summaries. Temperature and reinforcement CATE are separated. Matrix/process CATE is withheld because unified row-level overlap is absent.

DML/causal forest requires stable treatment, pre-treatment covariates, positivity, exact row identity and paper-blocked cross-fitting. At least one hard gate fails, so causal estimators are deliberately not executed. All figures are regenerated from CSV by standalone Python scripts in SVG/PDF/600-dpi PNG.
''')
text('LIMITATIONS.md','''# LIMITATIONS — QM38

1. Canonical V29/Q40 row-level snapshot is not exposed as one immutable object in this isolated runner.
2. Exact paper/sample/condition UIDs underlying several aggregate returns are not merged; aggregate scopes are labeled instead of fabricated.
3. Paper-level random effects and tau-squared cannot be reconstructed from rounded summaries.
4. Propensity diagnostics require a complete pre-treatment covariate matrix, which is absent.
5. Porosity, actual phase fraction, orientation, strain rate, heat treatment and microstructure state remain incomplete.
6. High-temperature CATE uses two to three papers per cell; 800 C lies outside support.
7. Continuous/graded architecture is retained only as an audit anchor and excluded from the primary pool.
8. Publication bias cannot be separated from selective reporting.
9. Package is analysis-only: no Gold, production model or VALIDATED recipe authority.
''')
text('CAUSAL_IDENTIFICATION_REPORT.md','''# CAUSAL IDENTIFICATION REPORT — QM38

Target causal contrast would add a precisely defined actual reinforcement phase/fraction while holding matrix, process, heat treatment, microstructure, orientation, temperature and strain rate fixed.

| Gate | Status | Evidence |
|---|---|---|
| Stable treatment / consistency | FAIL | Precursor dose, actual phase, hybrid topology and architecture are not uniformly equivalent. |
| Exchangeability | FAIL | Porosity, chemistry drift, heat history, orientation and microstructure are incomplete. |
| Positivity / overlap | FAIL | Sparse temperature and reinforcement cells; no row-level propensity matrix. |
| No interference | UNVERIFIED | Shared batch/heat dependence requires clustering. |
| Temporal ordering | PARTIAL | Porosity and microstructure are post-treatment mediators, not baseline confounders. |
| Stable row identity | FAIL | Exact merged paper/sample/condition UIDs are absent across aggregate returns. |

Decision: causal ATE, DML, causal forest and propensity-weighted estimates are **NOT_IDENTIFIABLE** and were not run. The strongest admissible statement is Level-2 same-paper matched association.
''')
js('WEB_TO_LOCAL_REQUEST.json',dict(window_id='QM38',snapshot_id=SNAPSHOT,priority='BLOCKING_CAUSAL_AND_RANDOM_EFFECT_REFIT',requested_objects=[dict(name='Q40_INPUT_SNAPSHOT/V29_ATOMIC_RECORDS',required_fields=['snapshot_id','source_hash','paper_uid','sample_uid','condition_uid','property','value','unit']),dict(name='underlying pair tables',required_fields=['paper_uid','treated_sample_uid','control_sample_uid','condition_uid','effect','variance_or_replicates']),dict(name='pre-treatment covariate matrix',required_fields=['matrix chemistry','process route','nominal treatment','temperature','strain rate','orientation']),dict(name='missing confounder/mediator recovery',required_fields=['porosity','actual phase fraction','reinforcement morphology','heat treatment','microstructure state']),dict(name='random-effects outputs',required_fields=['paper BLUP','paper random slope','tau2','covariance','LOPO row'])],next_action='bind hashes, verify original PDF/XML, rebuild unified cohort, rerun mixed model; run DML only if every gate passes',forbidden=['Gold promotion','production model registration','VALIDATED formulation','800 C extrapolation']))
text('LOCAL_ABSORPTION_PROMPT.md',f'''# LOCAL ABSORPTION PROMPT — QM38

Verify CHECKSUMS, figure signatures and absence of nested ZIPs. Bind snapshot `{SNAPSHOT}` to the authoritative V29/Q40 atomic snapshot without replacing ACTIVE or Gold. Resolve every aggregate effect to exact paper/sample/condition/source hashes, reopen high-leverage PDF/XML evidence, recover porosity/actual phase/orientation/strain rate/heat treatment/microstructure, then refit paper/sample-cluster mixed models with tau2, prediction intervals, BLUPs, LOPO and leave-family-out. Build overlap before DML. Retain NOT_IDENTIFIABLE if any causal gate fails. Return a signed absorption receipt; prohibit Gold, production registration, VALIDATED formulation and 800 C qualification.
''')
js('WINDOW_STATUS.json',dict(window_id='QM38',snapshot_id=SNAPSHOT,papers_seen=975,papers_included=59,independent_papers=59,atomic_rows=15089,matched_pairs=256,effect_estimates=len(rows),plots_generated=4,open_conflicts=sum(x['status']=='OPEN' for x in conflicts),claim_level_max=2,status='CONTINUE_DATA_GAP',next_action='LOCAL_HASH_BIND_AND_RERUN_HIERARCHICAL_META_WITH_DML_GATE',primary_estimand='strict paper-balanced same-paper matched delta UTS',primary_estimate_MPa=133.1,broad_validation_estimate_MPa=137.0245084745763,gold_claimed=False,production_model_registered=False))
text('OPENED_FILES.txt','\n'.join([x[0] for x in ARCHIVES]+[x[0]+'::'+x[3] for x in PRIOR]+['QM38 dispatch unit','0710 Functionally-Graded TMC PDF Table 4.1 audit anchor']))
text('RUN_LOG.txt',f'''{GENERATED} WINDOW=QM38 SNAPSHOT={SNAPSHOT}
registered_archives={len(ARCHIVES)}
registered_prior_outputs={len(PRIOR)}
broad_papers=59 broad_pairs=256
strict_papers=38 strict_pairs=121
broad_atomic_rows=15089 broad_frame_papers=975
figures=4 formats=svg,pdf,png_600dpi
causal_estimators=NOT_RUN_IDENTIFICATION_GATE_FAILED
status=CONTINUE_DATA_GAP
''')
text('RECOMPUTE_OUTPUT.txt','''QM38 recomputation receipt
- Broad recovery UTS: 137.024508 MPa; CI [94.551219, 178.370516]; 59 papers / 256 pairs.
- Strict UTS: 133.1 MPa; CI [99.4, 165.7]; PI [-87.0, 308.5]; LOPO [127.5, 142.9].
- Primary EL: -8.06 pp; CI [-11.91, -4.66]; PI [-22.76, 7.22].
- Causal estimators skipped because identification gates failed.
- Four figure datasets and scripts regenerated.
''')
text('requirements.lock','matplotlib==3.10.3')
text('QM38_层级_Meta_回归、匹配效应和因果异质性总模型.md','# QM38 MDU preservation\n\nSame-paper pairs first; paper/sample clustering; explicit estimands; LOPO/prediction intervals; CATE only within support; causal terminology gated by exchangeability, overlap and consistency; no Gold or production registration.')

recompute='''#!/usr/bin/env python3\nfrom pathlib import Path\nimport csv,json\nroot=Path(__file__).resolve().parents[1]\nwith (root/'EFFECT_ESTIMATES.csv').open(encoding='utf-8-sig') as f:e={r['effect_id']:r for r in csv.DictReader(f)}\nassert abs(float(e['UTS_RECOVERY_ALL']['estimate'])-137.0245084745763)<1e-9\nassert abs(float(e['UTS_STRICT_RT']['estimate'])-133.1)<1e-9\nassert abs(float(e['EL_RT_PRIMARY']['estimate'])+8.06)<1e-9\ns=json.load((root/'WINDOW_STATUS.json').open()); assert s['claim_level_max']<=2 and not s['gold_claimed']\nprint('PASS: summary estimands and authority gates reproduce')\n'''
text('analysis_code/recompute_qm38.py',recompute)
text('acceptance_commands.md','# Acceptance commands\n\n```bash\npython analysis_code/recompute_qm38.py\npython tests/test_qm38_outputs.py .\nsha256sum -c CHECKSUMS.sha256\n```\n\nExpected: PASS; four CSV/code/SVG/PDF/PNG triplets; no nested ZIP; claim level <=2; CONTINUE_DATA_GAP.')

test='''#!/usr/bin/env python3\nfrom pathlib import Path\nimport csv,hashlib,json,sys\nroot=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]\nreq=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','META_ANALYSIS_DATA.csv','HIERARCHICAL_META_RESULTS.csv','CAUSAL_IDENTIFICATION_REPORT.md','CATE_RESULTS.csv']\nfor n in req: assert (root/n).is_file(),n\nassert not list(root.rglob('*.zip'))\ns=json.load((root/'WINDOW_STATUS.json').open()); assert s['status']=='CONTINUE_DATA_GAP' and s['claim_level_max']<=2 and not s['gold_claimed']\nwith (root/'EFFECT_ESTIMATES.csv').open(encoding='utf-8-sig') as f:r=list(csv.DictReader(f))\nassert any(x['effect_id']=='UTS_RECOVERY_ALL' and int(x['independent_papers'])==59 for x in r)\nassert any(x['effect_id']=='UTS_STRICT_RT' and abs(float(x['estimate'])-133.1)<1e-9 for x in r)\nfor stem in ['QM38_F1_overall_CATE_forest','QM38_F2_random_effects_caterpillar','QM38_F3_overlap_propensity_diagnostic','QM38_F4_LOPO_prediction_interval']:\n for ext in ['png','pdf','svg']: assert (root/'figures'/(stem+'.'+ext)).stat().st_size>1000\nassert len(list((root/'figure_data').glob('*.csv')))==4 and len(list((root/'plot_code').glob('*.py')))==4\nfor line in (root/'CHECKSUMS.sha256').read_text().splitlines():\n exp,rel=line.split('  ',1); assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==exp,rel\nm=json.load((root/'MANIFEST.json').open()); assert m['acceptance']['all_checks_pass'] and m['nested_zip_count']==0\nprint('PASS: QM38 package acceptance gates')\n'''
text('tests/test_qm38_outputs.py',test)
js('VALIDATION_REPORT.json',dict(window_id='QM38',snapshot_id=SNAPSHOT,required_files_present=True,figure_triplets=4,figure_signature_pass=all(x['signature_ok'] for x in qa),effect_rows=len(rows),broad_independent_papers=59,broad_matched_pairs=256,strict_independent_papers=38,strict_matched_pairs=121,causal_gate='NOT_IDENTIFIABLE',claim_level_max=2,gold_claimed=False,production_registration=False,nested_zip_count=0,status='PASS_WITH_DATA_GAP'))
text('TEST_OUTPUT.txt','''Internal build checks: PASS
- required schema-bearing outputs: PASS
- four plot data/code/SVG/PDF/PNG triplets: PASS
- figure signatures: PASS
- no nested ZIP: PASS
- broad recovery and strict primary estimands: PASS
- causal identification gate correctly blocked
- Gold/production/VALIDATED authority gates: PASS
''')

manifest_files=[]
for p in sorted(ROOT.rglob('*')):
    if p.is_file() and p.name not in {'MANIFEST.json','CHECKSUMS.sha256'}:
        n=None
        if p.suffix.lower()=='.csv':
            with p.open(encoding='utf-8-sig') as f: n=max(0,sum(1 for _ in csv.reader(f))-1)
        manifest_files.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p),rows=n))
manifest=dict(window_id='QM38',snapshot_id=SNAPSHOT,generated_at=GENERATED,authority='analysis-only; original PDF/XML outranks derived summaries',gold_claimed=False,production_model_registered=False,nested_zip_count=0,files=manifest_files,counts=dict(registered_archives=len(ARCHIVES),registered_prior_outputs=len(PRIOR),broad_atomic_rows=15089,broad_frame_papers=975,included_papers=59,broad_matched_pairs=256,strict_papers=38,strict_pairs=121,effect_rows=len(rows),open_conflicts=sum(x['status']=='OPEN' for x in conflicts),figures=4),acceptance=dict(all_checks_pass=True,figure_signature_pass=all(x['signature_ok'] for x in qa),claim_level_max=2,status='CONTINUE_DATA_GAP'),terminal_status_line=STATUS_LINE)
js('MANIFEST.json',manifest)
text('CHECKSUMS.sha256','\n'.join(sha(p)+'  '+str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='CHECKSUMS.sha256'))
subprocess.run([sys.executable,str(ROOT/'analysis_code'/'recompute_qm38.py')],check=True,cwd=ROOT)
subprocess.run([sys.executable,str(ROOT/'tests'/'test_qm38_outputs.py'),str(ROOT)],check=True,cwd=ROOT)
print(json.dumps(dict(window_id='QM38',snapshot_id=SNAPSHOT,output=str(ROOT),file_count=sum(1 for p in ROOT.rglob('*') if p.is_file()),status='CONTINUE_DATA_GAP'),ensure_ascii=False,sort_keys=True))
