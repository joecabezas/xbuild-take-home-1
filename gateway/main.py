from fastapi import FastAPI
from shared.db import init_schema
from gateway.routes.reports import router as reports_router
from gateway.routes.proposals import router as proposals_router

app = FastAPI(title="Proposal Engine")


@app.on_event("startup")
def startup():
    init_schema()


app.include_router(reports_router)
app.include_router(proposals_router)
