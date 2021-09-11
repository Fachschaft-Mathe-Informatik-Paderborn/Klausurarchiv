import datetime
import os
import shutil
import sqlite3
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID

SCHEMA_SQL = """
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Items" (
    "ID"	        INTEGER NOT NULL,
    "UUID"          TEXT NOT NULL UNIQUE,
    "downloadable"	INTEGER DEFAULT false NOT NULL,
    "name"	        TEXT NOT NULL,
    "date"	        TEXT,
    "folderID"      ID,
    "authorID"      ID,
    FOREIGN KEY("folderID") REFERENCES "Folders"("ID"),
    FOREIGN KEY("authorID") REFERENCES "Authors"("ID"),
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Documents" (
    "ID"	INTEGER NOT NULL,
    "name"	TEXT NOT NULL,
    "path"	TEXT NOT NULL,
    "item"	INTEGER NOT NULL,
    FOREIGN KEY("item") REFERENCES "Items"("ID"),
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Courses" (
    "ID"	            INTEGER NOT NULL,
    "canonical_name"	TEXT NOT NULL,
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "CourseAliases" (
    "ID"	INTEGER NOT NULL,
    "alias"	TEXT NOT NULL,
    PRIMARY KEY("ID","alias"),
    FOREIGN KEY("ID") REFERENCES "Courses"("ID")
);
CREATE TABLE IF NOT EXISTS "ItemCourseMap" (
    "ItemID"	INTEGER NOT NULL,
    "CourseID"	INTEGER NOT NULL,
    PRIMARY KEY("ItemID","CourseID"),
    FOREIGN KEY("CourseID") REFERENCES "Courses"("ID"),
    FOREIGN KEY("ItemID") REFERENCES "Items"("ID")
);
CREATE TABLE IF NOT EXISTS "Folders" (
    "ID"    INTEGER NOT NULL,
    "name"  TEXT NOT NULL,
    PRIMARY KEY("ID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Authors" (
    "ID"    INTEGER NOT NULL,
    "name"  TEXT NOT NULL,
    PRIMARY KEY("ID" AUTOINCREMENT)
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


class Folder(object):
    def __init__(self, folder_id: int, db: sqlite3.Connection):
        self.__folder_id = folder_id
        self.__db = db

    @property
    def folder_id(self) -> int:
        return self.__folder_id

    @property
    def name(self) -> str:
        cursor = self.__db.cursor()
        cursor.execute("select name from Folders where ID=?", (self.folder_id,))
        name = cursor.fetchone()[0]
        cursor.close()
        return name

    @name.setter
    def name(self, new_name):
        cursor = self.__db.cursor()
        cursor.execute("update Folders set name=? where ID=?", (new_name, self.folder_id))
        cursor.close()

    def __eq__(self, other: 'Folder'):
        return self.__db == other.__db and self.folder_id == other.folder_id

    def __ne__(self, other: 'Folder'):
        return not self == other

    def __hash__(self):
        return hash((self.folder_id, self.__db))


class Author(object):
    def __init__(self, author_id: int, db: sqlite3.Connection):
        self.__author_id = author_id
        self.__db = db

    @property
    def author_id(self) -> int:
        return self.__author_id

    @property
    def name(self) -> str:
        cursor = self.__db.cursor()
        cursor.execute("select name from Authors where ID=?", (self.author_id,))
        name = cursor.fetchone()[0]
        cursor.close()
        return name

    @name.setter
    def name(self, new_name):
        cursor = self.__db.cursor()
        cursor.execute("update Authors set name=? where ID=?", (new_name, self.author_id))
        cursor.close()

    def __eq__(self, other: 'Author'):
        return self.__db == other.__db and self.author_id == other.author_id

    def __ne__(self, other: 'Author'):
        return not self == other

    def __hash__(self):
        return hash((self.author_id, self.__db))


class Item(object):
    def __init__(self, item_id: int, db: sqlite3.Connection, docs_dir: Path):
        self.__item_id = item_id
        self.__db = db
        self.__docs_dir = docs_dir

    @property
    def uuid(self) -> UUID:
        cursor = self.__db.cursor()
        cursor.execute("select uuid from Items where ID=?", (self.item_id,))
        uuid = UUID(cursor.fetchone()[0])
        cursor.close()
        return uuid

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
    def date(self) -> Optional[datetime.date]:
        cursor = self.__db.cursor()
        cursor.execute("select date from Items where ID=?", (self.item_id,))
        date = cursor.fetchone()[0]
        if date is not None:
            date = datetime.date.fromisoformat(date)
        cursor.close()
        return date

    @date.setter
    def date(self, new_date: Optional[datetime.date]):
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

    def get_document_with_name(self, name: str) -> Optional[Document]:
        cursor = self.__db.cursor()
        cursor.execute("select ID from Documents where name=?", (name,))
        document = cursor.fetchone()
        if document is not None:
            document = Document(self.__db, document[0])
        cursor.close()
        return document

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

    @property
    def author(self) -> Optional[Author]:
        cursor = self.__db.cursor()
        cursor.execute("select authorID from Items where ID=?", (self.item_id,))
        author = cursor.fetchone()[0]
        if author is not None:
            author = Author(author, self.__db)
        cursor.close()
        return author

    @author.setter
    def author(self, folder: Optional[Author]):
        cursor = self.__db.cursor()
        cursor.execute("update Items set authorID=? where ID=?", (folder.author_id, self.item_id))
        cursor.close()

    @property
    def folder(self) -> Optional[Folder]:
        cursor = self.__db.cursor()
        cursor.execute("select folderID from Items where ID=?", (self.item_id,))
        folder = cursor.fetchone()[0]
        if folder is not None:
            folder = Folder(folder, self.__db)
        cursor.close()
        return folder

    @folder.setter
    def folder(self, folder: Optional[Folder]):
        cursor = self.__db.cursor()
        cursor.execute("update Items set folderID=? where ID=?", (folder.folder_id, self.item_id))
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

    def add_item(self, name: str) -> Item:
        cursor = self.__db.cursor()
        cursor.execute('insert into Items(name, uuid) values (?, ?)', (name, str(uuid4())))
        item = Item(int(cursor.lastrowid), self.__db, self.docs_dir)
        cursor.close()
        return item

    def remove_item(self, item: Item):
        cursor = self.__db.cursor()
        cursor.execute("delete from Items where Id = ?", (item.item_id,))
        cursor.close()

    def get_item_with_uuid(self, uuid: UUID) -> Optional[Item]:
        cursor = self.__db.cursor()
        cursor.execute("select ID from Items where uuid=?", (str(uuid),))
        item = cursor.fetchone()
        if item is not None:
            item = Item(item[0], self.__db, self.docs_dir)
        cursor.close()
        return item

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

    def get_items_for_course(self, course: Course) -> List[Item]:
        cursor = self.__db.cursor()
        items = [Item(row[0], self.__db, self.docs_dir) for row in
                 cursor.execute("select ItemID from ItemCourseMap where CourseID=?", (course.course_id,))]
        cursor.close()
        return items

    @property
    def folders(self) -> List[Folder]:
        cursor = self.__db.cursor()
        folders = [Folder(row[0], self.__db) for row in cursor.execute("select ID from Folders")]
        cursor.close()
        return folders

    def add_folder(self, name: str) -> Folder:
        cursor = self.__db.cursor()
        cursor.execute("insert into Folders(name) values (?)", (name,))
        folder = Folder(cursor.lastrowid, self.__db)
        cursor.close()
        return folder

    def remove_folder(self, folder: Folder):
        cursor = self.__db.cursor()
        cursor.execute("delete from Folders where ID=?", (folder.folder_id,))
        cursor.close()

    def get_items_in_folder(self, folder: Folder) -> List[Item]:
        cursor = self.__db.cursor()
        items = [Item(row[0], self.__db, self.docs_dir) for row in
                 cursor.execute("select ID from Items where folderID=?", (folder.folder_id,))]
        cursor.close()
        return items

    @property
    def authors(self) -> List[Author]:
        cursor = self.__db.cursor()
        authors = [Author(row[0], self.__db) for row in cursor.execute("select ID from Authors")]
        cursor.close()
        return authors

    def add_author(self, name: str) -> Author:
        cursor = self.__db.cursor()
        cursor.execute("insert into Authors(name) values (?)", (name,))
        author = Author(cursor.lastrowid, self.__db)
        cursor.close()
        return author

    def remove_author(self, author: Author):
        cursor = self.__db.cursor()
        cursor.execute("delete from Authors where ID=?", (author.author_id,))
        cursor.close()

    def get_author_by_name(self, name: str) -> Optional[Author]:
        cursor = self.__db.cursor()
        cursor.execute("select ID from Authors where name=?", (name,))
        author = cursor.fetchone()
        if author is not None:
            author = Author(author[0], self.__db)
        cursor.close()
        return author

    def get_items_by_author(self, author: Author) -> List[Item]:
        cursor = self.__db.cursor()
        items = [Item(row[0], self.__db, self.docs_dir) for row in
                 cursor.execute("select ID from Items where authorID=?", (author.author_id,))]
        cursor.close()
        return items

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __new(self, other: 'Archive') -> bool:
        return not self.path == other.path
