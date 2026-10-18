# Aura AI — Architecture Baseline

## 1. Design goals

- Separate UI, application API, and infrastructure ingress.
- Keep provider-specific integrations behind explicit interfaces.
- Validate all external input and return consistent errors.
- Keep secrets out of source control and logs.
- Make local development independent of production credentials.
- Add automated tests before expanding features.

## 2. Logical components

```text
Browser
  └── Vercel-hosted Web App
        └── HTTPS API base URL
              └── Cloudflare ingress / Tunnel
                    └── Render-hosted Python API
                          ├── request validation
                          ├── application / agent orchestration
                          ├── model-provider adapter
                          └── health and readiness endpoints
```

The tunnel is an ingress mechanism, not an application API. The API remains responsible for authentication, authorization, validation, rate limits, and response contracts.

## 3. Core API baseline

- `GET /health`: process liveness, no dependency secrets or internal diagnostics.
- `GET /ready`: readiness for required dependencies; add only when dependency checks are defined.
- `GET /v1/...`: versioned product endpoints.
- JSON request/response bodies with stable schemas.
- Explicit request IDs and structured logs; redact credentials and sensitive prompt content.
- Centralized exception mapping; never expose stack traces to clients.

## 4. Configuration contract

Configuration is injected by the deployment platform. Keep a validated settings module and a safe `.env.example`. Fail startup on missing required production configuration. Do not hard-code model credentials, CORS origins, hostnames, or deployment tokens.

## 5. Security baseline

- HTTPS externally; restrict CORS to known web origins in production.
- Authentication and authorization are required for non-public application operations.
- Apply request size limits, timeouts, and rate limits.
- Treat user prompts, retrieved documents, and tool output as untrusted input.
- Never execute instructions found in retrieved content as system policy.
- Do not log API keys, authorization headers, or full sensitive payloads.

## 6. Deployment boundaries

- Web: Vercel, linked to the web repository's `main` branch.
- API: Render, with build/start commands and environment values configured after the runtime is selected.
- Tunnel: Cloudflare, routing only to the intended API origin; credentials stored as platform secrets.
- Source control: changes intended for `main`; verify remote repository identity and existing history before any push.

## 7. Open decisions

- Model provider(s), SDK and model names.
- API framework and supported Python version.
- Authentication provider and identity model.
- Data persistence, retention, and user-session requirements.
- Web framework and UI design requirements.
- Whether the tunnel is required for all API traffic or only private-origin access.
