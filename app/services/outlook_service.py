# app/services/outlook_service.py
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Importamos O365 de forma tolerante: si no está instalada, la web sigue
# funcionando y solo falla (con mensaje claro) la captura de correos.
try:
    from O365 import Account, FileSystemTokenBackend
except ImportError:
    Account = None
    FileSystemTokenBackend = None

load_dotenv()

# Modo DELEGADO (solo lectura). El programa lee ÚNICAMENTE tu buzón y los
# buzones compartidos a los que TÚ tienes acceso (como rfid@stcretail.com).
# Nunca lee los buzones de otras personas.
#   - Mail.Read        = tu propio buzón
#   - Mail.Read.Shared = buzones COMPARTIDOS que tú ya abres (rfid@)
# Nota: NO incluir 'offline_access'/'openid'/'profile' — MSAL los añade solo.
SCOPES = ["Mail.Read", "Mail.Read.Shared"]
# Dónde se guarda la sesión una vez autenticado (para no pedir login cada vez).
TOKEN_PATH = "."
TOKEN_FILE = "o365_token.txt"
# URL de redirección tras el login. El '.../oauth2/nativeclient' por defecto ya
# no funciona en muchos tenants (manda a "wrongplace"), y el puerto 80 lo ocupa
# el software de Zebra en este equipo; por eso usamos localhost con puerto 8400.
REDIRECT_URI = "http://localhost:8400"


def construir_account():
    """Crea la cuenta O365 en modo DELEGADO con la sesión persistida en disco.
    La usan tanto el servicio como el script de login de un solo uso."""
    if Account is None:
        raise RuntimeError("La librería 'O365' no está instalada. Ejecuta: pip install O365")

    client_id = os.getenv("OUTLOOK_CLIENT_ID")
    tenant_id = os.getenv("OUTLOOK_TENANT_ID")
    if not client_id or not tenant_id:
        raise RuntimeError(
            "Faltan credenciales de Outlook en el .env "
            "(OUTLOOK_CLIENT_ID / OUTLOOK_TENANT_ID)."
        )

    token_backend = FileSystemTokenBackend(
        token_path=TOKEN_PATH, token_filename=TOKEN_FILE
    )
    # auth_flow_type="public" => cliente PÚBLICO con PKCE (delegado, sin secreto).
    # La app en Azure está marcada como "cliente público", así que NO se manda
    # client_secret (si no, error AADSTS700025). Para este flujo la librería pide
    # SOLO el client_id; la seguridad la aporta PKCE.
    account = Account(
        (client_id,), auth_flow_type="public",
        tenant_id=tenant_id, token_backend=token_backend,
    )
    # La librería fija el redirect a 'nativeclient' en el constructor; lo sobreescribimos.
    account.con.oauth_redirect_url = REDIRECT_URI
    return account


class OutlookService:
    def __init__(self):
        self.account = construir_account()

        # En modo delegado NO autenticamos aquí (eso requiere navegador y se hace
        # una sola vez con 'autenticar_outlook.py'). Aquí solo cargamos la sesión.
        if not self.account.is_authenticated:
            raise RuntimeError(
                "No hay sesión de Outlook guardada. Ejecuta primero (una sola vez):\n"
                "    python autenticar_outlook.py"
            )

        # Buzón del usuario que ha iniciado sesión (tu propio buzón).
        # Si quieres vigilar OTRO buzón al que tengas acceso, pon OUTLOOK_MAILBOX en el .env.
        mailbox_addr = os.getenv("OUTLOOK_MAILBOX")
        self.mailbox = (
            self.account.mailbox(resource=mailbox_addr)
            if mailbox_addr else self.account.mailbox()
        )
        print(f"[INFO] Vigilando el buzón: {mailbox_addr or '(tu buzón)'}")

        # --- Fecha de corte: solo procesamos correos a partir de aquí ---
        # DIAS_HISTORICO=1 (por defecto) => solo desde ayer a las 00:00.
        # Súbelo (ej. 7) o ponlo a 0 para coger también los de hoy sin límite hacia atrás.
        dias = int(os.getenv("DIAS_HISTORICO", "1"))
        self.fecha_corte = (datetime.now() - timedelta(days=dias)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        print(f"[INFO] Solo se procesarán correos recibidos desde: {self.fecha_corte:%d/%m/%Y %H:%M}")

    def obtener_correos_nuevos(self):
        """Trae los correos de la Bandeja de Entrada recibidos a partir de la fecha
        de corte (por defecto, desde ayer).

        Importante: en modo SOLO LECTURA no marcamos los correos como leídos, así que
        NO podemos filtrar por 'no leído' (si tú los abres en Outlook desaparecerían
        del filtro). Filtramos solo por fecha y los duplicados se evitan dentro de la
        app (por conversation_id)."""
        inbox = self.mailbox.inbox_folder()
        qb = inbox.new_query()
        flt = qb.greater_equal('receivedDateTime', self.fecha_corte)
        return inbox.get_messages(
            limit=50, query=flt, order_by="receivedDateTime desc",
            download_attachments=False,
        )

    def obtener_conversacion(self, conversation_id):
        """Trae TODOS los correos de un hilo (recibidos Y enviados, todas las
        carpetas) por su conversationId, ordenados del más antiguo al más nuevo."""
        from datetime import timezone
        qb = self.mailbox.new_query()
        q = qb.equals("conversationId", conversation_id)
        msgs = list(self.mailbox.get_messages(limit=100, query=q, download_attachments=False))

        def clave(m):
            r = getattr(m, "received", None)
            if r is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            return r if r.tzinfo is not None else r.replace(tzinfo=timezone.utc)

        msgs.sort(key=clave)

        # Dedup: el mismo correo aparece en "Enviados" y en "Recibidos" (cuando
        # rfid@ está en copia). Comparten el internetMessageId real -> nos quedamos
        # con una sola copia (la más antigua tras ordenar).
        vistos, unicos = set(), []
        for m in msgs:
            imid = getattr(m, "internet_message_id", None) or getattr(m, "object_id", None)
            if imid in vistos:
                continue
            vistos.add(imid)
            unicos.append(m)
        return unicos

    @staticmethod
    def descargar_adjuntos(message):
        """Descarga los adjuntos de ARCHIVO de un correo y devuelve una lista de
        (nombre, contenido_en_bytes). Filtra los LOGOS/ICONOS de firma (LinkedIn,
        Twitter, banners…) y quita duplicados, para que solo queden las fotos
        reales que ha enviado el cliente. Best-effort."""
        import base64
        import hashlib
        from app.services.email_utils import es_imagen_de_firma
        resultado = []
        vistos = set()
        try:
            atts = message.attachments
            atts.download_attachments()
            for a in atts:
                # Solo adjuntos de tipo archivo (no correos incrustados)
                if getattr(a, "attachment_type", "file") != "file":
                    continue
                nombre = getattr(a, "name", None) or "adjunto"
                contenido = getattr(a, "content", None)
                if contenido is None:
                    continue
                datos = base64.b64decode(contenido) if isinstance(contenido, str) else bytes(contenido)
                # Descarta logos/iconos/banners de firma
                if es_imagen_de_firma(nombre, datos):
                    continue
                # Evita duplicados exactos (la misma imagen citada varias veces)
                h = hashlib.md5(datos).hexdigest()
                if h in vistos:
                    continue
                vistos.add(h)
                resultado.append((nombre, datos))
        except Exception as e:
            print(f"[AVISO] No se pudieron descargar adjuntos: {e}")
        return resultado