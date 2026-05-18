from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_code = Column(String, unique=True, index=True)
    company = Column(String)
    store = Column(String)
    phone = Column(String)
    description = Column(String)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)