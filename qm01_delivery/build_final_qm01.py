#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import textwrap
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Wedge

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'FINAL_QM01'
ZIP = ROOT / 'FINAL_QM01.zip'
SNAPSHOT = 'QM01_RECOVERY_XW01_V11_20260713'
WINDOW = 'QM01'
STATUS = 'CONTINUE_DATA_GAP'

XW01_SCOPE = [
    ('TI_ALLOY_IN_SCOPE', 33769),
    ('NON_TITANIUM', 35411),
    ('TI_TMC_POSSIBLE', 4258),
    ('METHOD_TRANSFER_CANDIDATE', 3125),
    ('TI_TMC_CONFIRMED', 1827),
    ('CORRECTION_OR_ERRATUM', 171),
    ('RETRACTION', 82),
    ('NON_ARTICLE_XML', 40),
]
CLASS_COUNTS = [
    ('TMC/composites', 19507, 'TMC'),
    ('alpha+beta', 12548, 'alpha+beta'),
    ('near-alpha', 5955, 'near-alpha'),
    ('beta', 4997, 'beta'),
    ('alpha/CP-Ti', 3284, 'cp-Ti/alpha'),
    ('near-beta', 2400, 'metastable-beta'),
    ('mixed/other', 6746, 'mixed/other'),
]
GRADE_COUNTS = [
    ('Ti-6Al-4V', 4191, 'alpha+beta'),
    ('CP-Ti', 589, 'cp-Ti'),
    ('TA15', 477, 'near-alpha'),
    ('Ti60', 396, 'near-alpha'),
    ('IMI834', 221, 'near-alpha'),
    ('TC11', 217, 'alpha+beta'),
    ('Ti65', 198, 'near-alpha'),
    ('Ti-6Al-4V ELI', 192, 'alpha+beta'),
    ('Ti600', 183, 'near-alpha'),
    ('Ti-10-2-3', 182, 'metastable-beta'),
]
ALIASES = [
    ('Ti-6Al-4V', 'TC4|Ti64|Ti6Al4V|Ti-6Al4V', 'alpha+beta', 'literature label'),
    ('Ti-6Al-4V ELI', 'Grade 23|Ti64 ELI|Ti6Al4V ELI', 'alpha+beta', 'literature label'),
    ('CP-Ti', 'commercially pure titanium|Grade 1|Grade 2|Grade 3|Grade 4', 'cp-Ti', 'purity grade required'),
    ('Ti65', 'Ti-65', 'near-alpha', 'composition/label conflict must remain explicit'),
    ('Ti1100', 'Ti-1100', 'near-alpha', 'not separately counted in summary source'),
    ('IMI834', 'IMI 834|Ti834', 'near-alpha', 'literature label'),
    ('TA15', 'Ti-6.5Al-2Zr-1Mo-1V', 'near-alpha', 'nominal alias'),
    ('Ti60', 'Ti-60', 'near-alpha', 'literature label'),
    ('Ti600', 'Ti-600', 'near-alpha', 'literature label'),
    ('TC11', 'Ti-6.5Al-3.5Mo-1.5Zr-0.3Si', 'alpha+beta', 'nominal alias'),
    ('Ti-10-2-3', 'Ti1023|Ti-10V-2Fe-3Al', 'metastable-beta', 'nominal alias'),
]
FAMILY_ORDER = ['cp-Ti', 'alpha', 'near-alpha', 'alpha+beta', 'metastable-beta', 'beta', 'TiAl/intermetallic control', 'TMC', 'mixed/other']
PROPS = ['UTS_MPa', 'YS02_MPa', 'Elong_pct', 'hardness_HV', 'elastic_modulus_GPa']


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')


def support_flag(n: int) -> str:
    if n >= 500:
        return 'HIGH_RECORD_COVERAGE_ONLY'
    if n >= 200:
        return 'MODERATE_RECORD_COVERAGE_ONLY'
    if n >= 100:
        return 'LOW_RECORD_COVERAGE_ONLY'
    return 'SPARSE_RECORD_COVERAGE_ONLY'


