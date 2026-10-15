from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

def get_lead_action_keyboard(
    lead_id: int,
    phone: str,
    tg_username: Optional[str] = None,
    instagram_username: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Admin uchun lead tasdiqlash va tezkor aloqa tugmalari"""
    buttons = []

    # 1. Telegramda ochish tugmasi
    clean_phone = phone.replace("+", "").strip() if phone else ""
    if tg_username:
        tg_url = f"https://t.me/{tg_username}"
        tg_btn_text = f"📱 Telegramda yozish (@{tg_username})"
        buttons.append([InlineKeyboardButton(text=tg_btn_text, url=tg_url)])
    elif clean_phone and clean_phone != "Ko'rsatilmagan":
        tg_url = f"https://t.me/+{clean_phone}"
        tg_btn_text = "📱 Telegramda ochish"
        buttons.append([InlineKeyboardButton(text=tg_btn_text, url=tg_url)])

    # 2. Telefon qilindi va Instagram profil tugmalari
    action_row = [
        InlineKeyboardButton(text="📞 Telefon qilindi", callback_data=f"called:{lead_id}")
    ]
    if instagram_username:
        clean_ig = instagram_username.replace("@", "").strip()
        action_row.append(
            InlineKeyboardButton(text="📸 Instagram", url=f"https://instagram.com/{clean_ig}")
        )
    buttons.append(action_row)

    # 3. Rad etish tugmasi
    buttons.append([
        InlineKeyboardButton(text="❌ Kerak emas / Rad etish", callback_data=f"reject:{lead_id}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
