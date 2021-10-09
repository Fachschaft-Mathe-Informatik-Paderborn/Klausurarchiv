import datetime
import importlib.resources as import_res
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict
from werkzeug.exceptions import BadRequest, NotFound
from flask import Flask, request

from flask import g, current_app, make_response, Response


class Resource(object):

    ATTRIBUTE_SCHEMA = dict()
    RESOURCE_PATH = ""

    @classmethod
    def validate_data(cls, data: Dict, may_be_partial: bool = False):
        if data is None:
            raise BadRequest("Request body may not be empty")
        if not isinstance(data, Dict):
            raise BadRequest("Request body must be an object")
        for (attribute_name, attribute_type) in cls.ATTRIBUTE_SCHEMA.items():
            if attribute_name not in data:
                if may_be_partial:
                    continue
                else:
                    raise BadRequest(f"Attribute \"{attribute_name}\" is missing")
            if not isinstance(data[attribute_name], attribute_type):
                raise BadRequest(
                    f"Attribute \"{attribute_name}\" must be of type \"{attribute_type.__name__}\""
                )

    @classmethod
    def register_resource(cls, app: Flask):
        def get_entry(entry_id: int) -> Resource:
            entry = cls.get_entry(Archive.get_singleton(), entry_id)
            if entry is None:
                raise NotFound("The requested resource does not exist")
            return entry

        def commit_and_make_response(data: Dict, status=200) -> Response:
            response = make_response(data, status)
            Archive.get_singleton().commit()
            return response

        @app.get(f"{cls.RESOURCE_PATH}", endpoint=f"GET {cls.RESOURCE_PATH}")
        def get_all():
            return make_response({
                entry.entry_id: entry.dict
                for entry in cls.get_entries(Archive.get_singleton())
            })

        @app.get(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"GET {cls.RESOURCE_PATH}/id")
        def get(entry_id: int):
            return make_response(cls.get_entry(Archive.get_singleton(), entry_id).dict)

        @app.post(f"{cls.RESOURCE_PATH}", endpoint=f"POST {cls.RESOURCE_PATH}")
        def post():
            entry = cls.new_entry(Archive.get_singleton(), request.get_json())
            return commit_and_make_response({"id": entry.entry_id}, 201)

        @app.patch(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"PATCH {cls.RESOURCE_PATH}/id")
        def patch(entry_id: int):
            get_entry(entry_id).update(request.get_json())
            return commit_and_make_response({})

        @app.delete(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"DELETE {cls.RESOURCE_PATH}/id")
        def delete(entry_id: int):
            get_entry(entry_id).delete()
            return commit_and_make_response({})

    @classmethod
    def get_entries(cls, archive: 'Archive') -> List['Resource']:
        raise NotImplementedError

    @classmethod
    def get_entry(cls, archive: 'Archive', entry_id: int) -> Optional['Resource']:
        raise NotImplementedError

    @classmethod
    def new_entry(cls, archive: 'Archive', data: Dict) -> 'Resource':
        raise NotImplementedError

    @property
    def entry_id(self) -> int:
        raise NotImplementedError

    @property
    def dict(self) -> Dict:
        raise NotImplementedError

    def update(self, data: Dict):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError


