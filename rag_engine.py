"""RAG 引擎：将世界观文档切片嵌入 ChromaDB，按需检索相关片段"""

import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
COLLECTION_NAME = "world_lore"
CHROMA_DIR = str(BASE_DIR / "chroma_data")
LORE_FILE = str(BASE_DIR / "world_lore_full.md")

# 云端 Embedding — 优先用硅基流动(免费额度)，其次 OpenAI
EMBED_API_KEY = os.getenv("EMBED_API_KEY", os.getenv("EMBED_API_KEY", ""))
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "https://api.siliconflow.cn/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3.7-text-embedding")

_openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=EMBED_API_KEY,
    api_base=EMBED_BASE_URL,
    model_name=EMBED_MODEL,
)


def _get_client():
    return chromadb.PersistentClient(path=CHROMA_DIR)


def _get_collection():
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_openai_ef,
    )


def _split_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """简单段落切片：按 ## 标题分段，长段再按长度切"""
    # 先按标题分段
    sections = text.split("\n## ")
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        # 如果段长超过 chunk_size，按句子再切
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            sentences = section.replace("\n", " ").split("。")
            current = ""
            for s in sentences:
                s = s.strip() + "。"
                if len(current) + len(s) > chunk_size:
                    if current:
                        chunks.append(current.strip())
                    current = s
                else:
                    current += s
            if current.strip():
                chunks.append(current.strip())
    return chunks


def index_lore(filepath: str = LORE_FILE) -> int:
    """读取世界观文档，切片并存入向量库。返回切片数量"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = _split_text(text)
    if not chunks:
        return 0

    collection = _get_collection()

    # 清除旧数据
    try:
        collection.delete(ids=collection.get()["ids"])
    except Exception:
        pass

    # 分批存入（千问限制每次最多10条）
    batch_size = 8
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        ids = [f"chunk_{j}" for j in range(i, i+len(batch))]
        collection.add(documents=batch, ids=ids)

    return len(chunks)


def query_world(query: str, n: int = 3) -> str:
    """根据用户输入检索最相关的世界观片段，返回拼接文本"""
    try:
        collection = _get_collection()
        results = collection.query(query_texts=[query], n_results=n)
        docs = results.get("documents", [[]])[0]
        if docs:
            return "\n\n---\n\n".join(docs)
    except Exception:
        pass
    return ""


def is_indexed() -> bool:
    """检查是否已索引"""
    try:
        collection = _get_collection()
        return collection.count() > 0
    except Exception:
        return False


if __name__ == "__main__":
    n = index_lore()
    print(f"已索引 {n} 个片段")