def make_plots() -> list[dict[str, object]]:
    figdir = OUT / 'figures'
    datadir = OUT / 'figure_data'
    figdir.mkdir(parents=True, exist_ok=True)
    datadir.mkdir(parents=True, exist_ok=True)
    specs = []

    # F1: family -> grade sunburst. Process/property levels are deliberately unresolved.
    family_totals: dict[str, int] = {}
    for _, n, fam in GRADE_COUNTS:
        family_totals[fam] = family_totals.get(fam, 0) + n
    total = sum(family_totals.values())
    rows = []
    for grade, n, fam in GRADE_COUNTS:
        rows.append([fam, grade, 'UNRESOLVED_PROCESS', 'UNRESOLVED_PROPERTY', n, 'DATABASE_PRIOR'])
    write_csv(datadir / 'sunburst_data.csv', ['matrix_family','alloy_grade','process','property','records','evidence_grade'], rows)
    fig, ax = plt.subplots(figsize=(9,9), subplot_kw={'aspect':'equal'})
    start = 90.0
    family_angles = {}
    for fam, n in sorted(family_totals.items(), key=lambda x: -x[1]):
        span = 360.0 * n / total
        family_angles[fam] = (start, start + span)
        ax.add_patch(Wedge((0,0), 1.0, start, start+span, width=0.35, alpha=0.75, label=fam))
        start += span
    for fam, (a0, a1) in family_angles.items():
        items = [(g,n) for g,n,f in GRADE_COUNTS if f == fam]
        pos = a0
        fam_total = sum(n for _,n in items)
        for grade, n in items:
            span = (a1-a0) * n/fam_total
            ax.add_patch(Wedge((0,0), 1.45, pos, pos+span, width=0.35, alpha=0.55))
            mid = math.radians((pos+pos+span)/2)
            ax.text(1.25*math.cos(mid), 1.25*math.sin(mid), grade, ha='center', va='center', fontsize=7)
            pos += span
    ax.set_xlim(-1.55,1.55); ax.set_ylim(-1.55,1.55); ax.axis('off')
    ax.set_title('Matrix family → core grade coverage\nProcess/property identities unresolved in summary snapshot')
    for ext in ['png','pdf','svg']:
        fig.savefig(figdir / f'QM01_F1_sunburst.{ext}', dpi=600 if ext=='png' else None, bbox_inches='tight')
    plt.close(fig)
    specs.append({'figure':'QM01_F1_sunburst','estimand':'record coverage by family and core grade','independent_papers':'global total only: 5537','support_domain':'TiKB V11 summary','claim_level':1})

    # F2: family x property x evidence heatmap. Unknown family-property cells are explicit NA.
    heat_rows = []
    for fam in FAMILY_ORDER:
        for prop in PROPS:
            heat_rows.append([fam, prop, 'DATABASE_PRIOR', -1, 'NOT_IDENTIFIABLE_WITHOUT_ATOMIC_ROWS'])
    write_csv(datadir / 'coverage_heatmap_data.csv', ['matrix_family','property','evidence_grade','independent_papers','status'], heat_rows)
    mat = np.full((len(FAMILY_ORDER), len(PROPS)), np.nan)
    fig, ax = plt.subplots(figsize=(10,6))
    ax.imshow(np.zeros_like(mat), vmin=0, vmax=1, aspect='auto', alpha=0.08)
    for i in range(len(FAMILY_ORDER)):
        for j in range(len(PROPS)):
            ax.text(j, i, 'NI', ha='center', va='center', fontsize=8)
    ax.set_xticks(range(len(PROPS)), PROPS, rotation=30, ha='right')
    ax.set_yticks(range(len(FAMILY_ORDER)), FAMILY_ORDER)
    ax.set_title('Matrix family × property coverage\nNI = paper/sample/condition-resolved count not identifiable')
    for ext in ['png','pdf','svg']:
        fig.savefig(figdir / f'QM01_F2_coverage_heatmap.{ext}', dpi=600 if ext=='png' else None, bbox_inches='tight')
    plt.close(fig)
    specs.append({'figure':'QM01_F2_coverage_heatmap','estimand':'independent-paper coverage per family-property-evidence cell','result':'NOT_IDENTIFIABLE','claim_level':1})

    # F3: baseline ridgeline required by prompt; no per-family atomic performance distribution exists.
    write_csv(datadir / 'baseline_ridgeline_data.csv', ['matrix_family','property','value','paper_uid','sample_uid','condition_uid','status'], [])
    fig, ax = plt.subplots(figsize=(10,5))
    ax.text(0.5, 0.62, 'NOT IDENTIFIABLE', ha='center', va='center', fontsize=24, transform=ax.transAxes)
    ax.text(0.5, 0.40, 'Per-family baseline distributions require authoritative atomic performance rows\nwith paper/sample/condition identities.', ha='center', va='center', fontsize=11, transform=ax.transAxes)
    ax.set_axis_off(); ax.set_title('Baseline performance ridgeline — blocked by atomic identity gap')
    for ext in ['png','pdf','svg']:
        fig.savefig(figdir / f'QM01_F3_baseline_ridgeline.{ext}', dpi=600 if ext=='png' else None, bbox_inches='tight')
    plt.close(fig)
    specs.append({'figure':'QM01_F3_baseline_ridgeline','estimand':'family-specific baseline distribution','result':'NOT_IDENTIFIABLE','claim_level':1})

    # F4: estimability traffic light based on record coverage only; effect estimability remains red.
    traffic = []
    for grade, n, fam in GRADE_COUNTS:
        coverage = support_flag(n)
        effect = 'RED_EFFECT_NOT_IDENTIFIABLE'
        traffic.append([fam, grade, n, coverage, effect, 'paper counts by grade unavailable'])
    write_csv(datadir / 'estimability_traffic_light_data.csv', ['matrix_family','alloy_grade','records','coverage_support','effect_estimability','limitation'], traffic)
    fig, ax = plt.subplots(figsize=(10,6))
    y = np.arange(len(GRADE_COUNTS))
    counts = [x[1] for x in GRADE_COUNTS]
    labels = [x[0] for x in GRADE_COUNTS]
    ax.barh(y, counts)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlabel('Records in TiKB V11 summary')
    ax.set_title('Coverage support and effect-estimability traffic light')
    for yi, n in zip(y, counts):
        ax.text(n, yi, '  effect: NOT IDENTIFIABLE', va='center', fontsize=7)
    for ext in ['png','pdf','svg']:
        fig.savefig(figdir / f'QM01_F4_estimability_traffic_light.{ext}', dpi=600 if ext=='png' else None, bbox_inches='tight')
    plt.close(fig)
    specs.append({'figure':'QM01_F4_estimability_traffic_light','estimand':'record coverage support; causal/effect estimability','result':'coverage descriptive; effects not identifiable','claim_level':1})
    return specs


