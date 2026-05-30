import asyncio
import httpx
from fastapi import APIRouter
from core.config import SERVER_URL, progress
from routers.experiment.models import RunRequest
from routers.experiment.service import send_queries

router = APIRouter()


@router.post("/api/run")
async def run_experiment(req: RunRequest):
    if progress["running"]:
        return {"ok": False, "detail": "Ya hay un experimento en curso"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{SERVER_URL}/api/experiment/start", json={
                "distribution": req.distribution,
                "n_queries":    req.n_queries,
            })
    except Exception as e:
        return {"ok": False, "detail": f"No se pudo conectar al servidor: {e}"}

    progress["running"]      = True
    progress["total"]        = req.n_queries
    progress["completed"]    = 0
    progress["successful"]   = 0
    progress["errors"]       = 0
    progress["distribution"] = req.distribution

    asyncio.create_task(send_queries(req.distribution, req.n_queries))
    return {"ok": True}


@router.get("/api/status")
def get_status():
    return progress
