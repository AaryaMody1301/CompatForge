# Security policy

Do not publish secrets, private diagnostic payloads, device serial numbers, authentication tokens, or exploit details in public issues or pull requests.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting/security-advisory channel for this repository when available. If private reporting is unavailable, contact the repository owner privately before disclosing exploit details.

Include the affected commit or release, reproduction steps, expected impact, and any relevant environment details. Do not include real credentials or private user data.

## Security boundaries

CompatForge treats the following as security-sensitive surfaces:

- untrusted JSON and community-submission validation;
- Supabase authentication, RLS, moderation, and publication boundaries;
- GitHub Actions permissions and third-party action pinning;
- Python and npm dependency vulnerabilities;
- release manifests, SBOMs, attestations, and immutable-release checks;
- diagnostic privacy guarantees and explicit export approval.

Pull requests run repository-owned vulnerability audits, workflow-policy checks, CodeQL, browser security-header acceptance, database/RLS tests, and release-provenance verification. See [`docs/SECURITY_HARDENING.md`](docs/SECURITY_HARDENING.md) and [`docs/RELEASE_ACCEPTANCE.md`](docs/RELEASE_ACCEPTANCE.md).
