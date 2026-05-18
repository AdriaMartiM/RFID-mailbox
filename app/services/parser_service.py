# app/services/parser_service.py
import re
from typing import Dict

class ParserService:
    @staticmethod
    def parse_outlook_email(body: str) -> Dict[str, str]:
        """
        Analiza el correo extrayendo campos clave sin importar la empresa de la cabecera.
        """
        # Detecta cualquier emoji + NOMBRE EMPRESA – INCIDENCIA RFID
        empresa_match = re.search(r"🔵\s*([^-–]+)\s*[-–]\s*INCIDENCIA", body, re.IGNORECASE)
        empresa = empresa_match.group(1).strip() if empresa_match else "Desconocida"

        localizacion = re.search(r"Localización de la tienda:\s*(.*)", body, re.IGNORECASE)
        telefono = re.search(r"Teléfono de contacto:\s*(.*)", body, re.IGNORECASE)
        
        # Extrae la descripción deteniéndose antes de llegar a la sección de fotos/vídeos
        descripcion = re.search(r"Descripción del problema:\s*([\s\S]*?)(?=Foto o vídeo|$)", body, re.IGNORECASE)

        return {
            "empresa": empresa,
            "localizacion": localizacion.group(1).strip() if localizacion else "No aportado",
            "telefono": telefono.group(1).strip() if telefono else "No aportado",
            "descripcion": descripcion.group(1).strip() if descripcion else "Sin descripción"
        }