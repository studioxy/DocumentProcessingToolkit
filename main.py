# main.py
# Flask app initialization and configuration for DocumentProcessingToolkit

import os
import logging

from flask import Flask
from models import db

# Tworzymy aplikację Flask
app = Flask(__name__)

# Ustawiamy secret key (może być z ENV albo domyślny dla dev)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "dev_secret_key"

# Konfiguracja bazy danych: najpierw z ENV, a jak nie ma to SQLite do testów/dev
app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.environ.get("DATABASE_URL") or "sqlite:///test.db"
)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Inicjalizujemy SQLAlchemy z aplikacją
db.init_app(app)

# Importujemy routes i resztę logiki PO skonfigurowaniu aplikacji
from app import *

# Tworzymy tabele, jeśli nie istnieją (tylko w dev)
with app.app_context():
    db.create_all()

# Uruchamiamy serwer, jeśli to główny plik
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
