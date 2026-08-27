from pydantic import BaseModel

from app.schemas.author_summary import AuthorSummary


class CandidateAuthorScore(BaseModel):
    author: AuthorSummary
    confidence_score: float


class DisputedDocumentResponse(BaseModel):
    candidates: list[CandidateAuthorScore]