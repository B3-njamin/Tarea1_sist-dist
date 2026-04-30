from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import redis
import json
import time
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import declarative_base, sessionmaker
import asyncio

# ============================================================
# INICIALIZACIÓN
# ============================================================
app = FastAPI(title="Servidor de Respuestas - Tarea 1 SD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")
cache = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

# SQLite
os.makedirs("/app/data", exist_ok=True)
DATABASE_URL = "sqlite:////app/data/experiments.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class Experiment(Base):
    __tablename__ = "experiments"
    id              = Column(Integer, primary_key=True, index=True)
    timestamp       = Column(String)
    distribution    = Column(String)
    policy          = Column(String)
    memory_mb       = Column(Integer)
    ttl_seconds     = Column(Integer)
    n_queries       = Column(Integer)
    hits            = Column(Integer)
    misses          = Column(Integer)
    hit_rate        = Column(Float)
    throughput      = Column(Float)
    latency_p50     = Column(Float)
    latency_p95     = Column(Float)
    eviction_rate   = Column(Float)
    cache_efficiency= Column(Float)
    duration_seconds= Column(Float)

Base.metadata.create_all(bind=engine)

# ============================================================
# ESTADO GLOBAL CONFIGURABLE
# ============================================================
current_config = {
    "ttl": 60,
    "policy": "allkeys-lfu",
    "memory_mb": 50,
}

experiment_state = {
    "active": False,
    "distribution": None,
    "n_queries": 0,
    "start_time": None,
    "evictions_at_start": 0,
}


ZONAS = {
    "Z1": {"nombre": "Providencia",     "lat_min": -33.445, "lat_max": -33.420, "lon_min": -70.640, "lon_max": -70.600},
    "Z2": {"nombre": "Las Condes",      "lat_min": -33.420, "lat_max": -33.390, "lon_min": -70.600, "lon_max": -70.550},
    "Z3": {"nombre": "Maipu",           "lat_min": -33.530, "lat_max": -33.490, "lon_min": -70.790, "lon_max": -70.740},
    "Z4": {"nombre": "Santiago Centro", "lat_min": -33.460, "lat_max": -33.430, "lon_min": -70.670, "lon_max": -70.630},
    "Z5": {"nombre": "Pudahuel",        "lat_min": -33.470, "lat_max": -33.430, "lon_min": -70.810, "lon_max": -70.760},
}
AREAS_KM2 = {"Z1": 14.4, "Z2": 99.4, "Z3": 133.0, "Z4": 22.4, "Z5": 197.0}

def cargar_datos_en_memoria(ruta_dataset):
    print("Cargando dataset en memoria...")
    df = pd.read_csv(
        ruta_dataset, skiprows=1, header=None,
        names=["latitude", "longitude", "area_in_meters", "confidence", "geometry", "plus_code"]
    )
    datos_por_zona = {}
    for zona_id, limites in ZONAS.items():
        filtro = (
            (df["latitude"]  >= limites["lat_min"]) & (df["latitude"]  <= limites["lat_max"]) &
            (df["longitude"] >= limites["lon_min"]) & (df["longitude"] <= limites["lon_max"])
        )
        datos_por_zona[zona_id] = df[filtro].reset_index(drop=True)
        print(f"[{zona_id}] {limites['nombre']}: {len(datos_por_zona[zona_id])} edificios cargados.")
    return datos_por_zona

datos_memoria = cargar_datos_en_memoria("/app/967_buildings.csv")

# ============================================================
# FUNCIONES Q1-Q5 (de Benja, lógica intacta)
# ============================================================
def q1_count(zona_id, confidence_min=0.0):
    df = datos_memoria[zona_id]
    return int(len(df[df["confidence"] >= confidence_min]))

def q2_area(zona_id, confidence_min=0.0):
    df = datos_memoria[zona_id]
    df_f = df[df["confidence"] >= confidence_min]
    if df_f.empty:
        return {"avg_area": 0.0, "total_area": 0.0, "n": 0}
    return {
        "avg_area":   float(df_f["area_in_meters"].mean()),
        "total_area": float(df_f["area_in_meters"].sum()),
        "n":          int(len(df_f)),
    }

def q3_density(zona_id, confidence_min=0.0):
    return float(q1_count(zona_id, confidence_min) / AREAS_KM2[zona_id])

def q4_compare(zona_a, zona_b, confidence_min=0.0):
    da = q3_density(zona_a, confidence_min)
    db = q3_density(zona_b, confidence_min)
    return {"zone_a": da, "zone_b": db, "winner": zona_a if da > db else zona_b}

