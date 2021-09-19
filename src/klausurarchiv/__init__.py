from flask import Flask
from klausurarchiv import webapp, model
from flask.cli import with_appcontext
import click
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

    @app.cli.add_command
    @click.command("init-archive")
    @with_appcontext
    def init_archive_command():
        model.Archive.get_singleton().init_archive()
    app.teardown_appcontext(model.Archive.close_singleton)

    app.register_blueprint(webapp.bp)

    return app
