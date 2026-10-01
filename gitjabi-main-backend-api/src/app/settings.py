import os, logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
load_dotenv()   # For another libraries having more security conditions...

from app.modules.enum import CacheBackendEnum

class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',  # extra=forbid (default)
        frozen=True  
    )
    #######################################
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")

    ALLOW_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]
    
    # 로그인
    TOKEN_DEFAULT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    HTTP_SECURE: bool = not(os.getenv("DEBUG", False))

    # API
    GITHUB_API_BASE_URL: str = os.getenv("GITHUB_API_BASE_URL", "https://api.github.com")
    GOVERNANCE_ENGINE_API_ENDPOINT: str = os.getenv("GOVERNANCE_ENGINE_API_ENDPOINT", "")

    # 백엔드
    CACHE_BACKEND: CacheBackendEnum = CacheBackendEnum.LOCAL_CACHE
    DATABASE_USER: str = os.getenv("DATABASE_USER", "")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_DB: str = os.getenv("DATABASE_DB", "")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", 0))

    # 지식 그래프, AI
    CONTENT_SAFETY_KEY: str      = os.getenv("CONTENT_SAFETY_KEY", "")
    CONTENT_SAFETY_ENDPOINT: str = os.getenv("CONTENT_SAFETY_ENDPOINT", "")  

    # Azure AI Search
    AI_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AI_SEARCH_KEY: str      = os.getenv("AZURE_SEARCH_KEY", "")
    AI_INDEX_NAME: str      = os.getenv("AZURE_SEARCH_INDEX", "")


api_settings = ApiSettings()


# 검증

assert api_settings.SECRET_KEY != "", "Secret Key를 입력하세요."
assert len(str(api_settings.SECRET_KEY)) > 16, "Secret Key는 16자리 이상이어야 합니다. 너무 짧습니다."
assert api_settings.DATABASE_USER != ""
assert api_settings.DATABASE_DB != ""
assert api_settings.DATABASE_PASSWORD != ""
assert api_settings.DATABASE_HOST != ""
assert api_settings.DATABASE_PORT != 0
assert api_settings.GOVERNANCE_ENGINE_API_ENDPOINT != ""
