# Aura AI API — Developer Reference

## Overview

- Base URL: `https://api-aura.koharu.live`
- Protocol: HTTPS, JSON REST, Server-Sent Events (SSE)
- API framework: FastAPI / Uvicorn
- Interactive schema: `/docs`; OpenAPI JSON: `/openapi.json`
- The API runs Aura's own experimental decoder-only Transformer. It does not proxy to a hosted third-party language model.

## Technology stack

| Layer | Technology |
| --- | --- |
| Model | PyTorch, decoder-only causal Transformer |
| Tokenizer | UTF-8 byte tokenizer |
| Inference | Python autoregressive decoding |
| API | FastAPI, Pydantic, Uvicorn |
| Browser app | Next.js, React, TypeScript |
| Hosting | Vercel web app, Render API service |
| Progress events | SSE (`text/event-stream`) |

## Endpoints

### `GET /`
Returns service metadata and the API documentation path.

### `GET /health`
Returns `status`, `model_ready`, `model_type`, and (in the current code version) `progress_stream`. A healthy HTTP service does not guarantee that a model checkpoint is available.

### `POST /v1/chat`
Generates a reply synchronously.

Request:

```json
{
  "messages": [
    { "role": "user", "content": "안녕하세요." }
  ]
}
```

Validation: `messages` contains 1–40 items. Each item has role `user` or `assistant`; `content` is 1–8,000 characters.

Response (`200 OK`):

```json
{ "reply": "모델이 생성한 답변" }
```

### `POST /v1/chat/stream`
Sends user-facing progress events and then a final reply. This is a progress/status stream, not token-by-token generation. Private chain-of-thought is never sent to clients.

Example events:

```text
event: progress
data: {"stage":"received","message":"요청을 확인했어요."}

event: progress
data: {"stage":"generating","message":"자체 Transformer가 답변을 생성하고 있어요."}

event: complete
data: {"reply":"모델이 생성한 답변","message":"답변 생성이 완료됐어요."}
```

An error may be sent as `event: error` with a JSON `message` field. Clients should also handle non-2xx HTTP responses before reading the stream.

## Sample code

### cURL

```bash
curl -X POST https://api-aura.koharu.live/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"안녕하세요."}]}'
```

### JavaScript / TypeScript

```ts
const response = await fetch("https://api-aura.koharu.live/v1/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    messages: [{ role: "user", content: "안녕하세요." }],
  }),
});
if (!response.ok) throw new Error(`Aura API: ${response.status}`);
const data: { reply: string } = await response.json();
console.log(data.reply);
```

### Python

```python
import requests

response = requests.post(
    "https://api-aura.koharu.live/v1/chat",
    json={"messages": [{"role": "user", "content": "안녕하세요."}]},
    timeout=90,
)
response.raise_for_status()
print(response.json()["reply"])
```

## Errors and operational notes

- `400` / `422`: request validation or malformed payload.
- `503`: model checkpoint is missing or the model is not ready.
- `500`: unexpected server-side failure.
- Network/CORS errors: check service availability, allowed origins, DNS, and HTTPS configuration.

The model is an experimental small research prototype; answers can be incorrect or nonsensical. Model weights must be present in the deployed service filesystem. Do not send sensitive personal information. The API does not currently provide per-user accounts or server-side conversation history. Public rate limits and access policy depend on deployment configuration.

## Local development

```bash
python -m venv .venv
# activate the environment, then:
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive API exploration. Run `python -m pytest -q` and `ruff check app aura tests --select F,I` before publishing changes.
