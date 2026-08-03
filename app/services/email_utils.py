# app/services/email_utils.py
# Utilidades para convertir el cuerpo de un correo (normalmente HTML de Outlook)
# en texto legible: con saltos de línea, sin etiquetas, y recortando el hilo
# citado y las firmas para quedarnos solo con el mensaje nuevo.
import re
import html as _html

# Marcadores que indican el inicio del HILO CITADO o de una FIRMA boilerplate.
# A partir del primero que aparezca, recortamos (es "ruido" repetido).
_MARCADORES_CORTE = [
    r"_{5,}",                                 # ___________ (separador de firma)
    r"-{2,}\s*Original Message\s*-{2,}",      # -----Original Message-----
    r"\bDe:\s.+?\bEnviado:",                  # cabecera Outlook ES (De:/Enviado:)
    r"\bFrom:\s.+?\bSent:",                   # cabecera Outlook EN (From:/Sent:)
    r"\bDe:\s.+?\bPara:",                     # cabecera Outlook ES (De:/Para:)
    r"El\s.{0,80}?\bescribió:",               # "El <fecha> ... escribió:"
    r"On\s.{0,90}?\bwrote:",                  # "On <date> ... wrote:"
    r"\bEnviado el:\s",
    # Avisos legales / confidencialidad (boilerplate que ensucia el mensaje)
    r"Este (mensaje|correo|e-?mail) y (sus|los) (archivos )?adjuntos",
    r"La informaci[oó]n contenida en este (mensaje|correo)",
    r"This (e-?mail|message) and any (attachments|files)",
    r"AVISO (DE|LEGAL|DE CONFIDENCIALIDAD)",
    r"\bSíguenos en\b",
]


def html_a_texto(cuerpo: str, es_html: bool = True) -> str:
    """Convierte HTML en texto plano legible (conservando saltos de línea)."""
    if not cuerpo:
        return ""
    t = cuerpo
    if es_html:
        # Fuera bloques que no son contenido
        t = re.sub(r"(?is)<(script|style|head|title)[^>]*>.*?</\1>", "", t)
        # Saltos de línea donde tocan
        t = re.sub(r"(?i)<br\s*/?>", "\n", t)
        t = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table|blockquote)>", "\n", t)
        # Quitamos el resto de etiquetas
        t = re.sub(r"(?s)<[^>]+>", "", t)
        t = _html.unescape(t)
    # Normalización de espacios
    t = t.replace("\xa0", " ").replace("​", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def recortar_citas(texto: str) -> str:
    """Recorta el hilo citado / firma: deja solo el mensaje nuevo (la parte de arriba)."""
    if not texto:
        return ""
    corte = len(texto)
    for patron in _MARCADORES_CORTE:
        m = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if m:
            corte = min(corte, m.start())
    limpio = texto[:corte].strip()
    # Si el recorte dejó algo demasiado corto, mejor devolver el texto completo
    return limpio if len(limpio) >= 15 else texto.strip()


def dividir_hilo(texto: str):
    """Separa el mensaje NUEVO (lo de arriba) del hilo citado/firma (lo de abajo).
    Devuelve (nuevo, citado); 'citado' puede ser cadena vacía."""
    if not texto:
        return "", ""
    corte = len(texto)
    for patron in _MARCADORES_CORTE:
        m = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if m:
            corte = min(corte, m.start())
    return texto[:corte].strip(), texto[corte:].strip()


# Líneas "Para:" / "To:" dentro del hilo citado (destinatarios del correo).
_RE_DESTINATARIO = re.compile(r"(?:^|\n)[ \t]*(?:Para|To)[ \t]*:[ \t]*(.+)", re.IGNORECASE)
# Nuestras propias direcciones: si el destinatario somos nosotros, no es un "reenvío a".
_ES_NOSOTROS = re.compile(r"rfid@|stcretail|sistema|software", re.IGNORECASE)


def extraer_destinatario(texto: str):
    """Saca el nombre del PRIMER destinatario real (que no seamos nosotros) de las
    líneas 'Para:'/'To:' del hilo citado. Devuelve None si no hay ninguno."""
    if not texto:
        return None
    for m in _RE_DESTINATARIO.finditer(texto):
        linea = m.group(1)
        # Si en la misma línea siguen otras cabeceras, cortamos ahí
        linea = re.split(r"\b(?:Asunto|Subject|Cc|CC|Enviado|Sent|De|From)\b[ \t]*:", linea)[0]
        for parte in re.split(r"[;,]", linea):        # cada destinatario de la línea
            parte = parte.strip()
            if not parte or _ES_NOSOTROS.search(parte):
                continue                              # nos saltamos nuestras direcciones
            nombre = re.sub(r"<[^>]*>", "", parte).strip().strip('"').strip()  # sin <email>
            if nombre:
                return nombre
    return None


def cuerpo_para_hilo(contenido: str, es_nuestro: bool = False):
    """Prepara un mensaje para mostrarlo en el hilo de la incidencia: deja solo el
    texto NUEVO (sin el hilo citado ni la firma) y, si es un correo NUESTRO
    reenviado/respondido, averigua a quién iba (línea 'Para:').
    Devuelve (texto_visible, reenviado_a)."""
    contenido = contenido or ""
    nuevo, citado = dividir_hilo(contenido)
    reenviado_a = extraer_destinatario(citado) if es_nuestro else None
    if not nuevo:
        # Correo sin texto nuevo (solo firma + hilo citado):
        #  - si es NUESTRO y sabemos el destinatario, lo dejamos vacío para que la
        #    vista muestre únicamente la línea "Reenviado a: X".
        #  - si no, no vaciamos un mensaje ajeno: mostramos su contenido tal cual.
        if not (es_nuestro and reenviado_a):
            nuevo = contenido.strip()
    return nuevo, reenviado_a


def cuerpo_legible(cuerpo: str, es_html: bool = True, recortar: bool = True) -> str:
    """Pipeline completo: HTML -> texto -> (opcional) recortar citas/firma."""
    texto = html_a_texto(cuerpo, es_html=es_html)
    if recortar:
        texto = recortar_citas(texto)
    return texto


# --- Filtrado de imágenes de FIRMA (logos de redes, banners) -----------------
_EXT_IMAGEN = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}

