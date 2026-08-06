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
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    model=os.getenv("DEEPSEEK_MODEL", "qwen3-flash"),
    temperature=0,
    max_tokens=150,
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
仅当主AI叙事中明确出现了玩家尚未拥有的全新物品（武器/文件/药物/工具等）且玩家主动拾取时才输出。以下物品绝对禁止作为道具掉落：金爪灵摆、赤金罗盘、双蛇权杖、长青剑、分辨善恶之果、幸运之星，以及主AI叙事中玩家已携带或使用的任何物品。如果一个场景没有全新物品，不要无中生有。大多数场景不输出道具标记。

【强制检定 — 仅特定场景】
仅以下触发：躲避暴雨/接触雨水、破解机关陷阱、对抗强于玩家的敌人、说服关键NPC改变立场。
格式：[强制检定:洞察] 或 [强制检定:魅力] 或 [强制检定:战斗] 或 [强制检定:学识]

【非对称核素浓度 — 必须输出】
默认安全场景输出 [核素-1]。仅当主AI叙事中出现以下情况时输出正值（最多一条，禁止自行加总）：
(1) 主AI明确写到暴雨/雨滴将接触到玩家且玩家无防护 → [核素+3]
(2) 主AI明确写到敌人发动攻击命中玩家 → [核素+2]
(3) 主AI明确写到玩家受伤流血 → [核素+1]
以上条件均不满足时必须输出 [核素-1]。核素累积由前端处理，不要输出[冒险失败]。

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
    # 用系统提示（含框架） + 玩家行动组合查询，提高检索精准度
    rag_query = system[:800] + " " + prompt
    rag_context = query_world(rag_query)

    messages = build_messages(prompt, history, system, rag_context)
    full_response = ""
    for chunk in llm.stream(messages):
        if chunk.content:
            full_response += chunk.content
            yield chunk.content

    # 信号：主AI叙事完成，前端可以立即渲染
    yield "\n[MAIN_DONE]\n"

    # 副 AI 追加机制标记（不阻塞前端渲染）
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
