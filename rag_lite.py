"""RAG 轻量版：直接用 sqlite3 + numpy 读 ChromaDB，无需 chromadb 包"""
import os
import json
import sqlite3
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "chroma_data" / "chroma.sqlite3"

# Embedding 客户端
_client = OpenAI(
    api_key=os.getenv("EMBED_API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
    base_url=os.getenv("EMBED_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)


def _load_docs() -> list[str]:
    """直接从 sqlite3 读取所有文档"""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT id, string_value FROM embedding_metadata "
        "WHERE key='chroma:document' ORDER BY id"
    ).fetchall()
    conn.close()

    ids = [row[0] for row in rows]
    docs = [json.loads(row[1]) for row in rows]

    # 加载对应 embedding
    conn = sqlite3.connect(str(DB_PATH))
    emb_rows = conn.execute(
        "SELECT id, embedding FROM embeddings ORDER BY id"
    ).fetchall()
    conn.close()

    emb_map = {}
    for eid, emb_blob in emb_rows:
        arr = np.frombuffer(emb_blob, dtype=np.float32)
        emb_map[eid] = arr

    # 按 embedding_metadata 的顺序对齐
    embeddings = []
    ordered_docs = []
    for i, doc in enumerate(docs):
        if i < len(ids) and ids[i] in emb_map:
            embeddings.append(emb_map[ids[i]])
            ordered_docs.append(doc)

    return ordered_docs, np.array(embeddings)


def _embed(text: str) -> np.ndarray:
    """调用 API 嵌入文本"""
    resp = _client.embeddings.create(
        model=os.getenv("EMBED_MODEL", "text-embedding-v3"),
        input=text,
    )
    return np.array(resp.data[0].embedding, dtype=np.float32)


def query_world(query: str, n: int = 12, pick: int = 5, max_chars: int = 1500) -> str:
    """检索文档片段，取最相关的前N条"""
    try:
        docs, embs = _load_docs()
        if len(docs) == 0:
            return ""

        q_emb = _embed(query)
        sims = np.dot(embs, q_emb) / (np.linalg.norm(embs, axis=1) * np.linalg.norm(q_emb) + 1e-8)
        top_idx = np.argsort(sims)[-n:][::-1]

        # 去重 + 取前 pick 条（不随机，取最相关）
        seen = []
        candidates = []
        for idx in top_idx:
            doc = docs[idx]
            if any(_overlap(doc, s) > 0.3 for s in seen):
                continue
            seen.append(doc)
            candidates.append(doc)
            if len(candidates) >= pick:
                break

        result = ""
        for doc in candidates:
            if len(result) + len(doc) + 10 > max_chars:
                result += doc[:max_chars - len(result) - 10] + "..."
                break
            result += doc + "\n\n---\n\n"
        return result.rstrip("\n- \n")
    except Exception:
        return ""

def _overlap(a: str, b: str) -> float:
    a_set = set(a[:200])
    b_set = set(b[:200])
    if not a_set or not b_set:
        return 0
    return len(a_set & b_set) / max(len(a_set), len(b_set))


def is_indexed() -> bool:
    return DB_PATH.exists()


def index_lore() -> int:
    return -1  # rag_lite 不支持重建索引，用 chromadb 版
