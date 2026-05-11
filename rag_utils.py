"""RAG (Retrieval-Augmented Generation) для UFC Predictor.

Хранилище: ChromaDB (persistent, ./chroma_db)
Эмбеддинги: sentence-transformers (all-MiniLM-L6-v2 — быстро + достаточно качественно)

Документы:
  - fighter_profile: профиль бойца (стилистика, статы, сила/слабость)
  - fight_record:    исторический бой (результат, метод, раунд, разбор стиля)

Используется в Predictor + Event Predictor чтобы LLM-аналитика опиралась на
реальные данные, а не только на параметрические знания модели.
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path

import streamlit as st


CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "ufc_kb_v1"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Lazy / cached resources
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="🧠 Загружаю embedding-модель (первый раз ~90 МБ)...")
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


@st.cache_resource(show_spinner=False)
def get_chroma_client():
    import chromadb
    from chromadb.config import Settings
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )


def get_collection():
    """Возвращает (или создаёт) коллекцию."""
    client = get_chroma_client()
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        return client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Векторизуем список строк (нормализованные эмбеддинги)."""
    model = get_embedder()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist()


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------

def fighter_to_doc(f: dict) -> tuple[str, str, dict]:
    """Преобразуем fighter dict в (id, text, metadata) для индексации."""
    name = f.get("name", "Unknown")
    parts = [
        f"FIGHTER PROFILE: {name}",
        f"Division: {f.get('division', '')}",
        f"Country: {f.get('country', '')}",
        f"Age: {f.get('age', '?')} | Record: {f.get('record', '?')}",
        f"Height: {f.get('height_cm', '?')}cm | Reach: {f.get('reach_cm', '?')}cm | Stance: {f.get('stance', '')}",
        f"Style: {f.get('style', '')}",
        (
            f"Stats — SLpM: {f.get('SLpM', '?')}, SApM: {f.get('SApM', '?')}, "
            f"StrAcc: {f.get('StrAcc', '?')}%, StrDef: {f.get('StrDef', '?')}%, "
            f"TDAvg: {f.get('TDAvg', '?')}, TDDef: {f.get('TDDef', '?')}%, "
            f"SubAvg: {f.get('SubAvg', '?')}"
        ),
        f"Strengths: {', '.join(f.get('strengths', []) or [])}",
        f"Weaknesses: {', '.join(f.get('weaknesses', []) or [])}",
        f"Weight cut difficulty: {f.get('weight_cut_difficulty', '')}",
    ]
    if f.get("bio"):
        parts.append(f"Bio: {f['bio']}")
    if f.get("recent_fights"):
        recent = "; ".join(
            f"{r.get('opponent', '?')} ({r.get('result', '?')}, {r.get('method', '?')})"
            for r in f["recent_fights"][:5]
        )
        parts.append(f"Recent fights: {recent}")

    text = "\n".join(p for p in parts if p)
    metadata = {
        "doc_type": "fighter_profile",
        "fighter_name": name,
        "division": f.get("division", "") or "",
        "country": f.get("country", "") or "",
    }
    safe_name = name.lower().replace(" ", "_").replace("'", "")
    doc_id = f"fighter::{safe_name}"
    return doc_id, text, metadata


def fight_to_doc(fight: dict) -> tuple[str, str, dict]:
    """Преобразуем исторический бой в (id, text, metadata)."""
    a = fight.get("fighter_a", "?")
    b = fight.get("fighter_b", "?")
    parts = [
        f"FIGHT RECORD: {a} vs {b}",
        f"Event: {fight.get('event', '')} | Date: {fight.get('date', '')}",
        f"Weight class: {fight.get('weight_class', '')}",
        f"Result: {fight.get('winner', '?')} won by {fight.get('method', '?')} in R{fight.get('round', '?')}",
    ]
    if fight.get("notes"):
        parts.append(f"Key dynamics: {fight['notes']}")
    if fight.get("stylistic_lessons"):
        parts.append(f"Stylistic lessons: {fight['stylistic_lessons']}")

    text = "\n".join(p for p in parts if p)

    fight_id = fight.get("id") or f"{a}_{b}_{fight.get('date', '')}".replace(" ", "_").lower()
    metadata = {
        "doc_type": "fight_record",
        "fighter_a": a,
        "fighter_b": b,
        "winner": fight.get("winner", "") or "",
        "method": fight.get("method", "") or "",
        "weight_class": fight.get("weight_class", "") or "",
        "date": fight.get("date", "") or "",
        "fight_id": fight_id,
    }
    return f"fight::{fight_id}", text, metadata


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_documents(docs: list[tuple[str, str, dict]]) -> int:
    """Upsert документов в коллекцию. docs = [(id, text, metadata), ...]"""
    if not docs:
        return 0
    col = get_collection()
    ids = [d[0] for d in docs]
    texts = [d[1] for d in docs]
    metas = [d[2] for d in docs]
    embeddings = embed_texts(texts)

    # Убираем дубликаты id (Chroma не любит)
    try:
        col.delete(ids=ids)
    except Exception:
        pass
    col.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metas)
    return len(docs)


def index_fighters(fighters: list[dict]) -> int:
    docs = [fighter_to_doc(f) for f in fighters if f.get("name")]
    return index_documents(docs)


def index_fights(fights: list[dict]) -> int:
    docs = [fight_to_doc(f) for f in fights if f.get("fighter_a") and f.get("fighter_b")]
    return index_documents(docs)


