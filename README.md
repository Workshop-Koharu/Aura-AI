# Aura AI

Aura AI is a modular AI application organized into three independently deployable components:

- **Core AI service** — Python API and orchestration, intended for Render.
- **API edge / tunnel** — Cloudflare-managed ingress and routing; secrets stay in environment configuration.
- **Web application** — separate frontend repository, intended for Vercel.

## Repository boundaries

- Core repository: `Workshop-Koharu/Aura-AI`
- Web repository: `Workshop-Koharu/Aura-AI-Web`
- Production branch target: `main`

## Initial implementation status

This repository currently contains the project logo only. The architecture and implementation contracts are being established before application logic is added. Repository access and the complete existing prompt/specification set must be verified before claiming compatibility with prior requirements.

## Configuration

Never commit API keys, tokens, private URLs, `.env` files, or credentials. Use environment variables and keep `.env.example` limited to variable names and safe placeholders.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Prompt and requirements index](docs/PROMPTS.md)
- [Implementation roadmap](docs/ROADMAP.md)
