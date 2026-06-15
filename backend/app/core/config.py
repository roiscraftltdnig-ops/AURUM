from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    claude_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    app_base_url: str = "http://localhost:8000"
    admin_chat_id: str = ""
    admin_notification_group: str = ""
    cors_origins: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: str = ""
    smtp_user: str = ""
    smtp_password: str = ""
    access_token_minutes: int = 720
    ai_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    daily_report_hour_utc: int = 17

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cors_origin_list() -> list[str]:
    return [origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()]
