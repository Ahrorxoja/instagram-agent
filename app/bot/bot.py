import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.config import settings
from app.bot.keyboards import get_lead_action_keyboard

logger = logging.getLogger(__name__)

# Aiogram 3 bot va dispatcher inisializatsiyasi
bot = Bot(
    token=settings.BOT_TOKEN or "123456:dummy_token_for_validation",
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

async def send_lead_notification_to_admin(lead_dict: dict) -> bool:
    """
    Administratorga yangi mijoz haqida bildirishnoma va 'Ha/Yo'q' tugmalarini yuborish
    """
    if not settings.BOT_TOKEN or not settings.ADMIN_TELEGRAM_ID:
        logger.warning("BOT_TOKEN yoki ADMIN_TELEGRAM_ID sozlanmagan. Adminga xabar yuborilmadi.")
        return False

    tg_status = "✅ Mavjud" if lead_dict.get("telegram_found") else "⚠️ Qidirilmoqda / Topilmadi"
    tg_user = f" (@{lead_dict.get('telegram_username')})" if lead_dict.get("telegram_username") else ""
    insta = lead_dict.get("instagram_username") or "Ko'rsatilmagan"

    text = (
        f"🔥 <b>Yangi mijoz qabul qilindi!</b>\n\n"
        f"🆔 <b>Lead ID:</b> #{lead_dict.get('id')}\n"
        f"👤 <b>Ism:</b> {lead_dict.get('full_name')}\n"
        f"📸 <b>Instagram:</b> {insta}\n"
        f"📞 <b>Telefon:</b> <code>{lead_dict.get('phone_number')}</code>\n"
        f"✈️ <b>Telegram:</b> {tg_status}{tg_user}\n"
        f"⏰ <b>Vaqt:</b> {lead_dict.get('created_at')}\n\n"
        f"<i>Ushbu mijozga Telegram orqali xabar yuborilsinmi?</i>"
    )

    keyboard = get_lead_action_keyboard(
        lead_id=lead_dict.get("id"),
        phone=lead_dict.get("phone_number"),
        tg_username=lead_dict.get("telegram_username"),
        instagram_username=lead_dict.get("instagram_username")
    )

    try:
        await bot.send_message(
            chat_id=settings.ADMIN_TELEGRAM_ID,
            text=text,
            reply_markup=keyboard
        )
        logger.info(f"Adminga #{lead_dict.get('id')} lead bo'yicha bildirishnoma yuborildi.")
        return True
    except Exception as e:
        logger.error(f"Adminga bildirishnoma yuborishda xatolik: {e}")
        return False

