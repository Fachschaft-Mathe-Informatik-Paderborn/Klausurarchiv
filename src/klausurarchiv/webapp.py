import json

from flask import Response, Blueprint

from klausurarchiv.model import *

bp = Blueprint("interface-v1", __name__, url_prefix="/v1")


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
