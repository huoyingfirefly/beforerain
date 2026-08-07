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


def _load_docs():
    """直接从 sqlite3 读取所有文档 + 向量（兼容 ChromaDB 1.5+）"""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT em.id, em.string_value, eq.vector "
        "FROM embedding_metadata em "
        "LEFT JOIN embeddings_queue eq ON em.id = eq.seq_id "
        "WHERE em.key='chroma:document' "
        "ORDER BY em.id"
    ).fetchall()
    conn.close()

    docs = []
    embeddings = []
    for row in rows:
        if row[1] is not None and row[2] is not None:
            docs.append(row[1])
            embeddings.append(np.frombuffer(row[2], dtype=np.float32))

    return docs, np.array(embeddings) if embeddings else np.array([])

def _embed(text: str) -> np.ndarray:
    """调用 API 嵌入文本"""
    resp = _client.embeddings.create(
        model=os.getenv("EMBED_MODEL", "text-embedding-v3"),
        input=text,
    )
    return np.array(resp.data[0].embedding, dtype=np.float32)


def query_world(query: str, n: int = 8, pick: int = 3, max_chars: int = 1200) -> str:
    """检索文档片段，随机抽取增加多样性"""
    try:
        docs, embs = _load_docs()
        if len(docs) == 0:
            return ""

        # 给查询加随机噪声词，扰动嵌入结果
        import random
        noise_words = ['悬疑','生存','情感','史诗','战斗','秘法','逃亡','探索','阴谋','宿命']
        noisy_query = query + ' ' + random.choice(noise_words)

        q_emb = _embed(noisy_query)
        sims = np.dot(embs, q_emb) / (np.linalg.norm(embs, axis=1) * np.linalg.norm(q_emb) + 1e-8)
        top_idx = np.argsort(sims)[-n:][::-1]

        # 去重
        seen = []
        candidates = []
        for idx in top_idx:
            doc = docs[idx]
            if any(_overlap(doc, s) > 0.3 for s in seen):
                continue
            seen.append(doc)
            candidates.append(doc)

        # 随机抽取 pick 条
        if len(candidates) > pick:
            candidates = random.sample(candidates, pick)

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
