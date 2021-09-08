from pathlib import Path
from datetime import date
from uuid import UUID
import os
import shutil
import json

CONFIG_FILENAME = Path(".config")


class Document(object):
    def __init__(self, path: Path):
        self.__path = path

    @property
    def path(self) -> Path:
        return self.__path


class Item(object):
    def __init__(self, path: Path):
        self.__path = path
        assert (self.__path.is_dir())
        assert ((self.__path / CONFIG_FILENAME).exists())

    def __get_config(self) -> dict:
        config_path = self.path / CONFIG_FILENAME
        return json.load(open(config_path, mode="r"))

    @property
    def uuid(self) -> UUID:
        return UUID(self.path.name.partition(" ")[0])

    @property
    def downloadable(self) -> bool:
        return self.__get_config()["downloadable"]

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def name(self) -> str:
        return self.path.name.partition(" ")[2]

    @property
    def date(self) -> date:
        return date.fromisoformat(self.__get_config()["date"])

    @property
    def author(self) -> str:
        return self.__get_config()["author"]

    @property
    def documents(self) -> list[Document]:
        return [Document(doc_path) for doc_path in self.path.iterdir() if doc_path.name != CONFIG_FILENAME]

    def add_document(self, original_path: Path) -> Document:
        target_path = self.path / original_path.name
        shutil.copy(original_path, target_path)
        return Document(target_path)

    def remove_document(self, document: Document):
        if document.path.parent != self.path:
            raise KeyError(f"Document {document} is not part of item {self}")
        os.remove(document.path)


class Subject(object):
    @property
    def items(self) -> list[Item]:
        pass

    def add_item(self, item: Item):
        pass

    def remove_item(self, item: Item):
        pass


class Archive(object):
    @property
    def items(self) -> list[Item]:
        pass

    def add_item(self) -> Item:
        pass

    def remove_item(self, item: Item):
        pass

    @property
    def subjects(self) -> list[Item]:
        pass

    def add_subject(self) -> Subject:
        pass

    def remove_subject(self, subject: Subject):
        pass
