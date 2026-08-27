import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_login import LoginManager

from app.config import get_config

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
login_manager = LoginManager()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_app():
    config_class = get_config()
    config_class.validate()

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "views.login_page"

    with app.app_context():
        from app import models

        from app.models.user import User

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        from app.auth import auth_bp
        app.register_blueprint(auth_bp)

        from app.uploads import uploads_bp
        app.register_blueprint(uploads_bp)

        from app.views import views_bp
        app.register_blueprint(views_bp)

        from app.cli import create_admin
        app.cli.add_command(create_admin)

        from app import sockets

    return app