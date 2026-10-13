from fastapi import APIRouter

from app.api.v1.routers import agent, auth, documents, evidence, health, query, reports, tasks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(evidence.tasks_router, prefix="/tasks", tags=["evidence"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(query.router, prefix="/query", tags=["rag"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(reports.dashboard_router, prefix="/dashboard", tags=["reports"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
