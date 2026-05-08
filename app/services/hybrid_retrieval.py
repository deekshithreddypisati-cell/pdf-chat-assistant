from __future__ import annotations
from typing import Dict, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bm25_retrieval import bm25_search
from app.services.vector_index import vector_search


def _rrf_fuse(
    bm25_hits: List[dict],
    vec_hits: List[dict],
    k: int = 60,
) -> List[dict]:
    """
    Reciprocal Rank Fusion:
    score = sum(1 / (k + rank))
    Works even when BM25 and vector scores are on different scales.
    """
    fused: Dict[Tuple[str, int, int], dict] = {}

    # BM25 ranking contribution
    for rank, h in enumerate(bm25_hits, start=1):
        key = (str(h["doc_id"]), int(h["page_num"]), int(h["chunk_index"]))
        if key not in fused:
            fused[key] = {
                "doc_id": key[0],
                "page_num": key[1],
                "chunk_index": key[2],
                "preview": h.get("preview", ""),
                "rrf_score": 0.0,
                "from_bm25_rank": rank,
                "from_vector_rank": None,
            }
        fused[key]["rrf_score"] += 1.0 / (k + rank)

    # Vector ranking contribution
    for rank, h in enumerate(vec_hits, start=1):
        key = (str(h["doc_id"]), int(h["page_num"]), int(h["chunk_index"]))
        if key not in fused:
            fused[key] = {
                "doc_id": key[0],
                "page_num": key[1],
                "chunk_index": key[2],
                "preview": h.get("preview", ""),
                "rrf_score": 0.0,
                "from_bm25_rank": None,
                "from_vector_rank": rank,
            }
        else:
            fused[key]["from_vector_rank"] = rank

        fused[key]["rrf_score"] += 1.0 / (k + rank)

    return sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)


async def hybrid_search(
    db: AsyncSession,
    query: str,
    k: int = 10,
    doc_ids: list[str] | None = None,
):
    bm25_hits = await bm25_search(
        db,
        query=query,
        k=20,
        doc_ids=doc_ids,
    )

    vec_hits_objects = await vector_search(
        db,
        query=query,
        k=20,
        doc_ids=doc_ids,
    )
    vec_hits = [v.__dict__ for v in vec_hits_objects]

    fused = _rrf_fuse(bm25_hits, vec_hits, k=60)
    return fused[:k]