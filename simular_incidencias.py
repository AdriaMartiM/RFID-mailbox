# simular_incidencias.py
# -----------------------------------------------------------------------------
# Crea incidencias de EJEMPLO en la base de datos para ver la app funcionando
# sin necesidad de Outlook. Ejecuta:
#     python simular_incidencias.py
# Para borrarlas (dejan de molestar) usa la opción --limpiar:
#     python simular_incidencias.py --limpiar
# -----------------------------------------------------------------------------
import sys
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database import SessionLocal, engine, Base
from app.models.ticket import Ticket
from app.models.message import Message

Base.metadata.create_all(bind=engine)

PREFIJO_DEMO = "conv-demo-"

# (empresa, localización, teléfono, descripción, estado, dias_desde_hoy, solucion, [(remitente, texto, dias), ...])
DEMOS = [
    ("Blue Banana", "ECI Lisboa", "351 912 345 678",
     "Desde el 4 de mayo no puedo conectar la PDA con las antenas RFID de la tienda.",
     "PROCESADO", 0, None,
     [("ECI Lisboa <eci.lisboa@bluebanana.com>", "Buenas, seguimos sin poder leer etiquetas en la entrada.", 0)]),

    ("Blue Banana", "Zaragoza Centro", "976 112 233",
     "El iD POS no tiene conexión con el lector RFID, no detecta ninguna prenda.",
     "EN_PROGRESO", 2, None,
     [("Tienda Zaragoza <zaragoza@bluebanana.com>", "El iD POS no tenía conexión, ¿podéis revisarlo?", 2),
      ("rfid@stcretail.com", "Estamos revisando la configuración de red del lector. Os avisamos.", 1)]),

    ("Blue Banana", "Pozuelo", "915 998 877",
     "Hola buenas tardes, estamos teniendo cortes intermitentes con el RFID en caja.",
     "EN_PROGRESO", 3, None,
     [("ECI Pozuelo <ecipozuelo@bluebanana.com>", "Los cortes pasan sobre todo por la tarde.", 3),
      ("rfid@stcretail.com", "Llamada realizada y reset del RFID12. Monitorizando.", 1)]),

    ("Koala Bay", "C.C. Habaneras (Torrevieja)", "966 700 100",
     "Algo está pasando con el arco de seguridad, pita sin motivo constantemente.",
     "CERRADO", 20, "Nos conectamos en remoto y recalibramos las antenas. El arco dejó de pitar.",
     [("Koala Bay Habaneras <habaneras@koalabay.com>", "El arco pita sin parar desde ayer.", 20),
      ("rfid@stcretail.com", "Nos conectamos en remoto y recalibramos las antenas.", 18),
      ("Koala Bay Habaneras <habaneras@koalabay.com>", "Perfecto, ya no pita. Gracias!", 17)]),

    ("Koala Bay", "C.C. Yumbo (Gran Canaria)", "928 760 540",
     "Se observó que el contador de entradas RFID no cuadra con las ventas.",
     "CERRADO", 35, "Se realizaron varias pruebas y se ajustó el inventario. Resuelto.",
     [("Koala Bay Yumbo <yumbo@koalabay.com>", "Los números no cuadran esta semana.", 35),
      ("rfid@stcretail.com", "Se realizaron varias pruebas y se ajustó el inventario. Resuelto.", 30)]),

    ("Sindicat", "Sindicat Mallorca", "971 220 330",
     "Las antenas de seguridad de la puerta principal no encienden.",
     "PROCESADO", 0, None,
     []),
]


def limpiar(db):
    # Borramos uno a uno para que la cascada elimine también sus mensajes
    tickets = db.query(Ticket).filter(Ticket.outlook_conversation_id.like(PREFIJO_DEMO + "%")).all()
    for t in tickets:
        db.delete(t)
    # Por si quedaron mensajes huérfanos de versiones anteriores, los limpiamos
    ids_validos = {r[0] for r in db.query(Ticket.id).all()}
    huerfanos = [m for m in db.query(Message).all() if m.ticket_id_fk not in ids_validos]
    for m in huerfanos:
        db.delete(m)
    db.commit()
    print(f"Eliminadas {len(tickets)} incidencias de ejemplo ({len(huerfanos)} mensajes huérfanos limpiados).")


def sembrar(db):
    ahora = datetime.now()
    creadas = 0
    for i, (empresa, loc, tel, desc, estado, dias, solucion, mensajes) in enumerate(DEMOS):
        conv = f"{PREFIJO_DEMO}{i:03d}"
        if db.query(Ticket).filter(Ticket.outlook_conversation_id == conv).first():
            continue  # ya existe, no duplicar
        creado = ahora - timedelta(days=dias)
        ticket = Ticket(
            ticket_id=f"INC-DEMO{i:02d}",
            empresa=empresa, localizacion=loc, telefono=tel, descripcion=desc,
            outlook_conversation_id=conv, estado=estado,
            created_at=creado, updated_at=creado,
            hora_llegada=creado,                       # llegada = llegada del correo
            solucion=solucion,
            hora_cierre=(creado + timedelta(days=2)) if estado == "CERRADO" else None,
        )
        db.add(ticket)
        db.flush()  # para tener ticket.id
        ult = creado
        for rem, texto, dmsg in mensajes:
            fecha = ahora - timedelta(days=dmsg)
            db.add(Message(ticket_id_fk=ticket.id, remitente=rem, contenido=texto, fecha_envio=fecha))
            ult = max(ult, fecha)
        # updated_at refleja el último movimiento (para el filtro de cerradas)
        ticket.updated_at = ult
        creadas += 1
    db.commit()

    # Simula que llega un correo NUEVO a una incidencia en progreso (aviso azul)
    demo = db.query(Ticket).filter(Ticket.outlook_conversation_id == PREFIJO_DEMO + "002").first()
    if demo and not any("vuelto a aparecer" in (m.contenido or "") for m in demo.messages):
        db.add(Message(
            ticket_id_fk=demo.id,
            remitente="ECI Pozuelo <ecipozuelo@bluebanana.com>",
            contenido="El problema ha vuelto a aparecer esta mañana, ¿podéis revisarlo otra vez?",
            fecha_envio=ahora,
        ))
        demo.nuevo_mensaje = True
        db.commit()
    print(f"Creadas {creadas} incidencias de ejemplo. Abre http://127.0.0.1:8000")


def main():
    db = SessionLocal()
    try:
        if "--limpiar" in sys.argv:
            limpiar(db)
        else:
            sembrar(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