def q5_confidence_dist(zona_id, bins=5):
    df = datos_memoria[zona_id]
    if df.empty:
        return []
    counts, edges = np.histogram(df["confidence"].values, bins=bins, range=(0, 1))
    return [{"bucket": i, "min": float(edges[i]), "max": float(edges[i+1]), "count": int(counts[i])} for i in range(bins)]

# ============================================================
# PADDING — infla cada entrada en caché para estresar memoria
# ============================================================
PAD = "x" * 160000  # ~160KB por entrada → total posible ~633MB con 2 decimales

# ============================================================
# HELPERS DE MÉTRICAS
# ============================================================
def registrar_latencia(latencia_ms: float):
    cache.rpush("stats:latencies", latencia_ms)

def registrar_metrica(tipo: str):
    cache.incr("stats:total_requests")
    cache.incr(f"stats:{tipo}")

def get_evictions():
    try:
        return int(cache.info("stats").get("evicted_keys", 0))
    except:
        return 0

def calcular_percentiles():
    latencias = cache.lrange("stats:latencies", 0, -1)
    if not latencias:
        return 0.0, 0.0
    vals = sorted([float(x) for x in latencias])
    return float(np.percentile(vals, 50)), float(np.percentile(vals, 95))

def set_cache(key: str, value: str):
    ttl = current_config["ttl"]
    cache.setex(key, ttl, value)

# ============================================================
# HANDLER GENÉRICO DE CONSULTAS
# ============================================================
def handle_query(cache_key: str, compute_fn):
    t_start = time.time()

    # TTL=0 → sin caché: todo es miss, nada se guarda en Redis
    if current_config["ttl"] == 0:
        resultado = compute_fn()
        registrar_latencia((time.time() - t_start) * 1000)
        registrar_metrica("miss")
        return resultado

    cached = cache.get(cache_key)
    if cached:
        registrar_latencia((time.time() - t_start) * 1000)
        registrar_metrica("hit")
        data = json.loads(cached)
        data.pop("_pad", None)
        return data
    resultado = compute_fn()
    registrar_latencia((time.time() - t_start) * 1000)
    registrar_metrica("miss")
    to_cache = dict(resultado)
    to_cache["_pad"] = PAD
    set_cache(cache_key, json.dumps(to_cache))
    return resultado

# ============================================================
# ENDPOINTS Q1-Q5
# ============================================================
@app.get("/api/q1/{zona_id}")
def api_q1(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"count:{zona_id}:conf={round(confidence_min, 2)}",
        lambda: {"zona": zona_id, "count": q1_count(zona_id, confidence_min)}
    )

@app.get("/api/q2/{zona_id}")
def api_q2(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"area:{zona_id}:conf={round(confidence_min, 2)}",
        lambda: q2_area(zona_id, confidence_min)
    )

@app.get("/api/q3/{zona_id}")
def api_q3(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"density:{zona_id}:conf={round(confidence_min, 2)}",
        lambda: {"zona": zona_id, "density": q3_density(zona_id, confidence_min)}
    )

@app.get("/api/q4/{zona_a}/{zona_b}")
def api_q4(zona_a: str, zona_b: str, confidence_min: float = 0.0):
    if zona_a not in ZONAS or zona_b not in ZONAS:
        raise HTTPException(status_code=400, detail="Zonas no válidas")
    return handle_query(
        f"compare:density:{zona_a}:{zona_b}:conf={round(confidence_min, 2)}",
        lambda: q4_compare(zona_a, zona_b, confidence_min)
    )

@app.get("/api/q5/{zona_id}")
def api_q5(zona_id: str, bins: int = 5):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"confidence_dist:{zona_id}:bins={bins}",
        lambda: {"zona": zona_id, "distribution": q5_confidence_dist(zona_id, bins)}
    )

# ============================================================
# CONFIGURACIÓN
# ============================================================
class ConfigRequest(BaseModel):
    ttl: int
    policy: str
    memory_mb: int

@app.get("/api/config")
def get_config():
    return current_config

@app.post("/api/config")
def set_config(req: ConfigRequest):
    current_config["ttl"]       = req.ttl
    current_config["policy"]    = req.policy
    current_config["memory_mb"] = req.memory_mb
    try:
        cache.config_set("maxmemory", f"{req.memory_mb}mb")
        cache.config_set("maxmemory-policy", req.policy)
    except Exception as e:
        print(f"Advertencia al configurar Redis: {e}")
    return {"ok": True, "config": current_config}

