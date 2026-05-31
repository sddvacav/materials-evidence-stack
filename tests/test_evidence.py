from materials_evidence_stack.demo import demo_facts
from materials_evidence_stack.retrieval import answer_with_evidence


def test_demo_fact_has_evidence_link() -> None:
    fact = demo_facts()[0]
    assert fact.source.source_id == "demo_source_001"
    assert fact.evidence.evidence_id == "span_001"
    assert fact.property_value == 980


def test_answer_with_evidence_returns_source_bound_answer() -> None:
    result = answer_with_evidence(
        "What is the ultimate tensile strength of the demo Ti alloy?",
        demo_facts(),
    )
    assert "980 MPa" in result["answer"]
    assert result["evidence"] == "demo_source_001#span_001"
    assert result["evidence_text"]
