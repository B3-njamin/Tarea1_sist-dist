from fastapi import APIRouter
from routers.config.models import ConfigRequest
from routers.config.service import get_config, set_config

router = APIRouter()


@router.get("/api/config")
def api_get_config():
    return get_config()


@router.post("/api/config")
def api_set_config(req: ConfigRequest):
    return set_config(req.ttl, req.policy, req.memory_mb)
