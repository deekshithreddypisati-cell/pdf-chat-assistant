from sqlalchemy.ext.asyncio import AsyncSession
from app.services.bm25_retrieval import bm25_search
from app.services.vector_index import vector_search
from app.services.hybrid_retrieval import hybrid_search


async def debug_retrieval(db: AsyncSession, query: str):
    bm25_hits = await bm25_search(db, query=query, k=10)

    vec_objs = await vector_search(db, query=query, k=10)
    vector_hits = [v.__dict__ for v in vec_objs]

    hybrid_hits = await hybrid_search(db, query=query, k=10)

    return {
        "query": query,
        "bm25_hits": bm25_hits,
        "vector_hits": vector_hits,
        "hybrid_hits": hybrid_hits,
    }