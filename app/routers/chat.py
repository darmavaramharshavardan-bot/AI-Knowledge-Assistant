from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.schemas.chat import ChatRequest
from app.models import Conversation, Message, Document
from app.services.auth_service import get_current_user
from app.services.langgraph_rag_service import rag_graph


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# ============================================================
# RUN LANGGRAPH RAG
# ============================================================

def run_rag(
    db: Session,
    question: str,
    user_id: int
):
    """
    Run the existing LangGraph RAG pipeline.
    """

    result = rag_graph.invoke(
        {
            "question": question,
            "user_id": user_id,
            "context": "",
            "answer": "",
            "sources": [],
            "db": db
        }
    )

    return result


# ============================================================
# NORMAL CHAT
# ============================================================

@router.post("")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Normal non-streaming chat endpoint.
    """

    user_id = current_user

    # --------------------------------------------------------
    # Find existing conversation
    # --------------------------------------------------------

    conversation = None

    if request.conversation_id:

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user_id
            )
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

    # --------------------------------------------------------
    # Create new conversation
    # --------------------------------------------------------

    else:

        conversation = Conversation(
            user_id=user_id
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()

    # --------------------------------------------------------
    # Run LangGraph RAG
    # --------------------------------------------------------

    result = run_rag(
        db=db,
        question=request.message,
        user_id=user_id
    )

    answer = result.get(
        "answer",
        ""
    )

    sources = result.get(
        "sources",
        []
    )

    # --------------------------------------------------------
    # Build detailed sources
    # --------------------------------------------------------

    detailed_sources = []

    for source in sources:

        chunk_id = source.get(
            "chunk_id"
        )

        document_id = source.get(
            "document_id"
        )

        # Find document
        document = (
            db.query(Document)
            .filter(
                Document.id == document_id
            )
            .first()
        )

        # Find chunk
        from app.models import DocumentChunk

        chunk = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.id == chunk_id
            )
            .first()
        )

        detailed_sources.append(
            {
                "chunk_id": chunk_id,

                "document_id": document_id,

                "filename": (
                    document.filename
                    if document
                    else None
                ),

                "page_number": (
                    chunk.page_number
                    if chunk
                    else None
                ),

                "section": (
                    chunk.section
                    if chunk
                    else None
                ),

                "chunk_type": (
                    chunk.chunk_type
                    if chunk
                    else None
                ),

                "source": (
                    chunk.source
                    if chunk
                    else None
                )
            }
        )

    # --------------------------------------------------------
    # Save assistant message
    # --------------------------------------------------------

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer
    )

    db.add(assistant_message)
    db.commit()

    return {
        "answer": answer,
        "sources": detailed_sources,
        "conversation_id": conversation.id
    }


# ============================================================
# STREAMING CHAT
# ============================================================

@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    SSE chat endpoint.

    The RAG generation itself is completed first,
    then the answer and source information are
    sent through SSE.
    """

    user_id = current_user

    # --------------------------------------------------------
    # Find existing conversation
    # --------------------------------------------------------

    conversation = None

    if request.conversation_id:

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user_id
            )
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

    # --------------------------------------------------------
    # Create conversation
    # --------------------------------------------------------

    else:

        conversation = Conversation(
            user_id=user_id
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()

    # --------------------------------------------------------
    # Run existing LangGraph RAG
    # --------------------------------------------------------

    result = run_rag(
        db=db,
        question=request.message,
        user_id=user_id
    )

    answer = result.get(
        "answer",
        ""
    )

    sources = result.get(
        "sources",
        []
    )

    # --------------------------------------------------------
    # Build detailed sources
    # --------------------------------------------------------

    detailed_sources = []

    from app.models import DocumentChunk

    for source in sources:

        chunk_id = source.get(
            "chunk_id"
        )

        document_id = source.get(
            "document_id"
        )

        document = (
            db.query(Document)
            .filter(
                Document.id == document_id
            )
            .first()
        )

        chunk = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.id == chunk_id
            )
            .first()
        )

        detailed_sources.append(
            {
                "chunk_id": chunk_id,

                "document_id": document_id,

                "filename": (
                    document.filename
                    if document
                    else None
                ),

                "page_number": (
                    chunk.page_number
                    if chunk
                    else None
                ),

                "section": (
                    chunk.section
                    if chunk
                    else None
                ),

                "chunk_type": (
                    chunk.chunk_type
                    if chunk
                    else None
                ),

                "source": (
                    chunk.source
                    if chunk
                    else None
                )
            }
        )

    # --------------------------------------------------------
    # Save assistant message
    # --------------------------------------------------------

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer
    )

    db.add(assistant_message)
    db.commit()

    # ========================================================
    # SSE EVENT STREAM
    # ========================================================

    def event_stream():

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        yield (
            "event: start\n"
            "data: Generating answer...\n\n"
        )

        # ----------------------------------------------------
        # ANSWER
        # ----------------------------------------------------

        yield (
            "event: answer\n"
            f"data: {answer}\n\n"
        )

        # ----------------------------------------------------
        # SOURCES
        # ----------------------------------------------------

        yield (
            "event: sources\n"
            f"data: {json.dumps(detailed_sources)}\n\n"
        )

        # ----------------------------------------------------
        # CONVERSATION
        # ----------------------------------------------------

        yield (
            "event: conversation\n"
            f"data: {conversation.id}\n\n"
        )

        # ----------------------------------------------------
        # DONE
        # ----------------------------------------------------

        yield (
            "event: done\n"
            "data: complete\n\n"
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )