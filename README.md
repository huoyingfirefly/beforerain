# 雨前演练 · Before the Rain

基于《重返未来 1999》世界观的互动剧本游戏。玩家在暴雨不断回溯的时间线中扮演角色，通过选择推动剧情，在每一次抉择中改写命运。

## 功能

- **互动剧本**：AI 驱动的文字冒险，每次选择影响故事走向
- **角色创建**：自由设定姓名、背景，分配洞察/魅力/战斗/学识四项属性
- **技能检定**：D20 骰点系统，根据属性判定行动成败
- **剧情框架**：内置暴雨预兆、第一防线、孤儿院时钟等可选剧本
- **纺锤商店**：剧情评分获得货币，购买加成道具
- **道具系统**：剧情中获得物品，影响后续选择
- **存档系统**：localStorage 存储，刷新/关闭不丢进度
- **死亡机制**：角色死亡后自动返回主界面，保留养成数据
- **流式输出**：AI 回复逐字显示，无需等待
- **手机适配**：600px 以下自动切换移动端布局

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python · FastAPI · LangChain |
| AI | DeepSeek API (兼容 OpenAI 格式) |
| 前端 | 原生 HTML/CSS/JS · 无框架 |
| 风格 | 重返未来 1999 美术风格 · 英伦复古菱格纹背景 |

## 本地运行

```bash
# 1. 安装依赖
pip install fastapi uvicorn langchain-openai langchain-core python-dotenv

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key

# 3. 启动
python api.py
```

浏览器访问 `http://localhost:8000`。

## 部署到服务器

```bash
# 服务器上克隆项目
git clone https://gitee.com/fire-flies/beforerain.git
cd beforerain

# 创建 .env 并填入 Key
cp .env.example .env && nano .env

# 安装依赖
pip3 install fastapi uvicorn langchain-openai langchain-core python-dotenv --break-system-packages

# 注册系统服务（开机自启 + 后台运行）
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

浏览器访问 `http://你的服务器IP:8000`。

## 项目结构

```
├── api.py              # FastAPI 后端，路由 + LLM 代理
├── hub.html            # 主菜单：新游戏/读档/商店/角色创建
├── game.html           # 游戏主页面：叙事/选择/骰点/背包
├── chat.html           # 旧版对话页面
├── deepseek.py         # DeepSeek API 测试脚本
├── .env.example        # 环境变量模板
└── .gitignore
```

## 游戏机制

### 属性系统
- **洞察**：观察环境、识破谎言、感知危险
- **魅力**：说服他人、伪装身份、获取信任
- **战斗**：格斗、武器使用、体能对抗
- **学识**：神秘术理解、典籍解读、历史认知
创建角色时分配 4 点，每项 1-3 级。AI 根据属性判定行动成败。

### 骰点检定
行动前点击 🎲 掷 D20：
- 16-20 大成功 · 11-15 成功 · 6-10 失败 · 1-5 大失败
AI 根据掷骰结果叙述行动后果。

### 纺锤经济
每次选择获得评分奖励（+2~20 纺锤），可在商店购买永久加成。

### 道具系统
AI 在剧情中奖励道具，存入背包。道具有效影响后续选择。

## License

MIT
