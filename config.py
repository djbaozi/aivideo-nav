import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'djbaozi-nav-2026-secret-key-change-in-prod')
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'nav.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
