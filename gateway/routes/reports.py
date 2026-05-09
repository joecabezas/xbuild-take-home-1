from fastapi import APIRouter, HTTPException
from gateway.schemas import FieldReportRequest, ReportCreatedResponse
from shared.repos.reports_repo import save_report, get_report

router = APIRouter()


@router.post("/reports", response_model=ReportCreatedResponse, status_code=201)
def create_report(body: FieldReportRequest):
    report_id, _ = save_report(body.model_dump())
    return {"reportId": report_id}


@router.get("/reports/{report_id}")
def fetch_report(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
