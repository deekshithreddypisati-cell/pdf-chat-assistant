from __future__ import annotations
from dataclasses import dataclass
from typing import List

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk
from app.services.cache_service import CacheService
from app.utils.hashing import embedding_cache_key


# Embedding model
MODEL_NAME = "all-MiniLM-L6-v2"
_model = SentenceTransformer(MODEL_NAME)

# In-memory FAISS cache for global search only
_cached_index = None
_cached_chunks = None


@dataclass
class VectorHit:
    doc_id: str
    page_num: int
    chunk_index: int
    score: float
    preview: str


def clear_vector_cache():
    """
    Clears in-memory FAISS cache.
    Call this after uploading new PDFs / new chunks.
    """
    global _cached_index, _cached_chunks
    _cached_index = None
    _cached_chunks = None


async def build_faiss_index(
    db: AsyncSession,
    doc_ids: list[str] | None = None,
):
    """
    Builds FAISS index from chunks.
    Uses embedding cache table so vectors are not recomputed.
    If doc_ids is provided, only those documents are indexed.
    """
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

    results = [None] * len(texts)
    missing_texts = []
    missing_indices = []
    missing_keys = []

    # Check embedding cache first
    for i, text in enumerate(texts):
        key = embedding_cache_key(MODEL_NAME, text)
        cached_vector = await CacheService.get_embedding(db, key)

        if cached_vector is not None:
            results[i] = cached_vector
        else:
            missing_texts.append(text)
            missing_indices.append(i)
            missing_keys.append(key)

    # Compute only missing embeddings
    if missing_texts:
        new_vectors = _model.encode(missing_texts, normalize_embeddings=True)
        new_vectors = np.asarray(new_vectors, dtype="float32")

        for idx, key, text, vector in zip(
            missing_indices, missing_keys, missing_texts, new_vectors
        ):
            vector_list = vector.tolist()

            await CacheService.set_embedding(
                db=db,
                cache_key=key,
                model_name=MODEL_NAME,
                text=text,
                vector=vector_list,
            )

            results[idx] = vector_list

    emb = np.asarray(results, dtype="float32")

    d = emb.shape[1]
    index = faiss.IndexFlatIP(d)  # cosine similarity because normalized
    index.add(emb)

    return index, chunks


async def vector_search(
    db: AsyncSession,
    query: str,
    k: int = 10,
    doc_ids: list[str] | None = None,
) -> List[VectorHit]:
    """
    Vector search with optional workspace/doc filtering.

    - If doc_ids is None: reuse global in-memory FAISS cache
    - If doc_ids is provided: build a filtered index for only those docs
    """
    global _cached_index, _cached_chunks

    if doc_ids is not None:
        index, chunks = await build_faiss_index(db, doc_ids=doc_ids)
    else:
        if _cached_index is None or _cached_chunks is None:
            _cached_index, _cached_chunks = await build_faiss_index(db)

        index, chunks = _cached_index, _cached_chunks

    if index is None:
        return []

    q_emb = _model.encode([query], normalize_embeddings=True)
    q_emb = np.asarray(q_emb, dtype="float32")

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