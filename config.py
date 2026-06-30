import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings using Pydantic Settings v2.
    Loads safely from environment variables and an optional .env file.
    """
    # Use SettingsConfigDict for Pydantic v2 configurations
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database connection parameters
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")
    db_name: str = Field(default="app_db", alias="DB_NAME")

    # Application settings
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    @property
    def async_database_url(self) -> str:
        """Construct the async database URL string (e.g., using asyncpg)."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


# Instantiate a singleton settings object
settings = Settings()
