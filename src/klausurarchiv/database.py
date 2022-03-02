"""
database.py
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
from flask import Flask, request, send_file, Blueprint
from flask import g, make_response, Response
from flask_login import login_required, current_user
from flask_caching import Cache
from werkzeug.exceptions import BadRequest, NotFound, RequestEntityTooLarge, Unauthorized
from werkzeug.utils import secure_filename
import base64
from datetime import datetime
import hashlib
from flask import Flask, request, make_response
from flask_sqlalchemy import SQLAlchemy, inspect
from flask_marshmallow import Marshmallow
# import magic #  TODO is this needed?
from marshmallow import ValidationError, validates, post_dump, post_load, pre_dump

from klausurarchiv.models import authors_schema, author_schema, course_schema, folders_schema, \
    folder_schema, documents_schema, document_schema, items_schema, item_schema, courses_schema, \
    Author, Folder, Course, Item, Document
from klausurarchiv.models import db

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


bp = Blueprint('database', __name__, url_prefix="/v1")

"""
Author related routes
"""


@bp.route("/authors/", methods=["GET"], strict_slashes=False)
def get_all_authors():
    all_authors = Author.query.all()
    return authors_schema.dumps(all_authors)


@bp.route("/authors/", methods=["POST"], strict_slashes=False)
def add_author():
    try:
        loaded_schema = author_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": err.messages}, 400
    loaded_author = Author(**loaded_schema)
    db.session.add(loaded_author)
    db.session.commit()
    return {"id": loaded_author.id}, 201


@bp.route("/authors/<int:author_id>", methods=["GET"], strict_slashes=False)
def get_author(author_id):
    author = Author.query.get_or_404(author_id)
    return author_schema.dump(author)


@bp.route("/authors/<int:author_id>", methods=["PATCH"], strict_slashes=False)
def update_author(author_id):
    try:
        loaded_schema = author_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": err.messages}, 400
    Author.query.filter_by(id=author_id).update(loaded_schema)
    db.session.commit()
    return '', 200


@bp.route("/authors/<int:author_id>", methods=["DELETE"], strict_slashes=False)
def delete_author(author_id):
    author = Author.query.get_or_404(author_id)
    db.session.delete(author)
    db.session.commit()
    return '', 200


"""
Course related routes
"""

@bp.route("/courses/", methods=["GET"], strict_slashes=False)
def get_all_courses():
    all_courses = Course.query.all()
    return courses_schema.dumps(all_courses)

@bp.route("/courses/", methods=["POST"], strict_slashes=False)
def add_course():
    try:
        loaded_schema = course_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": err.messages}, 400
    loaded_course = Course(**loaded_schema)
    db.session.add(loaded_course)
    db.session.commit()
    return {"id": loaded_course.id}, 201


@bp.route("/courses/<int:course_id>", methods=["GET"], strict_slashes=False)
def get_course(course_id):
    course = Course.query.get_or_404(course_id)
    return course_schema.dump(course)

@bp.route("/courses/<int:course_id>", methods=["PATCH"], strict_slashes=False)
def update_course(course_id):
    try:
        loaded_schema = course_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": err.messages}, 400
    Course.query.filter_by(id=course_id).update(loaded_schema)
    db.session.commit()
    return '', 200

@bp.route("/courses/<int:course_id>", methods=["DELETE"], strict_slashes=False)
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    return '', 200


"""
Folder related routes
"""

@bp.route("/folders/", methods=["GET"], strict_slashes=False)
def get_all_folders():
    all_folders = Folder.query.all()
    return folders_schema.dump(all_folders)

@bp.route("/folders/", methods=["POST"], strict_slashes=False)
def add_folder():
    try:
        loaded_schema = folder_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": err.messages}, 400
    loaded_folder = Folder(**loaded_schema)
    db.session.add(loaded_folder)
    db.session.commit()
    return {"id": loaded_folder.id}, 201

@bp.route("/folders/<int:folder_id>", methods=["GET"], strict_slashes=False)
def get_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    return folder_schema.dump(folder)

@bp.route("/folders/<int:folder_id>", methods=["PATCH"], strict_slashes=False)
def update_folder(folder_id):
    try:
        loaded_schema = folder_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": err.messages}, 400
    Folder.query.filter_by(id=folder_id).update(loaded_schema)
    db.session.commit()
    return '', 200

@bp.route("/folders/<int:folder_id>", methods=["DELETE"], strict_slashes=False)
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    db.session.delete(folder)
    db.session.commit()
    return '', 200


"""
Document related routes
"""
@bp.route("/documents/", methods=["GET"], strict_slashes=False)
def get_all_documents():
    all_documents = Document.query.all()
    return documents_schema.dump(all_documents)

@bp.route("/documents/", methods=["POST"], strict_slashes=False)
def add_document():
    try:
        loaded_schema = document_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": err.messages}, 400
    loaded_document = Document(**loaded_schema)
    db.session.add(loaded_document)
    db.session.commit()
    return {"id": loaded_document.id}, 201

@bp.route("/documents/<int:document_id>", methods=["GET"], strict_slashes=False)
def get_document(document_id):
    document = Document.query.get_or_404(document_id)
    return document_schema.dump(document)

@bp.route("/documents/<int:document_id>", methods=["PATCH"], strict_slashes=False)
def update_document(document_id):
    try:
        loaded_schema = document_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": err.messages}, 400
    Document.query.filter_by(id=document_id).update(loaded_schema)
    db.session.commit()
    return '', 200

@bp.route("/documents/<int:document_id>", methods=["DELETE"], strict_slashes=False)
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    db.session.delete(document)
    db.session.commit()
    return '', 200

ALLOWED_CONTENT_TYPES = [
    "application/msword",
    "application/pdf",
    "application/x-latex",
    "image/png",
    "image/jpeg",
    "image/gif",
    "text/plain",
]

@bp.route("/upload", methods=["POST"], strict_slashes=False)
def upload_document(self):
    document_id = request.args.get("id", default=None)
    document = Document.query.get(document_id)
    if not document:
        document = Document()
    document.file = request.get_data()
    document.content_type = magic.from_buffer(document.file, mime=True)
    if document.content_type not in self.ALLOWED_CONTENT_TYPES:
        return {"message": f"Content Type {document.content_type} not allowed"}, 400
    if not document.filename:
        document.filename = hashlib.sha256(document.file).hexdigest()
    db.session.add(document)
    db.session.commit()
    return {"id": document.id}, 201


@bp.route("/download", methods=["GET"], strict_slashes=False)
def download_document(self):
    document_id = request.args.get("id", default=None)
    document = Document.query.get_or_404(document_id)
    response = make_response(document.file)
    response.headers['Content-Type'] = document.content_type
    response.headers['Content-Disposition'] = f'attachment; filename={document.filename}'
    return response


"""
Item related routes
"""
@bp.route("/items/", methods=["GET"], strict_slashes=False)
def get_all_items():
    all_items = Item.query.all()
    return items_schema.dump(all_items)

@bp.route("/items/", methods=["POST"], strict_slashes=False)
def add_item(self):
    try:
        loaded_schema = item_schema.load(request.json, partial=False, transient=False)
    except ValidationError as err:
        return {"message": err.messages}, 400
    loaded_item = Item(**loaded_schema)
    db.session.add(loaded_item)
    db.session.commit()
    return {"id": loaded_item.id}, 201


@bp.route("/items/<int:item_id>", methods=["GET"], strict_slashes=False)
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return item_schema.dump(item)

@bp.route("/items/<int:item_id>", methods=["PATCH"], strict_slashes=False)
def update_item(item_id):
    try:
        loaded_schema = item_schema.load(request.json, partial=True)
        # print(loaded_schema)
    except ValidationError as err:
        return {"message": err.messages}, 400
    # TODO: update of other cases fails here, maybe theres a broader problem and this should always be done
    i = Item.query.get(item_id)
    for key, value in loaded_schema.items():
        setattr(i, key, value)

    db.session.commit()
    return '', 200

@bp.route("/items/<int:item_id>", methods=["DELETE"], strict_slashes=False)
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return '', 200
