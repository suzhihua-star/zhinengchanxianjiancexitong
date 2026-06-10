"""应用配置管理"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "Smart Factory Monitor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库模式: "postgres" 或 "sqlite"
    DB_MODE: str = "sqlite"

    # PostgreSQL (TimescaleDB) — 仅当 DB_MODE=postgres 时使用
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "smart_factory"

    @property
    def database_url(self) -> str:
        if self.DB_MODE == "sqlite":
            return "sqlite+aiosqlite:///./smart_factory.db"
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def is_postgres(self) -> bool:
        return self.DB_MODE == "postgres"

    # Redis（可选，未安装时自动降级）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # 模拟器
    SIMULATOR_ENABLED: bool = True
    SIMULATOR_INTERVAL_SECONDS: float = 1.0
    SIMULATOR_ANOMALY_RATE: float = 0.03
    SIMULATOR_BACKEND_URL: str = "http://localhost:8000"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
