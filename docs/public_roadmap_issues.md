# Public Roadmap Issues

Create these as GitHub issues after publishing the repository. They are written as copy-paste-ready issue bodies.

## 1. Add public Ti/TiBw/LDED fixture examples

Title:

```text
Add public Ti/TiBw/LDED fixture examples
```

Body:

```text
Goal: add one or more public, redistribution-safe example records for Ti/TiBw/LDED process-structure-property evidence chains.

Acceptance criteria:
- Fixture uses only public/open information.
- Every structured fact includes source_id, evidence_id, evidence_text, material_system, process, property, unit, and condition.
- Demo or test covers at least one fixture record.
- Documentation states source boundary and claim level.
```

## 2. Add extraction benchmark for materials property values

Title:

```text
Add extraction benchmark for materials property values
```

Body:

```text
Goal: create a small benchmark scaffold for evaluating material property extraction.

Acceptance criteria:
- Benchmark fixture is public and reproducible.
- Metrics include evidence coverage, numeric/unit accuracy, and field completeness.
- Test command can run without external APIs or private data.
- Results format is documented.
```

## 3. Add citation-grounded retrieval evaluation

Title:

```text
Add citation-grounded retrieval evaluation
```

Body:

```text
Goal: evaluate whether answers are supported by the cited evidence spans.

Acceptance criteria:
- Evaluation checks that every answer has at least one evidence link.
- Evaluation checks that answer text does not introduce unsupported numeric/property claims.
- Add a passing and failing fixture.
- Document how to interpret the score.
```

## 4. Add patent-watch public example

Title:

```text
Add patent-watch public example
```

Body:

```text
Goal: show how the evidence model can represent technical claims from a public patent-style source.

Acceptance criteria:
- Example uses public data only.
- Claims are labeled as patent/technical claims, not peer-reviewed validation.
- Evidence spans are preserved.
- Demo explains source type and claim boundary.
```

## 5. Add lightweight evidence viewer demo

Title:

```text
Add lightweight evidence viewer demo
```

Body:

```text
Goal: create a small local viewer that displays answers next to source/evidence fields.

Acceptance criteria:
- Runs locally without hosted services.
- Shows answer, evidence_id, evidence_text, source_title, property, value, unit, and condition.
- Includes at least one screenshot or terminal demo in docs.
```

## 6. Add numeric-unit normalization tests

Title:

```text
Add numeric-unit normalization tests
```

Body:

```text
Goal: add tests for preserving numeric values and units in extracted facts.

Acceptance criteria:
- Tests cover MPa, percent, Celsius, and dimensionless examples where applicable.
- Tests fail if value or unit is dropped.
- Documentation explains that normalization does not imply scientific validation.
```

## 7. Add provenance schema documentation

Title:

```text
Add provenance schema documentation
```

Body:

```text
Goal: document the expected provenance fields and how maintainers should populate them.

Acceptance criteria:
- Explain source_id, source_url, source_type, evidence_id, and evidence_text.
- Include examples for paper, patent, technical report, and synthetic fixture source types.
- Clarify that evidence links are required for source-bound answers.
```

## 8. Add reproducibility check command

Title:

```text
Add reproducibility check command
```

Body:

```text
Goal: provide a single local command for contributors to verify the repository before opening a PR.

Acceptance criteria:
- Command runs demo and tests.
- Command reports evidence-link coverage for included fixtures.
- Documentation includes Windows and Unix examples.
```
