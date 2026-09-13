import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask


def _configure_ui_logging() -> None:
    root_logger = logging.getLogger()

    # Avoid adding duplicate handlers if create_app is called multiple times
    log_dir = Path(__file__).resolve().parents[1] / "output" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "scribe-ui.log"

    existing_paths = {
        getattr(h, "baseFilename", None)
        for h in root_logger.handlers
        if getattr(h, "baseFilename", None)
    }
    has_console = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)

    if str(log_path) not in existing_paths:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(file_handler)

    if not has_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(console_handler)

    if root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)

def create_app() -> Flask:
    _configure_ui_logging()
    app = Flask(__name__)
    app.secret_key = "replace-this-secret-key"

    # Import and register blueprints inside the function to avoid circular imports
    from scribe.ui.routes.reminder_routes import reminder_bp
    app.register_blueprint(reminder_bp)

    return app
