from flask import Flask
import pytest
from models import db
from config import Config

from flask import Flask
from models import db
from config import Config
import routes

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['JSON_AS_ASCII'] = False
    db.init_app(app)

    routes.init_app(app)

    return app

if __name__ == '__main__':
    create_app().run(debug=True, port=5000)