from fastapi import FastAPI
from pydantic import BaseModel
import requests as req_lib
import uvicorn

VLLM_URL = "http://localhost:11434"
MODEL_NAME = "/datadisk/home/lsr/qwen2.5-72b-awq"

app = FastAPI(title="Quant-Qwen3 Inference API")


class ChatRequest(BaseModel):
    prompt: str
    system: str = "你是专业A股AI产业链分析师,直接输出结论,不要思考过程。使用中文。"
    max_tokens: int = 1024
    temperature: float = 0.3
    use_lora: bool = False


class ChatResponse(BaseModel):
    content: str





@app.get("/health")
def health():
    try:
        resp = req_lib.get(f"{VLLM_URL}/v1/models", timeout=5)
        models = [m.get("id", "") for m in resp.json().get("data", [])] if resp.ok else []
        return {"status": "ok", "vllm": "running", "models": models}
    except Exception as e:
        return {"status": "error", "vllm": str(e)}


@app.post("/generate", response_model=ChatResponse)
def generate(req: ChatRequest):
    model = "finance-lora" if req.use_lora else MODEL_NAME
    messages = [
        {"role": "system", "content": req.system},
        {"role": "user", "content": req.prompt},
    ]
    try:
        resp = req_lib.post(
            f"{VLLM_URL}/v1/chat/completions",
            json={"model": model, "messages": messages,
                  "max_tokens": req.max_tokens, "temperature": req.temperature},
            timeout=120,
        )
        if resp.status_code == 200:
            return ChatResponse(content=resp.json()["choices"][0]["message"]["content"])
        return ChatResponse(content=f"vLLM错误: HTTP {resp.status_code}")
    except Exception as e:
        return ChatResponse(content=f"调用失败: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=11435)
