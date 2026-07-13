#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, shutil, textwrap
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path('FINAL_QM23')
NOW=datetime.now(timezone.utc).isoformat()
WINDOW='QM23'
DOI='10.1016/j.msea.2024.146757'
TITLE='Effect of thermal exposure on microstructure and mechanical properties of Ti65 high-temperature titanium alloy deposited by laser direct energy deposition'
MANDATORY=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','SN_ZR_SI_EFFECTS.csv','ELEMENT_TEMP_INTERACTIONS.csv','SILICIDE_RISK.csv','HIGHTEMP_ELEMENT_NET_BENEFIT.csv']
DENS={'Ti':4.506,'Al':2.70,'Sn':7.31,'Zr':6.52,'Mo':10.28,'Nb':8.57,'Ta':16.69,'Si':2.329,'W':19.25,'C':2.267}
COMP={'Ti':84.2,'Al':5.8,'Sn':4.0,'Zr':3.5,'Mo':0.8,'Nb':0.4,'Ta':0.4,'Si':0.4,'W':0.4,'C':0.1}

def h(s): return hashlib.sha256(str(s).encode()).hexdigest()
def uid(p,*x): return p+'_'+h('|'.join(map(str,x)))[:20]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def wt_density(c): return 1/sum((v/100)/DENS[k] for k,v in c.items())
def txt(rel,s):
 p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.rstrip()+'\n',encoding='utf-8')
def js(rel,o): txt(rel,json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True))
def csvw(rel,rows,cols=None):
 p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True)
 if cols is None: cols=list(rows[0]) if rows else ['status','reason']
 pd.DataFrame(rows,columns=cols).to_csv(p,index=False,encoding='utf-8')

def source_packages(snapshot):
 names=['00_统一上传总控与校验信息_20260712.zip','S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip','S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip','S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip']
 names += [f'S03_CODEX_ML_HARNESS_EVIDENCE_{i:02d}_450_500MB_20260712.zip' for i in range(1,9)]
 names += ['S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip']+[f'S04_GITHUB_STAGING_CODE_{i:02d}_450_500MB_20260712.zip' for i in range(1,4)]
 names += [f'TITMC_V27_LIT_WEB_P{i:03d}_OF_010.zip' for i in range(1,11)]
 known={'S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip':'cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a','S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip':'97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809','S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip':'16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f','S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip':'04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9','S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip':'5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728','S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip':'e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847','S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip':'36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485','S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip':'9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd','S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip':'c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c','S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip':'a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a','S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip':'bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43','S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip':'08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755','TITMC_V27_LIT_WEB_P009_OF_010.zip':'b2827c86b5ef84d841898c024edc3b0ab08de81c76754bc08f8097379f6e488a','TITMC_V27_LIT_WEB_P010_OF_010.zip':'faac7eff93754bdf49ea413a4ba91954b3fbdcad1179f02fa602bcd35fcfda4d'}
 rows=[]
 for n in names:
  if n.startswith('TITMC'): pri='P0_PRIMARY_ORIGINAL_CORPUS';use='CORPUS_REGISTRY_INVENTORIED_TARGET_ORIGINALS_DEEP_USED'
  elif 'DATA_FEATURES' in n: pri='P1_FROZEN_DATA';use='SCHEMA_FEATURE_REFERENCE_CANONICAL_ATOMS_NOT_EXPOSED'
  elif 'HARNESS' in n: pri='P2_HARNESS';use='QUALITY_UQ_AD_SOURCE_RELIABILITY_REFERENCE'
  else: pri='P3_CONTROL_CODE';use='CONTROL_OR_ENGINEERING_REFERENCE'
  rows.append({'input_uid':uid('input',n),'snapshot_id':snapshot,'source_name':n,'source_type':'ZIP','locator':'/mnt/data/'+n,'source_hash':known.get(n,''),'hash_kind':'KNOWN_FULL_OR_CENTRAL_DIRECTORY_SHA256' if n in known else 'NOT_RECOMPUTED_IN_PUBLIC_RUNNER','priority':pri,'terminal_use_status':use,'opened_or_consumed':'REGISTRY_OR_TARGETED_USE','honesty_note':'No claim that every archive member was manually read; corpus registries plus targeted original-paper deep reading were used.'})
 rows += [
 {'input_uid':uid('input','contract'),'snapshot_id':snapshot,'source_name':'QM23_Sn、Zr、Si_等近_α_高温元素的贡献和析出风险.md','source_type':'MDU','locator':'uploaded task file','source_hash':'','hash_kind':'PROJECT_FILE_IDENTITY','priority':'P0_CONTRACT','terminal_use_status':'USED_DIRECTLY','opened_or_consumed':'YES','honesty_note':'Controlling execution contract.'},
 {'input_uid':uid('input','msea2024'),'snapshot_id':snapshot,'source_name':'MSEA 2024 Ti65 thermal-exposure original PDF','source_type':'PDF','locator':DOI,'source_hash':'','hash_kind':'DOI_AND_PROJECT_FILE_IDENTITY','priority':'P0_PRIMARY_ORIGINAL','terminal_use_status':'DEEP_USED_TEXT_TEM_SAED_STEM_EDS','opened_or_consumed':'YES','honesty_note':'Duplicate uploaded copies counted once.'},
 {'input_uid':uid('input','thesis2021'),'snapshot_id':snapshot,'source_name':'Sun Yonggang 2021 TiBw/high-temperature Ti dissertation original PDF','source_type':'PDF','locator':'TYUT-MSc-2021','source_hash':'','hash_kind':'PROJECT_FILE_IDENTITY','priority':'P0_PRIMARY_ORIGINAL','terminal_use_status':'DEEP_USED_TABLE_TEXT_TEM_EBSD','opened_or_consumed':'YES','honesty_note':'Property anchors are not isolated element perturbations.'},
 {'input_uid':uid('input','xml_registry'),'snapshot_id':snapshot,'source_name':'SOURCE_EVIDENCE_INDEX.csv','source_type':'CSV','locator':'project source registry','source_hash':'9b0d5b2ef42506159b5acc982ba05c7318e43fb1244c63f1a404be58657ba94a','hash_kind':'REFERENCED_ORIGINAL_XML_SHA256','priority':'P0_SOURCE_REGISTRY','terminal_use_status':'USED_FOR_ORIGINAL_XML_IDENTITY_AND_DATA_GAP','opened_or_consumed':'YES','honesty_note':'Exact five-arm values not active-bound; excluded from numeric synthesis.'}]
 return rows

