import os

SERVER_URL = os.getenv("SERVER_URL", "http://server-backend:8000")

ZONAS   = ["Z1", "Z2", "Z3", "Z4", "Z5"]
QUERIES = ["q1", "q2", "q3", "q4", "q5"]

# Estado del experimento en curso (compartido entre service y router)
progress = {
    "running":      False,
    "total":        0,
    "completed":    0,
    "successful":   0,
    "errors":       0,
    "distribution": None,
}
