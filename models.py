from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class ProcessedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    processed_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    processing_time = db.Column(db.Float, nullable=False)
    processing_date = db.Column(db.DateTime, default=datetime.utcnow)
    changes = db.Column(db.JSON, nullable=True)
    
    def __repr__(self):
        return f'<ProcessedFile {self.original_filename}>'