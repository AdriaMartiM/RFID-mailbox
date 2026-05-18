# app/services/outlook_service.py
import os
from O365 import Account
from dotenv import load_dotenv

load_dotenv()

class OutlookService:
    def __init__(self):
        # Autenticación profesional usando las variables de entorno
        credentials = (os.getenv("OUTLOOK_CLIENT_ID"), os.getenv("OUTLOOK_CLIENT_SECRET"))
        self.tenant_id = os.getenv("OUTLOOK_TENANT_ID")
        self.account = Account(credentials, tenant_id=self.tenant_id)
        
        # Esto gestionará el login por primera vez en la consola
        if not self.account.is_authenticated:
            self.account.authenticate(scopes=['https://graph.microsoft.com/.default'])
            
        self.mailbox = self.account.mailbox()

    def obtener_correos_nuevos(self):
        """Trae solo los correos NO LEÍDOS de la Bandeja de Entrada (Inbox)"""
        inbox = self.mailbox.inbox_folder()
        # Filtramos de forma eficiente para no saturar la red
        query = inbox.new_query().on_attribute('isReadA').equals(False)
        return inbox.get_messages(limit=25, query=query)

    def procesar_y_mover_correo(self, message, ticket_id: str):
        """Modifica el asunto agregando el ID de tu sistema y lo mueve a .01PROCESADO"""
        try:
            # 1. Cambiar el asunto de la conversación de forma limpia
            nuevo_asunto = f"[{ticket_id}] {message.subject}"
            message.subject = nuevo_asunto
            message.save_message() # Guarda el cambio en los servidores de Microsoft
            
            # 2. Marcar como leído para que no se vuelva a procesar
            message.mark_as_read()

            # 3. Buscar la carpeta de destino o crearla si no existe
            root_folder = self.mailbox.get_folder(folder_name='Bandeja de entrada') # O la raíz del Mailbox
            try:
                folder_procesado = root_folder.get_folder(folder_name='.01PROCESADO')
            except Exception:
                # Si la carpeta no existe, la creamos automáticamente para evitar errores
                folder_procesado = root_folder.create_child_folder('.01PROCESADO')

            # 4. Mover el correo al archivo histórico procesado
            message.move(folder_procesado)
            print(f"📦 Correo [{ticket_id}] movido con éxito a .01PROCESADO.")
            return True
        except Exception as e:
            print(f"❌ Error en OutlookService al mover el correo: {str(e)}")
            return False