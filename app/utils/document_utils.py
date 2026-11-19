import hashlib
import io
from pathlib import Path
from zipfile import BadZipFile

import docx
from docx.opc.exceptions import PackageNotFoundError
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.document import Document
from app.services.style_profile_service import StyleProfileService


class InvalidDocumentError(HTTPException):
    """The upload isn't a supported, readable .docx or .txt file."""
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)


class DuplicateDocumentError(HTTPException):
    """This exact content is already credited to every requested author."""
    def __init__(self):
        super().__init__(status_code=422, detail="Document already exists for these authors")


async def parse_document_upload(file: UploadFile) -> tuple[str, int, str]:
    extension = Path(file.filename or "").suffix.lower()
    file_bytes = await file.read()

    if extension == ".docx":
        doc_text = _parse_docx_bytes(file_bytes)
    elif extension == ".txt":
        doc_text = _parse_txt_bytes(file_bytes)
    else:
        raise InvalidDocumentError("Unsupported file type. Must be .docx or .txt")

    word_count = len(doc_text.split())
    content_hash = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()

    return doc_text, word_count, content_hash


def _parse_docx_bytes(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return " ".join([para.text for para in doc.paragraphs])
    except (PackageNotFoundError, BadZipFile):
        raise InvalidDocumentError("Trouble reading document. Not .docx")


def _parse_txt_bytes(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidDocumentError("Trouble reading document. Not valid .txt")


def find_document_by_content_hash(db: Session, content_hash: str) -> Document | None:
    return db.query(Document).filter(Document.content_hash == content_hash).first()


def add_new_authors_to_document(db: Session, document: Document, authors: list[Author]) -> Document:
    new_authors = [author for author in authors if author not in document.authors]
    if not new_authors:
        raise DuplicateDocumentError()

    document.authors.extend(new_authors)
    db.commit()
    db.refresh(document)
    return document


async def store_known_document(db: Session, file: UploadFile, authors: list[Author]) -> Document:
    """Parses and persists one uploaded file credited to authors. If identical
    content already exists, the authors are added to that document instead.
    Raises InvalidDocumentError if the file can't be parsed, or
    DuplicateDocumentError if it's already credited to all of these authors."""
    doc_text, word_count, content_hash = await parse_document_upload(file)

    existing_document = find_document_by_content_hash(db, content_hash)

    if existing_document is not None:
        return add_new_authors_to_document(db, existing_document, authors)

    document_stats = StyleProfileService().compute_document_stats(doc_text)

    try:
        new_document = Document(
            filename=file.filename,
            text=doc_text,
            word_count=word_count,
            content_hash=content_hash,
            authors=authors,
            **document_stats,
        )

        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        return new_document
    except IntegrityError:
        db.rollback()
        raise DuplicateDocumentError()
