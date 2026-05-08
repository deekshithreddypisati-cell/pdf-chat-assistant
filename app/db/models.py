import uuid

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Column,
    Text,
    DateTime,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String, nullable=False)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="uploaded")


class DocumentPage(Base):
    __tablename__ = "doc_pages"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True, nullable=False)
    page_num = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)
    clean_text = Column(Text, nullable=True)
    is_empty = Column(Boolean, nullable=False, default=False)
    char_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("doc_id", "page_num", name="uq_doc_page"),
    )


class DocumentChunk(Base):
    __tablename__ = "doc_chunks"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True, nullable=False)
    page_num = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    char_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("doc_id", "page_num", "chunk_index", name="uq_doc_chunk"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    cache_key = Column(String, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    vector = Column(Text, nullable=False)