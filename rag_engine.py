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

# 使用本地 sentence-transformers，无需 API 调用
# 首次运行会自动下载模型（~120MB）
_openai_ef = embedding_functions.DefaultEmbeddingFunction()


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

    # 存入
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids)

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
