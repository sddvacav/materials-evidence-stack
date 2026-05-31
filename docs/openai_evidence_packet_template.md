# OpenAI Evidence Packet Template

Fill this after publishing the repository.

## Public Links

```text
Repository:
Release v0.1.0:
CI run:
Issues:
Maintainer profile:
```

## Demo Evidence

```bash
python -m materials_evidence_stack.demo
pytest -q
```

Expected output:

```text
Question: What tensile strength was reported for the demo alloy?
Answer: The demo Ti alloy reports ultimate tensile strength of 980 MPa after laser-directed energy deposition and heat treatment under room temperature.
Evidence: demo_source_001#span_001
```

## API Credit Use Plan

Credits would be used for:

- Codex-assisted issue triage and roadmap maintenance.
- Test generation for evidence-linking behavior.
- Documentation improvements for provenance, extraction, and evaluation workflows.
- Benchmark fixture generation and review.
- Release-note drafting and changelog maintenance.
- Refactoring source-bound retrieval and extraction utilities.
- Evaluation report generation for public materials-science examples.

## Success Metrics

- Evidence coverage: every answer has an evidence link.
- Citation fidelity: answers are supported by evidence text.
- Numeric accuracy: values and units match evidence.
- Reproducibility: demos and tests run from a clean checkout.
- Maintenance cadence: public issues and releases reflect active maintainer work.
