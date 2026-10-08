from typing import Generator
from app.core.config import settings
from app.core.security import install_log_redaction
from app.db.connection import create_database_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base

install_log_redaction()
engine = create_database_engine(settings.DATABASE_URL, settings)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
