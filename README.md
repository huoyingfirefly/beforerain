# 雨前演练 · Before the Rain

基于《重返未来 1999》世界观的 AI 互动剧本游戏。暴雨倒飞，时间回溯，触碰雨滴者被抹除。你的每一次选择都在改写命运——是抵达庇护所，还是成为暴雨中又一个消失的名字。

## 功能

### AI 叙事

- **双 AI 架构**：主 AI（DeepSeek, temp 0.7）流式输出叙事，副 AI（DeepSeek, temp 0）独立判定纺锤、道具、战斗、检定、核素浓度与胜负
- **随机题材**：悬疑推理 / 生存逃亡 / 阵营博弈 / 情感羁绊 / 黑色幽默 / 史诗悲歌 / 谍战暗线 / 探险考古 / 孤岛求生，每局随机抽取
- **RAG 世界观**：ChromaDB 向量库 + 千问 text-embedding-v3，119 条世界观片段按需检索注入，AI 引用吻合设定

### 卡牌战斗

- **D20 判定**：1-5 MISS / 6-10 半伤 / 11-15 命中 / 16-19 重击 / 20 暴击 ×2.5，战斗属性加成
- **能量机制**：每回合 3 点能量，攻击/防御/技能消耗 1-2 点，道具免费，能量耗尽自动结束回合
- **四阶敌人**：杂兵 → 精锐 → 精英 → BOSS，按轮次概率出现，属性随轮次成长
- **道具卡**：武器/药物/情报/工具四类，关键词自动识别效果（伤害/回复/翻倍/眩晕），每张每场限用一次
- **特效动画**：出牌抖动、伤害浮动数字、HP 脉冲、屏幕闪光、胜利/战败动画

### 卡组构筑

- **基础卡组**：攻击(×5) + 防御(×3) + 全力一击(×2)，共 10 张
- **自定义编辑**：开战前自由调整卡牌数量，总上限 12 张，攻击≥3、防御≥1
- **神秘术商店**：纺锤购买尘酿鹰、缄默的负重、劫数难逃、安眠曲四张法术卡，编入卡组后生效

### 角色系统

- **四项属性**：洞察 / 魅力 / 战斗 / 学识，留空随机分配
- **全局 HP**：初始 12 点，战斗中受伤延续，治愈术/道具回复

### 核素浓度

- 默认安全递减（-2），极端危险递增（+3），单次上限 ±3，累积至 14 触发死亡结局
- 正值仅限：雨滴接触身体 / 被敌人击中流血 / 绝境濒死

### 其他

- **D20 强制检定**：高风险场景禁用选项必须掷骰（洞察/魅力/战斗/学识）
- **纺锤经济**：副 AI 按创造性/风险性/世界观契合打分，商店购买永久加成，跨存档保留
- **26 套故事框架**：每局随机抽取开场，包括 7 套新增原创剧本
- **道具背包**：副 AI 自动判定掉落，影响后续检定与战斗
- **安全路径提示**：副 AI 从选项中评估最安全选择
- **音效**：Web Audio API 合成，掷骰/收益/战斗/结局各有音效
- **存档**：localStorage 持久化，纺锤/加成/卡牌库存/自定义卡组跨存档保留

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python · FastAPI · LangChain |
| 主 AI | DeepSeek Chat (temperature 0.7, streaming) |
| 副 AI | DeepSeek Chat (temperature 0, 机制判定) |
| RAG | ChromaDB 1.5+ (sqlite3 直读) · 千问 text-embedding-v3 |
| 前端 | 原生 HTML/CSS/JS · 无框架 · Web Audio API |
| 风格 | 重返未来 1999 美术风格 · 英伦复古菱格纹 |

## 项目结构

```
├── api.py                  # FastAPI 后端，双 AI 调用 + RAG 检索 + 流式输出
├── rag_lite.py             # RAG 轻量引擎（sqlite3 直读 ChromaDB，无需 chromadb 包）
├── rag_engine.py           # ChromaDB 索引工具（需 chromadb 包）
├── deepseek.py             # DeepSeek 流式测试脚本
├── deploy.bat              # 一键部署脚本（零环境 → 运行）
├── requirements.txt        # 运行时 Python 依赖
├── requirements-reindex.txt # 重建 RAG 索引所需的额外依赖（chromadb）
├── hub.html                # 主菜单：新游戏/读档/神秘术商店/角色创建/成就
├── game.html               # 游戏主页面：叙事/骰点/战斗/卡组编辑/音效
├── .env.example            # 环境变量模板
├── chroma_data/            # 向量库数据（已纳入 Git）
└── world_lore_full.txt     # 世界观源文档
```

## 本地运行

### 方式一：一键部署（Windows，零环境）

**适用于全新电脑（连 Python 和 Git 都没有）。** 下载项目后双击 `deploy.bat`，脚本会自动完成：

| 步骤 | 内容 | 容错策略 |
|------|------|----------|
| 0 | 检测 Python，没有则自动安装 | curl → PowerShell → winget → 手动 |
| 1 | 检测项目文件，没有则克隆仓库 | GitHub → Gitee 镜像 |
| 2 | 创建 `.env` 配置，引导注册 API Key | 弹浏览器 + 记事本 |
| 3 | 安装 Python 依赖 | PyPI → 清华 → 阿里云 → 中科大镜像 |
| 4 | 检查/重建 RAG 向量索引 | 已有索引则跳过 |
| 5 | 启动服务器 `http://localhost:8000` | |

> **注意**：如果在编辑器里修改了 `deploy.bat`，务必确保文件换行符为 **CRLF**（Windows），不是 LF（Unix）。LF 换行符会导致 cmd.exe 解析错乱、闪退。

### 方式二：手动安装

```bash
# 1. 安装 Python 3.10+ → https://www.python.org/downloads/
#    安装时勾选 "Add Python to PATH"

# 2. 克隆仓库（GitHub 或 Gitee）
git clone https://github.com/huoyingfirefly/beforerain.git
:: 或国内镜像
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain

# 3. 配置 API Key
copy .env.example .env
:: 编辑 .env 填入你的密钥

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动
python api.py
```

浏览器访问 `http://localhost:8000`。

### API Key 获取

| 密钥 | 用途 | 注册地址 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | 主 AI 叙事 + 副 AI 判定 | https://platform.deepseek.com |
| `EMBED_API_KEY` | 向量检索（RAG） | https://cloud.siliconflow.cn (免费额度) |

> DeepSeek：充值 10 元够用数月。Embedding 也可用阿里云 DashScope (`https://dashscope.aliyuncs.com/compatible-mode/v1`, model: `text-embedding-v3`)。

## 服务器部署

```bash
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain
cp .env.example .env && nano .env
pip install fastapi uvicorn langchain-openai langchain-core python-dotenv openai numpy --break-system-packages

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

更新：`cd ~/beforerain && git pull && sudo systemctl restart beforerain`

## License

MIT
