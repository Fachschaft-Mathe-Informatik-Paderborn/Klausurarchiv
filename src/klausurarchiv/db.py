import datetime
import os
import shutil
import sqlite3
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID

from flask import g, current_app


class Document(object):
    def __init__(self, db: sqlite3.Connection, doc_id: int):
        self.__db = db
        self.__doc_id = doc_id

    @property
    def doc_id(self) -> int:
        return self.__doc_id

    @property
    def name(self) -> str:
        cursor = self.__db.execute("select name from Documents where ID=?", (self.__doc_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name: str):
        cursor = self.__db.execute("update Documents set name=? where ID=?", (new_name, self.__doc_id))

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
        cursor = self.__db.execute("select path from Documents where ID=?", (self.__doc_id,))
        return Path(cursor.fetchone()[0])

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
        cursor = self.__db.execute("select canonical_name from Courses where ID=?", (self.course_id,))
        return cursor.fetchone()[0]

    @canonical_name.setter
    def canonical_name(self, new_name):
        self.__db.execute("update Courses set canonical_name=? where ID=?", (new_name, self.course_id))

    @property
    def aliases(self) -> List[str]:
        return [row[0] for row in
                self.__db.execute("select `alias` from `CourseAliases` where ID=?", (self.__courses_id,))]

    def add_alias(self, new_alias: str):
        self.__db.execute("insert into CourseAliases(ID, alias) values (?, ?)", (self.__courses_id, new_alias))

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
    def uuid(self) -> UUID:
        cursor = self.__db.execute("select uuid from Items where ID=?", (self.item_id,))
        return UUID(cursor.fetchone()[0])

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
        return [Document(self.__db, int(row[0])) for row in
                self.__db.execute("select ID from Documents where item=?", (self.__item_id,))]

    def add_document(self, original_path: Path) -> Document:
        target_path = self.__docs_dir / Path(f"{uuid4()}{original_path.suffix}")
        shutil.copy(original_path, target_path)

        cursor = self.__db.execute("insert into Documents(name, path, item) values (?, ?, ?)",
                                   (original_path.name, str(target_path), self.__item_id))
        return Document(self.__db, cursor.lastrowid)

    def remove_document(self, document: Document):
        self.__db.execute("delete from Documents where ID=?", (document.doc_id,))

    def get_document_with_name(self, name: str) -> Optional[Document]:
        cursor = self.__db.execute("select ID from Documents where name=?", (name,))
        document = cursor.fetchone()
        if document is not None:
            document = Document(self.__db, document[0])
        return document

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
    def folder(self) -> Optional[Folder]:
        cursor = self.__db.execute("select folderID from Items where ID=?", (self.item_id,))
        folder = cursor.fetchone()[0]
        if folder is not None:
            folder = Folder(folder, self.__db)
        return folder

    @folder.setter
    def folder(self, folder: Optional[Folder]):
        if folder is None:
            self.__db.execute("update Items set folderID=NULL where ID=?", (self.item_id,))
        else:
            self.__db.execute("update Items set folderID=? where ID=?", (folder.folder_id, self.item_id))

    def __eq__(self, other: 'Item') -> bool:
        return self.__db == other.__db and self.item_id == other.item_id

    def __ne__(self, other: 'Item') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash((self.__db, self.item_id))


class Archive(object):
    def __init__(self, path: Path):
        self.__path: Path = Path(path)
        if self.__db_path.is_file():
            self.__db: sqlite3.Connection = sqlite3.connect(self.__db_path)

    def init_archive(self):
        if self.path.exists():
            shutil.rmtree(self.path)
        os.makedirs(self.path)

        # Initialize docs directory
        os.makedirs(self.__docs_path)

        # Initialize database
        self.__db = sqlite3.connect(self.__db_path)
        with current_app.open_resource("schema.sql", mode="r") as f:
            self.__db.executescript(f.read())

        # Initialize secret
        with open(self.__secret_path, mode="wb") as file:
            file.write(os.urandom(32))
        self.__secret_path.chmod(0o400)

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
        with open(self.__secret_path, mode="rb") as file:
            return file.read()

    @property
    def __db_path(self) -> Path:
        return self.__path / Path("archive.sqlite")

    @property
    def __docs_path(self) -> Path:
        return self.__path / Path("docs")

    @property
    def __secret_path(self) -> Path:
        return self.__path / Path("SECRET")

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def items(self) -> List[Item]:
        return [Item(item_id[0], self.__db, self.docs_dir) for item_id in self.__db.execute("select ID from Items")]

    def add_item(self, name: str) -> Item:
        cursor = self.__db.execute('insert into Items(name, uuid) values (?, ?)', (name, str(uuid4())))
        return Item(int(cursor.lastrowid), self.__db, self.docs_dir)

    def remove_item(self, item: Item):
        self.__db.execute("delete from Items where Id = ?", (item.item_id,))

    @property
    def courses(self) -> List[Course]:
        return [Course(row[0], self.__db) for row in self.__db.execute("select ID from Courses")]

    def add_course(self, canonical_name: str) -> Course:
        cursor = self.__db.execute("insert into Courses(canonical_name) values (?)", (canonical_name,))
        course = Course(cursor.lastrowid, self.__db)
        return course

    def remove_course(self, course: Course):
        self.__db.execute("delete from Courses where ID=?", (course.course_id,))

    @property
    def folders(self) -> List[Folder]:
        return [Folder(row[0], self.__db) for row in self.__db.execute("select ID from Folders")]

    def add_folder(self, name: str) -> Folder:
        cursor = self.__db.execute("insert into Folders(name) values (?)", (name,))
        return Folder(cursor.lastrowid, self.__db)

    def remove_folder(self, folder: Folder):
        self.__db.execute("delete from Folders where ID=?", (folder.folder_id,))

    @property
    def authors(self) -> List[Author]:
        return [Author(row[0], self.__db) for row in self.__db.execute("select ID from Authors")]

    def add_author(self, name: str) -> Author:
        cursor = self.__db.execute("insert into Authors(name) values (?)", (name,))
        return Author(cursor.lastrowid, self.__db)

    def remove_author(self, author: Author):
        self.__db.execute("delete from Authors where ID=?", (author.author_id,))

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __new(self, other: 'Archive') -> bool:
        return not self.path == other.path
