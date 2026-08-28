import hashlib
import io

from fastapi import status
from sqlalchemy.orm import joinedload

from app.extensions import get_db
from app.models import Author, AuthorStyleProfile, Document
from test.fixtures.authors import test_author
from test.fixtures.document import make_docx_upload, make_txt_upload, test_document
from test.utils import TestingSessionLocal, app, client, override_get_db

app.dependency_overrides[get_db] = override_get_db

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(author_names, filename, fileobj, content_type=DOCX_CONTENT_TYPE):
    if isinstance(author_names, str):
        author_names = [author_names]
    return client.post(
        "/documents/upload-known",
        params={"author_names": author_names},
        files={"file": (filename, fileobj, content_type)},
    )


def _upload_disputed(filename, fileobj, content_type=DOCX_CONTENT_TYPE):
    return client.post(
        "/documents/upload-disputed",
        files={"document": (filename, fileobj, content_type)},
    )


def _get_author_by_name(name):
    db = TestingSessionLocal()
    try:
        return db.query(Author).filter(Author.name == name.title()).first()
    finally:
        db.close()


def _get_documents_for_author(author_id):
    db = TestingSessionLocal()
    try:
        author = db.get(Author, author_id)
        return list(author.documents) if author else []
    finally:
        db.close()


def _get_style_profiles_for_author(author_id):
    db = TestingSessionLocal()
    try:
        return (
            db.query(AuthorStyleProfile)
            .options(joinedload(AuthorStyleProfile.features))
            .filter(AuthorStyleProfile.author_id == author_id)
            .all()
        )
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


def test_upload_triggers_a_style_profile_rebuild_for_the_author(make_docx_upload):
    filename, fileobj, _ = make_docx_upload(
        paragraphs=["The quick brown fox jumps over the lazy dog."], filename="fox.docx"
    )

    response = _upload("Style Profile Author", filename, fileobj)

    assert response.status_code == status.HTTP_200_OK

    author = _get_author_by_name("Style Profile Author")
    profiles = _get_style_profiles_for_author(author.id)

    assert len(profiles) == 1
    assert profiles[0].model_version == "v1"
    assert profiles[0].num_documents_used == 1
    assert {feature.feature_type for feature in profiles[0].features} == {
        "function_word_freq", "avg_sentence_length", "vocabulary_richness",
    }


def test_uploading_a_second_document_increments_the_authors_model_version(make_docx_upload):
    first_filename, first_fileobj, _ = make_docx_upload(
        paragraphs=["First document content."], filename="first.docx"
    )
    second_filename, second_fileobj, _ = make_docx_upload(
        paragraphs=["Second document, different content."], filename="second.docx"
    )

    _upload("Revision Author", first_filename, first_fileobj)
    _upload("Revision Author", second_filename, second_fileobj)

    author = _get_author_by_name("Revision Author")
    profiles = _get_style_profiles_for_author(author.id)

    assert sorted(profile.model_version for profile in profiles) == ["v1", "v2"]


def test_upload_titlecases_new_author_name(make_docx_upload):
    filename, fileobj, _ = make_docx_upload()

    response = _upload("stephen king", filename, fileobj)

    assert response.status_code == status.HTTP_200_OK
    assert _get_author_by_name("Stephen King") is not None


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


def test_upload_same_author_with_docx_and_txt_associates_both_documents(make_docx_upload, make_txt_upload):
    docx_filename, docx_fileobj, _ = make_docx_upload(
        paragraphs=["First document content."], filename="first.docx"
    )
    txt_filename, txt_fileobj, _ = make_txt_upload(
        text="Second document, different content.", filename="second.txt"
    )

    docx_response = _upload("Jane Austen", docx_filename, docx_fileobj)
    txt_response = _upload("Jane Austen", txt_filename, txt_fileobj)

    assert docx_response.status_code == status.HTTP_200_OK
    assert txt_response.status_code == status.HTTP_200_OK

    author = _get_author_by_name("Jane Austen")
    documents = _get_documents_for_author(author.id)
    assert {document.filename for document in documents} == {"first.docx", "second.txt"}


def test_upload_duplicate_content_for_same_author_returns_error(make_docx_upload):
    first_filename, first_fileobj, _ = make_docx_upload(filename="first.docx")
    second_filename, second_fileobj, _ = make_docx_upload(filename="second.docx")

    first_response = _upload("Charles Dickens", first_filename, first_fileobj)
    assert first_response.status_code == status.HTTP_200_OK

    second_response = _upload("Charles Dickens", second_filename, second_fileobj)
    assert second_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert second_response.json()["detail"] == "Document already exists for these authors"

    author = _get_author_by_name("Charles Dickens")
    assert len(_get_documents_for_author(author.id)) == 1


def test_upload_same_filename_different_content_for_same_author_creates_two_documents(make_docx_upload):
    """Filename is no longer part of the uniqueness key: only content_hash is,
    since the same file content might legitimately be credited to a different
    set of authors later. Two genuinely different documents that happen to
    share a filename are both kept."""
    first_filename, first_fileobj, _ = make_docx_upload(
        paragraphs=["First version of the document."], filename="report.docx"
    )
    second_filename, second_fileobj, _ = make_docx_upload(
        paragraphs=["A different, revised version of the document."], filename="report.docx"
    )

    first_response = _upload("Charlotte Bronte", first_filename, first_fileobj)
    assert first_response.status_code == status.HTTP_200_OK

    second_response = _upload("Charlotte Bronte", second_filename, second_fileobj)
    assert second_response.status_code == status.HTTP_200_OK

    author = _get_author_by_name("Charlotte Bronte")
    assert len(_get_documents_for_author(author.id)) == 2


