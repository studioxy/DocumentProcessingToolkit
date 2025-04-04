import os
import logging

from flask import Flask
from models import db

# Create the app
app = Flask(__name__)

# Setup a secret key
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "dev_secret_key"

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import routes after initializing app
from app import *

# Create all database tables
with app.app_context():
    db.create_all()

# Start the server if file is executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
