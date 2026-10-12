"""Database configuration and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.

    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db: Session, dealer_id: int) -> None:
    """Set the PostgreSQL RLS tenant context for the current transaction."""
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.current_dealer_id', :dealer_id, true)"), {"dealer_id": str(dealer_id)})
