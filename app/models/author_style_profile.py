from datetime import datetime

from app.extensions import Base
from sqlalchemy import String, JSON, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

'''
AUTHOR_STYLE_PROFILE table holds the stylometric fingerprint computed for an author,
scoped to a single feature family (feature_type, e.g. "function_word_freq") and a
single extraction pipeline version (model_version). Old profiles are kept rather than
overwritten so a new model_version can be compared against an author's prior baseline.
'''

class AuthorStyleProfile(Base):
    __tablename__ = "author_style_profiles"
    __table_args__ = (
        UniqueConstraint(
            "author_id", "feature_type", "model_version",
            name="uq_author_style_profile_triple",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)
    feature_type: Mapped[str] = mapped_column(String(50))
    profile_vector: Mapped[list] = mapped_column(JSON)
    feature_names: Mapped[list] = mapped_column(JSON)
    num_documents_used: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(50))
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author = relationship("Author", backref="style_profiles")
