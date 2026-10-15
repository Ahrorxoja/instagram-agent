from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Supabase yoki boshqa Postgres URL'larini SQLAlchemy asyncpg formatiga o'tkazish
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Supabase connection pooler uchun asyncpg parametrlarini sozlash
connect_args = {}
if "postgresql+asyncpg" in db_url:
    # Supabase Transaction pooler (port 6543) bilan ishlaganda prepared statementlarni o'chirish tavsiya etiladi
    connect_args = {
        "statement_cache_size": 0
    }

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    """FastAPI dependency for database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Jadvallarni yaratish (agar mavjud bo'lmasa)"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Ma'lumotlar bazasi jadvallari muvaffaqiyatli tekshirildi/yaratildi.")
    except Exception as e:
        logger.error(f"Bazani ishga tushirishda xatolik: {e}")
        raise

