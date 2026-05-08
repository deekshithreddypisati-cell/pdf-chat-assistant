import os
import uuid
from pathlib import Path


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def save_pdf(upload_dir: str, workspace_id: str, filename: str, content: bytes):
    doc_id = str(uuid.uuid4())
    safe_name = filename.replace("/", "_").replace("\\", "_")

    folder = os.path.join(upload_dir, workspace_id)
    ensure_dir(folder)

    path = os.path.join(folder, f"{doc_id}_{safe_name}")

    with open(path, "wb") as f:
        f.write(content)

    return doc_id, path


def delete_file(path: str) -> bool:
    try:
        if path and os.path.exists(path):
            os.remove(path)
            return True
        return False
    except Exception:
        return False