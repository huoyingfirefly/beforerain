# 🌧️ 雨前演练 · Before the Rain

> 基于《重返未来 1999》世界观的 AI 互动剧本游戏 —— **暴雨倒飞，时间回溯，触碰雨滴者被抹除。你的每一次选择都在改写命运。**

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)
![Deploy](https://img.shields.io/badge/一键部署-Windows-brightgreen)

**玩家自带 API Key · 服务器零成本 · 混合检索引擎 · 双 AI 叙事**

</div>

---

## 📑 目录

- [✨ 核心特性](#-核心特性)
- [📸 截图](#-截图)
- [🚀 快速开始](#-快速开始)
- [🔑 API Key 配置](#-api-key-配置)
- [🧠 检索架构](#-检索架构)
- [🃏 卡牌战斗](#-卡牌战斗)
- [🌐 部署到公网](#-部署到公网)
- [📁 项目结构](#-项目结构)
- [🛠️ 日常维护](#️-日常维护)
- [💻 技术栈](#-技术栈)
- [❓ 常见问题](#-常见问题)
- [📄 License](#-license)

---

## ✨ 核心特性

### 🎮 玩家自带 API Key（公网零成本架构）
- 每个玩家在浏览器里输入**自己的** API Key，即可开玩
- 密钥只保存在浏览器 `localStorage`，**服务端不保存、不落盘**
- 服务器自身不需要付费 Key 也能跑 —— 部署到公网零成本
- 服务端 `.env` 中可配置默认 Key，玩家未设置时自动回退

### 🧠 三路混合检索（Hybrid RAG）
每轮对话三条检索管道并行，结果拼入 System Prompt 后再生成：

| 管道 | 技术 | 数据源 | 作用 |
|------|------|--------|------|
| 直接检索 | Dense Passage Retrieval | `chroma.sqlite3` 文本库 | 查叙事片段、文笔参考 |
| 分类检索 | Multi-Index Vector Search | `lore/*.txt` 每类型独立向量库 | 按 AI 判定的类型精准搜实体 |
| 图检索 | Knowledge Graph Expansion | `lore/edges.txt` 关系边 | 沿关系边递归展开关联实体 |

检索管线：`用户输入 → AI 路由判断类型 → 分类向量搜 + 图递归展开 + 全文 RAG → 拼入提示词`

### 🤖 双 AI 架构
- **主 AI**（叙事，temp 0.7）：生成剧情文本，流式输出
- **副 AI**（机制判定，temp 0）：输出纺锤评分 / 道具掉落 / 战斗触发 / 强制检定 / 核素浓度 / 胜利结算

### 🚫 防幻觉约束
硬性规则注入 System Prompt：AI **只能使用检索到的实体**，不得凭空创造不存在的人物或设定。检索信息不足时优先推进现有线索。

### 🎨 文风注入
`lore/文风.txt` 自动追加到每次检索，AI 按指定笔调写作。每个类型的向量库有**独立切块策略**（chunk_size / overlap，见 `build_graph.py`）。

### 📚 其他玩法
- 26 套故事框架，每局随机抽取
- 卡组构筑、角色系统、核素浓度、纺锤经济
- 随机题材：悬疑推理 / 生存逃亡 / 阵营博弈 / 情感羁绊 / 黑色幽默 / 史诗悲歌 / 谍战暗线 / 探险考古 / 孤岛求生
- 音效（Web Audio API）、存档（localStorage 跨存档保留）

---

## 📸 截图

> 待补充：主菜单界面 / 游戏对话界面 / API 设置面板 / 卡牌战斗界面

| 主菜单 | 游戏界面 |
|--------|----------|
| 待补充 | 待补充 |

---

## 🚀 快速开始

### 方式一：一键部署（零环境）

下载 [deploy.bat](https://gitee.com/fire-flies/beforerain/raw/main/deploy.bat)，**双击运行**即可。

脚本自动完成：检测/安装 Python → 下载代码 → 安装依赖（含镜像回退）→ 配置 .env → 构建向量库 → 启动服务。

> ⚠️ **注意**：用编辑器修改 `deploy.bat` 后，必须确保换行符为 **CRLF**（不是 LF），否则双击闪退。项目已通过 `.gitattributes` 强制 `*.bat -text`。

### 方式二：手动运行

```bash
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain
copy .env.example .env        # Windows 编辑填入 API Key
pip install -r requirements.txt
python build_graph.py         # 构建图向量库（首次必做）
python api.py                 # 启动 → 浏览器打开 http://localhost:8000
```

---

## 🔑 API Key 配置

所有 AI 服务默认走**阿里云 DashScope**（OpenAI 兼容接口），叙事与 Embedding 可用**同一个 Key**。

`.env` 模板（`.env.example`）：

```ini
DEEPSEEK_API_KEY=your_api_key_here        # 叙事 + 机制判定
DEEPSEEK_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEEPSEEK_MODEL=deepseek-v4-flash-0731

# Embedding 服务（与 AI 叙事分开配置）
EMBED_API_KEY=your_api_key_here           # 向量嵌入
EMBED_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBED_MODEL=text-embedding-v3
```

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | 叙事 LLM + 机制判定 LLM | 无（玩家可自行输入） |
| `DEEPSEEK_BASE_URL` | 叙事 LLM 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `DEEPSEEK_MODEL` | 叙事 LLM 模型 | `deepseek-v4-flash-0731` |
| `EMBED_API_KEY` | 向量嵌入 | 无（可复用 DEEPSEEK_API_KEY） |
| `EMBED_BASE_URL` | 嵌入服务地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `EMBED_MODEL` | 嵌入模型 | `text-embedding-v3` |

> 💡 玩家在游戏主菜单点击 **⚙️ API 设置**，即可填入自己的 Key（LLM 与 Embedding 分开配置）。全部覆盖服务端默认值，只存于浏览器本地。

---

## 🧠 检索架构

### 混合检索引擎（`graph_engine.py`）

每轮对话的检索分三步：

```
玩家输入
   │
   ▼
① AI 类型路由（suggest_types）
   │   判断该搜哪些类型：角色 / 世界观 / 世界观详细 / 文风…
   ▼
② 分类向量检索（query_types）
   │   在每个类型独立向量库中余弦相似度搜索，找入口实体
   ▼
③ 图展开（expand_neighbors）
   │   从命中实体出发，沿 edges 关系边 BFS 递归展开邻居
   ▼
合并格式化 → 注入 System Prompt
```

- **类型路由**：副 AI 输出 JSON 数组选类型（最多 3 种），失败时关键词兜底
- **图展开**：`edges.txt` 中 `A → B = 关系` 双向建边，支持多对多、递归 N 层
- **文风恒在**：`文风` 类型永远追加为补充检索，不占其他类型的名额
- **预算控制**：关系图谱优先占预算，实体按字符上限填充，防止提示词膨胀

### 知识图谱数据源（`lore/`）

| 文件 | 格式 | 说明 |
|------|------|------|
| `角色.txt` 等 | `## 名称` 或 `【名称】` 分隔实体，`别名：` 行，描述正文 | 每个 `.txt` 是一个类型 |
| `edges.txt` | `A → B = 关系`，每行一条边 | 支持一对多、多对一、递归展开 |

### 直接检索（`rag_lite.py`）
轻量版 Dense Retrieval：sqlite3 直读 `chroma_data/chroma.sqlite3`，numpy 算余弦相似度，**零额外依赖**（不需要 chromadb 包）。

---

## 🃏 卡牌战斗

- **实时敌人名**：副 AI 从主 AI 叙事中提取具体敌人描述（如"持断刀的重塑之手信徒"），不再用预设名
- **D20 判定**：1-5 MISS / 6-10 半伤 / 11-15 命中 / 16-19 重击 / 20 暴击 ×2.5
- **四阶敌人**：杂兵 → 精锐 → 精英 → BOSS，按轮次概率出现，属性成长
- **道具卡**：武器 / 药物 / 情报 / 工具四类，关键词自动识别效果

---

## 🌐 部署到公网

架构天然支持公网零成本部署：**玩家用自己的 Key，服务器只需要一台能跑 Python 的机器**。

```bash
# 1. 拉代码（Linux 服务器）
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain
cp .env.example .env          # 可选：填服务端默认 Key（不填也能跑）
pip install -r requirements.txt
python build_graph.py         # 构建向量库

# 2. systemd 守护
sudo tee /etc/systemd/system/beforerain.service << 'EOF'
[Unit]
Description=Before Rain Game
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/root/beforerain
ExecStart=/usr/bin/python3 /root/beforerain/api.py
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now beforerain
```

- 服务默认监听 `0.0.0.0:8000`，可用 Nginx 反代加域名 / HTTPS
- **更新**：`cd ~/beforerain && git pull && python build_graph.py && sudo systemctl restart beforerain`
- **玩家体验**：打开网址 → 点击 ⚙️ 填入自己的 Key → 开始游戏

> 🔒 **隐私说明**：玩家 Key 仅存于浏览器 `localStorage`，每次请求时发送给服务端临时调用，**不落盘、不记录、不持久化**。

---

## 📁 项目结构

```
├── api.py                  # FastAPI 后端：三路混合检索 + 双 AI + 流式输出
├── graph_engine.py         # 混合检索引擎（分类向量 + 图展开 + AI 类型路由）
├── build_graph.py          # 图谱构建脚本（lore/*.txt → 向量库 + 关系图）
├── rag_lite.py             # 全文 RAG（sqlite3 直读，零额外依赖）
├── rag_engine.py           # ChromaDB 索引工具（旧版，需 chromadb 包）
├── deepseek.py             # DeepSeek 流式测试脚本
│
├── lore/                   # 知识图谱数据源
│   ├── 角色.txt            #   每个实体：## 或 【】 分隔，支持别名
│   ├── 世界观.txt          #   不同类型可配置独立切块策略
│   ├── 世界观详细.txt      #   （在 CHUNK_CONFIG 中按需新增类型）
│   ├── 文风.txt            #   检索时自动追加的笔调参考
│   └── edges.txt           #   关系边：A → B = 关系名
│
├── chroma_data/            # 向量数据（文本库 + 各类型图向量库）
├── deploy.bat              # 一键部署（零环境 → 运行）
├── requirements.txt        # 运行时依赖（不含 chromadb）
├── hub.html                # 主菜单（含 API 设置面板）
├── game.html               # 游戏主页面
├── .env.example            # 环境变量模板
└── .gitattributes          # 强制 *.bat 以 CRLF 存储
```

---

## 🛠️ 日常维护

改完 `lore/*.txt` 或 `lore/edges.txt` 后重新构建向量库：

```bash
python build_graph.py
```

- 构建后**无需重启服务**，下次请求自动加载新数据
- 想看当前索引状态：`python graph_engine.py status`
- 单库测试：`python graph_engine.py search 角色 维尔汀`
- 完整管线测试：`python graph_engine.py context 暴雨来临前我该去哪`

---

## 💻 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python · FastAPI · LangChain |
| 检索引擎 | Multi-Index Vector + GraphRAG + Dense Retrieval |
| 嵌入 | DashScope `text-embedding-v3` |
| LLM | DeepSeek `deepseek-v4-flash-0731`（DashScope 兼容接口） |
| 存储 | SQLite + NumPy（零向量数据库依赖） |
| 前端 | 原生 HTML/CSS/JS · Web Audio API |

---

## ❓ 常见问题

**Q：部署后玩家不填 Key 能玩吗？**
能，但会使用服务端 `.env` 中的默认 Key（若已配置）。建议玩家填自己的 Key，服务器零成本。

**Q：为什么不能给玩家用同一个服务器 Key？**
你的 Key 一旦放在前端，任何人都能抓走盗用。玩家自带 Key 是最安全的零成本方案。

**Q：修改了 lore 文档需要重启吗？**
只需要重新运行 `python build_graph.py`，无需重启服务。

**Q：deploy.bat 双击闪退？**
多半是换行符被改成 LF 了。仓库已强制 CRLF，重新下载即可；本地编辑后请转回 CRLF。

**Q：检索质量差 / 命中不准？**
检查 `lore/` 文档格式是否正确（`## 名称` 分隔）、`edges.txt` 是否用半角 `→` 和 `=`；适当调大 `build_graph.py` 中 `CHUNK_CONFIG` 的 overlap。

---

## 📄 License

MIT
