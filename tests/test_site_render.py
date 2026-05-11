from datetime import datetime, timezone

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


def test_blog_layout_renders_post_listing(client, app):
    with app.app_context():
        site = Site(slug="dora", title="Dora", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown="Welcome", layout="blog"))
        site.pages.append(
            Page(
                slug="first",
                title="First post",
                body_markdown="hello",
                is_post=True,
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
        site.pages.append(
            Page(
                slug="second",
                title="Second post",
                body_markdown="hello again",
                is_post=True,
                published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
        )
        db.session.add(site)
        db.session.commit()

    body = client.get("/dora").get_data(as_text=True)
    assert "Second post" in body
    assert "First post" in body
    # Newest first
    assert body.index("Second post") < body.index("First post")
    # Listing links point at each post
    assert 'href="/dora/second"' in body
    assert 'href="/dora/first"' in body
    # Body markdown still rendered above the listing
    assert body.index("Welcome") < body.index("Second post")


def test_default_layout_does_not_render_post_listing(client, app):
    with app.app_context():
        site = Site(slug="eli", title="Eli", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown="just a page"))
        site.pages.append(
            Page(
                slug="hello",
                title="Hello",
                body_markdown="x",
                is_post=True,
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
        db.session.add(site)
        db.session.commit()

    body = client.get("/eli").get_data(as_text=True)
    assert "Hello" not in body


def test_posts_excluded_from_nav(client, app):
    with app.app_context():
        site = Site(slug="fin", title="Fin", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        site.pages.append(Page(slug="about", title="About", body_markdown=""))
        site.pages.append(
            Page(
                slug="news",
                title="A news post",
                body_markdown="",
                is_post=True,
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
        db.session.add(site)
        db.session.commit()

    body = client.get("/fin").get_data(as_text=True)
    # Nav contains the page but not the post.
    nav_start = body.index("<nav>")
    nav_end = body.index("</nav>")
    nav = body[nav_start:nav_end]
    assert "About" in nav
    assert "A news post" not in nav


def test_post_detail_page_renders(client, app):
    with app.app_context():
        site = Site(slug="gus", title="Gus", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        site.pages.append(
            Page(
                slug="hello",
                title="Hello",
                body_markdown="## body of the post",
                is_post=True,
                published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
        db.session.add(site)
        db.session.commit()

    response = client.get("/gus/hello")
    assert response.status_code == 200
    assert "<h2>body of the post</h2>" in response.get_data(as_text=True)
