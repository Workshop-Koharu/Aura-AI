# Aura AI

Aura is a local-first AI research project. Its trainable weights are initialized randomly. It does not load Ollama, Hugging Face, pretrained checkpoints, or a third-party foundation model.

## What exists in this repository

- Decoder-only transformer language model (12 layers, 512 hidden width, 8 attention heads).
- Independently initialized image patch encoder and audio spectrogram encoder.
- Byte-level BPE tokenizer trained from the local corpus.
- Slow CPU training with resumable checkpoints and process resource limits.
- Local FastAPI interface, OpenAI-compatible chat endpoint, and MCP tools.
- Responsive chat UI with local conversation history, image/audio attachments, and microphone recording.
- PNG brand mark drawn programmatically with transparent background.

The model is an experimental from-scratch model, not a pretrained assistant. It will not be intelligent at first. It needs a large, high-quality, legally usable dataset and long training runs. A larger parameter count alone does not create intelligence.

## Hardware limits

Defaults are deliberately conservative for the i5-10400F / 16 GB RAM / GTX 1050 Ti machine:

- CPU only; GPU disabled.
- At most 4 logical CPU processors (about one third of 12 logical processors).
- 4 PyTorch intra-op threads and 1 inter-op thread.
- 5 GB process-RAM budget; training pauses if the process exceeds it.
- Batch size 1, sequence length 256, one optimizer update per batch.
- Below-normal process priority and a 0.75 second pause after each optimizer update.

No GPU VRAM is allocated for training. The GPU remains available to Windows and other applications.

## Start

~~~powershell
cd C:\Users\L\Downloads\Koharu\aura-ai
.\setup.ps1
.\start.ps1
~~~

Open http://127.0.0.1:8000

## Training data

- Text: add UTF-8 .txt files under data/text/.
- Images: place image files under data/image_text/ and add pairs.jsonl records such as {"file":"image_text/cat.jpg","text":"A cat sitting on a chair."}.
- Audio: place 16-bit PCM WAV files under data/audio_text/ and add pairs.jsonl records such as {"file":"audio_text/hello.wav","text":"안녕하세요."}.

Then use Model training in the app or POST /api/training/start. Training is resumed from data/checkpoints/latest.pt. Stop gracefully with the app or POST /api/training/stop.

Only data you have permission to use should be added. Do not put private or sensitive information into a dataset.

## API

- GET /api/health
- GET /api/model/status
- GET /api/training/status
- POST /api/training/start
- POST /api/training/stop
- GET /api/datasets
- POST /api/datasets/text
- POST /api/chat
- POST /api/chat/stream
- POST /v1/chat/completions
- GET /api/config

The chat body accepts message, optional image_base64, optional audio_base64, and max_tokens.

## MCP

Run a local stdio MCP server:

~~~powershell
.\start-mcp.ps1
~~~

Tools: health, model_info, generate_text, generate_with_image, generate_with_audio, training_status, start_training, stop_training, list_datasets, add_text_data.

For a local streamable-HTTP MCP endpoint on `http://127.0.0.1:8001/mcp`:

~~~powershell
.\start-mcp-http.ps1
~~~

Keep MCP bound to localhost. Do not expose local training or file operations directly to the public internet.

## Cloud deployment layout

The public web shell can be hosted on Vercel and protected by Cloudflare. Supabase is reserved for authentication and optional account metadata. Render is reserved for a queue/monitoring service. The local model weights and inference runtime stay on this PC; deploying the static UI does not make the local model remotely reachable.

Cloud integrations are intentionally not provisioned until the correct Render workspace and Supabase organization are confirmed. The local model must not silently fall back to hosted models.

## Brand

assets/aura-mark.png is a transparent PNG generated from deterministic vector-like drawing code. No generative image model is used.
