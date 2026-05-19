from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # --- DB ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:54322/postgres"

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model_chat: str = "gpt-4o-mini"
    openai_model_review: str = "gpt-4o"

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
