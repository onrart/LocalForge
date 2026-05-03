"""
{project_name} — Ana Uygulama
FastAPI + SQLAlchemy + Pydantic
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import Base, engine

# Tabloları oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="{project_name}",
    description="{project_description}",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Servis sağlık kontrolü."""
    return {"status": "ok", "version": "0.1.0"}
