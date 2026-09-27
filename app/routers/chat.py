from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import json

from app.database import get_db
from app.schemas.chat import ChatRequest
from app.models import Conversation, Message

from app.services.rag_service import answer_question
from app.services.auth_service import get_current_user
from app.services.vector_search import search_similar_chunks
from app.services.llm_service import generate_answer_stream
from app.services.redis_service import get_cache, set_cache


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# ============================================================
# GET OR CREATE CONVERSATION
# ============================================================

def get_or_create_conversation(
    db: Session,
    user_id: int,
    conversation_id: int | None
):
    """
    Get an existing conversation belonging to the user,
    or create a new conversation.
    """

    # Existing conversation
    if conversation_id is not None:

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

        return conversation

    # Create new conversation
    conversation = Conversation(
        user_id=user_id
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


# ============================================================
# NORMAL CHAT
# ============================================================

@router.post("")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    Normal RAG chat endpoint with conversation history.
    """

    # 1. Get or create conversation
    conversation = get_or_create_conversation(
        db=db,
        user_id=user_id,
        conversation_id=request.conversation_id
    )

    # 2. Save user's message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()

    # 3. Generate RAG answer
    result = answer_question(
        db,
        request.message,
        user_id
    )

    # 4. Save assistant's answer
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["answer"]
    )

    db.add(assistant_message)
    db.commit()

    # 5. Return response
    return {
        "conversation_id": conversation.id,
        "question": request.message,
        "answer": result["answer"],
        "sources": result["sources"]
    }


# ============================================================
# SSE STREAMING CHAT
# ============================================================

@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    Stream the RAG answer using Server-Sent Events.

    Features:
    - JWT authentication
    - User-specific documents
    - Conversation history
    - Redis caching
    - Gemini streaming
    - Sources
    """

    # --------------------------------------------------------
    # 1. Get or create conversation
    # --------------------------------------------------------

    conversation = get_or_create_conversation(
        db=db,
        user_id=user_id,
        conversation_id=request.conversation_id
    )

    # --------------------------------------------------------
    # 2. Save user message
    # --------------------------------------------------------

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()

    # --------------------------------------------------------
    # 3. Create user-specific Redis cache key
    # --------------------------------------------------------

    cache_key = f"rag:user:{user_id}:{request.message}"

    cached_data = get_cache(cache_key)

    # ========================================================
    # CACHE HIT
    # ========================================================

    if cached_data:

        cached = json.loads(cached_data)

        cached_answer = cached["answer"]
        cached_sources = cached["sources"]

        def cached_generator():

            yield "event: start\n"
            yield "data: Loading cached answer...\n\n"

            # Send cached answer
            yield "event: answer\n"
            yield f"data: {cached_answer}\n\n"

            # Send sources
            yield "event: sources\n"
            yield f"data: {json.dumps(cached_sources)}\n\n"

            # Send conversation ID
            yield "event: conversation\n"
            yield f"data: {conversation.id}\n\n"

            # Save assistant message
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=cached_answer
            )

            db.add(assistant_message)
            db.commit()

            # Finished
            yield "event: done\n"
            yield "data: complete\n\n"

        return StreamingResponse(
            cached_generator(),
            media_type="text/event-stream"
        )

    # ========================================================
    # CACHE MISS
    # ========================================================

    # --------------------------------------------------------
    # 4. Search user's documents
    # --------------------------------------------------------

    results = search_similar_chunks(
        db,
        request.message,
        user_id=user_id,
        limit=3
    )

    # --------------------------------------------------------
    # 5. No relevant documents
    # --------------------------------------------------------

    if not results:

        assistant_text = (
            "I could not find relevant information "
            "in your documents."
        )

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_text
        )

        db.add(assistant_message)
        db.commit()

        def no_results():

            yield "event: answer\n"
            yield f"data: {assistant_text}\n\n"

            yield "event: sources\n"
            yield "data: []\n\n"

            yield "event: conversation\n"
            yield f"data: {conversation.id}\n\n"

            yield "event: done\n"
            yield "data: complete\n\n"

        return StreamingResponse(
            no_results(),
            media_type="text/event-stream"
        )

    # --------------------------------------------------------
    # 6. Build RAG context
    # --------------------------------------------------------

    context_parts = []

    for result in results:
        context_parts.append(result.content)

    context = "\n\n---\n\n".join(
        context_parts
    )

    # --------------------------------------------------------
    # 7. Create Gemini prompt
    # --------------------------------------------------------

    prompt = f"""
You are a knowledge assistant.

Answer the user's question using ONLY the provided context.

If the answer is not present in the context,
say that you could not find the answer in the provided documents.

Context:
{context}

Question:
{request.message}

Answer:
"""

    # --------------------------------------------------------
    # 8. Streaming generator
    # --------------------------------------------------------

    def event_generator():

        full_answer = ""

        # Start event
        yield "event: start\n"
        yield "data: Generating answer...\n\n"

        # ----------------------------------------------------
        # Stream Gemini response
        # ----------------------------------------------------

        for chunk in generate_answer_stream(prompt):

            full_answer += chunk

            yield "event: answer\n"
            yield f"data: {chunk}\n\n"

        # ----------------------------------------------------
        # Create sources
        # ----------------------------------------------------

        sources = [
            {
                "chunk_id": result.id,
                "document_id": result.document_id
            }
            for result in results
        ]

        # ----------------------------------------------------
        # Save assistant message
        # ----------------------------------------------------

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_answer
        )

        db.add(assistant_message)
        db.commit()

        # ----------------------------------------------------
        # Save complete response in Redis
        # ----------------------------------------------------

        response_data = {
            "answer": full_answer,
            "sources": sources
        }

        set_cache(
            cache_key,
            json.dumps(response_data),
            expire=3600
        )

        # ----------------------------------------------------
        # Send sources
        # ----------------------------------------------------

        yield "event: sources\n"
        yield f"data: {json.dumps(sources)}\n\n"

        # ----------------------------------------------------
        # Send conversation ID
        # ----------------------------------------------------

        yield "event: conversation\n"
        yield f"data: {conversation.id}\n\n"

        # ----------------------------------------------------
        # Finished
        # ----------------------------------------------------

        yield "event: done\n"
        yield "data: complete\n\n"

    # --------------------------------------------------------
    # Return SSE response
    # --------------------------------------------------------

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )