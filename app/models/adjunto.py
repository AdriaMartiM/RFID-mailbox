# app/models/adjunto.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class Adjunto(Base):
    """Un adjunto de un correo (imagen o documento) guardado en la app.
    Se enlaza al ticket y, opcionalmente, al mensaje del hilo del que vino
    (si message_id_fk es None, vino con el correo inicial / la descripción)."""
    __tablename__ = "adjuntos"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id_fk = Column(Integer, ForeignKey("tickets.id"))
    message_id_fk = Column(Integer, ForeignKey("messages.id"), nullable=True)
    tipo = Column(String, default="documento")   # imagen | documento
    nombre = Column(String, default="")
    ruta = Column(String, default="")
    tamano = Column(Integer, default=0)           # bytes
    created_at = Column(DateTime, default=datetime.utcnow)
