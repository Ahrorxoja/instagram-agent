from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, func
from app.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    instagram_username = Column(String(255), nullable=True)
    instagram_pk = Column(String(100), nullable=True, index=True)  # Instagram foydalanuvchi ID raqami
    phone_number = Column(String(50), nullable=False, index=True)
    
    # Telegram ma'lumotlari (Telethon orqali topilganda)
    telegram_id = Column(BigInteger, nullable=True, index=True)
    telegram_username = Column(String(255), nullable=True)
    telegram_found = Column(Boolean, default=False)
    
    # Xabar va qo'ng'iroq holati
    message_sent = Column(Boolean, default=False)
    phone_called = Column(Boolean, default=False)  # Telefon qilinganmi
    notes = Column(String(500), nullable=True)     # Qo'shimcha izohlar
    status = Column(String(50), default="pending")  # pending, sent, rejected, not_found, failed
    
    # Vaqtlar
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "instagram_username": self.instagram_username,
            "phone_number": self.phone_number,
            "telegram_id": self.telegram_id,
            "telegram_username": self.telegram_username,
            "telegram_found": self.telegram_found,
            "message_sent": self.message_sent,
            "phone_called": self.phone_called,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

