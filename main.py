#!/usr/bin/env python
"""
NESAKO AI Assistant - Development Server
Compatible with Render deployment and local development
"""
import os
import sys
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Remove c:\Users\PC from path to avoid conflicts with transport module
if 'C:\\Users\\PC' in sys.path:
    sys.path.remove('C:\\Users\\PC')

# Set the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NESAKO.settings')

if __name__ == '__main__':
    """Run the Django server (Railway/production uses Procfile to invoke this)."""
    from django.core.management import execute_from_command_line

    # Prefer Railway PORT if present, bind to all interfaces
    port = os.environ.get('PORT')
    if not port:
        # Allow override by CLI arg for local dev
        if len(sys.argv) > 1:
            port = sys.argv[1]
        else:
            port = '8080'

    argv = ['main.py', 'runserver', f'0.0.0.0:{port}']

    # Execute Django management command
    execute_from_command_line(argv)
else:
    # For WSGI deployment (Render, etc.)
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    application.nesako_ai_id = "nesako-ai-assistant-v1"
