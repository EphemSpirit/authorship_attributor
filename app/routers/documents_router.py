from fastapi import APIRouter, BackgroundTasks, UploadFile, Depends, HTTPException, Path, Query, status
from app.extensions import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from app.models.document import Document
from app.schemas.author_summary import AuthorSummary
from app.schemas.disputed_document_response import CandidateAuthorScore, DisputedDocumentResponse
from app.schemas.document_response import DocumentResponse
from app.services.author_attribution_service import AuthorAttributionService
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.style_profile_service import StyleProfileService
from app.services.style_profile_rebuild_service import StyleProfileRebuildService
from app.utils.author_utils import get_or_create_author
from app.utils.document_utils import add_new_authors_to_document, find_document_by_content_hash, parse_document_upload

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


@router.get("/{document_name}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
async def get_document(db: Annotated[Session, Depends(get_db)], document_name: str = Path(min_length=1)):
    document = db.query(Document).filter(Document.filename == document_name).first()

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return document


@router.post("/upload-known", response_model=DocumentResponse)
async def upload_document_known_author(
        db: Annotated[Session, Depends(get_db)],
        background_tasks: BackgroundTasks,
        file: UploadFile,
        author_names: Annotated[list[str], Query()]
):
    if not author_names:
        raise HTTPException(status_code=422, detail="At least one author_name is required")

    authors = [get_or_create_author(db, name) for name in author_names]

    doc_text, word_count, content_hash = await parse_document_upload(file)

    existing_document = find_document_by_content_hash(db, content_hash)

    if existing_document is not None:
        existing_document = add_new_authors_to_document(db, existing_document, authors)
        background_tasks.add_task(StyleProfileRebuildService(StyleProfileService()).rebuild_all_in_background)
        return existing_document

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
        background_tasks.add_task(StyleProfileRebuildService(StyleProfileService()).rebuild_all_in_background)
        return new_document
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=422, detail="Document already exists for these authors")


@router.post("/upload-disputed", response_model=DisputedDocumentResponse)
async def upload_disputed(
        db: Annotated[Session, Depends(get_db)],
        document: UploadFile,
):
    doc_text, _word_count, _content_hash = await parse_document_upload(document)

    try:
        attribution_service = AuthorAttributionService(DocumentAnalysisService(StyleProfileService()))
        ranked_candidates = attribution_service.attribute(db, doc_text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return DisputedDocumentResponse(
        candidates=[
            CandidateAuthorScore(
                author=AuthorSummary.model_validate(author),
                confidence_score=confidence_score,
            )
            for author, confidence_score in ranked_candidates
        ],
    )
