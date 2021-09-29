import datetime
import importlib.resources as import_res
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict

from flask import g, current_app


class Document(object):
    def __init__(self, db: sqlite3.Connection, doc_id: int, docs_path: Path):
        self.__db = db
        self.__doc_id = doc_id
        self.__docs_path = docs_path

    @property
    def doc_id(self) -> int:
        return self.__doc_id

    @property
    def name(self) -> str:
        cursor = self.__db.execute("select name from Documents where ID=?", (self.__doc_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name: str):
        self.__db.execute("update Documents set name=? where ID=?", (new_name, self.__doc_id))

    @property
    def content_type(self) -> str:
        cursor = self.__db.execute("select content_type from Documents where ID=?", (self.__doc_id,))
        return cursor.fetchone()[0]

    @content_type.setter
    def content_type(self, new_type: str):
        self.__db.set_authorizer("update Documents set content_type=? where ID=?", (new_type, self.__doc_id))

    @property
    def downloadable(self) -> bool:
        cursor = self.__db.execute("select downloadable from Documents where ID=?", (self.doc_id,))
        return cursor.fetchone()[0] == 1

    @downloadable.setter
    def downloadable(self, downloadable: bool):
        if downloadable:
            downloadable = 1
        else:
            downloadable = 0
        self.__db.execute("update Documents set downloadable=? where ID=?", (downloadable, self.doc_id))

    @property
    def path(self) -> Path:
        return self.__docs_path / Path(str(self.__doc_id))

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
    def long_name(self) -> str:
        cursor = self.__db.execute("select long_name from Courses where ID=?", (self.course_id,))
        return cursor.fetchone()[0]

    @long_name.setter
    def long_name(self, new_name):
        self.__db.execute("update Courses set long_name=? where ID=?", (new_name, self.course_id))

    @property
    def short_name(self) -> str:
        cursor = self.__db.execute("select short_name from Courses where ID=?", (self.course_id,))
        return cursor.fetchone()[0]

    @short_name.setter
    def short_name(self, new_name):
        self.__db.execute("update Courses set short_name=? where ID=?", (new_name, self.course_id))

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
        cursor = self.__db.execute("select name from Folders where ID=?", (self.folder_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name):
        self.__db.execute("update Folders set name=? where ID=?", (new_name, self.folder_id))

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
        cursor = self.__db.execute("select name from Authors where ID=?", (self.author_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name):
        self.__db.execute("update Authors set name=? where ID=?", (new_name, self.author_id))

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
    def item_id(self):
        return self.__item_id

    @property
    def name(self) -> str:
        cursor = self.__db.execute("select name from Items where ID=?", (self.item_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name: str):
        self.__db.execute("update Items set name=? where ID=?", (new_name, self.item_id))

    @property
    def date(self) -> Optional[datetime.date]:
        cursor = self.__db.execute("select date from Items where ID=?", (self.item_id,))
        date = cursor.fetchone()[0]
        if date is not None:
            date = datetime.date.fromisoformat(date)
        return date

    @date.setter
    def date(self, new_date: Optional[datetime.date]):
        self.__db.execute("update Items set date=? where ID=?", (new_date.isoformat(), self.item_id))

    @property
    def documents(self) -> List[Document]:
        return [Document(self.__db, int(row[0]), self.__docs_dir) for row in
                self.__db.execute("select DocumentID from ItemDocumentMap where ItemID=?", (self.__item_id,))]

    def add_document(self, document: Document):
        self.__db.execute("insert into ItemDocumentMap(ItemID, DocumentID) values (?, ?)",
                          (self.item_id, document.doc_id))

    def remove_document(self, document: Document):
        self.__db.execute("delete from ItemDocumentMap where ItemID=? and DocumentID=?",
                          (self.item_id, document.doc_id))

    @property
    def applicable_courses(self) -> List[Course]:
        return [Course(row[0], self.__db) for row in
                self.__db.execute("select CourseID from ItemCourseMap where ItemID=?", (self.item_id,))]

    def add_to_course(self, course: Course):
        self.__db.execute("insert into ItemCourseMap(ItemID, CourseID) values (?, ?)", (self.item_id, course.course_id))

    def remove_from_course(self, course: Course):
        self.__db.execute("delete from ItemCourseMap where ItemID=? and CourseID=?", (self.item_id, course.course_id))

    @property
    def authors(self) -> List[Author]:
        return [Author(row[0], self.__db) for row in
                self.__db.execute("select AuthorID from ItemAuthorMap where ItemID=?", (self.item_id,))]

    def add_author(self, author: Author):
        self.__db.execute("insert into ItemAuthorMap(ItemID, AuthorID) values (?, ?)", (self.item_id, author.author_id))

    def remove_author(self, author: Author):
        self.__db.execute("delete from ItemAuthorMap where ItemID=? and AuthorID=?", (self.item_id, author.author_id))

    @property
    def folder(self) -> List[Folder]:
        return [Folder(folder_id, self.__db) for folder_id in
                self.__db.execute("select FolderID from ItemFolderMap where ItemID=?", (self.item_id,))]

    def add_folder(self, folder: Folder):
        self.__db.execute("insert into ItemFolderMap(ItemID, FolderID) values (?, ?)", (self.item_id, folder.folder_id))

    def remove_folder(self, folder: Folder):
        self.__db.execute("delete from ItemFolderMap where ItemID=? and FolderID=?", (self.item_id, folder.folder_id))

    def __eq__(self, other: 'Item') -> bool:
        return self.__db == other.__db and self.item_id == other.item_id

    def __ne__(self, other: 'Item') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash((self.__db, self.item_id))


class Archive(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)
        if not self.__path.exists():
            os.makedirs(path)

        # Check Docs Dir
        if not self.docs_path.exists():
            os.makedirs(self.docs_path)

        # Check database
        database_exists = self.db_path.exists()
        self.__db: sqlite3.Connection = sqlite3.connect(self.db_path)
        if not database_exists:
            import klausurarchiv
            with import_res.open_text(klausurarchiv, "schema.sql") as f:
                self.__db.executescript(f.read())

        # Check secret
        if not self.secret_path.exists():
            with open(self.secret_path, mode="wb") as file:
                file.write(os.urandom(32))
            self.secret_path.chmod(0o400)

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
        with open(self.secret_path, mode="rb") as file:
            return file.read()

    @property
    def db_path(self) -> Path:
        return self.__path / Path("archive.sqlite")

    @property
    def docs_path(self) -> Path:
        return self.__path / Path("docs")

    @property
    def secret_path(self) -> Path:
        return self.__path / Path("SECRET")

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def items(self) -> List[Item]:
        return [Item(item_id[0], self.__db, self.docs_path) for item_id in self.__db.execute("select ID from Items")]

    def add_item(self, attributes: Dict) -> Item:
        cursor = self.__db.execute(
            "insert into Items(name, date, visible) values (?, ?, ?)",
            (attributes["name"], attributes["date"], attributes["visible"])
        )
        item = Item(cursor.lastrowid, self.__db, self.docs_path)
        self.__db.executemany(
            "insert into ItemDocumentMap values (?, ?)",
            ((item.item_id, doc_id) for doc_id in attributes["documents"])
        )
        self.__db.executemany(
            "insert into ItemAuthorMap values (?, ?)",
            ((item.item_id, author_id) for author_id in attributes["authors"])
        )
        self.__db.executemany(
            "insert into ItemCourseMap values (?, ?)",
            ((item.item_id, course_id) for course_id in attributes["courses"])
        )
        self.__db.executemany(
            "insert into ItemFolderMap values (?, ?)",
            ((item.item_id, folder_id) for folder_id in attributes["folders"])
        )
        return item

    def remove_item(self, item: Item):
        self.__db.execute("delete from Items where Id = ?", (item.item_id,))

    @property
    def documents(self) -> List[Document]:
        return [Document(self.__db, row[0], self.docs_path) for row in self.__db.execute("select ID from Documents")]

    def add_document(self, attributes: Dict) -> Document:
        cursor = self.__db.execute(
            "insert into Documents(name, downloadable, content_type) values (?, ?, ?)",
            (attributes["name"], attributes["downloadable"], attributes["content_type"])
        )
        return Document(self.__db, cursor.lastrowid, self.docs_path)

    def remove_document(self, document: Document):
        self.__db.execute("delete from Documents where ID=?", (document.doc_id,))

    @property
    def courses(self) -> List[Course]:
        return [Course(row[0], self.__db) for row in self.__db.execute("select ID from Courses")]

    def add_course(self, attributes: Dict) -> Course:
        cursor = self.__db.execute(
            "insert into Courses(long_name, short_name) values (?, ?)",
            (attributes["long_name"], attributes["short_name"])
        )
        return Course(cursor.lastrowid, self.__db)

    def remove_course(self, course: Course):
        self.__db.execute("delete from Courses where ID=?", (course.course_id,))

    @property
    def folders(self) -> List[Folder]:
        return [Folder(row[0], self.__db) for row in self.__db.execute("select ID from Folders")]

    def add_folder(self, attributes: Dict) -> Folder:
        cursor = self.__db.execute(
            "insert into Folders(name) values (?)",
            (attributes["name"],)
        )
        return Folder(cursor.lastrowid, self.__db)

    def remove_folder(self, folder: Folder):
        self.__db.execute("delete from Folders where ID=?", (folder.folder_id,))

    @property
    def authors(self) -> List[Author]:
        return [Author(row[0], self.__db) for row in self.__db.execute("select ID from Authors")]

    def add_author(self, attributes: Dict) -> Author:
        cursor = self.__db.execute(
            "insert into Authors(name) values (?)",
            (attributes["name"],)
        )
        return Author(cursor.lastrowid, self.__db)

    def remove_author(self, author: Author):
        self.__db.execute("delete from Authors where ID=?", (author.author_id,))

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __new(self, other: 'Archive') -> bool:
        return not self.path == other.path
