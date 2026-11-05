# Aura AI

Aura is an experimental generative AI service built around an independently initialized Transformer model. Its weights are trained from scratch; it does not rely on a pretrained foundation model or third-party model checkpoints.

## Model architecture

- Decoder-only Transformer language model.
- Independently initialized image patch encoder and audio spectrogram encoder.
- Byte-level BPE tokenizer trained on the project corpus.
- Resumable training with periodic checkpoints.
- HTTP inference API and multimodal request handling.

Aura is an experimental model, not a pretrained assistant. Initial checkpoints will produce low-quality output until the model has been trained on a sufficiently large, diverse, high-quality corpus. Parameter count alone does not create intelligence.

## Training data

- Text: UTF-8 TXT files under data/text/.
- Images: image files under data/image_text/ with matching pairs.jsonl captions.
- Audio: 16-bit PCM WAV files under data/audio_text/ with matching pairs.jsonl transcripts.

Only data that you have permission to use should be included. Do not put private or sensitive information into a training corpus.

## Training

The training runner resumes from data/checkpoints/latest.pt. It saves checkpoints periodically and continues from the previous global step after a runtime restart. Training progress depends on the size and quality of the corpus and available compute.

## API

- GET /api/health
- GET /api/model/status
- GET /api/training/status
- POST /api/training/start
- POST /api/training/stop
- GET /api/datasets
- POST /api/datasets/text
- POST /api/datasets/image
- POST /api/datasets/audio
- POST /api/chat
- POST /api/chat/stream
- GET /v1/models
- POST /v1/chat/completions

## Local development

Run the setup script, start the API process, and open the local address printed by the launcher. Keep administrative and training endpoints private; do not expose them directly to the public internet.

## Brand

assets/aura-mark.png is the project's programmatically generated transparent brand mark.
