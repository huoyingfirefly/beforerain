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

MECHANIC_PROMPT = """你是游戏机制判定AI。绝对禁止输出解释、分析或额外文字，只输出格式标记，一行一个。

【世界观简报】暴雨是雨水倒飞、时间回溯的灾难现象。触雨者被抹除。维尔汀是唯一露天免疫者。庇护方式仅三种：手提箱、基金会堡垒、天然庇护点。世界正被暴雨反复回溯，从1999年一路退到1966年。普通人挣扎求生，神秘学家各有专长。

【纺锤评分 — 必须输出】
三项打分(创造性0-4 + 风险性0-4 + 世界观契合0-4)，只输出总分。
正确格式：[+8纺锤]
禁止格式：[纺锤:创造性3+风险性1+契合4=+8] [纺锤:…=+8纺锤] 等任何带计算过程的写法。

【道具掉落 — 可选】
格式：[+道具:名称|一句话描述]
只在场景中有自然可拾取物(武器/文件/徽章/药物/工具等)时才输出，没东西就不输出。

【强制检定 — 仅特定场景】
仅以下触发：躲避暴雨/接触雨水、破解机关陷阱、对抗强于玩家的敌人、说服关键NPC改变立场。
格式：[强制检定:洞察] 或 [强制检定:魅力] 或 [强制检定:战斗] 或 [强制检定:学识]

【非对称核素浓度 — 必须输出】
默认安全。仅以下三种输出正值（注意数值已降低，不要自行上调）：
(1) 主AI明确写到暴雨/触雨/雨滴直接攻击或即将吞噬玩家 → [核素+2]
(2) 主AI明确写到敌人持武器攻击玩家且玩家处于危险中 → [核素+1]
(3) 主AI明确写到玩家受伤流血或身处致命险境 → [核素+1]
以上均不满足时输出 [核素-1] 或 [核素-2]。
浓度≥10时输出 [冒险失败:死因简述]。

【安全路径 — 可选】
从3选项中选风险最低的。格式：[安全路径:1]（数字1/2/3）
无安全选项则不输出。

【胜利结算 — 严格禁止速通】
主AI有轮次限制(16轮后才可触发)。你判定胜利时必须确认：(1)玩家已抵达明确命名的庇护所 (2)框架核心目标已完成且至少经过3轮叙事铺垫。若主AI在前16轮内输出[冒险胜利]，你必须忽略它——改为继续正常判定纺锤/核素/道具。仅当16轮后且条件满足时，才输出 [冒险胜利:简述成果]。

最终输出范例（每轮基本格式）：
[+5纺锤]
[核素-1]"""



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
