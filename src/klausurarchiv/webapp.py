import json

from flask import Response, Blueprint, request, session
from werkzeug.exceptions import HTTPException, BadRequest, Unauthorized
from typing import Dict
from datetime import datetime

from klausurarchiv.db import *

bp = Blueprint("interface-v1", __name__, url_prefix="/v1")


@bp.errorhandler(HTTPException)
def handle_http_exception(e: HTTPException):
    return json.dumps({
        "message": e.description
    }), e.code


@bp.post("/login")
def login():
    data = request.get_json()

    if data is None:
        raise BadRequest("Request body may not be empty")

    try:
        username = str(data["username"])
    except KeyError:
        raise BadRequest("Request must contain username")

    try:
        password = str(data["password"])
    except KeyError:
        raise BadRequest("Request must contain password")

    # TODO: Implement password checking
    correct = username == "john" and password == "4711"

    if not correct:
        raise Unauthorized("Invalid username or password")

    session["username"] = username

    return json.dumps(dict())


@bp.post("/logout")
def logout():
    try:
        session.pop("username")
    except KeyError:
        pass
    return json.dumps(dict())


@bp.route("/item")
def get_all_items():
    archive = Archive.get_singleton()
    response = Response(
        response=json.dumps(
            [{"name": item.name,
              "uuid": item.uuid,
              "date": item.date,
              "author": item.author.name if item.author is not None else None,
              "downloadable": item.downloadable,
              "folder": item.folder.name if item.folder is not None else None,
              "documents": [doc.name for doc in item.documents]} for item in archive.items
             ],
            default=str),
        status=200,
        mimetype='application/json'
    )
    return response
