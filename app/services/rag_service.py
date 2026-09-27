import json

from app.services.vector_search import search_similar_chunks
from app.services.llm_service import generate_answer
from app.services.redis_service import get_cache, set_cache


def answer_question(
    db,
    question: str,
    user_id: int
):
    """
    Answer a question using the current user's documents.
    Redis caches both the answer and its sources.
    """

    # Create a user-specific cache key
    cache_key = f"rag:user:{user_id}:{question}"

    # 1. Check Redis cache
    cached_data = get_cache(cache_key)

    if cached_data:

        print("CACHE HIT")

        return json.loads(cached_data)

    print("CACHE MISS")

    # 2. Search only the current user's documents
    results = search_similar_chunks(
        db,
        question,
        user_id=user_id,
        limit=3
    )

    # 3. If nothing is found
    if not results:
        return {
            "answer": "I could not find relevant information in your documents.",
            "sources": []
        }

    # 4. Combine retrieved chunks
    context_parts = []

    for result in results:
        context_parts.append(result.content)

    context = "\n\n---\n\n".join(context_parts)

    # 5. Create Gemini prompt
    prompt = f"""
You are a knowledge assistant.

Answer the user's question using ONLY the provided context.

If the answer is not present in the context,
say that you could not find the answer in the provided documents.

Context:
{context}

Question:
{question}

Answer:
"""

    # 6. Generate answer
    answer = generate_answer(prompt)

    # 7. Create sources
    sources = [
        {
            "chunk_id": result.id,
            "document_id": result.document_id
        }
        for result in results
    ]

    # 8. Create complete response
    response_data = {
        "answer": answer,
        "sources": sources
    }

    # 9. Save answer + sources in Redis
    set_cache(
        cache_key,
        json.dumps(response_data),
        expire=3600
    )

    return response_data 