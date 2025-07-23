import os
from typing import Optional

from constants import OpenAIModels, ProcessingDefaults
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Settings
    app_name: str = "Document Intelligence Platform"
    debug: bool = Field(default=False, env="DEBUG")

    # API Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # CORS Settings (hardcoded for simplicity)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # File Upload Settings
    max_file_size: int = Field(
        default=ProcessingDefaults.MAX_FILE_SIZE, env="MAX_FILE_SIZE"
    )
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")

    # Database Settings
    database_url: str = Field(
        default="sqlite:///./document_intelligence.db", env="DATABASE_URL"
    )

    # Vector Database Settings
    vector_db_path: str = Field(default="./vector_db", env="VECTOR_DB_PATH")
    qdrant_url: Optional[str] = Field(default=None, env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")

    # LLM API Settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")

    # OpenAI Embedding Settings
    openai_embedding_model: str = Field(
        default=OpenAIModels.TEXT_EMBEDDING_SMALL, env="OPENAI_EMBEDDING_MODEL"
    )
    openai_embedding_dimension: int = Field(
        default=1536, env="OPENAI_EMBEDDING_DIMENSION"
    )

    # Text Processing Settings
    chunk_size: int = Field(default=ProcessingDefaults.CHUNK_SIZE, env="CHUNK_SIZE")
    chunk_overlap: int = Field(
        default=ProcessingDefaults.CHUNK_OVERLAP, env="CHUNK_OVERLAP"
    )

    # Search Settings
    max_search_results: int = Field(
        default=ProcessingDefaults.DEFAULT_SEARCH_LIMIT, env="MAX_SEARCH_RESULTS"
    )
    similarity_threshold: float = Field(
        default=ProcessingDefaults.SIMILARITY_THRESHOLD, env="SIMILARITY_THRESHOLD"
    )

    # Qdrant Vector Database Settings
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Don't require .env file - use defaults if not found
        extra = "ignore"


# Global settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.vector_db_path, exist_ok=True)
