from flask import Flask
from klausurarchiv import webapp, db, cli
from flask_cors import CORS


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    app.config.from_mapping(
        ARCHIVE_PATH=app.instance_path,
        MAX_CONTENT_PATH=int(100e6)
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    app.teardown_appcontext(db.Archive.close_singleton)

    app.register_blueprint(cli.bp)
    app.register_blueprint(webapp.bp)

    return app
