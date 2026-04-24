from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator, model_validator

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when required environment variables are missing or invalid."""
    pass


class Settings(BaseSettings):
    # Application settings
    app_name: str = Field(default="AI Virtual Coach API", env="APP_NAME")
    app_version: str = Field(default="3.0.0", env="APP_VERSION")
    frontend_url: str = Field(default="", env="FRONTEND_URL")
    
    # Database settings
    database_url: str = Field(default="", env="DATABASE_URL")
    
    # JWT settings
    jwt_secret_key: str = Field(default="", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Admin settings
    admin_email: str = Field(default="", env="ADMIN_EMAIL")
    admin_password: str = Field(default="", env="ADMIN_PASSWORD")
    
    # LLM settings
    llm_timeout_s: float = Field(default=12.0, env="LLM_TIMEOUT_S")
    llm_temperature: float = Field(default=0.2, env="LLM_TEMPERATURE")
    llm_top_p: float = Field(default=0.9, env="LLM_TOP_P")
    llm_retry_count: int = Field(default=2, env="LLM_RETRY_COUNT")
    llm_cache_ttl_s: int = Field(default=900, env="LLM_CACHE_TTL_SECONDS")
    
    # Google API settings
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    
    @validator('google_api_key')
    def validate_google_api_key(cls, v):
        if not v:
            raise ValueError('GOOGLE_API_KEY is required for Gemini API access')
        return v
    
    # ChromaDB settings
    chroma_dir: str = Field(default="./.chroma", env="CHROMA_DIR")
    
    # HuggingFace settings
    hf_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="HF_EMBEDDING_MODEL")
    hf_home: str = Field(default="/app/.hf_cache", env="HF_HOME")
    
    # Rate limiting
    ratelimit_enabled: bool = Field(default=True, env="RATELIMIT_ENABLED")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator('admin_email')
    def validate_admin_email(cls, v):
        if not v:
            raise ValueError('ADMIN_EMAIL is required')
        if "@" not in v:
            raise ValueError(f'Invalid admin email format: {v}')
        return v.lower()
    
    @validator('admin_password')
    def validate_admin_password(cls, v):
        if not v:
            raise ValueError('ADMIN_PASSWORD is required')
        if len(v) < 12:
            raise ValueError('ADMIN_PASSWORD must be at least 12 characters long')
        
        # Check for password complexity
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                'ADMIN_PASSWORD must contain at least one uppercase letter, '
                'one lowercase letter, one digit, and one special character'
            )
        
        # Check for common weak passwords
        weak_passwords = [
            'password', '123456', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', 'dragon', 'master', 'sunshine'
        ]
        if v.lower() in weak_passwords:
            raise ValueError('ADMIN_PASSWORD is too common and weak. Please choose a stronger password.')
        
        return v
    
    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        if not v:
            raise ValueError('JWT_SECRET_KEY is required')
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters long for security')
        return v
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if v and not v.startswith(("sqlite://", "postgresql://", "postgresql+psycopg2://", "mysql://")):
            raise ValueError(f'Invalid DATABASE_URL format: {v}')
        return v
    
    @validator('llm_timeout_s')
    def validate_llm_timeout(cls, v):
        if v <= 0:
            raise ValueError('LLM_TIMEOUT_S must be positive')
        return v
    
    @validator('llm_temperature')
    def validate_llm_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('LLM_TEMPERATURE must be between 0 and 2')
        return v
    
    @validator('llm_top_p')
    def validate_llm_top_p(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('LLM_TOP_P must be between 0 and 1')
        return v
    
    @validator('llm_retry_count')
    def validate_llm_retry_count(cls, v):
        if v < 0:
            raise ValueError('LLM_RETRY_COUNT must be non-negative')
        return v
    
    @validator('llm_cache_ttl_s')
    def validate_llm_cache_ttl(cls, v):
        if v < 0:
            raise ValueError('LLM_CACHE_TTL_SECONDS must be non-negative')
        return v
    
    @model_validator(mode='after')
    def validate_all_settings(cls, values):
        logger.info("Configuration validation passed")
        return values


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get and validate application settings."""
    try:
        return Settings()
    except Exception as e:
        logger.critical(f"Application configuration error: {e}")
        raise ConfigurationError(f"Failed to load configuration: {e}")
