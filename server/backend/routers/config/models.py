from pydantic import BaseModel


class ConfigRequest(BaseModel):
    ttl: int
    policy: str
    memory_mb: int