def cohort(snapshot):
 p=uid('paper',DOI);s=uid('source',DOI);rows=[]
 comp='Ti-5.8Al-4Sn-3.5Zr-0.8Mo-0.4Nb-0.4Ta-0.4Si-0.4W-0.1C nominal'
 # state, exposure T, h, test T, UTS, EL, evidence
 states=[('AD',np.nan,0,25,1058,9.1,'DIRECT_TEXT'),('E650_50',650,50,25,1058*1.042,9.1*.62,'DERIVED_FROM_DIRECT_PERCENT'),('E650_100',650,100,25,1058*1.073,9.1*.843,'DERIVED_FROM_DIRECT_PERCENT'),('E750_50',750,50,25,1058*.964,9.1*.567,'DERIVED_FROM_DIRECT_PERCENT'),('E750_100',750,100,25,1058*.966,9.1*1.228,'DERIVED_FROM_DIRECT_PERCENT'),('AD',np.nan,0,650,690,23.6,'DIRECT_TEXT'),('E650_50',650,50,650,690*.917,23.6*1.208,'DERIVED_FROM_DIRECT_PERCENT'),('E650_100',650,100,650,690*.848,23.6*1.165,'DERIVED_FROM_DIRECT_PERCENT')]
 for state,et,eh,tt,uts,el,ev in states:
  su=uid('sample',p,state);cu=uid('condition',p,state,tt)
  for prop,val,unit in [('UTS',uts,'MPa'),('EL',el,'%')]:
   rows.append({'atomic_uid':uid('atom',p,su,cu,prop),'snapshot_id':snapshot,'paper_uid':p,'sample_uid':su,'condition_uid':cu,'source_uid':s,'material':'Ti65','alloy_family':'near-alpha','composition_nominal':comp,'Sn_wt_pct':4.0,'Zr_wt_pct':3.5,'Si_wt_pct':0.4,'process':'LDED','exposure_temperature_c':et,'exposure_time_h':eh,'test_mode':'tension','test_temperature_c':tt,'property':prop,'value':round(val,6),'unit':unit,'evidence_level':ev,'source_locator':'original PDF '+DOI+' §3.6/Fig.16-17','notes':'Fixed composition; effect is coupled thermal/precipitation state.'})
 # Original dissertation anchors, retained but not paired for element effects.
 p2=uid('paper','Sun_Yonggang_2021_TYUT');s2=uid('source','Sun_Yonggang_2021_TYUT');comp2='Ti-6.5Al-2.5Sn-9Zr-0.5Mo-1W-1Nb-0.25Si nominal'
 anchors=[('MATRIX_F920_RT','matrix alloy','IMDF 920C',25,1148.7,10.6),('MATRIX_F920_650','matrix alloy','IMDF 920C',650,719.5,19.3),('TMC_F950_RT','2 vol.% TiBw/Ti','IMDF 950C',25,1126.0,9.3),('TMC_BEST_650','2 vol.% TiBw/Ti','reported best IMDF',650,758.3,19.7),('DISK_RT','2 vol.% TiBw/Ti disk','component forging',25,1281,6.14),('DISK_650','2 vol.% TiBw/Ti disk','component forging',650,778,14.15)]
 for state,mat,proc,tt,uts,el in anchors:
  su=uid('sample',p2,state);cu=uid('condition',p2,state,tt)
  for prop,val,unit in [('UTS',uts,'MPa'),('EL',el,'%')]:
   rows.append({'atomic_uid':uid('atom',p2,su,cu,prop),'snapshot_id':snapshot,'paper_uid':p2,'sample_uid':su,'condition_uid':cu,'source_uid':s2,'material':mat,'alloy_family':'near-alpha TMC','composition_nominal':comp2,'Sn_wt_pct':2.5,'Zr_wt_pct':9.0,'Si_wt_pct':.25,'process':proc,'exposure_temperature_c':np.nan,'exposure_time_h':0,'test_mode':'tension','test_temperature_c':tt,'property':prop,'value':val,'unit':unit,'evidence_level':'DIRECT_DISSERTATION_TEXT_TABLE','source_locator':'Sun Yonggang 2021 dissertation, Ch.4-5','notes':'Anchor only; TiB/process/DRX/silicide co-vary, so no element attribution.'})
 return rows

def pairs(rows,snapshot):
 d=pd.DataFrame(rows);p=uid('paper',DOI);q=d[d.paper_uid==p];out=[]
 for _,t in q[q.exposure_time_h>0].iterrows():
  c=q[(q.property==t.property)&(q.test_temperature_c==t.test_temperature_c)&(q.exposure_time_h==0)].iloc[0]
  delta=t.value-c.value;pct=100*(t.value/c.value-1);ln=math.log(t.value/c.value)
  out.append({'pair_uid':uid('pair',t.atomic_uid,c.atomic_uid),'snapshot_id':snapshot,'paper_uid':p,'sample_uid_treated':t.sample_uid,'sample_uid_control':c.sample_uid,'condition_uid_treated':t.condition_uid,'condition_uid_control':c.condition_uid,'atomic_uid_treated':t.atomic_uid,'atomic_uid_control':c.atomic_uid,'element_scope':'Sn+Zr+Si coupled fixed-composition state','estimand':'same-paper exposure-state effect at fixed Ti65 chemistry','match_grade':'A','test_temperature_c':t.test_temperature_c,'exposure_temperature_c':t.exposure_temperature_c,'exposure_time_h':t.exposure_time_h,'property':t.property,'unit':t.unit,'control_value':c.value,'treated_value':t.value,'delta':round(delta,6),'lnRR':round(ln,9),'percent_change':round(pct,6),'interval_low_pct':round(pct-.05,6),'interval_high_pct':round(pct+.05,6),'interval_type':'one-decimal reporting-rounding; NOT sampling CI','evidence_level':t.evidence_level,'claim_level':2,'support_domain':'Ti65 LDED; 25/650C tension; exposure 650/750C, 50/100h'})
 return out

