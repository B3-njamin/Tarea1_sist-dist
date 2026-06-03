import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import os
import numpy as np

app = FastAPI(title="Backend del Servidor - Tarea 2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")
cache = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

# Estado global del experimento en el servidor
experiment_state = {
    "running": False,
    "start_time": None,
    "end_time": None,
    "distribution": None,
    "total_target_queries": 0,
    "first_recovery_time": None,
    "recovery_completed_time": None
}

class ExperimentStart(BaseModel):
    distribution: str
    n_queries: int

@app.post("/api/experiment/start")
def start_experiment(data: ExperimentStart):
    cache.flushdb()  # Resetear métricas previas en Redis
    
    experiment_state["running"] = True
    experiment_state["start_time"] = time.time()
    experiment_state["end_time"] = None
    experiment_state["distribution"] = data.distribution
    experiment_state["total_target_queries"] = data.n_queries
    experiment_state["first_recovery_time"] = None
    experiment_state["recovery_completed_time"] = None
    return {"status": "started"}

@app.post("/api/experiment/end")
def end_experiment():
    experiment_state["running"] = False
    return {"status": "ended"}

@app.get("/api/metrics")
def get_metrics():
    # Contadores de Caché 
    try:
        hits = int(cache.get("stats:cache_hits") or 0)
        misses = int(cache.get("stats:cache_misses") or 0)
        info = cache.info("stats")
        evictions = int(info.get("evicted_keys", 0))
    except Exception:
        hits, misses, evictions = 0, 0, 0

    # Contadores de Resiliencia
    try:
        retries = int(cache.get("stats:retry_rate") or 0)
        recoveries = int(cache.get("stats:recovery_rate") or 0)
        dlq = int(cache.get("stats:dlq_rate") or 0)
    except Exception:
        retries, recoveries, dlq = 0, 0, 0

    processed_success = hits + misses

    # Cálculo del Backlog size 
    target = experiment_state["total_target_queries"]
    if experiment_state["running"] or target > 0:
        backlog_size = max(0, target - (processed_success + dlq))
    else:
        backlog_size = 0

    # Lógica de desacoplamiento asíncrono
    if experiment_state["start_time"]:
        if experiment_state["running"] or backlog_size > 0:
            elapsed = round(time.time() - experiment_state["start_time"], 1)
            experiment_state["end_time"] = time.time()
        else:
            elapsed = round(experiment_state["end_time"] - experiment_state["start_time"], 1)
    else:
        elapsed = 0.0

    # Cálculo Dinámico del Recovery Time
    # Inicia el cronómetro apenas se detecte CUALQUIER falla en el sistema y termina cuando la cola vuelve a estar en 0.
    if (retries > 0 or dlq > 0) and experiment_state["first_recovery_time"] is None:
        experiment_state["first_recovery_time"] = time.time()

    # La recuperación se considera completa cuando la cola vuelve a estar en 0
    if experiment_state["first_recovery_time"] is not None and backlog_size == 0:
        if experiment_state["recovery_completed_time"] is None:
            experiment_state["recovery_completed_time"] = time.time()
    
    # Calcular delta de tiempo de recuperación
    if experiment_state["recovery_completed_time"] and experiment_state["first_recovery_time"]:
        recovery_time_sec = round(experiment_state["recovery_completed_time"] - experiment_state["first_recovery_time"], 2)
    elif experiment_state["first_recovery_time"] and (experiment_state["running"] or backlog_size > 0):
        recovery_time_sec = round(time.time() - experiment_state["first_recovery_time"], 2)
    else:
        recovery_time_sec = 0.0

    # Throughput y Latencias
    throughput = round(processed_success / elapsed, 2) if elapsed > 0 else 0.0

    try:
        latencias = cache.lrange("stats:latencies", 0, -1)
        if latencias:
            vals = sorted([float(x) for x in latencias])
            p50 = round(float(np.percentile(vals, 50)), 2)
            p95 = round(float(np.percentile(vals, 95)), 2)
        else:
            p50, p95 = 0.0, 0.0
    except Exception:
        p50, p95 = 0.0, 0.0

    is_truly_active = experiment_state["running"] or backlog_size > 0

    return {
        "experiment": {
            "running": is_truly_active,
            "elapsed_time_seconds": elapsed,
            "distribution": experiment_state["distribution"],
            "total_target_queries": target
        },
        "performance": {
            "throughput_ops_sec": throughput,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95
        },
        "kafka_resilience": {
            "retry_count": retries,
            "recovery_count": recoveries,
            "dlq_count": dlq,
            "backlog_size": backlog_size,
            "recovery_time_seconds": recovery_time_sec
        },
        "cache": {
            "hits": hits,
            "misses": misses,
            "evictions": evictions
        }
    }