from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
import numpy as np
import random
import os

# ============================================================
# INICIALIZACIÓN
# ============================================================
app = FastAPI(title="Cliente Generador de Tráfico - Tarea 1 SD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVER_URL = os.getenv("SERVER_URL", "http://server-backend:8000")

ZONAS   = ["Z1", "Z2", "Z3", "Z4", "Z5"]
QUERIES = ["q1", "q2", "q3", "q4", "q5"]

# Estado del experimento en curso
progress = {
    "running":    False,
    "total":      0,
    "completed":  0,
    "successful": 0,
    "errors":     0,
    "distribution": None,
}

# ============================================================
# GENERADORES DE ZONA (de Benja)
# ============================================================
def generar_zona_uniforme():
    return random.choice(ZONAS)

def generar_zona_zipf(s=1.5):
    r = np.random.zipf(s)
    while r > len(ZONAS):
        r = np.random.zipf(s)
    return ZONAS[r - 1]

def construir_url(query: str, zona: str, distribucion: str) -> str:
    if query in ["q1", "q2", "q3"]:
        confianza = round(random.uniform(0, 1), 2)
        return f"{SERVER_URL}/api/{query}/{zona}?confidence_min={confianza}"
    elif query == "q4":
        zona_b = generar_zona_uniforme() if distribucion == "uniforme" else generar_zona_zipf()
        confianza = round(random.uniform(0, 1), 2)
        return f"{SERVER_URL}/api/q4/{zona}/{zona_b}?confidence_min={confianza}"
    elif query == "q5":
        bins = random.choice([5, 10, 20])
        return f"{SERVER_URL}/api/q5/{zona}?bins={bins}"

# ============================================================
# LÓGICA DE ENVÍO DE CONSULTAS
# ============================================================
async def send_queries(distribucion: str, total: int):
    async with httpx.AsyncClient(timeout=10.0) as client:
        for _ in range(total):
            try:
                zona  = generar_zona_uniforme() if distribucion == "uniforme" else generar_zona_zipf()
                query = random.choice(QUERIES)
                url   = construir_url(query, zona, distribucion)
                resp  = await client.get(url)
                if resp.status_code == 200:
                    progress["successful"] += 1
            except Exception:
                progress["errors"] += 1
            finally:
                progress["completed"] += 1

            await asyncio.sleep(0.01)

    # Avisar al servidor que terminó el experimento
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{SERVER_URL}/api/experiment/end")
    except Exception as e:
        print(f"Error al cerrar experimento: {e}")

    progress["running"] = False

# ============================================================
# ENDPOINTS
# ============================================================
class RunRequest(BaseModel):
    distribution: str
    n_queries: int

@app.post("/api/run")
async def run_experiment(req: RunRequest):
    if progress["running"]:
        return {"ok": False, "detail": "Ya hay un experimento en curso"}

    # Avisar al servidor que empieza un experimento
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

@app.get("/api/status")
def get_status():
    return progress

@app.get("/")
def health():
    return {"status": "ok", "message": "Cliente Generador de Tráfico activo"}
