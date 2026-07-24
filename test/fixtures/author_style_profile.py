import pytest
from app.models import AuthorStyleProfile, AuthorStyleFeature
from test.utils import TestingSessionLocal, engine
from test.fixtures.authors import test_author
from sqlalchemy import text
from datetime import datetime

@pytest.fixture
def test_author_style_profile(test_author):
    style_profile = AuthorStyleProfile(
        author_id=test_author.id,
        num_documents_used=12,
        model_version="v1",
        computed_at=datetime(
            year=2026,
            month=7,
            day=21,
            hour=17,
            minute=25,
            second=46,
            microsecond=221560
        ),
        features=[
            AuthorStyleFeature(
                feature_type="function_word_freq",
                profile_vector=[0.021, 0.104, 0.0087],
                feature_names=["the", "of", "and"],
            )
        ]
    )


    db = TestingSessionLocal()
    db.add(style_profile)
    db.commit()
    db.refresh(style_profile)

    yield style_profile

    with engine.connect() as connection:
        connection.execute(text("DELETE FROM author_style_features;"))
        connection.execute(text("DELETE FROM author_style_profiles;"))
        connection.commit()
