"""BigInteger PKs/FKs — avoids MySQL 8 error 3780 (INT/BIGINT FK mismatch)."""

from sqlalchemy import BigInteger, Column, ForeignKey


def pk_bigint() -> Column:
    return Column(BigInteger, primary_key=True, autoincrement=True)


def fk_bigint(
    ref: str,
    *,
    nullable: bool = True,
    ondelete: str | None = None,
) -> Column:
    if ondelete is not None:
        fk = ForeignKey(ref, ondelete=ondelete)
    else:
        fk = ForeignKey(ref)
    return Column(BigInteger, fk, nullable=nullable)
