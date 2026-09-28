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
    Retrieve the most relevant document chunks
    for the user's question.
    """

    db = state["db"]

    results = search_similar_chunks(
        db,
        state["question"],
        user_id=state["user_id"],
        limit=5
    )

    context_parts = []
    sources = []

    for result in results:

        context_parts.append(
            result.content
        )

        sources.append(
            {
                "chunk_id": result.id,
                "document_id": result.document_id
            }
        )

    return {
        "context": "\n\n--- DOCUMENT PASSAGE ---\n\n".join(
            context_parts
        ),
        "sources": sources
    }


def generate(state: RAGState):
    """
    Generate the final answer using only
    the retrieved document information.
    """

    prompt = f"""
You are an AI Knowledge Assistant.

Answer the user's COMPLETE question using ONLY the
information in the document passages below.

USER QUESTION:
{state["question"]}

DOCUMENT PASSAGES:
{state["context"]}

IMPORTANT:

- Answer every part of the user's question.
- If the user asks about two concepts, explain BOTH concepts.
- If the user asks for a difference, explain BOTH concepts
  and then clearly explain their difference.
- Use information from multiple passages when necessary.
- Do not answer only one part of the question.
- Do not invent information.
- Do not mention RAG, retrieval, chunks, vector search,
  or internal system processes.
- Do not start with "Based on the provided documents".
- Use simple and clear language.
- Preserve important technical terminology.

For a comparison question, use this structure:

Concept 1:
Explain the first concept.

Concept 2:
Explain the second concept.

Difference:
Explain the difference between them.

If there is not enough information in the document passages,
say:

"I could not find enough information in the provided documents."

Now write the complete answer.

USER QUESTION:
{state["question"]}

DOCUMENT PASSAGES:
{state["context"]}
"""

    answer = generate_with_langchain(
        prompt
    )

    return {
        "answer": answer
    }


# --------------------------------------------------
# Build LangGraph RAG workflow
# --------------------------------------------------

builder = StateGraph(RAGState)

builder.add_node(
    "retrieve",
    retrieve
)

builder.add_node(
    "generate",
    generate
)

builder.add_edge(
    START,
    "retrieve"
)

builder.add_edge(
    "retrieve",
    "generate"
)

builder.add_edge(
    "generate",
    END
)

rag_graph = builder.compile()