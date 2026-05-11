from tiny.db import db
from tiny.models import Page, Site


def _seed_site(app):
    with app.app_context():
        site = Site(slug="alice", title="Alice", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        site.pages.append(Page(slug="about", title="About", body_markdown="about"))
        db.session.add(site)
        db.session.commit()


def test_studio_shows_new_page_form(client, app):
    _seed_site(app)
    body = client.get("/studio/alice").get_data(as_text=True)
    assert 'action="/studio/alice/pages"' in body


def test_studio_shows_delete_button_for_non_home_pages(client, app):
    _seed_site(app)
    body = client.get("/studio/alice").get_data(as_text=True)
    assert 'action="/studio/alice/pages/about/delete"' in body
    # No delete form for the home page.
    assert 'action="/studio/alice/pages/home/delete"' not in body


def test_create_page(client, app):
    _seed_site(app)
    response = client.post(
        "/studio/alice/pages",
        data={"slug": "projects", "title": "Projects"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/studio/alice?page=projects")

    with app.app_context():
        site = db.session.query(Site).filter_by(slug="alice").one()
        slugs = [p.slug for p in site.pages]
        assert "projects" in slugs
        projects = next(p for p in site.pages if p.slug == "projects")
        assert projects.title == "Projects"
        assert projects.body_markdown == ""


def test_create_page_rejects_empty_slug(client, app):
    _seed_site(app)
    response = client.post("/studio/alice/pages", data={"slug": "", "title": "X"})
    assert response.status_code == 400


def test_create_page_rejects_duplicate_slug(client, app):
    _seed_site(app)
    response = client.post("/studio/alice/pages", data={"slug": "about", "title": "Other About"})
    assert response.status_code == 409


def test_delete_page(client, app):
    _seed_site(app)
    response = client.post("/studio/alice/pages/about/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/studio/alice")

    with app.app_context():
        site = db.session.query(Site).filter_by(slug="alice").one()
        assert [p.slug for p in site.pages] == ["home"]


def test_delete_home_page_refused(client, app):
    _seed_site(app)
    response = client.post("/studio/alice/pages/home/delete")
    assert response.status_code == 400

    with app.app_context():
        site = db.session.query(Site).filter_by(slug="alice").one()
        assert "home" in [p.slug for p in site.pages]


def test_delete_unknown_page_returns_404(client, app):
    _seed_site(app)
    response = client.post("/studio/alice/pages/missing/delete")
    assert response.status_code == 404
