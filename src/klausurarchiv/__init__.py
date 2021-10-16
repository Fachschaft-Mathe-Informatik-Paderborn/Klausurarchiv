from flask import Flask
from flask_cors import CORS

from klausurarchiv import webapp, db
from werkzeug.exceptions import HTTPException
from flask import Response, g
import json


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    app.config.from_mapping(
        ARCHIVE_PATH=app.instance_path,
        MAX_CONTENT_PATH=int(100e6),
        SESSION_COOKIE_NAME="KLAUSURARCHIV"
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        app.secret_key = db.Archive(app.config["ARCHIVE_PATH"]).secret_key
    except FileNotFoundError:
        pass

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
        g.archive = db.Archive(app.config["ARCHIVE_PATH"])

    app.teardown_appcontext(db.Archive.close_singleton)
    app.register_blueprint(webapp.bp)
    for resource in [db.Document, db.Course, db.Folder, db.Author]:
        resource.register_resource(app)

    return app
