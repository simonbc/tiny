# tiny

Chat-driven small website builder. See [CLAUDE.md](./CLAUDE.md) for the
project overview.

## Local development

Requires [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```bash
uv sync                     # install deps from uv.lock into .venv

cp .env.example .env        # then edit .env with your ANTHROPIC_API_KEY
set -a; source .env; set +a

uv run flask db upgrade     # create / upgrade local SQLite schema
uv run flask run --debug --port 8000
```

Visit `http://localhost:8000` to use the landing page. Created sites
are served at `http://localhost:8000/<slug>` and edited at
`http://localhost:8000/studio/<slug>`.

Tests use SQLite in-memory and a scripted fake LLM client:

```bash
uv run pytest
```

Before committing, run the formatters:

```bash
uv run black .
uv run ruff check --fix .
```

## Database migrations

We use Flask-Migrate (Alembic). The first migration in
`migrations/versions/` covers the `sites`, `pages`, and `chat_messages`
tables.

After changing a model:

```bash
uv run flask db migrate -m "what changed"
uv run flask db upgrade
```

## Deploying to Fly.io

The repo has a `Dockerfile` and `fly.toml`. First-time setup:

```bash
fly apps create tiny-ai                       # claim the app name
fly postgres create --name tiny-ai-pg \
  --region fra --initial-cluster-size 1 \
  --vm-size shared-cpu-1x --volume-size 1     # provision Postgres
fly postgres attach --app tiny-ai tiny-ai-pg  # sets DATABASE_URL
fly secrets set ANTHROPIC_API_KEY=sk-ant-... --app tiny-ai
fly deploy
```

`fly.toml` runs `flask db upgrade` as the release command, so each
deploy applies any new migrations before traffic is shifted to the new
version. The app boots under `gunicorn` from `wsgi.py`.
