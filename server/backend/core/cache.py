import os
import numpy as np
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")
cache = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)


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
    from core.config import current_config
    ttl = current_config["ttl"]
    cache.setex(key, ttl, value)
