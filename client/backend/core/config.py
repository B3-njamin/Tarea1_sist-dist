import os
from typing import Dict, Any, List #Tipado explicito 

SERVER_URL: str = os.getenv("SERVER_URL", "http://server-backend:8000")


# CONFIGURACIÓN PARA APACHE KAFKA

KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC_QUERIES: str = os.getenv("KAFKA_TOPIC_QUERIES", "queries-main")


ZONAS: List[str] = ["Z1", "Z2", "Z3", "Z4", "Z5"]
QUERIES: List[str] = ["q1", "q2", "q3", "q4", "q5"]


progress: Dict[str, Any] = {
    "running":      False,
    "total":        0,
    "completed":    0,
    "successful":   0,
    "errors":       0,
    "distribution": None,
}