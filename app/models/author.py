from app.extensions import Base
from sqlalchemy import String, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

'''
AUTHOR table meant to hold basic information about an Author.
Not meant to hold any stylometric data.
This will serve as a list of authors to check a document against,
and the [DETERMINE TABLE] table will handle the actual document analysis.
'''

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
        back_populates="author",
        cascade="all, delete-orphan",
    )