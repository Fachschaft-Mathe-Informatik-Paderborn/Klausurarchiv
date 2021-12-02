"""
db.py
========================
Contains the logic for all API endpoints that access the underlying database.
"""
import datetime
import importlib.resources as import_res
import os
import sqlite3
from itertools import groupby
from pathlib import Path
from typing import List, Optional, Dict, TypeVar

from flask import Flask, request, send_file
from flask import g, make_response, Response
from flask_login import login_required, current_user
from flask_caching import Cache
from werkzeug.exceptions import BadRequest, NotFound, RequestEntityTooLarge, Unauthorized
from werkzeug.utils import secure_filename


class Archive(object):
    """
    The central object of the archive, which manages the database containing all the available resources.
    """
    def __init__(self, path: Path):
        """
        Initializes the archive from a given path.

        If path or subfolders for docs, database or the secret key do not yet exist, they will be created accordingly.
        Secret key will be created as read-only, only available to the owner.

        Parameters
        ----------
        path: Path
            path to the location where all data will be saved
        """
        self.__path: Path = Path(path)
        if not self.__path.exists():
            os.makedirs(path)

        # Check Docs Dir
        if not self.docs_path.exists():
            os.makedirs(self.docs_path)

        # Check database
        database_exists = self.db_path.exists()
        self.db: sqlite3.Connection = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
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
        """Commits any changes to the database."""
        self.db.commit()

    @property
    def secret_key(self) -> bytes:
        """
        The secret key.

        :getter: Reads the secret key from the corresponding file. This will read the file each time instead of permanently storing the secret key.
        :type: bytes
        """
        with open(self.secret_path, mode="rb") as file:
            return file.read()

    @property
    def db_path(self) -> Path:
        """The path to where the database is stored."""
        return self.__path / Path("archive.sqlite")

    @property
    def docs_path(self) -> Path:
        """The path to where all documents are stored."""
        return self.__path / Path("docs")

    @property
    def secret_path(self) -> Path:
        """The path to where the secret key is stored."""
        return self.__path / Path("SECRET")

    @property
    def path(self) -> Path:
        """The path to where all of the archives files are stored."""
        return self.__path

    def __eq__(self, other: 'Archive') -> bool:
        """Checks whether the path of two archives matches."""
        return self.path == other.path

    def __ne__(self, other: 'Archive') -> bool:
        """Checks whether the path of two archives does not match."""
        return not self.path == other.path


def validate_schema(schema: Dict, data: Dict, may_be_partial: bool = False):
    """
    Checks whether a given dictionary of data contains all the required keys with corresponding values of the right type.

    Given some data in form of a dictionary, this function determines whether a given list of required keys corresponding to a specific type is contained. There may be cases where a only a subset of the schema is required and missing keys are allowed, but any combinations contradicting the given schema will result in an exception.

    Parameters
    ----------
        schema: Dict
            contains a mapping of attribute name to required type
        data: Dict
            data to be checked in form of a simple dictionary
        may_be_partial: bool
            determines whether part of the schema may be missing from the given data

    Returns
    -------
        bool
            True if data conforms to the schema, False otherwise.

    Raises
    ------
    BadRequest
        if data is empty, not a dictionary, misses a required attribute or has an attribute of a different type than required
    """
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
            try:
                typename = attribute_type.__name__
            except AttributeError:
                typename = attribute_type._name
            raise BadRequest(
                f"Attribute \"{attribute_name}\" must be of type \"{typename}\""
            )


R = TypeVar('R', bound='Resource')


