# Materials Evidence Stack

Minimal evidence-linked data model, source-bound answer demo, and evaluation scaffold for materials AI research.

## Why This Exists

Materials AI systems often produce answers that are hard to audit: a property value may come from a paper table, a figure caption, a patent claim, or a secondary summary, but the generated answer may not preserve that source chain. This project provides a small open-source evidence model and demo pipeline for keeping AI outputs tied to source evidence.

This public repository is intentionally small. It is derived from experience building larger local/private materials-evidence workflows for titanium alloy and titanium matrix composite research, including TiKB / TiForge-style schema design, provenance tracking, field lineage, quality gates, uncertainty labels, and audit records. The public seed keeps only reproducible demo fixtures and testable code so that it can be reviewed without private PDFs, closed datasets, credentials, or unverifiable model-performance claims.

The first target is simple and reproducible:

1. Represent source documents with provenance.
2. Represent structured materials facts with evidence spans.
3. Answer questions with explicit evidence links.
4. Evaluate whether each answer is source-bound.

## Maintainer Context

Maintainer: Ranxing Chu, PhD student in the School of Materials Science and Engineering, Harbin Institute of Technology.

Research context:

- AI-driven titanium matrix composite design.
- Laser-directed energy deposition (L-DED) process-structure-property evidence chains.
- Ti/TiBw/LDED literature extraction and source-grounded materials RAG.
- Titanium Knowledge Base (TiKB) style data infrastructure for experimental materials records.
- Evidence quality workflows for noisy scientific text, tables, figures, units, microstructure descriptions, and process-property records.
- Uncertainty-aware extraction and answer evaluation, with emphasis on source-bound claims rather than unsupported generation.

## Use Cases

- Literature-to-property extraction research prototypes.
- Patent and technical document monitoring prototypes.
- Evidence-linked RAG demos for AI-for-science workflows.
- Reproducible benchmarks for extraction quality and citation-grounded answers.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -e .
python -m materials_evidence_stack.demo
pytest
```

Expected demo output:

```text
Question: What tensile strength was reported for the demo alloy?
Answer: The demo Ti alloy reports ultimate tensile strength of 980 MPa after laser-directed energy deposition and heat treatment under room temperature.
Evidence: demo_source_001#span_001
```

## Evidence Model

Each extracted fact keeps:

- `source_id`
- `source_title`
- `source_url`
- `source_type`
- `evidence_id`
- `evidence_text`
- `material_system`
- `process`
- `property_name`
- `property_value`
- `property_unit`
- `condition`
- `confidence`

See `docs/evidence_model.md`.

## OpenAI Evidence Packet

Before applying for OpenAI Codex for Open Source or the open-source fund, publish this repository and collect:

- Public repository URL.
- `v0.1.0` release URL.
- Green CI run URL.
- Demo terminal output.
- Roadmap issue links.
- Maintainer role statement.

See `docs/openai_application_note.md` and `docs/openai_evidence_packet_template.md`.

Additional publication materials:

- `docs/maintainer_statement.md`
- `docs/release_notes_v0.1.0.md`
- `docs/public_roadmap_issues.md`
- `docs/ci_evidence.md`

## Evaluation Policy

Every answer should be evaluated on four checks:

1. Evidence coverage: is an evidence link present?
2. Citation fidelity: does the answer follow the cited evidence text?
3. Numeric accuracy: do values and units match the evidence?
4. Field completeness: are material, process, property, condition, and source fields populated?

This repository deliberately starts with a synthetic fixture so that the demo is reproducible without private PDFs, paid datasets, scraping credentials, or API keys.

## What This Repository Does Not Include

- No private PDFs.
- No paid or closed datasets.
- No unauthorized scraping.
- No API keys or account credentials.
- No claim that extracted facts are validated beyond the provided source evidence.

## Roadmap

- Add more public fixtures.
- Add extraction benchmarks.
- Add citation-grounded retrieval evaluation.
- Add patent-watch examples.
- Add a lightweight web demo.
- Add CI checks for evidence coverage and numeric accuracy.
- Add example notebooks for Ti/TiBw/LDED papers using only public/open examples.

## License

MIT.
