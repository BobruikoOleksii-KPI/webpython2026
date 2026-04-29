from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection string
DATABASE_URL = "postgresql+psycopg2://postgres:SdKfz251AusfD@localhost:5432/library_db"

engine = create_engine(DATABASE_URL, echo=False)  # echo=True shows SQL queries (useful for debugging)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()