def test_upload_with_multiple_authors_links_document_to_all_of_them(make_docx_upload):
    filename, fileobj, _ = make_docx_upload(paragraphs=["A jointly written paper."], filename="paper.docx")

    response = _upload(["Jane Doe", "John Smith"], filename, fileobj)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert {author["name"] for author in body["authors"]} == {"Jane Doe", "John Smith"}

    jane = _get_author_by_name("Jane Doe")
    john = _get_author_by_name("John Smith")
    assert len(_get_documents_for_author(jane.id)) == 1
    assert len(_get_documents_for_author(john.id)) == 1
    assert _get_documents_for_author(jane.id)[0].id == _get_documents_for_author(john.id)[0].id


def test_uploading_same_content_with_a_new_author_adds_them_to_existing_document(make_docx_upload):
    filename, fileobj, _ = make_docx_upload(paragraphs=["Shared content."], filename="paper.docx")
    second_filename, second_fileobj, _ = make_docx_upload(paragraphs=["Shared content."], filename="paper.docx")

    first_response = _upload("Jane Doe", filename, fileobj)
    assert first_response.status_code == status.HTTP_200_OK
    first_document_id = first_response.json()["id"]

    second_response = _upload(["Jane Doe", "John Smith"], second_filename, second_fileobj)
    assert second_response.status_code == status.HTTP_200_OK
    body = second_response.json()

    assert body["id"] == first_document_id
    assert {author["name"] for author in body["authors"]} == {"Jane Doe", "John Smith"}


def test_upload_unsupported_file_type_returns_error():
    response = _upload(
        "Someone New",
        "notes.pdf",
        io.BytesIO(b"This is not a docx or txt file."),
        content_type="application/pdf",
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Unsupported file type. Must be .docx or .txt"


def test_upload_unsupported_file_type_still_creates_author_but_no_document():
    _upload(
        "Someone New",
        "notes.pdf",
        io.BytesIO(b"This is not a docx or txt file."),
        content_type="application/pdf",
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


def test_upload_extension_determines_parser_not_content(make_docx_upload):
    """The file extension picks the parser, regardless of the actual bytes or Content-Type header.
    A real .docx uploaded with a .txt filename is parsed as text and rejected as invalid UTF-8."""
    _, fileobj, _ = make_docx_upload(filename="whatever.txt")

    response = _upload("Extension Mismatch", "whatever.txt", fileobj, content_type="text/plain")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Trouble reading document. Not valid .txt"


def test_upload_txt_file_creates_document(make_txt_upload):
    filename, fileobj, _ = make_txt_upload(text="Hello world, this is a sample document.", filename="sample.txt")

    response = _upload("Txt Author", filename, fileobj, content_type="text/plain")

    assert response.status_code == status.HTTP_200_OK
    author = _get_author_by_name("Txt Author")
    documents = _get_documents_for_author(author.id)
    assert len(documents) == 1
    assert documents[0].filename == "sample.txt"
    assert documents[0].text == "Hello world, this is a sample document."
    assert documents[0].word_count == 7


def test_upload_missing_file_returns_422():
    response = client.post("/documents/upload-known", params={"author_names": ["No File"]})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_upload_missing_author_names_returns_422(make_docx_upload):
    filename, fileobj, _ = make_docx_upload()

    response = client.post(
        "/documents/upload-known",
        files={"file": (filename, fileobj, DOCX_CONTENT_TYPE)},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_get_document(test_document: Document):
    response = client.get(f"/documents/{test_document.filename}")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == test_document.id
    assert {author["id"] for author in body["authors"]} == {author.id for author in test_document.authors}
    assert body["filename"] == test_document.filename
    assert body["content_hash"] == test_document.content_hash
    assert body["text"] == test_document.text
    assert body["word_count"] == test_document.word_count
    assert body["status"] == test_document.status


def test_get_document_not_found():
    response = client.get("/documents/does-not-exist.docx")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Document not found."


def test_upload_disputed_returns_the_closer_matching_author(make_docx_upload):
    terse_filename, terse_fileobj, _ = make_docx_upload(
        paragraphs=["I go. I see. I win."], filename="terse.docx"
    )
    verbose_filename, verbose_fileobj, _ = make_docx_upload(
        paragraphs=["Subsequently, following considerable deliberation, one might reasonably "
                    "conclude that the outcome was, in fact, favorable."],
        filename="verbose.docx",
    )
    _upload("Terse Author", terse_filename, terse_fileobj)
    _upload("Verbose Author", verbose_filename, verbose_fileobj)

    disputed_filename, disputed_fileobj, _ = make_docx_upload(
        paragraphs=["I run. I jump. I win."], filename="disputed.docx"
    )
    response = _upload_disputed(disputed_filename, disputed_fileobj)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    candidates = body["candidates"]
    assert candidates[0]["author"]["name"] == "Terse Author"
    assert 0 < candidates[0]["confidence_score"] <= 1
    assert [c["confidence_score"] for c in candidates] == sorted(
        (c["confidence_score"] for c in candidates), reverse=True
    )


def test_upload_disputed_requires_at_least_two_author_profiles(make_docx_upload):
    filename, fileobj, _ = make_docx_upload(paragraphs=["Solo author's only document."], filename="solo.docx")
    _upload("Solo Author", filename, fileobj)

    disputed_filename, disputed_fileobj, _ = make_docx_upload(
        paragraphs=["Some disputed text."], filename="disputed.docx"
    )
    response = _upload_disputed(disputed_filename, disputed_fileobj)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_upload_disputed_unsupported_file_type_returns_error():
    response = _upload_disputed("notes.pdf", io.BytesIO(b"This is not a docx or txt file."), content_type="application/pdf")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"] == "Unsupported file type. Must be .docx or .txt"
