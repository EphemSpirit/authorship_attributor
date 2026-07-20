from pydantic import BaseModel, Field
from typing import Optional

class AuthorRequest(BaseModel):
    id: Optional[int] = None
    name: str = Field(min_length=1)
    author_metadata: dict = Field()


    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "name": "Stephen King",
                "author_metadata": {
                    "bio": "He was a man",
                    "age": 65
                }
            }
        }
    }