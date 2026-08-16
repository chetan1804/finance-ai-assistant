# Release process

The repository publishes production containers to GitHub Container Registry
(GHCR). Publishing is intentionally separate from deployment so a hosting target
and its production environment approval rules can be selected independently.

## Continuous integration

Every push and pull request runs backend integration tests with PostgreSQL and
Redis, frontend lint/tests/build, dependency review for pull requests, and a
container smoke test. Dependabot checks Python, npm, GitHub Actions, and Docker
dependencies weekly.

The smoke test starts the built image and verifies both `/health` and `/version`.
The version response contains only build-supplied release version, commit SHA,
and build timestamp; local builds report safe development defaults.

## Publish a release

Start from a clean, reviewed commit whose CI checks pass. Create and push an
annotated semantic-version tag:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Only `vMAJOR.MINOR.PATCH` tags pass release validation. The release workflow
reruns backend and frontend verification, builds the image, and publishes these
GHCR tags:

- `1.0.0`
- `1.0`
- `sha-<short-commit>`
- `latest`

It also attaches a software bill of materials, maximum BuildKit provenance, and
a GitHub artifact attestation. No application secrets are passed as Docker build
arguments or stored in provenance.

Verify a published image before promotion:

```bash
gh attestation verify \
  oci://ghcr.io/chetan1804/finance-ai-assistant:1.0.0 \
  --repo chetan1804/finance-ai-assistant
```

Deploy the immutable digest shown by the release job rather than relying on the
mutable `latest` tag. Configure application secrets only in the hosting
platform's secret manager.

## Rollback

Keep the previous known-good image digest and database backup through the
release window. Application rollback means redeploying that previous digest.
Database rollback is separate: migrations are forward-only, so restore a tested
pre-release backup only under the disaster-recovery procedure in
`DEPLOYMENT.md`. Confirm `/health`, `/ready`, and `/version` after promotion or
rollback.
