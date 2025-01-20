import os
from Shipmates import app  # Imports the app instance from Shipmates/__init__.py

if __name__ == '__main__':
    # Set default host and port
    HOST = os.environ.get('SERVER_HOST', '127.0.0.1')  # Use 127.0.0.1 instead of "localhost" for better compatibility
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555

    # Run the Flask application
    app.run(host=HOST, port=PORT, debug=True)  # Enable debug mode for development