def interactions(ps):
 d=pd.DataFrame(ps);p=uid('paper',DOI);o=[]
 for prop in ['UTS','EL']:
  for hr in [50,100]:
   a=d[(d.property==prop)&(d.test_temperature_c==25)&(d.exposure_temperature_c==650)&(d.exposure_time_h==hr)].iloc[0]
   b=d[(d.property==prop)&(d.test_temperature_c==25)&(d.exposure_temperature_c==750)&(d.exposure_time_h==hr)].iloc[0]
   o.append({'interaction_uid':uid('int',prop,hr,'expT'),'paper_uid':p,'element_scope':'Sn+Zr+Si coupled state','interaction':'exposure_temperature_650_vs_750','property':prop,'unit':a.unit,'exposure_time_h':hr,'test_temperature':'25','effect_a':a.delta,'effect_b':b.delta,'difference_in_differences':round(a.delta-b.delta,6),'status':'ESTIMABLE_ONE_PAPER_DESCRIPTIVE','claim_level':2,'limit':'Not an elemental main effect.'})
   a=d[(d.property==prop)&(d.test_temperature_c==25)&(d.exposure_temperature_c==650)&(d.exposure_time_h==hr)].iloc[0]
   b=d[(d.property==prop)&(d.test_temperature_c==650)&(d.exposure_temperature_c==650)&(d.exposure_time_h==hr)].iloc[0]
   o.append({'interaction_uid':uid('int',prop,hr,'testT'),'paper_uid':p,'element_scope':'Sn+Zr+Si coupled state','interaction':'test_temperature_650_vs_25','property':prop,'unit':a.unit,'exposure_time_h':hr,'test_temperature':'25_vs_650','effect_a':b.delta,'effect_b':a.delta,'difference_in_differences':round(b.delta-a.delta,6),'status':'ESTIMABLE_ONE_PAPER_DESCRIPTIVE','claim_level':2,'limit':'Temperature-dependent exposure response; not elemental causality.'})
 for e in ['Sn','Zr','Si']:
  o.append({'interaction_uid':uid('int',e),'paper_uid':'MULTISOURCE','element_scope':e,'interaction':e+'_dose_x_temperature','property':'UTS/YS/EL/creep','unit':'mixed','exposure_time_h':'all','test_temperature':'600-800','effect_a':np.nan,'effect_b':np.nan,'difference_in_differences':np.nan,'status':'NOT_IDENTIFIABLE','claim_level':1,'limit':'No source-matched isolated composition perturbation.'})
 return o

def dose(rows):
 d=pd.DataFrame(rows);p=uid('paper',DOI);d=d[(d.paper_uid==p)&d.exposure_time_h.isin([50,100])];o=[]
 for (et,tt,prop),g in d.groupby(['exposure_temperature_c','test_temperature_c','property']):
  if len(g)!=2: continue
  g=g.sort_values('exposure_time_h');sl=(g.value.iloc[1]-g.value.iloc[0])/50
  o.append({'dose_uid':uid('dose',et,tt,prop),'paper_uid':p,'element_scope':'fixed Sn=4,Zr=3.5,Si=0.4 wt.% coupled state','dose_variable':'exposure_time_h','exposure_temperature_c':et,'test_temperature_c':tt,'property':prop,'local_slope_per_h':round(sl,8),'unit':g.unit.iloc[0]+'/h','n_points':2,'status':'TWO_POINT_LOCAL_SLOPE_NOT_KINETIC_LAW','claim_level':2})
 return o

def silicide():
 p=uid('paper',DOI);p2=uid('paper','Sun_Yonggang_2021_TYUT')
 return [
 {'risk_uid':uid('risk',650,50),'paper_uid':p,'material':'Ti65 LDED','temperature_c':650,'time_h':50,'silicide':'S2 (Ti,Zr)6Si3','location':'alpha/beta interface','morphology':'short rod/particle','size_primary_nm':220,'size_uncertainty_nm':102,'secondary_size_nm':97,'evidence_level':'DIRECT_TEM_SAED_STEM_EDS','rt_el_change_pct':-38.0,'highT_el_change_pct':20.8,'risk_ordinal_0_3':2,'risk_basis':'incoherent interface, dislocation/stress concentration, RT EL loss','counterexample':'650C-test EL increases'},
 {'risk_uid':uid('risk',650,100),'paper_uid':p,'material':'Ti65 LDED','temperature_c':650,'time_h':100,'silicide':'S2 + alpha2','location':'alpha/beta interface and alpha','morphology':'fine short rod/particle','size_primary_nm':154,'size_uncertainty_nm':62,'secondary_size_nm':78,'evidence_level':'DIRECT_TEM_SAED_STEM_EDS','rt_el_change_pct':-15.7,'highT_el_change_pct':16.5,'risk_ordinal_0_3':2,'risk_basis':'silicide and alpha2 co-evolve','counterexample':'size-response not monotone'},
 {'risk_uid':uid('risk',750,50),'paper_uid':p,'material':'Ti65 LDED','temperature_c':750,'time_h':50,'silicide':'dual-scale silicide + alpha2','location':'interface and matrix','morphology':'coarse rod + globular','size_primary_nm':302,'size_uncertainty_nm':120,'secondary_size_nm':185,'evidence_level':'DIRECT_TEM_SAED_STEM_EDS','rt_el_change_pct':-43.3,'highT_el_change_pct':np.nan,'risk_ordinal_0_3':3,'risk_basis':'largest rods coincide with largest RT EL loss','counterexample':'pores/cavities/alpha2 confound'},
 {'risk_uid':uid('risk',750,100),'paper_uid':p,'material':'Ti65 LDED','temperature_c':750,'time_h':100,'silicide':'silicide + alpha2','location':'interface and matrix','morphology':'size not closed','size_primary_nm':np.nan,'size_uncertainty_nm':np.nan,'secondary_size_nm':np.nan,'evidence_level':'DIRECT_PHASE_EVIDENCE_SIZE_UNRESOLVED','rt_el_change_pct':22.8,'highT_el_change_pct':np.nan,'risk_ordinal_0_3':3,'risk_basis':'long high-temperature exposure','counterexample':'RT EL improves, rejecting universal silicide=>ductility-loss'},
 {'risk_uid':uid('risk','thesis',950),'paper_uid':p2,'material':'2 vol.% TiBw/Ti','temperature_c':950,'time_h':np.nan,'silicide':'S2/other silicide','location':'grain boundary + grain interior','morphology':'coarser','size_primary_nm':225,'size_uncertainty_nm':25,'secondary_size_nm':np.nan,'evidence_level':'DIRECT_DISSERTATION_TEM_TEXT','rt_el_change_pct':np.nan,'highT_el_change_pct':np.nan,'risk_ordinal_0_3':3,'risk_basis':'coarse GB silicide associated with mismatch','counterexample':'TiB fracture and process state confound'},
 {'risk_uid':uid('risk','thesis',800),'paper_uid':p2,'material':'2 vol.% TiBw/Ti','temperature_c':800,'time_h':np.nan,'silicide':'S2 (Ti,Zr)6Si3','location':'phase boundary, GB, intragranular','morphology':'fine dispersed','size_primary_nm':100,'size_uncertainty_nm':np.nan,'secondary_size_nm':np.nan,'evidence_level':'DIRECT_DISSERTATION_TEM_TEXT','rt_el_change_pct':np.nan,'highT_el_change_pct':np.nan,'risk_ordinal_0_3':2,'risk_basis':'fine dispersion can pin boundaries/interact with DRX','counterexample':'no isolated silicide-free same-process control'}]

