from __future__ import annotations
import os, sys, time, uuid
from pathlib import Path
from typing import Any
import torch
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
MODEL_ROOT = Path(os.environ.get("AURA_MODEL_DIR", ROOT / "kaggle" / "aura-ai-korean-chat-sft-v2" / "outputs" / "Aura-AI")).resolve()
sys.path.insert(0, str(MODEL_ROOT))
from aura.config import MODEL, TOKENIZER_PATH
from aura.models.transformer import AuraModel
from aura.tokenizer import AuraTokenizer, EOS, BOS

SYSTEM_PROMPT = (
 "너는 Aura AI다. 자연스럽고 정확한 한국어로 답한다. "
 "질문에 직접 답하고 근거 없는 사실을 만들지 않는다. "
 "불확실한 정보는 불확실하다고 밝히며, 이전 대화의 맥락과 조건을 유지한다."
)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.set_num_threads(max(1, int(os.environ.get("AURA_TORCH_THREADS", "4"))))
if DEVICE.type == "cuda":
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

tokenizer = AuraTokenizer.load(TOKENIZER_PATH)
if tokenizer.vocab_size != MODEL.vocab_size:
    raise RuntimeError(f"Tokenizer/model vocab mismatch: {tokenizer.vocab_size} != {MODEL.vocab_size}")
checkpoint_path = MODEL_ROOT / "data" / "checkpoints" / "best_chat_sft.pt"
checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model = AuraModel(MODEL)
model.load_state_dict(checkpoint["model"], strict=True)
model.to(DEVICE).eval()
MODEL_INFO = {"name":"Aura Korean Chat SFT v2","step":checkpoint.get("step"),"validation_loss":checkpoint.get("validation_loss"),"device":str(DEVICE),"parameters":sum(p.numel() for p in model.parameters())}

app=FastAPI(title="Aura Inference",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["https://aura.koharu.live"],allow_methods=["GET","POST"],allow_headers=["Authorization","Content-Type"])

class Message(BaseModel):
 role:str
 content:str
class ChatRequest(BaseModel):
 model:str="aura"
 messages:list[Message]
 max_tokens:int=Field(default=128,ge=1,le=192)
 temperature:float=Field(default=0.7,ge=0.1,le=1.5)
 top_k:int=Field(default=30,ge=1,le=80)
 stream:bool=False

def authorize(auth:str|None):
 secret=os.environ.get("AURA_GATEWAY_SECRET","")
 if secret and auth!="Bearer "+secret:
  raise HTTPException(status_code=401,detail="Unauthorized")

def prompt_ids(messages:list[Message])->list[int]:
 ids=[BOS]
 for m in messages:
  role=m.role if m.role in {"system","user","assistant"} else "user"
  content=m.content[:12000]
  ids.extend(tokenizer.encode(f"<|{role}|>\n{content}\n",add_special=False))
 ids.extend(tokenizer.encode("<|assistant|>\n",add_special=False))
 return ids[-MODEL.max_seq_len:]

@app.get("/health")
def health():
 return {"ok":True,"model":MODEL_INFO}

@app.get("/v1/models")
def models(authorization:str|None=Header(default=None)):
 authorize(authorization)
 return {"object":"list","data":[{"id":"aura","object":"model","owned_by":"KCS"}]}

@app.post("/v1/chat/completions")
def completions(req:ChatRequest,authorization:str|None=Header(default=None)):
 authorize(authorization)
 if not req.messages or req.messages[-1].role!="user":
  raise HTTPException(status_code=400,detail="The last message must be from the user.")
 messages=[Message(role="system",content=SYSTEM_PROMPT)]+req.messages[-12:]
 ids=prompt_ids(messages)
 input_ids=torch.tensor([ids],dtype=torch.long,device=DEVICE)
 start=time.time()
 try:
  with torch.inference_mode():
   output=model.generate(input_ids,max_new_tokens=req.max_tokens,temperature=req.temperature,top_k=req.top_k)
  generated=output[0,len(ids):].tolist()
  if EOS in generated: generated=generated[:generated.index(EOS)]
  content=tokenizer.decode(generated).strip()
  if not content: content="답변을 생성하지 못했습니다. 질문을 조금 다르게 입력해 주세요."
 except torch.cuda.OutOfMemoryError:
  if DEVICE.type=="cuda": torch.cuda.empty_cache()
  raise HTTPException(status_code=503,detail="Inference memory limit exceeded.")
 except Exception as exc:
  raise HTTPException(status_code=500,detail="Inference failed: "+type(exc).__name__)
 return {"id":"chatcmpl-"+uuid.uuid4().hex,"object":"chat.completion","created":int(time.time()),"model":"aura","choices":[{"index":0,"message":{"role":"assistant","content":content},"finish_reason":"stop"}],"usage":{"prompt_tokens":len(ids),"completion_tokens":len(generated),"total_tokens":len(ids)+len(generated)},"latency_seconds":round(time.time()-start,3)}
