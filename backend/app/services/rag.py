from io import BytesIO
from typing import Any
import uuid
import numpy as np
from docx import Document
from openai import AsyncOpenAI
from pypdf import PdfReader
from app.core.config import get_settings
from app.db.supabase import supabase


_EMBED_CACHE: dict[str, list[float]] = {}
_RETRIEVAL_CACHE: dict[tuple[str, str | None, int], list[dict[str, Any]]] = {}
_MAX_CACHE_ITEMS = 256


def remember_cache(cache: dict[Any, Any], key: Any, value: Any) -> None:
    if len(cache) >= _MAX_CACHE_ITEMS:
        first_key = next(iter(cache))
        cache.pop(first_key, None)
    cache[key] = value


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith(".docx"):
        doc = Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    return content.decode("utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    cleaned = " ".join(text.split())
    chunks: list[str] = []
    cursor = 0
    while cursor < len(cleaned):
        chunk = cleaned[cursor: cursor + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        cursor += max(1, chunk_size - overlap)
    return chunks


async def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    cached: list[list[float] | None] = [_EMBED_CACHE.get(text) for text in texts]
    missing_indexes = [index for index, value in enumerate(cached) if value is None]
    if not missing_indexes:
        return [value for value in cached if value is not None]

    missing_texts = [texts[index] for index in missing_indexes]
    if not settings.openai_api_key:
        generated = [deterministic_embedding(text) for text in missing_texts]
    else:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.embeddings.create(model=settings.embedding_model, input=missing_texts)
        generated = [item.embedding for item in response.data]

    for index, embedding in zip(missing_indexes, generated):
        remember_cache(_EMBED_CACHE, texts[index], embedding)
        cached[index] = embedding

    return [value for value in cached if value is not None]


def deterministic_embedding(text: str, dimensions: int = 1536) -> list[float]:
    vector = np.zeros(dimensions, dtype=float)
    for index, char in enumerate(text.encode("utf-8")[:6000]):
        vector[(index * 31 + char) % dimensions] += (char % 17) / 17
    norm = np.linalg.norm(vector)
    return (vector / norm).tolist() if norm else vector.tolist()


async def ingest_document(
    filename: str,
    content: bytes,
    portfolio: str,
    uploaded_by: str | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = extract_text(filename, content)
    chunks = chunk_text(text)
    embeddings = await embed_texts(chunks)
    document_id = str(uuid.uuid4())
    document_metadata = {"chunk_count": len(chunks), **(metadata or {})}
    await supabase.insert("knowledge_documents", {
        "id": document_id,
        "filename": filename,
        "portfolio": portfolio,
        "status": "processed",
        "uploaded_by": uploaded_by,
        "metadata": document_metadata,
    })
    rows = [
        {
            "document_id": document_id,
            "chunk_index": index,
            "content": chunk,
            "embedding": embedding,
            "metadata": {"filename": filename, "portfolio": portfolio, **(metadata or {})},
        }
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    if rows:
        await supabase.insert("document_chunks", rows)
    return {"document_id": document_id, "chunks": len(rows), "characters": len(text)}


async def retrieve_context(query: str, portfolio: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    cache_key = (" ".join(query.lower().split()), portfolio, limit)
    if cache_key in _RETRIEVAL_CACHE:
        return _RETRIEVAL_CACHE[cache_key]

    embedding = (await embed_texts([query]))[0]
    match_count = max(limit * 2, 10)
    payload = {"query_embedding": embedding, "match_count": match_count, "portfolio_filter": portfolio}
    try:
        chunks = await supabase.rpc("match_document_chunks", payload)
    except Exception:
        return []
    if not isinstance(chunks, list):
        return []

    def priority(chunk: dict[str, Any]) -> tuple[int, float]:
        metadata = chunk.get("metadata") or {}
        resource_key = metadata.get("resource_key")
        priority_value = int(metadata.get("priority") or 0)
        if resource_key == "aurum_conversation_kb_v31":
            priority_value += 100
        if resource_key == "aurum_partner_program":
            priority_value += 100
        return (priority_value, float(chunk.get("similarity") or 0))

    result = sorted(chunks, key=priority, reverse=True)[:limit]
    remember_cache(_RETRIEVAL_CACHE, cache_key, result)
    return result
