from datetime import datetime

from pydantic import BaseModel, Field


class AuthorStyleProfileResponse(BaseModel):
    id: int
    author_id: int
    feature_type: str
    profile_vector: list[float]
    feature_names: list[str]
    num_documents_used: int
    model_version: str
    computed_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "author_id": 1,
                "feature_type": "function_word_freq",
                "profile_vector": [0.021, 0.104, 0.0087],
                "feature_names": ["the", "of", "and"],
                "num_documents_used": 12,
                "model_version": "v1",
                "computed_at": "2026-07-21T17:25:46.221560"
            }
        }
    }
