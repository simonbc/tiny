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
