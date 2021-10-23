import datetime
import importlib.resources as import_res
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict

from flask import Flask, request, send_file
from flask import g, make_response, Response
from flask_login import login_required
from werkzeug.exceptions import BadRequest, NotFound, RequestEntityTooLarge, Unauthorized
from werkzeug.utils import secure_filename


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

    def __eq__(self, other: 'Archive') -> bool:
        return self.path == other.path

    def __ne__(self, other: 'Archive') -> bool:
        return not self.path == other.path


def validate_schema(schema: Dict, data: Dict, may_be_partial: bool = False):
    if data is None:
        raise BadRequest("Request body may not be empty")
    if not isinstance(data, Dict):
        raise BadRequest("Request body must be an object")
    for (attribute_name, attribute_type) in schema.items():
        if attribute_name not in data:
            if may_be_partial:
                continue
            else:
                raise BadRequest(f"Attribute \"{attribute_name}\" is missing")
        if not isinstance(data[attribute_name], attribute_type):
            raise BadRequest(
                f"Attribute \"{attribute_name}\" must be of type \"{attribute_type.__name__}\""
            )


class Resource(object):
    ATTRIBUTE_SCHEMA = dict()
    TABLE_NAME = ""
    RESOURCE_PATH = ""

    def __init__(self, entry_id: int):
        self.__entry_id: int = int(entry_id)

    @property
    def entry_id(self) -> int:
        return self.__entry_id

    @classmethod
    def validate_data(cls, data: Dict, may_be_partial: bool = False):
        validate_schema(cls.ATTRIBUTE_SCHEMA, data, may_be_partial)

    @classmethod
    def register_resource(cls, app: Flask):
        def get_entry(entry_id: int) -> Resource:
            entry = cls.get_entry(entry_id)
            if entry is None:
                raise NotFound("The requested resource does not exist")
            return entry

        def commit_and_make_response(data: Dict, status=200) -> Response:
            response = make_response(data, status)
            g.archive.commit()
            return response

        @app.get(f"{cls.RESOURCE_PATH}", endpoint=f"GET {cls.RESOURCE_PATH}")
        def get_all():
            return make_response({
                entry.entry_id: entry.dict
                for entry in cls.get_entries()
            })

        @app.get(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"GET {cls.RESOURCE_PATH}/id")
        def get(entry_id: int):
            return make_response(cls.get_entry(entry_id).dict)

        @app.post(f"{cls.RESOURCE_PATH}", endpoint=f"POST {cls.RESOURCE_PATH}")
        @login_required
        def post():
            data = request.get_json()
            cls.validate_data(data)
            entry = cls.new_entry(data)
            return commit_and_make_response({"id": entry.entry_id}, 201)

        @app.patch(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"PATCH {cls.RESOURCE_PATH}/id")
        @login_required
        def patch(entry_id: int):
            data = request.get_json()
            cls.validate_data(data, may_be_partial=True)
            get_entry(entry_id).update(data)
            return commit_and_make_response({})

        @app.delete(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"DELETE {cls.RESOURCE_PATH}/id")
        @login_required
        def delete(entry_id: int):
            get_entry(entry_id).delete()
            return commit_and_make_response({})

    @classmethod
    def get_entries(cls) -> List['Resource']:
        return [cls(entry_id[0]) for entry_id in g.archive.db.execute(f"select ID from {cls.TABLE_NAME}")]

    @classmethod
    def get_entry(cls, entry_id: int) -> Optional['Resource']:
        cursor = g.archive.db.execute(f"select count(ID) from {cls.TABLE_NAME} where ID = ?", (entry_id,))
        if cursor.fetchone()[0] == 1:
            return cls(entry_id)
        else:
            return None

    @classmethod
    def new_entry(cls, data: Dict) -> 'Resource':
        raise NotImplementedError

    @property
    def dict(self) -> Dict:
        raise NotImplementedError

    def update(self, data: Dict):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError


