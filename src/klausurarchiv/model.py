import datetime
import os
import shutil
import sqlite3
from pathlib import Path
from typing import List
from uuid import uuid4

SCHEMA_SQL = """
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Items" (
    "ID"	        INTEGER NOT NULL,
    "downloadable"  INTEGER DEFAULT false,
    "name"	        TEXT,
    "date"	        TEXT,
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Documents" (
    "ID"	INTEGER NOT NULL,
    "name"	TEXT,
    "path"	TEXT,
    "item"	INTEGER,
    PRIMARY KEY("ID" AUTOINCREMENT),
    FOREIGN KEY("item") REFERENCES "Items"("ID")
);
CREATE TABLE IF NOT EXISTS "SubjectNames" (
    "ID"	INTEGER NOT NULL,
    "name"	TEXT NOT NULL,
    FOREIGN KEY("ID") REFERENCES "Subjects"("ID")
);
CREATE TABLE IF NOT EXISTS "Subjects" (
    "ID"	INTEGER NOT NULL,
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "ItemSubjectMap" (
    "ItemID"	INTEGER NOT NULL,
    "SubjectID"	INTEGER NOT NULL,
    FOREIGN KEY("ItemID") REFERENCES "Items"("ID"),
    FOREIGN KEY("SubjectID") REFERENCES "Subjects"("ID")
);
COMMIT;
"""


class Document(object):
    def __init__(self, db: sqlite3.Connection, doc_id: int):
        self.__db = db
        self.__doc_id = doc_id

    @property
    def doc_id(self) -> int:
        return self.__doc_id

    @property
    def name(self) -> str:
        cursor = self.__db.cursor()
        cursor.execute("select name from Documents where ID=?", (self.__doc_id,))
        name = cursor.fetchone()[0]
        cursor.close()
        return name

    @name.setter
    def name(self, new_name: str):
        cursor = self.__db.cursor()
        cursor.execute("update Documents set name=? where ID=?", (new_name, self.__doc_id))
        cursor.close()

    @property
    def path(self) -> Path:
        cursor = self.__db.cursor()
        cursor.execute("select path from Documents where ID=?", (self.__doc_id,))
        path = Path(cursor.fetchone()[0])
        cursor.close()
        return path

    def __eq__(self, other: 'Document') -> bool:
        return self.__db == other.__db and self.doc_id == other.doc_id

    def __ne__(self, other: 'Document') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash((self.__db, self.doc_id))


class ItemMeta(object):
    def __init__(self, db: sqlite3.Connection, item_id: int):
        self.downloadable = False
        self.name = None
        self.date = None

        cursor = db.cursor()
        cursor.execute("select downloadable, name, date from Items where ID=?", (item_id,))
        (downloadable, name, date) = cursor.fetchone()
        self.downloadable = downloadable == 1
        self.name = name
        if date is None:
            self.date = None
        else:
            self.date = datetime.date.fromisoformat(date)
        cursor.close()

    def store(self, db: sqlite3.Connection, item_id: int):
        cursor = db.cursor()
        if self.downloadable:
            downloadable = 1
        else:
            downloadable = 0
        name = self.name
        date = self.date.isoformat()
        cursor.execute("update Items set downloadable=?, name=?, date=? where ID=?",
                       (downloadable, name, date, item_id))
        cursor.close()


class Item(object):
    def __init__(self, item_id: int, db: sqlite3.Connection, docs_dir: Path):
        self.__item_id = item_id
        self.__db = db
        self.__docs_dir = docs_dir

    @property
    def meta(self) -> ItemMeta:
        return ItemMeta(self.__db, self.__item_id)

    @meta.setter
    def meta(self, new_meta: ItemMeta):
        new_meta.store(self.__db, self.__item_id)

    @property
    def item_id(self):
        return self.__item_id

    @property
    def documents(self) -> List[Document]:
        cursor = self.__db.cursor()
        docs = [Document(self.__db, int(row[0])) for row in
                cursor.execute("select ID from Documents where item=?", (self.__item_id,))]
        cursor.close()
        return docs

    def add_document(self, original_path: Path) -> Document:
        target_path = self.__docs_dir / Path(f"{uuid4()}{original_path.suffix}")
        shutil.move(original_path, target_path)

        cursor = self.__db.cursor()
        cursor.execute("insert into Documents(name, path, item) values (?, ?, ?)",
                       (original_path.name, str(target_path), self.__item_id))
        doc = Document(self.__db, cursor.lastrowid)
        cursor.close()

        return doc

    def remove_document(self, document: Document):
        cursor = self.__db.cursor()
        cursor.execute("delete from Documents where ID=?", (document.doc_id,))
        cursor.close()

    def __eq__(self, other: 'Item') -> bool:
        return self.__db == other.__db and self.item_id == other.item_id

    def __ne__(self, other: 'Item') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash((self.__db, self.item_id))


class Archive(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)
        self.__db: sqlite3.Connection = sqlite3.connect(self.path / Path("archive.sqlite"))
        cursor = self.__db.cursor()
        cursor.executescript(SCHEMA_SQL)
        cursor.close()

        if not self.docs_dir.exists():
            os.mkdir(self.docs_dir)

    def __del__(self):
        self.__db.commit()

    @property
    def docs_dir(self) -> Path:
        return self.__path / Path("docs")

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def items(self) -> List[Item]:
        cursor = self.__db.cursor()
        items = [Item(item_id[0], self.__db, self.docs_dir) for item_id in cursor.execute("select ID from Items")]
        cursor.close()
        return items

    def add_item(self) -> Item:
        cursor = self.__db.cursor()
        cursor.execute('insert into Items(name) values (NULL)')
        item = Item(int(cursor.lastrowid), self.__db, self.docs_dir)
        cursor.close()
        return item

    def remove_item(self, item: Item):
        cursor = self.__db.cursor()
        cursor.execute("delete from Items where Id = ?", (item.item_id,))
        cursor.close()

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __new(self, other: 'Archive') -> bool:
        return not self.path == other.path
