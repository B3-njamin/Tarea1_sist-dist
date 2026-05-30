import time
from datetime import datetime
from core.config import current_config, experiment_state
from core.cache import cache, get_evictions, calcular_percentiles
from core.database import SessionLocal, Experiment


def start_experiment(distribution: str, n_queries: int):
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
    experiment_state["distribution"]       = distribution
    experiment_state["n_queries"]          = n_queries
    experiment_state["start_time"]         = time.time()
    experiment_state["evictions_at_start"] = get_evictions()
    return {"ok": True}


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


def get_stats():
    total  = int(cache.get("stats:total_requests") or 0)
    hits   = int(cache.get("stats:hit") or 0)
    misses = int(cache.get("stats:miss") or 0)
    p50, p95 = calcular_percentiles()
    return {
        "total":       total,
        "hits":        hits,
        "misses":      misses,
        "hit_rate":    round((hits / total * 100) if total > 0 else 0.0, 2),
        "latency_p50": round(p50, 2),
        "latency_p95": round(p95, 2),
        "active":      experiment_state["active"],
    }


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


def clear_history():
    db = SessionLocal()
    db.query(Experiment).delete()
    db.commit()
    db.close()
    return {"ok": True}
