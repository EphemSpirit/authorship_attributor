'''
AUTHOR_STYLE_FEATURE table holds a single feature family's vector (e.g.
"function_word_freq", "avg_sentence_length") for a parent AUTHOR_STYLE_PROFILE.
A profile has one row here per feature_type it was computed with.
'''

from app.extensions import Base
from sqlalchemy import Integer, String, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AuthorStyleFeature(Base):
    __tablename__ = "author_style_features"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "feature_type",
            name="uq_author_style_feature_profile_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("author_style_profiles.id"), index=True)
    feature_type: Mapped[str] = mapped_column(String(50))
    profile_vector: Mapped[list] = mapped_column(JSON)
    feature_names: Mapped[list] = mapped_column(JSON)

    profile = relationship("AuthorStyleProfile", back_populates="features")
