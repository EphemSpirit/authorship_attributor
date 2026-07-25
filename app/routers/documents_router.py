from fastapi import APIRouter, UploadFile, File, Depends, status
from app.extensions import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from app.models.author import Author
import docx
import hashlib

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

# this route is for author registration. User uploads a file and provides the author name
# Author is then created in the DB for further stylometric analysis
@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_document_known_author(db: Annotated[Session, Depends(get_db)], file: UploadFile, author_name: str):
    # ingest the file
    # try/except:
    # # create author record and insert it into the database
    # # if intergrity error, return an error hash

    # after author is created, create the Document record in the database
    # doc = docx.Document(file.filename)
    # doc_text = "".join([para.text for para in doc.paragraphs])
    # Document(
    #     author_id=new_author.id,
    #     filename=file.filename,
    #     text=doc_text,
    #     word_count=len(doc_text),
    #     content_hash=hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
    # )


