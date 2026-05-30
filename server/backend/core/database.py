import os
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import declarative_base, sessionmaker

os.makedirs("/app/data", exist_ok=True)
DATABASE_URL = "sqlite:////app/data/experiments.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)


class Experiment(Base):
    __tablename__ = "experiments"
    id               = Column(Integer, primary_key=True, index=True)
    timestamp        = Column(String)
    distribution     = Column(String)
    policy           = Column(String)
    memory_mb        = Column(Integer)
    ttl_seconds      = Column(Integer)
    n_queries        = Column(Integer)
    hits             = Column(Integer)
    misses           = Column(Integer)
    hit_rate         = Column(Float)
    throughput       = Column(Float)
    latency_p50      = Column(Float)
    latency_p95      = Column(Float)
    eviction_rate    = Column(Float)
    cache_efficiency = Column(Float)
    duration_seconds = Column(Float)


Base.metadata.create_all(bind=engine)