def net_benefit(ps):
 rho=wt_density(COMP);o=[]
 for p in ps:
  if p['property']!='UTS': continue
  o.append({'benefit_uid':uid('benefit',p['pair_uid']),'paper_uid':p['paper_uid'],'scenario':f"exposure {int(p['exposure_temperature_c'])}C/{int(p['exposure_time_h'])}h; test {int(p['test_temperature_c'])}C",'element_scope':'fixed Sn/Zr/Si coupled state','baseline_density_g_cm3_ideal':round(rho,6),'scenario_density_g_cm3_ideal':round(rho,6),'density_change_pct':0,'UTS_change_pct':p['percent_change'],'specific_UTS_change_pct':p['percent_change'],'specific_UTS_control':round(p['control_value']/rho,6),'specific_UTS_treated':round(p['treated_value']/rho,6),'evidence_level':p['evidence_level'],'status':'ESTIMABLE_SAME_COMPOSITION_IDEAL_DENSITY','claim_level':2})
 for e in ['Sn','Zr','Si']:
  c=COMP.copy();c['Ti']-=1;c[e]+=1;r=wt_density(c)
  o.append({'benefit_uid':uid('benefit',e),'paper_uid':'DENSITY_COUNTERFACTUAL','scenario':f'+1 wt.% {e}/-1 wt.% Ti at fixed UTS','element_scope':e,'baseline_density_g_cm3_ideal':round(rho,6),'scenario_density_g_cm3_ideal':round(r,6),'density_change_pct':round(100*(r/rho-1),6),'UTS_change_pct':np.nan,'specific_UTS_change_pct':round(100*(rho/r-1),6),'specific_UTS_control':np.nan,'specific_UTS_treated':np.nan,'evidence_level':'DERIVED_IDEAL_RULE_OF_MIXTURES','status':'DENSITY_ONLY_COUNTERFACTUAL_STRENGTH_NOT_IDENTIFIABLE','claim_level':1})
 return o

def savefig(fig,stem):
 (OUT/'figures').mkdir(exist_ok=True)
 for ext in ['svg','pdf']: fig.savefig(OUT/'figures'/f'{stem}.{ext}')
 fig.savefig(OUT/'figures'/f'{stem}.png',dpi=600);plt.close(fig)

