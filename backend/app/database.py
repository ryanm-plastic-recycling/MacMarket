from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import mysql.connector

# Connection string for SQLAlchemy. Use an environment variable in production
# to avoid committing credentials. The fallback uses local development values.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://macmarket_user:MarketLLMftw2020Brentwood@localhost:3306/macmarket",
)

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def connect_to_db():
    """Return a new MySQL connection using the DATABASE_URL settings."""
    url = engine.url
    return mysql.connector.connect(
        host=url.host or "localhost",
        user=url.username or "user",
        password=url.password or "password",
        database=url.database or "",
        port=url.port or 3306,
    )
