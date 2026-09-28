from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.schemas.chat import ChatRequest
from app.models import Conversation, Message, Document, DocumentChunk
from app.services.auth_service import get_current_user
from app.services.langgraph_rag_service import rag_graph


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


def run_rag(
    db: Session,
    question: str,
    user_id: int
):
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


def get_detailed_sources(
    db: Session,
    sources: list
):
    detailed_sources = []

    for source in sources:

        chunk_id = source.get("chunk_id")
        document_id = source.get("document_id")

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

    return detailed_sources


@router.post("")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = current_user

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

    else:

        conversation = Conversation(
            user_id=user_id
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()

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

    detailed_sources = get_detailed_sources(
        db,
        sources
    )

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


@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = current_user

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

    else:

        conversation = Conversation(
            user_id=user_id
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()

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

    detailed_sources = get_detailed_sources(
        db,
        sources
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer
    )

    db.add(assistant_message)
    db.commit()

    conversation_id = conversation.id

    def event_stream():

        # Start event
        yield (
            "event: start\n"
            "data: Generating answer...\n\n"
        )

        # Answer event
        #
        # SSE requires every line of a multi-line
        # message to start with "data:".
        answer_lines = answer.splitlines()

        yield "event: answer\n"

        for line in answer_lines:
            yield f"data: {line}\n"

        yield "\n"

        # Sources event
        yield (
            "event: sources\n"
            f"data: {json.dumps(detailed_sources)}\n\n"
        )

        # Conversation event
        yield (
            "event: conversation\n"
            f"data: {conversation_id}\n\n"
        )

        # Complete event
        yield (
            "event: done\n"
            "data: complete\n\n"
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )