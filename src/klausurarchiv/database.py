"""
database.py
========================
Contains the logic for all API endpoints that access the underlying database.
"""
import cgi
import datetime
import importlib.resources as import_res
import io
import os
import sqlite3
from io import BytesIO
from itertools import groupby
from pathlib import Path
from typing import List, Optional, Dict, TypeVar
from flask import Flask, request, send_file, Blueprint, current_app
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
from marshmallow import ValidationError, validates, post_dump, post_load, pre_dump
from werkzeug.wsgi import FileWrapper

from klausurarchiv.models import author_schema, course_schema, folder_schema, document_schema, item_schema, \
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


def make_list_response(schema, elements):
    """
    Lists of items are serialized as a mapping from their id to the actual item
    :param schema: serialization schema of type T
    :param list: list of elements of type T
    :return: Mapped serialization
    """
    # map ids to objects
    resp = {obj.id : schema.dump(obj) for obj in elements}
    return resp, 200


bp = Blueprint('database', __name__, url_prefix="/v1")

"""
Author related routes
"""


@bp.route("/authors/", methods=["GET"], strict_slashes=False)
def get_all_authors():
    all_authors = Author.query.all()
    # flask does not jsonify lists for security reasons, so explicit mimetype
    return make_list_response(author_schema, all_authors)


@bp.route("/authors/", methods=["POST"], strict_slashes=False)
@login_required
def add_author():
    try:
        loaded_schema = author_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    loaded_author = Author(**loaded_schema)
    db.session.add(loaded_author)
    db.session.commit()
    return {"id": loaded_author.id}, 201


@bp.route("/authors/<int:author_id>", methods=["GET"], strict_slashes=False)
def get_author(author_id):
    author = Author.query.get_or_404(author_id)
    return author_schema.dump(author)


@bp.route("/authors/<int:author_id>", methods=["PATCH"], strict_slashes=False)
@login_required
def update_author(author_id):
    try:
        loaded_schema = author_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    a = Author.query.get_or_404(author_id)
    for key, value in loaded_schema.items():
        setattr(a, key, value)
    db.session.commit()
    return dict(), 200


@bp.route("/authors/<int:author_id>", methods=["DELETE"], strict_slashes=False)
@login_required
def delete_author(author_id):
    author = Author.query.get_or_404(author_id)
    db.session.delete(author)
    db.session.commit()
    return dict(), 200


"""
Course related routes
"""


@bp.route("/courses/", methods=["GET"], strict_slashes=False)
def get_all_courses():
    all_courses = Course.query.all()
    return make_list_response(course_schema, all_courses)


@bp.route("/courses/", methods=["POST"], strict_slashes=False)
@login_required
def add_course():
    try:
        loaded_schema = course_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    loaded_course = Course(**loaded_schema)
    db.session.add(loaded_course)
    db.session.commit()
    return {"id": loaded_course.id}, 201


@bp.route("/courses/<int:course_id>", methods=["GET"], strict_slashes=False)
def get_course(course_id):
    course = Course.query.get_or_404(course_id)
    return course_schema.dump(course)


@bp.route("/courses/<int:course_id>", methods=["PATCH"], strict_slashes=False)
@login_required
def update_course(course_id):
    try:
        loaded_schema = course_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    c = Course.query.get_or_404(course_id)
    for key, value in loaded_schema.items():
        setattr(c, key, value)

    db.session.commit()
    return dict(), 200


@bp.route("/courses/<int:course_id>", methods=["DELETE"], strict_slashes=False)
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    return dict(), 200


"""
Folder related routes
"""


@bp.route("/folders/", methods=["GET"], strict_slashes=False)
def get_all_folders():
    all_folders = Folder.query.all()
    return make_list_response(folder_schema, all_folders)


@bp.route("/folders/", methods=["POST"], strict_slashes=False)
@login_required
def add_folder():
    try:
        loaded_schema = folder_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    loaded_folder = Folder(**loaded_schema)
    db.session.add(loaded_folder)
    db.session.commit()
    return {"id": loaded_folder.id}, 201


@bp.route("/folders/<int:folder_id>", methods=["GET"], strict_slashes=False)
def get_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    return folder_schema.dump(folder)


@bp.route("/folders/<int:folder_id>", methods=["PATCH"], strict_slashes=False)
@login_required
def update_folder(folder_id):
    try:
        loaded_schema = folder_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    f = Folder.query.get_or_404(folder_id)
    for key, value in loaded_schema.items():
        setattr(f, key, value)
    db.session.commit()
    return dict(), 200


@bp.route("/folders/<int:folder_id>", methods=["DELETE"], strict_slashes=False)
@login_required
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    db.session.delete(folder)
    db.session.commit()
    return dict(), 200


"""
Document related routes
"""


