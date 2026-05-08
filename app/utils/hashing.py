import hashlib

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def embedding_cache_key(model_name: str, chunk_text: str) -> str:
    raw = f"{model_name}::{chunk_text}"
    return sha256_text(raw)