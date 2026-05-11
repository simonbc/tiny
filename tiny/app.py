import os
import secrets

from dotenv import find_dotenv, load_dotenv
from flask import Flask, abort, redirect, render_template, request, url_for
from flask_migrate import Migrate
from markdown import markdown

from tiny.agent import run_agent
from tiny.db import db
from tiny.models import ChatMessage, Page, Site


def create_app(config: dict | None = None, llm_client=None) -> Flask:
    load_dotenv(find_dotenv(usecwd=True))
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if config:
        app.config.update(config)

    db.init_app(app)
    Migrate(app, db)
    app.llm_client = llm_client

    # Import models so SQLAlchemy registers them before create_all runs.
    import tiny.models  # noqa: F401

    @app.get("/")
    def landing():
        return render_template("landing.html")

    @app.post("/sites")
    def create_site():
        prompt = request.form.get("prompt", "").strip()
        if not prompt:
            abort(400)
        slug = _generate_unique_slug()
        site = Site(slug=slug, title="", custom_css="")
        site.pages.append(Page(slug="home", title="Home", body_markdown=""))
        db.session.add(site)
        db.session.commit()
        run_agent(_resolve_llm_client(app), site, prompt)
        return redirect(url_for("studio", site_slug=slug))

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

    @app.post("/studio/<site_slug>/pages")
    def studio_create_page(site_slug: str):
        site = _get_site_or_404(site_slug)
        slug = request.form.get("slug", "").strip()
        title = request.form.get("title", "").strip()
        if not slug:
            abort(400)
        if _find_page(site, slug) is not None:
            abort(409)
        site.pages.append(Page(slug=slug, title=title or slug, body_markdown=""))
        db.session.commit()
        return redirect(url_for("studio", site_slug=site_slug, page=slug))

    @app.post("/studio/<site_slug>/pages/<page_slug>/delete")
    def studio_delete_page(site_slug: str, page_slug: str):
        site = _get_site_or_404(site_slug)
        if page_slug == "home":
            abort(400)
        page = _find_page(site, page_slug)
        if page is None:
            abort(404)
        db.session.delete(page)
        db.session.commit()
        return redirect(url_for("studio", site_slug=site_slug))

    @app.post("/studio/<site_slug>/css")
    def studio_update_css(site_slug: str):
        site = _get_site_or_404(site_slug)
        site.custom_css = request.form["custom_css"]
        db.session.commit()
        return redirect(url_for("studio", site_slug=site_slug))

    @app.post("/studio/<site_slug>/chat")
    def studio_chat(site_slug: str):
        site = _get_site_or_404(site_slug)
        message = request.form.get("message", "").strip()
        if not message:
            abort(400)
        history = [{"role": m.role, "content": m.content} for m in site.chat_messages]
        site.chat_messages.append(ChatMessage(role="user", content=message))
        db.session.commit()
        reply = run_agent(_resolve_llm_client(app), site, message, history=history)
        site.chat_messages.append(ChatMessage(role="assistant", content=reply))
        db.session.commit()
        return redirect(url_for("studio", site_slug=site_slug))

    @app.get("/<site_slug>")
    def site_home(site_slug: str):
        return _render_page(site_slug, "home")

    @app.get("/<site_slug>/<page_slug>")
    def site_page(site_slug: str, page_slug: str):
        return _render_page(site_slug, page_slug)

    return app


def _resolve_database_url() -> str:
    """Pick the right DB URL. Normalize ``postgres://`` (Fly/Heroku) to
    ``postgresql+psycopg://`` so SQLAlchemy uses psycopg v3."""
    url = os.environ.get("DATABASE_URL", "sqlite:///tiny.db")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _generate_unique_slug() -> str:
    for _ in range(10):
        candidate = secrets.token_hex(3)
        if db.session.query(Site).filter_by(slug=candidate).one_or_none() is None:
            return candidate
    raise RuntimeError("could not generate a unique slug")


def _resolve_llm_client(app: Flask):
    if app.llm_client is None:
        from tiny.llm import AnthropicClient

        app.llm_client = AnthropicClient()
    return app.llm_client


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
