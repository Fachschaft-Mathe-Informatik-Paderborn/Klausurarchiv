"""
database.py
========================
Contains the logic for all API endpoints that access the underlying database.
"""
import cgi
import hashlib
import io
import ipaddress
from typing import Dict, Optional, List

from flask import request, send_file, Blueprint, current_app
from flask_login import login_required, current_user
from werkzeug.exceptions import RequestEntityTooLarge, Unauthorized

from klausurarchiv.models import *


def make_list_response(schema, elements):
    """
    Lists of items are serialized as a mapping from their id to the actual item
    :param schema: serialization schema of type T
    :param list: list of elements of type T
    :return: Mapped serialization
    """
    # map ids to objects
    resp = {obj.id: schema.dump(obj) for obj in elements}
    return resp, 200


bp = Blueprint('database', __name__, url_prefix="/v1")


@bp.before_request
def check_ip_address():
    client_ip = ipaddress.ip_address(request.access_route[0])

    def check_rules(rules: Optional[Dict[str, List[str]]]) -> bool:
        if "allow" in rules and "deny" in rules:
            raise Exception("Config error: No simultaneous allow and deny rules allowed")

        if "allow" in rules:
            return any(client_ip in ipaddress.ip_network(network) for network in rules["allow"])
        elif "deny" in rules:
            return all(client_ip not in ipaddress.ip_network(network) for network in rules["deny"])
        else:
            return True

    access_config = current_app.config.get("ACCESS")

    if access_config is None:
        allowed = True
    else:
        resource_name = request.path.split("/")[2]

        if resource_name in access_config:
            allowed = check_rules(access_config[resource_name])
        elif "*" in access_config:
            allowed = check_rules(access_config["*"])
        else:
            allowed = True

    if not allowed:
        raise Unauthorized("IP address blocked")


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
        document = Document.query.join(Document.items, aliased=True).filter_by(visible=True, id=document_id) \
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
