from flask import Flask
from flask_cors import CORS
from models import db
from config import Config
import routes

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['JSON_AS_ASCII'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    CORS(app, resources={r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": "*",
        "expose_headers": "*",
        "supports_credentials": True
    }})

    routes.init_app(app)

    return app

if __name__ == '__main__':
    create_app().run(debug=True, host='0.0.0.0', port=5002)