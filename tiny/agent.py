from __future__ import annotations

from typing import Any

from tiny.db import db
from tiny.llm import LLMClient
from tiny.models import Page, Site

SYSTEM_PROMPT = """\
You are tiny, an agent that builds and edits small personal websites.

You can call tools to set the site title and CSS, and to create, update, or
delete pages. Pages have a URL slug, a title, and a markdown body. Every site
must have a page with slug "home" — it is the landing page. Keep designs
warm, readable, and personal. Prefer few pages over many.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "set_site",
        "description": "Set the site's title and custom CSS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "custom_css": {"type": "string"},
            },
            "required": ["title", "custom_css"],
        },
    },
    {
        "name": "upsert_page",
        "description": (
            "Create a new page or update an existing one. Identified by slug. "
            'The home page must use slug "home".'
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "body_markdown": {"type": "string"},
            },
            "required": ["slug", "title", "body_markdown"],
        },
    },
    {
        "name": "delete_page",
        "description": 'Delete a page by slug. Refuse to delete "home".',
        "input_schema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
]

MAX_TURNS = 10


def run_agent(client: LLMClient, site: Site, user_message: str) -> None:
    """Drive a tool-use loop until the model stops calling tools.

    Mutates `site` in place via tool calls and commits at the end.
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    for _ in range(MAX_TURNS):
        response = client.create_message(system=SYSTEM_PROMPT, messages=messages, tools=TOOLS)
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.get("type") == "tool_use"]
        if not tool_uses:
            break

        tool_results = [
            {
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": _execute_tool(site, tu["name"], tu["input"]),
            }
            for tu in tool_uses
        ]
        messages.append({"role": "user", "content": tool_results})

    db.session.commit()


def _execute_tool(site: Site, name: str, input_: dict[str, Any]) -> str:
    if name == "set_site":
        site.title = input_["title"]
        site.custom_css = input_["custom_css"]
        return "ok"
    if name == "upsert_page":
        slug = input_["slug"]
        existing = next((p for p in site.pages if p.slug == slug), None)
        if existing:
            existing.title = input_["title"]
            existing.body_markdown = input_["body_markdown"]
        else:
            site.pages.append(
                Page(
                    slug=slug,
                    title=input_["title"],
                    body_markdown=input_["body_markdown"],
                )
            )
        return "ok"
    if name == "delete_page":
        slug = input_["slug"]
        if slug == "home":
            return "error: cannot delete the home page"
        existing = next((p for p in site.pages if p.slug == slug), None)
        if existing is None:
            return f"error: no page with slug {slug!r}"
        db.session.delete(existing)
        return "ok"
    return f"error: unknown tool {name!r}"