def reset_collection():
    """Удаляем и пересоздаём коллекцию."""
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def collection_stats() -> dict:
    """Сводная статистика коллекции."""
    try:
        col = get_collection()
        all_data = col.get()
        ids = all_data.get("ids", []) or []
        metas = all_data.get("metadatas", []) or []
        n_fighters = sum(1 for m in metas if (m or {}).get("doc_type") == "fighter_profile")
        n_fights = sum(1 for m in metas if (m or {}).get("doc_type") == "fight_record")
        return {
            "total": len(ids),
            "fighters": n_fighters,
            "fights": n_fights,
            "last_indexed": _read_last_indexed(),
        }
    except Exception as e:
        return {"total": 0, "fighters": 0, "fights": 0, "error": str(e)}


def list_all_documents() -> list[dict]:
    """Все документы со всеми метаданными (для UI инспектора)."""
    try:
        col = get_collection()
        d = col.get()
        out = []
        for i, doc_id in enumerate(d.get("ids", [])):
            out.append({
                "id": doc_id,
                "text": d["documents"][i],
                "meta": d["metadatas"][i] or {},
            })
        return out
    except Exception:
        return []


_LAST_INDEXED_FILE = "./chroma_db/.last_indexed"


def _write_last_indexed():
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    with open(_LAST_INDEXED_FILE, "w") as f:
        f.write(datetime.now().isoformat())


def _read_last_indexed() -> str:
    try:
        with open(_LAST_INDEXED_FILE) as f:
            return f.read().strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Retrieval (hybrid: semantic + metadata boost)
# ---------------------------------------------------------------------------

def retrieve_relevant_context(
    query: str,
    fighter_a: str | None = None,
    fighter_b: str | None = None,
    top_k: int = 6,
) -> dict:
    """Семантический поиск с бустом по именам бойцов.

    Возвращает:
      {
        'context_text': str — готовый текст для инжекта в LLM-промпт,
        'sources': list[str] — короткие источники [1] [2] ...,
        'raw': list[dict] — топ-K кандидатов,
        'error': str | None
      }
    """
    try:
        col = get_collection()
        # Получаем кандидатов в 3х количестве чтобы было что ранжировать
        emb = embed_texts([query])[0]
        n_fetch = max(top_k * 3, 12)
        res = col.query(
            query_embeddings=[emb],
            n_results=n_fetch,
        )

        if not res.get("documents") or not res["documents"][0]:
            return {"context_text": "", "sources": [], "raw": [], "error": None}

        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res.get("distances", [[0] * len(docs)])[0]

        candidates = []
        for i, doc in enumerate(docs):
            meta = metas[i] or {}
            # cosine distance в Chroma: 0=одинаково, 2=противоположно. score = 1-d
            score = max(0.0, 1.0 - float(dists[i] or 0))

            # Boost: документ релевантен одному из бойцов запроса
            for fname in [fighter_a, fighter_b]:
                if not fname:
                    continue
                fname_l = fname.lower()
                if (
                    (meta.get("fighter_name") or "").lower() == fname_l
                    or (meta.get("fighter_a") or "").lower() == fname_l
                    or (meta.get("fighter_b") or "").lower() == fname_l
                ):
                    score += 0.35
            candidates.append({"doc": doc, "meta": meta, "score": score})

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:top_k]

        # Готовим контекст для LLM
        ctx_lines = []
        sources = []
        for i, c in enumerate(top, 1):
            m = c["meta"]
            if m.get("doc_type") == "fighter_profile":
                label = f"Fighter Profile · {m.get('fighter_name', '?')}"
            elif m.get("doc_type") == "fight_record":
                label = (
                    f"Historical Fight · {m.get('fighter_a', '?')} vs "
                    f"{m.get('fighter_b', '?')} ({m.get('date', '?')})"
                )
            else:
                label = m.get("doc_type", "doc")
            sources.append(f"[{i}] {label}")
            ctx_lines.append(f"[Source {i}] {label}\n{c['doc']}")

        return {
            "context_text": "\n\n---\n\n".join(ctx_lines),
            "sources": sources,
            "raw": top,
            "error": None,
        }
    except Exception as e:
        return {"context_text": "", "sources": [], "raw": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Bootstrap (auto-seed на первый запуск)
# ---------------------------------------------------------------------------

def bootstrap_if_empty(fighters: list[dict] | None = None) -> dict:
    """Если коллекция пустая — заливаем сидовые данные (бойцы + исторические бои).
    Возвращает: {'fighters_indexed': N, 'fights_indexed': M, 'skipped': bool}
    """
    stats = collection_stats()
    if stats.get("total", 0) > 0:
        return {"fighters_indexed": 0, "fights_indexed": 0, "skipped": True}

    n_fighters = 0
    n_fights = 0

    if fighters:
        n_fighters = index_fighters(fighters)

    try:
        from rag_seed import HISTORICAL_FIGHTS
        n_fights = index_fights(HISTORICAL_FIGHTS)
    except Exception:
        pass

    if n_fighters or n_fights:
        _write_last_indexed()

    return {
        "fighters_indexed": n_fighters,
        "fights_indexed": n_fights,
        "skipped": False,
    }


def reindex_all(fighters: list[dict] | None = None) -> dict:
    """Полная переиндексация: бойцы из st.session_state + сидовые бои."""
    reset_collection()
    n_fighters = index_fighters(fighters or [])
    n_fights = 0
    try:
        from rag_seed import HISTORICAL_FIGHTS
        n_fights = index_fights(HISTORICAL_FIGHTS)
    except Exception:
        pass
    _write_last_indexed()
    return {"fighters_indexed": n_fighters, "fights_indexed": n_fights}
