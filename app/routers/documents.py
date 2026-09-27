from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import get_current_user
from app.services.document_service import ingest_pdf


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    Upload a PDF for the authenticated user.
    """

    # 1. Check file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # 2. Create a temporary file path
    temp_file = f"temp_{file.filename}"

    try:
        # 3. Save uploaded file temporarily
        with open(temp_file, "wb") as buffer:
            buffer.write(file.file.read())

        # 4. Ingest PDF
        result = ingest_pdf(
            db=db,
            file_path=temp_file,
            user_id=user_id
        )

        return {
            "message": "Document uploaded successfully",
            "document_id": result["document_id"],
            "filename": file.filename,
            "chunks_created": result["chunks_created"]
        }

    finally:
        # 5. Delete temporary file
        import os

        if os.path.exists(temp_file):
            os.remove(temp_file)