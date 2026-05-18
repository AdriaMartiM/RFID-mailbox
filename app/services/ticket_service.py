# app/services/ticket_service.py
import uuid
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.message import Message
from app.services.parser_service import ParserService

class TicketService:
    @staticmethod
    def create_from_email(db: Session, email_body: str, conversation_id: str) -> Ticket:
        # 1. Extraemos los datos del texto del correo con tu parser de Regex
        parsed_data = ParserService.parse_outlook_email(email_body)
        
        # 2. Generamos tu propio ID de incidencia único (ej: INC-A4B2)
        unique_ticket_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        
        # 3. Guardamos el ticket en tu base de datos local (tu propio Praxedo)
        db_ticket = Ticket(
            ticket_id=unique_ticket_id,
            empresa=parsed_data["empresa"],
            localizacion=parsed_data["localizacion"],
            telefono=parsed_data["telefono"],
            descripcion=parsed_data["descripcion"],
            outlook_conversation_id=conversation_id,
            estado="PROCESADO" # Estado inicial en tu sistema
        )
        
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
        return db_ticket

    @staticmethod
    def append_reply_to_thread(db: Session, conversation_id: str, sender: str, body: str):
        """Busca si el hilo de Outlook pertenece a un ticket tuyo y le añade el mensaje"""
        ticket = db.query(Ticket).filter(Ticket.outlook_conversation_id == conversation_id).first()
        if not ticket:
            return None
        
        # Creamos el mensaje en el "chat" de este ticket
        new_message = Message(
            ticket_id_fk=ticket.id,
            remitente=sender,
            contenido=body
        )
        db.add(new_message)
        db.commit()
        return ticket