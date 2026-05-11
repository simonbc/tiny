from tiny.db import db
from tiny.models import Page, Site


def _seed_site(app, slug="alice", title="Alice", custom_css="body { color: blue; }"):
    with app.app_context():
        site = Site(slug=slug, title=title, custom_css=custom_css)
        site.pages.append(Page(slug="home", title="Welcome", body_markdown="# Hi"))
        site.pages.append(Page(slug="about", title="About", body_markdown="## About"))
        db.session.add(site)
        db.session.commit()


def test_studio_returns_404_for_unknown_site(client):
    assert client.get("/studio/nope").status_code == 404


def test_studio_links_external_css(client, app):
    _seed_site(app)
    body = client.get("/studio/alice").get_data(as_text=True)
    assert '<link rel="stylesheet" href="/static/css/base.css">' in body
    assert '<link rel="stylesheet" href="/static/css/studio.css">' in body
    # Inline app-chrome <style> block should be gone; only the user's
    # per-site custom_css is still inlined (and that lives in site.html).
    assert "<style>" not in body


def test_static_css_files_are_served(client):
    base = client.get("/static/css/base.css")
    studio = client.get("/static/css/studio.css")
    assert base.status_code == 200
    assert studio.status_code == 200
    # base.css owns the design tokens.
    assert "--color-bg" in base.get_data(as_text=True)
    # studio.css owns the studio layout.
    assert ".studio" in studio.get_data(as_text=True)


def test_studio_shows_home_page_editor_by_default(client, app):
    _seed_site(app)
    response = client.get("/studio/alice")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    # Page editor populated with home page
    assert 'value="Welcome"' in body
    assert "# Hi" in body
    # CSS editor populated with site CSS
    assert "body { color: blue; }" in body
    # Page list shows both pages
    assert "home" in body
    assert "about" in body
    # Preview iframe points at the public site
    assert 'src="/alice"' in body


def test_studio_can_switch_to_another_page(client, app):
    _seed_site(app)
    response = client.get("/studio/alice?page=about")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'value="About"' in body
    assert "## About" in body


def test_studio_unknown_page_returns_404(client, app):
    _seed_site(app)
    assert client.get("/studio/alice?page=missing").status_code == 404


def test_studio_updates_page(client, app):
    _seed_site(app)
    response = client.post(
        "/studio/alice/pages/home",
        data={"title": "Hello world", "body_markdown": "# New body"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/studio/alice?page=home")
    with app.app_context():
        page = (
            db.session.query(Page)
            .join(Site)
            .filter(Site.slug == "alice", Page.slug == "home")
            .one()
        )
        assert page.title == "Hello world"
        assert page.body_markdown == "# New body"


def test_studio_update_unknown_page_returns_404(client, app):
    _seed_site(app)
    response = client.post(
        "/studio/alice/pages/missing",
        data={"title": "x", "body_markdown": "y"},
    )
    assert response.status_code == 404


def test_studio_updates_css(client, app):
    _seed_site(app)
    response = client.post(
        "/studio/alice/css",
        data={"custom_css": "body { color: green; }"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/studio/alice")
    with app.app_context():
        site = db.session.query(Site).filter_by(slug="alice").one()
        assert site.custom_css == "body { color: green; }"
