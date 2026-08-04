from datetime import datetime

from app.extensions import Base
from sqlalchemy import Integer, String, Text, JSON, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

'''
DOCUMENT table holds one ingested writing sample per row. A document may be
credited to multiple authors (e.g. co-authored scientific publications), so
the document/author relationship is many-to-many via the document_authors
association table. filename/text/word_count are populated at upload time;
status tracks the separate, later stylometric analysis stage
(pending/processed/failed). content_hash is globally unique: identical
content uploaded again is the same document, just possibly credited to an
additional author, rather than a new row.

token_counts/sentence_count/total_sentence_word_count are stylometric stats
cached at upload time (see StyleProfileService.compute_document_stats). Style
profiles get rebuilt from the whole corpus on every upload, so these let
that rebuild aggregate cached per-document counts instead of re-tokenizing
every document's raw text on every rebuild.
'''

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "content_hash",
            name="uq_document_content_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    token_counts: Mapped[dict] = mapped_column(JSON)
    sentence_count: Mapped[int] = mapped_column(Integer)
    total_sentence_word_count: Mapped[int] = mapped_column(Integer)

    authors = relationship(
        "Author",
        secondary="document_authors",
        back_populates="documents",
    )
