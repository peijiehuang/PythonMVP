from fastapi import APIRouter
from app.api.endpoints import auth, items, install, tasks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(install.router, prefix="/install", tags=["install"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
