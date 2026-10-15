import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from sqlalchemy import select, desc
from app.database import AsyncSessionLocal
from app.models import Lead
from app.config import settings
from app.services.telegram_service import userbot_service
from app.services.excel_service import update_lead_in_excel, ensure_excel_file

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def handle_start(message: Message):
    is_admin = message.from_user and message.from_user.id == settings.ADMIN_TELEGRAM_ID
    if is_admin:
        await message.answer(
            "👋 <b>Assalomu alaykum, Administrator!</b>\n\n"
            "Instagram Lead boshqaruv boti to'liq faol ishlamoqda.\n\n"
            "📌 <b>Mavjud buyruqlar:</b>\n"
            "📊 /stats — Mijozlar bo'yicha statistika\n"
            "📑 /excel — Excel faylni (.xlsx) Telegramga yuklab olish\n"
            "👥 /last — Oxirgi 5 ta mijoz ro'yxati\n"
            "ℹ️ /help — Yordam va qo'llanma\n\n"
            "<i>Instagram Direct'dan yangi mijozlar aniqlanishi bilan shu yerga xabar va tezkor aloqa tugmalari keladi.</i>"
        )
    else:
        await message.answer(
            f"Assalomu alaykum! Sizning Telegram ID raqamingiz: <code>{message.from_user.id}</code>\n"
            f"Administrator bilan bog'laning."
        )

@router.message(Command("stats"))
async def handle_stats(message: Message):
    """Baza bo'yicha qisqacha statistika"""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead))
        leads = result.scalars().all()
        total = len(leads)
        called = sum(1 for l in leads if l.phone_called)
        sent = sum(1 for l in leads if l.message_sent)
        pending = sum(1 for l in leads if l.status == "pending")

        await message.answer(
            f"📊 <b>Mijozlar statistikasi:</b>\n\n"
            f"🔹 Jami mijozlar: <b>{total} ta</b>\n"
            f"📞 Qo'ng'iroq qilingan: <b>{called} ta</b>\n"
            f"✉️ Telegramdan yozilgan: <b>{sent} ta</b>\n"
            f"⏳ Kutilayotganlar: <b>{pending} ta</b>"
        )

@router.message(Command("scan"))
async def handle_scan_command(message: Message):
    """Instagram Direct chatlarini qayta chuqur skanerlash"""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        return

    # Foydalanuvchi son kiritgan bo'lsa (masalan: /scan 200 yoki /scan 500)
    args = message.text.split()
    amount = 100
    if len(args) > 1 and args[1].isdigit():
        amount = min(int(args[1]), 500)

    from app.services.instagram_service import instagram_watcher
    if not instagram_watcher._is_logged_in:
        await message.answer("⚠️ Instagramga ulanmagan! Iltimos, sessiyani tekshiring.")
        return

    status_msg = await message.answer(f"⏳ Instagram Direct'dan <b>{amount} ta</b> suhbat to'liq skanerlanmoqda... Bir oz kuting.")

    try:
        new_found = await instagram_watcher.scan_and_process(amount=amount)
        await status_msg.edit_text(
            f"✅ <b>Skanerlash yakunlandi!</b>\n\n"
            f"🔍 Tekshirilgan chatlar: <b>{amount} ta</b>\n"
            f"🆕 Yangi topilgan mijozlar: <b>{new_found} ta</b>\n\n"
            f"Yangilangan bazani olish uchun <b>/excel</b> buyrug'ini bosing."
        )
    except Exception as e:
        logger.error(f"Skanerlashda xatolik: {e}")
        await status_msg.edit_text(f"❌ Skanerlashda xatolik yuz berdi: {e}")

@router.message(Command("send_all"))
async def handle_send_all(message: Message):
    """Barcha hali xabar olmagan mijozlarga avtomatik xabar yuborishni boshlash"""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        return

    from app.services.broadcast_service import broadcast_service
    await broadcast_service.start_broadcast(message.chat.id)

@router.message(Command("stop_send"))
async def handle_stop_send(message: Message):
    """Xabar tarqatishni to'xtatish"""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        return

    from app.services.broadcast_service import broadcast_service
    await broadcast_service.stop_broadcast(message.chat.id)

@router.message(Command("excel"))
async def handle_excel_download(message: Message):
    """Excel faylini to'g'ridan-to'g'ri Telegram chatga yuborish"""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        return

    file_path = settings.EXCEL_FILE_PATH
    if not os.path.exists(file_path):
        ensure_excel_file()

    try:
        excel_file = FSInputFile(path=file_path, filename="leads.xlsx")
        await message.answer_document(
            document=excel_file,
            caption="📑 <b>Mijozlarning to'liq Excel bazasi</b>\n(Status va qo'ng'iroqlar bilan)"
        )
    except Exception as e:
        logger.error(f"Excel faylini yuborishda xatolik: {e}")
        await message.answer(f"❌ Faylni yuklashda xatolik: {e}")

