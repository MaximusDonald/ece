from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/ece", validation_alias="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    
    # MinIO
    minio_endpoint: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", validation_alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")
    
    # Security
    secret_key: str = Field(default="dev-secret-change-in-production", validation_alias="SECRET_KEY")
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # LLM
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: Optional[str] = Field(default="llama-3.3-70b-versatile", validation_alias="GROQ_MODEL")
    gemini_api_key: Optional[str] = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: Optional[str] = Field(default="gemini-1.5-flash", validation_alias="GEMINI_MODEL")
    
    # OAuth
    google_oauth_client_id: Optional[str] = Field(default=None, validation_alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: Optional[str] = Field(default=None, validation_alias="GOOGLE_OAUTH_CLIENT_SECRET")
    github_oauth_client_id: Optional[str] = Field(default=None, validation_alias="GITHUB_OAUTH_CLIENT_ID")
    github_oauth_client_secret: Optional[str] = Field(default=None, validation_alias="GITHUB_OAUTH_CLIENT_SECRET")
    
    # Frontend
    frontend_url: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()