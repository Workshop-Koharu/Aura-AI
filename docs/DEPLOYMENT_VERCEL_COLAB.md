# Aura deployment: Vercel + Colab inference + Supabase

## Architecture
- Vercel root: web/ (static UI and one small Node gateway)
- Colab: temporary GPU inference runtime; not a guaranteed 24/7 host
- Supabase: authentication and Postgres
- GitHub: source of truth

## Why the old Vercel build failed
The root pyproject.toml declares torch and other machine-learning packages. Vercel detected the Python app and attempted to package the model runtime (5.3 GB), exceeding the standard Python function bundle limit. The web project now lives under web/ and has no Python dependency manifest. Vercel must use web/ as its Root Directory. The tiny Node gateway forwards authenticated requests to AURA_INFERENCE_URL.

## Vercel settings
Project: aura-ai
Root Directory: web
Framework Preset: Other
Build Command: leave empty
Output Directory: leave empty
Install Command: leave empty
Production Branch: main

Environment variables:
- SUPABASE_URL = https://YOUR_SUPABASE_REF.supabase.co
- SUPABASE_PUBLISHABLE_KEY = sb_publishable_...
- AURA_INFERENCE_URL = https://YOUR_COLAB_TUNNEL_HOST
- AURA_GATEWAY_SECRET = long random secret shared with the inference runtime

Never set the Postgres password or Supabase service_role key in browser-exposed variables.

## Colab quick start
1. Open the notebook colab/Aura_Inference_Colab.ipynb in Google Colab.
2. Choose Runtime > Change runtime type > GPU (if available).
3. Run the setup cell. It clones the public GitHub repository.
4. Run the Drive cell to persist data/checkpoints.
5. Set AURA_GATEWAY_SECRET as a Colab Secret named AURA_GATEWAY_SECRET.
6. Run the inference cell. It starts Uvicorn and a Cloudflare quick tunnel.
7. Copy the HTTPS tunnel URL (hostname only, no trailing slash) into Vercel's AURA_INFERENCE_URL.
8. Redeploy Vercel. Sign in to Aura and test /api/health, then send a prompt.

Quick tunnels use temporary hostnames and change when the runtime restarts. For a stable hostname, configure a named Cloudflare Tunnel under an account/domain you control and store its token in Colab Secrets. Never commit the tunnel token.

## 24/7 limitation
Google Colab is an interactive notebook service. Free runtimes can terminate, generally run for up to 12 hours, and are not guaranteed. Colab Pro+ may support up to 24 hours with sufficient compute units, but this is still not an always-on production server. For reliable 24/7 global inference, use a dedicated GPU VM or managed GPU inference service. Do not use scripts that simulate user activity or bypass Colab runtime limits.

## Supabase credentials
A database connection URI was pasted into a chat. Treat its database password as exposed and rotate it in Supabase Dashboard > Project Settings > Database > Reset database password before using it. This repo intentionally contains no real database password. The project reference in the supplied hostname was not visible in the currently connected Supabase project list, so confirm the project and access before applying migrations.
Use the Supabase Data API with the publishable key for browser auth; keep database credentials and secret/service_role keys server-side.

## Legal pages
- /privacy
- /terms
Replace the bracketed operator legal name and support email before public launch. Confirm retention, subprocessors, transfer regions, and minimum age policy with the actual deployed configuration.
