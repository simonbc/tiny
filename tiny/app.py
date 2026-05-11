import os

from flask import Flask, abort, render_template
from markdown import markdown

from tiny.db import db
from tiny.models import Site


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tiny.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if config:
        app.config.update(config)

    db.init_app(app)

    # Import models so SQLAlchemy registers them before create_all runs.
    import tiny.models  # noqa: F401

    @app.get("/")
    def landing():
        return render_template("landing.html")

    @app.get("/<site_slug>")
    def site_home(site_slug: str):
        return _render_page(site_slug, "home")

    @app.get("/<site_slug>/<page_slug>")
    def site_page(site_slug: str, page_slug: str):
        return _render_page(site_slug, page_slug)

    return app


def _render_page(site_slug: str, page_slug: str):
    site = db.session.query(Site).filter_by(slug=site_slug).one_or_none()
    if site is None:
        abort(404)
    page = next((p for p in site.pages if p.slug == page_slug), None)
    if page is None:
        abort(404)
    body_html = markdown(page.body_markdown)
    return render_template("site.html", site=site, page=page, body_html=body_html)
