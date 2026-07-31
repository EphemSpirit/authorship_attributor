import pytest
from sqlalchemy import text

from test.utils import engine


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
