import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="DeepSeek API")

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
    temperature=0,
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


from fastapi import Response

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse("hub.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/chat-page")
def chat_page():
    return FileResponse("chat.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/game")
def game():
    return FileResponse("game.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


# ---------- 启动 ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
