from pydantic import BaseModel


class AuthorStyleFeatureResponse(BaseModel):
    id: int
    feature_type: str
    profile_vector: list[float]
    feature_names: list[str]

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "feature_type": "function_word_freq",
                "profile_vector": [0.021, 0.104, 0.0087],
                "feature_names": ["the", "of", "and"],
            }
        }
    }
