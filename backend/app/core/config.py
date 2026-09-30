import os
from pathlib import Path
from typing import Dict, Any, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CEST Practice Simulator"
    VERSION: str = "1.0.0"

    # Database & Storage
    DATABASE_URL: str = "sqlite:///./data/cest.db"
    AUDIO_STORAGE_DIR: str = "./data/audio"

    # AI Provider Config
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    LM_STUDIO_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LM_STUDIO_MODEL: str = "local-model"
    LM_STUDIO_API_KEY: str = "lm-studio"

    AI_DEFAULT_PROVIDER: str = "lm_studio"
    WRITING_DEFAULT_PROVIDER: str = "lm_studio"

    # Exam Timings (in seconds, per PRD Section 2.1 & 35.3)
    READING_MAX_TIME_SECONDS: int = 59 * 60     # 59 min
    LISTENING_MAX_TIME_SECONDS: int = 59 * 60   # 59 min
    WRITING_MAX_TIME_SECONDS: int = 45 * 60     # 45 min
    WRITING_PART1_RECOMMENDED_MINUTES: int = 15
    WRITING_PART2_RECOMMENDED_MINUTES: int = 30
    WRITING_PART1_MIN_WORDS: int = 50
    WRITING_PART2_MIN_WORDS: int = 180

    # Adaptive Engine Defaults (PRD Section 15)
    IRT_PRIOR_MEAN: float = 0.0
    IRT_PRIOR_SD: float = 1.0
    IRT_MIN_ITEM_UNITS_SIMULATION: int = 12
    IRT_MAX_ITEM_UNITS_SIMULATION: int = 30
    IRT_TARGET_SE: float = 0.30
    IRT_TOP_K_EXPOSURE: int = 3

    # CEFR Calibration Thresholds (PRD Section 15.5)
    # A1 < -1.20, A2 [-1.20, -0.40), B1 [-0.40, +0.40), B2 [+0.40, +1.20), C1 >= +1.20
    CEFR_THETA_THRESHOLDS: Dict[str, float] = {
        "A1_MAX": -1.20,
        "A2_MAX": -0.40,
        "B1_MAX": 0.40,
        "B2_MAX": 1.20,
    }

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure data & audio directories exist
Path(settings.AUDIO_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    Path(db_file).parent.mkdir(parents=True, exist_ok=True)
