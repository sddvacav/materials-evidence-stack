from .evidence import EvidenceSpan, MaterialsFact, SourceDocument
from .retrieval import answer_with_evidence


def demo_facts() -> list[MaterialsFact]:
    source = SourceDocument(
        source_id="demo_source_001",
        title="Synthetic public demo record for evidence-linked materials extraction",
        source_type="synthetic_fixture",
        url="https://example.org/materials-evidence-stack/demo",
    )
    evidence = EvidenceSpan(
        evidence_id="span_001",
        source_id=source.source_id,
        text=(
            "The demo Ti alloy sample processed by laser-directed energy deposition "
            "and heat treatment showed an ultimate tensile strength of 980 MPa at room temperature."
        ),
        locator="examples/public_demo/demo_record.md#L7",
    )
    return [
        MaterialsFact(
            fact_id="fact_001",
            source=source,
            evidence=evidence,
            material_system="demo Ti alloy",
            process="laser-directed energy deposition and heat treatment",
            property_name="ultimate tensile strength",
            property_value=980,
            property_unit="MPa",
            condition="room temperature",
            confidence="high",
        )
    ]


def main() -> None:
    question = "What tensile strength was reported for the demo alloy?"
    result = answer_with_evidence(question, demo_facts())
    print(f"Question: {result['question']}")
    print(f"Answer: {result['answer']}")
    print(f"Evidence: {result['evidence']}")


if __name__ == "__main__":
    main()
