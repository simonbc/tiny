import os

from flask import Flask, abort, redirect, render_template, request, url_for
from markdown import markdown

from tiny.db import db
from tiny.models import Page, Site


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

    @app.get("/studio/<site_slug>")
    def studio(site_slug: str):
        site = _get_site_or_404(site_slug)
        page_slug = request.args.get("page", "home")
        page = _find_page(site, page_slug)
        if page is None:
            abort(404)
        return render_template("studio.html", site=site, page=page)

    @app.post("/studio/<site_slug>/pages/<page_slug>")
    def studio_update_page(site_slug: str, page_slug: str):
        site = _get_site_or_404(site_slug)
        page = _find_page(site, page_slug)
        if page is None:
            abort(404)
        page.title = request.form["title"]
        page.body_markdown = request.form["body_markdown"]
        db.session.commit()
        return redirect(url_for("studio", site_slug=site_slug, page=page_slug))

    @app.post("/studio/<site_slug>/css")
    def studio_update_css(site_slug: str):
        site = _get_site_or_404(site_slug)
        site.custom_css = request.form["custom_css"]
        db.session.commit()
        return redirect(url_for("studio", site_slug=site_slug))

    @app.get("/<site_slug>")
    def site_home(site_slug: str):
        return _render_page(site_slug, "home")

    @app.get("/<site_slug>/<page_slug>")
    def site_page(site_slug: str, page_slug: str):
        return _render_page(site_slug, page_slug)

    return app


def _get_site_or_404(site_slug: str) -> Site:
    site = db.session.query(Site).filter_by(slug=site_slug).one_or_none()
    if site is None:
        abort(404)
    return site


def _find_page(site: Site, page_slug: str) -> Page | None:
    return next((p for p in site.pages if p.slug == page_slug), None)


def _render_page(site_slug: str, page_slug: str):
    site = _get_site_or_404(site_slug)
    page = _find_page(site, page_slug)
    if page is None:
        abort(404)
    body_html = markdown(page.body_markdown)
    return render_template("site.html", site=site, page=page, body_html=body_html)
