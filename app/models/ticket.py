# app/models/ticket.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
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
    resumen = Column(String, default="")              # descripción breve a mano (sale en la tarjeta)
    descripcion = Column(Text)                         # editable a mano (no afecta al hilo)
    cuerpo_inicial = Column(Text, nullable=True)       # correo inicial ORIGINAL (inmutable; es lo que se ve en el hilo)
    outlook_conversation_id = Column(String, unique=True, index=True)  # ID del hilo de Outlook
    estado = Column(String, default="PROCESADO")  # PROCESADO, EN_PROGRESO, CERRADO
    created_at = Column(DateTime, default=datetime.utcnow)  # Cuándo llegó (orden de llegada)
    # Se actualiza al cambiar de estado: nos da la fecha de cierre para filtrar las cerradas
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Datos del flujo de trabajo (se rellenan a mano en la app) ---
    hora_llegada = Column(DateTime, nullable=True)   # cuándo se empieza a atender (paso a En progreso)
    hora_cierre = Column(DateTime, nullable=True)     # cuándo se cierra del todo
    solucion = Column(Text, nullable=True)            # explicación de cómo se resolvió (obligatoria al cerrar)
    proximo_paso = Column(Text, nullable=True)        # qué hay que hacer a continuación (next step)

    # --- Avisos de novedad ---
    nuevo_mensaje = Column(Boolean, default=False)    # True si llegó un correo nuevo al hilo sin leer
    email_inicial_id = Column(String, nullable=True)  # id del correo de Outlook que originó la incidencia

    # Relación uno-a-muchos con los mensajes del chat
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")