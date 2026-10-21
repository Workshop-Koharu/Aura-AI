# Aura AI

Aura AI is being developed as its **own language model**, initialized with random weights and trained from text data. It does not call OpenAI, another hosted model, or a third-party inference API, and it does not fine-tune a pretrained model.

## Current implementation
- `aura/tokenizer.py`: deterministic UTF-8 byte tokenizer with BOS/EOS tokens.
- `aura/model.py`: decoder-only causal Transformer implemented with PyTorch.
- `aura/train.py`: next-token prediction training loop, validation loss, gradient clipping, and checkpoint saving.
- `aura/inference.py`: autoregressive generation from Aura's own checkpoint.
- `app/main.py`: FastAPI health and chat endpoints. Chat returns HTTP 503 until a trained checkpoint exists; it never silently falls back to an external model.
- Web app: separate repository `Workshop-Koharu/Aura-AI-Web`, deployed through Vercel.

This is a small research prototype, not yet a generally capable assistant. Randomly initialized weights do not contain language knowledge; useful behavior requires a sufficiently large, legally usable corpus, substantial training, evaluation, and suitable compute.

## 1. Set up Python
Use Python 3.11 or 3.12 for smooth local compatibility:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

The project pins the CPU-only PyTorch build for deployment. Render's environment must include `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu` so pip can resolve the `+cpu` wheel without pulling the much larger CUDA distribution. Local Windows installs can use the same setting, or install the matching CPU build from PyTorch's official CPU wheel index.

## 2. Prepare training data
Create `data/train.txt` in UTF-8 containing text you wrote or have permission to use. Do not include secrets, private messages, or copyrighted content without appropriate rights. Byte tokenization supports Korean but uses multiple tokens per character. The model requires at least 148 tokens to exercise the training pipeline; a tiny corpus is only a smoke test, not enough for a useful assistant.

## 3. Train from random initialization
```powershell
python -m aura.train --data data/train.txt --steps 3000 --batch-size 16
```
Default configuration: 4 Transformer blocks, width 128, context length 128, vocabulary size 258. Training reports train/validation loss and saves `models/checkpoints/aura-small.pt`. Checkpoints and the corpus are ignored by Git because they may be large or private. For deployment, provide the checkpoint through private artifact storage; do not commit large model files to source control.

Optional `--device auto|cpu|cuda`. CPU training may be slow; CUDA training requires a separate CUDA-enabled PyTorch install, not the deployment CPU wheel.

## 4. Run the API
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- `GET /health`: service liveness and whether a checkpoint file exists.
- `POST /v1/chat`: autoregressive generation only if the checkpoint exists and loads; otherwise HTTP 503 with a clear not-trained message.

Example body: `{"messages":[{"role":"user","content":"안녕하세요"}]}`

## Deployment note
Render free instances have limited CPU/RAM; PyTorch loading may cause slow cold starts or memory exhaustion. A trained checkpoint must be made available on the service filesystem or fetched from authenticated artifact storage. Train on a local GPU or dedicated compute, not on a free web-service instance. No external model API key is required or used.

## Repositories
- Core: `Workshop-Koharu/Aura-AI` (branch `main`).
- Web: `Workshop-Koharu/Aura-AI-Web` (Vercel domain `aura.koharu.live`).
- API: `api-aura.koharu.live`.

> **Project identity:** Aura AI is an independently developed personal project, not a project created or operated by the National Information Society Agency (NIA). Where NIA datasets are used, their required attribution is retained as data-source attribution only; each dataset’s separate license and terms still apply.
