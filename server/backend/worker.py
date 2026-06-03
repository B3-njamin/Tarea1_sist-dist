import os
import json
import time
import random
import redis
from confluent_kafka import Consumer, Producer

# Configuración de Entorno
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")

MAX_RETRIES = 3

# Conexión a Redis
try:
    cache = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
    cache.ping()
except Exception as e:
    print(f"[FATAL] No se pudo conectar a Redis: {e}")

# Configuración del Productor (para reenviar a Retry y DLQ)
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

def procesar_consulta(mensaje):
    #Extracción de datos
    data = mensaje.get("data", {})
    tipo = mensaje.get("tipo", "unknown")
    
    #Chequeo de Caché (Hit/Miss)
    #Serialización de los parámetros
    llave_datos = json.dumps(data, sort_keys=True)
    cache_key = f"query:{tipo}:{llave_datos}"
    
    if cache.exists(cache_key):
        cache.incr("stats:cache_hits")
        return True # Retorna si hay Hit
        
    cache.incr("stats:cache_misses")
    
    #Simulación de Fallo Controlado (Poison Pill)
    if data.get("zona") == "Z5" and data.get("confidence_min", 0) > 0.90:
        raise ValueError("Poison Pill activada: Fallo forzado para demostrar DLQ.")

    # procesamiento y simulación 
    time.sleep(random.uniform(0.2, 0.5)) 
    resultado_simulado = {"status": "success", "processed_type": tipo, "params": data}
    
    # Guardar en caché tras éxito (Usamos 60s para forzar evictions si la RAM es baja)
    cache.setex(cache_key, 60, json.dumps(resultado_simulado))

    # registrar métrica de latencia
    timestamp_origen = float(mensaje.get("timestamp", time.time()))
    latencia_ms = (time.time() - timestamp_origen) * 1000
    cache.rpush("stats:latencies", latencia_ms)
    
    return True

def run_worker():
    # Configuración del Consumidor
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'gis-workers-group', 
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False # tolerancia a fallos 
    })
    
    consumer.subscribe(['queries-main', 'queries-retry'])
    print("Worker iniciado, escuchando tópicos: queries-main, queries-retry...")
    
    try:
        while True:
            # Escuchar mensajes
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            if msg.error():
                print(f"[KAFKA ERROR] {msg.error()}")
                continue
                
            # Extraer metadata
            topic = msg.topic()
            
            try:
                mensaje = json.loads(msg.value().decode('utf-8'))
                
                # Asegurar que hay un campo intentos
                if "intentos" not in mensaje:
                    mensaje["intentos"] = 0
                
                # Intenta procesar
                procesar_consulta(mensaje)
                
                # Si llegó de retry y no falló, es una recuperación exitosa demostrable
                if topic == 'queries-retry':
                    cache.incr("stats:recovery_rate")
                
                # Éxito total: Confirmamos a Kafka que puede avanzar al siguiente offset
                consumer.commit(msg)
                    
            except ValueError as ve: # Atrapa la Poison Pill específicamente
                mensaje["intentos"] += 1
                query_id = mensaje.get("id", "N/A")
                print(f"Error procesando query {query_id}. Intento {mensaje['intentos']}. Causa: {ve}")
                
                if mensaje["intentos"] <= MAX_RETRIES:
                    # Enviar a tópico de reintentos
                    cache.incr("stats:retry_rate")
                    producer.produce('queries-retry', key=query_id, value=json.dumps(mensaje).encode('utf-8'))
                else:
                    # Superó el límite, va a la Dead Letter Queue (DLQ)
                    print(f"Query {query_id} enviada a DLQ.")
                    cache.incr("stats:dlq_rate")
                    producer.produce('queries-dlq', key=query_id, value=json.dumps(mensaje).encode('utf-8'))
                
                # Forzar el envío asíncrono
                producer.poll(0)
                # Confirmar el mensaje original
                consumer.commit(msg)
                
            except json.JSONDecodeError:
                print("[CRÍTICO] Mensaje no es JSON válido. Descartado para evitar bloqueos.")
                consumer.commit(msg)
            except Exception as e:
                print(f"[ERROR INESPERADO CRÍTICO] {e}")
                # En caso de errores, no hacemos commit. 
                # El worker se reiniciará y vuelve a intentar leer este mensaje sin perderlo.
            
    except KeyboardInterrupt:
        print("\nApagando worker limpiamente...")
    finally:
        consumer.close()

if __name__ == "__main__":
    # Esperamos unos segundos para asegurar que Kafka/Redis estén arriba en Docker
    time.sleep(10)
    run_worker()