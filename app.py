"""
Office Management System (OMS) - Vercel / WSGI Application Entry Point
Re-exports the Flask 'app' instance initialized in run.py.
"""
from run import app

# For local invocation via 'python app.py'
if __name__ == '__main__':
    app.run()