class Resource(object):
    """
    Any kind of resource associated with a list of attributes, which is stored in the database and accessible via the public API.

    Attributes
    ----------
    entry_id: int
        numerical id corresponding to one unique resource
    """
    ATTRIBUTE_SCHEMA = dict()
    PRIVATE_TABLE_NAME = ""
    PUBLIC_TABLE_NAME = ""
    RESOURCE_PATH = ""

    @classmethod
    def validate_data(cls, data: Dict, may_be_partial: bool = False):
        validate_schema(cls.ATTRIBUTE_SCHEMA, data, may_be_partial)

    @classmethod
    def register_resource(cls, app: Flask):
        cache = Cache(app)

        def commit_and_make_response(data: Dict, status=200) -> Response:
            response = make_response(data, status)
            g.archive.commit()
            return response

        @app.get(f"{cls.RESOURCE_PATH}", endpoint=f"GET {cls.RESOURCE_PATH}", strict_slashes=False)
        @cache.cached(unless=lambda: current_user.is_authenticated)
        def get_all():
            return make_response(cls.get_all())

        @app.get(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"GET {cls.RESOURCE_PATH}/id")
        @cache.memoize(unless=lambda: current_user.is_authenticated)
        def get(entry_id: int):
            return make_response(cls.get(entry_id))

        @app.post(f"{cls.RESOURCE_PATH}", endpoint=f"POST {cls.RESOURCE_PATH}", strict_slashes=False)
        @login_required
        def post():
            data = request.get_json()
            cls.validate_data(data)
            entry_id = cls.post(data)
            return commit_and_make_response({"id": entry_id}, 201)

        @app.patch(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"PATCH {cls.RESOURCE_PATH}/id")
        @login_required
        def patch(entry_id: int):
            data = request.get_json()
            cls.validate_data(data, may_be_partial=True)
            cls.patch(entry_id, data)
            return commit_and_make_response({})

        @app.delete(f"{cls.RESOURCE_PATH}/<int:entry_id>", endpoint=f"DELETE {cls.RESOURCE_PATH}/id")
        @login_required
        def delete(entry_id: int):
            cls.delete(entry_id)
            return commit_and_make_response({})

    @classmethod
    def get(cls, entry_id: int) -> Dict:
        if current_user.is_authenticated:
            table_name = cls.PRIVATE_TABLE_NAME
        else:
            table_name = cls.PUBLIC_TABLE_NAME
        row = g.archive.db.execute(f"select * from {table_name} where ID=?", (entry_id,)).fetchone()
        if row is None:
            raise NotFound
        entry = dict(row)
        del entry["ID"]
        return entry

    @classmethod
    def get_all(cls) -> Dict[int, Dict]:
        if current_user.is_authenticated:
            table_name = cls.PRIVATE_TABLE_NAME
        else:
            table_name = cls.PUBLIC_TABLE_NAME

        def delete_id(row: Dict):
            del row["ID"]
            return row

        return {
            row["ID"]: delete_id(dict(row))
            for row in g.archive.db.execute(f"select * from {table_name}")
        }

    @classmethod
    def post(cls, data: Dict) -> int:
        raise NotImplementedError

    @classmethod
    def patch(cls, entry_id: int, data: Dict):
        raise NotImplementedError

    @classmethod
    def delete(cls, entry_id: int):
        g.archive.db.execute(f"delete from {cls.PRIVATE_TABLE_NAME} where ID=?", (entry_id,))


