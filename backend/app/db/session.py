from collections.abc import Generator

import psycopg
from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.models import collection, document, document_chunk, ingestion_job

settings = get_settings()

engine = create_engine(settings.resolved_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


@event.listens_for(engine, "connect")
def register_vector_type(dbapi_connection, _) -> None:
    try:
        register_vector(dbapi_connection)
    except psycopg.ProgrammingError as exc:
        if "vector type not found" not in str(exc):
            raise


def initialize_pgvector() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    engine.dispose()


def ensure_vector_schema() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE document_chunks "
                f"ADD COLUMN IF NOT EXISTS embedding vector({settings.embedding_dimensions})"
            )
        )


def initialize_database() -> None:
    initialize_pgvector()
    Base.metadata.create_all(bind=engine)
    ensure_vector_schema()


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
