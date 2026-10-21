# Aura AI

Aura AI is being developed as its **own language model**, initialized with random weights and trained from text data. It does not call OpenAI, another hosted model, or a third-party inference API, and it does not fine-tune a pretrained model.

## Current implementation
- `aura/tokenizer.py`: deterministic UTF-8 byte tokenizer with BOS/EOS tokens.
- `aura/model.py`: decoder-only causal Transformer implemented with PyTorch and memory-efficient scaled dot-product attention.
- `aura/train.py`: memory-mapped next-byte training, small-batch sampling, validation loss, gradient clipping, and periodic checkpoint saving.
- `aura/inference.py`: autoregressive generation from Aura's own checkpoint.
- `app/main.py`: FastAPI health and chat endpoints; chat only responds when the checkpoint is present and loadable.
- `models/checkpoints/aura-small.pt`: small trained checkpoint included as a deployment artifact so the API service can load a model. The raw corpus is not committed.
- Web app: separate repository `Workshop-Koharu/Aura-AI-Web`, deployed through Vercel.

This is a small research prototype, not a generally capable assistant. A working generation endpoint does not imply high-quality, factual, or safe answers. Useful behavior requires a sufficiently large, legally usable corpus, substantial training, evaluation, and suitable compute.

## 1. Set up Python
Use Python 3.11 or 3.12 for smooth local compatibility:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

The project pins a CPU PyTorch build for deployment. Render's environment must include `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu` so pip can resolve the CPU wheel. Local Windows installs can use the matching CPU build. A CUDA-enabled install requires a compatible NVIDIA GPU, driver, and matching PyTorch build.

## 2. Prepare training data
`data/train.txt` is generated locally from text data the project is permitted to use. The current corpus is about 20.5 GB. Do not commit `data/train.txt`, `data/source/`, or private data. Byte tokenization supports Korean but represents characters as UTF-8 bytes, which may require several tokens per character.

## 3. Train from random initialization

Low-memory CPU example:

```powershell
python -m aura.train --data data/train.txt --steps 3000 --batch-size 1 --threads 1 --log-every 25 --checkpoint-every 250 --device cpu
```

The trainer memory-maps the corpus instead of loading the full text into RAM. The current configuration has 4 Transformer blocks, width 128, context length 128, and vocabulary size 258. The default checkpoint path is `models/checkpoints/aura-small.pt`.

The checked-in checkpoint is a small initial deployment artifact trained for 3,000 optimizer steps on the local corpus. Further training overwrites it locally; evaluate it before replacing the deployed artifact. Loss reduction alone does not guarantee useful responses.

## 4. Run the API locally

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- `GET /health`: service liveness and whether a checkpoint file exists.
- `POST /v1/chat`: autoregressive generation from the local checkpoint.
- `GET /docs`: interactive API documentation.

Example request body: `{"messages":[{"role":"user","content":"Hello"}]}`.

## 5. Deploy

- Core/API repository: `Workshop-Koharu/Aura-AI`, branch `main`.
- Web repository: `Workshop-Koharu/Aura-AI-Web`, branch `main`.
- Web domain: `https://aura.koharu.live`.
- API domain: `https://api-aura.koharu.live`.
- Render blueprint: `render.yaml`.

The API requires the checkpoint to exist in the deployed filesystem. The included checkpoint is small enough to ship with this source repository; do not upload raw datasets to GitHub. Render free instances have limited CPU/RAM and may have cold starts. For a much larger model, use a private artifact store or suitable persistent storage instead of committing model weights.

## Dataset attribution and project identity

Aura AI is an independently developed personal project, not a project created or operated by the National Information Society Agency (NIA). Where NIA datasets are used, the required attribution is retained as data-source attribution only; each dataset's separate license and terms still apply.

Required NIA data attribution:

> 본 AI데이터 등을 이용할 때에는 반드시 한국지능정보사회의 사업결과임을 밝혀야 하며, 본 AI데이터 등을 이용한 2차적 저작물에도 동일하게 밝혀야 합니다.

Check the dataset's original terms for the exact attribution wording required by its provider.
