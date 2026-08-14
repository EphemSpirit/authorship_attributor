from pydantic import BaseModel

from app.schemas.author_summary import AuthorSummary

class DisputedDocumentResponse(BaseModel):
    predicted_author: AuthorSummary
    confidence_score: float