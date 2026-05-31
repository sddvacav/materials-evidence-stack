# Architecture

The project is intentionally small:

```text
source document
  -> evidence span
  -> materials fact
  -> source-bound answer
  -> evaluation
```

The central design rule is that no generated answer should appear without a source identifier and evidence span.
