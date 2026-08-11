"""
图向量检索引擎：AI 判断类型 → 多库并行搜索 → 格式化上下文。
你自己构建向量库（build_index），引擎只负责检索。
"""
import os
import re
import json
import sqlite3
import random
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = Path(__file__).parent
STORE_DIR = BASE_DIR / "chroma_data"

_embed_client = OpenAI(
    api_key=os.getenv("EMBED_API_KEY", ""),
    base_url=os.getenv("EMBED_BASE_URL", "https://api.siliconflow.cn/v1"),
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-v3")


# ==========================================
# 构建向量库（你来调）
# ==========================================

def _embed(text: str) -> np.ndarray:
    resp = _embed_client.embeddings.create(model=EMBED_MODEL, input=text)
    return np.array(resp.data[0].embedding, dtype=np.float32)


def _store_paths(etype: str) -> tuple[Path, Path]:
    safe = etype.replace("/", "_").replace("\\", "_")
    return STORE_DIR / f"graph_{safe}.db", STORE_DIR / f"graph_{safe}.npy"


def build_index(etype: str, entities: list[dict]) -> int:
    """
    构建一个类型的向量库。
    entities: [{"name": "维尔汀", "text": "唯一露天免疫暴雨者..."}, ...]

    返回实体数量。
    """
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    db_path, vec_path = _store_paths(etype)

    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS entities (idx INTEGER PRIMARY KEY, name TEXT, document TEXT)")
    conn.execute("DELETE FROM entities")

    all_vecs = []
    for ent in entities:
        vec = _embed(ent["text"])
        all_vecs.append(vec)
        conn.execute("INSERT INTO entities (name, document) VALUES (?, ?)", (ent["name"], ent["text"]))

    conn.commit()
    conn.close()
    np.save(str(vec_path), np.array(all_vecs, dtype=np.float32))
    return len(entities)


# ==========================================
# 检索（核心）
# ==========================================

def _load_type(etype: str) -> tuple[list[dict], np.ndarray]:
    db_path, vec_path = _store_paths(etype)
    if not vec_path.exists() or not db_path.exists():
        return [], np.array([])
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT name, document FROM entities ORDER BY idx").fetchall()
    conn.close()
    if not rows:
        return [], np.array([])
    return [{"name": r[0], "document": r[1]} for r in rows], np.load(str(vec_path))


def query_type(query: str, etype: str, n: int = 5) -> list[dict]:
    """在单个类型库中搜索。返回 [{type, name, document, distance}]"""
    docs, embs = _load_type(etype)
    if len(docs) == 0:
        return []
    q_emb = _embed(query)
    norms_d = np.linalg.norm(embs, axis=1)
    sims = np.dot(embs, q_emb) / (norms_d * np.linalg.norm(q_emb) + 1e-8)
    results = []
    for idx in np.argsort(sims)[::-1][:n]:
        results.append({
            "type": etype, "name": docs[idx]["name"],
            "document": docs[idx]["document"], "distance": float(1.0 - sims[idx]),
        })
    return results


def query_types(query: str, types: list[str], n_per_type: int = 3) -> list[dict]:
    """在多个类型库中并行搜索，合并按距离排序。"""
    all_results = []
    for etype in types:
        all_results.extend(query_type(query, etype, n=n_per_type))
    all_results.sort(key=lambda r: r["distance"])
    return all_results


# ==========================================
# AI 类型判断
# ==========================================

def _list_types() -> list[str]:
    """扫描 chroma_data/ 下已有的向量库类型"""
    if not STORE_DIR.exists():
        return []
    types = set()
    for f in STORE_DIR.glob("graph_*.npy"):
        name = f.stem.replace("graph_", "", 1)
        if name:
            types.add(name)
    return sorted(types)


TYPE_DETECT_PROMPT = """你是游戏知识库路由。根据玩家输入，判断需要检索哪些类型的实体。
可选类型：{types}
只输出JSON数组，如 ["角色", "阵营"]。最多选3种，最少选1种。"""


async def suggest_types(query: str, llm=None) -> list[str]:
    """AI 判断该搜哪些类型。llm 为空则关键词回退。"""
    types = _list_types()
    if not types:
        return []

    if llm is not None:
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            resp = await llm.ainvoke([
                SystemMessage(content=TYPE_DETECT_PROMPT.format(types="、".join(types))),
                HumanMessage(content=query),
            ])
            raw = resp.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
            suggested = json.loads(raw)
            if isinstance(suggested, list):
                return [t for t in suggested if t in types][:3]
        except Exception:
            pass

    # 关键词回退
    mapping = {
        "角色": ["角色", "人物", "介绍", "是谁", "关系"],
        "阵营": ["阵营", "组织", "势力", "基金会", "重塑", "学校", "岛"],
        "事件": ["事件", "暴雨", "时间线", "发生", "灾难", "历史"],
        "机制": ["机制", "规则", "免疫", "庇护", "核素", "浓度", "检定", "战斗"],
        "地点": ["地点", "位置", "在哪", "庇护所", "手提箱", "堡垒"],
    }
    for etype, keywords in mapping.items():
        if etype in types and any(kw in query for kw in keywords):
            return [etype]
    return [t for t in ["角色", "机制"] if t in types][:2]


# ==========================================
# 主入口
# ==========================================

async def get_context(
    query: str, n_total: int = 4, types: list[str] = None, llm=None,
    max_chars: int = 1000, expand_depth: int = 1,
) -> str:
    """
    三步合一管线：
    1. AI 判类型 → 分类向量搜索（找入口实体）
    2. 图遍历展开关系（沿边捞关联实体）
    3. 合并格式化为 AI 上下文

    用法：ctx = await get_context(prompt, llm=mechanic_llm)
    """
    if types is None:
        types = await suggest_types(query, llm=llm)
    if not types:
        return ""

    # 文风永远作为补充检索（不抢其他类型的名额）
    all_types = _list_types()
    if "文风" in all_types and "文风" not in types:
        types = list(types) + ["文风"]

    # Step 1: 分类向量检索
    entities = query_types(query, types, n_per_type=max(1, n_total // len(types)))

    # Step 2: 图展开——从命中的实体名出发沿边捞关系
    entity_names = [e["name"] for e in entities[:5]]
    neighbors = expand_neighbors(entity_names, depth=expand_depth)

    # 先构建关系块，从总预算中预扣
    rel_lines = []
    for name, edges in neighbors.items():
        base = re.sub(r"-\d+$", "", name)
        for target, rel, direction in edges[:4]:
            if direction == "→":
                line = f"{base} → {rel} → {target}"
            else:
                line = f"{target} → {rel} → {base}"
            if line not in rel_lines:
                rel_lines.append(line)

    rel_block = ""
    if rel_lines:
        rel_block = "【关系图谱】\n" + "\n".join(rel_lines[:10])

    # 实体预算 = 总额 - 关系块 - 标签
    rel_budget = len(rel_block) + 2 if rel_block else 0
    entity_budget = max_chars - rel_budget - 50

    # Step 3: 格式化——图谱优先，实体填空
    label = f"[检索类型：{'/'.join(types)}]"
    parts = [label]
    total = len(label) + 2

    # 实体：每个最多 120 字符
    for r in entities[:n_total]:
        doc_short = r['document'][:120]
        block = f"【{r['type']}·{r['name']}】{doc_short}"
        if total + len(block) > entity_budget:
            break
        parts.append(block)
        total += len(block) + 2

    # 关系图谱（有预算就全放，不做截断）
    if rel_block and total + len(rel_block) <= max_chars:
        parts.append(rel_block)

    return "\n\n".join(parts)


def query_world(query: str, n: int = 5, max_chars: int = 1000) -> str:
    """同步全类型搜索（兼容 rag_lite 接口）"""
    types = _list_types()
    if not types:
        return ""
    results = query_types(query, types, n_per_type=max(1, n // len(types)))[:n]
    parts = []
    for r in results:
        block = f"【{r['type']}·{r['name']}】{r['document']}"
        if len("\n".join(parts)) + len(block) + 2 > max_chars:
            break
        parts.append(block)
    return "\n".join(parts)


# ==========================================
# 图遍历——纯内存，零延迟
# ==========================================

GRAPH_FILE = STORE_DIR / "graph_edges.json"

# 运行时缓存
_graph = None  # {name: [(target, relation), ...]}


def store_graph(edges: list[tuple[str, str, str]]):
    """
    存储关系边。edges = [(from, to, relation), ...]
    由 build_graph.py 调。
    """
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    data = [[f, t, r] for f, t, r in edges]
    with open(str(GRAPH_FILE), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    global _graph
    _graph = _build_adjacency(data)


def _build_adjacency(edges: list) -> dict:
    """构建双向邻接表"""
    adj = {}
    for src, dst, rel in edges:
        adj.setdefault(src, []).append((dst, rel, "→"))
        adj.setdefault(dst, []).append((src, rel, "←"))
    return adj


def _load_graph() -> dict:
    global _graph
    if _graph is not None:
        return _graph
    if not GRAPH_FILE.exists():
        _graph = {}
        return _graph
    with open(str(GRAPH_FILE), "r", encoding="utf-8") as f:
        data = json.load(f)
    _graph = _build_adjacency(data)
    return _graph


def _normalize(name: str) -> str:
    """标准化实体名：去【】、去 -数字 后缀"""
    n = re.sub(r"-\d+$", "", name)
    n = re.sub(r"^【|】$", "", n)
    return n


def expand_neighbors(names: list[str], depth: int = 1) -> dict[str, list[tuple[str, str, str]]]:
    """
    给一批实体名，沿边递归展开 N 层关系。
    返回 {name: [(related_name, relation, direction), ...]}
    depth=1: 只看直接关系
    depth=2: 加上关系的邻居（但不会回到已访问节点）
    """
    adj = _load_graph()
    result = {}

    for name in names:
        key = _normalize(name)
        if key not in adj:
            result[name] = []
            continue

        edges = []
        visited = {key}
        queue = [(key, 0)]

        while queue:
            cur, d = queue.pop(0)
            if d >= depth:
                continue
            for target, rel, direction in adj.get(cur, []):
                if direction == "→":
                    line = (name, target, rel, "→")
                else:
                    line = (name, target, rel, "←")

                if line[1] not in visited and (line[1], line[2], line[3]) not in [
                    (e[1], e[2], e[3]) for e in edges
                ]:
                    edges.append(line)
                    if d + 1 < depth and _normalize(target) in adj:
                        visited.add(_normalize(target))
                        queue.append((_normalize(target), d + 1))

        result[name] = [(e[1], e[2], e[3]) for e in edges][:10]

    return result


def is_indexed() -> bool:
    for etype in _list_types():
        if _store_paths(etype)[1].exists():
            return True
    return False


# ==========================================
# 命令行
# ==========================================

if __name__ == "__main__":
    import sys, asyncio
    if len(sys.argv) < 2:
        print("用法:")
        print("  python graph_engine.py search <类型> <关键词>  单库搜索")
        print("  python graph_engine.py types <关键词>          类型判断")
        print("  python graph_engine.py context <关键词>         完整管线")
        print("  python graph_engine.py status                  索引状态")
        sys.exit(0)

    cmd, arg = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""
    if cmd == "search":
        etype, kw = arg, sys.argv[3] if len(sys.argv) > 3 else ""
        for r in query_type(kw, etype):
            print(f"  [{r['type']}] {r['name']}  dist={r['distance']:.3f}")
            print(f"    {r['document'][:100]}")
    elif cmd == "types":
        print(f"  关键词 → {_list_types()}")
        print(f"  判断 → {asyncio.run(suggest_types(arg))}")
    elif cmd == "context":
        print(asyncio.run(get_context(arg)))
    elif cmd == "status":
        print(f"  已索引: {is_indexed()}")
        for etype in _list_types():
            docs, _ = _load_type(etype)
            print(f"  [{etype}] {len(docs)} 实体")
