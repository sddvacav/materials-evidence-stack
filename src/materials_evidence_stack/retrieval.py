from .evidence import MaterialsFact


def answer_with_evidence(question: str, facts: list[MaterialsFact]) -> dict[str, str]:
    """Return a simple source-bound answer for the best matching fact."""
    if not facts:
        return {
            "question": question,
            "answer": "No evidence-linked fact is available.",
            "evidence": "",
        }

    question_lower = question.lower()
    scored = sorted(
        facts,
        key=lambda fact: _score_fact(question_lower, fact),
        reverse=True,
    )
    best = scored[0]
    return {
        "question": question,
        "answer": best.answer_sentence(),
        "evidence": f"{best.source.source_id}#{best.evidence.evidence_id}",
        "evidence_text": best.evidence.text,
        "source_title": best.source.title,
        "source_url": best.source.url,
    }


def _score_fact(question_lower: str, fact: MaterialsFact) -> int:
    fields = [
        fact.material_system,
        fact.process,
        fact.property_name,
        fact.property_unit,
        fact.condition,
    ]
    return sum(1 for field in fields if field.lower() in question_lower)
