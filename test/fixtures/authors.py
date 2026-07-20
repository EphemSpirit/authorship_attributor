import pytest
from app.models import Author
from test.utils import TestingSessionLocal, engine
from sqlalchemy import text

@pytest.fixture
def test_author():
    author = Author(
        name="Test Author",
        author_metadata={
            "bio": "He wrote a lot of stuff",
            "age": 50,
            "main_influence": "George Orwell"
        }
    )

    db = TestingSessionLocal()
    db.add(author)
    db.commit()

    yield author

    with engine.connect() as connection:
        connection.execute(text("DELETE FROM authors;"))
        connection.commit()