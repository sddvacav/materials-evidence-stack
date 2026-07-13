#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, shutil, subprocess, sys, textwrap
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'artifact'
if OUT.exists(): shutil.rmtree(OUT)
for d in ['figure_data','plot_code','figures','analysis_code','tests']: (OUT/d).mkdir(parents=True,exist_ok=True)
NOW=datetime.now(timezone.utc).isoformat()
WINDOW='QM05'; BATCH='V30_TITMC_Q40_20260713'

def wtext(rel,s):
 p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(str(s).rstrip()+'\n',encoding='utf-8')
def wjson(rel,o): wtext(rel,json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True))
def wcsv(rel,cols,rows):
 p=OUT/rel; p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8',newline='') as f:
  x=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); x.writeheader()
  for r in rows: x.writerow({c:r.get(c,'') for c in cols})
def hfile(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

# All 26 uploaded package central directories were opened before the execution runtime reset.
specs=[
('00_统一上传总控与校验信息_20260712.zip',13,'CONTROL','',''),
('S02_PLATFORM_CORE_WEB_RETURN_PLOT_CODE_450_500MB_20260712.zip',32,'PLATFORM_CODE','',''),
('S03_CODEX_ML_DATA_FEATURES_01_450_500MB_20260712.zip',15,'FROZEN_DATA','',''),
('S03_CODEX_ML_DATA_FEATURES_02_450_500MB_20260712.zip',25,'FROZEN_DATA','',''),
('S03_CODEX_ML_HARNESS_EVIDENCE_01_450_500MB_20260712.zip',7,'HARNESS','cf3d8e2fbc5be40e12c19b850af977f6884556442aa59676ba95b55cdeadbc3a','FULL_FILE_SHA256'),
('S03_CODEX_ML_HARNESS_EVIDENCE_02_450_500MB_20260712.zip',7,'HARNESS','97d15f6de609eae14cd3026a49e72cd9cd2e5c3464ca060a3d6d5cda669b2809','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S03_CODEX_ML_HARNESS_EVIDENCE_03_450_500MB_20260712.zip',9,'HARNESS','16019caeb61ad857a48a95cf42a1c96438593e7cb02ff21b934a2d9562d6316f','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S03_CODEX_ML_HARNESS_EVIDENCE_04_450_500MB_20260712.zip',11,'HARNESS','04184a08b67516bb4fc4ec0ec9dee526821f302489f5a96ea6418a6fa56c24a9','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S03_CODEX_ML_HARNESS_EVIDENCE_05_450_500MB_20260712.zip',17,'HARNESS','5ffe8e7a0be2638f42b10fb0ac870f8c8ea15524b00d86977c82a45bd336d728','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S03_CODEX_ML_HARNESS_EVIDENCE_06_450_500MB_20260712.zip',38,'HARNESS','e41b52604a26aab1e665b7a2ddde6487bfd396a3a66eca465577ff1ce4e51847','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S03_CODEX_ML_HARNESS_EVIDENCE_07_450_500MB_20260712.zip',69,'HARNESS','36cd504237f79f81acc45b0cd1994a4849376704e83b18278b77b414d11f4485','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S03_CODEX_ML_HARNESS_EVIDENCE_08_450_500MB_20260712.zip',246,'HARNESS','9c38083895f9255beded9c7378c45a1cfefd6bcf4ce207e73fa7fce2555972dd','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S04_GITHUB_HISTORY_STAGING_01_450_500MB_20260712.zip',57191,'HISTORY','c45cde385c02fb3e7a847baaa8815ecd00894834713ef46f0c4287b1462ef31c','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S04_GITHUB_STAGING_CODE_01_450_500MB_20260712.zip',244,'CODE','a5df586a0d619483fc4d182186bd79901711f517b1130a1365c6f25c3f8ec36a','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S04_GITHUB_STAGING_CODE_02_450_500MB_20260712.zip',396,'CODE','bf320529787b3dc8ad6e35f80932cd65d6b31a3191c22a6617c379b2f5c1ce43','ZIP_CENTRAL_DIRECTORY_SHA256'),
('S04_GITHUB_STAGING_CODE_03_450_500MB_20260712.zip',499,'CODE','08fcdf8c3c2bab7bc75b59334eb01bb7a6c9f741d13fda7db9d5cc9baec96755','ZIP_CENTRAL_DIRECTORY_SHA256'),
('TITMC_V27_LIT_WEB_P001_OF_010.zip',15,'PRIMARY_LITERATURE','42ea6aab13dd1f1f78abda0d405455b487276c35f78a4498b66bd6bb7659c9d0','ZIP_CENTRAL_DIRECTORY_SHA256'),
('TITMC_V27_LIT_WEB_P002_OF_010.zip',154,'PRIMARY_LITERATURE','05154dead5ca9bc8d735f176ec9c8c9bb7ca379a0f15c5f1faf911d21045d193','ZIP_CENTRAL_DIRECTORY_SHA256'),
('TITMC_V27_LIT_WEB_P003_OF_010.zip',4610,'PRIMARY_LITERATURE','535a7ab923abee6e198e13d27ba6c889fb0b418803980afb8e8e4727e9515917','ZIP_CENTRAL_DIRECTORY_SHA256'),
('TITMC_V27_LIT_WEB_P004_OF_010.zip',7747,'PRIMARY_LITERATURE','bedcf5c644ff575bb01af96ccc811695b50992b2009d8a1216e1231bb2ee6b2a','ZIP_CENTRAL_DIRECTORY_SHA256'),
('TITMC_V27_LIT_WEB_P005_OF_010.zip',10068,'PRIMARY_LITERATURE','',''),
('TITMC_V27_LIT_WEB_P006_OF_010.zip',11778,'PRIMARY_LITERATURE','',''),
('TITMC_V27_LIT_WEB_P007_OF_010.zip',13499,'PRIMARY_LITERATURE','',''),
('TITMC_V27_LIT_WEB_P008_OF_010.zip',15702,'PRIMARY_LITERATURE','',''),
('TITMC_V27_LIT_WEB_P009_OF_010.zip',20036,'PRIMARY_LITERATURE','',''),
('TITMC_V27_LIT_WEB_P010_OF_010.zip',57717,'PRIMARY_LITERATURE','','')]
raw='\n'.join(f'{a}|{b}|{d}' for a,b,c,d,e in specs).encode(); SNAP='QM05_PARTIAL_'+hashlib.sha256(raw).hexdigest()[:20]
ledger=[]
for i,(name,n,kind,digest,dtype) in enumerate(specs,1):
 ledger.append(dict(input_id=f'QM05-IN-{i:03d}',snapshot_id=SNAP,source_name=name,source_class=kind,path_or_locator='/mnt/data/'+name,source_hash=digest or 'HASH_NOT_CAPTURED_AFTER_RUNTIME_RESET',source_hash_kind=dtype or 'MISSING',member_count=n,central_directory_status='READABLE_OPENED',row_level_use='SCHEMA_OR_TARGETED_USE' if kind in {'FROZEN_DATA','HARNESS','PRIMARY_LITERATURE'} else 'REFERENCE_ONLY',opened_or_consumed='YES',notes='Missing digest is an explicit gap, not an implied match.'))
wcsv('INPUT_LEDGER.csv',list(ledger[0]),ledger)

cohort=[
 dict(cohort_id='C01',source_object='store_ingested_v2_quality.parquet',unit='atomic_record',rows_seen=841899,tmc_rows=17532,unique_record_uuid='NOT_RECOMPUTED',independent_papers='NOT_IDENTIFIABLE',included_for_effect_synthesis='NO',status='PARTIAL_SCHEMA_AND_COUNT_VERIFIED',reason='authoritative paper/sample/condition lineage not bound'),
 dict(cohort_id='C02',source_object='t9_tmc_feat.parquet',unit='feature_record',rows_seen=8192,tmc_rows=8192,unique_record_uuid=8192,independent_papers='NOT_IDENTIFIABLE',included_for_effect_synthesis='NO',status='ROW_COUNT_AND_UUID_UNIQUENESS_VERIFIED',reason='control arm and provenance join unavailable'),
 dict(cohort_id='C03',source_object='quality_domains_20260702.parquet',unit='quality_record',rows_seen=555635,tmc_rows='NOT_RECOMPUTED',unique_record_uuid='NOT_RECOMPUTED',independent_papers='NOT_IDENTIFIABLE',included_for_effect_synthesis='NO',status='SCHEMA_VERIFIED',reason='row-level replay interrupted'),
 dict(cohort_id='C04',source_object='unified_matrix_v2.parquet',unit='unified_record',rows_seen=555635,tmc_rows='NOT_RECOMPUTED',unique_record_uuid='NOT_RECOMPUTED',independent_papers='NOT_IDENTIFIABLE',included_for_effect_synthesis='NO',status='SCHEMA_VERIFIED',reason='V29 atomic authority absent'),
 dict(cohort_id='C05',source_object='V27 document-corpus manifest',unit='document',rows_seen=78683,tmc_rows=1827,unique_record_uuid='N/A',independent_papers='NOT_IDENTIFIABLE',included_for_effect_synthesis='NO',status='SUPPORTING_PRIOR_ONLY',reason='document scope is not atomic sample/property cohort')]
wcsv('ANALYSIS_COHORT.csv',list(cohort[0]),cohort)

reliability=[]
for e,d,lo,base,hi,use,claim in [
 ('DIRECT_TABLE_TEXT','original table or explicit text',.90,1,1,'UNWEIGHTED','direct report, not automatically unbiased'),
 ('SAME_WORK_SUPPLEMENT','publisher or same-work supplement',.85,.95,1,'UNWEIGHTED','lineage must be joined'),
 ('FIGURE_DERIVED','digitized figure',.50,.75,.90,'UNWEIGHTED','digitization uncertainty required'),
 ('DERIVED_CALCULATION','calculated from reported quantities',.45,.70,.90,'UNWEIGHTED','formula and propagation required'),
 ('DATABASE_PRIOR','secondary database or registry',.25,.50,.75,'DISCOVERY_ONLY','return to original work'),
 ('UNRESOLVED','unresolved identity or provenance',0,0,0,'EXCLUDE','no quantitative claim')]:
 reliability.append(dict(evidence_level=e,directness=d,main_analysis_use=use,weight_low=lo,weight_base=base,weight_high=hi,variance_interpretation='NONE',status='SENSITIVITY_ONLY' if e!='UNRESOLVED' else 'EXCLUDED',claim_ceiling=claim))
wcsv('SOURCE_RELIABILITY_REPLAY.csv',list(reliability[0]),reliability)

missing=[
 dict(model_row_id='MIS-001',paper_uid='doi:10.1016/0921-5093(94)90373-5',sample_uid='UNRESOLVED',condition_uid='800C_vf0.40_SiC_fibre_IMI834',source_type='ORIGINAL_PUBLISHER_XML',publisher_format='XML_TEXT',outcome='elongation_pct',outcome_missing=1,other_property_reported='UTS=1500 MPa',candidate_mechanism='MAR_OR_MNAR_CANDIDATE',diagnostic_basis='property-specific omission despite reported high-temperature UTS',global_inference='NOT_IDENTIFIABLE',evidence_level='DIRECT_TABLE_TEXT',notes='No numerical elongation in the direct XML passage.'),
 dict(model_row_id='MIS-002',paper_uid='doi:10.1016/j.matdes.2015.07.058',sample_uid='UNRESOLVED',condition_uid='as_aged_TiBw_near_alpha_700_750_800C',source_type='ORIGINAL_PUBLISHER_XML',publisher_format='XML_TEXT',outcome='elongation_pct',outcome_missing=1,other_property_reported='UTS=760/540/400 MPa at 700/750/800 C',candidate_mechanism='MAR_OR_MNAR_CANDIDATE',diagnostic_basis='UTS numerical; elongation qualitative only',global_inference='NOT_IDENTIFIABLE',evidence_level='DIRECT_TABLE_TEXT',notes='Targeted evidence cannot distinguish MAR from MNAR.'),
 dict(model_row_id='MIS-GLOBAL',paper_uid='',sample_uid='',condition_uid='',source_type='ALL',publisher_format='ALL',outcome='UTS|YS|EL|microstructure|dose|SE',outcome_missing='',other_property_reported='',candidate_mechanism='MCAR_TEST_NOT_RUN',diagnostic_basis='authoritative atomic missingness and lineage unavailable',global_inference='NOT_IDENTIFIABLE',evidence_level='UNRESOLVED',notes='Failure to reject cannot establish MCAR.')]
wcsv('MISSINGNESS_MODEL.csv',list(missing[0]),missing)

dup=[]
for fam,title,ids in [
 ('DAF-001','0679 Understanding confined TiB fiber-like structure for strength-ductility combination',['file_000000001f48720ba525c2cf0c3d1fe0','file_000000005d9471f899d1a5e9f81f803c']),
 ('DAF-002','0788 Heat transfer and diffusion-controlled kinetics of liquid-solid phases',['file_000000009870720ba68b77b51165cb75','file_00000000bd60720bbd31920cffbcafd6'])]:
 for j,x in enumerate(ids,1): dup.append(dict(duplicate_family_id=fam,duplicate_level='SOURCE_ASSET',canonical_work=title,asset_id=x,asset_occurrence=j,paper_uid='UNRESOLVED',sample_uid='UNRESOLVED',condition_uid='UNRESOLVED',match_basis='same filename/title and identical visible snippet',byte_hash_match='NOT_AVAILABLE',family_size=2,independent_work_units=1,status='PROBABLE_EXACT_ASSET_DUPLICATE',effect_synthesis_action='collapse only after content hash and lineage confirmation'))
wcsv('DUPLICATE_FAMILY.csv',list(dup[0]),dup)

pair_cols=['pair_id','paper_uid','sample_uid_tmc','sample_uid_control','condition_uid','property','match_grade','tmc_value','control_value','effect_definition','effect_value','evidence_level','status','reason']
wcsv('PAIR_MATCHES.csv',pair_cols,[dict(pair_id='NOT_IDENTIFIABLE',evidence_level='UNRESOLVED',status='NO_AUTHORITATIVE_SAMPLE_CONTROL_LINEAGE',reason='V29 ATOMIC_RECORDS and provenance-bound registries were not present.')])

effects=[
 dict(estimand_id='QM05_DUP_ASSET_INFLATION_CONFIRMED_SUBSET',estimand='raw source-asset count / lineage-collapsed work count',analysis_unit='confirmed duplicate source-asset subset',raw_units=4,independent_units=2,estimate=2.0,estimate_scale='inflation_factor',ci_low='NOT_IDENTIFIABLE',ci_high='NOT_IDENTIFIABLE',prediction_interval='NOT_IDENTIFIABLE',independent_papers='NOT_IDENTIFIABLE',samples='NOT_IDENTIFIABLE',match_grade='E',claim_level=1,support_domain='two observed duplicate asset families only',status='DESCRIPTIVE_IDENTIFIED',notes='Not a global paper/sample estimate.'),
 dict(estimand_id='QM05_PROPERTY_EFFECT_BIAS',estimand='effect size association with SE, paper size, and year',analysis_unit='independent paper effect',raw_units=0,independent_units=0,estimate='NOT_IDENTIFIABLE',estimate_scale='',ci_low='',ci_high='',prediction_interval='',independent_papers=0,samples=0,match_grade='',claim_level=0,support_domain='none',status='NOT_IDENTIFIABLE',notes='No matched effect table with legitimate SE semantics.')]
wcsv('EFFECT_ESTIMATES.csv',list(effects[0]),effects)

bias=[]
for i,m,req,rule in [('001','Funnel plot','independent effects and legitimate SE','visual only after provenance-bound effects'),('002','Egger regression','k>=10 independent effects with SE','k>=10 and dependence resolved'),('003','selection-model sensitivity','effect likelihood and SE','raw and sensitivity side-by-side'),('004','year/paper-size association','independent effect, year, sample size','paper-cluster robust')]:
 bias.append(dict(bias_test_id='PUB-'+i,method=m,required_input=req,k_independent=0,result='NOT_IDENTIFIABLE',raw_result='NOT_RUN',sensitivity_result='NOT_RUN',threshold_rule=rule,reason='valid paper-level effect/SE cohort absent'))
wcsv('BIAS_SENSITIVITY.csv',list(bias[0]),bias)

sens=[
 dict(analysis_id='SENS-001',estimand='confirmed source-asset inflation',scenario='raw asset counting',estimate=4,unit='assets',independent_papers='NOT_IDENTIFIABLE',status='OBSERVED'),
 dict(analysis_id='SENS-001',estimand='confirmed source-asset inflation',scenario='collapse probable duplicate family',estimate=2,unit='works',independent_papers='NOT_IDENTIFIABLE',status='OBSERVED_SUBSET_ONLY'),
 dict(analysis_id='SENS-002',estimand='source reliability',scenario='unweighted main analysis',estimate='NOT_RUN',unit='',independent_papers=0,status='PRIMARY_SPECIFICATION'),
 dict(analysis_id='SENS-002',estimand='source reliability',scenario='low/base/high weight bands',estimate='NOT_RUN',unit='',independent_papers=0,status='REPLAY_ONLY'),
 dict(analysis_id='SENS-003',estimand='missingness mechanism',scenario='complete case vs mechanism-consistent MI',estimate='NOT_RUN',unit='',independent_papers=0,status='NOT_IDENTIFIABLE')]
wcsv('SENSITIVITY_ANALYSIS.csv',list(sens[0]),sens)

nulls=[
 ('NULL-001','Are property effects associated with standard error?','NOT_IDENTIFIABLE','No independent effects with legitimate SE','no publication-bias correction'),
 ('NULL-002','Is global missingness MCAR?','NOT_IDENTIFIABLE','Atomic missingness not joined to lineage','do not declare MCAR'),
 ('NULL-003','How much does paper/sample reuse inflate N globally?','NOT_IDENTIFIABLE','Lineage registry absent','only source-asset subset=2.0'),
 ('NULL-004','Can quality weights correct true effect?','NO','Not known sampling variances','raw and sensitivity results both required'),
 ('NULL-005','Can figure-derived values be promoted to Gold?','NO','Digitization/provenance need validation','no Gold promotion')]
wcsv('NULL_NEGATIVE_RESULTS.csv',['result_id','question','result','reason','claim_ceiling'],[dict(result_id=a,question=b,result=c,reason=d,claim_ceiling=e) for a,b,c,d,e in nulls])

conflicts=[
 dict(conflict_id='CON-001',field_or_object='snapshot authority',source_a=SNAP,value_a='partial package/schema audit',source_b='required V29/Q40 atomic snapshot',value_b='missing',conflict_type='AUTHORITY_GAP',resolution='no effect synthesis',status='OPEN'),
 dict(conflict_id='CON-002',field_or_object='TMC unit count',source_a='t9_tmc_feat.parquet',value_a=8192,source_b='store is_tmc flags',value_b=17532,conflict_type='SCOPE_UNIT_MISMATCH',resolution='feature subset versus store flags; crosswalk required',status='OPEN_MAPPING'),
 dict(conflict_id='CON-003',field_or_object='TMC unit count',source_a='V27 document corpus',value_a='1827 confirmed documents',source_b='S03 feature records',value_b='8192 rows',conflict_type='DOCUMENT_VS_ATOMIC',resolution='paper/sample/condition crosswalk required',status='OPEN_MAPPING'),
 dict(conflict_id='CON-004',field_or_object='duplicate source assets',source_a='two visible duplicate pairs',value_a='2 families / 4 assets',source_b='byte hashes',value_b='not available',conflict_type='IDENTITY_UNCERTAINTY',resolution='probable only; do not delete or globally collapse',status='OPEN')]
wcsv('CONFLICT_LEDGER.csv',list(conflicts[0]),conflicts)

# Required common tables not estimable in this partial snapshot.
def status_table(name,cols,status,reason):
 r={c:'' for c in cols}; r[cols[0]]=status; r['status']=status if 'status' in cols else r.get('status',''); r['reason']=reason if 'reason' in cols else r.get('reason',''); wcsv(name,cols,[r])
status_table('HIERARCHICAL_RESULTS.csv',['result_id','outcome','model','estimate','se','ci_low','ci_high','prediction_low','prediction_high','papers','samples','status','reason'],'NOT_IDENTIFIABLE','No provenance-bound independent paper effects.')
status_table('DOSE_RESPONSE.csv',['result_id','outcome','dose_definition','model','estimate','ci_low','ci_high','papers','samples','status','reason'],'NOT_APPLICABLE_QM05','No valid dose cohort was formed.')
status_table('INTERACTION_EFFECTS.csv',['result_id','outcome','interaction','estimate','ci_low','ci_high','papers','samples','status','reason'],'NOT_APPLICABLE_QM05','No valid property-effect cohort was formed.')
status_table('HETEROGENEITY.csv',['result_id','outcome','metric','estimate','ci_low','ci_high','papers','samples','status','reason'],'NOT_IDENTIFIABLE','Between-paper heterogeneity needs independent effects and uncertainty.')

prov=[]
for r in ledger: prov.append(dict(provenance_id='PROV-'+r['input_id'],snapshot_id=SNAP,source_hash=r['source_hash'],paper_uid=None,sample_uid=None,condition_uid=None,source_locator=r['path_or_locator'],evidence_level='UNRESOLVED' if r['source_class']=='PRIMARY_LITERATURE' else 'DATABASE_PRIOR',action='ZIP_CENTRAL_DIRECTORY_OPENED',result={'member_count':r['member_count'],'status':'READABLE'}))
prov += [
 dict(provenance_id='PROV-MIS-001',snapshot_id=SNAP,source_hash='8753e100a19623ad8264f0d8c1ec95c430c8ef6c183e5b8b1e42d0b771cd87d4',paper_uid='doi:10.1016/0921-5093(94)90373-5',sample_uid=None,condition_uid='800C_vf0.40_SiC_fibre_IMI834',source_locator='TITMC_V27_LIT_WEB_P009_OF_010.zip::8753e100_8753e100a19623ad.xml',evidence_level='DIRECT_TABLE_TEXT',action='TARGETED_ORIGINAL_XML_MISSINGNESS_CHECK',result={'uts_mpa':1500,'elongation_pct':None}),
 dict(provenance_id='PROV-MIS-002',snapshot_id=SNAP,source_hash='fed57cf5ba75312c691092603ebcd9a6210176f91b68a31d14de3fe54886412e',paper_uid='doi:10.1016/j.matdes.2015.07.058',sample_uid=None,condition_uid='as_aged_TiBw_near_alpha_700_750_800C',source_locator='TITMC_V27_LIT_WEB_P009_OF_010.zip::fed57cf5_fed57cf5ba75312c.xml',evidence_level='DIRECT_TABLE_TEXT',action='TARGETED_ORIGINAL_XML_MISSINGNESS_CHECK',result={'uts_by_temp':{'700':760,'750':540,'800':400},'elongation_pct':None}),
 dict(provenance_id='PROV-DUP-001',snapshot_id=SNAP,source_hash=None,paper_uid=None,sample_uid=None,condition_uid=None,source_locator='file_library::0679 duplicate pair',evidence_level='DATABASE_PRIOR',action='SOURCE_ASSET_DUPLICATE_CANDIDATE',result={'family_size':2,'byte_hash':'missing'}),
 dict(provenance_id='PROV-DUP-002',snapshot_id=SNAP,source_hash=None,paper_uid=None,sample_uid=None,condition_uid=None,source_locator='file_library::0788 duplicate pair',evidence_level='DATABASE_PRIOR',action='SOURCE_ASSET_DUPLICATE_CANDIDATE',result={'family_size':2,'byte_hash':'missing'})]
wtext('PROVENANCE.jsonl','\n'.join(json.dumps(x,ensure_ascii=False,sort_keys=True) for x in prov))

# Figure data.
wcsv('figure_data/source_reliability_effective_n.csv',['stratum','raw_units','independent_units','unit_type','evidence_scope','status'],[
 dict(stratum='S03 store: all atomic rows',raw_units=841899,independent_units='',unit_type='atomic rows',evidence_scope='frozen store',status='effective N not identifiable'),
 dict(stratum='S03 store: TMC-flagged rows',raw_units=17532,independent_units='',unit_type='atomic rows',evidence_scope='frozen store',status='effective N not identifiable'),
 dict(stratum='S03 TMC feature subset',raw_units=8192,independent_units='',unit_type='feature rows',evidence_scope='frozen subset',status='effective N not identifiable'),
 dict(stratum='V27 TMC-confirmed documents',raw_units=1827,independent_units='',unit_type='documents',evidence_scope='supporting audit prior',status='not an effect cohort'),
 dict(stratum='Confirmed duplicate-asset subset',raw_units=4,independent_units=2,unit_type='assets / works',evidence_scope='two observed families',status='subset inflation=2.0')])
wcsv('figure_data/missingness_upset.csv',['pattern','UTS_reported','YS_reported','EL_reported','within_study_SE_reported','count_works','scope'],[dict(pattern='UTS reported; EL numeric missing',UTS_reported=1,YS_reported='unknown',EL_reported=0,within_study_SE_reported=0,count_works=2,scope='targeted original-XML examples only')])
wcsv('figure_data/duplicate_network.csv',['family_id','asset_id','status'],[dict(family_id='DAF-001',asset_id='0679-A',status='probable duplicate'),dict(family_id='DAF-001',asset_id='0679-B',status='probable duplicate'),dict(family_id='DAF-002',asset_id='0788-A',status='probable duplicate'),dict(family_id='DAF-002',asset_id='0788-B',status='probable duplicate')])
wcsv('figure_data/funnel_status.csv',['estimand','k_independent_effects','within_study_se_available','funnel_status','egger_status','reason'],[dict(estimand='material-property effect vs precision',k_independent_effects=0,within_study_se_available=0,funnel_status='NOT_IDENTIFIABLE',egger_status='NOT_IDENTIFIABLE',reason='no provenance-bound matched effects with legitimate SE')])

plot_code=r'''#!/usr/bin/env python3
from pathlib import Path
import csv, matplotlib.pyplot as plt
B=Path(__file__).resolve().parents[1]; D=B/'figure_data'; F=B/'figures'; F.mkdir(exist_ok=True)
def rows(n):
 with (D/n).open(encoding='utf-8') as f:return list(csv.DictReader(f))
def save(stem):
 for ext,kw in [('svg',{}),('pdf',{}),('png',{'dpi':600})]: plt.savefig(F/f'{stem}.{ext}',bbox_inches='tight',**kw)
 plt.close()
# F01
r=rows('source_reliability_effective_n.csv'); fig,ax=plt.subplots(figsize=(11,6.5)); y=list(range(len(r))); raw=[float(x['raw_units']) for x in r]; ind=[float(x['independent_units'] or 0) for x in r]
ax.barh(y,raw,label='Raw units'); ax.barh(y,ind,label='Lineage-collapsed units (identified only)'); ax.set_xscale('log'); ax.set_yticks(y,[x['stratum'] for x in r]); ax.set_xlabel('Count (log scale)'); ax.set_title('Source inventory and effective-sample-size status')
for i,x in enumerate(r): ax.text(max(raw[i],1)*1.08,i,x['status'],va='center',fontsize=8)
ax.legend(loc='lower right'); fig.text(.01,.01,'Independent papers: not identifiable | Samples: not identifiable | Estimand: raw/lineage-collapsed source units | Evidence: audit only',fontsize=8); save('QM05_F01_source_reliability_effective_n')
# F02
r=rows('missingness_upset.csv'); fig,ax=plt.subplots(figsize=(10,6)); c=[int(x['count_works']) for x in r]; ax.bar([x['pattern'] for x in r],c); ax.set_ylabel('Number of works'); ax.set_title('Targeted missingness pattern (not corpus prevalence)'); ax.set_ylim(0,max(c)+1); ax.text(.5,.55,'UTS: reported\nEL: numeric value missing\nWithin-study SE: unavailable',transform=ax.transAxes,ha='center',fontsize=12,bbox={'facecolor':'white','alpha':.85}); fig.text(.01,.01,'Independent papers: 2 targeted works | Samples: unresolved | Evidence: direct original XML | Support: two examples only',fontsize=8); save('QM05_F02_missingness_upset')
# F03
r=rows('duplicate_network.csv'); fig,ax=plt.subplots(figsize=(10,6)); pos={'DAF-001':(.28,.5),'DAF-002':(.72,.5),'0679-A':(.15,.8),'0679-B':(.15,.2),'0788-A':(.85,.8),'0788-B':(.85,.2)}
for x in r:
 a,b=pos[x['family_id']],pos[x['asset_id']]; ax.plot([a[0],b[0]],[a[1],b[1]],linewidth=2)
for n,(x,y) in pos.items(): ax.scatter([x],[y],s=900 if n.startswith('DAF') else 500,marker='s' if n.startswith('DAF') else 'o'); ax.text(x,y,n,ha='center',va='center',fontsize=9)
ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off');ax.set_title('Observed source-asset duplicate dependency network');ax.text(.5,.05,'Raw assets = 4; probable independent works = 2; subset inflation factor = 2.0',ha='center',fontsize=11);fig.text(.01,.01,'Independent papers/samples: unresolved | Estimand: source-asset inflation | Support: two families',fontsize=8);save('QM05_F03_duplicate_network')
# F04
x=rows('funnel_status.csv')[0];fig,ax=plt.subplots(figsize=(10,6));ax.axis('off');ax.text(.5,.72,'FUNNEL / EGGER: NOT IDENTIFIABLE',ha='center',fontsize=19,weight='bold');ax.text(.5,.48,f"Independent effects: {x['k_independent_effects']}\nLegitimate within-study SE: {x['within_study_se_available']}\n{x['reason']}",ha='center',fontsize=13,bbox={'facecolor':'white','edgecolor':'black','pad':12});ax.text(.5,.24,'No pseudo-funnel was drawn from row counts, residuals, or confidence scores.',ha='center',fontsize=11);fig.text(.01,.01,'Independent papers: 0 | Samples: 0 | Estimand: small-study effect | Support domain: none',fontsize=8);save('QM05_F04_funnel_not_identifiable')
'''
wtext('plot_code/plot_all.py',plot_code)

spec={'window_id':WINDOW,'generated_at':NOW,'style':{'language':'English','png_dpi':600,'vector':['SVG','PDF'],'generative_images':False},'figures':[]}
for fid,stem,data,status in [('QM05_F01','QM05_F01_source_reliability_effective_n','source_reliability_effective_n.csv','PARTIAL_AUDIT'),('QM05_F02','QM05_F02_missingness_upset','missingness_upset.csv','TARGETED_EXAMPLES_ONLY'),('QM05_F03','QM05_F03_duplicate_network','duplicate_network.csv','SOURCE_ASSET_LEVEL_ONLY'),('QM05_F04','QM05_F04_funnel_not_identifiable','funnel_status.csv','NOT_IDENTIFIABLE')]: spec['figures'].append({'id':fid,'data':'figure_data/'+data,'code':'plot_code/plot_all.py','outputs':[f'figures/{stem}.{e}' for e in ['svg','pdf','png']],'status':status})
wjson('PLOT_SPECS.json',spec)

replay=r'''#!/usr/bin/env python3
"""Memory-safe QM05 replay. Refuses pseudo-SE, label imputation, and cross-paper pairing."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,shutil,tempfile,zipfile
from collections import Counter
from pathlib import Path

def norm(x):
 s='' if x is None else str(x).strip().lower(); s=re.sub(r'https?://(dx\.)?doi\.org/','',s); return re.sub(r'\s+',' ',s)
def sid(prefix,*x): return prefix+hashlib.sha256('|'.join(norm(i) for i in x).encode()).hexdigest()[:20]
def wc(p,cols,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();[w.writerow({c:r.get(c,'') for c in cols}) for r in rows]
def extract(root,names,td):
 out={}
 for z in sorted(root.glob('*.zip')):
  try:
   with zipfile.ZipFile(z) as q:
    for n in q.namelist():
     b=Path(n).name
     if b in names and b not in out:
      d=td/b
      with q.open(n) as a,d.open('wb') as f: shutil.copyfileobj(a,f)
      out[b]=d
  except zipfile.BadZipFile: pass
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input-root',type=Path,default=Path('/mnt/data'));ap.add_argument('--out',type=Path,default=Path('QM05_REPLAY'));a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 import pandas as pd,pyarrow.parquet as pq
 need={'store_ingested_v2_quality.parquet','source_reliability_table.csv','condition_canonical_manifest.csv','paper_slice_manifest.csv','target_truth_evidence_manifest.csv'}
 with tempfile.TemporaryDirectory() as t:
  f=extract(a.input_root,need,Path(t));(a.out/'INPUT_DISCOVERY.json').write_text(json.dumps({'found':sorted(f),'missing':sorted(need-set(f))},indent=2))
  if 'store_ingested_v2_quality.parquet' not in f: raise SystemExit('BLOCKED_INPUT: store missing')
  avail=pq.read_schema(f['store_ingested_v2_quality.parquet']).names; want=['record_uuid','paper_uid','doi','sample_uid','condition_uid','cond_id','matrix_alloy','process','heat_treatment','test_mode','test_temp_c','strain_rate_s','direction','reinf_vol_pct','reinf_wt_pct','is_tmc','uts_mpa','ys_mpa','elong_pct']; use=[x for x in want if x in avail]; df=pd.read_parquet(f['store_ingested_v2_quality.parquet'],columns=use)
  p='paper_uid' if 'paper_uid' in df else 'doi';s='sample_uid' if 'sample_uid' in df else 'record_uuid';c='condition_uid' if 'condition_uid' in df else 'cond_id'
  if not all(x in df for x in [p,s,c]): raise SystemExit('BLOCKED_INPUT: stable lineage unavailable')
  df['_paper']=df[p].map(norm);df['_sample']=df[s].map(norm);df['_condition']=df[c].map(norm);df=df[(df._paper!='')&(df._sample!='')&(df._condition!='')]
  miss=[]
  for k,g in df.groupby(['_paper','_sample','_condition'],dropna=False):
   r=dict(paper_uid=k[0],sample_uid=k[1],condition_uid=k[2])
   for y in ['uts_mpa','ys_mpa','elong_pct']:r[y+'_missing']=int(y not in g or g[y].notna().sum()==0)
   miss.append(r)
  wc(a.out/'MISSINGNESS_MODEL.csv',list(miss[0]) if miss else ['paper_uid'],miss)
  dose='reinf_vol_pct' if 'reinf_vol_pct' in df else ('reinf_wt_pct' if 'reinf_wt_pct' in df else None)
  if not dose: raise SystemExit('CONTINUE_DATA_GAP: dose unavailable')
  df['_dose']=pd.to_numeric(df[dose],errors='coerce'); keys=['_paper','_condition']+[x for x in ['matrix_alloy','process','heat_treatment','test_mode','test_temp_c','strain_rate_s','direction'] if x in df];pairs=[]
  for kk,g in df.groupby(keys,dropna=False):
   ctrl=g[g._dose.fillna(0)<=0];trt=g[g._dose.fillna(0)>0]
   if ctrl.empty or trt.empty:continue
   for y in ['uts_mpa','ys_mpa','elong_pct']:
    if y not in g:continue
    cv=pd.to_numeric(ctrl[y],errors='coerce').dropna();tv=pd.to_numeric(trt[y],errors='coerce').dropna()
    if cv.empty or tv.empty:continue
    cval=float(cv.mean())
    for idx,v in tv.items():
     v=float(v);lr=math.log(v/cval) if v>0 and cval>0 else float('nan');pairs.append(dict(pair_id=sid('PAIR-',kk,y,idx),paper_uid=g.loc[idx,'_paper'],sample_uid_tmc=g.loc[idx,'_sample'],condition_uid=g.loc[idx,'_condition'],property=y,tmc_value=v,control_value=cval,delta=v-cval,lnRR=lr,pct_change=100*math.expm1(lr) if math.isfinite(lr) else ''))
  cols=['pair_id','paper_uid','sample_uid_tmc','condition_uid','property','tmc_value','control_value','delta','lnRR','pct_change'];wc(a.out/'PAIR_MATCHES.csv',cols,pairs)
  (a.out/'STATUS.txt').write_text('CONTINUE_DATA_GAP: provenance review and SE semantics remain mandatory\n')
if __name__=='__main__':main()
'''
wtext('analysis_code/qm05_replay.py',replay)
wtext('requirements.txt','matplotlib==3.10.3\nnumpy==2.3.2\npandas==2.3.1\npyarrow==20.0.0')
wtext('environment.lock','python==3.11\nmatplotlib==3.10.3\nnumpy==2.3.2\npandas==2.3.1\npyarrow==20.0.0')

wtext('00_EXECUTIVE_VERDICT.md',f'''# QM05 执行裁决

`WINDOW=QM05 | SNAPSHOT={SNAP} | INPUT_MODE=QUANT_EXECUTE/COHORT_BUILD`

本轮完成 26 个上传包的中央目录级全量清点、关键冻结表 schema/规模核验、两组可见重复源资产识别、两篇出版社原始 XML 的目标特异性缺失复核，以及可复算代码、四图三格式、数据、证据链、清单和校验。

唯一可数值识别的 estimand：在已观察的两组重复源资产子集中，4 个资产折叠为 2 个独立作品，计数膨胀因子 **2.0**。该估计只适用于这两个家族，不能外推为全库论文或样品有效样本量。

两篇原始 XML 均出现 UTS 数值存在而 EL 数值缺失，支持属性选择性报告的 MAR/MNAR 候选机制，但不能估计全库缺失率或区分 MAR 与 MNAR。来源权重只用于敏感性，不作为精确方差或真值概率。

当前无法形成权威 matrix/control 配对、paper-cluster/LOPO、层级异质性、预测区间或 funnel/Egger；根因是缺少同一权威快照绑定的 `ATOMIC_RECORDS + PROVENANCE + paper/sample/condition lineage + SE semantics`。用 841,899 行、17,532 个 TMC 标记行或 8,192 个特征行冒充独立研究数，会制造伪精度。

Claim ceiling：**Level 1 描述性审计**。不得自晋 Gold、不得注册生产模型、不得生成 VALIDATED 配方。

`STATUS: CONTINUE_DATA_GAP | WINDOW=QM05 | MISSING=V29_ATOMIC_RECORDS+PROVENANCE+LINEAGE+SE_SEMANTICS | NEXT=execute_WEB_TO_LOCAL_REQUEST_and_rerun_qm05_replay`
''')
wtext('METHODS.md',f'''# Methods — QM05

快照 `{SNAP}` 是基于实际枚举包名、可用 Hash 与成员数生成的部分审计指纹，不是 V29 权威快照。

原子单位必须是 `paper × sample × composition × precursor × reinforcement × process × heat treatment × microstructure × test mode × temperature × strain rate × orientation × property`。行数、特征数、文档数与独立论文数不可互换。

主分析不做主观质量加权；证据等级低/基准/高权重只用于敏感性。标签不插补。MCAR 不能由“未检出预测因子”证明；MAR 依赖观测协变量；MNAR 只能做选择模型/模式混合敏感性。

重复识别优先 DOI、出版社身份、内容 SHA、样品与条件指纹。属性效应只允许同论文同条件 matrix/control 配对，优先 `ΔY`、`lnRR`、百分比变化和可信体积分数下的单位剂量效率。论文是聚类单位，禁止按原子行加权。

Funnel/Egger 的硬门为至少 10 个独立论文效应且具有合法的研究内 SE。质量分、图读置信度、模型残差、行间离散度均不能替代 SE。门失败时结论是 `NOT_IDENTIFIABLE`，不是“无发表偏倚”。
''')
wtext('LIMITATIONS.md','''# Limitations

1. 缺少权威 V29 ATOMIC_RECORDS、provenance、排除账本和 paper/sample/condition registries 的联合快照。
2. 执行运行时在 schema/规模核验后重置，未完成内存安全 lineage join。
3. 部分大包完整 Hash 未捕获，已在 INPUT_LEDGER 明示。
4. 两组重复是源资产级，不是重复实验样品的证明。
5. 两个 XML 例子只能证明候选选择性报告，不能估计患病率。
6. 无合法研究内 SE，因此 funnel/Egger/selection model 未运行。
7. 任何质量权重都不解释为已知方差或真值概率。
8. 本包无权修改 ACTIVE_TITMC、Gold、统一 Schema 或生产模型注册表。
''')
request={'window_id':WINDOW,'status':'CONTINUE_DATA_GAP','snapshot_id':SNAP,'required_objects':[
 {'name':'ATOMIC_RECORDS.parquet','required_columns':['snapshot_id','source_hash','paper_uid','sample_uid','condition_uid','record_uuid','property','value','unit','evidence_level','source_locator']},
 {'name':'PROVENANCE.jsonl','required_keys':['snapshot_id','source_hash','paper_uid','sample_uid','condition_uid','source_locator','evidence_level']},
 {'name':'CONFLICT_LEDGER.csv'},{'name':'EXCLUDED_RECORDS.csv'},
 {'name':'PAPER_SOURCE_REGISTRY.csv','required_columns':['paper_uid','doi','year','journal','publisher','source_type','original_review_simulation','own_lab_public','duplicate_family_id']},
 {'name':'SAMPLE_LINEAGE.csv','required_columns':['paper_uid','sample_uid','parent_sample_uid','reuse_type','duplicate_family_id']},
 {'name':'source_reliability_table.csv'},{'name':'condition_canonical_manifest.csv'},{'name':'paper_slice_manifest.csv'},{'name':'target_truth_evidence_manifest.csv'},
 {'name':'WITHIN_STUDY_UNCERTAINTY.csv','required_columns':['paper_uid','sample_uid','condition_uid','property','n','uncertainty_type','uncertainty_value','se_value']}],
 'integrity_requirements':['full-file SHA-256 for all 26 ZIPs','CRC/testzip PASS','one authoritative snapshot_id','one-to-one lineage crosswalk','no label imputation'],
 'execution_command':'python analysis_code/qm05_replay.py --input-root /mnt/data --out QM05_REPLAY','promotion_forbidden':['ACTIVE_TITMC','Gold','unified schema','production model registry','VALIDATED recipe']}
wjson('WEB_TO_LOCAL_REQUEST.json',request)
wtext('LOCAL_ABSORPTION_PROMPT.md',f'''# QM05 local absorption

1. 在解压根目录运行 `python validate_package.py .` 并核验 `CHECKSUMS.sha256`。
2. 按 `WEB_TO_LOCAL_REQUEST.json` 提供同一不可变快照下的全部对象，不得用报告替代原子记录。
3. 隔离环境安装 `requirements.txt`，运行：

```bash
python analysis_code/qm05_replay.py --input-root /mnt/data --out QM05_REPLAY
```

4. 若 `paper_uid + sample_uid + condition_uid + source_hash` 不完整、标签被插补、质量分被当作 SE，立即拒收。
5. 不修改 ACTIVE_TITMC、Gold、统一 Schema 或生产模型注册表。
6. `{SNAP}` 仅为部分审计快照，必须由 V29 权威 Hash 取代。
''')
wtext('README.md','# FINAL_QM05\n\nTi/TMC 来源可靠性、缺失机制、重复依赖与发表偏倚可识别性审计回包。')
wtext('REPRODUCE.md','''# Reproduce

```bash
python -m pip install matplotlib==3.10.3
python plot_code/plot_all.py
python validate_package.py .
```

完整数据回放使用 `analysis_code/qm05_replay.py`。''')
status={'window_id':WINDOW,'batch_id':BATCH,'snapshot_id':SNAP,'snapshot_authority':'PARTIAL_DERIVED_NOT_V29_AUTHORITY','papers_seen':None,'papers_included':0,'independent_papers':None,'atomic_rows':8192,'store_rows_seen':841899,'store_tmc_rows':17532,'matched_pairs':0,'effect_estimates':1,'plots_generated':4,'open_conflicts':4,'claim_level_max':1,'status':'CONTINUE_DATA_GAP','next_action':'Supply authoritative V29 atomic/provenance/lineage/SE objects and rerun qm05_replay.py','generated_at':NOW}
wjson('WINDOW_STATUS.json',status)

# Contract tests and validator.
wtext('tests/test_contract.py',r'''from pathlib import Path
import csv,json
R=Path(__file__).resolve().parents[1]
def test_required():
 for n in ['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','SOURCE_RELIABILITY_REPLAY.csv','MISSINGNESS_MODEL.csv','DUPLICATE_FAMILY.csv','BIAS_SENSITIVITY.csv','WINDOW_STATUS.json']:assert (R/n).is_file()
def test_status():
 s=json.loads((R/'WINDOW_STATUS.json').read_text());assert s['status']=='CONTINUE_DATA_GAP' and s['claim_level_max']<=1
def test_estimand():
 x=list(csv.DictReader((R/'EFFECT_ESTIMATES.csv').open()))[0];assert float(x['estimate'])==2.0
def test_no_nested_zip():assert not list(R.rglob('*.zip'))
def test_figures():
 for s in ['QM05_F01_source_reliability_effective_n','QM05_F02_missingness_upset','QM05_F03_duplicate_network','QM05_F04_funnel_not_identifiable']:
  for e in ['svg','pdf','png']:assert (R/'figures'/f'{s}.{e}').is_file()
''')
validator=r'''#!/usr/bin/env python3
import csv,hashlib,json,sys
from pathlib import Path
R=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); req=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','SOURCE_RELIABILITY_REPLAY.csv','MISSINGNESS_MODEL.csv','DUPLICATE_FAMILY.csv','BIAS_SENSITIVITY.csv'];err=[]
for n in req:
 if not (R/n).is_file():err.append('missing:'+n)
if list(R.rglob('*.zip')):err.append('nested zip')
for line in (R/'CHECKSUMS.sha256').read_text().splitlines():
 if not line:continue
 h,p=line.split('  ',1);q=R/p
 if not q.is_file() or hashlib.sha256(q.read_bytes()).hexdigest()!=h:err.append('sha:'+p)
s=json.loads((R/'WINDOW_STATUS.json').read_text());
if s['status'] not in ['TASK_COMPLETE','CONTINUE_DATA_GAP','BLOCKED_INPUT']:err.append('status')
print(json.dumps({'pass':not err,'errors':err},indent=2));raise SystemExit(bool(err))
'''
wtext('validate_package.py',validator)

# Run plots.
cp=subprocess.run([sys.executable,str(OUT/'plot_code/plot_all.py')],cwd=OUT,text=True,capture_output=True)
wjson('PLOT_RUN_LOG.json',{'returncode':cp.returncode,'stdout':cp.stdout[-2000:],'stderr':cp.stderr[-2000:]})
if cp.returncode: raise RuntimeError(cp.stderr)

# Five self-tests without pytest.
checks=[]
def ck(name,cond): checks.append({'test':name,'pass':bool(cond)}); assert cond,name
ck('required',all((OUT/n).is_file() for n in ['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','WINDOW_STATUS.json']))
ck('status',json.loads((OUT/'WINDOW_STATUS.json').read_text())['status']=='CONTINUE_DATA_GAP')
ck('estimand',float(next(csv.DictReader((OUT/'EFFECT_ESTIMATES.csv').open()))['estimate'])==2.0)
ck('no_nested_zip',not list(OUT.rglob('*.zip')))
ck('figures',len(list((OUT/'figures').glob('*')))==12)
wtext('SELF_TEST_OUTPUT.txt',json.dumps({'pass':True,'tests':checks},ensure_ascii=False,indent=2))

# Manifest then checksums (checksums excludes itself).
files=[]
for p in sorted(x for x in OUT.rglob('*') if x.is_file() and x.name not in ['MANIFEST.json','CHECKSUMS.sha256']):files.append({'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':hfile(p)})
wjson('MANIFEST.json',{'window_id':WINDOW,'batch_id':BATCH,'snapshot_id':SNAP,'generated_at':NOW,'status':'CONTINUE_DATA_GAP','claim_level_max':1,'no_nested_zip':True,'files':files,'self_hash_policy':'MANIFEST included in CHECKSUMS; CHECKSUMS excludes itself'})
lines=[]
for p in sorted(x for x in OUT.rglob('*') if x.is_file() and x.name!='CHECKSUMS.sha256'):lines.append(f'{hfile(p)}  {p.relative_to(OUT).as_posix()}')
wtext('CHECKSUMS.sha256','\n'.join(lines))
print(json.dumps({'artifact':str(OUT),'snapshot_id':SNAP,'file_count':len(list(OUT.rglob('*'))),'status':'CONTINUE_DATA_GAP'},indent=2))
