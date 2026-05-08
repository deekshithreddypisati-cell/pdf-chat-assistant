import asyncio
from app.db.session import AsyncSessionLocal
from app.services.cache_service import CacheService


async def main():
    print("Starting cache test...")

    async with AsyncSessionLocal() as db:
        key = "test_key_123"
        vector = [0.1, 0.2, 0.3]

        await CacheService.set_embedding(
            db=db,
            cache_key=key,
            model_name="text-embedding-3-small",
            text="hello world",
            vector=vector,
        )

        cached = await CacheService.get_embedding(db, key)
        print("Cached vector:", cached)


if __name__ == "__main__":
    asyncio.run(main())