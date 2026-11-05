# Architecture

## Runtime boundaries

- aura/models/transformer.py: random-initialized language, image and audio networks.
- aura/tokenizer.py: corpus-trained byte-level BPE.
- aura/training/runner.py: CPU-limited resumable training.
- aura/multimodal/preprocess.py: deterministic image and WAV preprocessing.
- aura/engine.py: local checkpoint loading and inference.
- api/main.py: local REST API and browser UI server.
- mcp_server/: stdio and streamable-HTTP MCP endpoints.
- web/: static responsive browser client.

## Data flow

Text documents are tokenized from scratch. Image-caption and WAV-transcript pairs condition the language model through independently initialized modality encoders. The encoders and decoder are optimized together by next-token prediction.

No pretrained embedding, model checkpoint, external inference endpoint, or hosted model is used.

## Planned cloud control plane

- GitHub: source, review, CI and release.
- Vercel: public static web shell and project previews.
- Cloudflare: edge security, DNS and optional Worker gateway.
- Supabase: auth, metadata and user-controlled sync.
- Render: queue/monitoring control plane only.

Cloud control plane services do not perform model inference.
