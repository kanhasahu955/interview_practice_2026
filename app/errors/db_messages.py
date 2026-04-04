"""User-facing text derived from DB driver / SQLAlchemy errors."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError, OperationalError


def integrity_user_message(exc: IntegrityError) -> str:
    raw = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
    lower = raw.lower()

    # PostgreSQL
    if "23505" in raw or "uniqueviolation" in lower or "duplicate key value violates unique constraint" in lower:
        return (
            "That value already exists (for example this email or slug is taken). "
            "Try a different value or update the existing item."
        )
    if "23503" in raw or "foreignkeyviolation" in lower or "violates foreign key constraint" in lower:
        return (
            "A linked record is missing or was deleted (invalid reference). "
            "Check related IDs and try again."
        )
    if "23502" in raw or "notnullviolation" in lower:
        return "A required field was empty and could not be saved."

    # MySQL / MariaDB
    if "duplicate" in lower or "unique" in lower or "1062" in raw:
        return (
            "That value already exists (for example the email or slug is already in use). "
            "Use a different value or update the existing record."
        )
    if "foreign key" in lower or "1452" in raw or "cannot add or update a child row" in lower:
        return "A related record is missing or was removed (invalid reference). Check IDs and try again."
    if "cannot delete or update a parent row" in lower or "1451" in raw:
        return "This record is still in use elsewhere and cannot be changed or removed that way."
    if "not null" in lower or "1048" in raw or "column cannot be null" in lower:
        return "A required field was missing when saving to the database."

    return (
        "The change could not be saved because it conflicts with existing data or database rules. "
        "If this keeps happening, contact support with the time of the request."
    )


def operational_user_message(exc: OperationalError) -> str:
    raw = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
    lower = raw.lower()

    if "timeout" in lower or "timed out" in lower or "57014" in raw:
        return "The database took too long to answer. Please wait a moment and try again."
    if "too many connections" in lower or "1040" in raw:
        return "The database is at capacity right now. Please try again in a short while."
    if "can't connect" in lower or "connection refused" in lower or "2003" in raw or "could not connect" in lower:
        return "We cannot reach the database from the application. Please try again shortly."
    if "lost connection" in lower or "gone away" in lower or "2013" in raw or "server has gone away" in lower:
        return "The database connection dropped while processing your request. Please try again."
    if "ssl" in lower or "tls" in lower or "certificate" in lower:
        return "A secure connection to the database failed. If this continues, contact the operator."
    if "read only" in lower or "1290" in raw:
        return "The database is temporarily read-only. Try again later."

    return "The database is temporarily unavailable. Please try again later."


def generic_database_user_message() -> str:
    return (
        "Something went wrong while talking to the database. "
        "Your change may not have been saved. Please try again; if it persists, contact support."
    )
