# Evidence Model

## SourceDocument

Represents an original source:

- `source_id`
- `title`
- `source_type`
- `url`

## EvidenceSpan

Represents the exact text or locator supporting a fact:

- `evidence_id`
- `source_id`
- `text`
- `locator`

## MaterialsFact

Represents a structured materials claim:

- `material_system`
- `process`
- `property_name`
- `property_value`
- `property_unit`
- `condition`
- `confidence`

The fact keeps both the source document and the evidence span.
