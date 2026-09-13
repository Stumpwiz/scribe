"""
clerk_models.py - Wrapper to access clerk database models from scribe

This module provides access to clerk's database models while avoiding
environment variable conflicts between the two projects.
"""

import os
import sys
from pathlib import Path

# Temporarily store scribe's env vars
_scribe_env = {}
_scribe_keys = [
    'MODEL', 'OPENAI_MAX_TOKENS', 'OPENAI_RETRIES', 'OPENAI_API_KEY',
    'EMAIL_FROM', 'EMAIL_SENDER_NAME', 'RECIPIENTS_DIR', 'REPORT_SUBMISSION_EMAIL',
    'DEFAULT_FALLBACK_EMAIL', 'DRY_RUN'
]

for key in _scribe_keys:
    if key in os.environ:
        _scribe_env[key] = os.environ.pop(key)

# Add clerk backend to path
_clerk_backend = Path(__file__).parent.parent.parent.parent / 'clerk' / 'backend'
if str(_clerk_backend) not in sys.path:
    sys.path.insert(0, str(_clerk_backend))

# Import clerk models
from app.models import (
    Body,
    Person,
    Office,
    Term,
    ReportRecord,
    LetterTemplate,
    User,
)

# Import Base for potential use
from app.database import Base

# Restore scribe's env vars
for key, value in _scribe_env.items():
    os.environ[key] = value

# Export models
__all__ = [
    'Body',
    'Person',
    'Office',
    'Term',
    'ReportRecord',
    'LetterTemplate',
    'User',
    'Base',
]