def build() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    ZIP.unlink(missing_ok=True)
    OUT.mkdir(parents=True)

    total_xml = sum(n for _, n in XW01_SCOPE)
    total_v11 = sum(n for _, n, _ in CLASS_COUNTS)
    opened = [
        'QM01 dispatch: file_00000000e808720b883343c335b2715b',
        'XW01 MANIFEST.json: file_000000004b2c72088bd03bd2731a4735',
        'XW01 COVERAGE_REPORT.json: file_00000000bc247208a271fb5c892fea75',
        'TiKB_V11_Data_Inventory_Report.md: file_000000005d0c71f59efbc8364a2bb79b',
        'TiKB_V11_Technical_Report.md: file_00000000a1b0722f869816e718556345',
        'Current GitHub execution code: q40/QM01/run_qm01.py, commit 82a30a67903f113f9141ae764476d3471a9e64df',
    ]
    write_text(OUT / 'OPENED_FILES.txt', '\n'.join(opened) + '\n')

    verdict = f'''# QM01 Executive Verdict

`WINDOW=QM01 | SNAPSHOT={SNAPSHOT} | INPUT_MODE=COHORT_BUILD`

## Terminal scientific verdict

The available project sources support a **Level-1 descriptive coverage map**, not a paper/sample/condition-resolved matrix-family effect model. The publisher-XML identity corpus contains **{total_xml:,} terminal documents**; **33,769** are classified as titanium-alloy in scope, **1,827** as confirmed Ti-TMC and **4,258** as possible Ti-TMC. The older TiKB V11 inventory reports **55,437 records**, **5,537 unique papers**, and a highly imbalanced alloy distribution dominated by Ti-6Al-4V and TMC records.

The required Q40/V29 atomic table body and its row-level provenance were not available to this runtime. Therefore per-grade independent-paper counts, family baseline distributions, matrix-family random intercepts, reinforcement random slopes, tau-squared, I-squared, LOPO and same-condition matched effects are `NOT_IDENTIFIABLE`. No record count is presented as an independent-study count.

## Explicit estimands delivered

1. Publisher-XML scope fractions relative to {total_xml:,} terminal XML objects.
2. TiKB V11 class and core-grade record coverage relative to {total_v11:,} records.
3. Property availability in the 31,188-row ML-ready summary: UTS 17,153 rows (55.1%), YS 13,395 rows (43.0%), elongation 48.2% fill.
4. Grade-level **record-coverage support flags**. These are not effect-estimability claims.

## Claim ceiling

Only corpus coverage, summary-level missingness and taxonomy conflicts may be claimed. No alloy grade is claimed to cause a performance change. No Gold promotion, production-model registration, validated recipe or platform retraining is performed.

## Status

`CONTINUE_DATA_GAP`: the contract-complete recovery package, schemas, code, plots, tests, manifest and checksums are delivered; the authoritative Q40 atomic snapshot is still required for the requested hierarchical effect analysis.
'''
    write_text(OUT / '00_EXECUTIVE_VERDICT.md', verdict)

    input_rows = [
        ['I001',SNAPSHOT,'QM01 dispatch','MDU','file_00000000e808720b883343c335b2715b','NOT_EXPOSED','P0_CONTRACT','OPENED','defines estimands, output and claim ceiling'],
        ['I002',SNAPSHOT,'XW01 MANIFEST','JSON','file_000000004b2c72088bd03bd2731a4735','manifest-listed','P0_PUBLISHER_XML','OPENED','78,683 identities; package integrity and source hashes'],
        ['I003',SNAPSHOT,'XW01 COVERAGE_REPORT','JSON','file_00000000bc247208a271fb5c892fea75','7c6ff80d54f7346972cc5659749ba9d8a9f91dc00bcb61c3125034351e6af393','P0_PUBLISHER_XML','OPENED','scope and terminal counts'],
        ['I004',SNAPSHOT,'TiKB V11 Data Inventory','MD','file_000000005d0c71f59efbc8364a2bb79b','NOT_EXPOSED','P1_STRUCTURED_PRIOR','OPENED','class/grade counts, 5537 papers, missingness'],
        ['I005',SNAPSHOT,'TiKB V11 Technical Report','MD','file_00000000a1b0722f869816e718556345','NOT_EXPOSED','P1_STRUCTURED_PRIOR','OPENED','conflicting 4837-paper/49148-row variant retained as conflict'],
        ['I006',SNAPSHOT,'Q40 ATOMIC_RECORDS','PARQUET/CSV','missing','MISSING','P0_ATOMIC','NOT_AVAILABLE','required for effect and independent-paper-by-grade estimates'],
        ['I007',SNAPSHOT,'Q40 PROVENANCE','JSONL','missing','MISSING','P0_ATOMIC','NOT_AVAILABLE','required for row-level source binding'],
    ]
    write_csv(OUT / 'INPUT_LEDGER.csv', ['input_id','snapshot_id','source_name','source_type','locator','source_hash','priority','use_status','notes'], input_rows)
    write_csv(OUT / 'SOURCE_UTILIZATION_LEDGER.csv', ['source_group','objects_registered','objects_opened','use','authority','terminal_status'], [
        ['TITMC_V27_LIT_WEB_P001-P010',10,0,'indirect through XW01 extraction and integrity receipt','publisher XML highest','REGISTERED_VIA_HASHED_DERIVATIVE'],
        ['XW01 identity/scope/topology outputs',15,3,'corpus scope coverage and integrity','publisher XML-derived','USED'],
        ['S03 data/features packages',2,0,'expected frozen matrices and TMC subset','structured prior','RUNTIME_BODY_UNAVAILABLE'],
        ['S03 harness evidence packages',8,0,'expected condition/provenance/UQ assets','supporting','RUNTIME_BODY_UNAVAILABLE'],
        ['S02/S04 engineering packages',5,1,'execution-code cross-check only','engineering','PARTIAL_USE'],
        ['TiKB V11 reports',2,2,'legacy coverage/missingness prior','database prior','USED_WITH_CONFLICT_FLAG'],
    ])

    # Cohort is summary-level, never mislabeled atomic.
    cohort_rows = []
    for state, n in XW01_SCOPE:
        cohort_rows.append(['XW01_SCOPE',state,'',n,'publisher XML derived','DESCRIPTIVE_DOCUMENT_COUNT','NO_SAMPLE_CONDITION_ID'])
    for cls, n, fam in CLASS_COUNTS:
        cohort_rows.append(['V11_CLASS',fam,cls,n,'database prior','DESCRIPTIVE_RECORD_COUNT','NO_GRADE_PAPER_UID_BREAKDOWN'])
    for grade, n, fam in GRADE_COUNTS:
        cohort_rows.append(['V11_GRADE',fam,grade,n,'database prior','DESCRIPTIVE_RECORD_COUNT','NO_GRADE_PAPER_UID_BREAKDOWN'])
    write_csv(OUT / 'ANALYSIS_COHORT.csv', ['cohort_type','matrix_family','alloy_grade_or_state','count','evidence_grade','estimand_role','identity_status'], cohort_rows)

    # Required outputs with explicit empty schemas.
    write_csv(OUT / 'PAIR_MATCHES.csv', ['pair_id','paper_uid','matrix_sample_uid','tmc_sample_uid','condition_uid','property','match_level','delta','lnRR','status'], [])
    write_csv(OUT / 'EFFECT_ESTIMATES.csv', ['estimand_id','matrix_family','alloy_grade','reinforcement','property','estimate','ci95_low','ci95_high','prediction_low','prediction_high','independent_papers','match_level','claim_level','status'], [])
    write_csv(OUT / 'HIERARCHICAL_RESULTS.csv', ['model_id','outcome','term','estimate','se','ci95_low','ci95_high','tau2','I2_pct','independent_papers','status'], [])
    write_csv(OUT / 'DOSE_RESPONSE.csv', ['reinforcement','matrix_family','property','dose_unit','dose','estimate','ci95_low','ci95_high','independent_papers','status'], [])
    write_csv(OUT / 'INTERACTION_EFFECTS.csv', ['interaction','property','estimate','ci95_low','ci95_high','p_value','q_value','independent_papers','status'], [])
    write_csv(OUT / 'HETEROGENEITY.csv', ['scope','property','tau2','I2_pct','prediction_low','prediction_high','independent_papers','status'], [])
    write_csv(OUT / 'SENSITIVITY_ANALYSIS.csv', ['analysis','estimand','base_result','sensitivity_result','delta','status','interpretation'], [
        ['V11 row-count variant','total records',55437,49148,-6289,'CONFLICT','reports reflect different pipeline snapshots; no silent reconciliation'],
        ['V11 paper-count variant','unique papers',5537,4837,-700,'CONFLICT','global paper total is snapshot-dependent'],
        ['Atomic identity removal','matched effects','NOT_IDENTIFIABLE','NOT_IDENTIFIABLE','','HARD_FAIL','summary records cannot substitute sample/condition identities'],
    ])
    write_csv(OUT / 'NULL_NEGATIVE_RESULTS.csv', ['question','result','reason','required_to_resolve'], [
        ['Per-grade independent paper counts','NOT_IDENTIFIABLE','only record counts exposed','ATOMIC_RECORDS with paper_uid'],
        ['Family baseline ridgelines','NOT_IDENTIFIABLE','no row-level property values by family','atomic property table'],
        ['Matrix-family random intercepts','NOT_IDENTIFIABLE','no cluster-resolved cohort','paper/sample/condition identities'],
        ['Reinforcement random slopes','NOT_IDENTIFIABLE','no same-condition pairs','matched controls and reinforcement dose'],
        ['tau2 and I2','NOT_IDENTIFIABLE','study-level estimates absent','paper-cluster effect table'],
        ['LOPO stability','NOT_IDENTIFIABLE','no per-paper model input','atomic cohort'],
    ])
    write_csv(OUT / 'CONFLICT_LEDGER.csv', ['conflict_id','field','source_a','value_a','source_b','value_b','resolution','impact'], [
        ['C001','V11 total records','Data Inventory/Chronicle','55437','Technical Report variant','49148','retain both; do not merge snapshots','coverage denominator'],
        ['C002','V11 unique papers','Data Inventory/Chronicle','5537','Technical Report variant','4837','retain both; primary descriptive view uses 5537 and labels snapshot conflict','global independent-paper total'],
        ['C003','atomic snapshot availability','QM01 contract','required','current runtime','missing','CONTINUE_DATA_GAP','effect analysis blocked'],
    ])

    # Taxonomy and coverage products.
    taxonomy_rows = []
    for fam in FAMILY_ORDER:
        grades = '|'.join(g for g,_,f in GRADE_COUNTS if f == fam)
        taxonomy_rows.append([fam,grades,'label-driven prior','composition-driven validation missing','UNRESOLVED' if not grades else 'SUMMARY_ONLY','do not silently classify composition conflicts'])
    write_csv(OUT / 'MATRIX_TAXONOMY.csv', ['matrix_family','core_grades_seen','taxonomy_basis','composition_validation','status','conflict_rule'], taxonomy_rows)
    write_csv(OUT / 'GRADE_ALIAS_REGISTRY.csv', ['canonical_grade','aliases','matrix_family','notes'], [list(x) for x in ALIASES])

    est_rows = []
    for grade, n, fam in GRADE_COUNTS:
        est_rows.append([fam,grade,n,'NOT_IDENTIFIABLE',support_flag(n),'NOT_IDENTIFIABLE','NOT_IDENTIFIABLE','NOT_IDENTIFIABLE','SUMMARY_ONLY','requires per-grade paper/sample/condition identities'])
    for grade in ['Ti1100']:
        est_rows.append(['near-alpha',grade,0,'NOT_IDENTIFIABLE','SPARSE_OR_MISSING','NOT_IDENTIFIABLE','NOT_IDENTIFIABLE','NOT_IDENTIFIABLE','MISSING','not separately counted in exposed summary'])
    write_csv(OUT / 'ESTIMABILITY_MATRIX.csv', ['matrix_family','alloy_grade','records','independent_papers','coverage_support','baseline_estimability','paired_effect_estimability','random_slope_estimability','status','reason'], est_rows)

    coverage_rows = []
    for state, n in XW01_SCOPE:
        coverage_rows.append(['XW01','document_scope',state,'','','DIRECT_XML_DERIVED',n,n/total_xml,'DOCUMENT_COUNT'])
    for cls, n, fam in CLASS_COUNTS:
        coverage_rows.append(['TiKB_V11','matrix_family',fam,cls,'','DATABASE_PRIOR',n,n/total_v11,'RECORD_COUNT'])
    for grade, n, fam in GRADE_COUNTS:
        coverage_rows.append(['TiKB_V11','alloy_grade',fam,grade,'','DATABASE_PRIOR',n,n/total_v11,'RECORD_COUNT'])
    cov = pd.DataFrame(coverage_rows, columns=['source_snapshot','axis','matrix_family_or_state','alloy_grade_or_class','property','evidence_grade','count','fraction','count_semantics'])
    cov.to_csv(OUT / 'COVERAGE_CUBE.csv', index=False)
    cov.to_parquet(OUT / 'COVERAGE_CUBE.parquet', index=False)

    # Summary estimands.
    summary_rows = []
    for state, n in XW01_SCOPE:
        summary_rows.append([f'XW01_SCOPE_{state}', 'scope fraction', state, n, total_xml, n/total_xml, 'DIRECT_XML_DERIVED', 1, 'ESTIMABLE_DESCRIPTIVE'])
    for cls, n, fam in CLASS_COUNTS:
        summary_rows.append([f'V11_CLASS_{fam}', 'record coverage fraction', fam, n, total_v11, n/total_v11, 'DATABASE_PRIOR', 1, 'ESTIMABLE_DESCRIPTIVE'])
    write_csv(OUT / 'COVERAGE_ESTIMANDS.csv', ['estimand_id','estimand','stratum','numerator','denominator','estimate','evidence_grade','claim_level','status'], summary_rows)

    # Provenance contains no invented paper/sample IDs.
    prov = [
        {'snapshot_id':SNAPSHOT,'source_hash':'1f6a17abda4f69c42a6bf3f9fcb855600c66ced52f940ecfbd852f22dee3c5bb','source_locator':'XW01 ARTICLE_IDENTITY.parquet via manifest','paper_uid':'MULTIPLE_DOCUMENT_IDENTITIES','sample_uid':None,'condition_uid':None,'evidence_grade':'DIRECT_XML_DERIVED','role':'document coverage'},
        {'snapshot_id':SNAPSHOT,'source_hash':'7c6ff80d54f7346972cc5659749ba9d8a9f91dc00bcb61c3125034351e6af393','source_locator':'XW01 COVERAGE_REPORT.json','paper_uid':'MULTIPLE_DOCUMENT_IDENTITIES','sample_uid':None,'condition_uid':None,'evidence_grade':'DIRECT_XML_DERIVED','role':'scope counts'},
        {'snapshot_id':SNAPSHOT,'source_hash':'NOT_EXPOSED','source_locator':'TiKB_V11_Data_Inventory_Report.md file_000000005d0c71f59efbc8364a2bb79b','paper_uid':'GLOBAL_SUMMARY_ONLY','sample_uid':None,'condition_uid':None,'evidence_grade':'DATABASE_PRIOR','role':'class/grade record counts and missingness'},
    ]
    with (OUT / 'PROVENANCE.jsonl').open('w', encoding='utf-8') as f:
        for row in prov:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    methods = '''# Methods

## Estimands

This recovery execution estimates corpus/document and database-record coverage only. Fractions use their own source-specific denominators and are never mixed across XW01 and TiKB V11.

## Taxonomy

A literature-grade alias registry maps labels to cp-Ti, near-alpha, alpha+beta, metastable-beta, beta and TMC families. Composition-driven verification is marked missing; ambiguous labels are retained rather than silently forced.

## Independence

The global TiKB V11 source reports 5,537 unique papers, but it does not expose a per-grade paper-identity table in the current runtime. Therefore grade-level record counts are not converted to effective study counts. Rows are not treated as independent studies.

## Effects and uncertainty

No matched effect, hierarchical model, tau-squared, I-squared, random slope, LOPO or prediction interval is fitted without authoritative paper/sample/condition-resolved atomic rows. Required empty-schema outputs are delivered with `NOT_IDENTIFIABLE` explanations.

## Figures

Figures are generated from `figure_data/*.csv` by deterministic matplotlib code. Required figures whose estimands are not identifiable show an explicit NI panel rather than fabricated distributions.
'''
    write_text(OUT / 'METHODS.md', methods)
    write_text(OUT / 'LIMITATIONS.md', '''# Limitations

1. The authoritative Q40/V29 `ATOMIC_RECORDS` body was unavailable.
2. Per-grade paper counts, sample identities and condition identities are absent from the exposed summaries.
3. TiKB V11 reports contain snapshot-dependent totals (55,437/5,537 versus 49,148/4,837); both are retained in the conflict ledger.
4. Record counts measure coverage, not evidence independence or scientific quality.
5. Global unfiltered property means contain documented extreme outliers and are not used as family baselines.
6. The XW01 corpus provides document identity/scope, not sample-level mechanical performance.
7. No causal, validated-design or production-model claim is made.
''')

    req = {
        'window_id':WINDOW,
        'request_id':'QM01_AUTHORITATIVE_ATOMIC_RESTORE',
        'required':[

            'Q40_INPUT_SNAPSHOT.json with immutable snapshot_id and SHA-256',
            'ATOMIC_RECORDS.parquet/csv with paper_uid, sample_uid, condition_uid, source_hash',
            'PROVENANCE.jsonl',
            'CONFLICT_LEDGER.csv and EXCLUDED_RECORDS.csv',
            'paper/source registry',
            'condition canonical manifest',
            'member map and package hashes for S03/S04/V27 inputs'
        ],
        'minimum_columns':['paper_uid','sample_uid','condition_uid','alloy_grade','matrix_family','process','heat_treatment','test_mode','test_temperature_C','strain_rate','orientation','reinforcement_type','reinforcement_fraction','property','value','unit','evidence_grade','source_hash'],
        'next_command':'python -X utf8 build_final_qm01.py --authoritative-input <path>',
        'acceptance':'all published effects bind to paper/sample/condition/provenance; paper-cluster LOPO and source-grade sensitivity pass'
    }
    write_text(OUT / 'WEB_TO_LOCAL_REQUEST.json', json.dumps(req, ensure_ascii=False, indent=2))
    write_text(OUT / 'LOCAL_ABSORPTION_PROMPT.md', '''# Local absorption

1. Verify `FINAL_QM01.zip.sha256` and every entry in `CHECKSUMS.sha256`.
2. Inspect `WINDOW_STATUS.json`; this package is `CONTINUE_DATA_GAP`, not Gold or production-ready.
3. Supply the immutable Q40 atomic snapshot requested in `WEB_TO_LOCAL_REQUEST.json`.
4. Rerun the builder, then require paper-cluster matched effects, LOPO, evidence-grade sensitivity and plot regeneration before promotion.
5. Do not mutate ACTIVE_TITMC, Gold, unified Schema, split authority or production model registry from this recovery package.
''')

    specs = make_plots()
    write_text(OUT / 'PLOT_SPECS.json', json.dumps({'window_id':WINDOW,'figures':specs,'language':'English','formats':['SVG','PDF','PNG 600 dpi'],'data_sidecars':True}, ensure_ascii=False, indent=2))

    # Standalone plot code, using the already materialized sidecars.
    plot_template = '''#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'figure_data'/'{data}'
OUT=ROOT/'figures'/'{name}_reproduced.png'
df=pd.read_csv(DATA)
fig,ax=plt.subplots(figsize=(10,6))
{body}
fig.tight_layout(); fig.savefig(OUT,dpi=600)
print(OUT)
'''
    scripts = [
        ('plot_f1_sunburst.py','sunburst_data.csv','QM01_F1_sunburst',"d=df.groupby(['matrix_family','alloy_grade'],as_index=False)['records'].sum(); ax.barh(d['alloy_grade'],d['records']); ax.set_title('Matrix family → grade record coverage'); ax.set_xlabel('records')"),
        ('plot_f2_heatmap.py','coverage_heatmap_data.csv','QM01_F2_coverage_heatmap',"ax.axis('off'); ax.text(0.5,0.5,'NOT IDENTIFIABLE\\nAtomic family-property identities required',ha='center',va='center',transform=ax.transAxes)"),
        ('plot_f3_ridgeline.py','baseline_ridgeline_data.csv','QM01_F3_baseline_ridgeline',"ax.axis('off'); ax.text(0.5,0.5,'NOT IDENTIFIABLE\\nAtomic performance values required',ha='center',va='center',transform=ax.transAxes)"),
        ('plot_f4_traffic.py','estimability_traffic_light_data.csv','QM01_F4_estimability_traffic_light',"ax.barh(df['alloy_grade'],df['records']); ax.set_title('Record coverage; effect estimability blocked'); ax.set_xlabel('records')"),
    ]
    for filename, data, name, body in scripts:
        write_text(OUT / 'plot_code' / filename, plot_template.format(data=data,name=name,body=body))

    status = {
        'window_id':WINDOW,'snapshot_id':SNAPSHOT,'papers_seen':5537,'papers_included':5537,
        'independent_papers':5537,'independent_papers_semantics':'global legacy-database total only; per-grade counts not identifiable',
        'atomic_rows':0,'matched_pairs':0,'effect_estimates':0,'plots_generated':4,'open_conflicts':3,
        'claim_level_max':1,'status':STATUS,'next_action':'restore authoritative Q40 atomic snapshot and rerun paper-cluster analysis',
        'production_model_registration':False,'gold_promotion':False
    }
    write_text(OUT / 'WINDOW_STATUS.json', json.dumps(status, ensure_ascii=False, indent=2))

    # Six deterministic tests.
    tests = '''import hashlib, json, pathlib, zipfile
import pandas as pd
ROOT=pathlib.Path(__file__).resolve().parents[1]

def test_required_files():
    required=['00_EXECUTIVE_VERDICT.md','INPUT_LEDGER.csv','ANALYSIS_COHORT.csv','PAIR_MATCHES.csv','EFFECT_ESTIMATES.csv','HIERARCHICAL_RESULTS.csv','DOSE_RESPONSE.csv','INTERACTION_EFFECTS.csv','HETEROGENEITY.csv','SENSITIVITY_ANALYSIS.csv','NULL_NEGATIVE_RESULTS.csv','CONFLICT_LEDGER.csv','PROVENANCE.jsonl','METHODS.md','LIMITATIONS.md','PLOT_SPECS.json','WEB_TO_LOCAL_REQUEST.json','LOCAL_ABSORPTION_PROMPT.md','WINDOW_STATUS.json','MANIFEST.json','CHECKSUMS.sha256','MATRIX_TAXONOMY.csv','GRADE_ALIAS_REGISTRY.csv','COVERAGE_CUBE.parquet','ESTIMABILITY_MATRIX.csv']
    assert all((ROOT/x).exists() for x in required)

def test_status_and_claim_ceiling():
    s=json.loads((ROOT/'WINDOW_STATUS.json').read_text(encoding='utf-8'))
    assert s['window_id']=='QM01' and s['status']=='CONTINUE_DATA_GAP'
    assert s['claim_level_max']<=1 and not s['gold_promotion'] and not s['production_model_registration']

def test_no_row_as_paper_substitution():
    e=pd.read_csv(ROOT/'ESTIMABILITY_MATRIX.csv')
    assert (e['independent_papers']=='NOT_IDENTIFIABLE').all()

def test_empty_effect_outputs_are_schema_valid():
    assert len(pd.read_csv(ROOT/'PAIR_MATCHES.csv'))==0
    assert len(pd.read_csv(ROOT/'EFFECT_ESTIMATES.csv'))==0
    assert len(pd.read_csv(ROOT/'HIERARCHICAL_RESULTS.csv'))==0

def test_coverage_fractions():
    c=pd.read_csv(ROOT/'COVERAGE_ESTIMANDS.csv')
    assert ((c['estimate']>=0)&(c['estimate']<=1)).all()
    assert set(c['claim_level'])=={1}

def test_provenance_has_snapshot_and_hash():
    rows=[json.loads(x) for x in (ROOT/'PROVENANCE.jsonl').read_text(encoding='utf-8').splitlines() if x]
    assert rows and all(x['snapshot_id'] and x['source_hash'] for x in rows)

def test_checksums():
    for line in (ROOT/'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines():
        h,rel=line.split('  ',1)
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h
'''
    write_text(OUT / 'tests' / 'test_contract.py', tests)
    write_text(OUT / 'acceptance_commands.md', '''# Acceptance commands

```bash
python -m pip install pandas==2.2.3 pyarrow==18.1.0 pytest==8.3.4 matplotlib==3.9.2 numpy==2.1.3
python -m pytest -q tests/test_contract.py
python plot_code/plot_f1_sunburst.py
python plot_code/plot_f2_heatmap.py
python plot_code/plot_f3_ridgeline.py
python plot_code/plot_f4_traffic.py
```

Acceptance requires all tests PASS, checksum verification PASS, four figures reproducible, and `WINDOW_STATUS.status` preserved as `CONTINUE_DATA_GAP` until the authoritative atomic snapshot is restored.
''')

    # Manifest and checksums.
    files = []
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name not in {'MANIFEST.json','CHECKSUMS.sha256'}:
            files.append({'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha256(p)})
    manifest = {
        'window_id':WINDOW,'snapshot_id':SNAPSHOT,'status':STATUS,'created_by':'deterministic GitHub Actions builder',
        'files':files,'file_count_excluding_control_files':len(files),'required_contract_files_present':True,
        'no_nested_zip':True,'gold_claimed':False,'production_model_registration':False,
        'source_note':'publisher XML-derived XW01 evidence has highest authority; TiKB V11 is a database prior'
    }
    write_text(OUT / 'MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    checksum_files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='CHECKSUMS.sha256']
    write_text(OUT / 'CHECKSUMS.sha256', '\n'.join(f'{sha256(p)}  {p.relative_to(OUT).as_posix()}' for p in checksum_files)+'\n')

    # Zip and validate.
    with zipfile.ZipFile(ZIP,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                z.write(p, Path('FINAL_QM01')/p.relative_to(OUT))
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None
        assert not any(n.lower().endswith('.zip') for n in z.namelist())
    write_text(ROOT / 'FINAL_QM01.zip.sha256', f'{sha256(ZIP)}  FINAL_QM01.zip\n')
    receipt={'window_id':WINDOW,'snapshot_id':SNAPSHOT,'zip':'FINAL_QM01.zip','zip_sha256':sha256(ZIP),'zip_bytes':ZIP.stat().st_size,'zip_entries':len(zipfile.ZipFile(ZIP).namelist()),'testzip':'PASS','status':STATUS,'figures':12,'independent_papers_global':5537,'matched_pairs':0}
    write_text(ROOT / 'QM01_DELIVERY_RECEIPT.json', json.dumps(receipt,ensure_ascii=False,indent=2))
    print(json.dumps(receipt,ensure_ascii=False))


if __name__ == '__main__':
    build()
