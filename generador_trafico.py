import requests
import random
import time
import numpy as np
import argparse

ZONAS = ["Z1", "Z2", "Z3", "Z4", "Z5"]
QUERIES = ["q1", "q2", "q3", "q4", "q5"] # MODIFICADO: Agregamos q4 y q5
URL_BASE = "http://generador-respuestas:8000/api"
URL_ROOT = "http://generador-respuestas:8000/" 

def generar_zona_uniforme():
    return random.choice(ZONAS)

def generar_zona_zipf(s=1.5):
    r = np.random.zipf(s)
    while r > len(ZONAS):
        r = np.random.zipf(s)
    return ZONAS[r - 1]

def esperar_api():
    print("⏳ Esperando a que el Generador de Respuestas cargue los datos en memoria...")
    while True:
        try:
            respuesta = requests.get(URL_ROOT, timeout=2)
            if respuesta.status_code == 200:
                print("✅ ¡La API está lista! Comenzando la simulación de tráfico...\n")
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)

def enviar_trafico(distribucion, total_peticiones):
    esperar_api()
    
    print(f"--- Iniciando simulación: {total_peticiones} peticiones | Distribución: {distribucion} ---")
    tiempo_inicio = time.time()
    exitos = 0

    for i in range(total_peticiones):
        # 1. Generamos la zona base (MANTENIDO)
        if distribucion == "uniforme":
            zona = generar_zona_uniforme()
        else:
            zona = generar_zona_zipf()
            
        # Elegimos una consulta al azar, ahora incluye q4 y q5
        query = random.choice(QUERIES) 
        
        # 2. Lógica para construir la URL correcta (MODIFICADO)
        if query in ["q1", "q2", "q3"]:
            confianza = random.choice([0.0, 0.5, 0.8])
            url = f"{URL_BASE}/{query}/{zona}?confidence_min={confianza}"
            
        elif query == "q4":
            # Para comparar, necesitamos una segunda zona con la misma distribución
            if distribucion == "uniforme":
                zona_b = generar_zona_uniforme()
            else:
                zona_b = generar_zona_zipf()
            confianza = random.choice([0.0, 0.5, 0.8])
            url = f"{URL_BASE}/q4/{zona}/{zona_b}?confidence_min={confianza}"
            
        elif query == "q5":
            # q5 usa 'bins' en lugar de 'confidence_min'
            bins = random.choice([5, 10, 20])
            url = f"{URL_BASE}/q5/{zona}?bins={bins}"
        
        # 3. Petición HTTP y Métricas (MANTENIDO)
        try:
            respuesta = requests.get(url)
            if respuesta.status_code == 200:
                exitos += 1
                if i % 50 == 0:  
                    print(f"[{i}/{total_peticiones}] OK: {url}")
        except Exception as e:
            print(f"Error conectando a la API: {e}")
            
        time.sleep(0.01)
        
    tiempo_total = time.time() - tiempo_inicio
    print(f"\n--- Simulación Terminada ---")
    print(f"Peticiones Exitosas: {exitos}/{total_peticiones}")
    print(f"Tiempo Total: {tiempo_total:.2f} segundos")
    print(f"Throughput (Peticiones/seg): {exitos / tiempo_total:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generador de Tráfico')
    parser.add_argument('--dist', type=str, choices=['uniforme', 'zipf'], default='uniforme', help='Distribución de las consultas')
    parser.add_argument('--n', type=int, default=1000, help='Número total de peticiones a enviar')
    
    args = parser.parse_args()
    enviar_trafico(args.dist, args.n)