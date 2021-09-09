import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Optional, List
from uuid import UUID, uuid4

META_FILENAME = Path("meta.json")


class Document(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)

    @property
    def path(self) -> Path:
        return self.__path

    def rename(self, new_name: str):
        new_path = self.path.parent / Path(new_name)
        shutil.move(self.path, new_path)
        self.__path = new_path

    def __str__(self) -> str:
        return str(self.path.parent / self.path.name)

    def __eq__(self, other) -> bool:
        return self.path == other.path

    def __ne__(self, other) -> bool:
        return self.path != other.path

    def __hash__(self) -> int:
        return hash(self.__path)


class ItemMeta(object):
    def __init__(self):
        self.downloadable: bool = False
        self.name = "unnamed"
        self.date: Optional[datetime.date] = None
        self.author: Optional[str] = None

    def store(self, file):
        data = self.__dict__
        if data["date"] is not None:
            data["date"] = self.date.isoformat()
        json.dump(data, file)

    def load(self, file):
        data = json.load(file)
        if data["date"] is not None:
            data["date"] = datetime.date.fromisoformat(data["date"])
        self.__dict__ = data


class Item(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)

    @property
    def meta_path(self):
        return self.__path / META_FILENAME

    @property
    def meta(self) -> ItemMeta:
        meta = ItemMeta()
        with open(self.meta_path, mode="r") as file:
            meta.load(file)
        return meta

    @meta.setter
    def meta(self, new_meta: ItemMeta):
        with open(self.meta_path, mode="w") as file:
            new_meta.store(file)

    @staticmethod
    def new_item(base_dir: Path) -> 'Item':
        uuid = uuid4()
        item_path = base_dir / Path(str(uuid))
        os.mkdir(item_path)

        item = Item(item_path)
        item.meta = ItemMeta()
        return item

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def uuid(self) -> UUID:
        return UUID(self.path.name)

    @property
    def documents(self) -> List[Document]:
        return [Document(doc_path) for doc_path in self.path.iterdir() if doc_path.name != str(META_FILENAME)]

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

    def __eq__(self, other) -> bool:
        return self.path == other.path

    def __ne__(self, other) -> bool:
        return self.path != other.path

    def __hash__(self) -> int:
        return hash(self.__path)


class Archive(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)
        if not self.items_dir.exists():
            os.mkdir(self.items_dir)

    @property
    def items_dir(self) -> Path:
        return self.path / Path("items")

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def items(self) -> List[Item]:
        return [Item(item_path) for item_path in self.items_dir.iterdir() if item_path.is_dir()]

    def add_item(self) -> Item:
        item = Item.new_item(self.items_dir)
        return item

    def remove_item(self, item: Item):
        if item.path.parent != self.items_dir:
            raise KeyError(f"Item {item} is not part of the archive")
        shutil.rmtree(item.path)

    def __eq__(self, other) -> bool:
        return self.path == other.path

    def __ne__(self, other) -> bool:
        return self.path != other.path

    def __hash__(self) -> int:
        return hash(self.__path)
