# app/models/recordatorio.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from app.database import Base


class Recordatorio(Base):
    """Una incidencia/nota MANUAL que NO llega por correo.
    Es independiente de los tickets: solo sirve como recordatorio.
    """
    __tablename__ = "recordatorios"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)        # texto principal del recordatorio
    detalle = Column(Text, default="")             # notas extra (opcional)
    empresa = Column(String, default="")           # marca/tienda relacionada (opcional)
    prioridad = Column(String, default="normal")   # baja | normal | alta
    hecho = Column(Boolean, default=False)         # marcado como resuelto
    created_at = Column(DateTime, default=datetime.utcnow)
