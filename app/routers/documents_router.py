from fastapi import APIRouter, UploadFile, File, Depends, status
from app.extensions import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from app.models.author import Author
from app.models.document import Document
import docx
from docx.opc.exceptions import PackageNotFoundError
import hashlib
import io
import zipfile

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_document_known_author(db: Annotated[Session, Depends(get_db)], file: UploadFile, author_name: str):
    title_cased_name = author_name.title()
    try:
        author = Author(name=title_cased_name)
        db.add(author)
        db.commit()
    except IntegrityError:
        db.rollback()
        author = db.query(Author).filter(Author.name == title_cased_name).first()

    try:
        file_bytes = await file.read()
        doc = docx.Document(io.BytesIO(file_bytes))
        doc_text = " ".join([para.text for para in doc.paragraphs])
        word_count = sum(len(para.text.split()) for para in doc.paragraphs)
        new_document = Document(
            author_id=author.id,
            filename=file.filename,
            text=doc_text,
            word_count=word_count,
            content_hash=hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
        )

        db.add(new_document)
        db.commit()
    except (PackageNotFoundError, zipfile.BadZipFile):
        return {"error": "Trouble reading document. Not .docx"}
    except IntegrityError:
        db.rollback()
        return {"error": "Document already exists for this author"}



