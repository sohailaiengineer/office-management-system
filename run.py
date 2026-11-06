import os
import socket
from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

def find_available_port(preferred_port=5000):
    env_port = os.environ.get('PORT')
    if env_port:
        return int(env_port)
    
    # Check preferred port first
    for port in [preferred_port, 5001, 5050, 8000, 8080]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return preferred_port

if __name__ == '__main__':
    port = find_available_port(5000)
    print(f"============================================================")
    print(f"  OFFICE MANAGEMENT SYSTEM (OMS) IS RUNNING LOCALLY")
    print(f"  Access URL: http://127.0.0.1:{port}")
    print(f"============================================================")
    app.run(host='127.0.0.1', port=port, debug=False)
