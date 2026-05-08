import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmbeddingCache


class CacheService:
    @staticmethod
    async def get_embedding(db: AsyncSession, cache_key: str):
        result = await db.execute(
            select(EmbeddingCache).where(EmbeddingCache.cache_key == cache_key)
        )
        row = result.scalar_one_or_none()

        if not row:
            return None

        return json.loads(row.vector)

    @staticmethod
    async def set_embedding(
        db: AsyncSession,
        cache_key: str,
        model_name: str,
        text: str,
        vector,
    ):
        existing = await db.execute(
            select(EmbeddingCache).where(EmbeddingCache.cache_key == cache_key)
        )
        existing_row = existing.scalar_one_or_none()

        if existing_row:
            return existing_row

        row = EmbeddingCache(
            cache_key=cache_key,
            model_name=model_name,
            text=text,
            vector=json.dumps(vector),
        )

        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row