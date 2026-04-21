"""
TamgaFlow Configuration
Powered by TOUROSAT — Tourism Revenue Hackathon Kyrgyzstan
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # === App Meta ===
    APP_NAME: str = "TamgaFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # === Security ===
    SECRET_KEY: str = "tamgaflow-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа
    
    # === Database ===
    DATABASE_URL: str = "sqlite+aiosqlite:///./tamgaflow.db"
    
    # === Revenue Split (CORE BUSINESS LOGIC) ===
    REVENUE_OWNER_PCT: float = 88.0      # Хозяину юрты
    REVENUE_PLATFORM_PCT: float = 7.0    # TamgaFlow
    REVENUE_FUND_PCT: float = 5.0        # WeFund
    
    # === Rest Points (Loyalty) ===
    REST_POINTS_CASHBACK_PCT: float = 10.0  # 10% кэшбек
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
    TOUROSAT_MODELS_DIR: str = "./app/ml/models"
    TOUROSAT_ENSEMBLE_SIZE: int = 3
    TOUROSAT_N_FEATURES: int = 24
    
    # === Dynamic Pricing ===
    PRICING_BASE_MULTIPLIER: float = 1.0
    PRICING_SCORE_80_PLUS_MULTIPLIER: float = 1.3  # Топ места +30%
    PRICING_SCORE_60_79_MULTIPLIER: float = 1.0
    PRICING_SCORE_BELOW_60_MULTIPLIER: float = 0.8
    
    # === Paths ===
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Кешированная загрузка настроек"""
    return Settings()


settings = get_settings()