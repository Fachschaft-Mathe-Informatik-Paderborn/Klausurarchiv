from pathlib import Path
from datetime import date


class Document(object):
    @property
    def path(self) -> Path:
        pass


class Item(object):
    def __init__(self):
        pass

    @property
    def downloadable(self) -> bool: 
        pass

    @property
    def path(self) -> Path:
        pass

    @property
    def name(self) -> str:
        pass

    @property
    def date(self) -> date:
        pass

    @property
    def author(self) -> str:
        pass

    @property
    def documents(self) -> list[Document]:
        pass

    def add_document(self, original_path: Path) -> Document:
        pass

    def remove_document(self, document: Document):
        pass


class Subject(object):
    @property
    def items(self) -> list[Item]:
        pass

    def add_item(self, item: Item):
        pass

    def remove_item(self, item: Item):
        pass


class Archive(object):
    def __init__(self, base_path: Path):
        self.__base_path = base_path

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