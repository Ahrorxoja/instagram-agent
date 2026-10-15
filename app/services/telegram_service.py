import asyncio
import logging
from typing import Optional, Tuple
from telethon import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from app.config import settings

logger = logging.getLogger(__name__)

class TelegramUserbotService:
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.phone = settings.TELEGRAM_PHONE
        self.client: Optional[TelegramClient] = None
        self._is_ready = False

    async def initialize(self):
        """Telethon clientini ishga tushirish"""
        if not self.api_id or not self.api_hash:
            logger.warning("TELEGRAM_API_ID yoki TELEGRAM_API_HASH sozlanmagan. Userbot xizmati nofaol bo'ladi.")
            return

        try:
            self.client = TelegramClient("userbot_session", self.api_id, self.api_hash)
            await self.client.connect()

            if not await self.client.is_user_authorized():
                logger.warning(
                    "Telethon sessiyasi avtorizatsiyadan o'tmagan! "
                    "Iltimos, avval `python -m app.services.telegram_service` buyrug'i orqali sessiyaga kiring."
                )
                self._is_ready = False
            else:
                self._is_ready = True
                me = await self.client.get_me()
                logger.info(f"Telethon muvaffaqiyatli ulandi! Akkaunt: {me.first_name} (@{me.username})")
        except Exception as e:
            logger.error(f"Telethonni ishga tushirishda xatolik: {e}")
            self._is_ready = False

    async def check_phone_number(self, phone: str, name: str = "Lead") -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Telefon raqam Telegramda ro'yxatdan o'tganligini tekshirish.
        Qaytaradi: (topildimi: bool, telegram_id: Optional[int], telegram_username: Optional[str])
        """
        if not self._is_ready or not self.client:
            logger.warning("Telethon faol emas. Raqam Telegramda tekshirilmadi.")
            return False, None, None

        clean_phone = phone.replace("+", "").strip()
        contact = InputPhoneContact(client_id=0, phone=clean_phone, first_name=name, last_name="")

        try:
            result = await self.client(ImportContactsRequest([contact]))
            if result.users:
                user = result.users[0]
                user_id = user.id
                username = user.username
                logger.info(f"Raqam {phone} Telegramda topildi: ID={user_id}, username=@{username}")

                # Kontaktlar ro'yxatini to'ldirmaslik uchun o'chirib tashlaymiz
                try:
                    await self.client(DeleteContactsRequest(id=[user_id]))
                except Exception:
                    pass

                return True, user_id, username
            else:
                logger.info(f"Raqam {phone} Telegramda topilmadi.")
                return False, None, None
        except Exception as e:
            logger.error(f"Raqamni tekshirishda xatolik yuz berdi ({phone}): {e}")
            return False, None, None

    async def send_direct_message(self, recipient: str | int, text: str, name: str = "Lead") -> bool:
        """
        Telegram foydalanuvchisiga (ID, username yoki telefon raqam) to'g'ridan-to'g'ri xabar yuborish.
        Agar raqam bo'lsa va to'g'ridan-to'g'ri topilmasa, avtomatik ravishda kontakt sifatida tekshirib yuboradi.
        """
        if not self._is_ready or not self.client:
            logger.error("Telethon faol emas! Xabar yuborib bo'lmadi.")
            return False

        try:
            await self.client.send_message(recipient, text)
            logger.info(f"Xabar muvaffaqiyatli yuborildi: {recipient}")
            return True
        except Exception as e:
            # Agar raqam bo'lsa, kontakt sifatida qo'shib urinib ko'ramiz
            recipient_str = str(recipient).strip()
            if recipient_str.startswith("+") or (recipient_str.isdigit() and len(recipient_str) > 7):
                try:
                    clean_phone = recipient_str.replace("+", "").replace(" ", "").replace("-", "").strip()
                    contact = InputPhoneContact(client_id=0, phone=clean_phone, first_name=name[:15] if name else "Lead", last_name="")
                    result = await self.client(ImportContactsRequest([contact]))
                    if result.users:
                        user = result.users[0]
                        await self.client.send_message(user, text)
                        logger.info(f"Xabar kontakt orqali muvaffaqiyatli yuborildi: {recipient} (ID: {user.id})")
                        try:
                            await self.client(DeleteContactsRequest(id=[user.id]))
                        except Exception:
                            pass
                        return True
                    else:
                        logger.warning(f"Raqam {recipient} Telegramda ro'yxatdan o'tmagan.")
                        return False
                except Exception as import_err:
                    logger.error(f"Kontakt orqali yuborishda xatolik ({recipient}): {import_err}")
                    return False

            logger.error(f"Xabar yuborishda xatolik ({recipient}): {e}")
            return False

    async def disconnect(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()

# Singleton nusxa
userbot_service = TelegramUserbotService()

# Alohida ishga tushirilganda sessiyani avtorizatsiya qilish uchun skript
if __name__ == "__main__":
    async def auth_session():
        print("--- Telegram Userbot Avtorizatsiyasi ---")
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            print("Xatolik: .env faylida TELEGRAM_API_ID va TELEGRAM_API_HASH kiritilishi kerak!")
            return
        client = TelegramClient("userbot_session", settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
        await client.start(phone=settings.TELEGRAM_PHONE)
        me = await client.get_me()
        print(f"Muvaffaqiyatli kirdingiz: {me.first_name} (@{me.username})")
        await client.disconnect()

    asyncio.run(auth_session())

