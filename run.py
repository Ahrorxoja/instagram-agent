import asyncio
import logging
import uvicorn
from app.config import settings
from app.bot.bot import bot, dp
from app.bot.handlers import router
from app.main import app
from app.services.instagram_service import instagram_watcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

async def start_fastapi():
    """FastAPI serverini ishga tushirish"""
    config = uvicorn.Config(
        app=app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def start_bot():
    """Telegram Bot pollingni ishga tushirish"""
    if not settings.BOT_TOKEN:
        logger.warning("BOT_TOKEN ko'rsatilmagan! Bot ishga tushmadi.")
        return

    dp.include_router(router)
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="send_all", description="🚀 Barcha mijozlarga xabar yuborish"),
        BotCommand(command="scan", description="🔍 Direct chatlarni skanerlash"),
        BotCommand(command="excel", description="📑 Excel faylni yuklab olish"),
        BotCommand(command="stats", description="📊 Statistika"),
        BotCommand(command="stop_send", description="🛑 Yuborishni to'xtatish"),
        BotCommand(command="help", description="ℹ️ Qo'llanma"),
    ])
    logger.info("Telegram Bot menyu buyruqlari o'rnatildi.")
    logger.info("Telegram Bot polling ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def start_instagram():
    """Instagram Direct kuzatuvchi xizmatini ishga tushirish"""
    if not settings.INSTAGRAM_USERNAME:
        logger.info("INSTAGRAM_USERNAME ko'rsatilmagan, Instagram kuzatuvi o'tkazib yuborildi.")
        return

    logger.info("Instagram hisobiga ulanish tekshirilmoqda...")
    await instagram_watcher.initialize()
    if instagram_watcher._is_logged_in:
        await instagram_watcher.start_polling()
    else:
        logger.warning("Instagramga ulanib bo'lmadi. Direct kuzatuvi faollashtirilmadi.")

async def main():
    logger.info("Tizim ishga tushirilmoqda (FastAPI + Telegram Bot + Instagram Watcher)...")
    await asyncio.gather(
        start_fastapi(),
        start_bot(),
        start_instagram()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        instagram_watcher.stop()
        logger.info("Tizim to'xtatildi.")
