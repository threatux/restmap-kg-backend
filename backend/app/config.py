"""
TamgaFlow Configuration
Powered by TOUROSAT — Tourism Revenue Hackathon Kyrgyzstan
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    # === App Meta ===
    APP_NAME: str = "TamgaFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # === API ===
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # === Security ===
    SECRET_KEY: str = "tamgaflow-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа
    
    # === Database ===
    DATABASE_URL: str = "sqlite+aiosqlite:///./tamgaflow.db"
    
    # === Revenue Split (CORE BUSINESS LOGIC) ===
    REVENUE_OWNER_PCT: float = 88.0
    REVENUE_PLATFORM_PCT: float = 7.0
    REVENUE_FUND_PCT: float = 5.0
    
    # Alias-совместимость (на случай другой нотации в .env)
    OWNER_PERCENT: float = 88.0
    PLATFORM_FEE_PERCENT: float = 7.0
    FUND_PERCENT: float = 5.0
    
    # === Rest Points (Loyalty) ===
    REST_POINTS_CASHBACK_PCT: float = 10.0
    REST_POINTS_CASHBACK_PERCENT: float = 3.0  # alias
    REST_POINTS_LEVEL_BRONZE: int = 0
    REST_POINTS_LEVEL_SILVER: int = 1000
    REST_POINTS_LEVEL_GOLD: int = 5000
    
    # === LLM (Ollama) ===
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT: int = 60
    
    # === External APIs ===
    OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"
    
    # === TOUROSAT ===
    TOUROSAT_ENABLED: bool = True
    TOUROSAT_MIN_CONFIDENCE: float = 0.65
    TOUROSAT_MODELS_DIR: str = "./app/ml/models"
    TOUROSAT_ENSEMBLE_SIZE: int = 3
    TOUROSAT_N_FEATURES: int = 24
    
    # === Dynamic Pricing ===
    PRICING_BASE_MULTIPLIER: float = 1.0
    PRICING_SCORE_80_PLUS_MULTIPLIER: float = 1.3
    PRICING_SCORE_60_79_MULTIPLIER: float = 1.0
    PRICING_SCORE_BELOW_60_MULTIPLIER: float = 0.8
    
    # === Paths ===
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    # 🔥 Новый синтаксис Pydantic v2 — разрешаем extra поля
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # 🔥 ИГНОРИРОВАТЬ неизвестные переменные из .env
    )


@lru_cache()
def get_settings() -> Settings:
    """Кешированная загрузка настроек"""
    return Settings()


settings = get_settings()