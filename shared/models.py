from dataclasses import dataclass, field


@dataclass
class FindingInput:
    id: str
    title: str
    severity: str
    notes: str
    photos: list[str]
    seq: int


@dataclass
class CustomerInput:
    name: str
    email: str


@dataclass
class PropertyInput:
    address: str
    type: str


@dataclass
class ReportInput:
    customer: CustomerInput
    property: PropertyInput
    findings: list[FindingInput]


@dataclass
class MatchedItem:
    finding_id: str
    source_finding: str
    code: str
    category: str
    description: str
    base_price: int
    match_reason: str


@dataclass
class PricedLineItem:
    finding_id: str
    source_finding: str
    code: str
    category: str
    description: str
    estimated_cost: int
    match_reason: str


@dataclass
class ProposalDraft:
    report_id: str
    summary: str
    line_items: list[PricedLineItem]
    total: int
