from datetime import datetime

from pydantic import BaseModel

from app.schemas.author_style_feature_response import AuthorStyleFeatureResponse


class AuthorStyleProfileResponse(BaseModel):
    id: int
    author_id: int
    num_documents_used: int
    model_version: str
    computed_at: datetime
    features: list[AuthorStyleFeatureResponse]

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "author_id": 1,
                "num_documents_used": 12,
                "model_version": "v1",
                "computed_at": "2026-07-21T17:25:46.221560",
                "features": [
                    {
                        "id": 1,
                        "feature_type": "function_word_freq",
                        "profile_vector": [0.021, 0.104, 0.0087],
                        "feature_names": ["the", "of", "and"]
                    },
                    {
                        "id": 2,
                        "feature_type": "avg_sentence_length",
                        "profile_vector": [18.4],
                        "feature_names": ["avg_sentence_length"]
                    }
                ]
            }
        }
    }
