from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    documents = relationship(
        "Document",
        back_populates="owner"
    )

    conversations = relationship(
        "Conversation",
        back_populates="user"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    filename = Column(
        String,
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    owner = relationship(
        "User",
        back_populates="documents"
    )

    chunks = relationship(
        "DocumentChunk",
        back_populates="document"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    embedding = Column(
        Vector(768)
    )

    # ==========================================
    # IMPROVED METADATA
    # ==========================================

    # PDF page where this chunk came from
    page_number = Column(
        Integer,
        nullable=True
    )

    # Section or heading associated with the chunk
    section = Column(
        String,
        nullable=True
    )

    # Type of content
    # Examples:
    # technical_content
    # heading
    # figure_caption
    # reference
    # general_content
    chunk_type = Column(
        String,
        nullable=True
    )

    # Original PDF filename
    source = Column(
        String,
        nullable=True
    )

    document = relationship(
        "Document",
        back_populates="chunks"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="conversations"
    )

    messages = relationship(
        "Message",
        back_populates="conversation"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False
    )

    role = Column(
        String,
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )