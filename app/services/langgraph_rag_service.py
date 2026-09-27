from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.services.vector_search import search_similar_chunks
from app.services.langchain_service import generate_with_langchain


class RAGState(TypedDict):
    question: str
    user_id: int
    context: str
    answer: str
    sources: list
    db: object


def retrieve(state: RAGState):
    """
    Retrieve relevant chunks belonging only
    to the current user.
    """

    db = state["db"]

    results = search_similar_chunks(
        db,
        state["question"],
        user_id=state["user_id"],
        limit=3
    )

    context_parts = []
    sources = []

    for result in results:
        context_parts.append(result.content)

        sources.append({
            "chunk_id": result.id,
            "document_id": result.document_id
        })

    return {
        "context": "\n\n---\n\n".join(context_parts),
        "sources": sources
    }


def generate(state: RAGState):
    """
    Generate an answer using only the retrieved context.
    """

    prompt = f"""
You are a knowledge assistant.

Answer the question using ONLY the provided context.

If the answer is not present in the context,
say that you could not find the answer in the provided documents.

Context:
{state["context"]}

Question:
{state["question"]}

Answer:
"""

    answer = generate_with_langchain(prompt)

    return {
        "answer": answer
    }


# Create LangGraph workflow
builder = StateGraph(RAGState)

builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

rag_graph = builder.compile()