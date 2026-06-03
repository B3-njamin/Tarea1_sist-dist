import random
import asyncio
import uuid
import time
import json
import numpy as np
import httpx
from confluent_kafka import Producer
from typing import Dict, Any

from core.config import (
    SERVER_URL, 
    ZONAS, 
    QUERIES, 
    progress, 
    KAFKA_BOOTSTRAP_SERVERS, 
    KAFKA_TOPIC_QUERIES
)

# CONFIGURACIÓN DEL PRODUCTOR KAFKA
producer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'traffic-generator-producer',
    'message.timeout.ms': 10000, # Evita que el cliente espere infinitamente, en caso de problemas con el broker
    'queue.buffering.max.messages': 100000, # Aumenta el buffer interno para las pruebas de estrés
}
producer = Producer(producer_conf)

def delivery_report(err: Any, msg: Any) -> None:
    """
    Callback asíncrono ejecutado por librdkafka cuando un mensaje
    es confirmado por el broker o falla su entrega.
    Actualiza el estado compartido para el Dashboard en tiempo real.
    """
    if err is not None:
        progress["errors"] += 1
        print(f"Error al entregar mensaje a Kafka: {err}")
    else:
        progress["successful"] += 1
    
    progress["completed"] += 1

# FUNCIONES (PAYLOADS Y DISTRIBUCIONES)
def generar_zona_uniforme() -> str:
    return random.choice(ZONAS)

def generar_zona_zipf(s: float = 1.5) -> str:
    r = np.random.zipf(s)
    while r > len(ZONAS):
        r = np.random.zipf(s)
    return ZONAS[r - 1]

def construir_payload(query: str, zona: str, distribucion: str) -> Dict[str, Any]:
   
    confidence = 0.99 if distribucion == "poison_pill" else round(random.uniform(0, 1), 2)
    
    payload = {
        "id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "tipo": query,
        "intentos": 0,
        "data": {
            "zona": zona,
            "confidence_min": confidence
        }
    }

    if query == "q4":
        if distribucion == "poison_pill":
            zona_b = "Z1" # Zona B arbitraria para evitar problemas
        elif distribucion == "uniforme":
            zona_b = generar_zona_uniforme()
        else:
            zona_b = generar_zona_zipf()
        payload["data"]["zona_b"] = zona_b
        
    elif query == "q5":
        payload["data"]["bins"] = random.choice([5, 10, 20])
    
    return payload

# MOTOR PRINCIPAL DE INYECCIÓN DE TRÁFICO (ASÍNCRONO)
async def send_queries(distribucion: str, total: int) -> None:
    """
    Genera y encola las consultas en Kafka. Utilizando asyncio para no bloquear
    la API del cliente mientras se generan los mensajes por segundo.
    """
    for i in range(total):
        if not progress["running"]: 
            break
        
        try:
            # Seleccionar la zona de acuerdo a la distribución solicitada
            if distribucion == "poison_pill":
                zona = "Z5"
            elif distribucion == "uniforme":
                zona = generar_zona_uniforme()
            else:
                zona = generar_zona_zipf()
                
            query = random.choice(QUERIES)
            payload = construir_payload(query, zona, distribucion)
            
            # Encolar mensaje en el buffer interno
            producer.produce(
                topic=KAFKA_TOPIC_QUERIES, 
                key=payload["id"], 
                value=json.dumps(payload).encode('utf-8'),
                callback=delivery_report
            )
            
            # evitar desbordamiento de RAM
            producer.poll(0)
            
        except Exception as e:
            print(f"Excepción crítica produciendo mensaje: {e}")
            progress["errors"] += 1
            progress["completed"] += 1

        # cada 100 iteraciones para no bloquear a /status
        if i % 100 == 0:
            await asyncio.sleep(0)

    #Vaciar todo el buffer antes de terminar
    producer.flush()

    #Notificar que la inyección ha finalizado
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{SERVER_URL}/api/experiment/end")
    except Exception as e:
        print(f"Error al notificar fin de experimento al servidor: {e}")

    progress["running"] = False