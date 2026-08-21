import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        db_user = os.getenv('DB_USER_CATALOG')
        db_password = os.getenv('DB_PASSWORD_CATALOG')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = 'bookstore_catalog_db'
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?client_encoding=utf8"

    SQLALCHEMY_TRACK_MODIFICATIONS = False