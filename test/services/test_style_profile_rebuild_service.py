import pytest

from app.models import Author, AuthorStyleProfile, Document
from app.services.style_profile_service import StyleProfileService
from app.services.style_profile_rebuild_service import StyleProfileRebuildService
from test.utils import TestingSessionLocal


@pytest.fixture
def rebuild_service():
    return StyleProfileRebuildService(StyleProfileService())


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


def _profiles_for(db, author_id: int) -> list[AuthorStyleProfile]:
    return db.query(AuthorStyleProfile).filter(AuthorStyleProfile.author_id == author_id).all()


class TestRebuildAll:
    def test_creates_a_profile_with_three_features_for_an_author_with_documents(self, rebuild_service, db):
        author = _author_with_document(db, "Author One", "The quick brown fox jumps.")

        rebuild_service.rebuild_all(db)

        profiles = _profiles_for(db, author.id)
        assert len(profiles) == 1
        assert profiles[0].model_version == "v1"
        assert profiles[0].num_documents_used == 1
        assert {f.feature_type for f in profiles[0].features} == {
            "function_word_freq", "avg_sentence_length", "vocabulary_richness",
        }

    def test_skips_authors_with_no_documents(self, rebuild_service, db):
        author = Author(name="No Documents")
        db.add(author)
        db.commit()
        db.refresh(author)

        rebuild_service.rebuild_all(db)

        assert _profiles_for(db, author.id) == []

    def test_second_rebuild_increments_model_version_and_keeps_history(self, rebuild_service, db):
        author = _author_with_document(db, "Author Two", "Some sample text for stylometry.")

        rebuild_service.rebuild_all(db)
        rebuild_service.rebuild_all(db)

        profiles = _profiles_for(db, author.id)
        assert sorted(p.model_version for p in profiles) == ["v1", "v2"]

    def test_shares_the_same_function_word_list_across_authors(self, rebuild_service, db):
        author_one = _author_with_document(db, "Author Three", "the cat sat on the mat")
        author_two = _author_with_document(db, "Author Four", "a dog ran in the park")

        rebuild_service.rebuild_all(db)

        feature_one = next(
            f for f in _profiles_for(db, author_one.id)[0].features if f.feature_type == "function_word_freq"
        )
        feature_two = next(
            f for f in _profiles_for(db, author_two.id)[0].features if f.feature_type == "function_word_freq"
        )
        assert feature_one.feature_names == feature_two.feature_names