class Document(Resource):
    def __init__(self, db: sqlite3.Connection, doc_id: int, docs_path: Path):
        self.__db = db
        self.__doc_id = doc_id
        self.__docs_path = docs_path

    ATTRIBUTE_SCHEMA = {
        "filename": str,
        "downloadable": bool,
        "content_type": str
    }
    RESOURCE_PATH = "/v1/documents"
    
    @classmethod
    def validate_data(cls, data: Dict, may_be_partial: bool = False):
        super(Document, cls).validate_data(data, may_be_partial)
        allowed_content_types = [
            "application/msword", "application/pdf", "application/x-latex", "image/png", "image/jpeg", "image/gif",
            "text/plain"
        ]
        if "content_type" in data and data["content_type"] not in allowed_content_types:
            raise BadRequest("Illegal content type")

    @classmethod
    def get_entries(cls, archive: 'Archive') -> List['Document']:
        return [Document(archive.db, row[0], archive.docs_path) for row in archive.db.execute("select ID from Documents")]

    @classmethod
    def get_entry(cls, archive: 'Archive', document_id: int) -> Optional['Document']:
        cursor = archive.db.execute("select count(ID) from Documents where ID=?", (document_id,))
        if cursor.fetchone()[0] == 1:
            return Document(archive.db, document_id, archive.docs_path)
        else:
            return None

    @classmethod
    def new_entry(cls, archive: 'Archive', data: Dict) -> 'Document':
        cls.validate_data(data)
        cursor = archive.db.execute(
            "insert into Documents(filename, downloadable, content_type) values (?, ?, ?)",
            (data["filename"], data["downloadable"], data["content_type"])
        )
        return Document(archive.db, cursor.lastrowid, archive.docs_path)

    @property
    def entry_id(self) -> int:
        return self.__doc_id

    @property
    def dict(self) -> Dict:
        return {
            "filename": self.filename,
            "downloadable": self.downloadable,
            "content_type": self.content_type
        }

    def update(self, data: Dict):
        self.validate_data(data, may_be_partial=True)
        if "filename" in data:
            self.filename = data["filename"]
        if "downloadable" in data:
            self.downloadable = data["downloadable"]
        if "content_type" in data:
            self.content_type = data["content_type"]

    def delete(self):
        self.__db.execute("delete from Documents where ID=?", (self.entry_id,))

    @property
    def filename(self) -> str:
        cursor = self.__db.execute("select filename from Documents where ID=?", (self.__doc_id,))
        return cursor.fetchone()[0]

    @filename.setter
    def filename(self, new_name: str):
        self.__db.execute("update Documents set filename=? where ID=?", (new_name, self.__doc_id))

    @property
    def content_type(self) -> str:
        cursor = self.__db.execute("select content_type from Documents where ID=?", (self.__doc_id,))
        return cursor.fetchone()[0]

    @content_type.setter
    def content_type(self, new_type: str):
        self.__db.execute("update Documents set content_type=? where ID=?", (new_type, self.__doc_id))

    @property
    def downloadable(self) -> bool:
        cursor = self.__db.execute("select downloadable from Documents where ID=?", (self.entry_id,))
        return cursor.fetchone()[0] == 1

    @downloadable.setter
    def downloadable(self, downloadable: bool):
        if downloadable:
            downloadable = 1
        else:
            downloadable = 0
        self.__db.execute("update Documents set downloadable=? where ID=?", (downloadable, self.entry_id))

    @property
    def path(self) -> Path:
        return self.__docs_path / Path(str(self.__doc_id))

    def __eq__(self, other: 'Document') -> bool:
        return self.__db == other.__db and self.entry_id == other.entry_id

    def __ne__(self, other: 'Document') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash((self.__db, self.entry_id))


