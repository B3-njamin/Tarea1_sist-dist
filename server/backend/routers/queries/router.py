from fastapi import APIRouter, HTTPException
from core.config import ZONAS
from routers.queries.service import handle_query, q1_count, q2_area, q3_density, q4_compare, q5_confidence_dist

router = APIRouter()


@router.get("/api/q1/{zona_id}")
def api_q1(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"count:{zona_id}:conf={round(confidence_min, 2)}",
        lambda: {"zona": zona_id, "count": q1_count(zona_id, confidence_min)}
    )


@router.get("/api/q2/{zona_id}")
def api_q2(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"area:{zona_id}:conf={round(confidence_min, 2)}",
        lambda: q2_area(zona_id, confidence_min)
    )


@router.get("/api/q3/{zona_id}")
def api_q3(zona_id: str, confidence_min: float = 0.0):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"density:{zona_id}:conf={round(confidence_min, 2)}",
        lambda: {"zona": zona_id, "density": q3_density(zona_id, confidence_min)}
    )


@router.get("/api/q4/{zona_a}/{zona_b}")
def api_q4(zona_a: str, zona_b: str, confidence_min: float = 0.0):
    if zona_a not in ZONAS or zona_b not in ZONAS:
        raise HTTPException(status_code=400, detail="Zonas no válidas")
    return handle_query(
        f"compare:density:{zona_a}:{zona_b}:conf={round(confidence_min, 2)}",
        lambda: q4_compare(zona_a, zona_b, confidence_min)
    )


@router.get("/api/q5/{zona_id}")
def api_q5(zona_id: str, bins: int = 5):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=400, detail="Zona no válida")
    return handle_query(
        f"confidence_dist:{zona_id}:bins={bins}",
        lambda: {"zona": zona_id, "distribution": q5_confidence_dist(zona_id, bins)}
    )
