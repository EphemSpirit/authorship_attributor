import hashlib
import io

from fastapi import status

from app.extensions import get_db
from app.models import Author, Document
from test.fixtures.authors import test_author
from test.fixtures.document import make_docx_upload
from test.utils import TestingSessionLocal, app, client, override_get_db

app.dependency_overrides[get_db] = override_get_db

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(author_name, filename, fileobj, content_type=DOCX_CONTENT_TYPE):
    return client.post(
        "/documents/upload",
        params={"author_name": author_name},
        files={"file": (filename, fileobj, content_type)},
    )


def _get_author_by_name(name):
    db = TestingSessionLocal()
    try:
        return db.query(Author).filter(Author.name == name).first()
    finally:
        db.close()


def _get_documents_for_author(author_id):
    db = TestingSessionLocal()
    try:
        return db.query(Document).filter(Document.author_id == author_id).all()
    finally:
        db.close()


def test_upload_creates_author_and_document(make_docx_upload):
    paragraphs = ["Hello world, this is a sample document.", "It has two paragraphs."]
    filename, fileobj, content = make_docx_upload(paragraphs=paragraphs, filename="sample.docx")

    response = _upload("Stephen King", filename, fileobj)

    assert response.status_code == status.HTTP_200_OK

    author = _get_author_by_name("Stephen King")
    assert author is not None

    documents = _get_documents_for_author(author.id)
    assert len(documents) == 1

    expected_text = " ".join(paragraphs)
    expected_word_count = sum(len(p.split()) for p in paragraphs)
    expected_hash = hashlib.sha256(expected_text.encode("utf-8")).hexdigest()

    document = documents[0]
    assert document.filename == "sample.docx"
    assert document.text == expected_text
    assert document.word_count == expected_word_count
    assert document.content_hash == expected_hash


def test_upload_titlecases_new_author_name(make_docx_upload):
    filename, fileobj, _ = make_docx_upload()

    response = _upload("stephen king", filename, fileobj)

    assert response.status_code == status.HTTP_200_OK
    assert _get_author_by_name("Stephen King") is not None
    assert _get_author_by_name("stephen king") is None


def test_upload_existing_author_associates_document_with_existing_author(test_author: Author, make_docx_upload):
    filename, fileobj, _ = make_docx_upload()

    response = _upload(test_author.name.lower(), filename, fileobj)

    assert response.status_code == status.HTTP_200_OK

    documents = _get_documents_for_author(test_author.id)
    assert len(documents) == 1
    assert documents[0].filename == filename


def test_upload_existing_author_does_not_create_duplicate_author_row(test_author: Author, make_docx_upload):
    filename, fileobj, _ = make_docx_upload()

    _upload(test_author.name.lower(), filename, fileobj)

    db = TestingSessionLocal()
    try:
        matching_authors = db.query(Author).filter(Author.name == test_author.name).all()
    finally:
        db.close()

    assert len(matching_authors) == 1
    assert matching_authors[0].id == test_author.id


def test_upload_same_author_twice_creates_two_documents(make_docx_upload):
    first_filename, first_fileobj, _ = make_docx_upload(
        paragraphs=["First document content."], filename="first.docx"
    )
    second_filename, second_fileobj, _ = make_docx_upload(
        paragraphs=["Second document, different content."], filename="second.docx"
    )

    first_response = _upload("Jane Austen", first_filename, first_fileobj)
    second_response = _upload("Jane Austen", second_filename, second_fileobj)

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_200_OK

    author = _get_author_by_name("Jane Austen")
    documents = _get_documents_for_author(author.id)
    assert {document.filename for document in documents} == {"first.docx", "second.docx"}


def test_upload_duplicate_content_for_same_author_returns_error(make_docx_upload):
    first_filename, first_fileobj, _ = make_docx_upload(filename="first.docx")
    second_filename, second_fileobj, _ = make_docx_upload(filename="second.docx")

    first_response = _upload("Charles Dickens", first_filename, first_fileobj)
    assert first_response.status_code == status.HTTP_200_OK

    second_response = _upload("Charles Dickens", second_filename, second_fileobj)
    assert second_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert second_response.json()["detail"] == "Document already exists for this author"

    author = _get_author_by_name("Charles Dickens")
    assert len(_get_documents_for_author(author.id)) == 1


def test_upload_duplicate_filename_for_same_author_returns_error(make_docx_upload):
    first_filename, first_fileobj, _ = make_docx_upload(
        paragraphs=["First version of the document."], filename="report.docx"
    )
    second_filename, second_fileobj, _ = make_docx_upload(
        paragraphs=["A different, revised version of the document."], filename="report.docx"
    )

    first_response = _upload("Charlotte Bronte", first_filename, first_fileobj)
    assert first_response.status_code == status.HTTP_200_OK

    second_response = _upload("Charlotte Bronte", second_filename, second_fileobj)
    assert second_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert second_response.json()["detail"] == "Document already exists for this author"

    author = _get_author_by_name("Charlotte Bronte")
    assert len(_get_documents_for_author(author.id)) == 1


def test_upload_invalid_file_type_returns_error():
    response = _upload(
        "Someone New",
        "notes.txt",
        io.BytesIO(b"This is plain text, not a docx file."),
        content_type="text/plain",
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Trouble reading document. Not .docx"


def test_upload_invalid_file_type_still_creates_author_but_no_document():
    _upload(
        "Someone New",
        "notes.txt",
        io.BytesIO(b"This is plain text, not a docx file."),
        content_type="text/plain",
    )

    author = _get_author_by_name("Someone New")
    assert author is not None
    assert _get_documents_for_author(author.id) == []


def test_upload_empty_file_returns_error():
    response = _upload("Empty Uploader", "empty.docx", io.BytesIO(b""))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Trouble reading document. Not .docx"


def test_upload_corrupted_docx_returns_error():
    response = _upload(
        "Corrupt Uploader",
        "corrupt.docx",
        io.BytesIO(b"PK\x03\x04not a real docx package"),
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Trouble reading document. Not .docx"


def test_upload_validates_content_not_just_extension(make_docx_upload):
    """A real .docx uploaded with a misleading filename should still succeed."""
    _, fileobj, _ = make_docx_upload(filename="whatever.txt")

    response = _upload("Extension Mismatch", "whatever.txt", fileobj, content_type="text/plain")

    assert response.status_code == status.HTTP_200_OK
    author = _get_author_by_name("Extension Mismatch")
    assert len(_get_documents_for_author(author.id)) == 1


def test_upload_missing_file_returns_422():
    response = client.post("/documents/upload", params={"author_name": "No File"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_upload_missing_author_name_returns_422(make_docx_upload):
    filename, fileobj, _ = make_docx_upload()

    response = client.post(
        "/documents/upload",
        files={"file": (filename, fileobj, DOCX_CONTENT_TYPE)},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
