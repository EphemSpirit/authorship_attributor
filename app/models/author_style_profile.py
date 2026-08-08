'''
AUTHOR_STYLE_PROFILE table represents a single stylometric fingerprint run for an
author under one extraction pipeline version (model_version). The individual
feature families (function word freq, avg sentence length, etc.) that make up the
fingerprint live on the related AUTHOR_STYLE_FEATURE rows. Old profiles are kept
rather than overwritten so a new model_version can be compared against an author's
prior baseline.
'''

from datetime import datetime

from app.extensions import Base
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AuthorStyleProfile(Base):
    __tablename__ = "author_style_profiles"
    __table_args__ = (
        UniqueConstraint(
            "author_id", "model_version",
            name="uq_author_style_profile_author_model_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)
    num_documents_used: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(50))
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author = relationship("Author", back_populates="style_profiles")
    features = relationship(
        "AuthorStyleFeature",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
