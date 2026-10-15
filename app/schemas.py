from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re

def normalize_phone(phone: str) -> str:
    """Telefon raqamidan faqat raqam va '+' belgisini qoldirish"""
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if not cleaned.startswith("+"):
        if cleaned.startswith("998"):
            cleaned = "+" + cleaned
        elif len(cleaned) == 9:
            cleaned = "+998" + cleaned
        else:
            cleaned = "+" + cleaned
    return cleaned

class LeadCreate(BaseModel):
    full_name: str = Field(..., description="Mijozning ismi va familiyasi", min_length=1)
    instagram_username: Optional[str] = Field(None, description="Instagram username yoki profil havolasi")
    phone_number: Optional[str] = Field("Ko'rsatilmagan", description="Telefon raqami (masalan: +998901234567)")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> str:
        if not v or v.strip() in ["Ko'rsatilmagan", "-", "null", "none", ""]:
            return "Ko'rsatilmagan"
        cleaned = normalize_phone(v)
        digits_only = re.sub(r"\D", "", cleaned)
        if len(digits_only) < 7:
            return "Ko'rsatilmagan"
        return cleaned

class LeadResponse(BaseModel):
    id: int
    full_name: str
    instagram_username: Optional[str]
    phone_number: str
    telegram_id: Optional[int]
    telegram_username: Optional[str]
    telegram_found: bool
    message_sent: bool
    phone_called: bool = False
    notes: Optional[str] = None
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class SendMessageRequest(BaseModel):
    lead_id: int
    custom_message: Optional[str] = None

