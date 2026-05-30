from core.config import current_config
from core.cache import cache


def get_config():
    return current_config


def set_config(ttl: int, policy: str, memory_mb: int):
    current_config["ttl"]       = ttl
    current_config["policy"]    = policy
    current_config["memory_mb"] = memory_mb
    try:
        cache.config_set("maxmemory", f"{memory_mb}mb")
        cache.config_set("maxmemory-policy", policy)
    except Exception as e:
        print(f"Advertencia al configurar Redis: {e}")
    return {"ok": True, "config": current_config}
