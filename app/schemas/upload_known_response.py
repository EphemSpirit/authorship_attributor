from pydantic import BaseModel

from app.schemas.document_response import DocumentResponse


INVALID_FORMAT_MESSAGE = "Not all files were uploaded. Please make sure each document is a .txt or .docx format"
DUPLICATE_MESSAGE = "Not all files were uploaded. Some documents have already been uploaded for these authors"
INVALID_AND_DUPLICATE_MESSAGE = (
    "Not all files were uploaded. Please make sure each document is a .txt or .docx format "
    "and hasn't already been uploaded for these authors"
)
GENERIC_PARTIAL_MESSAGE = "Not all files were uploaded. See the failed files for details"


def partial_upload_message(has_invalid: bool, has_duplicate: bool) -> str:
    if has_invalid and has_duplicate:
        return INVALID_AND_DUPLICATE_MESSAGE
    if has_invalid:
        return INVALID_FORMAT_MESSAGE
    if has_duplicate:
        return DUPLICATE_MESSAGE
    return GENERIC_PARTIAL_MESSAGE


class FailedUpload(BaseModel):
    filename: str
    detail: str


class UploadKnownResponse(BaseModel):
    uploaded: list[DocumentResponse]
    failed: list[FailedUpload]
    # User-facing summary; only set when some, but not all, files were stored.
    message: str | None = None
