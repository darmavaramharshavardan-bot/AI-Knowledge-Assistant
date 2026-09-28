from sqlalchemy import select

from app.models import Document, DocumentChunk
from app.services.embedding_service import create_embedding


def normalize_text(text: str) -> str:
    return " ".join(
        (text or "").lower().split()
    )


def is_corrupted_chunk(chunk) -> bool:
    content = normalize_text(chunk.content)

    corrupted_markers = [
        "<eos>",
        "<bos>",
        "<pad>",
        "the law will never be perfect",
    ]

    return any(
        marker in content
        for marker in corrupted_markers
    )


def is_reference_chunk(chunk) -> bool:
    chunk_type = (
        chunk.chunk_type or ""
    ).lower()

    content = normalize_text(chunk.content)

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


def is_caption_chunk(chunk) -> bool:
    chunk_type = (
        chunk.chunk_type or ""
    ).lower()

    return chunk_type in {
        "figure_caption",
        "table_caption",
    }


def is_weak_chunk(chunk) -> bool:
    content = normalize_text(chunk.content)

    if len(content.split()) < 30:
        return True

    if is_corrupted_chunk(chunk):
        return True

    if is_reference_chunk(chunk):
        return True

    return False


def content_type_score(chunk) -> int:
    chunk_type = (
        chunk.chunk_type or ""
    ).lower()

    if chunk_type == "technical_content":
        return 20

    if chunk_type == "heading":
        return 10

    if chunk_type == "figure_caption":
        return -10

    if chunk_type == "table_caption":
        return -15

    return 0


def keyword_score(
    query: str,
    content: str
) -> int:

    query_text = normalize_text(query)
    content_text = normalize_text(content)

    score = 0

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

    if query_text in content_text:
        score += 10

    return score


def concept_score(
    query: str,
    content: str
) -> int:

    query_text = normalize_text(query)
    content_text = normalize_text(content)

    score = 0

    concepts = [
        [
            "self-attention",
            "self attention",
        ],
        [
            "multi-head attention",
            "multi head attention",
        ],
        [
            "scaled dot-product attention",
            "scaled dot product attention",
        ],
    ]

    for concept in concepts:

        query_contains = any(
            phrase in query_text
            for phrase in concept
        )

        content_contains = any(
            phrase in content_text
            for phrase in concept
        )

        if query_contains and content_contains:
            score += 20

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


def extract_concepts(query: str) -> list[str]:

    query_text = normalize_text(query)

    concepts = []

    if (
        "self-attention" in query_text
        or "self attention" in query_text
    ):
        concepts.append(
            "self-attention"
        )

    if (
        "multi-head attention" in query_text
        or "multi head attention" in query_text
    ):
        concepts.append(
            "multi-head attention"
        )

    return concepts


def retrieve_for_query(
    db,
    query: str,
    user_id: int,
    candidate_limit: int = 50
):

    embedding = create_embedding(
        query
    )

    distance = (
        DocumentChunk.embedding.cosine_distance(
            embedding
        )
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

    return (
        db.execute(statement)
        .scalars()
        .all()
    )


def search_similar_chunks(
    db,
    query: str,
    user_id: int,
    limit: int = 6
):
    """
    Multi-query RAG retrieval.

    For comparison questions, retrieve each
    important concept independently and then
    merge the results.
    """

    concepts = extract_concepts(
        query
    )

    search_queries = [query]

    for concept in concepts:
        if concept not in search_queries:
            search_queries.append(
                concept
            )

    all_candidates = []

    for search_query in search_queries:

        candidates = retrieve_for_query(
            db,
            search_query,
            user_id,
            candidate_limit=50
        )

        for vector_rank, chunk in enumerate(
            candidates
        ):

            if is_weak_chunk(chunk):
                continue

            all_candidates.append(
                {
                    "chunk": chunk,
                    "query": search_query,
                    "vector_rank": vector_rank,
                }
            )

    # Remove duplicate chunks while preserving
    # their best retrieval rank.
    unique_candidates = {}

    for item in all_candidates:

        chunk = item["chunk"]

        if chunk.id not in unique_candidates:
            unique_candidates[chunk.id] = item
            continue

        if (
            item["vector_rank"]
            < unique_candidates[
                chunk.id
            ]["vector_rank"]
        ):
            unique_candidates[
                chunk.id
            ] = item

    ranked = []

    for item in unique_candidates.values():

        chunk = item["chunk"]
        search_query = item["query"]
        vector_rank = item["vector_rank"]

        keyword_boost = keyword_score(
            search_query,
            chunk.content
        )

        concept_boost = concept_score(
            query,
            chunk.content
        )

        type_boost = content_type_score(
            chunk
        )

        # Strongly reward concept-specific
        # retrieval and technical content.
        score = (
            keyword_boost * 5
            + concept_boost * 4
            + type_boost * 2
            - vector_rank
        )

        ranked.append(
            (
                score,
                vector_rank,
                chunk
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1]
        )
    )

    selected = []

    # First select technical content only.
    for _, _, chunk in ranked:

        if is_caption_chunk(chunk):
            continue

        if is_duplicate(
            chunk,
            selected
        ):
            continue

        selected.append(chunk)

        if len(selected) >= limit:
            break

    # Fallback if fewer than `limit` technical
    # chunks are available.
    if len(selected) < limit:

        for _, _, chunk in ranked:

            if is_duplicate(
                chunk,
                selected
            ):
                continue

            selected.append(chunk)

            if len(selected) >= limit:
                break

    return selected