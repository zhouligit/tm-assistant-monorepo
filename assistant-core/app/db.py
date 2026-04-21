import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


MYSQL_DSN = os.getenv(
    "MYSQL_DSN", "mysql+pymysql://root:123456@127.0.0.1:3306/tm_assistant"
)

engine = create_engine(MYSQL_DSN, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
