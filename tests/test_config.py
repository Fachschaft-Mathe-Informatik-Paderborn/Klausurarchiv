import json
import sqlite3
import tempfile
from pathlib import Path

import klausurarchiv
from klausurarchiv import create_app


def test_config():
    with tempfile.TemporaryDirectory() as tempdir:
        app = create_app(instance_path=tempdir)

        assert type(app.secret_key) == str
        assert len(app.secret_key) > 8

        config_path = Path(tempdir) / Path("config.json")
        assert json.load(open(config_path, mode="r")) == klausurarchiv.DEFAULT_CONFIG

        secret_path = Path(tempdir) / Path("secret")
        assert secret_path.is_file()
        assert secret_path.stat().st_mode & 0o777 == 0o400

        db_path = Path(tempdir) / Path("database.sqlite")
        old_config = json.load(open(config_path, mode="r"))
        old_config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        json.dump(old_config, open(config_path, mode="w"))

        create_app(instance_path=tempdir)
        assert db_path.is_file()
        sqlite3.connect(db_path)
