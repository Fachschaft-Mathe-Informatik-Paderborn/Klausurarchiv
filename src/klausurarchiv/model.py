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
    "ID"	INTEGER NOT NULL,
    "downloadable"	INTEGER DEFAULT false,
    "name"	TEXT,
    "date"	TEXT,
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Documents" (
    "ID"	INTEGER NOT NULL,
    "name"	TEXT,
    "path"	TEXT,
    "item"	INTEGER,
    FOREIGN KEY("item") REFERENCES "Items"("ID"),
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "CourseAliases" (
    "ID"	INTEGER NOT NULL,
    "alias"	TEXT NOT NULL,
    PRIMARY KEY("ID","alias"),
    FOREIGN KEY("ID") REFERENCES "Courses"("ID")
);
CREATE TABLE IF NOT EXISTS "Courses" (
    "ID"	            INTEGER NOT NULL,
    "canonical_name"	TEXT,
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "ItemCourseMap" (
    "ItemID"	INTEGER NOT NULL,
    "CourseID"	INTEGER NOT NULL,
    PRIMARY KEY("ItemID","CourseID"),
    FOREIGN KEY("CourseID") REFERENCES "Courses"("ID"),
    FOREIGN KEY("ItemID") REFERENCES "Items"("ID")
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


class Course(object):
    def __init__(self, course_id: int, db: sqlite3.Connection):
        self.__courses_id = course_id
        self.__db = db

    @property
    def course_id(self) -> int:
        return self.__courses_id

    @property
    def canonical_name(self) -> str:
        cursor = self.__db.cursor()
        cursor.execute("select canonical_name from Courses where ID=?", (self.course_id,))
        name = cursor.fetchone()[0]
        cursor.close()
        return name

    @canonical_name.setter
    def canonical_name(self, new_name):
        cursor = self.__db.cursor()
        cursor.execute("update Courses set canonical_name=? where ID=?", (new_name, self.course_id))
        cursor.close()

    @property
    def aliases(self) -> List[str]:
        cursor = self.__db.cursor()
        names = [row[0] for row in
                 cursor.execute("select `alias` from `CourseAliases` where ID=?", (self.__courses_id,))]
        cursor.close()
        return names

    def add_alias(self, new_alias: str):
        cursor = self.__db.cursor()
        cursor.execute("insert into CourseAliases(ID, alias) values (?, ?)", (self.__courses_id, new_alias))
        cursor.close()

    def remove_alias(self, alias: str):
        cursor = self.__db.cursor()
        cursor.execute("delete from CourseAliases where ID=? and alias=?", (self.__courses_id, alias))
        cursor.close()

    def __eq__(self, other: 'Course') -> bool:
        return self.__db == other.__db and self.course_id == other.course_id

    def __ne__(self, other: 'Course') -> bool:
        return not self == other

    def __hash__(self):
        return hash((self.course_id, self.__db))


class Item(object):
    def __init__(self, item_id: int, db: sqlite3.Connection, docs_dir: Path):
        self.__item_id = item_id
        self.__db = db
        self.__docs_dir = docs_dir

    @property
    def item_id(self):
        return self.__item_id

    @property
    def downloadable(self) -> bool:
        cursor = self.__db.cursor()
        cursor.execute("select downloadable from Items where ID=?", (self.item_id,))
        downloadable = cursor.fetchone()[0] == 1
        cursor.close()
        return downloadable

    @downloadable.setter
    def downloadable(self, downloadable: bool):
        cursor = self.__db.cursor()
        if downloadable:
            downloadable = 1
        else:
            downloadable = 0
        cursor.execute("update Items set downloadable=? where ID=?", (downloadable, self.item_id))
        cursor.close()

    @property
    def name(self) -> str:
        cursor = self.__db.cursor()
        cursor.execute("select name from Items where ID=?", (self.item_id,))
        name = cursor.fetchone()[0]
        cursor.close()
        return name

    @name.setter
    def name(self, new_name: str):
        cursor = self.__db.cursor()
        cursor.execute("update Items set name=? where ID=?", (new_name, self.item_id))
        cursor.close()

    @property
    def date(self) -> datetime.date:
        cursor = self.__db.cursor()
        cursor.execute("select date from Items where ID=?", (self.item_id,))
        date = datetime.date.fromisoformat(cursor.fetchone()[0])
        cursor.close()
        return date

    @date.setter
    def date(self, new_date: datetime.date):
        cursor = self.__db.cursor()
        cursor.execute("update Items set date=? where ID=?", (new_date.isoformat(), self.item_id))
        cursor.close()

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

    @property
    def applicable_courses(self) -> List[Course]:
        cursor = self.__db.cursor()
        courses = [Course(row[0], self.__db) for row in
                   cursor.execute("select CourseID from ItemCourseMap where ItemID=?", (self.item_id,))]
        cursor.close()
        return courses

    def add_to_course(self, course: Course):
        cursor = self.__db.cursor()
        cursor.execute("insert into ItemCourseMap(ItemID, CourseID) values (?, ?)", (self.item_id, course.course_id))
        cursor.close()

    def remove_from_course(self, course: Course):
        cursor = self.__db.cursor()
        cursor.execute("delete from ItemCourseMap where ItemID=? and CourseID=?", (self.item_id, course.course_id))
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

    @property
    def courses(self) -> List[Course]:
        cursor = self.__db.cursor()
        courses = [Course(row[0], self.__db) for row in cursor.execute("select ID from Courses")]
        cursor.close()
        return courses

    def add_course(self, canonical_name: str) -> Course:
        cursor = self.__db.cursor()
        cursor.execute("insert into Courses(canonical_name) values (?)", (canonical_name,))
        course = Course(cursor.lastrowid, self.__db)
        cursor.close()
        return course

    def remove_course(self, course: Course):
        cursor = self.__db.cursor()
        cursor.execute("delete from Courses where ID=?", (course.course_id,))
        cursor.close()

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __new(self, other: 'Archive') -> bool:
        return not self.path == other.path
