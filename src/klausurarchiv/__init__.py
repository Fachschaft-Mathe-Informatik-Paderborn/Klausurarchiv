import json
import os

from flask import Flask
from flask import Response, g
from flask_cors import CORS
from flask_login import LoginManager
from werkzeug.exceptions import HTTPException

from klausurarchiv import auth, database


def create_app(test_config=None):
    app = Flask(__name__, instance_path=os.environ.get("KLAUSURARCHIV_INSTANCE"), instance_relative_config=True)

    # should add the argument origins=["https://fsmi.uni-paderborn.de"] after deployment
    CORS(app, supports_credentials=True)

    app.config.from_mapping(
        ARCHIVE_PATH=app.instance_path,
        MAX_CONTENT_LENGTH=int(100e6),
        SESSION_COOKIE_NAME="KLAUSURARCHIV",
        USERNAME=None,
        PASSWORD_SHA256=None,
        CACHE_TYPE="SimpleCache",
        CACHE_DEFAULT_TIMEOUT=300
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        app.secret_key = database.Archive(app.config["ARCHIVE_PATH"]).secret_key
    except FileNotFoundError:
        pass

    login_manager = LoginManager()
    login_manager.init_app(app)

    @app.errorhandler(Exception)
    def handle_http_exception(e: Exception):
        if isinstance(e, HTTPException):
            return Response(
                response=json.dumps({
                    "message": e.description,
                }),
                status=e.code,
                content_type="application/json"
            )
        else:
            app.logger.error(e, exc_info=True)
            return Response(
                response=json.dumps({
                    "message": "Internal Server Error",
                }),
                status=500,
                content_type="application/json"
            )

    @app.before_request
    def open_archive():
        g.archive = database.Archive(app.config["ARCHIVE_PATH"])

    auth.init_app(app)

    # separately because order is important!
    from klausurarchiv.models import db
    db.init_app(app)

    with app.app_context():
        db.create_all()

    from klausurarchiv.models import ma
    ma.init_app(app)

    app.register_blueprint(database.bp)

    return app
