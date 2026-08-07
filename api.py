import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv
from rag_lite import query_world, is_indexed, index_lore

load_dotenv()

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not is_indexed():
        try:
            n = index_lore()
            print(f"[RAG] 已索引 {n} 个世界观片段")
        except Exception as e:
            print(f"[RAG] 索引失败: {e}")
    else:
        print("[RAG] 世界观索引已存在")
    yield


app = FastAPI(title="DeepSeek API", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 主 AI：叙事
llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    temperature=0.7,
    streaming=True,
    max_tokens=2048,
)

# 副 AI：机制判定
mechanic_llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    temperature=0,
    streaming=False,
)

MECHANIC_PROMPT = """你是游戏机制判定AI，只输出标记。

【世界观简报】暴雨是雨水倒飞、时间回溯的灾难现象。触雨者被抹除。维尔汀是唯一露天免疫者。庇护方式仅三种：手提箱、基金会堡垒、天然庇护点。世界正被暴雨反复回溯，从1999年一路退到1966年。普通人挣扎求生，神秘学家各有专长。

根据玩家行动和主AI的叙事进行判定：

【纺锤评分——按以下维度逐项打分，总分=X纺锤】
- 创造性(0-4)：玩家选择是否独特、出人意料？
- 风险性(0-4)：是否选择了高风险选项？是否掷了D20？
- 世界观契合(0-4)：行动是否符合暴雨世界的设定逻辑？
三项分数相加即为纺锤数X。示例：创造性2+风险性3+契合2=[+7纺锤]

【道具掉落——按以下规则】
- 每轮根据场景自动判定：如果当前场景有可拾取物品（武器/文件/徽章/药物/工具等），输出[+道具:名称|一句话描述]
- 不需要每轮都给，只在场景中有自然可拾取物时才给

【战斗触发——卡牌战斗】
- 当主AI叙事中出现明确战斗场景：敌人拔刀/怪物扑来/面临致命威胁时，输出[战斗:敌人名]
- 敌人名必须是从主AI叙事中提取的具体描述（如"持断刀的重塑之手信徒"、"从雨幕中爬出的骨架聚合体"），不要泛泛写"敌人"
- 每局游戏中最多触发2-3次战斗，不要滥用。仅当战斗是叙事自然推进的必需环节时才触发
- 非战斗紧张的普通对抗/追逐/躲避场景不需要触发，留给强制检定处理

【强制检定——仅以下场景触发】
- 躲避暴雨/接触雨水、破解机关陷阱、对抗明显强于玩家的敌人、说服关键NPC改变立场
输出[强制检定:洞察/魅力/战斗/学识]

【非对称核素浓度】默认必须输出[核素-1]。以下三种情况才能输出正值（单次数值禁止超过+3）：(1)主AI叙事明确提到暴雨/触雨/雨滴直接威胁玩家→[核素+3] (2)主AI明确写到敌人持武器攻击玩家→[核素+2] (3)主AI明确写到玩家受伤或身处险境→[核素+1]。以上均不满足时输出[核素-1]。核素累积和失败由前端自动处理，你绝对不要输出[冒险失败]。
【安全路径】阅读主AI给出的3个选项，从中选出最能降低风险的那一个，输出[安全路径:X]（X为选项编号1/2/3）。如果没有明显安全的选项则不输出。

【胜利结算】
仅在以下情况触发：
(1) 玩家成功逃离了本次暴雨(抵达庇护所/进入手提箱/到达天然庇护点)
(2) 玩家完成了框架中的核心目标(救出关键人物/取得关键情报/击败敌方首领/揭开重要真相)
(3) 主AI叙事中明确写到玩家在庇护所内安顿或暴雨结束，且玩家完成了至少一项阶段性目标
格式：[冒险胜利:简要描述胜利成果]

只输出标记，不写解释。"""



class ChatRequest(BaseModel):
    prompt: str
    history: list[dict] = []
    system: str = ""


def build_messages(prompt: str, history: list[dict], system: str, rag_context: str = ""):
    messages = []
    if rag_context:
        system = system + "\n\n【RAG补充世界观】\n" + rag_context
    if system:
        messages.append(SystemMessage(content=system))
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))
    # 轮次计数：强制AI在20轮内收束
    round_num = len([m for m in history if m["role"] == "user"]) + 1
    if round_num >= 15:
        prompt = f"[第{round_num}轮/最多20轮，请尽快推进结局] " + prompt
    messages.append(HumanMessage(content=prompt))
    return messages


def stream_response(prompt: str, history: list[dict], system: str):
    # 先取 RAG 上下文（主AI和副AI共用）
    rag_context = query_world(prompt, n=8, pick=3)

    messages = build_messages(prompt, history, system, rag_context)
    full_response = ""
    for chunk in llm.stream(messages):
        if chunk.content:
            full_response += chunk.content
            yield chunk.content

    # 副 AI 追加机制标记
    try:
        mech_messages = [
            SystemMessage(content=MECHANIC_PROMPT),
            HumanMessage(content=f"玩家行动：{prompt}\n主AI回复：{full_response[-500:]}\n请输出机制标记。"),
        ]
        mech_resp = mechanic_llm.invoke(mech_messages)
        if mech_resp.content:
            yield "\n" + mech_resp.content.strip()
    except Exception:
        pass


@app.post("/chat")
def chat(req: ChatRequest):
    return StreamingResponse(
        stream_response(req.prompt, req.history, req.system),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "hub.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/chat-page")
def chat_page():
    return FileResponse(BASE_DIR / "chat.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/game")
def game():
    return FileResponse(BASE_DIR / "game.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.post("/rag/reindex")
def reindex():
    try:
        n = index_lore()
        return {"status": "ok", "chunks": n}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/rag/status")
def rag_status():
    return {"indexed": is_indexed()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
