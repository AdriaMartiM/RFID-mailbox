# app/models/ticket.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True)  # Ej: INC-A4B2
    empresa = Column(String, nullable=False)
    localizacion = Column(String)
    telefono = Column(String)
    descripcion = Column(Text)
    outlook_conversation_id = Column(String, unique=True, index=True)  # ID del hilo de Outlook
    estado = Column(String, default="PROCESADO")  # PROCESADO, EN_PROGRESO, CERRADO
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación uno-a-muchos con los mensajes del chat
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")