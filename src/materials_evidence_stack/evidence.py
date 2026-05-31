from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    title: str
    source_type: str
    url: str


@dataclass(frozen=True)
class EvidenceSpan:
    evidence_id: str
    source_id: str
    text: str
    locator: str


@dataclass(frozen=True)
class MaterialsFact:
    fact_id: str
    source: SourceDocument
    evidence: EvidenceSpan
    material_system: str
    process: str
    property_name: str
    property_value: float
    property_unit: str
    condition: str
    confidence: str

    def answer_sentence(self) -> str:
        value = f"{self.property_value:g} {self.property_unit}"
        return (
            f"The {self.material_system} reports {self.property_name} of {value} "
            f"after {self.process} under {self.condition}."
        )
