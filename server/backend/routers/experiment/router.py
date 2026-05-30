from fastapi import APIRouter
from routers.experiment.models import ExperimentStart
from routers.experiment.service import start_experiment, end_experiment, get_stats, get_history, clear_history

router = APIRouter()


@router.post("/api/experiment/start")
def api_start_experiment(req: ExperimentStart):
    return start_experiment(req.distribution, req.n_queries)


@router.post("/api/experiment/end")
def api_end_experiment():
    return end_experiment()


@router.get("/api/stats")
def api_get_stats():
    return get_stats()


@router.get("/api/history")
def api_get_history():
    return get_history()


@router.delete("/api/history")
def api_clear_history():
    return clear_history()