# Huellas (md5) de logos de firma corporativa conocidos que NO son fotos de
# incidencias y no deben aparecer en el hilo. El logo de STC es grande (2717x1550),
# así que las heurísticas de tamaño no lo pillan: lo bloqueamos por su huella exacta.
_LOGOS_FIRMA_MD5 = {
    "8cac196f2011293b0af2276e6e357ff1",  # logo STC (image.png, 152407 bytes)
}


def dimensiones_imagen(datos: bytes):
    """Devuelve (ancho, alto) leyendo solo la cabecera (PNG/JPEG/GIF). None si no se sabe."""
    import struct
    try:
        if datos[:8] == b"\x89PNG\r\n\x1a\n" and len(datos) >= 24:
            w, h = struct.unpack(">II", datos[16:24])
            return (w, h)
        if datos[:2] == b"\xff\xd8":  # JPEG
            i, n = 2, len(datos)
            while i < n - 1:
                if datos[i] != 0xFF:
                    i += 1
                    continue
                marker = datos[i + 1]
                i += 2
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    continue
                if i + 2 > n:
                    break
                seglen = struct.unpack(">H", datos[i:i + 2])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    if i + 7 <= n:
                        h, w = struct.unpack(">HH", datos[i + 3:i + 7])
                        return (w, h)
                    break
                i += seglen
        if datos[:6] in (b"GIF87a", b"GIF89a") and len(datos) >= 10:
            w, h = struct.unpack("<HH", datos[6:10])
            return (w, h)
    except Exception:
        pass
    return None


def es_imagen_de_firma(nombre: str, datos: bytes) -> bool:
    """¿Es un logo/icono/banner de firma (y NO una foto real de la incidencia)?"""
    ext = (nombre or "").lower().rsplit(".", 1)[-1]
    if ext not in _EXT_IMAGEN:
        return False  # no es imagen (documento) -> nunca se descarta aquí
    # Logos de firma conocidos (STC…): fuera aunque sean grandes
    import hashlib
    if hashlib.md5(datos).hexdigest() in _LOGOS_FIRMA_MD5:
        return True
    size = len(datos)
    if size < 8000:
        return True  # iconos pequeños (LinkedIn, Twitter…)
    dims = dimensiones_imagen(datos)
    if dims:
        w, h = dims
        # Logos/iconos: imágenes pequeñas (el logo de STC es 210x120). Las fotos
        # reales de incidencias son capturas/fotos grandes (>=400px de lado).
        if max(w, h) < 300:
            return True
        if min(w, h) and max(w, h) / min(w, h) >= 4 and min(w, h) < 160:
            return True  # banner fino (logo de empresa)
    return False
