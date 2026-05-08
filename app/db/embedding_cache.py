from app.db.embedding_cache import EmbeddingCache
from sqlalchemy import Column, String, Text
from app.db.session import Base


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    cache_key = Column(String, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    vector = Column(Text, nullable=False)