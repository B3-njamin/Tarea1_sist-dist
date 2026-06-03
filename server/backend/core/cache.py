import os
import redis
import numpy as np
from typing import Tuple, Dict


# CONFIGURACIÓN DE CONEXIÓN
REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")
# decode_responses=True para garantizar que los strings de Redis se devuelvan 
cache = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

#CONTROL DE ESTADO
def reset_metrics() -> None:
     #Limpia completamente la base de datos actual.
    cache.flushdb()



#EXTRACCIÓN DE MÉTRICAS 
def calcular_percentiles() -> Tuple[float, float]:
    try:
        latencias = cache.lrange("stats:latencies", 0, -1)
        if not latencias:
            return 0.0, 0.0
            
        vals = sorted([float(x) for x in latencias])
        p50 = round(float(np.percentile(vals, 50)), 2)
        p95 = round(float(np.percentile(vals, 95)), 2)
        return p50, p95
    except Exception as e:
        print(f"Error calculando percentiles: {e}")
        return 0.0, 0.0


def get_evictions() -> int:
    try:
        info = cache.info("stats")
        return int(info.get("evicted_keys", 0))
    except Exception as e:
        print(f"Error extrayendo evictions: {e}")
        return 0


def get_kafka_metrics() -> Dict[str, int]:
    try:
        hits       = int(cache.get("stats:cache_hits") or 0)
        misses     = int(cache.get("stats:cache_misses") or 0)
        retries    = int(cache.get("stats:retry_rate") or 0)
        recoveries = int(cache.get("stats:recovery_rate") or 0)
        dlq        = int(cache.get("stats:dlq_rate") or 0)
        
        #total de elementos procesados
        processed_success = hits + misses

        return {
            "cache_hits": hits,
            "cache_misses": misses,
            "retry_rate": retries,
            "recovery_rate": recoveries,
            "dlq_rate": dlq,
            "processed_success": processed_success
        }
    except Exception as e:
        print(f"Error extrayendo métricas globales de Kafka/Redis: {e}")
        return {
            "cache_hits": 0,
            "cache_misses": 0,
            "retry_rate": 0,
            "recovery_rate": 0,
            "dlq_rate": 0,
            "processed_success": 0
        }