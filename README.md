# 雨前演练 · Before the Rain

基于《重返未来 1999》世界观的 AI 互动剧本游戏。暴雨倒飞，时间回溯，触碰雨滴者被抹除。你的每一次选择都在改写命运。

## 检索架构

采用**混合检索引擎（Hybrid RAG）**，每轮对话三条管道并行：

| 管道 | 技术 | 数据源 | 作用 |
|------|------|--------|------|
| 直接检索 | Dense Passage Retrieval | `world_lore_full.txt` | 查叙事片段、文笔参考 |
| 分类检索 | Multi-Index Vector Search | `lore/*.txt` 每个类型独立向量库 | 按 AI 判定的类型精准搜实体 |
| 图检索 | Knowledge Graph Expansion | `lore/edges.txt` | 沿关系边展开关联实体 |

检索管线：`用户输入 → AI 路由判断类型 → 分类向量搜 + 图递归展开 + 全文 RAG → 拼入提示词`

## 功能

### AI 叙事
- **三路混合检索**：每轮实时检索实体关系 + 叙事片段，注入 system prompt 后再生成
- **双 AI 架构**：主 AI（叙事，temp 0.7）+ 副 AI（机制判定，temp 0）
- **防幻觉约束**：硬性规则限制 AI 只能使用检索到的实体，不得凭空编造角色
- **文风注入**：`lore/文风.txt` 自动追加到每次检索，AI 模仿指定笔调写作
- **随机题材**：悬疑推理 / 生存逃亡 / 阵营博弈 / 情感羁绊 / 黑色幽默 / 史诗悲歌 / 谍战暗线 / 探险考古 / 孤岛求生

### 知识图谱
- **自定义实体**：`lore/` 下每个 `.txt` 文件对应一个类型，`##` 或 `【】` 分割实体
- **关系边**：`lore/edges.txt` 定义 `A → B = 关系`，支持一对多、多对一、递归展开
- **独立切块策略**：每个类型可配置不同 chunk_size 和 overlap（见 `build_graph.py`）
- **一键构建**：`python build_graph.py` 解析 TXT + edges → 嵌入 → 向量库 + 图

### 卡牌战斗
- **实时敌人名**：副 AI 从叙事中提取具体敌人描述（"持断刀的重塑之手信徒"），不再用预设名
- **D20 判定**：1-5 MISS / 6-10 半伤 / 11-15 命中 / 16-19 重击 / 20 暴击 ×2.5
- **四阶敌人**：杂兵 → 精锐 → 精英 → BOSS，按轮次概率出现，属性成长
- **道具卡**：武器/药物/情报/工具四类，关键词自动识别效果

### 其他
- 卡组构筑、角色系统、核素浓度、纺锤经济、26 套故事框架
- 音效（Web Audio API）、存档（localStorage 跨存档保留）
- 26 套故事框架，每局随机抽取

## 项目结构

```
├── api.py                  # FastAPI 后端，三路混合检索 + 双 AI + 流式输出
├── graph_engine.py         # 混合检索引擎（分类向量 + 图展开 + AI 路由）
├── build_graph.py          # 图谱构建脚本（lore/*.txt → 向量库 + 关系图）
├── rag_lite.py             # 全文 RAG（sqlite3 直读 ChromaDB，零额外依赖）
├── rag_engine.py           # ChromaDB 索引工具（需 chromadb 包）
├── deepseek.py             # DeepSeek 流式测试脚本
│
├── lore/                   # 知识图谱数据源
│   ├── 角色.txt            #   每个实体：## 或 【】 分隔
│   ├── 世界观.txt          #   支持别名、描述
│   ├── 事件.txt / 机制.txt / 地点.txt / 文风.txt
│   └── edges.txt           #   关系边：A → B = 关系名
│
├── chroma_data/            # 向量数据（RAG 文本库 + 各类型图向量库）
├── deploy.bat              # 一键部署（零环境 → 运行）
├── requirements.txt        # 运行时依赖（不含 chromadb）
├── hub.html                # 主菜单
├── game.html               # 游戏主页面
├── .env.example            # 环境变量模板
└── world_graph.json        # 旧版图数据（保留参考）
```

## 本地运行

### 方式一：一键部署

下载 [deploy.bat](https://gitee.com/fire-flies/beforerain/raw/main/deploy.bat)，双击运行。脚本自动：检测/安装 Python → 安装依赖 → 配置 .env → 启动服务。

> 编辑器修改 deploy.bat 后，确保文件换行符为 **CRLF**（不是 LF），否则双击闪退。

### 方式二：手动

```bash
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain
copy .env.example .env        # 编辑填入 API Key
pip install -r requirements.txt
python build_graph.py         # 构建图向量库
python api.py                 # 启动 → http://localhost:8000
```

### API Key

| 密钥 | 用途 | 获取 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 叙事 + 机制判定 | SiliconFlow 或 DeepSeek 注册 |
| `EMBED_API_KEY` | 向量嵌入 | 阿里云 DashScope（免费额度） |

### 日常维护

改完 `lore/*.txt` 或 `lore/edges.txt` 后重新构建向量库：

```bash
python build_graph.py
```

无需重启服务，下次请求自动加载新数据。

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python · FastAPI · LangChain |
| 检索引擎 | Multi-Index Vector + GraphRAG + Dense Retrieval |
| 嵌入 | DashScope text-embedding-v3 / SiliconFlow BGE |
| LLM | DeepSeek（通过 SiliconFlow 代理） |
| 前端 | 原生 HTML/CSS/JS · Web Audio API |

## 服务器部署

```bash
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain
cp .env.example .env && nano .env
pip install -r requirements.txt
python build_graph.py

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

更新：`cd ~/beforerain && git pull && python build_graph.py && sudo systemctl restart beforerain`

## License

MIT
