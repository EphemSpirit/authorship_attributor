import pytest
from sqlalchemy import text

import app.services.style_profile_rebuild_service as style_profile_rebuild_service
from test.utils import engine, TestingSessionLocal


@pytest.fixture(autouse=True)
def use_test_session_for_background_rebuild(monkeypatch):
    """
    StyleProfileRebuildService.rebuild_all_in_background opens its own DB
    session (it runs as a background task, outside any request-scoped
    session) via app.extensions.SessionLocal, which points at the real
    DATABASE_URL. TestClient runs background tasks synchronously within the
    test process, so without this, upload tests would write rebuild data
    into the real dev database instead of the test one.
    """
    monkeypatch.setattr(style_profile_rebuild_service, "SessionLocal", TestingSessionLocal)


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM author_style_features;"))
        connection.execute(text("DELETE FROM author_style_profiles;"))
        connection.execute(text("DELETE FROM document_authors;"))
        connection.execute(text("DELETE FROM documents;"))
        connection.execute(text("DELETE FROM authors;"))
        connection.commit()
