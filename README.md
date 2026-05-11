# tiny

Chat-driven small website builder. See [CLAUDE.md](./CLAUDE.md) for the
project overview.

## Local development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...
export FLASK_APP=tiny.app:create_app
.venv/bin/flask db upgrade            # create / upgrade local SQLite schema
.venv/bin/flask run --debug --port 8000
```

Visit `http://tiny.localhost:8000` to use the landing page. Created sites
are served at `http://tiny.localhost:8000/<slug>` and edited at
`http://tiny.localhost:8000/studio/<slug>`.

Tests use SQLite in-memory and a scripted fake LLM client:

```bash
.venv/bin/pytest
```

Before committing, run the formatters:

```bash
.venv/bin/black .
.venv/bin/ruff check --fix .
```

## Database migrations

We use Flask-Migrate (Alembic). The first migration in
`migrations/versions/` covers the `sites`, `pages`, and `chat_messages`
tables.

After changing a model:

```bash
.venv/bin/flask db migrate -m "what changed"
.venv/bin/flask db upgrade
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
