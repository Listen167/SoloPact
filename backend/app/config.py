from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SoloPact"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./receivables_radar.db"
    local_storage_path: Path = Path("./storage")
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    demo_today: date = date(2026, 11, 4)

    huawei_obs_endpoint: str | None = None
    huawei_obs_access_key: str | None = None
    huawei_obs_secret_key: str | None = None
    huawei_obs_bucket: str | None = None

    huawei_ocr_endpoint: str | None = None
    huawei_ocr_token: str | None = None
    huawei_ocr_project_id: str | None = None

    model_base_url: str | None = None
    model_api_key: str | None = None
    model_name: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
