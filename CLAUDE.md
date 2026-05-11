# tiny

tiny is a chat-driven small website builder that turns plain-language prompts into deployed, editable small websites. It's Lovable for the indieweb. You can edit the website yourself or by chat. You can change the design by chat (the agent updates custom CSS).

## Stack

- Flask
- SQLAlchemy
- Jinja2 (server-rendered HTML)
- Postgres
- Fly.io for deployment

## Development workflow

Always follow green/red TDD:

1. Write a failing test first (red)
2. Write the minimum code to make it pass (green)
3. Refactor if needed, keeping tests green

Never write production code without a failing test driving it.

## Before every commit

Run the formatters so the pre-commit hooks don't rewrite staged files and force a second attempt:

```
black .
ruff check --fix .
```
