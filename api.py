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
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    model=os.getenv("DEEPSEEK_MODEL", "qwen3-flash"),
    temperature=0.7,
    streaming=True,
    max_tokens=2048,
)

# 副 AI：机制判定
mechanic_llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    model=os.getenv("DEEPSEEK_MODEL", "qwen3-flash"),
    temperature=0,
    streaming=False,
)

MECHANIC_PROMPT = """你是游戏机制判定AI。你只输出无格式标记，不输出任何解释、分析、或额外文字。

【世界观简报】暴雨是雨水倒飞、时间回溯的灾难现象。触雨者被抹除。维尔汀是唯一露天免疫者。庇护方式仅三种：手提箱、基金会堡垒、天然庇护点。世界正被暴雨反复回溯，从1999年一路退到1966年。普通人挣扎求生，神秘学家各有专长。

根据玩家行动和主AI叙事进行判定，严格按以下格式输出，一行一个标记：

【纺锤评分 — 必须输出】
三项打分(创造性0-4 + 风险性0-4 + 世界观契合0-4)，只输出总分标记。
正确格式：[+8纺锤]
禁止格式：[纺锤:创造性3+风险性1+世界观契合4=[+8纺锤]]
禁止输出计算过程，直接给总分。

【道具掉落 — 可选】
场景有自然可拾取物时输出。格式：[+道具:名称|一句话描述]
不要每轮都给，没东西就不输出。

【强制检定 — 仅特定场景】
仅以下场景触发：躲避暴雨/接触雨水、破解机关陷阱、对抗明显强于玩家的敌人、说服关键NPC改变立场。
格式：[强制检定:洞察] 或 [强制检定:魅力] 或 [强制检定:战斗] 或 [强制检定:学识]

【非对称核素浓度 — 必须输出】
你假设场景安全为默认。仅以下三种情况输出正值：
(1) 主AI叙事明确提到暴雨/触雨/雨滴攻击玩家 → [核素+3]
(2) 主AI明确写到敌人持武器攻击玩家 → [核素+2]
(3) 主AI明确写到玩家受伤或身处险境 → [核素+1]
以上三种均不满足时必须输出 [核素-1] 或 [核素-2]。
浓度≥10时输出 [冒险失败:死因简述]。

【安全路径 — 可选】
从3个选项中选出风险最低的。格式：[安全路径:1]（X为1/2/3）
没有明显安全选项则不输出。

【胜利结算 — 可选】
仅当玩家成功逃离本次暴雨(抵达庇护所/进入手提箱/到达天然庇护点)、或完成框架核心目标、或主AI明确写到玩家在庇护所内安顿/暴雨结束时触发。
格式：[冒险胜利:简述成果]

【输出模板 — 严格遵循】
每轮你最简输出为两行：
[+X纺锤]
[核素±X]

有额外事件时追加对应标记。绝对禁止输出任何解释、推导、分析文字。只输出标记。"""



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