class Document(Resource):
    """
    A file of specific media type that is stored on disk.
    """
    ATTRIBUTE_SCHEMA = {
        "filename": str,
        "downloadable": bool,
        "content_type": str
    }
    PRIVATE_TABLE_NAME = "Documents"
    PUBLIC_TABLE_NAME = "VisibleDocuments"
    RESOURCE_PATH = "/v1/documents"

    @classmethod
    def path(cls, entry_id) -> Path:
        return g.archive.docs_path / Path(str(entry_id))

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

        @app.post("/v1/upload")
        @login_required
        def upload_document():
            entry_id = int(request.args["id"])
            doc = cls.get(entry_id)

            if request.content_type != doc["content_type"]:
                raise BadRequest("Illegal document type")
            if request.content_length > app.config["MAX_CONTENT_LENGTH"]:
                raise RequestEntityTooLarge()
            with open(cls.path(entry_id), mode="wb") as file:
                file.write(request.get_data())

            return make_response({})

        @app.get("/v1/download")
        def download_document():
            entry_id = int(request.args["id"])
            doc = cls.get(entry_id)

            # Check if the document belongs to an invisible item or is not downloadable.
            # If so, it may not be downloaded.
            if not current_user.is_authenticated and not doc["downloadable"]:
                raise Unauthorized("You are not allowed to download this document")

            return send_file(cls.path(entry_id), mimetype=doc["content_type"], as_attachment=True,
                             download_name=doc["filename"])

    @classmethod
    def post(cls, data: Dict) -> int:
        cursor = g.archive.db.execute(
            "insert into Documents(filename, downloadable, content_type) values (?, ?, ?)",
            (data["filename"], data["downloadable"], data["content_type"])
        )
        return cursor.lastrowid

    @classmethod
    def patch(cls, entry_id: int, new_data: Dict):
        data = cls.get(entry_id)
        data.update(new_data)
        g.archive.db.execute(
            "update Documents set filename=?, downloadable=?, content_type=? where ID=?",
            (data["filename"], data["downloadable"], data["content_type"], entry_id)
        )

    @classmethod
    def delete(cls, entry_id: int):
        super(Document, cls).delete(entry_id)
        cls.path(entry_id).unlink(missing_ok=True)


class Course(Resource):
    """
    A university course associated with a number of documents.
    """
    ATTRIBUTE_SCHEMA = {
        "long_name": str,
        "short_name": str
    }
    PRIVATE_TABLE_NAME = "Courses"
    PUBLIC_TABLE_NAME = "Courses"
    RESOURCE_PATH = "/v1/courses"

    @classmethod
    def post(cls, data: Dict) -> int:
        cursor = g.archive.db.execute(
            "insert into Courses(long_name, short_name) values (?, ?)",
            (data["long_name"], data["short_name"])
        )
        return cursor.lastrowid

    @classmethod
    def patch(cls, entry_id: int, new_data: Dict):
        data = cls.get(entry_id)
        data.update(new_data)
        g.archive.db.execute(
            "update Courses set long_name=?, short_name=? where ID=?",
            (data["long_name"], data["short_name"], entry_id)
        )


class Folder(Resource):
    """Representation of the physical folder an item may be found in."""
    ATTRIBUTE_SCHEMA = {
        "name": str
    }
    PRIVATE_TABLE_NAME = "Folders"
    PUBLIC_TABLE_NAME = "Folders"
    RESOURCE_PATH = "/v1/folders"

    @classmethod
    def post(cls, data: Dict) -> 'Folder':
        cursor = g.archive.db.execute(
            "insert into Folders(name) values (?)",
            (data["name"],)
        )
        return cursor.lastrowid

    @classmethod
    def patch(cls, entry_id: int, new_data: Dict):
        data = cls.get(entry_id)
        data.update(new_data)
        g.archive.db.execute("update Folders set name=? where ID=?", (data["name"], entry_id))


class Author(Resource):
    """Author responsible for a document.

    Attributes
    ----------
    entry_id: int
        id of the author in the database
    """
    ATTRIBUTE_SCHEMA = {
        "name": str
    }
    PRIVATE_TABLE_NAME = "Authors"
    PUBLIC_TABLE_NAME = "Authors"
    RESOURCE_PATH = "/v1/authors"

    @classmethod
    def post(cls, data: Dict) -> int:
        cursor = g.archive.db.execute("insert into Authors(name) values (?)", (data["name"],))
        return cursor.lastrowid

    @classmethod
    def patch(cls, entry_id: int, new_data: Dict):
        data = cls.get(entry_id)
        data.update(**new_data)
        g.archive.db.execute("update Authors set name=? where ID=?", (data["name"], entry_id))


