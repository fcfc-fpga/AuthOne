# backend/config.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class CasbinSettings(BaseModel):
    model_path: str = "rbac_model.conf"
    enable_auto_save: bool = True
    register_key_match: bool = True
    register_regex_match: bool = True

class CorsSettings(BaseModel):
    allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    allow_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "DELETE", "PUT", "PATCH"])
    allow_headers: List[str] = Field(default_factory=lambda: ["Authorization", "Content-Type"])

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AUTHONE_", case_sensitive=False)

    # 基础
    app_name: str = "AuthOne IAM Service"
    environment: str = "dev"  # dev / prod / test

    # DB
    db_url: str = "postgresql+asyncpg://postgres:123@127.0.0.1:5432/authone"
    init_db_drop_all: bool = True  # 生产关掉，走迁移

    # Casbin
    casbin: CasbinSettings = CasbinSettings()

    # CORS
    cors: CorsSettings = CorsSettings()

    # 资源到路径模式（原先写死在 service 里）
    resource_to_pattern: Dict[str, str] = Field(default_factory=lambda: {
        "doc": "/docs/*",
    })

def get_settings() -> AppSettings:
    return AppSettings()
