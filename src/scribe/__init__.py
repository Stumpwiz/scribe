# src/scribe/__init__.py
from flask import Flask

def create_ui_app():
    app = Flask(__name__)
    app.secret_key = "dev"  # Replace with a secure key in production

    # Import and register blueprints inside the function to avoid circular imports
    from scribe.ui.routes.reminder_routes import reminder_bp
    app.register_blueprint(reminder_bp)

    return app