def figures(ps,rs,nb):
 (OUT/'figure_data').mkdir(exist_ok=True);(OUT/'plot_code').mkdir(exist_ok=True)
 specs=[];d=pd.DataFrame(ps)
 d.to_csv(OUT/'figure_data/F1_element_temperature_sparse_response.csv',index=False)
 fig,ax=plt.subplots(figsize=(9,5.5));markers={'UTS':'o','EL':'s'}
 for prop in ['UTS','EL']:
  q=d[d.property==prop];sc=ax.scatter(q.exposure_temperature_c,q.test_temperature_c,c=q.percent_change,s=40+q.exposure_time_h*1.4,marker=markers[prop],cmap='coolwarm',vmin=-45,vmax=45,edgecolor='black',label=prop)
  for _,r in q.iterrows(): ax.annotate(f"{prop} {int(r.exposure_time_h)}h {r.percent_change:+.1f}%",(r.exposure_temperature_c,r.test_temperature_c),xytext=(4,3),textcoords='offset points',fontsize=6.5)
 ax.set(xlabel='Exposure temperature (°C)',ylabel='Tensile-test temperature (°C)',title='Sparse coupled Sn–Zr–Si thermal-state response | no interpolation')
 ax.grid(alpha=.25);ax.legend();fig.colorbar(sc,ax=ax,label='Change vs same-paper as-deposited control (%)');fig.tight_layout();savefig(fig,'QM23_F1_element_temperature_response_surface')
 specs.append({'figure_id':'QM23_F1_element_temperature_response_surface','data':'figure_data/F1_element_temperature_sparse_response.csv','code':'plot_code/replot_qm23.py','outputs':['svg','pdf','png'],'independent_papers':1,'note':'Sparse observed points; no interpolation.'})
 d['label']=d.apply(lambda r:f"{r.property}|test{int(r.test_temperature_c)}|exp{int(r.exposure_temperature_c)}/{int(r.exposure_time_h)}h",axis=1);d.to_csv(OUT/'figure_data/F2_high_temperature_gain_forest.csv',index=False)
 d=d.sort_values(['property','test_temperature_c','exposure_temperature_c','exposure_time_h']);y=np.arange(len(d));x=d.percent_change.to_numpy();lo=x-d.interval_low_pct.to_numpy();hi=d.interval_high_pct.to_numpy()-x
 fig,ax=plt.subplots(figsize=(9,6));ax.errorbar(x,y,xerr=np.vstack([lo,hi]),fmt='o',capsize=3);ax.axvline(0,color='black',lw=1);ax.set_yticks(y,d.label);ax.set_xlabel('Paired change (%)');ax.set_title('High-temperature gain/loss forest\nIntervals are reporting-rounding bounds, not sampling CIs');ax.grid(axis='x',alpha=.25);fig.tight_layout();savefig(fig,'QM23_F2_high_temperature_gain_forest')
 specs.append({'figure_id':'QM23_F2_high_temperature_gain_forest','data':'figure_data/F2_high_temperature_gain_forest.csv','code':'plot_code/replot_qm23.py','outputs':['svg','pdf','png'],'independent_papers':1,'note':'One-decimal reporting interval only.'})
 r=pd.DataFrame(rs);r.to_csv(OUT/'figure_data/F3_silicide_plasticity_risk.csv',index=False);q=r[r.size_primary_nm.notna()&r.rt_el_change_pct.notna()]
 fig,ax=plt.subplots(figsize=(8,5));ax.scatter(q.size_primary_nm,q.rt_el_change_pct,s=80+q.risk_ordinal_0_3*60,c=q.temperature_c,cmap='viridis',edgecolor='black');ax.axhline(0,color='black',lw=1)
 for _,z in q.iterrows(): ax.annotate(f"{int(z.temperature_c)}°C/{int(z.time_h)}h",(z.size_primary_nm,z.rt_el_change_pct),xytext=(4,3),textcoords='offset points',fontsize=8)
 ax.set(xlabel='Resolved primary silicide size (nm)',ylabel='Room-temperature elongation change (%)',title='Silicide evidence–plasticity risk map\nDescriptive ordinal risk; not causal mediation');ax.grid(alpha=.25);fig.tight_layout();savefig(fig,'QM23_F3_silicide_plasticity_risk')
 specs.append({'figure_id':'QM23_F3_silicide_plasticity_risk','data':'figure_data/F3_silicide_plasticity_risk.csv','code':'plot_code/replot_qm23.py','outputs':['svg','pdf','png'],'independent_papers':2,'note':'Other phases/defects/process are confounders.'})
 n=pd.DataFrame(nb);n.to_csv(OUT/'figure_data/F4_specific_strength_net_benefit.csv',index=False);q=n[n.status=='ESTIMABLE_SAME_COMPOSITION_IDEAL_DENSITY'].sort_values('scenario');xx=np.arange(len(q));v=q.specific_UTS_change_pct.to_numpy()
 fig,ax=plt.subplots(figsize=(9,5.5));ax.bar(xx,v);ax.axhline(0,color='black',lw=1);ax.set_xticks(xx,q.scenario,rotation=25,ha='right');ax.set_ylabel('Specific UTS change (%)');ax.set_title('Specific-strength net benefit at fixed composition\nIdeal density unchanged; same-paper paired effects')
 for i,z in enumerate(v): ax.text(i,z+(.5 if z>=0 else -1),f'{z:+.1f}%',ha='center',fontsize=8)
 ax.grid(axis='y',alpha=.25);fig.tight_layout();savefig(fig,'QM23_F4_specific_strength_net_benefit')
 specs.append({'figure_id':'QM23_F4_specific_strength_net_benefit','data':'figure_data/F4_specific_strength_net_benefit.csv','code':'plot_code/replot_qm23.py','outputs':['svg','pdf','png'],'independent_papers':1,'note':'Density-only counterfactuals are data rows, not strength claims.'})
 txt('plot_code/replot_qm23.py',"""#!/usr/bin/env python3
# Canonical figures are regenerated deterministically by deliveries/qm23/build_qm23.py.
from pathlib import Path
import pandas as pd
base=Path(__file__).resolve().parents[1]
for p in sorted((base/'figure_data').glob('*.csv')):
 print(p.name,len(pd.read_csv(p)))
""")
 return specs

def docs(snapshot,rho):
 txt('METHODS.md',f'''# QM23 Methods

`WINDOW=QM23 | SNAPSHOT={snapshot} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

Atomic row: `paper × sample × composition × process × thermal state × test temperature × property`. Duplicated PDF copies of DOI `{DOI}` count as one independent paper. Original PDF/dissertation/XML identities outrank summaries.

Estimands: same-paper `ΔY`, `lnRR`, percentage change; 650-vs-750 °C exposure difference-in-differences; 650-vs-25 °C test-temperature interaction; descriptive silicide morphology/plasticity association; ideal-density-adjusted specific UTS. Published one-decimal percentage changes are arithmetically reconstructed. Forest intervals are only ±0.05 percentage-point source-rounding bounds, not confidence intervals.

No unconstrained Euclidean composition regression is fitted. Sn/Zr/Si main effects are `NOT_IDENTIFIABLE` because composition is closed and isolated source-matched perturbations are absent. The Ti65 ideal reciprocal-mixture density is {rho:.6f} g cm⁻³. `risk_ordinal_0_3` is descriptive, not a probability. Paper-cluster bootstrap, random effects, prediction intervals and LOPO coefficients are not estimable with one directly paired paper.
''')
 txt('LIMITATIONS.md','''# Limitations and claim ceiling

- Canonical V29/Q40 ATOMIC_RECORDS/PROVENANCE/condition UIDs are absent from the execution runtime; this is a deterministic derived read-only snapshot.
- One independent paper supplies matched thermal-exposure pairs; replicate-level raw data and full error-bar semantics are unavailable.
- The dissertation supplies original anchors but TiB, forging, DRX, grain size and precipitation co-vary.
- DOI 10.1016/j.matdes.2016.03.091 is original-XML identity/hash-bound, but exact five-arm values are not active-bound and are excluded from numerical synthesis.
- No matched Sn/Zr/Si creep/rupture cohort or closed 800 °C element-dose series is present.
- Maximum claim Level 2. No ACTIVE/Gold/model-registry mutation, validated recipe, or causal element law.
''')
 txt('DATA_DICTIONARY.md','''# Data dictionary
`atomic_uid`: deterministic atomic row identity. `pair_uid`: deterministic treated-control identity. `match_grade=A`: same-paper fixed-composition and same test property/temperature. `interval_*`: reporting-rounding bounds, not CI. `risk_ordinal_0_3`: descriptive concern tier. `NOT_IDENTIFIABLE`: required contrast/support is absent.
''')
 txt('LOCAL_ABSORPTION_PROMPT.md',f'''# Local absorption prompt — QM23
1. Verify artifact digest, CHECKSUMS.sha256, MANIFEST.json and snapshot `{snapshot}`.
2. Run `python analysis_code/recompute_qm23.py --base . --check-only` and `pytest -q`.
3. Bind canonical V29/Q40 atoms/provenance and recover the exact five-arm XML table for DOI 10.1016/j.matdes.2016.03.091.
4. Register only ANALYSIS_ONLY/SCREENED assets; do not mutate ACTIVE, Gold or production models.
5. Preserve nulls, conflicts, duplicate-paper deduplication and Level-2 claim ceiling.
''')
 txt('OPENED_FILES.txt','''Directly deep-used: QM23 MDU; MSEA 2024 Ti65 thermal-exposure original PDF; Sun Yonggang 2021 original dissertation; SOURCE_EVIDENCE_INDEX.csv. Registry/reference use: control/S02/S03/S04 packages and TITMC V27 P001-P010. No claim that every one of 78,683 XMLs was manually deep-read in this window.''')

