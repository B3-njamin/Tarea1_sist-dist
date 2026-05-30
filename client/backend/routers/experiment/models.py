from pydantic import BaseModel


class RunRequest(BaseModel):
    distribution: str
    n_queries: int
