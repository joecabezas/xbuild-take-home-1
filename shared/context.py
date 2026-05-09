from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class PipelineContext:
    job_id: str
    report_id: str
    raw_input: dict[str, Any]

    # set by ValidatorWorker
    validated: bool = False

    # set by NormalizerWorker (serialized ReportInput)
    report_input: dict[str, Any] | None = None

    # set by MatcherWorker (list of serialized MatchedItem)
    matches: list[dict[str, Any]] = field(default_factory=list)

    # set by PricerWorker (list of serialized PricedLineItem)
    priced_items: list[dict[str, Any]] = field(default_factory=list)

    # set by AssemblerWorker (serialized ProposalDraft)
    proposal_draft: dict[str, Any] | None = None

    status: str = "pending"   # pending | failed | complete
    error: str | None = None

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @classmethod
    def from_json(cls, data: bytes | str) -> PipelineContext:
        return cls(**json.loads(data))
