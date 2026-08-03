# app/models/conocimiento.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Carpeta(Base):
    """Una carpeta de la biblioteca para organizar los items."""
    __tablename__ = "carpetas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Conocimiento(Base):
    """Una PREGUNTA frecuente de la Biblioteca (Q&A):
       - titulo    = la pregunta
       - contenido = la respuesta (texto)
       - carpeta_id = el TEMA al que pertenece (Impresoras RFID, PDA…)
       Además puede tener fotos/vídeos adjuntos (tabla Media).
    """
    __tablename__ = "conocimiento"

    id = Column(Integer, primary_key=True, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id"), nullable=True)
    tipo = Column(String, default="pregunta")
    orden = Column(Integer, default=0)                # orden manual dentro del tema
    titulo = Column(String, nullable=False)           # la pregunta
    categoria = Column(String, default="General")     # compatibilidad
    etiquetas = Column(String, default="")
    contenido = Column(Text, default="")              # la respuesta
    url = Column(String, default="")
    archivo_nombre = Column(String, default="")
    archivo_ruta = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    media = relationship("Media", back_populates="pregunta", cascade="all, delete-orphan")


class Media(Base):
    """Una foto o vídeo adjunto a una pregunta."""
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("conocimiento.id"))
    tipo = Column(String, default="imagen")           # imagen | video | enlace_video
    archivo_nombre = Column(String, default="")
    archivo_ruta = Column(String, default="")
    url = Column(String, default="")                  # para enlace_video (YouTube, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)

    pregunta = relationship("Conocimiento", back_populates="media")
