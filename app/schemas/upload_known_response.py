from pydantic import BaseModel

from app.schemas.document_response import DocumentResponse


class FailedUpload(BaseModel):
    filename: str
    detail: str


class UploadKnownResponse(BaseModel):
    uploaded: list[DocumentResponse]
    failed: list[FailedUpload]
