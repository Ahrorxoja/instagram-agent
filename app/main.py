import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import init_db, get_db
from app.models import Lead
from app.schemas import LeadCreate, LeadResponse
from app.services.lead_service import process_new_lead
from app.services.telegram_service import userbot_service
from app.services.excel_service import ensure_excel_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dastur ishga tushganda
    logger.info("Server ishga tushmoqda...")
    await init_db()
    ensure_excel_file()
    await userbot_service.initialize()
    yield
    # Dastur to'xtaganda
    logger.info("Server to'xtatilmoqda...")
    await userbot_service.disconnect()

app = FastAPI(
    title="Instagram & Telegram Lead Automation API",
    description="Instagramdan mijozlar ma'lumotlarini yig'ish, bazaga va Excelga saqlash hamda Telegram orqali xabar yuborish tizimi",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Status"])
async def health_check():
    return {
        "status": "ok",
        "userbot_ready": userbot_service._is_ready,
        "database": "connected"
    }

@app.post("/api/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED, tags=["Leads"])
async def create_lead(
    lead_in: LeadCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Yangi mijoz ma'lumotlarini qabul qilish:
    - Baza (Supabase/PostgreSQL)ga saqlaydi
    - Telegramda telefon raqamni tekshiradi
    - Excel faylga qo'shadi
    - Telegram bot orqali adminga xabar va inline tugma chiqaradi
    """
    try:
        created_lead = await process_new_lead(lead_in, db)
        return created_lead
    except Exception as e:
        logger.error(f"Lead qabul qilishda xatolik: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/webhook/instagram", tags=["Webhooks"])
async def verify_instagram_webhook(request: Request):
    """
    Meta (Facebook/Instagram) Webhook tekshiruvi (hub.challenge / hub.verify_token)
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = getattr(settings, "INSTAGRAM_VERIFY_TOKEN", "stolda_webhook_secret_2026")

    if mode == "subscribe" and token == verify_token:
        logger.info("Meta Webhook muvaffaqiyatli tasdiqlandi!")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=challenge, status_code=200)

    logger.warning(f"Meta Webhook tasdiqlashda xato: mode={mode}, token={token}")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook/instagram", tags=["Webhooks"])
async def instagram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Instagram Direct / Meta Webhook / ManyChat / Make / Zapier webhooklarini qabul qilish.
    """
    try:
        body = await request.json()
        logger.info(f"Webhook ma'lumot qabul qilindi: {body}")

        # 1. Meta rasmiy formati: {"object": "instagram", "entry": [...]}
        if body.get("object") == "instagram":
            for entry in body.get("entry", []):
                for messaging in entry.get("messaging", []):
                    sender_id = messaging.get("sender", {}).get("id")
                    message = messaging.get("message", {})
                    msg_text = message.get("text", "")
                    
                    if msg_text:
                        from app.services.parser_service import extract_phone_and_telegram, clean_phone_number
                        parsed_phone, parsed_tg = extract_phone_and_telegram(msg_text)
                        clean_phone = clean_phone_number(parsed_phone) if parsed_phone else "Ko'rsatilmagan"

                        lead_data = LeadCreate(
                            full_name=f"Instagram User {sender_id}",
                            instagram_username=str(sender_id),
                            phone_number=clean_phone
                        )
                        created_lead = await process_new_lead(lead_data, db)
                        created_lead.instagram_pk = str(sender_id)
                        if parsed_tg:
                            created_lead.telegram_username = parsed_tg
                        await db.commit()
            return {"status": "ok"}

        # 2. ManyChat / Make / oddiy JSON formati
        full_name = (
            body.get("full_name") or
            body.get("name") or
            body.get("first_name", "") + " " + body.get("last_name", "")
        ).strip() or "Instagram Mijoz"

        instagram_username = (
            body.get("instagram_username") or
            body.get("username") or
            body.get("ig_username") or
            body.get("instagram")
        )

        phone_number = (
            body.get("phone_number") or
            body.get("phone") or
            body.get("contact_phone")
        )

        if not phone_number:
            return JSONResponse(
                status_code=400,
                content={"error": "Telefon raqam (phone_number) topilmadi"}
            )

        lead_data = LeadCreate(
            full_name=full_name,
            instagram_username=instagram_username,
            phone_number=str(phone_number)
        )

        created_lead = await process_new_lead(lead_data, db)
        return {
            "success": True,
            "lead_id": created_lead.id,
            "status": created_lead.status,
            "telegram_found": created_lead.telegram_found
        }
    except Exception as e:
        logger.error(f"Webhook qayta ishlashda xatolik: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/leads", response_model=List[LeadResponse], tags=["Leads"])
async def get_all_leads(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Barcha mijozlar ro'yxatini olish"""
    result = await db.execute(
        select(Lead).order_by(Lead.id.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()

@app.get("/api/leads/export-excel", tags=["Leads"])
async def export_leads_excel():
    """Yig'ilgan mijozlar Excel faylini (.xlsx) yuklab olish"""
    file_path = settings.EXCEL_FILE_PATH
    if not os.path.exists(file_path):
        ensure_excel_file()

    return FileResponse(
        path=file_path,
        filename="instagram_mijozlar.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

