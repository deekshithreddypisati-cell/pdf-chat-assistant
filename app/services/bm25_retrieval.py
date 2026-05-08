from dataclasses import dataclass
from typing import List
import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk

WORD_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> List[str]:
    return WORD_RE.findall((text or "").lower())


@dataclass
class BM25Hit:
    doc_id: str
    page_num: int
    chunk_index: int
    score: float
    preview: str


async def bm25_search(
    db: AsyncSession,
    query: str,
    k: int = 10,
    doc_ids: list[str] | None = None,
):
    stmt = select(DocumentChunk)

    if doc_ids is not None:
        if not doc_ids:
            return []
        stmt = stmt.where(DocumentChunk.doc_id.in_(doc_ids))

    result = await db.execute(stmt)
    chunks = result.scalars().all()

    if not chunks:
        return []

    texts = [c.chunk_text or "" for c in chunks]

    tokenized_corpus = [tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized_corpus)

    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    top_idx = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:k]

    hits = []

    for i in top_idx:
        c = chunks[i]

        hits.append(
            {
                "doc_id": c.doc_id,
                "page_num": c.page_num,
                "chunk_index": c.chunk_index,
                "score": float(scores[i]),
                "preview": (c.chunk_text or "")[:200],
            }
        )

    return hits