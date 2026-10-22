"""Database engine/session setup (SQLModel over SQLAlchemy; PostgreSQL in prod, SQLite for local dev)."""
from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from src.config import get_settings

settings = get_settings()
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=_connect_args)


def init_db() -> None:
    """Create tables. Use Alembic migrations instead of this in production."""
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    # create_all does not alter existing tables; backfill columns added after a local DB was created.
    inspector = inspect(engine)
    if "literaturesource" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("literaturesource")}
    additions = {
        "selected": "BOOLEAN NOT NULL DEFAULT TRUE",
        "manually_accepted": "BOOLEAN NOT NULL DEFAULT FALSE",
        "manual_acceptance_reason": "VARCHAR",
    }
    missing = {name: ddl for name, ddl in additions.items() if name not in columns}
    if missing:
        with engine.begin() as connection:
            for name, ddl in missing.items():
                connection.execute(text(f"ALTER TABLE literaturesource ADD COLUMN {name} {ddl}"))


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