class Document(Resource):
    ATTRIBUTE_SCHEMA = {
        "filename": str,
        "downloadable": bool,
        "content_type": str
    }
    TABLE_NAME = "Documents"
    RESOURCE_PATH = "/v1/documents"

    @classmethod
    def validate_data(cls, data: Dict, may_be_partial: bool = False):
        super(Document, cls).validate_data(data, may_be_partial)
        allowed_content_types = [
            "application/msword", "application/pdf", "application/x-latex", "image/png", "image/jpeg", "image/gif",
            "text/plain"
        ]
        if "filename" in data and data["filename"] != secure_filename(data["filename"]):
            raise BadRequest("Insecure filename")
        if "content_type" in data and data["content_type"] not in allowed_content_types:
            raise BadRequest("Illegal content type")

    @classmethod
    def register_resource(cls, app: Flask):
        super(Document, cls).register_resource(app)

        def get_requested_document() -> Document:
            try:
                doc_id = int(request.args["id"])
            except KeyError:
                raise BadRequest("Parameter id is required")
            except ValueError:
                raise BadRequest("Parameter id must be an integer")
            return Document.get_entry(doc_id)

        @app.post("/v1/upload")
        def upload_document():
            doc = get_requested_document()

            if request.content_type != doc.content_type:
                raise BadRequest("Illegal document type")
            if request.content_length > app.config["MAX_CONTENT_LENGTH"]:
                raise RequestEntityTooLarge()
            with open(doc.path, mode="wb") as file:
                file.write(request.get_data())

            return make_response({})

        @app.get("/v1/download")
        def download_document():
            doc = get_requested_document()

            # Check if the document belongs to an invisible item or is not downloadable.
            # If so, it may not be downloaded.
            cursor = g.archive.db.execute("""
                select count(Items.ID)
                from Items inner join (select * from ItemDocumentMap where DocumentID = ?) IDM on Items.ID = IDM.ItemID
                where Items.visible=0
            """, (doc.entry_id,))
            if cursor.fetchone()[0] != 0 or not doc.downloadable:
                raise Unauthorized("You are not allowed to download this document")

            return send_file(doc.path, mimetype=doc.content_type, as_attachment=True, download_name=doc.filename)

    @classmethod
    def new_entry(cls, data: Dict) -> 'Document':
        cls.validate_data(data)
        cursor = g.archive.db.execute(
            "insert into Documents(filename, downloadable, content_type) values (?, ?, ?)",
            (data["filename"], data["downloadable"], data["content_type"])
        )
        return Document(cursor.lastrowid)

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
        g.archive.db.execute("delete from Documents where ID=?", (self.entry_id,))

    @property
    def filename(self) -> str:
        cursor = g.archive.db.execute("select filename from Documents where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @filename.setter
    def filename(self, new_name: str):
        g.archive.db.execute("update Documents set filename=? where ID=?", (new_name, self.entry_id))

    @property
    def content_type(self) -> str:
        cursor = g.archive.db.execute("select content_type from Documents where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @content_type.setter
    def content_type(self, new_type: str):
        g.archive.db.execute("update Documents set content_type=? where ID=?", (new_type, self.entry_id))

    @property
    def downloadable(self) -> bool:
        cursor = g.archive.db.execute("select downloadable from Documents where ID=?", (self.entry_id,))
        return cursor.fetchone()[0] == 1

    @downloadable.setter
    def downloadable(self, downloadable: bool):
        downloadable = 1 if downloadable else 0
        g.archive.db.execute("update Documents set downloadable=? where ID=?", (downloadable, self.entry_id))

    @property
    def path(self) -> Path:
        return g.archive.docs_path / Path(str(self.entry_id))

    def __eq__(self, other: 'Document') -> bool:
        return self.entry_id == other.entry_id

    def __ne__(self, other: 'Document') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash(self.entry_id)


class Course(Resource):
    ATTRIBUTE_SCHEMA = {
        "long_name": str,
        "short_name": str
    }
    TABLE_NAME = "Courses"
    RESOURCE_PATH = "/v1/courses"

    @classmethod
    def new_entry(cls, data: Dict) -> 'Course':
        cls.validate_data(data)
        cursor = g.archive.db.execute(
            "insert into Courses(long_name, short_name) values (?, ?)",
            (data["long_name"], data["short_name"])
        )
        return Course(cursor.lastrowid)

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
        g.archive.db.execute("delete from Courses where ID=?", (self.entry_id,))

    @property
    def long_name(self) -> str:
        cursor = g.archive.db.execute("select long_name from Courses where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @long_name.setter
    def long_name(self, new_name):
        g.archive.db.execute("update Courses set long_name=? where ID=?", (new_name, self.entry_id))

    @property
    def short_name(self) -> str:
        cursor = g.archive.db.execute("select short_name from Courses where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @short_name.setter
    def short_name(self, new_name):
        g.archive.db.execute("update Courses set short_name=? where ID=?", (new_name, self.entry_id))

    def __eq__(self, other: 'Course') -> bool:
        return self.entry_id == other.entry_id

    def __ne__(self, other: 'Course') -> bool:
        return not self == other

    def __hash__(self):
        return hash(self.entry_id)


class Folder(Resource):
    ATTRIBUTE_SCHEMA = {
        "name": str
    }
    TABLE_NAME = "Folders"
    RESOURCE_PATH = "/v1/folders"

    @classmethod
    def new_entry(cls, data: Dict) -> 'Folder':
        cls.validate_data(data)
        cursor = g.archive.db.execute(
            "insert into Folders(name) values (?)",
            (data["name"],)
        )
        return Folder(cursor.lastrowid)

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
        g.archive.db.execute("delete from Folders where ID=?", (self.entry_id,))

    @property
    def name(self) -> str:
        cursor = g.archive.db.execute("select name from Folders where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name):
        g.archive.db.execute("update Folders set name=? where ID=?", (new_name, self.entry_id))

    def __eq__(self, other: 'Folder'):
        is_equal = self.entry_id == other.entry_id
        return is_equal

    def __ne__(self, other: 'Folder'):
        return not self == other

    def __hash__(self):
        return hash(self.entry_id)


class Author(Resource):
    ATTRIBUTE_SCHEMA = {
        "name": str
    }
    TABLE_NAME = "Authors"
    RESOURCE_PATH = "/v1/authors"

    @classmethod
    def new_entry(cls, data: Dict) -> 'Author':
        cursor = g.archive.db.execute("insert into Authors(name) values (?)", (data["name"],))
        return Author(cursor.lastrowid)

    @property
    def dict(self) -> Dict:
        return {
            "name": self.name
        }

    def update(self, data: Dict):
        if "name" in data:
            self.name = data["name"]

    def delete(self):
        g.archive.db.execute("delete from Authors where ID=?", (self.entry_id,))

    @property
    def name(self) -> str:
        cursor = g.archive.db.execute("select name from Authors where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name):
        g.archive.db.execute("update Authors set name=? where ID=?", (new_name, self.entry_id))

    def __eq__(self, other: 'Author'):
        return self.entry_id == other.entry_id

    def __ne__(self, other: 'Author'):
        return not self == other

    def __hash__(self):
        return hash(self.entry_id)


class Item(Resource):
    ATTRIBUTE_SCHEMA = {
        "name": str,
        # date is not included as it may be None and the normal check can't deal with that.
        "documents": List,
        "authors": List,
        "courses": List,
        "folders": List,
        "visible": bool,
    }
    TABLE_NAME = "Items"
    RESOURCE_PATH = "/v1/items"

    @classmethod
    def validate_data(cls, data: Dict, may_be_partial: bool = False):
        super(Item, cls).validate_data(data, may_be_partial)

        if "date" in data:
            if data["date"] is not None:
                if not isinstance(data["date"], str):
                    raise BadRequest("Attribute \"date\" must be of type \"str\"")

                try:
                    datetime.date.fromisoformat(data["date"])
                except ValueError:
                    raise BadRequest(f"date must be an ISO-formatted date")
        elif not may_be_partial:
            raise BadRequest("Attribute \"date\" is missing")

        def validate_attribute(table_name, attribute_name):
            if may_be_partial and attribute_name not in data:
                return

            if any(not isinstance(entry_id, int) for entry_id in data[attribute_name]):
                raise BadRequest(f"{attribute_name} must contain integer IDs")

            placeholders = ", ".join("?" * len(data[attribute_name]))
            query = f"select count(ID) from {table_name} where ID in ({placeholders})"
            cursor = g.archive.db.execute(query, data[attribute_name])
            if cursor.fetchone()[0] != len(data[attribute_name]):
                raise BadRequest(f"{attribute_name} contains unknown IDs")

        validate_attribute("Documents", "documents")
        validate_attribute("Authors", "authors")
        validate_attribute("Courses", "courses")
        validate_attribute("Folders", "folders")

    @classmethod
    def new_entry(cls, data: Dict) -> 'Item':
        cursor = g.archive.db.execute("insert into Items(name, date, visible) values (?, ?, ?)",
                                      (data["name"], data["date"], data["visible"]))
        item = Item(cursor.lastrowid)
        item.documents = [Document(doc_id) for doc_id in data["documents"]]
        item.authors = [Author(author_id) for author_id in data["authors"]]
        item.courses = [Course(course_id) for course_id in data["courses"]]
        item.folders = [Folder(folder_id) for folder_id in data["folders"]]
        return item

    @property
    def dict(self):
        return {
            "name": self.name,
            "date": self.date,
            "documents": [document.entry_id for document in self.documents],
            "authors": [author.entry_id for author in self.authors],
            "courses": [course.entry_id for course in self.courses],
            "folders": [folder.entry_id for folder in self.folders],
            "visible": self.visible
        }

    def update(self, data: Dict):
        if "name" in data:
            self.name = data["name"]
        if "date" in data:
            self.date = data["date"]
        if "documents" in data:
            self.documents = [Document(entry_id) for entry_id in data["documents"]]
        if "authors" in data:
            self.authors = [Author(entry_id) for entry_id in data["authors"]]
        if "courses" in data:
            self.courses = [Course(entry_id) for entry_id in data["courses"]]
        if "folders" in data:
            self.folders = [Folder(entry_id) for entry_id in data["folders"]]
        if "visible" in data:
            self.visible = data["visible"]

    def delete(self):
        g.archive.db.execute("delete from Items where ID=?", (self.entry_id,))

    @property
    def name(self) -> str:
        cursor = g.archive.db.execute("select name from Items where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @name.setter
    def name(self, new_name: str):
        g.archive.db.execute("update Items set name=? where ID=?", (new_name, self.entry_id))

    @property
    def date(self) -> Optional[str]:
        cursor = g.archive.db.execute("select date from Items where ID=?", (self.entry_id,))
        return cursor.fetchone()[0]

    @date.setter
    def date(self, new_date: Optional[str]):
        g.archive.db.execute("update Items set date=? where ID=?", (new_date, self.entry_id))

    @property
    def documents(self) -> List[Document]:
        return [Document(int(row[0])) for row in
                g.archive.db.execute("select DocumentID from ItemDocumentMap where ItemID=?", (self.entry_id,))]

    @documents.setter
    def documents(self, new_documents: List[Document]):
        g.archive.db.execute("delete from ItemDocumentMap where ItemID=?", (self.entry_id,))
        g.archive.db.executemany(
            "insert into ItemDocumentMap(ItemID, DocumentID) values (?, ?)",
            ((self.entry_id, document.entry_id) for document in new_documents)
        )

    @property
    def courses(self) -> List[Course]:
        return [Course(row[0]) for row in
                g.archive.db.execute("select CourseID from ItemCourseMap where ItemID=?", (self.entry_id,))]

    @courses.setter
    def courses(self, new_courses: List[Course]):
        g.archive.db.execute("delete from ItemCourseMap where ItemID=?", (self.entry_id,))
        g.archive.db.executemany(
            "insert into ItemCourseMap(ItemID, CourseID) values (?, ?)",
            ((self.entry_id, course.entry_id) for course in new_courses)
        )

    @property
    def authors(self) -> List[Author]:
        return [Author(row[0]) for row in
                g.archive.db.execute("select AuthorID from ItemAuthorMap where ItemID=?", (self.entry_id,))]

    @authors.setter
    def authors(self, new_authors: List[Author]):
        g.archive.db.execute("delete from ItemAuthorMap where ItemID=?", (self.entry_id,))
        g.archive.db.executemany(
            "insert into ItemAuthorMap(ItemID, AuthorID) values (?, ?)",
            ((self.entry_id, author.entry_id) for author in new_authors)
        )

    @property
    def folders(self) -> List[Folder]:
        return [Folder(row[0]) for row in
                g.archive.db.execute("select FolderID from ItemFolderMap where ItemID=?", (self.entry_id,))]

    @folders.setter
    def folders(self, new_folders: List[Folder]):
        g.archive.db.execute("delete from ItemFolderMap where ItemID=?", (self.entry_id,))
        g.archive.db.executemany(
            "insert into ItemFolderMap(ItemID, FolderID) values (?, ?)",
            ((self.entry_id, folder.entry_id) for folder in new_folders)
        )

    @property
    def visible(self) -> bool:
        cursor = g.archive.db.execute("select visible from Items where ID=?", (self.entry_id,))
        return cursor.fetchone()[0] == 1

    @visible.setter
    def visible(self, new_visible: bool):
        new_visible = 1 if new_visible else 0
        g.archive.db.execute("update Items set visible=? where ID=?", (new_visible, self.entry_id))

    def __eq__(self, other: 'Item') -> bool:
        return self.entry_id == other.entry_id

    def __ne__(self, other: 'Item') -> bool:
        return not self == other

    def __hash__(self) -> int:
        return hash(self.entry_id)