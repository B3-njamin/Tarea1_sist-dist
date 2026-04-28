from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
import numpy as np 
import redis
import json

# ==========================================
# 1. INICIALIZACIÓN API Y CACHÉ
# ==========================================
app = FastAPI(title="Generador de Respuestas - Tarea 1 Sistemas Distribuidos")
cache = redis.Redis(host='redis-cache', port=6379, db=0, decode_responses=True) 

# ==========================================
# 2. CONSTANTES
# ==========================================
ZONAS = {
    "Z1": {"nombre": "Providencia", "lat_min": -33.445, "lat_max": -33.420, "lon_min": -70.640, "lon_max": -70.600},
    "Z2": {"nombre": "Las Condes", "lat_min": -33.420, "lat_max": -33.390, "lon_min": -70.600, "lon_max": -70.550},
    "Z3": {"nombre": "Maipú", "lat_min": -33.530, "lat_max": -33.490, "lon_min": -70.790, "lon_max": -70.740},
    "Z4": {"nombre": "Santiago Centro", "lat_min": -33.470, "lat_max": -33.430, "lon_min": -70.670, "lon_max": -70.630},
    "Z5": {"nombre": "Pudahuel", "lat_min": -33.470, "lat_max": -33.430, "lon_min": -70.810, "lon_max": -70.760}
}
AREAS_KM2 = {"Z1": 14.4, "Z2": 99.4, "Z3": 133.0, "Z4": 22.4, "Z5": 197.0}

# ==========================================
# 3. LÓGICA DE PROCESAMIENTO
# ==========================================
def cargar_datos_en_memoria(ruta_dataset):
    print("Cargando dataset en memoria...")
    df_completo = pd.read_csv(ruta_dataset)
    datos_por_zona = {}
    
    for zona_id, limites in ZONAS.items():
        filtro = (
            (df_completo['latitude'] >= limites['lat_min']) & 
            (df_completo['latitude'] <= limites['lat_max']) &
            (df_completo['longitude'] >= limites['lon_min']) & 
            (df_completo['longitude'] <= limites['lon_max'])
        )
        datos_por_zona[zona_id] = df_completo[filtro]
        print(f"[{zona_id}] {limites['nombre']}: {len(datos_por_zona[zona_id])} edificios cargados.")
        
    return datos_por_zona

def q1_count(datos_por_zona, zona_id, confidence_min=0.0):
    df_zona = datos_por_zona[zona_id]
    return len(df_zona[df_zona['confidence'] >= confidence_min])

def q2_area(datos_por_zona, zona_id, confidence_min=0.0):
    df_zona = datos_por_zona[zona_id]
    df_filtrado = df_zona[df_zona['confidence'] >= confidence_min]
    if df_filtrado.empty: return {"avg_area": 0, "total_area": 0, "n": 0}
    return {
        "avg_area": float(df_filtrado['area_in_meters'].mean()),
        "total_area": float(df_filtrado['area_in_meters'].sum()),
        "n": len(df_filtrado)
    }

def q3_density(datos_por_zona, zona_id, confidence_min=0.0):
    cantidad_edificios = q1_count(datos_por_zona, zona_id, confidence_min)
    return float(cantidad_edificios / AREAS_KM2[zona_id])

def q4_compare(datos_por_zona, zona_a, zona_b, confidence_min=0.0):
    da = q3_density(datos_por_zona, zona_a, confidence_min)
    db = q3_density(datos_por_zona, zona_b, confidence_min)
    return {"zone_a": da, "zone_b": db, "winner": zona_a if da > db else zona_b}

def q5_confidence_dist(datos_por_zona, zona_id, bins=5):
    df_zona = datos_por_zona[zona_id]
    if df_zona.empty: return []
    scores = df_zona['confidence'].values
    counts, edges = np.histogram(scores, bins=bins, range=(0, 1))
    
    resultado = []
    for i in range(bins):
        resultado.append({
            "bucket": i, 
            "min": float(edges[i]), 
            "max": float(edges[i+1]), 
            "count": int(counts[i])
        })
    return resultado

# ==========================================
# 4. CARGA DE DATOS Y AYUDANTES
# ==========================================
datos_memoria = cargar_datos_en_memoria("Dataset-Prueba.csv")

def registrar_metrica(tipo):
    """Incrementa contadores en Redis para el dashboard."""
    cache.incr("stats:total_requests")
    cache.incr(f"stats:{tipo}") 

# ==========================================
# 5. ENDPOINTS DE LA API (CON CACHÉ Y MÉTRICAS)
# ==========================================
@app.get("/")
def health_check():
    return {"status": "ok", "mensaje": "API lista para recibir tráfico"}

