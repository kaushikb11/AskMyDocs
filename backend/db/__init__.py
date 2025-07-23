import os

from config import settings
from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
)


def create_db_and_tables():
    """Create database tables."""
    # Import models to register them with SQLModel
    from db.models import ChatMessage, Conversation, Document

    SQLModel.metadata.create_all(engine)


def get_engine() -> Engine:
    """Get database engine instance."""
    return engine


# Database initialization is now handled in main.py lifespan
