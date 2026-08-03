# app/services/ticket_service.py
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.adjunto import Adjunto
from app.services.parser_service import ParserService

ADJUNTOS_DIR = "adjuntos_files"
EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def guardar_adjunto(db: Session, ticket_id: int, nombre: str, contenido: bytes, message_id: int = None) -> Adjunto:
    """Guarda en disco el contenido de un adjunto y crea su registro.
    Sirve tanto para los adjuntos que llegan por correo como para pruebas."""
    os.makedirs(ADJUNTOS_DIR, exist_ok=True)
    nombre = os.path.basename(nombre or "adjunto")
    # Anti-duplicados POR CONTENIDO: la misma foto citada en varias respuestas
    # llega con nombres distintos (Outlook los aleatoriza), así que comparamos el
    # contenido real (md5). Si ya está en el ticket, no la repetimos.
    import hashlib
    nuevo_hash = hashlib.md5(contenido).hexdigest()
    for a in db.query(Adjunto).filter(
            Adjunto.ticket_id_fk == ticket_id, Adjunto.tamano == len(contenido)).all():
        if a.ruta and os.path.isfile(a.ruta):
            try:
                if hashlib.md5(open(a.ruta, "rb").read()).hexdigest() == nuevo_hash:
                    return a
            except OSError:
                pass
    ext = os.path.splitext(nombre)[1].lower()
    ruta = os.path.join(ADJUNTOS_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(ruta, "wb") as f:
        f.write(contenido)
    adj = Adjunto(
        ticket_id_fk=ticket_id,
        message_id_fk=message_id,
        tipo=("imagen" if ext in EXT_IMAGEN else "documento"),
        nombre=nombre,
        ruta=ruta,
        tamano=len(contenido),
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return adj

class TicketService:
    @staticmethod
    def create_from_email(db: Session, email_body: str, conversation_id: str, recibido: datetime = None,
                          email_id: str = None, asunto: str = None, remitente: str = None) -> Ticket:
        # 0. Anti-duplicados: si ya existe un ticket para este hilo de Outlook,
        #    lo devolvemos sin crear otro (clave en modo solo-lectura, porque
        #    veremos el mismo correo en cada escaneo).
        existente = (
            db.query(Ticket)
            .filter(Ticket.outlook_conversation_id == conversation_id)
            .first()
        )
        if existente:
            return existente

        # 1. Extraemos los datos del texto del correo con tu parser de Regex
        parsed_data = ParserService.parse_outlook_email(email_body)

        # 1b. Correos LIBRES (sin la plantilla): usamos el ASUNTO como titular
        #     (campo "empresa", que es lo que se ve en la lista). El usuario lo
        #     ajusta luego en "Nuevas". Así no queda "Desconocida".
        empresa = parsed_data.get("empresa") or ""
        if not empresa or empresa == "Desconocida":
            titulo = (asunto or "").strip()
            # Quitamos los prefijos de respuesta/reenvío (RE:, Re:, RV:, FW:, Fwd:)
            import re as _re
            titulo = _re.sub(r"^(?:\s*(?:re|rv|fw|fwd|aw)\s*:\s*)+", "", titulo, flags=_re.IGNORECASE).strip()
            empresa = titulo or (remitente or "").strip() or "Sin asunto"
        parsed_data = {**parsed_data, "empresa": empresa}

        # 2. Generamos tu propio ID de incidencia único (ej: INC-A4B2)
        unique_ticket_id = f"INC-{uuid.uuid4().hex[:6].upper()}"

        # 3. La hora de llegada es la hora REAL del correo en Outlook (automática).
        #    Marca la prioridad: cuanto antes llegó, más urgente. Si no nos la pasan
        #    (webhook/manual), usamos el momento actual.
        momento = recibido or datetime.utcnow()

        # 4. La descripción es SIEMPRE el correo inicial completo (luego se puede
        #    editar a mano). Así no se pierde nada del mensaje original.
        descripcion = (email_body or "").strip() or parsed_data["descripcion"]

        # 5. Guardamos el ticket en tu base de datos local (tu propio Praxedo)
        db_ticket = Ticket(
            ticket_id=unique_ticket_id,
            empresa=parsed_data["empresa"],
            localizacion=parsed_data["localizacion"],
            telefono=parsed_data["telefono"],
            descripcion=descripcion,
            cuerpo_inicial=descripcion,   # copia ORIGINAL e inmutable para el hilo
            outlook_conversation_id=conversation_id,
            estado="PROCESADO",  # Estado inicial en tu sistema
            created_at=momento,
            hora_llegada=momento,  # hora de llegada = llegada del correo (automática)
            email_inicial_id=email_id,
        )

        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
        return db_ticket

    @staticmethod
    def append_reply_to_thread(db: Session, conversation_id: str, sender: str, body: str,
                               message_id: str = None, recibido: datetime = None):
        """Añade un correo entrante al hilo de un ticket y lo marca como novedad
        (para que aparezca en azul). Evita duplicar si ya teníamos ese correo."""
        ticket = db.query(Ticket).filter(Ticket.outlook_conversation_id == conversation_id).first()
        if not ticket:
            return None

        # Anti-duplicados: si ya teníamos ese correo (por su id de Outlook), no repetimos
        if message_id:
            ya = db.query(Message).filter(Message.outlook_message_id == message_id).first()
            if ya:
                return ticket

        new_message = Message(
            ticket_id_fk=ticket.id,
            remitente=sender,
            contenido=body,
            outlook_message_id=message_id,
            fecha_envio=recibido or datetime.utcnow(),
        )
        db.add(new_message)
        # Marca novedad: hay un mensaje nuevo sin leer en una incidencia abierta
        if ticket.estado != "CERRADO":
            ticket.nuevo_mensaje = True
        db.commit()
        return ticket