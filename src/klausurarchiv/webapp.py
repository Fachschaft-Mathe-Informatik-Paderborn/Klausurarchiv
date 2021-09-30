import json

from flask import Response, Blueprint, request, session, make_response
from werkzeug.exceptions import HTTPException, BadRequest, Unauthorized
from typing import Dict, Callable
from functools import wraps

from klausurarchiv.db import *

bp = Blueprint("interface-v1", __name__, url_prefix="/v1")


@bp.errorhandler(Exception)
def handle_http_exception(e: Exception):
    if isinstance(e, HTTPException):
        return Response(
            response=json.dumps({
                "message": e.description,
            }),
            status=e.code,
            content_type="application/json"
        )
    else:
        print(e)
        return Response(
            response=json.dumps({
                "message": "Internal Server Error",
            }),
            status=500,
            content_type="application/json"
        )


def data_validated(attributes: Dict[str, type]) -> Callable:
    def decorator(view: Callable):
        @wraps(view)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if data is None:
                raise BadRequest("Request body may not be empty")

            for attr_name, attr_type in attributes.items():
                if attr_name not in data:
                    raise BadRequest(f"{attr_name} is missing")
                if not isinstance(data[attr_name], attr_type):
                    raise BadRequest(f"{attr_name} must be of type \"{attr_type.__name__}\"")

            return view(*args, **kwargs)

        return wrapper

    return decorator


def autocommit(view: Callable[..., Response]) -> Callable[..., Response]:
    @wraps(view)
    def wrapper(*args, **kwargs):
        result = view(*args, **kwargs)
        if result.status_code in {200, 201}:
            Archive.get_singleton().commit()
        return result

    return wrapper


def authorized(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            raise Unauthorized("You are not authorized to make this request")
        return view(*args, **kwargs)

    return wrapper


@bp.post("/login")
@data_validated(attributes={"username": str, "password": str})
def login():
    data = request.get_json()

    # TODO: Implement password checking
    correct = data["username"] == "john" and data["password"] == "4711"

    if not correct:
        raise Unauthorized("Invalid username or password")

    session["username"] = data["username"]

    return make_response(dict())


@bp.post("/logout")
def logout():
    try:
        session.pop("username")
    except KeyError:
        pass
    return make_response(dict())


@bp.get("/folders")
def get_all_folders():
    archive = Archive.get_singleton()
    folders = {folder.folder_id: {"name": folder.name} for folder in archive.folders}
    return make_response(folders)


@bp.post("/folders")
@authorized
@data_validated(attributes={"name": str})
@autocommit
def post_folder():
    data = request.get_json()
    archive = Archive.get_singleton()
    new_folder = archive.add_folder(**data)
    return make_response({"id": new_folder.folder_id})


@bp.get("/folders/<int:folder_id>")
def get_folder(folder_id):
    archive = Archive.get_singleton()
    folder = archive.get_folder(folder_id)
    return make_response({"name": folder.name})


@bp.delete("/folders/<int:folder_id>")
@authorized
@autocommit
def delete_folder(folder_id):
    archive = Archive.get_singleton()
    folder = archive.get_folder(folder_id)
    archive.remove_folder(folder)
    return make_response({})