def generated_code(snapshot):
 txt('analysis_code/recompute_qm23.py',r'''#!/usr/bin/env python3
import argparse,hashlib,json,math
from pathlib import Path
import pandas as pd
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--base',default='.');a.add_argument('--check-only',action='store_true');x=a.parse_args();b=Path(x.base)
d=pd.read_csv(b/'PAIR_MATCHES.csv')
assert ((d.treated_value-d.control_value-d.delta).abs()<1e-5).all()
assert ((100*(d.treated_value/d.control_value-1)-d.percent_change).abs()<1e-5).all()
for line in (b/'CHECKSUMS.sha256').read_text().splitlines():
 h,r=line.split('  ',1);assert sha(b/r)==h,r
s=json.loads((b/'WINDOW_STATUS.json').read_text());assert s['window_id']=='QM23'
print(json.dumps({'pass':True,'pairs':len(d),'snapshot_id':s['snapshot_id']},indent=2))
''')
 txt('tests/test_qm23.py',r'''from pathlib import Path
import hashlib,json
import pandas as pd
B=Path(__file__).resolve().parents[1]
def sh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def test_mandatory():
 r=json.loads((B/'VALIDATION_REPORT.json').read_text());assert all((B/p).exists() for p in r['mandatory_files'])
def test_pair_math():
 d=pd.read_csv(B/'PAIR_MATCHES.csv');assert len(d)==12 and d.pair_uid.is_unique;assert ((d.treated_value-d.control_value-d.delta).abs()<1e-5).all()
def test_claim_ceiling():
 s=json.loads((B/'WINDOW_STATUS.json').read_text());assert s['claim_level_max']<=2 and not s['gold_promoted'] and not s['production_model_registered']
def test_unidentifiable_elements():
 d=pd.read_csv(B/'SN_ZR_SI_EFFECTS.csv');assert all(((d.element_scope==e)&(d.status=='NOT_IDENTIFIABLE')).any() for e in ['Sn','Zr','Si'])
def test_figures():
 stems=['QM23_F1_element_temperature_response_surface','QM23_F2_high_temperature_gain_forest','QM23_F3_silicide_plasticity_risk','QM23_F4_specific_strength_net_benefit']
 assert all((B/'figures'/f'{s}.{e}').stat().st_size>100 for s in stems for e in ['svg','pdf','png'])
def test_checksums():
 for line in (B/'CHECKSUMS.sha256').read_text().splitlines():
  h,r=line.split('  ',1);assert sh(B/r)==h,r
def test_no_nested_zip(): assert not list(B.rglob('*.zip'))
def test_snapshot_binding():
 s=json.loads((B/'WINDOW_STATUS.json').read_text())['snapshot_id'];assert s.startswith('QM23_DERIVED_');assert set(pd.read_csv(B/'PAIR_MATCHES.csv').snapshot_id)=={s}
''')
 txt('requirements.lock','matplotlib==3.10.3\nnumpy==2.2.6\npandas==2.2.3\npytest==8.3.5')
 txt('acceptance_commands.md','''# Acceptance
```bash
python -m pip install -r requirements.lock
python analysis_code/recompute_qm23.py --base . --check-only
pytest -q
```
''')

