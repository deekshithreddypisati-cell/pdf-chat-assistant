import re
import fitz  # PyMuPDF
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import models

log = logging.getLogger(__name__)

_hyphen_break = re.compile(r"(\w)-\s*\n\s*(\w)")
_ws = re.compile(r"[ \t]+")

def clean_for_retrieval(raw: str) -> str:
    if not raw:
        return ""
    s = raw.replace("\r\n", "\n").replace("\r", "\n")
    s = _hyphen_break.sub(r"\1\2", s)
    s = "\n".join(_ws.sub(" ", line).strip() for line in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s

def extract_pages(pdf_path: str):
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    pages = []

    for i in range(page_count):
        page = doc.load_page(i)
        raw = page.get_text("text") or ""
        clean = clean_for_retrieval(raw)
        is_empty = (len(clean.strip()) == 0)

        pages.append({
            "page_num": i + 1,
            "raw_text": raw,
            "clean_text": clean,
            "is_empty": is_empty,
            "char_count": len(clean),
        })

    doc.close()
    return page_count, pages

async def run_extraction_for_doc(db: AsyncSession, doc_id: str) -> dict:
    res = await db.execute(select(models.Document).where(models.Document.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise ValueError("Document not found")

    page_count, pages = extract_pages(doc.storage_path)

    # Quality gate
    if len(pages) != page_count:
        raise RuntimeError(f"Page mismatch: got {len(pages)} expected {page_count}")

    empty_pages = [p["page_num"] for p in pages if p["is_empty"]]
    if empty_pages:
        log.warning("Empty pages for doc_id=%s: %s", doc_id, empty_pages)

    # upsert pages
    for p in pages:
        q = select(models.DocumentPage).where(
            models.DocumentPage.doc_id == doc_id,
            models.DocumentPage.page_num == p["page_num"],
        )
        row_res = await db.execute(q)
        row = row_res.scalar_one_or_none()

        if row is None:
            row = models.DocumentPage(doc_id=doc_id, page_num=p["page_num"])
            db.add(row)

        row.raw_text = p["raw_text"]
        row.clean_text = p["clean_text"]
        row.is_empty = p["is_empty"]
        row.char_count = p["char_count"]

    await db.commit()

    return {
        "doc_id": doc_id,
        "doc_name": doc.filename,
        "pdf_page_count": page_count,
        "stored_pages": len(pages),
        "empty_pages": empty_pages,
        "empty_count": len(empty_pages),
        "ok": True,
    }
