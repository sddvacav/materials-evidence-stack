# Release Notes: v0.1.0

Initial public seed release for Materials Evidence Stack.

## What Is Included

- Minimal source document and evidence-span data model.
- Structured materials fact representation.
- Source-bound answer object.
- Deterministic demo question answering flow.
- Tests for evidence link preservation and demo output.
- Documentation for architecture, evidence model, evaluation policy, quickstart, and research context.
- GitHub issue templates, CI workflow, security policy, contribution guide, and code of conduct.

## Verification

```bash
python -m materials_evidence_stack.demo
pytest -q
```

Expected demo evidence link:

```text
demo_source_001#span_001
```

## Scope Boundary

This release uses a synthetic public fixture. It does not include private PDFs, paid datasets, scraping credentials, API keys, or claims that extracted facts are scientifically validated beyond the provided fixture evidence.

## Next Work

- Add public Ti/TiBw/LDED fixture examples.
- Add extraction benchmark scaffolds.
- Add citation-grounded retrieval evaluation.
- Add patent-watch public example.
- Add a lightweight evidence viewer.
