from fastapi import APIRouter, BackgroundTasks, UploadFile, Depends, HTTPException, Path, Query, Response, status
from app.extensions import get_db
from sqlalchemy.orm import Session
from typing import Annotated
from app.models.document import Document
from app.schemas.author_summary import AuthorSummary
from app.schemas.disputed_document_response import CandidateAuthorScore, DisputedDocumentResponse
from app.schemas.document_response import DocumentResponse
from app.schemas.upload_known_response import FailedUpload, UploadKnownResponse, partial_upload_message
from app.services.author_attribution_service import AuthorAttributionService
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.style_profile_service import StyleProfileService
from app.services.style_profile_rebuild_service import StyleProfileRebuildService
from app.utils.author_utils import get_or_create_author
from app.utils.document_utils import (
    DuplicateDocumentError,
    InvalidDocumentError,
    parse_document_upload,
    store_known_document,
)

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


@router.post("/upload-known", response_model=UploadKnownResponse)
async def upload_document_known_author(
        db: Annotated[Session, Depends(get_db)],
        background_tasks: BackgroundTasks,
        response: Response,
        files: list[UploadFile],
        author_names: Annotated[list[str], Query()]
):
    """Each file is processed and committed independently, so one bad file
    doesn't sink the rest of the batch. Returns 200 if at least one file was
    stored, 422 if every file failed; the body has the same shape either way."""
    if not author_names:
        raise HTTPException(status_code=422, detail="At least one author_name is required")

    authors = [get_or_create_author(db, name) for name in author_names]

    uploaded: list[Document] = []
    failed: list[FailedUpload] = []
    has_invalid = has_duplicate = False

    for file in files:
        try:
            document: Document = await store_known_document(db, file, authors)
            uploaded.append(document)
        except HTTPException as e:
            has_invalid |= isinstance(e, InvalidDocumentError)
            has_duplicate |= isinstance(e, DuplicateDocumentError)
            failed.append(FailedUpload(filename=file.filename or "", detail=str(e.detail)))

    if uploaded:
        # One rebuild covers every document in the batch.
        background_tasks.add_task(StyleProfileRebuildService(StyleProfileService()).rebuild_all_in_background)
    else:
        response.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    return UploadKnownResponse(
        uploaded=[DocumentResponse.model_validate(document) for document in uploaded],
        failed=failed,
        message=partial_upload_message(has_invalid, has_duplicate) if uploaded and failed else None,
    )


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
