"""
CARspective — Production WSGI Entrypoint

Provides the standard WSGI callable for production application servers.

Usage Examples:
  Linux / Docker Container (Gunicorn):
    gunicorn --bind 0.0.0.0:5001 --workers 4 --threads 2 --timeout 60 "server.wsgi:app"

  Windows Production (Waitress):
    waitress-serve --listen=0.0.0.0:5001 "server.wsgi:app"
"""

import sys
from server.app import create_app
from server.config import settings

# Instantiate WSGI callable
# In production (CARSPECTIVE_ENV=production), create_app() validates configuration fail-fast.
app = create_app()

if __name__ == "__main__":
    if settings.IS_PRODUCTION:
        sys.stderr.write(
            "CRITICAL: Direct execution of server/wsgi.py with the development server in production is prohibited.\n"
            "Use a production WSGI server (e.g., gunicorn --bind 0.0.0.0:5001 server.wsgi:app) instead.\n"
        )
        sys.exit(1)
    else:
        app.run(host="0.0.0.0", port=5001, debug=settings.DEBUG)
