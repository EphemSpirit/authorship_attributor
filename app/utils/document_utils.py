import hashlib
import io
from pathlib import Path
from zipfile import BadZipFile

import docx
from docx.opc.exceptions import PackageNotFoundError
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.document import Document


async def parse_document_upload(file: UploadFile) -> tuple[str, int, str]:
    extension = Path(file.filename or "").suffix.lower()
    file_bytes = await file.read()

    if extension == ".docx":
        doc_text = _parse_docx_bytes(file_bytes)
    elif extension == ".txt":
        doc_text = _parse_txt_bytes(file_bytes)
    else:
        raise HTTPException(status_code=422, detail="Unsupported file type. Must be .docx or .txt")

    word_count = len(doc_text.split())
    content_hash = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()

    return doc_text, word_count, content_hash


def _parse_docx_bytes(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return " ".join([para.text for para in doc.paragraphs])
    except (PackageNotFoundError, BadZipFile):
        raise HTTPException(status_code=422, detail="Trouble reading document. Not .docx")


def _parse_txt_bytes(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Trouble reading document. Not valid .txt")


def find_document_by_content_hash(db: Session, content_hash: str) -> Document | None:
    return db.query(Document).filter(Document.content_hash == content_hash).first()


def add_new_authors_to_document(db: Session, document: Document, authors: list[Author]) -> Document:
    new_authors = [author for author in authors if author not in document.authors]
    if not new_authors:
        raise HTTPException(status_code=422, detail="Document already exists for these authors")

    document.authors.extend(new_authors)
    db.commit()
    db.refresh(document)
    return document
