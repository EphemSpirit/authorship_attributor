from app.extensions import Base
from sqlalchemy import String, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

'''
AUTHOR table meant to hold basic information about an Author.
Not meant to hold any stylometric data.
This will serve as a list of authors to check a document against,
and the [DETERMINE TABLE] table will handle the actual document analysis.
Authors will also have a one-to-many relationship with Documents (table to-be-defined)
'''

class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    author_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)