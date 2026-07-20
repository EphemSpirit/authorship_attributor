from app.extensions import Base
from sqlalchemy import String, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    author_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)