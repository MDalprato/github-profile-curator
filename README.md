# GitHub Profile Curator

Conservative, weekly AI-assisted GitHub profile README editor. Runs on a Debian Mac mini with Docker Compose, reads your public repository metadata, and opens **draft PRs only** after validation.

## Setup

1. Copy `.env.example` to `.env` and replace both tokens.
2. Create a fine-grained GitHub PAT scoped to **all repositories** if you want to inspect private repository metadata. Permissions: **Metadata: read** for all; **Contents: read/write** and **Pull requests: read/write** for `MDalprato/MDalprato`. Fine-grained PATs cannot always express different per-repository permissions in a single token: **prefer two tokens or a GitHub App in production**. This MVP uses one token, so limit its reach and review access carefully. Classic PATs require broader scopes and are discouraged.
3. Set `OPENAI_API_KEY` for your chosen model. OpenAI API usage is billed separately.
4. On the Debian host, grant the non-root container access to the state folder: `sudo chown -R 10001:10001 data`
5. Run:

```bash
docker compose up -d --build
docker compose logs -f curator
```

6. Preview without touching GitHub:

```bash
docker compose exec curator python -m app.main --once --dry-run
cat data/proposed-README.md
cat data/proposal.json
```

7. When satisfied, change `DRY_RUN=false` in `.env`, then:

```bash
docker compose up -d --force-recreate
# Optional immediate real run:
docker compose exec curator python -m app.main --once
```

Runs every Monday at 09:00 Europe/Rome. If no meaningful changes are justified, does nothing. Existing curator PR blocks duplicates.

## Privacy and trust model

- Public repository metadata and current public profile README are sent to OpenAI API.
- Private repo names, descriptions, code, commit messages, and URLs are **never sent to OpenAI**, nor included in the PR.
- Private repo count and primary-language frequency are saved only in `data/private-summary.json`. The current implementation does **not** use private data to suggest public claims. This is deliberate: it cannot safely infer what you want to disclose.
- For skills learned in private repositories, confirm and add them manually to a public-approved source in a future version.
- Public repository descriptions and AI outputs are untrusted. Structural checks and manual PR review are essential; validation cannot guarantee every claim is true.
- Secrets are stored in `.env` and must never be committed. Avoid sharing `data/` publicly.
- Never grant the container Docker socket or deploy rights. No automatic merge.
- All public repository metadata scanned is from repos owned by `GITHUB_OWNER`, excluding forks and archived repos.

## Limitations

This first version uses repository metadata rather than code analysis, and does not inspect private repository content. It does not have Telegram notifications, GitHub webhook triggers, or a learning-journal UI. It does not claim that a language detected in a repository is a mastered skill. A new PR is created only if evidence passes conservative checks.

For GitHub fine-grained tokens, access to all repos with write permission may be broader than desirable. Recommended hardening: separate **read-only discovery token** from **profile-only write token**, or a GitHub App with per-repository installations.