# ============================================================
# EXPERIMENTO
# ============================================================
class ExperimentStart(BaseModel):
    distribution: str
    n_queries: int

@app.post("/api/experiment/start")
def start_experiment(req: ExperimentStart):
    # Limpiar stats anteriores
    keys_to_del = ["stats:total_requests", "stats:hit", "stats:miss", "stats:latencies"]
    for k in keys_to_del:
        cache.delete(k)
    # Limpiar entradas de caché (no stats)
    prefixes = ["count:", "area:", "density:", "compare:", "confidence_dist:"]
    for prefix in prefixes:
        for key in cache.scan_iter(f"{prefix}*"):
            cache.delete(key)

    experiment_state["active"]             = True
    experiment_state["distribution"]       = req.distribution
    experiment_state["n_queries"]          = req.n_queries
    experiment_state["start_time"]         = time.time()
    experiment_state["evictions_at_start"] = get_evictions()
    return {"ok": True}

@app.post("/api/experiment/end")
def end_experiment():
    if not experiment_state["active"]:
        return {"ok": False, "detail": "No hay experimento activo"}

    duration = time.time() - experiment_state["start_time"]
    total    = int(cache.get("stats:total_requests") or 0)
    hits     = int(cache.get("stats:hit") or 0)
    misses   = int(cache.get("stats:miss") or 0)

    hit_rate   = (hits / total) if total > 0 else 0.0
    throughput = total / duration if duration > 0 else 0.0
    p50, p95   = calcular_percentiles()

    evictions_during = get_evictions() - experiment_state["evictions_at_start"]
    eviction_rate    = evictions_during / (duration / 60) if duration > 0 else 0.0

    t_cache = p50 / 1000
    t_db    = (p95 / 1000) * 2
    cache_efficiency = ((hits * t_cache) - (misses * t_db)) / total if total > 0 else 0.0

    db = SessionLocal()
    exp = Experiment(
        timestamp        = datetime.now().isoformat(),
        distribution     = experiment_state["distribution"],
        policy           = current_config["policy"],
        memory_mb        = current_config["memory_mb"],
        ttl_seconds      = current_config["ttl"],
        n_queries        = total,
        hits             = hits,
        misses           = misses,
        hit_rate         = round(hit_rate, 4),
        throughput       = round(throughput, 2),
        latency_p50      = round(p50, 2),
        latency_p95      = round(p95, 2),
        eviction_rate    = round(eviction_rate, 2),
        cache_efficiency = round(cache_efficiency, 4),
        duration_seconds = round(duration, 2),
    )
    db.add(exp)
    db.commit()
    db.close()

    experiment_state["active"] = False
    return {"ok": True, "metrics": {
        "hit_rate": hit_rate, "throughput": throughput,
        "latency_p50": p50, "latency_p95": p95,
        "eviction_rate": eviction_rate, "cache_efficiency": cache_efficiency,
    }}

@app.get("/api/stats")
def get_stats():
    total  = int(cache.get("stats:total_requests") or 0)
    hits   = int(cache.get("stats:hit") or 0)
    misses = int(cache.get("stats:miss") or 0)
    p50, p95 = calcular_percentiles()
    return {
        "total":        total,
        "hits":         hits,
        "misses":       misses,
        "hit_rate":     round((hits / total * 100) if total > 0 else 0.0, 2),
        "latency_p50":  round(p50, 2),
        "latency_p95":  round(p95, 2),
        "active":       experiment_state["active"],
    }

@app.get("/api/history")
def get_history():
    db = SessionLocal()
    exps = db.query(Experiment).order_by(Experiment.id.desc()).all()
    result = [{
        "id": e.id, "timestamp": e.timestamp, "distribution": e.distribution,
        "policy": e.policy, "memory_mb": e.memory_mb, "ttl_seconds": e.ttl_seconds,
        "n_queries": e.n_queries, "hits": e.hits, "misses": e.misses,
        "hit_rate": e.hit_rate, "throughput": e.throughput,
        "latency_p50": e.latency_p50, "latency_p95": e.latency_p95,
        "eviction_rate": e.eviction_rate, "cache_efficiency": e.cache_efficiency,
        "duration_seconds": e.duration_seconds,
    } for e in exps]
    db.close()
    return result

@app.delete("/api/history")
def clear_history():
    db = SessionLocal()
    db.query(Experiment).delete()
    db.commit()
    db.close()
    return {"ok": True}

@app.get("/")
def health():
    return {"status": "ok", "message": "Servidor de Respuestas activo"}
