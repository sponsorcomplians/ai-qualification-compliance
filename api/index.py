from flask import Flask
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import your Flask app
from main import app

# This is the entry point that Vercel will call
def handler(request, response):
    return app(request.environ, response)

# For Vercel serverless functions
if __name__ == "__main__":
    app.run()