class Course(Resource):
    def __init__(self, course_id: int, db: sqlite3.Connection):
        self.__courses_id = course_id
        self.__db = db

    ATTRIBUTE_SCHEMA = {
        "long_name": str,
        "short_name": str
    }
    RESOURCE_PATH = "/v1/courses"

    @classmethod
    def get_entries(cls, archive: 'Archive') -> List['Course']:
        return [Course(row[0], archive.db) for row in archive.db.execute("select ID from Courses")]

    @classmethod
    def get_entry(cls, archive: 'Archive', entry_id: int) -> Optional['Course']:
        cursor = archive.db.execute("select count(ID) from Courses where ID=?", (entry_id,))
        if cursor.fetchone()[0] == 1:
            return Course(entry_id, archive.db)
        else:
            return None

    @classmethod
    def new_entry(cls, archive: 'Archive', data: Dict) -> 'Course':
        cls.validate_data(data)
        cursor = archive.db.execute(
            "insert into Courses(long_name, short_name) values (?, ?)",
            (data["long_name"], data["short_name"])
        )
        return Course(cursor.lastrowid, archive.db)

    @property
    def entry_id(self) -> int:
        return self.__courses_id

    @property
    def dict(self) -> Dict:
        return {
            "long_name": self.long_name,
            "short_name": self.short_name
        }

    def update(self, data: Dict):
        self.validate_data(data, may_be_partial=True)
        if "long_name" in data:
            self.long_name = data["long_name"]
        if "short_name" in data:
            self.short_name = data["short_name"]

    def delete(self):
        self.__db.execute("delete from Courses where ID=?", (self.entry_id,))

    @property
    def long_name(self) -> str:
        cursor = self.__db.execute("select long_name from Courses where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @long_name.setter
    def long_name(self, new_name):
        self.__db.execute("update Courses set long_name=? where ID=?", (new_name, self.entry_id))

    @property
    def short_name(self) -> str:
        cursor = self.__db.execute("select short_name from Courses where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @short_name.setter
    def short_name(self, new_name):
        self.__db.execute("update Courses set short_name=? where ID=?", (new_name, self.entry_id))

    def __eq__(self, other: 'Course') -> bool:
        return self.__db == other.__db and self.entry_id == other.entry_id

    def __ne__(self, other: 'Course') -> bool:
        return not self == other

    def __hash__(self):
        return hash((self.entry_id, self.__db))


class Folder(Resource):
    def __init__(self, folder_id: int, db: sqlite3.Connection):
        self.__folder_id = folder_id
        self.__db = db

    ATTRIBUTE_SCHEMA = {
        "name": str
    }
    RESOURCE_PATH = "/v1/folders"

    @classmethod
    def get_entries(cls, archive: 'Archive') -> List['Folder']:
        return [Folder(row[0], archive.db) for row in archive.db.execute("select ID from Folders")]

    @classmethod
    def get_entry(cls, archive: 'Archive', folder_id: int) -> Optional['Folder']:
        cursor = archive.db.execute("select count(ID) from Folders where ID=?", (folder_id,))
        if cursor.fetchone()[0] == 1:
            return Folder(folder_id, archive.db)
        else:
            return None

    @classmethod
    def new_entry(cls, archive: 'Archive', data: Dict) -> 'Folder':
        cls.validate_data(data)
        cursor = archive.db.execute(
            "insert into Folders(name) values (?)",
            (data["name"],)
        )
        return Folder(cursor.lastrowid, archive.db)

    @property
    def entry_id(self) -> int:
        return self.__folder_id

    @property
    def dict(self) -> Dict:
        return {
            "name": self.name
        }

    def update(self, data: Dict):
        self.validate_data(data, may_be_partial=True)
        if "name" in data:
            self.name = data["name"]

    def delete(self):
        self.__db.execute("delete from Folders where ID=?", (self.entry_id,))

    @property
    def name(self) -> str:
        cursor = self.__db.execute("select name from Folders where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name):
        self.__db.execute("update Folders set name=? where ID=?", (new_name, self.entry_id))

    def __eq__(self, other: 'Folder'):
        is_equal = self.__db == other.__db and self.entry_id == other.entry_id
        return is_equal

    def __ne__(self, other: 'Folder'):
        return not self == other

    def __hash__(self):
        return hash((self.entry_id, self.__db))


class Author(Resource):
    def __init__(self, author_id: int, db: sqlite3.Connection):
        self.__author_id = author_id
        self.__db = db

    @property
    def entry_id(self) -> int:
        return self.__author_id

    @property
    def name(self) -> str:
        cursor = self.__db.execute("select name from Authors where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name):
        self.__db.execute("update Authors set name=? where ID=?", (new_name, self.entry_id))

    def __eq__(self, other: 'Author'):
        return self.__db == other.__db and self.entry_id == other.entry_id

    def __ne__(self, other: 'Author'):
        return not self == other

    def __hash__(self):
        return hash((self.entry_id, self.__db))


class Item(Resource):
    def __init__(self, item_id: int, db: sqlite3.Connection, docs_dir: Path):
        self.__item_id = item_id
        self.__db = db
        self.__docs_dir = docs_dir

    @property
    def entry_id(self):
        return self.__item_id

    @property
    def name(self) -> str:
        cursor = self.__db.execute("select name from Items where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name: str):
        self.__db.execute("update Items set name=? where ID=?", (new_name, self.entry_id))

    @property
    def date(self) -> Optional[datetime.date]:
        cursor = self.__db.execute("select date from Items where ID=?", (self.entry_id,))
        date = cursor.fetchone()[0]
        if date is not None:
            date = datetime.date.fromisoformat(date)
        return date

    @date.setter
    def date(self, new_date: Optional[datetime.date]):
        self.__db.execute("update Items set date=? where ID=?", (new_date.isoformat(), self.entry_id))

    @property
    def documents(self) -> List[Document]:
        return [Document(self.__db, int(row[0]), self.__docs_dir) for row in
                self.__db.execute("select DocumentID from ItemDocumentMap where ItemID=?", (self.__item_id,))]

    def add_document(self, document: Document):
        self.__db.execute("insert into ItemDocumentMap(ItemID, DocumentID) values (?, ?)",
                          (self.entry_id, document.entry_id))

    def remove_document(self, document: Document):
        self.__db.execute("delete from ItemDocumentMap where ItemID=? and DocumentID=?",
                          (self.entry_id, document.entry_id))

    @property
    def applicable_courses(self) -> List[Course]:
        return [Course(row[0], self.__db) for row in
                self.__db.execute("select CourseID from ItemCourseMap where ItemID=?", (self.entry_id,))]

    def add_to_course(self, course: Course):
        self.__db.execute("insert into ItemCourseMap(ItemID, CourseID) values (?, ?)", (self.entry_id, course.entry_id))

    def remove_from_course(self, course: Course):
        self.__db.execute("delete from ItemCourseMap where ItemID=? and CourseID=?", (self.entry_id, course.entry_id))

    @property
    def authors(self) -> List[Author]:
        return [Author(row[0], self.__db) for row in
                self.__db.execute("select AuthorID from ItemAuthorMap where ItemID=?", (self.entry_id,))]

    def add_author(self, author: Author):
        self.__db.execute("insert into ItemAuthorMap(ItemID, AuthorID) values (?, ?)", (self.entry_id, author.entry_id))

    def remove_author(self, author: Author):
        self.__db.execute("delete from ItemAuthorMap where ItemID=? and AuthorID=?", (self.entry_id, author.entry_id))

    @property
    def folders(self) -> List[Folder]:
        return [Folder(row[0], self.__db) for row in
                self.__db.execute("select FolderID from ItemFolderMap where ItemID=?", (self.entry_id,))]

    def add_folder(self, folder: Folder):
        self.__db.execute("insert into ItemFolderMap(ItemID, FolderID) values (?, ?)", (self.entry_id, folder.entry_id))

    def remove_folder(self, folder: Folder):
        self.__db.execute("delete from ItemFolderMap where ItemID=? and FolderID=?", (self.entry_id, folder.entry_id))

    @property
    def visible(self) -> bool:
        cursor = self.__db.execute("select visible from Items where ID=?", (self.entry_id,))
        return cursor.fetchone()[0] == 1

    @visible.setter
    def visible(self, new_visible: bool):
        self.__db.execute("update Items set visible=? where ID=?", (new_visible, self.entry_id))

    def __eq__(self, other: 'Item') -> bool:
        return self.__db == other.__db and self.entry_id == other.entry_id

    def __ne__(self, other: 'Item') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash((self.__db, self.entry_id))


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
        self.db: sqlite3.Connection = sqlite3.connect(self.db_path)
        if not database_exists:
            import klausurarchiv
            with import_res.open_text(klausurarchiv, "schema.sql") as f:
                self.db.executescript(f.read())

        # Check secret
        if not self.secret_path.exists():
            with open(self.secret_path, mode="wb") as file:
                file.write(os.urandom(32))
            self.secret_path.chmod(0o400)

    def commit(self):
        self.db.commit()

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
        return [Item(item_id[0], self.db, self.docs_path) for item_id in self.db.execute("select ID from Items")]

    def add_item(self,
                 name: str = "",
                 date: Optional[datetime.date] = None,
                 documents: List[int] = None,
                 authors: List[int] = None,
                 courses: List[int] = None,
                 folders: List[int] = None,
                 visible: bool = False) -> Item:
        cursor = self.db.execute(
            "insert into Items(name, date, visible) values (?, ?, ?)",
            (name, date, visible)
        )
        item = Item(cursor.lastrowid, self.db, self.docs_path)
        if documents is not None:
            self.db.executemany(
                "insert into ItemDocumentMap values (?, ?)",
                ((item.entry_id, doc_id) for doc_id in documents)
            )
        if authors is not None:
            self.db.executemany(
                "insert into ItemAuthorMap values (?, ?)",
                ((item.entry_id, author_id) for author_id in authors)
            )
        if courses is not None:
            self.db.executemany(
                "insert into ItemCourseMap values (?, ?)",
                ((item.entry_id, course_id) for course_id in courses)
            )
        if folders is not None:
            self.db.executemany(
                "insert into ItemFolderMap values (?, ?)",
                ((item.entry_id, folder_id) for folder_id in folders)
            )
        return item

    def remove_item(self, item: Item):
        self.db.execute("delete from Items where Id = ?", (item.entry_id,))

    def get_item(self, item_id: int) -> Optional[Item]:
        cursor = self.db.execute("select count(ID) from Items where ID=?", (item_id,))
        if cursor.fetchone()[0] == 1:
            return Item(item_id, self.db, self.docs_path)
        else:
            return None

    @property
    def authors(self) -> List[Author]:
        return [Author(row[0], self.db) for row in self.db.execute("select ID from Authors")]

    def add_author(self, name: str = "") -> Author:
        cursor = self.db.execute(
            "insert into Authors(name) values (?)",
            (name,)
        )
        return Author(cursor.lastrowid, self.db)

    def remove_author(self, author: Author):
        self.db.execute("delete from Authors where ID=?", (author.entry_id,))

    def get_author(self, author_id: int) -> Optional[Author]:
        cursor = self.db.execute("select count(ID) from Authors where ID=?", (author_id,))
        if cursor.fetchone()[0] == 1:
            return Author(author_id, self.db)
        else:
            return None

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __ne__(self, other: 'Archive') -> bool:
        return not self.path == other.path
