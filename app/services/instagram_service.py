import os
import asyncio
import logging
import time
from typing import Optional, List, Dict
from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Lead
from app.services.parser_service import extract_phone_and_telegram, clean_phone_number
from app.services.lead_service import process_new_lead
from app.schemas import LeadCreate

logger = logging.getLogger(__name__)

class InstagramWatcherService:
    def __init__(self):
        self.username = settings.INSTAGRAM_USERNAME
        self.password = settings.INSTAGRAM_PASSWORD
        self.session_file = settings.INSTAGRAM_SESSION_FILE
        self.cl = None
        self._is_logged_in = False
        self._running = False

    def login_sync(self) -> bool:
        """Instagram hisobiga kirish va sessiyani saqlash (sinxron)"""
        if not self.username:
            logger.warning("INSTAGRAM_USERNAME sozlanmagan.")
            return False

        try:
            from instagrapi import Client
            self.cl = Client()
            self.cl.delay_range = [1, 2]

            # Sessiya fayli mavjud bo'lsa, undan yuklash
            if os.path.exists(self.session_file):
                try:
                    self.cl.load_settings(self.session_file)
                    self.cl.login(self.username, self.password)
                    logger.info(f"Instagram: Sessiya orqali muvaffaqiyatli ulandi! (@{self.username})")
                    self._is_logged_in = True
                    return True
                except Exception as e:
                    logger.warning(f"Eski sessiya bilan kirib bo'lmadi: {e}. Yangi login amalga oshirilmoqda...")

            if not self.password:
                logger.error("INSTAGRAM_PASSWORD ko'rsatilmagan!")
                return False

            self.cl.login(self.username, self.password)
            self.cl.dump_settings(self.session_file)
            logger.info(f"Instagram: Yangi sessiya saqlandi va ulandi! (@{self.username})")
            self._is_logged_in = True
            return True
        except Exception as e:
            logger.error(f"Instagramga kirishda xatolik: {e}")
            self._is_logged_in = False
            return False

    async def initialize(self):
        """Asinxron inisializatsiya"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.login_sync)

    def _fetch_threads(self, amount: int = 10):
        """Direct suhbatlarni yuklash"""
        if not self._is_logged_in or not self.cl:
            return []
        try:
            return self.cl.direct_threads(amount=amount)
        except Exception as e:
            logger.error(f"Direct suhbatlarni olishda xatolik: {e}")
            return []

    def _get_user_info_sync(self, user_pk: int):
        """Profil ma'lumotlarini yuklash"""
        try:
            return self.cl.user_info(user_pk)
        except Exception as e:
            logger.debug(f"User info olishda ogohlantirish ({user_pk}): {e}")
            return None

    async def scan_and_process(self, amount: int = 10) -> int:
        """
        Direct chatlarni skanerlash va har bir topilgan mijozni DARHOL (real-time) qayta ishlash.
        """
        if not self._is_logged_in or not self.cl:
            return 0

        loop = asyncio.get_event_loop()
        threads = await loop.run_in_executor(None, self._fetch_threads, amount)

        if not threads:
            return 0

        my_pk = str(self.cl.user_id)
        new_leads_count = 0

        for thread in threads:
            # O'zimizdan boshqa suhbatdoshni topish
            target_user = None
            for user in thread.users:
                if str(user.pk) != my_pk:
                    target_user = user
                    break

            if not target_user:
                continue

            user_pk = str(target_user.pk)
            username = target_user.username
            full_name = target_user.full_name or username

            # 1. Tezkor tekshirish: Bu mijoz allaqachon bazada bormi?
            async with AsyncSessionLocal() as session:
                stmt = select(Lead).where(
                    (Lead.instagram_pk == user_pk) |
                    (Lead.instagram_username == username)
                )
                existing = (await session.execute(stmt)).scalar_one_or_none()

            # Agar allaqachon bazada bo'lsa, uning profilini yuklab vaqt sarflamaymiz!
            if existing:
                continue

            logger.info(f"🔍 Yangi suhbatdosh tekshirilmoqda: @{username}")

            # Chatdagi xabarlar matnini yig'ish
            chat_texts = []
            for msg in thread.messages[:10]:
                if msg.text:
                    chat_texts.append(msg.text)
            combined_chat_text = "\n".join(chat_texts)

            # Profil ma'lumotlarini olish (Bio, linklar)
            user_info = await loop.run_in_executor(None, self._get_user_info_sync, target_user.pk)
            bio = ""
            external_url = ""
            public_phone = None

            if user_info:
                bio = getattr(user_info, "biography", "") or ""
                external_url = getattr(user_info, "external_url", "") or ""
                if hasattr(user_info, "contact_phone_number") and user_info.contact_phone_number:
                    public_phone = str(user_info.contact_phone_number)
                elif hasattr(user_info, "public_phone_number") and user_info.public_phone_number:
                    public_phone = str(user_info.public_phone_number)

            all_text = f"{bio}\n{combined_chat_text}"
            parsed_phone, parsed_tg = extract_phone_and_telegram(all_text, external_url)
            phone = public_phone or parsed_phone

            # Agar telefon yoki telegram topilsa — DARHOL bazaga va adminga yuboramiz!
            if phone or parsed_tg:
                clean_phone = clean_phone_number(phone) if phone else "Ko'rsatilmagan"

                async with AsyncSessionLocal() as session:
                    lead_in = LeadCreate(
                        full_name=full_name,
                        instagram_username=username,
                        phone_number=clean_phone
                    )
                    created_lead = await process_new_lead(lead_in, session)
                    created_lead.instagram_pk = user_pk
                    if parsed_tg:
                        created_lead.telegram_username = parsed_tg
                        created_lead.telegram_found = True
                    await session.commit()
                    new_leads_count += 1

                logger.info(f"🔥 DARHOL QAYTA ISHLANDI: @{username} (Tel: {clean_phone}, TG: {parsed_tg})")

        return new_leads_count

    async def start_polling(self):
        """Direct xabarlarni doimiy kuzatib boruvchi tezkor fon sikli (har 15 soniyada eng so'nggi chatlar)"""
        if not self._is_logged_in:
            logger.warning("Instagramga kirmaganligi sababli kuzatuvchi boshlanmadi.")
            return

        self._running = True
        logger.info("Instagram Direct tezkor kuzatuvchi ishga tushdi (Har 15 soniyada eng yangi suhbatlar).")

        while self._running:
            try:
                # Yangi suhbatlarni tezkor ushlash uchun oxirgi 10 ta suhbat yetarli
                await self.scan_and_process(amount=10)
            except Exception as e:
                logger.error(f"Kuzatuv siklida xatolik: {e}")

            await asyncio.sleep(15)

    def stop(self):
        self._running = False

instagram_watcher = InstagramWatcherService()
