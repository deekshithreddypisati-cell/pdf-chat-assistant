from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import models


def split_into_chunks(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    if not text:
        return []

    s = text.strip()
    if not s:
        return []

    out = []
    i = 0
    n = len(s)

    while i < n:
        j = min(i + chunk_size, n)
        out.append(s[i:j].strip())

        if j == n:
            break

        i = max(0, j - overlap)

    return [c for c in out if c]


async def chunk_document(db: AsyncSession, doc_id: str) -> dict:
    # Load all pages
    res = await db.execute(
        select(models.DocumentPage)
        .where(models.DocumentPage.doc_id == doc_id)
        .order_by(models.DocumentPage.page_num.asc())
    )
    pages = list(res.scalars())

    if not pages:
        raise ValueError("No extracted pages found. Run /documents/{doc_id}/extract first.")

    total_chunks = 0

    for page in pages:
        chunks = split_into_chunks(page.clean_text, chunk_size=800, overlap=150)

        for idx, chunk_text in enumerate(chunks):
            q = select(models.DocumentChunk).where(
                models.DocumentChunk.doc_id == doc_id,
                models.DocumentChunk.page_num == page.page_num,
                models.DocumentChunk.chunk_index == idx,
            )
            existing = (await db.execute(q)).scalar_one_or_none()

            if existing is None:
                existing = models.DocumentChunk(
                    doc_id=doc_id,
                    page_num=page.page_num,
                    chunk_index=idx,
                )
                db.add(existing)

            existing.chunk_text = chunk_text
            existing.char_count = len(chunk_text)

        total_chunks += len(chunks)

    await db.commit()

    return {
        "doc_id": doc_id,
        "pages": len(pages),
        "total_chunks": total_chunks,
        "ok": True
    }
