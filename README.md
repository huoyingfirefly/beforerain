# 雨前演练 · Before the Rain

基于《重返未来 1999》世界观的 AI 互动剧本游戏。暴雨倒飞，时间回溯，你的每一次选择都在改写命运。

## 功能

- **AI 叙事**：DeepSeek 驱动，流式输出，每局随机题材（悬疑/生存/阵营/情感/黑色/史诗）
- **双 AI 架构**：主 AI 负责叙事，副 AI 独立判定纺锤、道具、检定与失败结局
- **RAG 世界观**：ChromaDB 向量库 + 千问 Embedding，5 万字世界观按需检索注入
- **角色创建**：姓名、背景、四项属性（洞察/魅力/战斗/学识），留空随机分配
- **D20 骰点**：每轮限掷一次，赤金罗盘可增加重投次数，大成功/大失败戏剧性描写
- **强制检定**：AI 标记关键场景，禁用选项必须掷骰
- **纺锤商店**：剧情评分获得货币，购买永久加成（幸运之星/赤金罗盘/双蛇权杖/长青剑）
- **道具系统**：副 AI 自动判定道具掉落，背包收集影响后续检定
- **成就系统**：6 项成就自动解锁，主菜单展示进度
- **危险值系统**：前端累计危险行为自动触发失败结局，不依赖 AI
- **音效**：Web Audio 合成，掷骰/纺锤/道具/失败/结局各有音效
- **存档**：localStorage 持久化，刷新不丢，纺锤和加成跨存档保留
- **移动适配**：600px 以下自动切换布局

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python · FastAPI · LangChain |
| 主 AI | DeepSeek Chat (temperature 0.7) |
| 副 AI | DeepSeek Chat (temperature 0，判定机制) |
| RAG | ChromaDB (sqlite3 直读) · 千问 text-embedding-v3 |
| 前端 | 原生 HTML/CSS/JS · 无框架 |
| 风格 | 重返未来 1999 美术风格 · 英伦复古菱格纹 |

## 项目结构

```
├── api.py              # FastAPI 后端，路由 + 双 AI 调用 + RAG
├── rag_engine.py       # ChromaDB 索引工具（需 chromadb 包）
├── rag_lite.py         # RAG 轻量版（sqlite3 直读，无需 chromadb）
├── hub.html            # 主菜单：新游戏/读档/商店/角色创建/成就
├── game.html           # 游戏主页面：叙事/骰点/背包/音效
├── deepseek.py         # DeepSeek API 测试脚本
├── .env.example        # 环境变量模板
├── chroma_data/        # 向量库数据（已纳入 Git）
└── world_lore_full.txt # 世界观源文档（已 gitignore，不上传）
```

## 本地运行

```bash
# 安装依赖
pip install fastapi uvicorn langchain-openai langchain-core python-dotenv openai numpy

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入：
#   DEEPSEEK_API_KEY    DeepSeek 密钥（主/副 AI 共用）
#   EMBED_API_KEY       千问 Embedding 密钥
#   EMBED_BASE_URL      https://dashscope.aliyuncs.com/compatible-mode/v1
#   EMBED_MODEL         text-embedding-v3

# 启动
python api.py
```

浏览器访问 `http://localhost:8000`。

## 服务器部署

```bash
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain
cp .env.example .env && nano .env   # 填入 Key
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

## 游戏机制

### 属性系统
- **洞察**：观察、识谎、感知危险
- **魅力**：说服、伪装、获取信任
- **战斗**：格斗、武器、体能对抗
- **学识**：神秘术、典籍、历史认知

### D20 检定
- 1-5 大失败  ·  6-10 失败  ·  11-15 成功  ·  16-20 大成功
- 洞察每高一级 +1，赤金罗盘等级 = 额外重投次数

### 纺锤经济
- 每轮副 AI 强制给纺锤，平庸 +3~5 / 机智 +6~10 / 惊艳 +11~15
- 商店购买永久加成，跨存档保留

### 危险值系统
- 前端检测到暴雨/触雨/D20 大失败自动累加危险值
- 危险值 >= 5 有概率触发失败结局，>= 10 必定触发

## 路线图

- [x] 流式叙事 + 选项互动
- [x] 角色创建 + 四属性
- [x] D20 骰点 + 重投
- [x] 纺锤商店 + 永久加成
- [x] 道具背包系统
- [x] 成就系统
- [x] 死亡/失败/结局
- [x] RAG 世界观检索
- [x] 双 AI 架构
- [x] 音效系统
- [x] 移动适配
- [ ] 多存档槽位
- [ ] 主线章节框架
- [ ] NPC 好感度可视化

## License

MIT
