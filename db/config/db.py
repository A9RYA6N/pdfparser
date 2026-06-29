from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os

db_url=os.getenv("DATABASE_URL")

engine=create_engine(db_url)

SessionLocal=sessionmaker(
    autoflush=False,
    bind=engine
)

def getDb():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base=declarative_base()