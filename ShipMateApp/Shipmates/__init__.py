# ShipMates/__init__.py
from flask import Flask

# Create the Flask application instance
app = Flask(__name__)

# Optional: Load configuration settings (if you plan to use configuration files or environment variables)
app.config.from_mapping(
    SECRET_KEY="your-secret-key",  # Replace with a secure random key in production
    SQLALCHEMY_TRACK_MODIFICATIONS=False,  # Useful if using SQLAlchemy
)

# Import views after creating the app instance to avoid circular imports
from Shipmates import views
from Shipmates import logins


