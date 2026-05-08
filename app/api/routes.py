import asyncio
import json

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db import crud, models
from app.core.config import settings

from app.services.storage import save_pdf, delete_file
from app.services.chunking import chunk_document
from app.services.extraction import run_extraction_for_doc
from app.services.bm25_retrieval import bm25_search
from app.services.vector_index import vector_search, clear_vector_cache
from app.services.hybrid_retrieval import hybrid_search
from app.services.answering import ask_strict
from app.services.followup import rewrite_query_with_history
from app.services.debug_retrieval import debug_retrieval

from app.db.crud import (
    get_pages_for_doc,
    get_page,
    add_chat_message,
    get_recent_chat_messages,
)

router = APIRouter()


@router.post("/workspaces")
async def create_workspace(name: str):
    async with AsyncSessionLocal() as db:
        ws = await crud.create_workspace(db, name)
        return {"workspace_id": ws.id, "name": ws.name}


@router.get("/workspaces/{workspace_id}/documents")
async def list_documents(workspace_id: str):
    async with AsyncSessionLocal() as db:
        ws = await crud.get_workspace(db, workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")

        docs = await crud.list_documents(db, workspace_id)
        return [
    {
        "doc_id": d.id,
        "filename": d.filename,
        "storage_path": d.storage_path,
        "page_count": d.page_count,
        "status": d.status,
    }
    for d in docs
]


@router.post("/workspaces/{workspace_id}/upload")
async def upload_pdf(workspace_id: str, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    content = await file.read()

    async with AsyncSessionLocal() as db:
        ws = await crud.get_workspace(db, workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")

        current = await crud.count_docs(db, workspace_id)
        if current >= 10:
            raise HTTPException(
                status_code=400,
                detail="Workspace limit reached (max 10 PDFs)"
            )

        _, path = save_pdf(settings.upload_dir, workspace_id, file.filename, content)
        doc = await crud.add_document(db, workspace_id, file.filename, path)

        clear_vector_cache()

        return {"doc_id": doc.id, "filename": doc.filename}


# -------- Extraction / Chunking --------

@router.post("/documents/{doc_id}/extract")
async def extract_doc_pages(doc_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await run_extraction_for_doc(db, doc_id)

            doc = await db.get(models.Document, doc_id)
            if doc:
                doc.status = "extracted"
                await db.commit()

            return result

        except ValueError as e:
            doc = await db.get(models.Document, doc_id)
            if doc:
                doc.status = "failed"
                await db.commit()

            raise HTTPException(status_code=404, detail=str(e))

        except Exception as e:
            doc = await db.get(models.Document, doc_id)
            if doc:
                doc.status = "failed"
                await db.commit()

            raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/pages")
async def list_doc_pages(doc_id: str):
    async with AsyncSessionLocal() as db:
        pages = await get_pages_for_doc(db, doc_id)
        return [
            {
                "page_num": p.page_num,
                "char_count": p.char_count,
                "is_empty": p.is_empty,
            }
            for p in pages
        ]


@router.get("/documents/{doc_id}/pages/{page_num}")
async def inspect_doc_page(doc_id: str, page_num: int):
    async with AsyncSessionLocal() as db:
        p = await get_page(db, doc_id, page_num)
        if not p:
            raise HTTPException(status_code=404, detail="Page not found")

        return {
            "doc_id": doc_id,
            "page_num": page_num,
            "raw_text": p.raw_text,
            "clean_text": p.clean_text,
        }


@router.post("/documents/{doc_id}/chunk")
async def chunk_doc(doc_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await chunk_document(db, doc_id)

            doc = await db.get(models.Document, doc_id)
            if doc:
                doc.status = "ready"
                await db.commit()

            clear_vector_cache()
            return result

        except ValueError as e:
            doc = await db.get(models.Document, doc_id)
            if doc:
                doc.status = "failed"
                await db.commit()

            raise HTTPException(status_code=400, detail=str(e))

        except Exception as e:
            doc = await db.get(models.Document, doc_id)
            if doc:
                doc.status = "failed"
                await db.commit()

            raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/workspaces")
async def list_workspaces():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.Workspace))
        rows = result.scalars().all()

        return {
            "workspaces": [
                {
                    "id": ws.id,
                    "name": ws.name,
                }
                for ws in rows
            ]
        }

# -------- Workspace keyword search --------

@router.get("/workspaces/{workspace_id}/search")
async def search_workspace(workspace_id: str, q: str):
    async with AsyncSessionLocal() as db:
        docs = await crud.list_documents(db, workspace_id)
        if not docs:
            return []

        doc_ids = [d.id for d in docs]

        res = await db.execute(
            select(models.DocumentChunk)
            .where(models.DocumentChunk.doc_id.in_(doc_ids))
            .where(models.DocumentChunk.chunk_text.ilike(f"%{q}%"))
            .order_by(models.DocumentChunk.char_count.desc())
            .limit(10)
        )
        hits = list(res.scalars())

        return [
            {
                "doc_id": h.doc_id,
                "page_num": h.page_num,
                "chunk_index": h.chunk_index,
                "preview": h.chunk_text[:220],
            }
            for h in hits
        ]


# -------- Retrieval APIs --------

@router.get("/bm25_search")
async def bm25_search_endpoint(
    q: str,
    workspace_id: str | None = None,
):
    async with AsyncSessionLocal() as db:
        doc_ids = None

        if workspace_id is not None:
            docs = await crud.list_documents(db, workspace_id)
            doc_ids = [d.id for d in docs]

        results = await bm25_search(
            db,
            query=q,
            doc_ids=doc_ids,
        )

        return {"query": q, "results": results}


@router.get("/vector_search")
async def vector_search_endpoint(
    q: str,
    k: int = 10,
    workspace_id: str | None = None,
):
    async with AsyncSessionLocal() as db:
        doc_ids = None

        if workspace_id is not None:
            docs = await crud.list_documents(db, workspace_id)
            doc_ids = [d.id for d in docs]

        results = await vector_search(
            db,
            query=q,
            k=k,
            doc_ids=doc_ids,
        )

        return {"query": q, "results": [r.__dict__ for r in results]}


@router.get("/hybrid_search")
async def hybrid_search_endpoint(
    q: str,
    k: int = 10,
    workspace_id: str | None = None,
):
    async with AsyncSessionLocal() as db:
        doc_ids = None

        if workspace_id is not None:
            docs = await crud.list_documents(db, workspace_id)
            doc_ids = [d.id for d in docs]

        results = await hybrid_search(
            db,
            query=q,
            k=k,
            doc_ids=doc_ids,
        )

        return {"query": q, "k": k, "results": results}


# -------- Answer APIs --------

@router.get("/ask")
async def ask_endpoint(
    q: str,
    k: int = 5,
    workspace_id: str | None = None,
):
    async with AsyncSessionLocal() as db:
        return await ask_strict(
            db,
            query=q,
            k=k,
            workspace_id=workspace_id,
        )


@router.get("/chat")
async def chat(
    workspace_id: str,
    q: str,
    k: int = 5,
):
    async with AsyncSessionLocal() as db:
        await add_chat_message(
            db,
            workspace_id=workspace_id,
            role="user",
            content=q,
            citations=None,
        )

        msgs = await get_recent_chat_messages(
            db,
            workspace_id=workspace_id,
            limit=8,
        )
        user_questions = [m.content for m in msgs if m.role == "user"]

        rewritten_q = rewrite_query_with_history(q, user_questions[:-1])

        result = await ask_strict(
            db,
            query=rewritten_q,
            k=k,
            workspace_id=workspace_id,
        )

        await add_chat_message(
            db,
            workspace_id=workspace_id,
            role="assistant",
            content=result.get("answer", ""),
            citations=result.get("citations", []),
        )

        return {
            "workspace_id": workspace_id,
            "original_query": q,
            "rewritten_query": rewritten_q,
            **result,
        }


@router.get("/debug/retrieval")
async def debug_retrieval_endpoint(q: str):
    async with AsyncSessionLocal() as db:
        return await debug_retrieval(db, query=q)


# -------- Streaming APIs --------

@router.get("/ask_stream")
async def ask_stream_endpoint(
    q: str,
    k: int = 5,
    workspace_id: str | None = None,
):
    async def generator():
        try:
            async with AsyncSessionLocal() as db:
                result = await ask_strict(
                    db,
                    query=q,
                    k=k,
                    workspace_id=workspace_id,
                )

                answer_text = result.get("answer", "")
                citations = result.get("citations", [])

                for word in answer_text.split():
                    yield json.dumps({
                        "type": "token",
                        "content": word + " "
                    }) + "\n"
                    await asyncio.sleep(0.05)

                yield json.dumps({
                    "type": "citations",
                    "data": citations
                }) + "\n"

                yield json.dumps({
                    "type": "done"
                }) + "\n"

        except Exception as e:
            yield json.dumps({
                "type": "error",
                "message": str(e)
            }) + "\n"

    return StreamingResponse(generator(), media_type="application/x-ndjson")


@router.get("/chat_stream")
async def chat_stream(
    workspace_id: str,
    q: str,
    k: int = 5,
):
    async def generator():
        assistant_full_text = ""

        try:
            async with AsyncSessionLocal() as db:
                await add_chat_message(
                    db,
                    workspace_id=workspace_id,
                    role="user",
                    content=q,
                    citations=None,
                )

                msgs = await get_recent_chat_messages(
                    db,
                    workspace_id=workspace_id,
                    limit=8,
                )
                user_questions = [m.content for m in msgs if m.role == "user"]

                rewritten_q = rewrite_query_with_history(q, user_questions[:-1])

                yield json.dumps({
                    "type": "meta",
                    "workspace_id": workspace_id,
                    "original_query": q,
                    "rewritten_query": rewritten_q,
                }) + "\n"

                result = await ask_strict(
                    db,
                    query=rewritten_q,
                    k=k,
                    workspace_id=workspace_id,
                )

                answer_text = result.get("answer", "")
                citations = result.get("citations", [])

                for word in answer_text.split():
                    assistant_full_text += word + " "
                    yield json.dumps({
                        "type": "token",
                        "content": word + " "
                    }) + "\n"
                    await asyncio.sleep(0.05)

                yield json.dumps({
                    "type": "citations",
                    "data": citations
                }) + "\n"

                await add_chat_message(
                    db,
                    workspace_id=workspace_id,
                    role="assistant",
                    content=assistant_full_text.strip(),
                    citations=citations,
                )

                yield json.dumps({
                    "type": "done"
                }) + "\n"

        except Exception as e:
            yield json.dumps({
                "type": "error",
                "message": str(e)
            }) + "\n"

    return StreamingResponse(generator(), media_type="application/x-ndjson")
@router.delete("/documents/{doc_id}")
async def delete_document_endpoint(doc_id: str):
    async with AsyncSessionLocal() as db:
        doc = await crud.get_document(db, doc_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        file_path = doc.storage_path

        await crud.delete_document(db, doc_id)
        delete_file(file_path)

        clear_vector_cache()

        return {
            "deleted": True,
            "doc_id": doc_id,
            "filename": doc.filename,
        }