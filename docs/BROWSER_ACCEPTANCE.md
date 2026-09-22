# Browser acceptance

The browser-acceptance gate exercises the public CompatForge surface without introducing a browser-testing JavaScript dependency. The same contract also verifies deployed security headers.

## Why Chrome CLI

The web project keeps a deliberately small locked dependency set. GitHub-hosted Ubuntu runners already include Google Chrome, so the acceptance runner uses the installed browser directly with `--headless=new`, `--dump-dom`, and screenshots instead of adding Playwright/Puppeteer to `package-lock.json`.

The gate therefore tests the production Next.js build in a browser while leaving application dependencies unchanged.

## What is exercised

`apps/web/scripts/browser-acceptance.mjs` checks these reviewed surfaces:

1. home page, formatted corpus counts, canonical/social metadata, and primary calls to action;
2. default catalog ordering plus exact-ID and natural-language device search;
3. generic identity pages and reviewed evidence detail pages;
4. reviewed FTDI and Saleae checker queries across stable and Insider support channels;
5. invalid checker inputs, coverage, and the global 404 boundary;
6. the intentional read-only community state used when hosted submissions are disabled;
7. public discovery assets including robots, sitemap, web manifest, icons, and social images.

For every case the runner verifies the expected HTTP status, renders the page in headless Chrome, requires an application `<main>`, checks reviewed content markers, and rejects generic application/runtime error markers.

Every reviewed route must also return the configured CSP, Permissions Policy, Referrer Policy, HSTS, `X-Content-Type-Options`, and `X-Frame-Options` headers. The gate fails if `X-Powered-By` is exposed. The exact policy is documented in `docs/SECURITY_HARDENING.md`.

The default CI contract expects community submissions to be intentionally disabled unless a deployment explicitly enables the feature with its hosted authentication and moderation configuration. It does not attempt OAuth in CI.

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

The browser gate is public and unauthenticated. Hosted GitHub OAuth/Supabase moderation acceptance remains a separate configured-environment test. Supply-chain checks, immutable release manifests, attestations, and repository-setting acceptance remain separate release gates.
