from flask import Flask
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import your main Flask app
from main import app

# This is the entry point for Vercel
def handler(request):
    with app.app_context():
        return app.full_dispatch_request()

# For local testing
if __name__ == "__main__":
    app.run(debug=True)
