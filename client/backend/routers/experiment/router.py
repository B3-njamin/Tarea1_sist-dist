import httpx
from fastapi import APIRouter, BackgroundTasks
from typing import Dict, Any

from core.config import SERVER_URL, progress
from routers.experiment.models import RunRequest
from routers.experiment.service import send_queries

router = APIRouter()

@router.post("/api/run")
async def run_experiment(req: RunRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    
    # Evitar concurrencia
    if progress["running"]:
        return {"ok": False, "detail": "Ya hay un experimento en curso."}

    if req.distribution == "poison_pill":
        print("⚠️ [STRESS TEST] Iniciando inyección de fallos controlados (Poison Pills) hacia Kafka...")
    else:
        print(f"▶️ Iniciando inyección normal de tráfico. Distribución: {req.distribution}")

    # Notificar para preparar los contadores Redis y la máquina de estados
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{SERVER_URL}/api/experiment/start", json={
                "distribution": req.distribution,
                "n_queries":    req.n_queries,
            })
    except Exception as e:
        return {"ok": False, "detail": f"Fallo al contactar al servidor: {e}"}

    # Resetear el estado local del progreso de inyección a Kafka
    progress["running"]      = True
    progress["total"]        = req.n_queries
    progress["completed"]    = 0
    progress["successful"]   = 0
    progress["errors"]       = 0
    progress["distribution"] = req.distribution

    # Delegar la inyección masiva de mensajes a Kafka, desacoplando el flujo 
    background_tasks.add_task(send_queries, req.distribution, req.n_queries)
    
    return {"ok": True, "detail": "Inyección de eventos iniciada con éxito."}


@router.get("/api/status")
def get_status() -> Dict[str, Any]:
    #Devuelve el estado actual
    return progress