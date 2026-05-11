from tiny.db import db
from tiny.llm import LLMResponse
from tiny.models import Site

from .fake_llm import FakeLLMClient, text, tool_use


def test_post_sites_creates_site_via_agent_and_redirects_to_studio(client, app):
    app.llm_client = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[
                    tool_use(
                        "a",
                        "set_site",
                        {"title": "My Notes", "custom_css": "body { color: red; }"},
                    ),
                    tool_use(
                        "b",
                        "upsert_page",
                        {
                            "slug": "home",
                            "title": "Welcome",
                            "body_markdown": "# Welcome",
                        },
                    ),
                ],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("done")]),
        ]
    )

    response = client.post("/sites", data={"prompt": "build me a notes site"})

    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/studio/" in location
    slug = location.rsplit("/", 1)[-1]

    with app.app_context():
        site = db.session.query(Site).filter_by(slug=slug).one()
        assert site.title == "My Notes"
        assert site.custom_css == "body { color: red; }"
        assert [p.slug for p in site.pages] == ["home"]
        assert site.pages[0].body_markdown == "# Welcome"


def test_post_sites_requires_prompt(client, app):
    response = client.post("/sites", data={"prompt": ""})
    assert response.status_code == 400


def test_post_sites_studio_loads_even_when_agent_creates_no_pages(client, app):
    app.llm_client = FakeLLMClient(
        [LLMResponse(stop_reason="end_turn", content=[text("nothing to do")])]
    )

    response = client.post("/sites", data={"prompt": "hi"})
    assert response.status_code == 302
    slug = response.headers["Location"].rsplit("/", 1)[-1]

    studio_response = client.get(f"/studio/{slug}")
    assert studio_response.status_code == 200


def test_post_sites_persists_prompt_and_reply_as_chat_messages(client, app):
    app.llm_client = FakeLLMClient(
        [LLMResponse(stop_reason="end_turn", content=[text("tell me more about your site")])]
    )

    response = client.post("/sites", data={"prompt": "build me something"})
    slug = response.headers["Location"].rsplit("/", 1)[-1]

    with app.app_context():
        site = db.session.query(Site).filter_by(slug=slug).one()
        roles_and_contents = [(m.role, m.content) for m in site.chat_messages]

    assert roles_and_contents == [
        ("user", "build me something"),
        ("assistant", "tell me more about your site"),
    ]
