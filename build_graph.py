"""
图谱向量库构建脚本。
读取 lore/*.txt，调用 graph_engine.build_index 生成独立向量库。

TXT 格式：
  ## 实体名
  别名：别名1、别名2
  描述正文第一句。描述正文第二句。

用法：python build_graph.py
"""
import re
from pathlib import Path
from graph_engine import build_index, store_graph

BASE_DIR = Path(__file__).parent
LORE_DIR = BASE_DIR / "lore"

# ==========================================
# 切块策略 —— 每个类型独立配置
# ==========================================
# chunk_size: 每块最大字符数
# overlap:    块之间重叠字符数
# 如果某个类型不在此配置中，默认不切块（整段嵌入）

CHUNK_CONFIG = {
    "角色":     {"chunk_size": 200, "overlap": 50},
    "世界观":   {"chunk_size": 100, "overlap": 20},
    "世界观详细":   {"chunk_size": 300, "overlap": 20},
    "文风":     {"chunk_size": 300, "overlap": 50}, 
}


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    将长文本按句子切块，保持语义完整。
    优先按 。！？ 断句，再按长度截断。
    """
    if len(text) <= chunk_size:
        return [text]

    # 按句子分割
    sentences = re.split(r"(?<=[。！？.!?])", text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) <= chunk_size:
            current += s
        else:
            if current:
                chunks.append(current.strip())
            # 重叠：保留末尾一部分接到下块开头
            if overlap > 0 and current:
                overlap_text = current[-overlap:]
                current = overlap_text + s
            else:
                current = s

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


def parse_txt(filepath: str, chunk_size: int = None, overlap: int = 0) -> list[dict]:
    """
    解析 lore/*.txt → [{"name": "维尔汀", "text": "..."}, ...]
    如果指定 chunk_size，长文本会被切块（name 自动加 -1, -2 后缀）。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n##\s+", content)
    entities = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        name = lines[0].strip().lstrip("#").strip()
        name = re.sub(r"^【|】$", "", name).strip()  # 去掉【】括号

        aliases = []
        desc_lines = []

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("别名：") or line.startswith("别名:"):
                alias_str = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                aliases = [a.strip() for a in re.split(r"[、,]", alias_str) if a.strip()]
            elif line:
                desc_lines.append(line)

        # 拼嵌入文本
        text_parts = []
        if aliases:
            text_parts.append(f"别称：{'、'.join(aliases)}")
        text_parts.append(f"[{name}] " + "。".join(desc_lines) if desc_lines else f"[{name}]")
        text = "。".join(text_parts)

        # 跳过无实质内容的实体（只有名没有描述）
        # text 形如 "[维尔汀] " 说明没内容，嵌入 API 会拒
        if not desc_lines and not aliases:
            print(f"    跳过空实体: {name}")
            continue

        # 切块
        if chunk_size and len(text) > chunk_size:
            chunks = chunk_text(text, chunk_size, overlap)
            for i, c in enumerate(chunks):
                suffix = f"-{i + 1}" if len(chunks) > 1 else ""
                entities.append({"name": f"{name}{suffix}", "text": c})
        else:
            entities.append({"name": name, "text": text})

    return entities


def main():
    if not LORE_DIR.exists():
        print("lore/ 目录不存在，请先创建并放入 .txt 文件。")
        print("格式示例：")
        print("  ## 维尔汀")
        print("  别名：Vertin")
        print("  唯一露天免疫暴雨者。")
        return

    txt_files = sorted(LORE_DIR.glob("*.txt"))
    txt_files = [f for f in txt_files if f.stem != "edges"]  # edges.txt 单独处理
    if not txt_files:
        print("lore/ 目录下没有 .txt 文件。")
        return

    total = 0
    for filepath in txt_files:
        etype = filepath.stem
        cfg = CHUNK_CONFIG.get(etype, {})
        entities = parse_txt(str(filepath), cfg.get("chunk_size"), cfg.get("overlap", 0))

        if not entities:
            print(f"  [{etype}] 跳过（无有效实体）")
            continue

        n = build_index(etype, entities)
        total += n
        print(f"  [{etype}] {n} 块  (策略: {cfg.get('chunk_size', '整段')}/{cfg.get('overlap', 0)})")

        if n > 0:
            names = [e["name"] for e in entities[:6]]
            suffix = "..." if n > 6 else ""
            print(f"          {', '.join(names)}{suffix}")

    print(f"\n已构建 {len(txt_files)} 个向量库，共 {total} 个块。")

    # 图关系
    edges_file = LORE_DIR / "edges.txt"
    if edges_file.exists():
        edges = parse_edges(str(edges_file))
        if edges:
            store_graph(edges)
            print(f"\n已构建关系图：{len(edges)} 条边")
            for src, dst, rel in edges[:5]:
                print(f"  {src} → {rel} → {dst}")
            if len(edges) > 5:
                print(f"  ... 共 {len(edges)} 条")
    else:
        print("\n(未找到 edges.txt，跳过关系图构建)")


def parse_edges(filepath: str) -> list[tuple[str, str, str]]:
    """解析 edges.txt → [(from, to, relation), ...]"""
    edges = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 格式：A → B = 关系
            m = re.match(r"(.+?)→(.+?)=(.+)", line)
            if m:
                src = m.group(1).strip()
                dst = m.group(2).strip()
                rel = m.group(3).strip()
                edges.append((src, dst, rel))
    return edges


if __name__ == "__main__":
    main()
