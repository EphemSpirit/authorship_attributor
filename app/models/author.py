'''
AUTHOR table meant to hold basic information about an Author.
Not meant to hold any stylometric data.
This will serve as a list of authors to check a document against,
and the [DETERMINE TABLE] table will handle the actual document analysis.

An author may be credited on multiple documents, and a document may credit
multiple authors (e.g. co-authored scientific publications), so this is a
many-to-many relationship via the document_authors association table.
Deleting an author only removes their credit from shared documents, not the
documents themselves.
'''

from app.extensions import Base
from sqlalchemy import String, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Author(Base):
    __tablename__ = "authors"
    __table_args__ = (
        UniqueConstraint(
            "name",
            name="uq_author_name"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    author_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    documents = relationship(
        "Document",
        secondary="document_authors",
        back_populates="authors",
    )
    style_profiles = relationship(
        "AuthorStyleProfile",
        back_populates="author",
    )