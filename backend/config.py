"""
config.py - Application configuration loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GMAIL_EMAIL: str = os.getenv("GMAIL_EMAIL", "")
    GMAIL_PASSWORD: str = os.getenv("GMAIL_PASSWORD", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/jobagent.db")
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Derived paths
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR: str = os.path.join(BASE_DIR, "..", "data")
    RESUME_DIR: str = os.path.join(BASE_DIR, "..", "data", "resumes")
    DB_PATH: str = os.path.join(BASE_DIR, "..", "data", "jobagent.db")
    FRONTEND_DIR: str = os.path.join(BASE_DIR, "..", "frontend")

    def __init__(self):
        # Ensure required directories exist at runtime
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.RESUME_DIR, exist_ok=True)


settings = Settings()