@router.message(Command("last"))
async def handle_last_leads(message: Message):
    """Oxirgi 5 ta mijozni ko'rsatish"""
    if message.from_user.id != settings.ADMIN_TELEGRAM_ID:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Lead).order_by(desc(Lead.id)).limit(5)
        )
        leads = result.scalars().all()

        if not leads:
            await message.answer("Hozircha bazada mijozlar mavjud emas.")
            return

        text = "👥 <b>Oxirgi 5 ta mijoz:</b>\n\n"
        for l in leads:
            called_icon = "✅" if l.phone_called else "❌"
            insta = f"@{l.instagram_username}" if l.instagram_username else "-"
            text += (
                f"<b>#{l.id} {l.full_name}</b>\n"
                f"📞 <code>{l.phone_number}</code> | 📸 {insta}\n"
                f"Tel qilindi: {called_icon} | Status: <i>{l.status}</i>\n"
                f"━━━━━━━━━━━━━━\n"
            )

        await message.answer(text)

@router.message(Command("help"))
async def handle_help(message: Message):
    """Yordam komandasi"""
    await message.answer(
        "ℹ️ <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1. <b>Instagram Direct:</b> Siz Instagramda xaridor bilan yozishganingizda, bot avtomatik uning telefon raqami va Telegramini aniqlab shu yerga yuboradi.\n"
        "2. <b>Aloqa:</b> Xabar ostidagi '📱 Telegramda ochish' tugmasi orqali to'g'ridan-to'g'ri mijoz bilan chat ochasiz.\n"
        "3. <b>Qo'ng'iroq:</b> Telefon qilgach '📞 Telefon qilindi' tugmasini bossangiz, Excelda avtomatik 'Ha' bo'lib saqlanadi.\n"
        "4. <b>Baza:</b> Istalgan vaqtda /excel buyrug'i orqali faylni yuklab olishingiz mumkin."
    )

@router.callback_query(F.data.startswith("send_msg:"))
async def handle_send_message_callback(callback: CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    await callback.answer("Xabar yuborilmoqda...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()

        if not lead:
            await callback.message.edit_text("❌ Mijoz bazadan topilmadi.")
            return

        if lead.message_sent:
            await callback.message.reply("⚠️ Bu mijozga allaqachon xabar yuborilgan.")
            return

        message_text = settings.AUTO_MESSAGE_TEMPLATE.format(name=lead.full_name)
        recipient = lead.telegram_id if lead.telegram_id else lead.phone_number

        success = await userbot_service.send_direct_message(recipient, message_text)

        if success:
            lead.message_sent = True
            lead.status = "sent"
            await session.commit()
            update_lead_in_excel(lead.id, status="sent", message_sent=True)

            await callback.message.edit_text(
                f"{callback.message.html_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ <b>Xabar muvaffaqiyatli yuborildi!</b>\n"
                f"✉️ <i>\"{message_text}\"</i>"
            )
        else:
            lead.status = "failed"
            await session.commit()
            update_lead_in_excel(lead.id, status="failed", message_sent=False)

            clean_phone = lead.phone_number.replace("+", "").strip()
            await callback.message.edit_text(
                f"{callback.message.html_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ <b>Avtomatik xabar yuborib bo'lmadi!</b>\n"
                f"👉 <a href='https://t.me/+{clean_phone}'>Mijoz bilan qo'lda bog'lanish</a>"
            )

@router.callback_query(F.data.startswith("called:"))
async def handle_called_callback(callback: CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    await callback.answer("Qo'ng'iroq qilindi deb belgilandi")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()

        if lead:
            lead.phone_called = True
            await session.commit()
            update_lead_in_excel(lead.id, phone_called=True)

    await callback.message.reply(f"📞 #{lead_id} mijozga qo'ng'iroq qilindi deb belgilandi va Excel yangilandi.")

@router.callback_query(F.data.startswith("reject:"))
async def handle_reject_callback(callback: CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    await callback.answer("Rad etildi")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()

        if lead:
            lead.status = "rejected"
            await session.commit()
            update_lead_in_excel(lead.id, status="rejected", message_sent=False)

    await callback.message.edit_text(
        f"{callback.message.html_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"❌ <b>Xabar yuborish bekor qilindi.</b>"
    )
