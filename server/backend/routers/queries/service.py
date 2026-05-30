import json
import time
import numpy as np
from core.config import datos_memoria, AREAS_KM2, current_config, PAD
from core.cache import cache, registrar_latencia, registrar_metrica, set_cache


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
    return [
        {"bucket": i, "min": float(edges[i]), "max": float(edges[i + 1]), "count": int(counts[i])}
        for i in range(bins)
    ]


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
