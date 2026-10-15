import asyncio
import logging
from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Lead
from app.services.telegram_service import userbot_service
from app.services.excel_service import update_lead_in_excel
from app.bot.bot import bot

logger = logging.getLogger(__name__)

class BroadcastService:
    def __init__(self):
        self.is_broadcasting = False
        self.current_task: asyncio.Task = None

    async def start_broadcast(self, admin_chat_id: int):
        """Barcha hali xabar olmagan mijozlarga avtomatik xabar tarqatish"""
        if self.is_broadcasting:
            await bot.send_message(admin_chat_id, "⚠️ Xabar tarqatish jarayoni allaqachon ishlab turibdi!")
            return

        if not userbot_service._is_ready:
            await bot.send_message(
                admin_chat_id,
                "❌ Telegram Userbot faol emas! Iltimos, sessiya mavjudligini tekshiring."
            )
            return

        self.is_broadcasting = True
        self.current_task = asyncio.create_task(self._broadcast_worker(admin_chat_id))

    async def stop_broadcast(self, admin_chat_id: int):
        """Jarayonni to'xtatish"""
        if not self.is_broadcasting:
            await bot.send_message(admin_chat_id, "Hozir hech qanday xabar tarqatish jarayoni ketmayapti.")
            return

        self.is_broadcasting = False
        if self.current_task:
            self.current_task.cancel()
        await bot.send_message(admin_chat_id, "🛑 Xabar tarqatish to'xtatildi!")

    async def _broadcast_worker(self, admin_chat_id: int):
        logger.info("Ommaviy xabar yuborish boshlandi...")

        async with AsyncSessionLocal() as session:
            # Faqat hali xabar olmagan (message_sent == False) mijozlarni olish
            stmt = select(Lead).where(
                Lead.message_sent == False,
                Lead.status != "rejected"
            ).order_by(Lead.id.asc())
            result = await session.execute(stmt)
            leads = result.scalars().all()

        total = len(leads)
        if total == 0:
            self.is_broadcasting = False
            await bot.send_message(admin_chat_id, "ℹ️ Xabar yuborish uchun yangi mijozlar topilmadi (barchasiga allaqachon yuborilgan).")
            return

        progress_msg = await bot.send_message(
            admin_chat_id,
            f"🚀 <b>Ommaviy xabar yuborish boshlandi!</b>\n\n"
            f"👥 Jami qabul qiluvchilar: <b>{total} ta</b>\n"
            f"⏱ Xavfsiz oraliq: har bir xabar orasida <b>35 soniya</b>\n\n"
            f"<i>Jarayonni to'xtatish uchun /stop_send buyrug'ini yuboring.</i>"
        )

        sent_count = 0
        failed_count = 0

        for index, lead in enumerate(leads, 1):
            if not self.is_broadcasting:
                break

            # Qabul qiluvchi identifikatori (Telegram username, Telegram ID yoki telefon raqam)
            recipient = None
            if lead.telegram_username:
                recipient = f"@{lead.telegram_username.replace('@', '').strip()}"
            elif lead.telegram_id:
                recipient = lead.telegram_id
            elif lead.phone_number and lead.phone_number != "Ko'rsatilmagan":
                recipient = lead.phone_number

            if not recipient:
                # Na telegram, na telefon bor
                failed_count += 1
                continue

            # Xabar matni
            message_text = settings.AUTO_MESSAGE_TEMPLATE

            logger.info(f"[{index}/{total}] Xabar yuborilmoqda: {lead.full_name} ({recipient})")
            success = await userbot_service.send_direct_message(recipient, message_text)

            async with AsyncSessionLocal() as session:
                lead_to_update = await session.get(Lead, lead.id)
                if lead_to_update:
                    if success:
                        lead_to_update.message_sent = True
                        lead_to_update.status = "sent"
                        update_lead_in_excel(lead.id, message_sent=True, status="sent")
                        sent_count += 1
                    else:
                        lead_to_update.status = "failed"
                        update_lead_in_excel(lead.id, message_sent=False, status="failed")
                        failed_count += 1
                    await session.commit()

            # Har 5 ta mijozda adminga hisobot yangilab turish
            if index % 5 == 0 or index == total:
                try:
                    await progress_msg.edit_text(
                        f"📊 <b>Xabar yuborish jarayoni:</b>\n\n"
                        f"🔹 Jarayon: <b>{index}/{total}</b>\n"
                        f"✅ Muvaffaqiyatli yuborildi: <b>{sent_count} ta</b>\n"
                        f"⚠️ Yuborib bo'lmadi: <b>{failed_count} ta</b>\n\n"
                        f"<i>Keyingi xabar 35 soniyadan so'ng...</i>"
                    )
                except Exception:
                    pass

            # Telegram bloklamasligi uchun xavfsiz 35 soniya tanaffus
            if index < total and self.is_broadcasting:
                await asyncio.sleep(35)

        self.is_broadcasting = False
        await bot.send_message(
            admin_chat_id,
            f"🎉 <b>Xabar yuborish yakunlandi!</b>\n\n"
            f"✅ Muvaffaqiyatli ketdi: <b>{sent_count} ta</b>\n"
            f"⚠️ Yuborib bo'lmadi: <b>{failed_count} ta</b>\n"
            f"📑 Barcha natijalar Excelda aks etdi (/excel)."
        )

broadcast_service = BroadcastService()

