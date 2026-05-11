from tiny.agent import run_agent
from tiny.db import db
from tiny.llm import LLMResponse
from tiny.models import Page, Site

from .fake_llm import FakeLLMClient, text, tool_use


def test_run_agent_executes_tool_calls_then_stops(app):
    fake = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[
                    tool_use("a", "set_site", {"title": "Notes", "custom_css": "body{}"}),
                    tool_use(
                        "b",
                        "upsert_page",
                        {"slug": "home", "title": "Home", "body_markdown": "# Hi"},
                    ),
                ],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("done")]),
        ]
    )

    with app.app_context():
        site = Site(slug="x", title="", custom_css="")
        db.session.add(site)
        db.session.commit()

        run_agent(fake, site, "build me a notes site")

        site = db.session.query(Site).filter_by(slug="x").one()
        assert site.title == "Notes"
        assert site.custom_css == "body{}"
        assert [p.slug for p in site.pages] == ["home"]
        assert site.pages[0].body_markdown == "# Hi"


def test_upsert_page_updates_existing(app):
    fake = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[
                    tool_use(
                        "a",
                        "upsert_page",
                        {"slug": "home", "title": "New", "body_markdown": "new"},
                    ),
                ],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("done")]),
        ]
    )

    with app.app_context():
        site = Site(slug="x", title="", custom_css="")
        site.pages.append(Page(slug="home", title="Old", body_markdown="old"))
        db.session.add(site)
        db.session.commit()

        run_agent(fake, site, "rename home")

        site = db.session.query(Site).filter_by(slug="x").one()
        assert len(site.pages) == 1
        assert site.pages[0].title == "New"
        assert site.pages[0].body_markdown == "new"


def test_delete_page_refuses_home(app):
    fake = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[tool_use("a", "delete_page", {"slug": "home"})],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("ok")]),
        ]
    )

    with app.app_context():
        site = Site(slug="x", title="", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        db.session.add(site)
        db.session.commit()

        run_agent(fake, site, "delete home")

        site = db.session.query(Site).filter_by(slug="x").one()
        assert [p.slug for p in site.pages] == ["home"]

    # The tool result should have reported the refusal back to the model.
    second_call_messages = fake.calls[1]["messages"]
    last_user_msg = second_call_messages[-1]
    tool_result = last_user_msg["content"][0]
    assert "cannot delete" in tool_result["content"]


def test_upsert_page_can_create_post(app):
    fake = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[
                    tool_use(
                        "a",
                        "upsert_page",
                        {
                            "slug": "hello-world",
                            "title": "Hello world",
                            "body_markdown": "first post",
                            "is_post": True,
                            "published_at": "2026-05-01T10:00:00Z",
                        },
                    ),
                ],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("done")]),
        ]
    )

    with app.app_context():
        site = Site(slug="x", title="", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        db.session.add(site)
        db.session.commit()

        run_agent(fake, site, "add a post")

        site = db.session.query(Site).filter_by(slug="x").one()
        post = next(p for p in site.pages if p.slug == "hello-world")
        assert post.is_post is True
        assert post.published_at is not None
        assert post.layout == "page"


def test_upsert_page_can_set_blog_layout(app):
    fake = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[
                    tool_use(
                        "a",
                        "upsert_page",
                        {
                            "slug": "home",
                            "title": "Home",
                            "body_markdown": "welcome",
                            "layout": "blog",
                        },
                    ),
                ],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("done")]),
        ]
    )

    with app.app_context():
        site = Site(slug="x", title="", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        db.session.add(site)
        db.session.commit()

        run_agent(fake, site, "make home a blog")

        site = db.session.query(Site).filter_by(slug="x").one()
        home = next(p for p in site.pages if p.slug == "home")
        assert home.layout == "blog"


def test_delete_page_removes_non_home_page(app):
    fake = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[tool_use("a", "delete_page", {"slug": "about"})],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("ok")]),
        ]
    )

    with app.app_context():
        site = Site(slug="x", title="", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        site.pages.append(Page(slug="about", title="About", body_markdown=""))
        db.session.add(site)
        db.session.commit()

        run_agent(fake, site, "drop about")

        site = db.session.query(Site).filter_by(slug="x").one()
        assert [p.slug for p in site.pages] == ["home"]
