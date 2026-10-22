"""FastAPI application entrypoint. Run with: uvicorn src.api.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.agents.base import AgentQuotaExceededError, AgentUnavailableError
from src.api.routers import drafting, export, formatting, literature, papers, problem_statement, verification
from src.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ResearchAssist API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AgentUnavailableError)
async def handle_agent_unavailable(_request: Request, exc: AgentUnavailableError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(AgentQuotaExceededError)
async def handle_agent_quota_exceeded(_request: Request, exc: AgentQuotaExceededError):
    return JSONResponse(status_code=429, content={"detail": str(exc)}, headers={"Retry-After": "60"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(papers.router)
app.include_router(problem_statement.router)
app.include_router(literature.router)
app.include_router(drafting.router)
app.include_router(verification.router)
app.include_router(formatting.router)
app.include_router(export.router)


@app.get("/health")
def health():
    return {"status": "ok"}
