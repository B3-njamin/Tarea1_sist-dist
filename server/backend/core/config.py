import pandas as pd

# ============================================================
# CONSTANTES DE ZONAS
# ============================================================
ZONAS = {
    "Z1": {"nombre": "Providencia",     "lat_min": -33.445, "lat_max": -33.420, "lon_min": -70.640, "lon_max": -70.600},
    "Z2": {"nombre": "Las Condes",      "lat_min": -33.420, "lat_max": -33.390, "lon_min": -70.600, "lon_max": -70.550},
    "Z3": {"nombre": "Maipu",           "lat_min": -33.530, "lat_max": -33.490, "lon_min": -70.790, "lon_max": -70.740},
    "Z4": {"nombre": "Santiago Centro", "lat_min": -33.460, "lat_max": -33.430, "lon_min": -70.670, "lon_max": -70.630},
    "Z5": {"nombre": "Pudahuel",        "lat_min": -33.470, "lat_max": -33.430, "lon_min": -70.810, "lon_max": -70.760},
}
AREAS_KM2 = {"Z1": 14.4, "Z2": 99.4, "Z3": 133.0, "Z4": 22.4, "Z5": 197.0}

# Padding — infla cada entrada en caché para estresar memoria (~160KB por entrada)
PAD = "x" * 160000

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


# ============================================================
# CARGA DE DATOS EN MEMORIA
# ============================================================
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
