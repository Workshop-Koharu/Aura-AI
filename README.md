# Aura

Aura is an AI assistant web app by **KCS - Koharu Coding Server**.

## Stack

- Next.js App Router + TypeScript
- Tailwind CSS
- Supabase project configuration
- Kaggle-hosted model API through a server-side OpenAI-compatible adapter
- Vercel deployment

## Local development

1. Install dependencies with `pnpm install`.
2. Copy `.env.example` to `.env.local`.
3. Fill in the Supabase project settings and the model API endpoint.
4. Run `pnpm dev`.

## Environment

- `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`: Supabase publishable key
- `SUPABASE_DB_URL`: server-only PostgreSQL connection string
- `AURA_MODEL_API_URL`: server-side model inference endpoint
- `AURA_MODEL_API_KEY`: optional server-side model API key
- `NEXT_PUBLIC_APP_URL`: public app URL

Never commit `.env.local` or production credentials.
