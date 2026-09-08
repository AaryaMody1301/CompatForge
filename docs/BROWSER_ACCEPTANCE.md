# Browser acceptance

Phase 8A adds a real-browser release gate for the public CompatForge surface without introducing a new JavaScript testing dependency. Phase 8B extends the same contract with deployed security-header assertions.

## Why Chrome CLI

The web project keeps a deliberately small locked dependency set. GitHub-hosted Ubuntu runners already include Google Chrome, so the acceptance runner uses the installed browser directly with `--headless=new`, `--dump-dom`, and screenshots instead of adding Playwright/Puppeteer to `package-lock.json`.

The gate therefore tests the production Next.js build in a browser while leaving application dependencies unchanged.

## What is exercised

`apps/web/scripts/browser-acceptance.mjs` checks these reviewed surfaces:

1. home page and primary calls to action;
2. device-catalog search for FT232R;
3. FT232R evidence detail page;
4. a complete Windows 11 ARM64 compatibility-checker query;
5. coverage page;
6. unauthenticated community-submission entry point;
7. the custom reviewed-device 404 boundary.

For every case the runner verifies the expected HTTP status, renders the page in headless Chrome, requires an application `<main>`, checks reviewed content markers, and rejects generic application/runtime error markers.

Phase 8B additionally requires every case to return the configured CSP, Permissions Policy, Referrer Policy, HSTS, `X-Content-Type-Options`, and `X-Frame-Options` headers. It also fails if `X-Powered-By` is exposed. The exact policy is documented in `docs/SECURITY_HARDENING.md`.

The community-submission case accepts either safe unauthenticated state: hosted authentication configured but no signed-in user, or authentication intentionally unconfigured. It does not attempt OAuth in CI.

## Visual artifacts

Each run also captures:

- desktop home page;
- narrow/mobile-sized home page;
- desktop compatibility-checker result.

The JSON report, Markdown summary, screenshots, and local server log are uploaded as GitHub Actions artifacts for 14 days. The JSON report includes the observed security-header values for every reviewed route.

## Pull-request gate

The existing `Next.js web` CI job now:

1. installs locked dependencies;
2. lints and type-checks;
3. builds the production Next.js application;
4. starts `next start` on loopback only;
5. runs the browser acceptance suite against that exact build;
6. verifies the response-security contract on every reviewed route;
7. uploads the browser artifacts even when an assertion fails;
8. terminates the local production server.

The job keeps repository permissions at `contents: read`.

## Production smoke

`.github/workflows/browser-smoke.yml` runs the same browser and security-header contract every Tuesday against `https://compat-forge.vercel.app` and supports a manual `base_url` override for testing another public deployment URL.

The production workflow is read-only. It does not deploy, mutate evidence, authenticate users, or write to Supabase.

## Run locally

From `apps/web` after a production build:

```bash
npm ci
npm run build
npm run start -- --hostname 127.0.0.1 --port 3100
```

In another shell:

```bash
COMPATFORGE_BROWSER_BASE_URL=http://127.0.0.1:3100 \
  node scripts/browser-acceptance.mjs
```

Set `CHROME_BIN` if Chrome or Chromium is not available under one of the default executable names.

## Boundary

The browser gate is public and unauthenticated. Hosted GitHub OAuth/Supabase moderation acceptance remains a separate configured-environment test. Phase 8B adds supply-chain and response-security enforcement; immutable data release manifests and broader release attestations belong to Phase 8C, while repository-setting/release immutability acceptance belongs to Phase 8D.