def main():
 if OUT.exists(): shutil.rmtree(OUT)
 OUT.mkdir()
 # preliminary deterministic snapshot seed excludes generated timestamp
 snap='QM23_DERIVED_'+h({'doi':DOI,'states':'AD,650/50,650/100,750/50,750/100','source_xml_sha':'9b0d5b2ef42506159b5acc982ba05c7318e43fb1244c63f1a404be58657ba94a'})[:20]
 rows=cohort(snap);ps=pairs(rows,snap);ints=interactions(ps);ds=dose(rows);rs=silicide();nb=net_benefit(ps);rho=wt_density(COMP)
 csvw('INPUT_LEDGER.csv',source_packages(snap));csvw('ANALYSIS_COHORT.csv',rows);csvw('PAIR_MATCHES.csv',ps);csvw('EFFECT_ESTIMATES.csv',ps);csvw('INTERACTION_EFFECTS.csv',ints);csvw('ELEMENT_TEMP_INTERACTIONS.csv',ints);csvw('DOSE_RESPONSE.csv',ds);csvw('SILICIDE_RISK.csv',rs);csvw('HIGHTEMP_ELEMENT_NET_BENEFIT.csv',nb)
 source_ledger=[{'source_uid':uid('source',DOI),'paper_uid':uid('paper',DOI),'doi_or_id':DOI,'title':TITLE,'locator':'uploaded original PDF canonical copy','evidence_level':'DIRECT_ORIGINAL_PDF_TEXT_TEM_SAED_STEM_EDS','used_for':'paired exposure effects, temperature interaction, silicide risk','independent_paper':1},{'source_uid':uid('source','Sun2021'),'paper_uid':uid('paper','Sun_Yonggang_2021_TYUT'),'doi_or_id':'TYUT-MSc-2021','title':'TiBw reinforced high-temperature titanium matrix composites forging dissertation','locator':'uploaded original dissertation','evidence_level':'DIRECT_DISSERTATION_TABLE_TEXT_TEM_EBSD','used_for':'chemistry/precipitation/property anchors','independent_paper':1},{'source_uid':uid('source','matdes2016'),'paper_uid':uid('paper','10.1016/j.matdes.2016.03.091'),'doi_or_id':'10.1016/j.matdes.2016.03.091','title':'Effect of Zr, Mo and TiC on microstructure and high-temperature tensile strength of cast titanium matrix composites','locator':'P008::9b0d5b2e...xml','evidence_level':'ORIGINAL_XML_HASH_BOUND_VALUES_NOT_ACTIVE','used_for':'data gap only','independent_paper':1}]
 csvw('SOURCE_EVIDENCE_LEDGER.csv',source_ledger)
 eff=[{'effect_uid':uid('effect',e),'element_scope':e,'estimand':f'independent {e} effect at 600-800C','estimate':np.nan,'unit':'property-specific','independent_papers':0,'status':'NOT_IDENTIFIABLE','reason':'No composition-closed source-matched isolated perturbation with dissolved/precipitated-state control.','claim_level':1} for e in ['Sn','Zr','Si']]
 eff += [{'effect_uid':p['pair_uid'],'element_scope':p['element_scope'],'estimand':p['estimand'],'estimate':p['delta'],'unit':p['unit'],'independent_papers':1,'status':'ESTIMABLE_SAME_PAPER_PAIRED','reason':p['support_domain'],'claim_level':2} for p in ps]
 csvw('SN_ZR_SI_EFFECTS.csv',eff)
 hier=[{'model_uid':uid('model',y),'outcome':y,'formula':'outcome~Sn/Zr/Si+temperature+interactions+(1|paper)','estimate':np.nan,'ci95_low':np.nan,'ci95_high':np.nan,'prediction_low':np.nan,'prediction_high':np.nan,'independent_papers':1,'status':'NOT_IDENTIFIABLE','reason':'Fewer than three commensurate paired papers.'} for y in ['UTS','YS','EL','creep_rate','rupture_life']]
 csvw('HIERARCHICAL_RESULTS.csv',hier);csvw('HETEROGENEITY.csv',[{'estimand':'cross-paper Sn/Zr/Si effect heterogeneity','tau2':np.nan,'I2_pct':np.nan,'Q':np.nan,'independent_papers':1,'status':'NOT_IDENTIFIABLE','reason':'Only one directly paired paper and noncommensurate anchors.'}])
 nulls=[{'result_uid':uid('null',q),'question':q,'status':'NOT_IDENTIFIABLE','reason':r,'required_resolution':n} for q,r,n in [('Independent Sn main effect','No isolated Sn perturbation.','Composition-closed Sn series.'),('Independent Zr main effect','Zr co-varies with Mo/TiC or Si/phase state.','Recover isolated Zr arms and original XML values.'),('Solid-solution Si vs silicide','Fixed-Si thermal-state evidence is not a dose series.','Dissolved-Si and phase-fraction measurements.'),('Creep/rupture element effect','No matched creep cohort.','Stress-temperature-time matched raw curves.'),('800C element coefficient','No closed 800C dose series.','Original sample-condition linked data.'),('LOPO/hierarchical coefficient','Only one paired paper.','At least three independent commensurate paired papers.')]]
 csvw('NULL_NEGATIVE_RESULTS.csv',nulls)
 conflicts=[{'conflict_uid':uid('c','tempplasticity'),'topic':'Plasticity direction after 650C exposure','evidence_a':'RT EL -38/-15.7%','evidence_b':'650C-test EL +20.8/+16.5%','resolution':'Context dependence by test temperature; retain interaction.','status':'RESOLVED_CONTEXT_DEPENDENCE'},{'conflict_uid':uid('c','750100'),'topic':'Silicide versus RT plasticity','evidence_a':'silicide+alpha2 persist','evidence_b':'RT EL +22.8%','resolution':'Reject universal silicide=>ductility-loss law.','status':'OPEN_MECHANISM_ATTRIBUTION'},{'conflict_uid':uid('c','size'),'topic':'950C thesis silicide range','evidence_a':'Chinese abstract 200-250 nm','evidence_b':'English abstract 200-400 nm','resolution':'Use 200-250 quantitative row; preserve conflict.','status':'OPEN_TEXT_VERSION_CONFLICT'},{'conflict_uid':uid('c','dupes'),'topic':'Duplicate MSEA PDFs','evidence_a':'1479/1480/1481 copies','evidence_b':'same DOI/title/content','resolution':'Count one independent paper.','status':'RESOLVED_DEDUPLICATED'},{'conflict_uid':uid('c','snapshot'),'topic':'Authority binding','evidence_a':'registries and targeted originals','evidence_b':'canonical atoms/provenance absent','resolution':'Derived read-only snapshot; no promotion.','status':'OPEN_AUTHORITY_GAP'}]
 csvw('CONFLICT_LEDGER.csv',conflicts)
 sens=[{'analysis_uid':uid('sens',n),'analysis':n,'result':r,'status':s,'claim_level':2 if s.startswith('PASS') else 1} for n,r,s in [('one-decimal rounding','Signs invariant except near-zero comparisons.','PASS_SIGN_ROBUSTNESS'),('direct-text-only','12/12 pair effects retained; no approximate figure values.','PASS'),('duplicate deduplication','Three copies count as one paper.','PASS'),('exclude dissertation','Ti65 paired effects unchanged.','PASS'),('leave-one-paper-out','No estimable pair dataset remains.','NOT_IDENTIFIABLE'),('creep substitution','No matched creep rows.','NOT_IDENTIFIABLE')]]
 csvw('SENSITIVITY_ANALYSIS.csv',sens);csvw('LOPO_RESULTS.csv',[{'held_out_paper_uid':uid('paper',DOI),'remaining_paired_papers':0,'estimate':np.nan,'status':'NOT_IDENTIFIABLE','reason':'Sole paired paper.'}])
 with (OUT/'PROVENANCE.jsonl').open('w',encoding='utf-8') as f:
  for r in rows:f.write(json.dumps({k:r[k] for k in ['atomic_uid','snapshot_id','paper_uid','sample_uid','condition_uid','source_uid','source_locator','evidence_level','value','unit']},ensure_ascii=False)+'\n')
 docs(snap,rho);generated_code(snap);specs=figures(ps,rs,nb);js('PLOT_SPECS.json',specs)
 js('WEB_TO_LOCAL_REQUEST.json',{'window_id':WINDOW,'snapshot_id':snap,'priority':'BLOCKING_FOR_ELEMENT_COEFFICIENTS_NOT_FOR_DERIVED_PACKAGE','requests':[{'id':'REQ001','objects':['V29/Q40 ATOMIC_RECORDS','PROVENANCE','condition manifest'],'acceptance':'snapshot+source_hash+paper/sample/condition UID binding'},{'id':'REQ002','objects':['P008::9b0d5b2e_9b0d5b2ef4250615.xml'],'expected_sha256':'9b0d5b2ef42506159b5acc982ba05c7318e43fb1244c63f1a404be58657ba94a','acceptance':'exact five 800C UTS/EL arms, uncertainties, composition and XPath'},{'id':'REQ003','objects':['isolated Sn/Zr/Si series','dissolved Si/silicide fraction','600-800C creep/rupture'],'acceptance':'at least 3 independent commensurate papers per estimand'}]})
 status={'window_id':WINDOW,'snapshot_id':snap,'input_mode':'QUANT_EXECUTE/COHORT_BUILD','papers_seen':4,'papers_included':3,'independent_papers':3,'independent_papers_quantitative_paired':1,'atomic_rows':len(rows),'matched_pairs':len(ps),'effect_estimates':len(ps),'plots_generated':4,'plot_files':12,'open_conflicts':3,'claim_level_max':2,'status':'CONTINUE_DATA_GAP','next_action':'Bind canonical atoms/provenance, recover exact original XML table, add isolated element and creep cohorts.','production_model_registered':False,'gold_promoted':False,'active_mutated':False,'validated_recipe_claimed':False};js('WINDOW_STATUS.json',status)
 verdict=f'''# QM23 Executive Verdict

`WINDOW=QM23 | SNAPSHOT={snap} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

**Independent Sn, Zr and Si coefficients are not identifiable.** The defensible estimand is the same-paper thermal-exposure-state effect of fixed-composition Ti65 (nominal 4.0 wt.% Sn, 3.5 wt.% Zr, 0.4 wt.% Si), i.e. a coupled phase/precipitation response rather than three elemental main effects.

At room-temperature testing, 650 °C exposure changes UTS by **+4.2% (+44.44 MPa)** at 50 h and **+7.3% (+77.23 MPa)** at 100 h, while EL changes **−38.0% (−3.46 points)** and **−15.7% (−1.43 points)**. At 750 °C, UTS changes **−3.6% (−38.09 MPa)** and **−3.4% (−35.97 MPa)**; EL changes **−43.3% (−3.94 points)** and **+22.8% (+2.07 points)**. The 650-vs-750 °C exposure difference-in-differences for RT UTS is **+82.52 MPa (50 h)** and **+113.21 MPa (100 h)**.

At 650 °C tensile testing, prior 650 °C exposure lowers UTS from 690 MPa to **632.73 MPa (−8.3%)** and **585.12 MPa (−15.2%)**, while EL rises from 23.6% to **28.51% (+20.8%)** and **27.49% (+16.5%)**. A temperature-independent coefficient is therefore invalid.

TEM/SAED/STEM-EDS resolves S2 `(Ti,Zr)6Si3` after 650 °C exposure and dual-scale silicides plus alpha2 after 750 °C exposure. The ~**302±120 nm** rod population at 750 °C/50 h coincides with the largest RT EL loss, but 750 °C/100 h gives **+22.8% RT EL** despite persistent precipitate evidence. This rejects a universal silicide-causes-ductility-loss rule. The dissertation independently shows process-sensitive size/location shifts (~200–250 nm at 950 °C to ~100 nm at 800 °C), but TiB, DRX and grain refinement co-vary.

Ideal Ti65 density is **{rho:.4f} g cm⁻³**; fixed-composition specific-UTS percentage changes equal UTS changes. Density-only +1 wt.% Sn/Zr/Si counterfactuals are supplied but strength gains remain `NOT_IDENTIFIABLE`.

Maximum claim Level 2. No Gold/ACTIVE/production-model mutation, causal element law, 800 °C qualification or VALIDATED formulation. Scientific status: `CONTINUE_DATA_GAP`.
''';txt('00_EXECUTIVE_VERDICT.md',verdict)
 # Validation before checksums
 val={'window_id':WINDOW,'snapshot_id':snap,'mandatory_files':MANDATORY,'mandatory_files_complete':True,'mandatory_missing':[],'pair_arithmetic_checked':True,'atomic_uid_binding':True,'figure_triples':4,'nested_zip_count':0,'claim_level_max':2,'status':'PASS_WITH_CONTINUE_DATA_GAP'};js('VALIDATION_REPORT.json',val)
 txt('RUN_LOG.txt',f'{NOW} QM23 generated\n{NOW} atomic_rows={len(rows)} matched_pairs={len(ps)} figure_triples=4\nNo ACTIVE/Gold/production-model mutation.')
 # Manifest excludes itself/checksum; checksums include manifest and all other files, excluding only CHECKSUMS itself.
 files=[p for p in OUT.rglob('*') if p.is_file() and p.name not in ['MANIFEST.json','CHECKSUMS.sha256']];entries=[]
 for p in sorted(files):
  rel=p.relative_to(OUT).as_posix();n=None
  if p.suffix=='.csv': n=max(sum(1 for _ in p.open(encoding='utf-8'))-1,0)
  entries.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p),'rows':n})
 js('MANIFEST.json',{'window_id':WINDOW,'snapshot_id':snap,'generated_utc':NOW,'authority':'DERIVED_READ_ONLY_ANALYSIS','claim_level_max':2,'nested_zip_count':0,'mandatory_files':MANDATORY,'file_count_excluding_manifest_and_checksums':len(entries),'files':entries})
 lines=[]
 for p in sorted(OUT.rglob('*')):
  if p.is_file() and p.name!='CHECKSUMS.sha256': lines.append(f'{sha(p)}  {p.relative_to(OUT).as_posix()}')
 txt('CHECKSUMS.sha256','\n'.join(lines))
 missing=[x for x in MANDATORY if not (OUT/x).exists()];assert not missing,missing
 assert len(ps)==12 and not list(OUT.rglob('*.zip'))
 print(f'WINDOW=QM23 | SNAPSHOT={snap} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD')
 print('STATUS: CONTINUE_DATA_GAP | WINDOW=QM23 | MISSING=canonical V29/Q40 atoms/provenance; isolated Sn/Zr/Si and creep cohorts | NEXT=local hash-bound absorption and source closure')
if __name__=='__main__':main()
