import json
import os
import secrets
from pathlib import Path
from typing import Optional, Union

from flask import Flask
from flask import Response
from flask_cors import CORS
from flask_login import LoginManager
from werkzeug.exceptions import HTTPException

from klausurarchiv import auth, database

DEFAULT_CONFIG = {
    "MAX_CONTENT_LENGTH": int(100e6),
    "SESSION_COOKIE_NAME": "KLAUSURARCHIV",
    "USERNAME": None,
    "PASSWORD_SHA256": None,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,  # disables (unused) hooks that impact performance significantly
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
}


def create_app(test_config=None, instance_path: Optional[Union[Path, str]] = None):
    app = Flask(__name__)

    # should add the argument origins=["https://fsmi.uni-paderborn.de"] after deployment
    CORS(app, supports_credentials=True)

    app.config.from_mapping(DEFAULT_CONFIG)

    # If `test_config` is given, it will use it and generate a temporary secret. Otherwise, it will look for
    # configuration files. If the environment variable `KLAUSURARCHIV_INSTANCE` is set, it will use it the configuration
    # directory. Otherwise, it will use `/etc/klausurarchiv/`.
    #
    # The configuration files are:
    # * `config.json`: General, non-secret configuration values.
    # * `secret`: The secret signing secret.
    #
    # All of them are created with defaults or new values if they do not exist.
    if test_config is None:
        if instance_path is not None:
            app.instance_path = instance_path
        elif "KLAUSURARCHIV_INSTANCE" in os.environ:
            app.instance_path = os.environ["KLAUSURARCHIV_INSTANCE"]
        else:
            app.instance_path = Path("/etc/klausurarchiv/")

        app.instance_path = Path(app.instance_path)
        app.instance_path.mkdir(parents=True, exist_ok=True)

        config_path = app.instance_path / Path("config.json")
        secret_path = app.instance_path / Path("secret")

        if config_path.exists():
            app.config.from_file(config_path, silent=True, load=json.load)
        else:
            with open(config_path, mode="w") as config_file:
                json.dump(DEFAULT_CONFIG, config_file, indent="    ")

        if secret_path.exists():
            app.secret_key = open(secret_path, mode="r").read()
        else:
            app.secret_key = secrets.token_hex()
            secret_path.touch(mode=0o600)
            with open(secret_path, mode="w") as secret_file:
                secret_file.write(app.secret_key)
            secret_path.chmod(0o400)
    else:
        app.config.from_mapping(test_config)
        app.secret_key = secrets.token_hex()

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
