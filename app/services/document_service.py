from pathlib import Path

from pypdf import PdfReader

from app.services.embedding_service import create_embedding
from app.models import Document, DocumentChunk


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF."""

    reader = PdfReader(file_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n".join(pages)


def split_text(text: str, chunk_size: int = 500) -> list[str]:
    """Split text into simple chunks."""

    words = text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])

        if chunk.strip():
            chunks.append(chunk)

    return chunks


def ingest_pdf(
    db,
    file_path: str,
    user_id: int
):
    """Read PDF, create chunks and store embeddings."""

    filename = Path(file_path).name

    # Create document record
    document = Document(
        filename=filename,
        user_id=user_id
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # Extract PDF text
    text = extract_text_from_pdf(file_path)

    # Split text into chunks
    chunks = split_text(text)

    # Create and store embeddings
    for chunk_text in chunks:

        embedding = create_embedding(chunk_text)

        chunk = DocumentChunk(
            document_id=document.id,
            content=chunk_text,
            embedding=embedding
        )

        db.add(chunk)

    db.commit()

    return {
        "document_id": document.id,
        "filename": filename,
        "chunks_created": len(chunks)
    }