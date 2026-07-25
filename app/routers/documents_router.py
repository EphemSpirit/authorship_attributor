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

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_document_known_author(db: Annotated[Session, Depends(get_db)], file: UploadFile, author_name: str):
    try:
        new_author = Author(name=author_name.title())
        db.add(new_author)
        db.commit()
    except IntegrityError:
        return {"error": "Author already exists"}

    try:
        doc = docx.Document(file.filename)
        doc_text = " ".join([para.text for para in doc.paragraphs])
        word_count = sum(len(para.text.split()) for para in doc.paragraphs)
        new_document = Document(
            author_id=new_author.id,
            filename=file.filename,
            text=doc_text,
            word_count=word_count,
            content_hash=hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
        )

        db.add(new_document)
        db.commit()
    except PackageNotFoundError:
        return {"error": "Trouble reading document"}



