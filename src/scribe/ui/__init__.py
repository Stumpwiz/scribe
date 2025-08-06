from flask import Flask

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "replace-this-secret-key"

    # Import and register blueprints inside the function to avoid circular imports
    from scribe.ui.routes.reminder_routes import reminder_bp
    app.register_blueprint(reminder_bp)

    return app