@bp.route("/documents/", methods=["GET"], strict_slashes=False)
def get_all_documents():
    if current_user.is_authenticated:
        visible_documents = Document.query.all()
    else:
        # unauthenticated users only see documents belonging to a visible item
        # we join Document to items via backref
        visible_documents = Document.query.join(Document.items, aliased=True).filter_by(visible=True).all()
    return make_list_response(document_schema, visible_documents)


@bp.route("/documents/", methods=["POST"], strict_slashes=False)
@login_required
def add_document():
    try:
        loaded_schema = document_schema.load(request.json, partial=False)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    loaded_document = Document(**loaded_schema)

    db.session.add(loaded_document)
    db.session.commit()
    return {"id": loaded_document.id}, 201


@bp.route("/documents/<int:document_id>", methods=["GET"], strict_slashes=False)
def get_document(document_id):
    if current_user.is_authenticated:
        document = Document.query.get_or_404(document_id)
    else:
        # unauthenticated users only see documents belonging to a visible item
        # we join Document to items via backref
        document = Document.query.join(Document.items, aliased=True).filter_by(visible=True, id=document_id)\
            .first_or_404()
    return document_schema.dump(document)


@bp.route("/documents/<int:document_id>", methods=["PATCH"], strict_slashes=False)
@login_required
def update_document(document_id):
    try:
        loaded_schema = document_schema.load(request.json, partial=True)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    d = Document.query.get_or_404(document_id)
    for key, value in loaded_schema.items():
        setattr(d, key, value)
    db.session.commit()
    return dict(), 200


@bp.route("/documents/<int:document_id>", methods=["DELETE"], strict_slashes=False)
@login_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    db.session.delete(document)
    db.session.commit()
    return dict(), 200


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
@login_required
def upload_document():
    document_id = request.args.get("id", default=None)
    document = Document.query.get_or_404(document_id)

    if request.content_length > current_app.config["MAX_CONTENT_LENGTH"]:
        raise RequestEntityTooLarge()

    document.file = request.get_data()

    document.content_type = request.headers.get("Content-Type")
    if document.content_type not in ALLOWED_CONTENT_TYPES:
        return {"message": f"Content Type {document.content_type} not allowed"}, 400

    # parse Content-Disposition header for secure access to attributes without janky regex or similar
    _, params = cgi.parse_header(request.headers.get('Content-Disposition', ""))

    # if given override the old filename by the one given through the header, otherwise default to existing one
    new_filename = params.get("filename", document.filename)

    if not new_filename or secure_filename(new_filename) != new_filename:
        # if somehow neither header nor database contain a filename (or they are corrutped) we fallback to random
        new_filename = hashlib.sha256(bytes(document.file)).hexdigest()

    document.filename = new_filename

    db.session.add(document)
    db.session.commit()
    return dict(), 200


@bp.route("/download", methods=["GET"], strict_slashes=False)
def download_document():
    document_id = request.args.get("id", default=None)
    document = Document.query.get_or_404(document_id)
    # since document is stored in database, we cannot supply an actual file handle, just the corresponding bytes
    return send_file(io.BytesIO(document.file), mimetype=document.content_type, as_attachment=True,
                     download_name=document.filename)


"""
Item related routes
"""


@bp.route("/items/", methods=["GET"], strict_slashes=False)
def get_all_items():
    if current_user.is_authenticated:
        # authenticated users get to see all items
        visible_items = Item.query.all()
    else:
        visible_items = Item.query.filter_by(visible=True).all()
    return make_list_response(item_schema, visible_items)


@bp.route("/items/", methods=["POST"], strict_slashes=False)
@login_required
def add_item():
    try:
        # include db.session explicitly as workaround for weird corner case
        # https://github.com/marshmallow-code/flask-marshmallow/issues/44
        loaded_schema = item_schema.load(request.json, partial=False, transient=False, session=db.session)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    loaded_item = Item(**loaded_schema)
    db.session.add(loaded_item)
    db.session.commit()
    return {"id": loaded_item.id}, 201


@bp.route("/items/<int:item_id>", methods=["GET"], strict_slashes=False)
def get_item(item_id):
    if current_user.is_authenticated:
        item = Item.query.get_or_404(item_id)
    else:
        # unauthenticated users cannot see items with visible=False, so we can not just get by primary key
        item = Item.query.filter_by(visible=True, id=item_id).first_or_404()
    return item_schema.dump(item)


@bp.route("/items/<int:item_id>", methods=["PATCH"], strict_slashes=False)
@login_required
def update_item(item_id):
    try:
        loaded_schema = item_schema.load(request.json, partial=True)
        # print(loaded_schema)
    except ValidationError as err:
        return {"message": str(err.messages)}, 400
    i = Item.query.get_or_404(item_id)
    for key, value in loaded_schema.items():
        setattr(i, key, value)

    db.session.commit()
    return dict(), 200


@bp.route("/items/<int:item_id>", methods=["DELETE"], strict_slashes=False)
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return dict(), 200