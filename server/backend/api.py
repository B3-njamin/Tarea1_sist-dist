from fastapi import APIRouter
from routers.queries.router import router as queries_router
from routers.config.router import router as config_router
from routers.experiment.router import router as experiment_router

api_router = APIRouter()
api_router.include_router(queries_router)
api_router.include_router(config_router)
api_router.include_router(experiment_router)
