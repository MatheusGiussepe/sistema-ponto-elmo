from app import app
from extensoes import db

with app.app_context():
    db.create_all()
