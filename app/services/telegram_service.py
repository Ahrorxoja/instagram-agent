import asyncio
import logging
import random
from typing import Optional, Tuple
from telethon import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest, ResolvePhoneRequest
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

    async def get_target_entity(self, recipient: str | int, name: str = "Lead"):
        """
        Qabul qiluvchini (username, ID yoki telefon raqami) Telegram entity ob'yektiga aylantirish.
        Telefon raqamlar uchun:
        1. ResolvePhoneRequest (Saved Messages'da raqam bosilgandek to'g'ridan-to'g'ri qidiruv)
        2. ImportContactsRequest (Vaqtincha kontakt orqali maxfiy profillarni ochish)
        """
        if not self._is_ready or not self.client:
            return None

        recipient_str = str(recipient).strip()

        # 1. Agar @username yoki Telegram user ID bo'lsa
        if recipient_str.startswith("@") or (recipient_str.lstrip("-").isdigit() and len(recipient_str) < 12 and not recipient_str.startswith("998")):
            try:
                entity = await self.client.get_input_entity(recipient)
                return entity
            except Exception as e:
                logger.warning(f"Username/ID orqali entity topilmadi ({recipient}): {e}")

        # 2. Agar telefon raqam bo'lsa
        clean_phone = recipient_str.replace("+", "").replace(" ", "").replace("-", "").strip()
        if clean_phone.isdigit() and len(clean_phone) >= 7:
            # 1-usul: ResolvePhoneRequest (Telegram ilovasida xuddi Saved Messages'da bosilgandek)
            for phone_fmt in [f"+{clean_phone}", clean_phone]:
                try:
                    res = await self.client(ResolvePhoneRequest(phone=phone_fmt))
                    if res.users:
                        user = res.users[0]
                        logger.info(f"Raqam ResolvePhone orqali topildi: {clean_phone} -> ID={user.id}, @{user.username}")
                        return user
                except Exception:
                    pass

            # 2-usul: ImportContactsRequest (Agar foydalanuvchi maxfiylikni 'Faqat kontaktlar' qilib qo'ygan bo'lsa)
            try:
                cid = random.randint(1000000, 9999999)
                contact = InputPhoneContact(client_id=cid, phone=clean_phone, first_name=name[:15] if name else "Lead", last_name="")
                res = await self.client(ImportContactsRequest([contact]))
                if res.users:
                    user = res.users[0]
                    logger.info(f"Raqam Kontakt orqali topildi: {clean_phone} -> ID={user.id}, @{user.username}")
                    try:
                        await self.client(DeleteContactsRequest(id=[user.id]))
                    except Exception:
                        pass
                    return user
            except Exception as e:
                logger.error(f"Kontakt orqali qidirishda xatolik ({clean_phone}): {e}")

        # 3. Zaxira usul: get_input_entity
        try:
            return await self.client.get_input_entity(recipient)
        except Exception as e:
            logger.warning(f"Entity topilmadi ({recipient}): {e}")
            return None

    async def check_phone_number(self, phone: str, name: str = "Lead") -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Telefon raqam Telegramda ro'yxatdan o'tganligini tekshirish.
        Qaytaradi: (topildimi: bool, telegram_id: Optional[int], telegram_username: Optional[str])
        """
        if not self._is_ready or not self.client:
            logger.warning("Telethon faol emas. Raqam Telegramda tekshirilmadi.")
            return False, None, None

        entity = await self.get_target_entity(phone, name=name)
        if entity:
            user_id = getattr(entity, "id", None)
            username = getattr(entity, "username", None)
            logger.info(f"Raqam {phone} Telegramda mavjud: ID={user_id}, @{username}")
            return True, user_id, username
        else:
            logger.info(f"Raqam {phone} Telegramda topilmadi.")
            return False, None, None

    async def send_direct_message(self, recipient: str | int, text: str, name: str = "Lead") -> bool:
        """
        Telegram foydalanuvchisiga (ID, username yoki telefon raqam) to'g'ridan-to'g'ri xabar yuborish.
        Raqam bo'lsa avval uni Telegram tarmog'idan to'liq qidirib topadi, so'ng xabar jo'natadi.
        """
        if not self._is_ready or not self.client:
            logger.error("Telethon faol emas! Xabar yuborib bo'lmadi.")
            return False

        entity = await self.get_target_entity(recipient, name=name)
        if not entity:
            logger.warning(f"Telegramda qabul qiluvchi topilmadi yoki raqamda Telegram yo'q: {recipient}")
            return False

        try:
            await self.client.send_message(entity, text)
            logger.info(f"Xabar muvaffaqiyatli yuborildi: {recipient}")
            return True
        except Exception as e:
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

