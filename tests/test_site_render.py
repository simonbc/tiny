from tiny.db import db
from tiny.models import Page, Site


def test_unknown_site_returns_404(client):
    assert client.get("/nope").status_code == 404


def test_site_home_page_renders(client, app):
    with app.app_context():
        site = Site(slug="alice", title="Alices Place", custom_css="body { color: red; }")
        site.pages.append(Page(slug="home", title="Welcome", body_markdown="# Hi there"))
        db.session.add(site)
        db.session.commit()

    response = client.get("/alice")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Alices Place" in body
    assert "<h1>Hi there</h1>" in body
    assert "color: red" in body


def test_subpage_renders(client, app):
    with app.app_context():
        site = Site(slug="bob", title="Bob", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown="home"))
        site.pages.append(Page(slug="about", title="About", body_markdown="## About me"))
        db.session.add(site)
        db.session.commit()

    response = client.get("/bob/about")
    assert response.status_code == 200
    assert "<h2>About me</h2>" in response.get_data(as_text=True)


def test_unknown_subpage_returns_404(client, app):
    with app.app_context():
        site = Site(slug="carol", title="Carol", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        db.session.add(site)
        db.session.commit()

    assert client.get("/carol/missing").status_code == 404
