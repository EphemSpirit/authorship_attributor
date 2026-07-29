from datetime import datetime

from app.extensions import Base
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

'''
DOCUMENT table holds one ingested writing sample per row, belonging to an
Author. filename/text/word_count are populated at upload time; status tracks
the separate, later stylometric analysis stage (pending/processed/failed).
'''

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "author_id", "filename",
            name="uq_document_author_filename",
        ),
        UniqueConstraint(
            "author_id", "content_hash",
            name="uq_document_author_content_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author = relationship("Author", back_populates="documents")
