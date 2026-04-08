from collections.abc import Generator
import re

import psycopg
from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.models import (
    chat_message,
    chat_session,
    collection,
    document,
    document_chunk,
    ingestion_job,
    message_feedback,
)

settings = get_settings()
VECTOR_TYPE_PATTERN = re.compile(r"^vector\((\d+)\)$")

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
                f"ADD COLUMN IF NOT EXISTS embedding vector({settings.resolved_embedding_dimensions})"
            )
        )
        current_type = connection.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute AS a
                JOIN pg_class AS c ON a.attrelid = c.oid
                WHERE c.relname = 'document_chunks'
                  AND a.attname = 'embedding'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """
            )
        ).scalar_one_or_none()

        expected_type = f"vector({settings.resolved_embedding_dimensions})"
        if current_type == expected_type:
            return

        if current_type is not None and VECTOR_TYPE_PATTERN.match(current_type):
            connection.execute(
                text(
                    """
                    UPDATE documents
                    SET status = 'uploaded'
                    WHERE id IN (
                        SELECT DISTINCT document_id
                        FROM document_chunks
                        WHERE embedding IS NOT NULL
                    )
                    """
                )
            )
            connection.execute(text("UPDATE document_chunks SET embedding = NULL"))
            connection.execute(
                text(
                    "ALTER TABLE document_chunks "
                    f"ALTER COLUMN embedding TYPE vector({settings.resolved_embedding_dimensions}) "
                    f"USING NULL::vector({settings.resolved_embedding_dimensions})"
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
