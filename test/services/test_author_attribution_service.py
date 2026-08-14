import pytest

from app.models import Author, AuthorStyleFeature, AuthorStyleProfile, Document
from app.services.author_attribution_service import AuthorAttributionService
from app.services.style_profile_rebuild_service import StyleProfileRebuildService
from app.services.style_profile_service import StyleProfileService
from test.utils import TestingSessionLocal

TERSE_TEXT = "I go. I see. I win."
VERBOSE_TEXT = (
    "Subsequently, following considerable deliberation, one might reasonably "
    "conclude that the outcome was, in fact, favorable."
)


@pytest.fixture
def service():
    return AuthorAttributionService()


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


def _author_with_document(db, name: str, text: str) -> Author:
    stats = StyleProfileService().compute_document_stats(text)
    author = Author(
        name=name,
        documents=[Document(filename=f"{name}.docx", text=text, word_count=len(text.split()),
                             content_hash=f"hash-{name}-{text}", **stats)],
    )
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


class TestAttribute:
    def test_raises_with_fewer_than_two_author_profiles(self, service, db):
        _author_with_document(db, "Solo Author", TERSE_TEXT)
        StyleProfileRebuildService().rebuild_all(db)

        with pytest.raises(ValueError):
            service.attribute(db, "Some disputed text.")

    def test_picks_the_author_with_the_closer_style(self, service, db):
        terse_author = _author_with_document(db, "Terse Author", TERSE_TEXT)
        _author_with_document(db, "Verbose Author", VERBOSE_TEXT)
        StyleProfileRebuildService().rebuild_all(db)

        predicted_author, confidence_score = service.attribute(db, "I run. I jump. I win.")

        assert predicted_author.id == terse_author.id
        assert 0 < confidence_score <= 1

    def test_confidence_score_favors_the_closer_match(self, service, db):
        terse_author = _author_with_document(db, "Terse Author", TERSE_TEXT)
        _ = _author_with_document(db, "Verbose Author", VERBOSE_TEXT)
        StyleProfileRebuildService().rebuild_all(db)

        predicted_author, confidence_score = service.attribute(db, TERSE_TEXT)

        assert predicted_author.id == terse_author.id
        # An exact style match against one candidate and a wildly different
        # second candidate should be lopsided, not a coin flip.
        assert confidence_score > 0.5

    def test_raises_when_profiles_have_inconsistent_feature_sets(self, service, db):
        # Bypasses StyleProfileRebuildService, which always keeps every
        # author's feature schema in sync - this simulates the schema
        # drifting apart (e.g. an interrupted rebuild) that _shared_feature_keys
        # is meant to catch.
        author_one = Author(name="Author One")
        author_two = Author(name="Author Two")
        db.add_all([author_one, author_two])
        db.commit()

        db.add_all([
            AuthorStyleProfile(
                author_id=author_one.id,
                num_documents_used=1,
                model_version="v1",
                features=[
                    AuthorStyleFeature(
                        feature_type="function_word_freq", profile_vector=[0.1, 0.2], feature_names=["the", "of"]
                    ),
                    AuthorStyleFeature(
                        feature_type="avg_sentence_length", profile_vector=[10.0], feature_names=["avg_sentence_length"]
                    ),
                    AuthorStyleFeature(
                        feature_type="vocabulary_richness", profile_vector=[0.5], feature_names=["type_token_ratio"]
                    ),
                ],
            ),
            AuthorStyleProfile(
                author_id=author_two.id,
                num_documents_used=1,
                model_version="v1",
                features=[
                    AuthorStyleFeature(
                        feature_type="function_word_freq",
                        profile_vector=[0.1, 0.2, 0.3],
                        feature_names=["the", "of", "and"],
                    ),
                    AuthorStyleFeature(
                        feature_type="avg_sentence_length", profile_vector=[12.0], feature_names=["avg_sentence_length"]
                    ),
                    AuthorStyleFeature(
                        feature_type="vocabulary_richness", profile_vector=[0.4], feature_names=["type_token_ratio"]
                    ),
                ],
            ),
        ])
        db.commit()

        with pytest.raises(ValueError):
            service.attribute(db, "Some disputed text.")
