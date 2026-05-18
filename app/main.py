# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import SessionLocal, engine, Base
from app.services.ticket_service import TicketService
import app.models as models

# Aseguramos que se creen las tablas en tu archivo 'sql_app.db'
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mi Gestor de Incidencias RFID")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- WEBHOOKS DE ENTRADA (Para conectar con tu script de Outlook) ---

class EmailPayload(BaseModel):
    body: str
    conversation_id: str
    sender: str

@app.post("/api/v1/webhooks/new-email")
def webhook_nuevo_correo(payload: EmailPayload, db: Session = Depends(get_db)):
    """Tu script de Outlook llamará aquí al detectar un correo con la plantilla"""
    ticket = TicketService.create_from_email(
        db=db, email_body=payload.body, conversation_id=payload.conversation_id
    )
    # Devolvemos el ID generado para que tu script sepa cómo renombrar el correo
    return {"status": "procesado", "ticket_id": ticket.ticket_id}

@app.post("/api/v1/webhooks/email-reply")
def webhook_respuesta_hilo(payload: EmailPayload, db: Session = Depends(get_db)):
    """Tu script de Outlook llamará aquí si alguien responde al hilo de un correo"""
    ticket = TicketService.append_reply_to_thread(
        db=db, conversation_id=payload.conversation_id, sender=payload.sender, body=payload.body
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Este hilo no pertenece a ningún ticket activo.")
    return {"status": "mensaje_añadido", "ticket_id": ticket.ticket_id}


# --- VISTAS HTML DE TU PROPIO SISTEMA ---

@app.get("/", response_class=HTMLResponse)
def ver_dashboard(request: Request, db: Session = Depends(get_db)):
    """Tu panel de control principal: Lista todas las incidencias creadas"""
    tickets = db.query(models.ticket.Ticket).order_by(models.ticket.Ticket.created_at.desc()).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "tickets": tickets})

@app.get("/ticket/{ticket_id}", response_class=HTMLResponse)
def ver_detalle_ticket(ticket_id: str, request: Request, db: Session = Depends(get_db)):
    """El visor estilo conversación de un ticket concreto"""
    ticket = db.query(models.ticket.Ticket).filter(models.ticket.Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="El ticket no existe.")
    return templates.TemplateResponse("ticket.html", {
        "request": request, 
        "ticket": ticket, 
        "messages": ticket.messages
    })