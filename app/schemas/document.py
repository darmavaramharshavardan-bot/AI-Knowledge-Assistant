from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: int
    filename: str
    chunks_created: int