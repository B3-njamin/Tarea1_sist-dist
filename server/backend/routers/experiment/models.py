from pydantic import BaseModel


class ExperimentStart(BaseModel):
    distribution: str
    n_queries: int