class Item(Resource):
    """
    A concrete lecture or exam consisting of multiple documents, that can be used to prepare for a number of courses.

    Attributes
    ----------
    entry_id: int
        id of the item in the database.
    """
    ATTRIBUTE_SCHEMA = {
        "name": str,
        # date is not included as it may be None and the normal check can't deal with that.
        "documents": List,
        "authors": List,
        "courses": List,
        "folders": List,
        "visible": bool,
    }
    PRIVATE_TABLE_NAME = "Items"
    PUBLIC_TABLE_NAME = "VisibleItems"
    RESOURCE_PATH = "/v1/items"

    @classmethod
    def validate_data(cls, data: Dict, may_be_partial: bool = False):
        """Checks whether the dictionary representation of an item results in a valid item.

        Parameters
        ----------
        cls : type
            Item type
        data: Dict
            dictionary mapping attribute names to their respective values
        may_be_partial: bool, optional
            Whether part of the attributes may be missing

        Raises
        ------
        BadRequest
            If date attribute is missing, not a string or not ISO-formatted or if one of the other attributes contains entries with invalid entry_id
        """
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
    def get_all(cls) -> Dict[int, Dict]:
        items = super(cls, Item).get_all()

        def set_attribute(attribute_name: str, table_name: str, column_name: str):
            # Initializing, so every attribute is at least empty
            for item_id in items.keys():
                items[item_id][attribute_name] = []

            cursor = g.archive.db.execute(f"select * from {table_name} order by ItemID")
            for item_id, rows in groupby(cursor, lambda row: row["ItemID"]):
                if item_id in items:
                    attribute_list = [row[column_name] for row in rows]
                    if attribute_list == [None]:
                        items[item_id][attribute_name] = []
                    else:
                        items[item_id][attribute_name] = attribute_list

        set_attribute("documents", "JoinedItemDocumentMap", "DocumentID")
        set_attribute("authors", "JoinedItemAuthorMap", "AuthorID")
        set_attribute("courses", "JoinedItemCourseMap", "CourseID")
        set_attribute("folders", "JoinedItemFolderMap", "FolderID")
        return items

    @classmethod
    def get(cls, entity_id: int) -> Dict:
        item = super(cls, Item).get(entity_id)

        item["visible"] = item["visible"] == 1

        def set_attribute(attribute_name: str, table_name: str, column_name: str):
            cursor = g.archive.db.execute(f"select {column_name} from {table_name} where ItemID=?", (entity_id,))
            item[attribute_name] = [row[column_name] for row in cursor]

        set_attribute("documents", "ItemDocumentMap", "DocumentID")
        set_attribute("authors", "ItemAuthorMap", "AuthorID")
        set_attribute("courses", "ItemCourseMap", "CourseID")
        set_attribute("folders", "ItemFolderMap", "FolderID")
        return item

    @classmethod
    def insert_attributes(cls, item_id: int, data: Dict, cleanup: bool = False):
        attribute_triples = [
            ("ItemDocumentMap", "DocumentID", data["documents"]),
            ("ItemAuthorMap", "AuthorID", data["authors"]),
            ("ItemCourseMap", "CourseID", data["courses"]),
            ("ItemFolderMap", "FolderID", data["folders"]),
        ]
        for (table_name, target_column, target_ids) in attribute_triples:
            if cleanup:
                g.archive.db.execute(f"delete from {table_name} where ItemID=?", (item_id,))
            g.archive.db.executemany(
                f"insert into {table_name}(ItemID, {target_column}) values (?, ?)",
                ((item_id, target_id) for target_id in target_ids)
            )

    @classmethod
    def post(cls, data: Dict) -> 'Item':
        cursor = g.archive.db.execute("insert into Items(name, date, visible) values (?, ?, ?)",
                                      (data["name"], data["date"], data["visible"]))
        item_id = cursor.lastrowid
        cls.insert_attributes(item_id, data)
        return item_id

    @classmethod
    def patch(cls, entry_id: int, new_data: Dict):
        data = cls.get(entry_id)
        data.update(new_data)
        g.archive.db.execute("update Items set name=?, date=?, visible=? where ID=?",
                             (data["name"], data["date"], data["visible"], entry_id))
        cls.insert_attributes(entry_id, data, cleanup=True)
