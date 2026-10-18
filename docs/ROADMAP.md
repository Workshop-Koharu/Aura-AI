# Aura AI — Foundation Roadmap

## Phase 0 — Verify source of truth

- [x] Inspect configured local project directory.
- [x] Record currently available project logo.
- [ ] Restore/verify GitHub access to both configured repositories.
- [ ] Read existing branches, README files, prompt files, issues, and recent history before replacing any existing design.
- [ ] Reconcile all prior prompts into `PROMPTS.md`.

## Phase 1 — Repository and runtime skeleton

- [ ] Confirm Python version and API framework.
- [ ] Create a minimal API package with health endpoint and typed settings.
- [ ] Add dependency lockfile and reproducible development commands.
- [ ] Add unit tests and CI checks.
- [ ] Add `.gitignore` and safe `.env.example`.
- [ ] Add structured logging and consistent error responses.

## Phase 2 — Product contract

- [ ] Define supported use cases and API schemas.
- [ ] Define model adapter interface and timeout/retry policy.
- [ ] Define authentication, rate limiting, and data-retention policy.
- [ ] Define frontend-to-API contract and CORS origins.

## Phase 3 — Deployments

- [ ] Create or verify Render API service.
- [ ] Create or verify Cloudflare Tunnel and origin routing.
- [ ] Create or verify Vercel web project connected to `main`.
- [ ] Configure secrets in platform dashboards, not Git.
- [ ] Validate health, TLS, routing, logs, and rollback procedure.

## Definition of done for foundation

- Requirements are traceable to source prompts.
- Local setup is documented and reproducible.
- Automated checks pass.
- No secrets are committed.
- Deployment resources are verified rather than assumed.
- Changes are committed to the correct repository and `main` branch only after remote identity and current history are confirmed.
