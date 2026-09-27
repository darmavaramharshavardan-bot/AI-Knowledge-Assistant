from app.services.vector_search import search_similar_chunks
from app.services.langchain_service import generate_with_langchain


def answer_question_with_langchain(
    db,
    question: str,
    user_id: int
):
    """
    Answer a question using:
    vector search + LangChain + Gemini.

    Only the current user's documents are searched.
    """

    # 1. Retrieve relevant chunks
    results = search_similar_chunks(
        db,
        question,
        user_id=user_id,
        limit=3
    )

    # 2. No relevant information
    if not results:
        return {
            "answer": (
                "I could not find relevant information "
                "in your documents."
            ),
            "sources": []
        }

    # 3. Build context
    context_parts = []

    for result in results:
        context_parts.append(result.content)

    context = "\n\n---\n\n".join(context_parts)

    # 4. Create prompt
    prompt = f"""
You are a knowledge assistant.

Answer the question using ONLY the provided context.

If the answer is not present in the context,
say that you could not find the answer in the provided documents.

Context:
{context}

Question:
{question}

Answer:
"""

    # 5. Generate answer through LangChain
    answer = generate_with_langchain(prompt)

    # 6. Create sources
    sources = [
        {
            "chunk_id": result.id,
            "document_id": result.document_id
        }
        for result in results
    ]

    # 7. Return answer and sources
    return {
        "answer": answer,
        "sources": sources
    }