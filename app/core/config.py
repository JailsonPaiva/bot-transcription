"""Configuração centralizada da aplicação."""
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Meta / WhatsApp
    verify_token: str = Field(default="", alias="VERIFY_TOKEN")
    meta_wa_token: str = Field(default="", alias="META_WA_TOKEN")
    wa_phone_number_id: str = Field(default="", alias="WA_PHONE_NUMBER_ID")
    meta_app_secret: str = Field(default="", alias="META_APP_SECRET")
    require_webhook_signature: bool = Field(default=False, alias="REQUIRE_WEBHOOK_SIGNATURE")

    # Serviços
    transcription_service: str = Field(default="gladia", alias="TRANSCRIPTION_SERVICE")
    enable_gemini_correction: bool = Field(default=True, alias="ENABLE_GEMINI_CORRECTION")
    message_service: str = Field(default="whatsapp", alias="MESSAGE_SERVICE")
    gemini_model: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL")

    # Redis / estado
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    use_redis: bool = Field(default=True, alias="USE_REDIS")
    dedupe_ttl_seconds: int = Field(default=86400, alias="DEDUPE_TTL_SECONDS")
    session_ttl_seconds: int = Field(default=1800, alias="SESSION_TTL_SECONDS")

    # Resiliência
    http_timeout_seconds: float = Field(default=30.0, alias="HTTP_TIMEOUT_SECONDS")
    http_max_retries: int = Field(default=3, alias="HTTP_MAX_RETRIES")
    http_retry_backoff_seconds: float = Field(default=1.5, alias="HTTP_RETRY_BACKOFF_SECONDS")

    # Rate limit simples (Sprint 1 base)
    max_audio_per_hour: int = Field(default=20, alias="MAX_AUDIO_PER_HOUR")

    # Branding do PDF (futuro: por cliente no banco)
    pdf_company_name: str = Field(default="Sua Empresa de Materiais", alias="PDF_COMPANY_NAME")
    pdf_tagline: str = Field(
        default="Orçamentos para obra, direto no WhatsApp",
        alias="PDF_TAGLINE",
    )
    pdf_logo_path: str = Field(default="", alias="PDF_LOGO_PATH")
    pdf_phone: str = Field(default="", alias="PDF_PHONE")
    pdf_website: str = Field(default="", alias="PDF_WEBSITE")
    pdf_primary_color: str = Field(default="27,54,93", alias="PDF_PRIMARY_COLOR")
    pdf_accent_color: str = Field(default="242,141,62", alias="PDF_ACCENT_COLOR")
    pdf_validade_dias: int = Field(default=7, alias="PDF_VALIDADE_DIAS")

    @property
    def message_service_normalized(self) -> str:
        return self.message_service.lower().strip()

    @property
    def transcription_service_normalized(self) -> str:
        return self.transcription_service.lower().strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
