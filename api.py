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

MECHANIC_PROMPT = """你是游戏机制判定AI，只输出标记，不写任何叙事文字。

根据以下交互内容判定并输出：
1. 纺锤奖励：[+X纺锤]，平庸1-3/机智5-8/惊艳9-12。每轮必须给。
2. 道具：[+道具:名|描述]，每3轮至少1次。
3. 强制检定：[强制检定:属性名]，仅极端危险场景。
4. 失败结局：[冒险失败:死因简述]，仅露天触暴雨/D20大失败叠加低属性/明确作死。必须在冒号后附上一句简短死因（如"暴雨抹除""被时序乱流吞没""重伤不治"）。

只输出上述标记，不要任何解释或其他文字。"""


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

    # 副 AI 追加机制标记（注入世界观上下文）
    try:
        mech_system = MECHANIC_PROMPT
        if rag_context:
            mech_system += "\n\n【世界观参考】\n" + rag_context[:800]
        mech_messages = [
            SystemMessage(content=mech_system),
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
