import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str = ""
    ADMIN_TELEGRAM_ID: int = 0

    # Telegram Userbot (Telethon)
    TELEGRAM_API_ID: Optional[int] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_PHONE: Optional[str] = None

    # Instagram sozlamalari (Hisobingizga avtomatik ulanish uchun)
    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None
    INSTAGRAM_SESSION_FILE: str = "instagram_session.json"
    INSTAGRAM_CHECK_INTERVAL: int = 30  # Har 30 soniyada yangi chatlarni tekshirish
    INSTAGRAM_SCAN_AMOUNT: int = 100    # Direct chatlar skanerlash miqdori (20 o'rniga 100 ta)
    INSTAGRAM_AUTO_SEND: bool = False   # True bo'lsa adminga so'ramasdan darhol xabar yuboradi

    # Database (Supabase / PostgreSQL)
    DATABASE_URL: str = "sqlite+aiosqlite:///./leads.db"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Excel and message templates
    EXCEL_FILE_PATH: str = "leads.xlsx"
    AUTO_MESSAGE_TEMPLATE: str = (
        "Assalomu alaykum {name}! Siz Instagram sahifamizda so'rov qoldirgan edingiz. "
        "Sizga qanday yordam bera olamiz?"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

