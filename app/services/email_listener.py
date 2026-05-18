# app/services/email_listener.py
import time
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.outlook_service import OutlookService
from app.services.ticket_service import TicketService

def start_email_listener():
    """
    Bucle optimizado y controlado de monitorización de incidencias.
    Se ejecuta de forma asíncrona sin congelar la aplicación web.
    """
    print("👀 Daemon de escucha de correos activado. Buscando incidencias RFID...")
    
    # Inicializamos el servicio de Microsoft
    try:
        outlook = OutlookService()
    except Exception as e:
        print(f"❌ Error crítico al conectar con la API de Outlook: {str(e)}")
        return

    while True:
        # Creamos una sesión de Base de Datos nueva para cada ciclo de revisión
        db: Session = SessionLocal()
        try:
            mensajes_nuevos = outlook.obtener_correos_nuevos()
            
            for msg in mensajes_nuevos:
                # Verificamos si el cuerpo del correo contiene la plantilla de tu incidencia
                if "INCIDENCIA RFID" in msg.subject or "Localización de la tienda:" in msg.body:
                    print(f"📩 Detectada nueva incidencia de: {msg.sender}")
                    
                    # 1. Guardamos en tu base de datos (Tu propio Praxedo) y generamos el ID único
                    nuevo_ticket = TicketService.create_from_email(
                        db=db, 
                        email_body=msg.body, 
                        conversation_id=msg.conversation_id
                    )
                    
                    # 2. Modificamos el asunto en Outlook y lo movemos a la carpeta .01PROCESADO
                    outlook.procesar_y_mover_correo(
                        message=msg, 
                        ticket_id=nuevo_ticket.ticket_id
                    )
                else:
                    # Si es un correo normal, simplemente lo ignoramos para que el usuario lo lea
                    pass
                    
        except Exception as e:
            print(f"⚠️ Error durante el ciclo de escaneo: {str(e)}")
        finally:
            db.close() # Cerramos siempre la conexión a la base de datos para no saturar SQLite

        # Pausa de control profesional (30 segundos de respiro para la API y tu CPU)
        time.sleep(30)