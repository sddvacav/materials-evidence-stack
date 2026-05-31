# Research Context

Materials Evidence Stack is motivated by AI-assisted titanium alloy and titanium matrix composite research.

The core workflow is:

```text
public source
  -> provenance record
  -> evidence span
  -> structured materials fact
  -> source-bound retrieval answer
  -> evaluation report
```

The initial research domain is Ti/TiBw/LDED and titanium matrix composite design, where useful answers often depend on exact process conditions, temperature, property units, microstructure descriptions, and table or figure evidence.

## Why Generic RAG Is Not Enough

Generic RAG can retrieve a paragraph, but materials research needs structured traceability:

- What material system?
- What processing route?
- What heat treatment?
- What test temperature?
- What mechanical property?
- What unit?
- What table, figure, page, or evidence span?
- What confidence level?

This repository focuses on preserving those links instead of treating retrieval as text-only summarization.
