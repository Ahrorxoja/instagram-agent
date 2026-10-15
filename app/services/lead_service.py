import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import Lead
from app.schemas import LeadCreate
from app.services.telegram_service import userbot_service
from app.services.excel_service import append_lead_to_excel, update_lead_in_excel
from app.bot.bot import send_lead_notification_to_admin

logger = logging.getLogger(__name__)

async def process_new_lead(lead_in: LeadCreate, db: AsyncSession) -> Lead:
    """
    Yangi mijozni qayta ishlashning to'liq sikli:
    1. Bazaga saqlash
    2. Telegramda raqamni tekshirish
    3. Agar INSTAGRAM_AUTO_SEND yoqilgan bo'lsa, darhol Telegramiga avtomatik yozish
    4. Excel faylga yozish
    5. Adminga Telegram bot orqali bildirishnoma chiqarish
    """
    # 1. Boshlang'ich ma'lumotlarni bazaga qo'shish
    db_lead = Lead(
        full_name=lead_in.full_name,
        instagram_username=lead_in.instagram_username,
        phone_number=lead_in.phone_number,
        status="pending"
    )
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)

    logger.info(f"Yangi lead bazaga saqlandi: ID={db_lead.id}, Tel={db_lead.phone_number}")

    # 2. Telegram tarmog'ida ushbu telefon raqamni tekshirish
    if db_lead.phone_number and db_lead.phone_number != "Ko'rsatilmagan":
        found, tg_id, tg_user = await userbot_service.check_phone_number(
            phone=db_lead.phone_number,
            name=db_lead.full_name
        )
        if found:
            db_lead.telegram_found = True
            db_lead.telegram_id = tg_id
            db_lead.telegram_username = tg_user
            await db.commit()
            await db.refresh(db_lead)

    # 3. Avtomatik xabar jo'natish (agar INSTAGRAM_AUTO_SEND yoqilgan bo'lsa)
    if settings.INSTAGRAM_AUTO_SEND and not db_lead.message_sent:
        recipient = None
        if db_lead.telegram_username:
            recipient = f"@{db_lead.telegram_username.replace('@', '').strip()}"
        elif db_lead.telegram_id:
            recipient = db_lead.telegram_id
        elif db_lead.phone_number and db_lead.phone_number != "Ko'rsatilmagan":
            recipient = db_lead.phone_number

        if recipient:
            msg_text = settings.AUTO_MESSAGE_TEMPLATE.replace("\\n", "\n")
            logger.info(f"Yangi mijozga avtomatik xabar jo'natilmoqda: {recipient}")
            success = await userbot_service.send_direct_message(recipient, msg_text, name=db_lead.full_name)
            if success:
                db_lead.message_sent = True
                db_lead.status = "sent"
                await db.commit()
                await db.refresh(db_lead)

    lead_dict = db_lead.to_dict()

    # 4. Excel faylga saqlash
    append_lead_to_excel(lead_dict)

    # 5. Adminga bildirishnoma yuborish
    await send_lead_notification_to_admin(lead_dict)

    return db_lead
