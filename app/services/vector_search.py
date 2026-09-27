from sqlalchemy import select

from app.models import Document, DocumentChunk
from app.services.embedding_service import create_embedding


def search_similar_chunks(
    db,
    query: str,
    user_id: int,
    limit: int = 3
):
    """
    Search for the most similar document chunks
    belonging to the current user.
    """

    # Convert question into embedding
    query_embedding = create_embedding(query)

    # Calculate cosine distance
    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    # Search only documents belonging to this user
    statement = (
        select(DocumentChunk)
        .join(
            Document,
            DocumentChunk.document_id == Document.id
        )
        .where(Document.user_id == user_id)
        .order_by(distance)
        .limit(limit)
    )

    results = db.execute(
        statement
    ).scalars().all()

    return results