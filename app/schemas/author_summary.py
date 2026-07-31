from pydantic import BaseModel


class AuthorSummary(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Stephen King",
            }
        }
    }
