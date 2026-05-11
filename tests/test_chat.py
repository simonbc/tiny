from tiny.db import db
from tiny.llm import LLMResponse
from tiny.models import ChatMessage, Page, Site

from .fake_llm import FakeLLMClient, text, tool_use


def _seed_site(app, slug="alice"):
    with app.app_context():
        site = Site(slug=slug, title="Alice", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown="# Hi"))
        db.session.add(site)
        db.session.commit()


def test_studio_shows_chat_form(client, app):
    _seed_site(app)
    body = client.get("/studio/alice").get_data(as_text=True)
    assert 'name="message"' in body
    assert 'action="/studio/alice/chat"' in body


def test_studio_shows_existing_chat_history(client, app):
    with app.app_context():
        site = Site(slug="alice", title="Alice", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        site.chat_messages.append(ChatMessage(role="user", content="make it blue"))
        site.chat_messages.append(ChatMessage(role="assistant", content="Done, made it blue."))
        db.session.add(site)
        db.session.commit()

    body = client.get("/studio/alice").get_data(as_text=True)
    assert "make it blue" in body
    assert "Done, made it blue." in body


def test_post_chat_runs_agent_and_persists_messages(client, app):
    _seed_site(app)
    app.llm_client = FakeLLMClient(
        [
            LLMResponse(
                stop_reason="tool_use",
                content=[
                    tool_use(
                        "a",
                        "set_site",
                        {"title": "Alice", "custom_css": "body { color: blue; }"},
                    ),
                ],
            ),
            LLMResponse(stop_reason="end_turn", content=[text("Made it blue for you.")]),
        ]
    )

    response = client.post("/studio/alice/chat", data={"message": "make it blue"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/studio/alice#tab-chat")

    with app.app_context():
        site = db.session.query(Site).filter_by(slug="alice").one()
        assert site.custom_css == "body { color: blue; }"
        history = [(m.role, m.content) for m in site.chat_messages]
        assert history == [
            ("user", "make it blue"),
            ("assistant", "Made it blue for you."),
        ]


def test_post_chat_includes_prior_history_in_agent_messages(client, app):
    with app.app_context():
        site = Site(slug="alice", title="Alice", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        site.chat_messages.append(ChatMessage(role="user", content="hi"))
        site.chat_messages.append(ChatMessage(role="assistant", content="hello"))
        db.session.add(site)
        db.session.commit()

    fake = FakeLLMClient([LLMResponse(stop_reason="end_turn", content=[text("noted")])])
    app.llm_client = fake

    client.post("/studio/alice/chat", data={"message": "and now make it red"})

    sent_messages = fake.calls[0]["messages"]
    # Prior pairs + new user message.
    assert sent_messages[0] == {"role": "user", "content": "hi"}
    assert sent_messages[1] == {"role": "assistant", "content": "hello"}
    assert sent_messages[-1] == {"role": "user", "content": "and now make it red"}


def test_post_chat_rejects_empty_message(client, app):
    _seed_site(app)
    response = client.post("/studio/alice/chat", data={"message": ""})
    assert response.status_code == 400
