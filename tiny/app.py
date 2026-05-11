from flask import Flask, render_template


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if config:
        app.config.update(config)

    @app.get("/")
    def landing():
        return render_template("landing.html")

    return app
