import os
import shutil
import sqlite3
from pathlib import Path

from flask import g, current_app


class Archive(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)
        if self.__db_path.is_file():
            self.__db: sqlite3.Connection = sqlite3.connect(self.__db_path)

    def init_archive(self):
        if self.path.exists():
            shutil.rmtree(self.path)
        os.makedirs(self.path)

        # Initialize docs directory
        os.makedirs(self.__docs_path)

        # Initialize database
        self.__db = sqlite3.connect(self.__db_path)
        with current_app.open_resource("schema.sql", mode="r") as f:
            self.__db.executescript(f.read())

        # Initialize secret
        with open(self.__secret_path, mode="wb") as file:
            file.write(os.urandom(32))
        self.__secret_path.chmod(0o400)

    def commit(self):
        self.__db.commit()

    @staticmethod
    def get_singleton():
        if "archive" not in g:
            g.archive = Archive(Path(current_app.config["ARCHIVE_PATH"]))
        return g.archive

    @staticmethod
    def close_singleton(e=None):
        archive = g.pop("archive", None)
        if archive is not None:
            del archive

    @property
    def secret_key(self) -> bytes:
        with open(self.__secret_path, mode="rb") as file:
            return file.read()

    @property
    def __db_path(self) -> Path:
        return self.__path / Path("archive.sqlite")

    @property
    def __docs_path(self) -> Path:
        return self.__path / Path("docs")

    @property
    def __secret_path(self) -> Path:
        return self.__path / Path("SECRET")

    @property
    def path(self) -> Path:
        return self.__path

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __new(self, other: 'Archive') -> bool:
        return not self.path == other.path
