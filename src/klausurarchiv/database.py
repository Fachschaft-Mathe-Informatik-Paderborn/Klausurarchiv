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
from flask.views import MethodView
from flask_login import login_required, current_user
from werkzeug.exceptions import RequestEntityTooLarge, Unauthorized

from klausurarchiv.models import *

ALLOWED_CONTENT_TYPES = [
    "application/msword",
    "application/pdf",
    "application/x-latex",
    "image/png",
    "image/jpeg",
    "image/gif",
    "text/plain",
]

bp = Blueprint('database', __name__, url_prefix="/v1")


def dump_id_to_object_mapping(schema, resources):
    """
    A list of model objects are serialized as a mapping from their id to the actual item
    :param schema: serialization schema of type T
    :param resources: list of elements of type T
    :return: Mapped serialization
    """
    # map ids to objects
    resp = {obj.id: schema.dump(obj) for obj in resources}
    return resp, 200


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


def register_api(view, endpoint, url, pk='id', pk_type='int'):
    view_func = view.as_view(endpoint)
    bp.add_url_rule(url, defaults={pk: None},
                    view_func=view_func, methods=['GET', ], strict_slashes=False)
    bp.add_url_rule(url, view_func=view_func, methods=['POST', ], strict_slashes=False)
    bp.add_url_rule(f'{url}<{pk_type}:{pk}>', view_func=view_func,
                    methods=['GET', 'PATCH', 'DELETE'], strict_slashes=False)


# TODO: Make this abstract - inheriting ABC does not work because of metamagic
class Resource(MethodView):
    model: db.Model
    schema: ma.Schema

    def get(self, resource_id):
        if resource_id is None:
            all_resources = self.model.query.all()
            # flask does not jsonify lists for security reasons, so explicit mimetype
            return dump_id_to_object_mapping(self.schema, all_resources)
        else:
            resource = self.model.query.get_or_404(resource_id)
            return self.schema.dump(resource)

    @login_required
    def post(self):
        try:
            # include db.session explicitly as workaround for weird corner case
            # https://github.com/marshmallow-code/flask-marshmallow/issues/44
            loaded_schema = self.schema.load(request.json, partial=False, session=db.session)
        except ValidationError as err:
            return {"message": str(err.messages)}, 400
        loaded_resource = self.model(**loaded_schema)
        db.session.add(loaded_resource)
        db.session.commit()
        return {"id": loaded_resource.id}, 201

    @login_required
    def patch(self, resource_id):
        try:
            loaded_schema = self.schema.load(request.json, partial=True)
        except ValidationError as err:
            return {"message": str(err.messages)}, 400
        r = self.model.query.get_or_404(resource_id)
        for key, value in loaded_schema.items():
            setattr(r, key, value)
        db.session.commit()
        return dict(), 200

    @login_required
    def delete(self, resource_id):
        resource = self.model.query.get_or_404(resource_id)
        db.session.delete(resource)
        db.session.commit()
        return dict(), 200


class RestrictedResource(Resource):
    # TODO: subclass for resources where authorized/unauthorized behavior differ
    pass


class AuthorResource(Resource):
    model = Author
    schema = author_schema


class CourseResource(Resource):
    model = Course
    schema = course_schema


class FolderResource(Resource):
    model = Folder
    schema = folder_schema


class DocumentResource(Resource):
    model = Document
    schema = document_schema

    def get(self, resource_id):
        # TODO: Rework this with RestrictedResource
        if resource_id is None:
            if current_user.is_authenticated:
                visible_documents = Document.query.all()
            else:
                # unauthenticated users only see documents belonging to a visible item
                # we join Document to items via backref
                visible_documents = Document.query.join(Document.items, aliased=True).filter_by(visible=True).all()
            return dump_id_to_object_mapping(document_schema, visible_documents)
        else:
            if current_user.is_authenticated:
                document = Document.query.get_or_404(resource_id)
            else:
                # unauthenticated users only see documents belonging to a visible item
                # we join Document to items via backref
                document = Document.query.join(Document.items, aliased=True).filter_by(visible=True, id=resource_id) \
                    .first_or_404()
            return document_schema.dump(document)


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
    if document.downloadable or current_user.is_authenticated:
        # since document is stored in database, we cannot supply an actual file handle, just the corresponding bytes
        return send_file(io.BytesIO(document.file), mimetype=document.content_type, as_attachment=True,
                         download_name=document.filename)
    else:
        return {"message": "Not found"}, 404


class ItemResource(Resource):
    model = Item
    schema = item_schema

    def get(self, resource_id):
        # TODO: Rework this with RestrictedResource
        if resource_id is None:
            if current_user.is_authenticated:
                visible_items = Item.query.all()
            else:
                visible_items = Item.query.filter_by(visible=True).all()
            return dump_id_to_object_mapping(item_schema, visible_items)
        else:
            if current_user.is_authenticated:
                item = Item.query.get_or_404(resource_id)
            else:
                item = Item.query.filter_by(visible=True, id=resource_id).first_or_404()
        return item_schema.dump(item)


register_api(AuthorResource, 'author_api', '/authors/', pk='resource_id')

register_api(CourseResource, 'course_api', '/courses/', pk='resource_id')

register_api(FolderResource, 'folder_api', '/folders/', pk='resource_id')

register_api(DocumentResource, 'document_api', '/documents/', pk='resource_id')

register_api(ItemResource, 'item_api', '/items/', pk='resource_id')