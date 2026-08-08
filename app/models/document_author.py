'''
DOCUMENT_AUTHORS association table implementing the many-to-many relationship
between documents and authors (e.g. co-authored scientific publications).
Carries no data of its own beyond the two foreign keys.
'''

from app.extensions import Base
from sqlalchemy import Table, Column, Integer, ForeignKey

document_authors = Table(
    "document_authors",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id"), primary_key=True),
)
