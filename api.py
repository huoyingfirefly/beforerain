import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from rag_lite import query_world, is_indexed, index_lore

load_dotenv()

# 项目根目录（api.py 所在目录）
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

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- LLM 实例 ----------
llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    temperature=0.7,
    streaming=True,
)


from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ---------- 请求体 ----------
class ChatRequest(BaseModel):
    prompt: str
    history: list[dict] = []   # [{role: "user"|"ai", content: "..."}, ...]
    system: str = ""           # 系统提示词（世界观设定）


# ---------- 构建消息 ----------
def build_messages(prompt: str, history: list[dict], system: str):
    messages = []
    # RAG 检索：根据用户输入找最相关世界观片段
    rag_context = query_world(prompt, n=3)
    if rag_context:
        system = system + "\n\n【补充世界观（RAG检索）】\n" + rag_context
    if system:
        messages.append(SystemMessage(content=system))
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=prompt))
    return messages


# ---------- 流式输出 ----------
def stream_response(prompt: str, history: list[dict], system: str):
    messages = build_messages(prompt, history, system)
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content


# ---------- 接口 ----------
@app.post("/chat")
def chat(req: ChatRequest):
    """流式聊天接口（支持上下文）"""
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


# ---------- 启动 ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
