import json

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Workspace,
    Document,
    DocumentPage,
    DocumentChunk,
    ChatMessage,
)


async def create_workspace(db: AsyncSession, name: str) -> Workspace:
    ws = Workspace(name=name)
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


async def get_workspace(db: AsyncSession, workspace_id: str):
    res = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    return res.scalar_one_or_none()


async def count_docs(db: AsyncSession, workspace_id: str) -> int:
    res = await db.execute(
        select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
    )
    return int(res.scalar_one())


async def add_document(
    db: AsyncSession,
    workspace_id: str,
    filename: str,
    storage_path: str,
):
    doc = Document(
        workspace_id=workspace_id,
        filename=filename,
        storage_path=storage_path,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_documents(db: AsyncSession, workspace_id: str):
    res = await db.execute(
        select(Document).where(Document.workspace_id == workspace_id)
    )
    return list(res.scalars())


async def get_document(db: AsyncSession, doc_id: str):
    res = await db.execute(select(Document).where(Document.id == doc_id))
    return res.scalar_one_or_none()


async def get_pages_for_doc(db: AsyncSession, doc_id: str):
    res = await db.execute(
        select(DocumentPage)
        .where(DocumentPage.doc_id == doc_id)
        .order_by(DocumentPage.page_num.asc())
    )
    return list(res.scalars())


async def get_page(db: AsyncSession, doc_id: str, page_num: int):
    res = await db.execute(
        select(DocumentPage)
        .where(
            DocumentPage.doc_id == doc_id,
            DocumentPage.page_num == page_num,
        )
    )
    return res.scalar_one_or_none()


async def add_chat_message(
    db: AsyncSession,
    workspace_id: str,
    role: str,
    content: str,
    citations=None,
):
    msg = ChatMessage(
        workspace_id=workspace_id,
        role=role,
        content=content,
        citations_json=json.dumps(citations) if citations is not None else None,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_recent_chat_messages(db: AsyncSession, workspace_id: str, limit: int = 6):
    res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.workspace_id == workspace_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    msgs = list(res.scalars())
    msgs.reverse()  # oldest -> newest
    return msgs


async def delete_document_related_data(db: AsyncSession, doc_id: str):
    await db.execute(
        delete(DocumentPage).where(DocumentPage.doc_id == doc_id)
    )
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.doc_id == doc_id)
    )


async def delete_document(db: AsyncSession, doc_id: str):
    doc = await get_document(db, doc_id)
    if not doc:
        return None

    await delete_document_related_data(db, doc_id)
    await db.delete(doc)
    await db.commit()
    return doc