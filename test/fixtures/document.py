import pytest
from app.models import Document, Author
from test.utils import TestingSessionLocal, engine
from .authors import test_author
from sqlalchemy import text
import hashlib

@pytest.fixture
def test_document(test_author: Author):
    example_text = "This is a sample document"

    document = Document(
        author_id=test_author.id,
        filename="sample.docx",
        text=example_text,
        word_count=len(example_text.split()),
        content_hash=hashlib.sha256(example_text.encode("utf-8")).hexdigest()
    )

    db = TestingSessionLocal()
    db.add(document)
    db.commit()

    yield document

    with engine.connect() as connection:
        connection.execute(text("DELETE FROM documents;"))
        connection.commit()