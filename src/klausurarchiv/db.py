import os
import shutil
import sqlite3
from pathlib import Path

from flask import g, current_app


class Archive(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)
        if self.db_path.is_file():
            self.__db: sqlite3.Connection = sqlite3.connect(self.db_path)

    def init_archive(self):
        if not self.__path.exists():
            os.makedirs(self.__path)
        if self.docs_dir.exists():
            shutil.rmtree(self.docs_dir)
        os.makedirs(self.docs_dir)
        self.__db = sqlite3.connect(self.db_path)
        with current_app.open_resource("schema.sql", mode="r") as f:
            self.__db.executescript(f.read())

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
    def db_path(self):
        return self.__path / Path("archive.sqlite")

    @property
    def docs_dir(self) -> Path:
        return self.__path / Path("docs")

    @property
    def path(self) -> Path:
        return self.__path

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __new(self, other: 'Archive') -> bool:
        return not self.path == other.path
