from datetime import datetime

from pydantic import BaseModel

from app.schemas.author_summary import AuthorSummary


class DocumentResponse(BaseModel):
    id: int
    authors: list[AuthorSummary]
    filename: str
    content_hash: str
    text: str
    word_count: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "authors": [{"id": 1, "name": "Stephen King"}],
                "filename": "sample.docx",
                "content_hash": "3f786850e387550fdab836ed7e6dc881de23001b",
                "text": "This is a sample document",
                "word_count": 5,
                "status": "pending",
                "error_message": None,
                "created_at": "2026-07-21T17:25:46.221560"
            }
        }
    }
