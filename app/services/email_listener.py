# app/services/email_listener.py
import re
import time
from datetime import timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.outlook_service import OutlookService
from app.services.ticket_service import TicketService, guardar_adjunto
from app.services.email_utils import cuerpo_legible
from app.models.ticket import Ticket
from app.models.message import Message

_AUTORESPUESTA = re.compile(
    r"out of (the )?office|automatic reply|respuesta autom[aá]tica|fuera de la oficina",
    re.IGNORECASE,
)


def _es_autorespuesta(asunto: str) -> bool:
    return bool(_AUTORESPUESTA.search(asunto or ""))


def _cuerpo_limpio(msg) -> str:
    es_html = (getattr(msg, "body_type", "html") or "html").lower() == "html"
    return cuerpo_legible(msg.body or "", es_html=es_html)


def _recibido(msg):
    """Hora real del correo, sin zona horaria (para guardar en la BD)."""
    r = getattr(msg, "received", None)
    if r is not None and r.tzinfo is not None:
        r = r.astimezone().replace(tzinfo=None)
    return r


# Margen de seguridad que restamos al último correo conocido. Absorbe los correos
# que llegan desordenados y los pequeños desfases de reloj entre Outlook y el PC.
# Pedir de más no duplica nada (el anti-duplicados va por conversation_id y por
# el id de mensaje de Outlook), así que ser generoso sale gratis.
MARGEN = timedelta(hours=2)


def _fecha_corte(db: Session):
    """Desde cuándo hay que pedir correos: justo después del último que ya tenemos
    guardado (menos el margen). Así, si el programa ha estado parado un fin de
    semana o tres semanas, al arrancar recupera solo ese hueco; y en marcha normal
    la ventana es de un par de horas.

    Devuelve None si la base de datos está vacía (primer uso): entonces manda la
    fecha de arranque en frío de OutlookService (DIAS_HISTORICO)."""
    # Correo inicial más reciente. created_at es la hora real de llegada del correo
    # y NO se puede editar desde la web (a diferencia de hora_llegada).
    ultimo_ticket = db.query(func.max(Ticket.created_at)).scalar()
    # Respuesta más reciente traída de Outlook. Filtramos por outlook_message_id
    # para no contar las notas escritas a mano en la web, que llevan la fecha de
    # hoy y adelantarían el corte saltándose correos de verdad.
    ultima_resp = (
        db.query(func.max(Message.fecha_envio))
        .filter(Message.outlook_message_id.isnot(None))
        .scalar()
    )
    fechas = [f for f in (ultimo_ticket, ultima_resp) if f]
    if not fechas:
        return None
    return max(fechas) - MARGEN


def _sincronizar_hilo(db: Session, outlook: OutlookService, conv: str):
    """Trae el HILO COMPLETO de Outlook y lo refleja en la incidencia:
    crea el ticket si no existe (con el correo más antiguo como descripción) y
    añade como mensajes todos los correos del hilo que aún no tengamos."""
    hilo = outlook.obtener_conversacion(conv)
    # Fuera respuestas automáticas (fuera de oficina): son ruido
    hilo = [m for m in hilo if not _es_autorespuesta(m.subject or "")]
    if not hilo:
        return

    ticket = db.query(Ticket).filter(Ticket.outlook_conversation_id == conv).first()

    # 1) Si no existe, lo creamos a partir del correo MÁS ANTIGUO del hilo
    if not ticket:
        primero = hilo[0]
        ticket = TicketService.create_from_email(
            db=db, email_body=_cuerpo_limpio(primero), conversation_id=conv,
            recibido=_recibido(primero), email_id=getattr(primero, "object_id", None),
            asunto=primero.subject or "", remitente=str(primero.sender),
        )
        for nombre, datos in OutlookService.descargar_adjuntos(primero):
            guardar_adjunto(db, ticket.id, nombre, datos, message_id=None)
        print(f"[OK] Nueva incidencia: {ticket.ticket_id} (asunto: {(primero.subject or '')[:40]})")

    # 2) Sincronizamos el resto de correos del hilo como mensajes (solo los nuevos)
    for m in hilo:
        mid = getattr(m, "object_id", None)
        # El correo inicial ya es la descripción del ticket
        if mid and mid == ticket.email_inicial_id:
            continue
        # ¿Ya lo teníamos guardado?
        if mid and db.query(Message).filter(Message.outlook_message_id == mid).first():
            continue
        actualizado = TicketService.append_reply_to_thread(
            db=db, conversation_id=conv, sender=str(m.sender),
            body=_cuerpo_limpio(m), message_id=mid, recibido=_recibido(m),
        )
        if actualizado:
            nuevo_msg = db.query(Message).filter(Message.outlook_message_id == mid).first()
            for nombre, datos in OutlookService.descargar_adjuntos(m):
                guardar_adjunto(db, ticket.id, nombre, datos,
                                message_id=(nuevo_msg.id if nuevo_msg else None))


def start_email_listener():
    """Vigilante de incidencias: detecta hilos con actividad en la Bandeja de
    entrada y sincroniza la CONVERSACIÓN COMPLETA (recibidos + enviados)."""
    print("[INFO] Vigilante de correos activado. Buscando incidencias RFID...")

    try:
        outlook = OutlookService()
    except Exception as e:
        print(f"[ERROR] No se pudo conectar con la API de Outlook: {str(e)}")
        return

    primera_vuelta = True
    while True:
        db: Session = SessionLocal()
        try:
            # El corte se recalcula en CADA vuelta a partir de lo que ya tenemos
            # guardado: si el programa ha estado parado, la primera vuelta cubre
            # todo el hueco; después la ventana se queda en un par de horas.
            corte = _fecha_corte(db)
            if primera_vuelta:
                desde = corte or outlook.fecha_corte
                print(f"[INFO] Recuperando correos desde: {desde:%d/%m/%Y %H:%M}")
                primera_vuelta = False

            # Miramos la bandeja para detectar QUÉ hilos tienen actividad reciente
            nuevos = list(outlook.obtener_correos_nuevos(desde=corte))
            convs = []
            for msg in nuevos:
                c = msg.conversation_id
                if c and c not in convs:
                    convs.append(c)

            # Para cada hilo con actividad, sincronizamos la conversación entera
            for conv in convs:
                try:
                    _sincronizar_hilo(db, outlook, conv)
                except Exception as e:
                    print(f"[AVISO] No se pudo sincronizar un hilo: {str(e)}")

        except Exception as e:
            print(f"[AVISO] Error durante el ciclo de escaneo: {str(e)}")
        finally:
            db.close()

        # Pausa entre escaneos (30 s de respiro para la API y la CPU)
        time.sleep(30)
