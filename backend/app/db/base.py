"""Declarative base shared by every ORM model."""
import secrets
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, MetaData, TypeDecorator
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names so Alembic can drop/alter them on both SQLite and PostgreSQL.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator):
    """Timestamps always come back timezone-aware in UTC.

    SQLite stores datetimes without an offset, so values read back are naive; serialised as-is, the
    browser would take them for local time and show them hours off.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            raise ValueError("Naive datetime; use app.db.base.utcnow()")
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {dict: JSON, list: JSON, datetime: UTCDateTime()}


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    """Readable public id such as `LP-3F9A1C0B2E`, matching the ids the frontend already shows."""
    return f"{prefix}-{secrets.token_hex(5).upper()}"


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Store enum values as VARCHAR + CHECK instead of a native enum type.

    Native PostgreSQL enums need a migration for every new value; a CHECK constraint behaves
    the same on SQLite and PostgreSQL.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )
