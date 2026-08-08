import hashlib
import io

import docx
from docx.opc.exceptions import PackageNotFoundError
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from zipfile import BadZipFile

from app.models.author import Author
from app.models.document import Document


async def parse_docx_upload(file: UploadFile) -> tuple[str, int, str]:
    try:
        file_bytes = await file.read()
        doc = docx.Document(io.BytesIO(file_bytes))
        doc_text = " ".join([para.text for para in doc.paragraphs])
        word_count = sum(len(para.text.split()) for para in doc.paragraphs)
        content_hash = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
    except (PackageNotFoundError, BadZipFile):
        raise HTTPException(status_code=422, detail="Trouble reading document. Not .docx")

    return doc_text, word_count, content_hash


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
