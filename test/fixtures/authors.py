import pytest
from app.models import Author
from test.utils import TestingSessionLocal

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