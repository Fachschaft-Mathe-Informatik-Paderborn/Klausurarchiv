import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

META_FILENAME = Path("meta.json")


class Document(object):
    def __init__(self, path: Path):
        self.__path = path

    @property
    def path(self) -> Path:
        return self.__path

    def __str__(self) -> str:
        return str(self.path.parent / self.path.name)


class ItemMeta(object):
    def __init__(self):
        self.downloadable: bool = False
        self.date: Optional[datetime.date] = None
        self.author: Optional[str] = None


class Item(object):
    def __init__(self, path: Path):
        self.__path = path

    @property
    def __meta_path(self):
        return self.__path / META_FILENAME

    @property
    def __meta(self) -> ItemMeta:
        meta = ItemMeta()
        with open(self.__meta_path, mode="r") as file:
            meta.__dict__ = json.load(file)
        return meta

    @__meta.setter
    def __meta(self, new_meta: ItemMeta):
        with open(self.__meta_path, mode="w") as file:
            json.dump(new_meta.__dict__, file)

    @staticmethod
    def new_item(base_dir: Path) -> 'Item':
        uuid = uuid4()
        name = "unnamed"
        item_path = base_dir / Path(f"{uuid} {name}")
        os.mkdir(item_path)

        item = Item(item_path)
        item.__meta = ItemMeta()
        return item

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def uuid(self) -> UUID:
        return UUID(self.path.name.partition(" ")[0])

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
    def downloadable(self) -> bool:
        return self.__meta.downloadable

    @downloadable.setter
    def downloadable(self, new_value: bool):
        meta = self.__meta
        meta.downloadable = new_value
        self.__meta = meta

    @property
    def date(self) -> Optional[datetime.date]:
        return self.__meta.date

    @date.setter
    def date(self, new_date: Optional[datetime.date]):
        meta = self.__meta
        meta.date = new_date
        self.__meta = meta

    @property
    def author(self) -> Optional[str]:
        return self.__meta.author

    @author.setter
    def author(self, new_author: str):
        meta = self.__meta
        meta.author = new_author
        self.__meta = meta

    @property
    def documents(self) -> list[Document]:
        return [Document(doc_path) for doc_path in self.path.iterdir() if doc_path.name != META_FILENAME]

    def add_document(self, original_path: Path) -> Document:
        if original_path.name == META_FILENAME:
            raise KeyError(f"Documents may not have the name {META_FILENAME}")
        target_path = self.path / original_path.name
        shutil.copy(original_path, target_path)
        return Document(target_path)

    def remove_document(self, document: Document):
        if document.path.parent != self.path:
            raise KeyError(f"Document {document} is not part of item {self}")
        if document.path.name == META_FILENAME:
            raise KeyError(f"{META_FILENAME} is not a document")
        os.remove(document.path)

    def __str__(self) -> str:
        return str(self.path.name)


class Archive(object):
    def __init__(self, path: Path):
        self.__path = path

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def items(self) -> list[Item]:
        return [Item(item_path) for item_path in self.path.iterdir() if item_path.is_dir()]

    def add_item(self) -> Item:
        item = Item.new_item(self.path)
        return item

    def remove_item(self, item: Item):
        if item.path.parent != self.path:
            raise KeyError(f"Item {item} is not part of the archive")
        shutil.rmtree(item.path)
