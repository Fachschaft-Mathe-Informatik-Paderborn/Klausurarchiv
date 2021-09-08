from pathlib import Path
import datetime
from uuid import UUID
import os
import shutil
import json

META_FILENAME = Path("meta.json")


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
        assert (self.__get_config_path().exists())

    def __get_config_path(self):
        return self.__path / META_FILENAME

    def __get_config(self) -> dict:
        config_path = self.__get_config_path()
        with open(config_path, mode="r") as file:
            config = json.load(file)
        return config

    def __set_config_field(self, key: str, value: str):
        config = self.__get_config()
        config[key] = value
        config_path = self.__get_config_path()
        with open(config_path, mode="w") as file:
            json.dump(config, file)

    @property
    def uuid(self) -> UUID:
        return UUID(self.path.name.partition(" ")[0])

    @property
    def downloadable(self) -> bool:
        return self.__get_config()["downloadable"]

    @downloadable.setter
    def downloadable(self, new_value: bool):
        self.__set_config_field("downloadable", str(new_value))

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def name(self) -> str:
        return self.path.name.partition(" ")[2]

    @name.setter
    def name(self, new_name: str):
        new_path = Path(self.path)
        new_path.name = Path(f"{self.uuid} {new_name}")
        shutil.move(self.__path, new_path)
        self.__path = new_path

    @property
    def date(self) -> datetime.date:
        return datetime.date.fromisoformat(self.__get_config()["date"])

    @date.setter
    def date(self, new_date: date):
        self.__set_config_field("date", new_date.isoformat())

    @property
    def author(self) -> str:
        return self.__get_config()["author"]

    @author.setter
    def author(self, new_author: str):
        self.__set_config_field("author", new_author)

    @property
    def documents(self) -> list[Document]:
        return [Document(doc_path) for doc_path in self.path.iterdir() if doc_path.name != META_FILENAME]

    def add_document(self, original_path: Path) -> Document:
        target_path = self.path / original_path.name
        if original_path.name == META_FILENAME:
            raise KeyError(f"Documents may not have the name {META_FILENAME}")
        shutil.copy(original_path, target_path)
        return Document(target_path)

    def remove_document(self, document: Document):
        if document.path.parent != self.path:
            raise KeyError(f"Document {document} is not part of item {self}")
        if document.path.name == META_FILENAME:
            raise KeyError(f"{META_FILENAME} is not a document")
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
