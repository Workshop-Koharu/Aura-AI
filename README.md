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


## Kaggle-trained model inference

The Aura Korean Chat SFT v2 Kaggle kernel is the training job, not a permanent public inference server. The completed model artifacts are downloaded into the ignored local path `kaggle/aura-ai-korean-chat-sft-v2/outputs/Aura-AI`. The local GPU inference API loads `best_chat_sft.pt` and its paired `aura-bpe.json` tokenizer and exposes an OpenAI-compatible `/v1/chat/completions` endpoint.

The Cloudflare Tunnel `aura-ai-api` routes `https://inference.koharu.live` to the local API on port 8000. Vercel calls this endpoint server-to-server with the secret `AURA_MODEL_API_KEY`; the secret is never exposed to browser code. PostgreSQL remains storage only.

Run `start-aura-inference.ps1` after signing in to Windows to start the model API and tunnel. A Windows Scheduled Task named `Aura AI Inference` is configured to do this at logon. The PC must remain powered on, awake, connected to the internet, and running the GPU API for inference requests to succeed. Kaggle notebook sessions themselves are not used as always-on serving infrastructure.

The current checkpoint is a 47.3M-parameter custom model. The training run completed 4,000 SFT steps (best checkpoint at step 3,900; validation loss 3.2658) using 23,742 training and 2,638 validation examples. The current smoke tests show that response quality still needs substantial improvement before describing the model as production-quality or globally scalable.
