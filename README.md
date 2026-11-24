# Aura

Aura is a global generative-AI web application by **KCS - Koharu Coding Server**.

## Stack
- Next.js App Router, TypeScript and Tailwind CSS
- Supabase Auth, PostgreSQL and row-level security
- Kaggle for model training and artifact storage
- A server-side OpenAI-compatible inference gateway
- Vercel production hosting

## Local development
1. Install dependencies: `pnpm install`
2. Copy `.env.example` to `.env.local` and fill in the Supabase project values.
3. Configure a model inference gateway URL and server-only key.
4. Run `pnpm dev`.

## Environment variables
- `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`: Supabase publishable key
- `SUPABASE_DB_URL`: server-only Postgres URL (not exposed to browser code)
- `AURA_MODEL_API_URL`: OpenAI-compatible inference endpoint
- `AURA_MODEL_API_KEY`: optional server-only inference gateway key
- `AURA_INFERENCE_URL` / `AURA_GATEWAY_SECRET`: legacy Vercel production aliases supported by the chat route
- `NEXT_PUBLIC_APP_URL`: public app URL

Kaggle API authentication is configured separately in the Windows user environment as `KAGGLE_API_TOKEN`. A Kaggle API token authenticates Kaggle platform operations; it is not an online model inference URL and does not itself host a persistent model endpoint.

## Google OAuth setup
1. In Supabase Dashboard open **Authentication → Sign In / Providers → Google** and enable Google.
2. Paste the OAuth client ID and client secret from the Google Cloud OAuth client. Keep the client secret in Supabase Auth provider settings only; never add it to browser-visible `NEXT_PUBLIC_*` variables.
3. In Google Cloud Console, add this exact Authorized redirect URI:
   `https://jlfcajlrecnwycplvutp.supabase.co/auth/v1/callback`
4. Add `koharu.live` and `jlfcajlrecnwycplvutp.supabase.co` to the Google OAuth authorized domains.
5. In Supabase **Authentication → URL Configuration**, set Site URL to `https://aura.koharu.live` and add redirect URLs `https://aura.koharu.live/**` and `http://localhost:3000/**`.

## Database
The Supabase project contains `profiles`, `conversations` and `messages`. RLS policies scope profile, conversation and message access to the authenticated user. New Auth users receive a profile row through a database trigger.

## Legal and AI transparency
The app includes Terms, Privacy and AI Transparency pages. Before broad international launch, complete the operator's legal identity/address, region-specific processor and transfer disclosures, retention periods and contact details against the actual deployed infrastructure.

Never commit `.env.local`, OAuth client secrets, inference secrets, Kaggle credentials or model checkpoint files.


## Kaggle-hosted model inference

The trained Aura checkpoint is stored in the private Kaggle dataset `koharu81/aura-korean-chat-sft-v2-inference`. The private Kaggle inference notebook is `koharu81/aura-korean-chat-sft-v2-gpu-inference`; it loads the checkpoint and tokenizer directly from Kaggle, starts the FastAPI inference API, and connects the named Cloudflare Tunnel. The PC is not part of the serving path.

Vercel calls `https://inference.koharu.live/v1/chat/completions` server-to-server with `AURA_MODEL_API_KEY`. The Kaggle notebook reads the matching key from Kaggle Secrets under `AURA_GATEWAY_SECRET`. Set that Kaggle secret to the same value as the Vercel production `AURA_MODEL_API_KEY` before running the latest notebook version. Never commit the key or put it in browser-visible variables.

Kaggle notebook sessions are temporary and have runtime/accelerator quotas; they are suitable for cloud experiments and temporary inference, not guaranteed 24/7 production hosting. The current active runtime is CPU because the Kaggle GPU request was queued. A permanent global service needs an always-on inference host or managed GPU endpoint.

The current checkpoint is a 47.3M-parameter custom model. The training run completed 4,000 SFT steps (best checkpoint at step 3,900; validation loss 3.2658) using 23,742 training and 2,638 validation examples. The inference smoke test confirms the cloud endpoint responds, but generated text quality still needs substantial improvement before production launch.
