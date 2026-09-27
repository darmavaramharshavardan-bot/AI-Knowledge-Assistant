import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


# ============================================================
# USE PG8000
# ============================================================

# Convert:
# postgresql+psycopg://
#
# to:
# postgresql+pg8000://

if DATABASE_URL.startswith("postgresql+psycopg://"):

    DATABASE_URL = DATABASE_URL.replace(
        "postgresql+psycopg://",
        "postgresql+pg8000://",
        1
    )

elif DATABASE_URL.startswith("postgresql://"):

    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+pg8000://",
        1
    )


# ============================================================
# DATABASE ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================================
# BASE MODEL
# ============================================================

Base = declarative_base()


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()