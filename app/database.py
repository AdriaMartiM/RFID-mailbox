from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base  # <-- Añade esta línea
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"  # O la URL de tu base de datos

engine = create_engine(
    # connect_args={"check_same_thread": False} es necesario solo para SQLite
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base() 