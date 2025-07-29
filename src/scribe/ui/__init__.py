from flask import Flask
from scribe.ui.routes.reminder_routes import reminder_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "replace-this-secret-key"

    # Register blueprints
    app.register_blueprint(reminder_bp)

    return app
