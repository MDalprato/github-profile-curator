# GitHub Profile Curator

Conservative, weekly AI-assisted GitHub profile README editor. Runs on a Debian Mac mini with Docker Compose, reads your public repository metadata, and opens **draft PRs by default** after validation, with optional direct commits.

## Setup

1. Copy `.env.example` to `.env` and configure the credentials below.
2. Set `GITHUB_TOKEN` to a fine-grained PAT restricted to `MDalprato/MDalprato`, with **Contents: read/write** and **Pull requests: read/write**. To scan private repositories, create a separate fine-grained PAT with access to the repositories you want to inspect (or all repositories), **Metadata: read-only**, and no write permissions. Set it as `GITHUB_READ_TOKEN` and enable `PRIVATE_SCAN=true`. Discovery uses this read-only token; profile reads and PR operations use `GITHUB_TOKEN`. If `GITHUB_READ_TOKEN` is empty, discovery falls back to `GITHUB_TOKEN`. Only repositories visible to the selected token can be counted.
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

Runs every Monday at 09:00 Europe/Rome. If no meaningful changes are justified, does nothing. In draft PR mode, an existing curator PR blocks duplicates. Direct mode updates the configured branch and does not modify existing PRs.

## Automatic publishing

Set these values in `.env` to publish validated proposals directly to `README.md`
in `PROFILE_REPO` on `PROFILE_BRANCH`:

```dotenv
AUTO_PUSH=true
DRY_RUN=false
```

`AUTO_PUSH=false` (the default) uses draft PRs. `DRY_RUN=true` or `--dry-run`
always prevents writes, including scheduled runs. Both variables accept only
`true` or `false`; invalid values stop the run. Unchanged, insignificant, or
rejected proposals are never published.

For a Python run with `.env` loaded:

```bash
python -c 'from dotenv import load_dotenv; load_dotenv(override=True); from app.main import main; main()' --once
```

For Docker, rebuild and recreate the service after code/configuration changes:

```bash
docker compose up -d --build --force-recreate
```

Direct publishing uses `GITHUB_TOKEN` and creates a commit via the GitHub Contents
API; no local Git push or PR is needed. It requires Contents write access and
respects branch protection. The README SHA read before generation is included
in the update: if the file changed meanwhile, the run fails rather than
replacing that newer version. Failures are recorded in the local run history;
there is no force-push or automatic retry with a newer SHA.

This publishes the agent's generated proposals, not the separate redesign in
`profile/README.md`. Direct mode skips manual review, so validation alone does
not guarantee factual accuracy.

## Privacy and trust model

- Public repository metadata and current public profile README are sent to OpenAI API.
- Private repo names, descriptions, code, commit messages, and URLs are **never sent to OpenAI**, nor included in the PR.
- Private repo count and primary-language frequency are saved in `data/private-summary.json`. With `PRIVATE_SCAN=true` and `PRIVATE_LANGUAGES_FOR_PROFILE=true`, only sorted language names are sent to OpenAI, without counts or project details. A proposal based only on these names can add the exact sentence `Languages used across my projects: ... .`; other edits require public evidence. This does not establish mastery or recent activity.
- Language sharing is disabled by default. Enable it explicitly in `.env` to authorize use in public profile proposals.
- Public repository descriptions and AI outputs are untrusted. Structural checks run in both modes; draft PR mode also allows manual review. Validation cannot guarantee every claim is true.
- Secrets are stored in `.env` and must never be committed. Avoid sharing `data/` publicly.
- Never grant the container Docker socket or deploy rights. No automatic merge.
- All public repository metadata scanned is from repos owned by `GITHUB_OWNER`, excluding forks and archived repos.

## Limitations

This first version uses repository metadata rather than code analysis, and does not inspect private repository content. It does not have Telegram notifications, GitHub webhook triggers, or a learning-journal UI. It does not claim that a language detected in a repository is a mastered skill. A new PR is created only if evidence passes conservative checks.

Private scanning does not read source code. With explicit opt-in, aggregated language names may influence AI proposals. The scan visits up to 1,000 owned repositories. Private counts include archived repositories and forks and are not limited by LOOKBACK_DAYS.
