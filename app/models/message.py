# app/models/message.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id_fk = Column(Integer, ForeignKey("tickets.id"))
    remitente = Column(String)
    contenido = Column(Text)
    fecha_envio = Column(DateTime, default=datetime.utcnow)
    outlook_message_id = Column(String, nullable=True)  # id del correo en Outlook (para no duplicar)

    ticket = relationship("Ticket", back_populates="messages")