from pydantic import BaseModel, Field

from app.schemas.author_style_profile_response import AuthorStyleProfileResponse


class AuthorResponse(BaseModel):
    id: int
    name: str
    author_metadata: dict
    style_profiles: list[AuthorStyleProfileResponse] = Field(default_factory=list)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Stephen King",
                "author_metadata": {
                    "bio": "He was a man",
                    "age": 65
                },
                "style_profiles": [
                    {
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
                            }
                        ]
                    }
                ]
            }
        }
    }
