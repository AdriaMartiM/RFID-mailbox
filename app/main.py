from fastapi import FastAPI
from app.database import Base, engine

app = FastAPI(title="RFID Helpdesk")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {"status": "ok"}