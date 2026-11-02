# -*- coding: utf-8 -*-
"""A2 設定：環境變數前綴 PQ_，讀取專案根目錄的 .env。"""
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="PQ_",
        extra="ignore",
        hide_input_in_errors=True,
    )

    service_name: str = "PrismQuant A2 Political Monitoring API"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8120
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors(cls, values: list[str]) -> list[str]:
        for value in values:
            origin = urlsplit(value)
            if origin.scheme not in {"http", "https"} or not origin.hostname or origin.path or origin.query:
                raise ValueError("CORS origins 必須是精確的 HTTP(S) 來源")
        return list(dict.fromkeys(values))

    # 大模型
    llm_api_key: str = ""
    llm_model: str = "deepseek/deepseek-chat"
    llm_base_url: str = "https://openrouter.ai/api/v1"

    # PostgreSQL
    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "prismquant_political"
    db_user: str = "prismquant_app"
    db_password: SecretStr = SecretStr("")

    # 公開發言來源（官方 RSS，免費）
    political_rss_sources: list[str] = [
        "https://www.federalreserve.gov/feeds/press_all.xml",
        "https://www.ecb.europa.eu/rss/press.html",
    ]


settings = Settings()