@app.get("/api/q1/{zona_id}")
def api_q1(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS: return {"error": "Zona no válida"}
    cache_key = f"q1:{zona_id}:{confidence_min}"
    
    cached_res = cache.get(cache_key)
    if cached_res:
        registrar_metrica("hit")
        return json.loads(cached_res)

    registrar_metrica("miss")
    resultado = {"zona": zona_id, "q1_count": q1_count(datos_memoria, zona_id, confidence_min)}
    cache.setex(cache_key, 60, json.dumps(resultado)) 
    return resultado

@app.get("/api/q2/{zona_id}")
def api_q2(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS: return {"error": "Zona no válida"}
    cache_key = f"q2:{zona_id}:{confidence_min}"
    
    cached_res = cache.get(cache_key)
    if cached_res: 
        registrar_metrica("hit")
        return json.loads(cached_res)

    registrar_metrica("miss")
    resultado = q2_area(datos_memoria, zona_id, confidence_min)
    cache.setex(cache_key, 60, json.dumps(resultado))
    return resultado

@app.get("/api/q3/{zona_id}")
def api_q3(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS: return {"error": "Zona no válida"}
    cache_key = f"q3:{zona_id}:{confidence_min}"
    
    cached_res = cache.get(cache_key)
    if cached_res: 
        registrar_metrica("hit")
        return json.loads(cached_res)

    registrar_metrica("miss")
    resultado = {"zona": zona_id, "density": q3_density(datos_memoria, zona_id, confidence_min)}
    cache.setex(cache_key, 60, json.dumps(resultado))
    return resultado

@app.get("/api/q4/{zona_a}/{zona_b}")
def api_q4(zona_a: str, zona_b: str, confidence_min: float = 0.0):
    if zona_a not in ZONAS or zona_b not in ZONAS: return {"error": "Zonas no válidas"}
    cache_key = f"q4:{zona_a}:{zona_b}:{confidence_min}"
    
    cached_res = cache.get(cache_key)
    if cached_res: 
        registrar_metrica("hit")
        return json.loads(cached_res)

    registrar_metrica("miss")
    resultado = q4_compare(datos_memoria, zona_a, zona_b, confidence_min)
    cache.setex(cache_key, 60, json.dumps(resultado))
    return resultado

@app.get("/api/q5/{zona_id}")
def api_q5(zona_id: str, bins: int = 5):
    if zona_id not in ZONAS: return {"error": "Zona no válida"}
    cache_key = f"q5:{zona_id}:bins{bins}"
    
    cached_res = cache.get(cache_key)
    if cached_res: 
        registrar_metrica("hit")
        return json.loads(cached_res)

    registrar_metrica("miss")
    resultado = {"zona": zona_id, "distribution": q5_confidence_dist(datos_memoria, zona_id, bins)}
    cache.setex(cache_key, 60, json.dumps(resultado))
    return resultado

# ==========================================
# 6. DASHBOARD
# ==========================================
@app.get("/api/stats")
def obtener_estadisticas():
    total = int(cache.get("stats:total_requests") or 0)
    hits = int(cache.get("stats:hit") or 0)
    misses = int(cache.get("stats:miss") or 0)
    hit_rate = (hits / total * 100) if total > 0 else 0.0
    return {"total": total, "hits": hits, "misses": misses, "hit_rate": round(hit_rate, 2)}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_html():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard Tarea 1</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; text-align: center; padding: 50px; }
            h1 { color: #2c3e50; }
            .metric-container { display: flex; justify-content: center; gap: 20px; margin-top: 30px; flex-wrap: wrap; }
            .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); min-width: 200px; }
            .card h2 { margin: 0 0 10px 0; font-size: 1.2em; color: #7f8c8d; }
            .card p { margin: 0; font-size: 2.5em; font-weight: bold; color: #2980b9; }
            .hit { color: #27ae60 !important; }
            .miss { color: #e74c3c !important; }
        </style>
        <script>
            async function actualizarMetricas() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    document.getElementById('total').innerText = data.total;
                    document.getElementById('hits').innerText = data.hits;
                    document.getElementById('misses').innerText = data.misses;
                    document.getElementById('hit-rate').innerText = data.hit_rate + "%";
                } catch (error) { console.error(error); }
            }
            setInterval(actualizarMetricas, 1000);
            window.onload = actualizarMetricas;
        </script>
    </head>
    <body>
        <h1>📊 Dashboard de Rendimiento</h1>
        <div class="metric-container">
            <div class="card"><h2>Total Peticiones</h2><p id="total">0</p></div>
            <div class="card"><h2>Cache HITS ⚡</h2><p id="hits" class="hit">0</p></div>
            <div class="card"><h2>Cache MISSES 🐌</h2><p id="misses" class="miss">0</p></div>
            <div class="card"><h2>Hit Rate</h2><p id="hit-rate">0%</p></div>
        </div>
    </body>
    </html>
    """
    return html_content