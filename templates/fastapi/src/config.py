"""
Uygulama yapılandırması.
.env dosyasından okunur.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Uygulama
    app_name: str = "{project_name}"
    debug: bool = False

    # Veritabanı
    database_url: str = "sqlite:///./app.db"

    # Güvenlik
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Ayarları önbellekli döner."""
    return Settings()
