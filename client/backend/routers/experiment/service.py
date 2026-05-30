import random
import asyncio
import numpy as np
import httpx
from core.config import SERVER_URL, ZONAS, QUERIES, progress


def generar_zona_uniforme():
    return random.choice(ZONAS)


def generar_zona_zipf(s=1.5):
    r = np.random.zipf(s)
    while r > len(ZONAS):
        r = np.random.zipf(s)
    return ZONAS[r - 1]


def construir_url(query: str, zona: str, distribucion: str) -> str:
    if query in ["q1", "q2", "q3"]:
        confianza = round(random.uniform(0, 1), 2)
        return f"{SERVER_URL}/api/{query}/{zona}?confidence_min={confianza}"
    elif query == "q4":
        zona_b = generar_zona_uniforme() if distribucion == "uniforme" else generar_zona_zipf()
        confianza = round(random.uniform(0, 1), 2)
        return f"{SERVER_URL}/api/q4/{zona}/{zona_b}?confidence_min={confianza}"
    elif query == "q5":
        bins = random.choice([5, 10, 20])
        return f"{SERVER_URL}/api/q5/{zona}?bins={bins}"


async def send_queries(distribucion: str, total: int):
    async with httpx.AsyncClient(timeout=10.0) as client:
        for _ in range(total):
            try:
                zona  = generar_zona_uniforme() if distribucion == "uniforme" else generar_zona_zipf()
                query = random.choice(QUERIES)
                url   = construir_url(query, zona, distribucion)
                resp  = await client.get(url)
                if resp.status_code == 200:
                    progress["successful"] += 1
            except Exception:
                progress["errors"] += 1
            finally:
                progress["completed"] += 1

            await asyncio.sleep(0.01)

    # Avisar al servidor que terminó el experimento
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{SERVER_URL}/api/experiment/end")
    except Exception as e:
        print(f"Error al cerrar experimento: {e}")

    progress["running"] = False
