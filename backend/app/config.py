from pydantic_settings import BaseSettings
from typing import ClassVar


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    GEMINI_API_KEY: str
    PRIMARY_MODEL: str = "gemini-2.5-flash"
    FALLBACK_MODEL: str = "gemini-2.5-flash-lite"
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_MIME_TYPES: ClassVar[list[str]] = ["image/jpeg", "image/png"]
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    SCRAPE_TIMEOUT_MS: int = 120000

    @property
    def cors_origins_list(self) -> list[str]:
        """Returns CORS_ORIGINS as a list, parsing comma-separated strings if necessary."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS

    @property
    def max_image_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
