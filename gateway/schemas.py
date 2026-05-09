from pydantic import BaseModel, field_validator


class Customer(BaseModel):
    name: str
    email: str


class Property(BaseModel):
    address: str
    type: str


class Finding(BaseModel):
    title: str
    severity: str
    notes: str = ""
    photos: list[str] = []


class FieldReportRequest(BaseModel):
    customer: Customer
    property: Property
    findings: list[Finding]


class ReportCreatedResponse(BaseModel):
    reportId: str


class ProposalCreatedResponse(BaseModel):
    proposalId: str
