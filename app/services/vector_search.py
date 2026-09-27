from sqlalchemy import select

from app.models import Document, DocumentChunk
from app.services.embedding_service import create_embedding


def normalize_text(text: str) -> str:
    return " ".join(
        (text or "").lower().split()
    )


def is_corrupted_chunk(chunk) -> bool:
    content = normalize_text(
        chunk.content
    )

    corrupted_markers = [
        "<eos>",
        "<bos>",
        "<pad>",
        "the law will never be perfect",
    ]

    for marker in corrupted_markers:
        if marker in content:
            return True

    return False


def is_reference_chunk(chunk) -> bool:
    chunk_type = (
        chunk.chunk_type or ""
    ).lower()

    content = normalize_text(
        chunk.content
    )

    if chunk_type == "reference":
        return True

    if content.startswith("["):
        return True

    reference_indicators = [
        "arxiv preprint",
        "proceedings of",
        "international conference on learning representations",
    ]

    return any(
        indicator in content
        for indicator in reference_indicators
    )


def is_weak_chunk(chunk) -> bool:
    content = normalize_text(
        chunk.content
    )

    if len(content.split()) < 30:
        return True

    if is_corrupted_chunk(chunk):
        return True

    if is_reference_chunk(chunk):
        return True

    return False


def keyword_score(
    query: str,
    content: str
) -> int:

    query_text = normalize_text(query)
    content_text = normalize_text(content)

    score = 0

    # Exact phrase match gets a strong boost.
    if query_text in content_text:
        score += 10

    # Important individual terms.
    query_words = {
        word
        for word in query_text.split()
        if len(word) >= 4
    }

    content_words = set(
        content_text.split()
    )

    score += len(
        query_words.intersection(
            content_words
        )
    )

    return score


def is_duplicate(
    chunk,
    selected_chunks
) -> bool:

    current = normalize_text(
        chunk.content
    )

    current_words = set(
        current.split()
    )

    if not current_words:
        return True

    for selected in selected_chunks:

        selected_text = normalize_text(
            selected.content
        )

        selected_words = set(
            selected_text.split()
        )

        if not selected_words:
            continue

        overlap = (
            len(
                current_words.intersection(
                    selected_words
                )
            )
            / min(
                len(current_words),
                len(selected_words)
            )
        )

        if overlap >= 0.80:
            return True

    return False


def search_similar_chunks(
    db,
    query: str,
    user_id: int,
    limit: int = 6
):
    """
    Retrieve relevant, clean and diverse
    chunks for the current user.
    """

    query_embedding = create_embedding(
        query
    )

    distance = (
        DocumentChunk.embedding.cosine_distance(
            query_embedding
        )
    )

    candidate_limit = max(
        limit * 5,
        30
    )

    statement = (
        select(DocumentChunk)
        .join(
            Document,
            DocumentChunk.document_id
            == Document.id
        )
        .where(
            Document.user_id == user_id
        )
        .order_by(
            distance
        )
        .limit(
            candidate_limit
        )
    )

    candidates = (
        db.execute(statement)
        .scalars()
        .all()
    )

    # Remove bad candidates while
    # preserving vector-search order.
    clean_candidates = [
        chunk
        for chunk in candidates
        if not is_weak_chunk(chunk)
    ]

    # Give keyword matches a small boost,
    # but keep vector similarity important.
    ranked_candidates = []

    for vector_rank, chunk in enumerate(
        clean_candidates
    ):

        keyword_boost = keyword_score(
            query,
            chunk.content
        )

        ranking_score = (
            keyword_boost * 5
            - vector_rank
        )

        ranked_candidates.append(
            (
                ranking_score,
                vector_rank,
                chunk
            )
        )

    ranked_candidates.sort(
        key=lambda item: (
            -item[0],
            item[1]
        )
    )

    selected = []

    for _, _, chunk in ranked_candidates:

        if is_duplicate(
            chunk,
            selected
        ):
            continue

        selected.append(chunk)

        if len(selected) >= limit:
            break

    return selected