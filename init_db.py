from app import app
from extensions import db
from models import *

def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
