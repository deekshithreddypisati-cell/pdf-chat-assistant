from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import faiss
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk


MODEL_NAME = "hashing-vectorizer"
VECTOR_DIM = 384

_vectorizer = HashingVectorizer(
    n_features=VECTOR_DIM,
    alternate_sign=False,
    norm=None,
    lowercase=True,
    ngram_range=(1, 2),
)

_cached_index = None
_cached_chunks = None


@dataclass
class VectorHit:
    doc_id: str
    page_num: int
    chunk_index: int
    score: float
    preview: str


def _encode_texts(texts: list[str]) -> np.ndarray:
    """
    Lightweight embedding replacement for Render free tier.
    Converts text into normalized hashing vectors.
    """
    if not texts:
        return np.zeros((0, VECTOR_DIM), dtype="float32")

    matrix = _vectorizer.transform(texts)
    matrix = normalize(matrix, norm="l2", axis=1)
    return matrix.astype("float32").toarray()


def clear_vector_cache():
    global _cached_index, _cached_chunks
    _cached_index = None
    _cached_chunks = None


async def build_faiss_index(
    db: AsyncSession,
    doc_ids: list[str] | None = None,
):
    stmt = select(DocumentChunk)

    if doc_ids is not None:
        if not doc_ids:
            return None, []

        stmt = stmt.where(DocumentChunk.doc_id.in_(doc_ids))

    res = await db.execute(stmt)
    chunks = res.scalars().all()

    if not chunks:
        return None, []

    texts = [c.chunk_text or "" for c in chunks]
    emb = _encode_texts(texts)

    if emb.shape[0] == 0:
        return None, []

    d = emb.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(emb)

    return index, chunks


async def vector_search(
    db: AsyncSession,
    query: str,
    k: int = 10,
    doc_ids: list[str] | None = None,
) -> List[VectorHit]:
    global _cached_index, _cached_chunks

    if doc_ids is not None:
        index, chunks = await build_faiss_index(db, doc_ids=doc_ids)
    else:
        if _cached_index is None or _cached_chunks is None:
            _cached_index, _cached_chunks = await build_faiss_index(db)

        index, chunks = _cached_index, _cached_chunks

    if index is None:
        return []

    q_emb = _encode_texts([query])

    scores, ids = index.search(q_emb, k)
    scores = scores[0]
    ids = ids[0]

    hits: List[VectorHit] = []

    for score, idx in zip(scores, ids):
        if idx == -1:
            continue

        c = chunks[int(idx)]

        hits.append(
            VectorHit(
                doc_id=str(c.doc_id),
                page_num=int(c.page_num),
                chunk_index=int(c.chunk_index),
                score=float(score),
                preview=(c.chunk_text[:220] if c.chunk_text else ""),
            )
        )

    return hits