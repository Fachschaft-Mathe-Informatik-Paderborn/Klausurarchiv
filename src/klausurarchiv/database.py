"""
database.py
========================
Contains the logic for all API endpoints that access the underlying database.
"""
import io
import ipaddress
from typing import Dict, Optional, List, Union

from flask import request, send_file, Blueprint, current_app
from flask.views import MethodView
from flask_caching import Cache
from flask_login import login_required, current_user
from werkzeug.exceptions import RequestEntityTooLarge, Unauthorized, abort

from klausurarchiv.models import *

bp = Blueprint('database', __name__, url_prefix="/v1")

cache = Cache()


@bp.before_request
def check_ip_address():
    client_ip = ipaddress.ip_address(request.access_route[0])

    def check_rules(rules: Optional[Dict[str, List[str]]]) -> bool:
        if "allow" in rules and "deny" in rules:
            raise Exception(
                "Config error: No simultaneous allow and deny rules allowed")

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
    bp.add_url_rule(url, view_func=view_func, methods=[
                    'POST', ], strict_slashes=False)
    bp.add_url_rule(f'{url}<{pk_type}:{pk}>', view_func=view_func,
                    methods=['GET', 'PATCH', 'DELETE'], strict_slashes=False)


# TODO: would like to make this abstract, but I'll have to read up on metaclasses for that
class Resource(MethodView):
    model: db.Model
    schema: ma.Schema

    @cache.cached()
    def get(self, resource_id):
        if resource_id is None:
            all_resources = self.model.query.all()
            return self.dump_id_to_object_mapping(all_resources)
        else:
            resource = self.model.query.get_or_404(resource_id)
            return self.schema.dump(resource)

    @login_required
    def post(self):
        try:
            # include db.session explicitly as workaround for weird corner case
            # https://github.com/marshmallow-code/flask-marshmallow/issues/44
            loaded_schema = self.schema.load(
                request.json, partial=False, session=db.session)
        except ValidationError as err:
            return {"message": str(err.messages)}, 400
        loaded_resource = self.model(**loaded_schema)

        error_message = self.is_resource_valid(loaded_resource)

        if error_message is None:
            db.session.add(loaded_resource)
            db.session.commit()
            return {"id": loaded_resource.id}, 201
        else:
            return {"message": error_message}, 400

    @login_required
    def patch(self, resource_id):
        try:
            loaded_schema = self.schema.load(request.json, partial=True)
        except ValidationError as err:
            return {"message": str(err.messages)}, 400
        r = self.model.query.get_or_404(resource_id)
        for key, value in loaded_schema.items():
            setattr(r, key, value)

        error_message = self.is_resource_valid(r)
        if error_message is None:
            db.session.commit()
            return dict(), 200
        else:
            return {"message": error_message}, 400

    def is_resource_valid(self, resource) -> Union[None, str]:
        """
        Test the resource's semantic structure.

        If the resource is valid, return None. Otherwise, return a string that describes the offense.
        """
        return None

    @login_required
    def delete(self, resource_id):
        resource = self.model.query.get_or_404(resource_id)
        db.session.delete(resource)
        db.session.commit()
        return dict(), 200

    def dump_id_to_object_mapping(self, resources):
        """
        Serializes a list of resources as a mapping of their id to their actual content
        :param resources: list of model objects
        :return: Mapped serialization
        """
        resp = {r.id: self.schema.dump(r) for r in resources}
        return resp, 200


class AuthorResource(Resource):
    model = Author
    schema = AuthorSchema()


class CourseResource(Resource):
    model = Course
    schema = CourseSchema()


class FolderResource(Resource):
    model = Folder
    schema = FolderSchema()


class DocumentResource(Resource):
    model = Document
    schema = DocumentSchema()

    def is_resource_valid(self, resource) -> Union[None, str]:
        if resource.content_type not in current_app.config["ALLOWED_CONTENT_TYPES"]:
            return f"Content type '{resource.content_type}' is not allowed by the server."

        if len(resource.filename) == 0:
            return "Empty filename"

        if not secure_filename(resource.filename):
            return "Insecure filename"


@bp.route("/upload", methods=["POST"], strict_slashes=False)
@login_required
def upload_document():
    document_id = request.args.get("id", default=None)
    document = Document.query.get_or_404(document_id)

    if request.content_length > current_app.config["MAX_CONTENT_LENGTH"]:
        raise RequestEntityTooLarge()

    if document.content_type != request.headers.get("Content-Type"):
        return {"message": "The uploaded content's type does not match the database entry"}, 400

    document.file = request.get_data()

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
        abort(404)


class ItemResource(Resource):
    model = Item
    schema = ItemSchema()


register_api(AuthorResource, 'author_api', '/authors/', pk='resource_id')

register_api(CourseResource, 'course_api', '/courses/', pk='resource_id')

register_api(FolderResource, 'folder_api', '/folders/', pk='resource_id')

register_api(DocumentResource, 'document_api', '/documents/', pk='resource_id')

register_api(ItemResource, 'item_api', '/items/', pk='resource_id')
