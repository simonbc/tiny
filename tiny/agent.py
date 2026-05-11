from __future__ import annotations

from datetime import datetime
from typing import Any

from tiny.db import db
from tiny.llm import LLMClient
from tiny.models import Page, Site

SYSTEM_PROMPT = """\
You are tiny, an agent that builds and edits small personal websites and blogs.

You can call tools to set the site title and CSS, and to create, update, or
delete pages. Pages have a URL slug, a title, a markdown body, and a layout
("page" or "blog"). Every site must have a page with slug "home" — it is the
landing page. Keep designs warm, readable, and personal. Prefer few pages
over many.

Blog support:
- A page is just a page by default. To make a page act as a blog index that
  lists posts, set its layout to "blog". Any page can be a blog index — most
  commonly "home" or a page with slug "blog".
- A post is a page with is_post=true and a published_at timestamp (ISO 8601).
  Posts are excluded from the site navigation and listed by every blog-layout
  page, newest first. Posts get their own URL at /<site>/<post-slug>.
- All blog-layout pages share the same chronological list of posts.
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
            'The home page must use slug "home". Set layout="blog" to make a '
            "page render the chronological post listing. Set is_post=true and "
            "published_at (ISO 8601) to make a page act as a blog post."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "body_markdown": {"type": "string"},
                "layout": {"type": "string", "enum": ["page", "blog"]},
                "is_post": {"type": "boolean"},
                "published_at": {
                    "type": "string",
                    "description": "ISO 8601 timestamp, e.g. 2026-05-01T10:00:00Z",
                },
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


def run_agent(
    client: LLMClient,
    site: Site,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Drive a tool-use loop until the model stops calling tools.

    Mutates `site` in place via tool calls and commits at the end. Returns the
    final assistant text (concatenated text blocks from the last response, or
    empty string if the model produced no text).
    """
    messages: list[dict[str, Any]] = list(history or [])
    messages.append({"role": "user", "content": user_message})

    final_text = ""
    for _ in range(MAX_TURNS):
        response = client.create_message(system=SYSTEM_PROMPT, messages=messages, tools=TOOLS)
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.get("type") == "tool_use"]
        if not tool_uses:
            final_text = "".join(b["text"] for b in response.content if b.get("type") == "text")
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
    return final_text


def _execute_tool(site: Site, name: str, input_: dict[str, Any]) -> str:
    if name == "set_site":
        site.title = input_["title"]
        site.custom_css = input_["custom_css"]
        return "ok"
    if name == "upsert_page":
        slug = input_["slug"]
        fields: dict[str, Any] = {
            "title": input_["title"],
            "body_markdown": input_["body_markdown"],
        }
        if "layout" in input_:
            fields["layout"] = input_["layout"]
        if "is_post" in input_:
            fields["is_post"] = bool(input_["is_post"])
        if "published_at" in input_ and input_["published_at"]:
            fields["published_at"] = _parse_iso(input_["published_at"])
        existing = next((p for p in site.pages if p.slug == slug), None)
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
        else:
            site.pages.append(Page(slug=slug, **fields))
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


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
