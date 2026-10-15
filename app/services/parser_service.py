import re
from typing import Optional, Tuple

# Telefon raqamlarini topuvchi regex
# +998901234567, 998901234567, +998 90 123 45 67, 90 123 45 67, va xalqaro raqamlar
PHONE_PATTERN = re.compile(
    r"(?:\+?998[\s.-]?\(?\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}|\b9\d{8}\b|\b\(?\d{2,3}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}\b|\+?[1-9]\d{9,14})"
)

# Telegram havolalarini topuvchi regex
# t.me/username, telegram.me/username, tg://resolve?domain=username
TELEGRAM_URL_PATTERN = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)\/([a-zA-Z0-9_]{4,32})",
    re.IGNORECASE
)

# Matndagi "tg: @username" yoki "telegram: username" ko'rinishidagi yozuvlar
TELEGRAM_TEXT_PATTERN = re.compile(
    r"(?:telegram|tg|тг)[\s:]+@?([a-zA-Z0-9_]{4,32})",
    re.IGNORECASE
)

def clean_phone_number(raw_phone: str) -> str:
    """Telefon raqamini standart xalqaro formatga (+998...) keltirish"""
    digits = re.sub(r"[^\d+]", "", raw_phone.strip())

    if digits.startswith("+"):
        return digits

    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits

    if len(digits) == 9 and digits.startswith("9"):
        return "+998" + digits

    if digits.startswith("8") and len(digits) == 11 and digits.startswith("89"):
        return "+998" + digits[1:]

    return "+" + digits

def extract_phone_and_telegram(text: str, external_url: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Matndan (Bio, xabarlar yoki havola) telefon raqam va Telegram usernamesini ajratib olish.
    Qaytaradi: (phone_number, telegram_username)
    """
    if not text:
        text = ""

    combined_text = f"{text}\n{external_url or ''}"

    # 1. Telegram havolasini qidirish
    tg_username = None
    url_match = TELEGRAM_URL_PATTERN.search(combined_text)
    if url_match:
        found_tg = url_match.group(1).strip()
        # Ba'zi umumiy so'zlarni filtrlaymiz (joinchat, share va h.k.)
        if found_tg.lower() not in ["joinchat", "share", "addstickers", "c", "proxy"]:
            tg_username = found_tg

    if not tg_username:
        text_match = TELEGRAM_TEXT_PATTERN.search(combined_text)
        if text_match:
            tg_username = text_match.group(1).strip()

    # 2. Telefon raqamni qidirish
    phone_number = None
    phone_matches = PHONE_PATTERN.findall(combined_text)
    for match in phone_matches:
        cleaned = clean_phone_number(match)
        # Uzunligi kamida 9 ta raqam bo'lishi kerak
        digits_only = re.sub(r"\D", "", cleaned)
        if 9 <= len(digits_only) <= 15:
            phone_number = cleaned
            break

    return phone_number, tg_username

