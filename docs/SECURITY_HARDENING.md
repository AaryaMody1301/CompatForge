# Security hardening

Phase 8B adds enforceable repository and deployed-web security gates without introducing a privileged application credential or weakening the evidence/publication trust boundary.

## Pull-request supply-chain gate

`.github/workflows/security.yml` runs GitHub dependency review on pull requests targeting `main` and fails when a dependency change introduces a vulnerability at **high** severity or above.

The dependency-review action requires GitHub's repository dependency graph. The first Phase 8B run reported that dependency review is not currently supported for this repository because the dependency graph is not enabled/available to the action. Keep the dependency-review job as a hard failure until the repository owner enables **Settings → Advanced Security → Dependency graph**. Do not replace the native dependency diff with a weaker `continue-on-error` path.

The same workflow also runs current-state audits so an advisory published after a dependency was merged can still break the scheduled/main security run:

- `npm audit --audit-level=high` against the committed `apps/web/package-lock.json` dependency graph;
- a Python audit over an exact `pip list --local --format=freeze --exclude-editable` snapshot after installing the full development/data/release dependency surface, then `pip-audit==2.10.1 --strict --no-deps` against those pinned third-party versions.

The explicit installed-package snapshot excludes CompatForge's own editable source package while retaining strict collection behavior for every third-party distribution actually present in the CI environment.

Dependabot is configured weekly for GitHub Actions, npm and Python dependency updates.

## Code scanning

CodeQL runs `security-extended` queries for both repository language families:

- `javascript-typescript`;
- `python`.

Both are interpreted-language analyses and use `build-mode: none`, so the security job does not need to execute repository build scripts to extract the code database.

The CodeQL job has only `contents: read` plus `security-events: write`, scoped to that job. Other security jobs retain the workflow-level `contents: read` permission.

## Workflow policy

`python -m compatforge_pipeline.workflow_security .github/workflows` rejects:

1. workflows without explicit top-level `permissions`;
2. `pull_request_target` triggers;
3. network-fetched shell scripts piped directly from `curl`/`wget` into a shell;
4. external action references without a version;
5. mutable third-party action references.

GitHub-maintained `actions/*` and `github/*` actions may track a major tag such as `@v6` or `@v4`. Other action owners must use a full 40-character commit SHA. Existing release-critical third-party actions are already SHA-pinned.

The policy intentionally does not pretend that a YAML text check replaces repository settings, review, CodeQL, dependency review, or secret scanning.

## Secret scanning boundary

CompatForge is public, so GitHub secret scanning is a platform-provided control. Phase 8B does not create a workflow that reads repository secrets or exports secret-scanning alert content into CI logs.

Repository push-protection and release/ruleset settings are administrative controls and are verified during Phase 8D rather than changed implicitly from a code pull request.

## Web response headers

`apps/web/next.config.ts` applies the following headers to every route:

| Header | Required value / purpose |
| --- | --- |
| `Content-Security-Policy` | `base-uri 'self'; frame-ancestors 'none'; object-src 'none'` |
| `Permissions-Policy` | disables camera, microphone, geolocation and browsing-topics |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | two-year HTTPS-only policy with subdomains/preload |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` legacy clickjacking defense |

`poweredByHeader: false` remains enabled, and browser acceptance now fails if `X-Powered-By` is exposed.

The CSP is intentionally non-breaking and narrow in Phase 8B. It protects base URL injection, plugin/object embedding, and framing without adding brittle static `script-src` rules around Next.js inline runtime data or future Supabase OAuth navigation. A nonce/hash-based script policy can be added later only with a dedicated runtime design and browser acceptance coverage.

## Acceptance

The Phase 8A browser suite now validates all six required security headers on every reviewed route, including the custom 404 response. The same script is used by:

- pull-request CI against the exact local `next build`/`next start` output;
- the scheduled/manual production smoke against the stable Vercel alias.

A missing/mutated header, exposed `X-Powered-By`, wrong HTTP status, missing reviewed DOM marker, or runtime error marker fails the gate.

## Remaining repository-setting gates

Before Phase 8B can be called fully green, the repository dependency graph must be enabled so the native dependency-review action can run. At the start of Phase 8B, `main` is also not branch-protected and the repository has no rulesets. The latter release-immutability controls remain Phase 8D work rather than being changed implicitly from this code pull request.
