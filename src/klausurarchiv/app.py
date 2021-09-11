import json
import tempfile

from flask import Flask, send_file, request, jsonify, abort, Response, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename

from model import *

app = Flask(__name__)
CORS(app)

# app.config["UPLOAD_FOLDER"] = "../UPLOAD_FOLDER"
app.config["MAX_CONTENT_PATH"] = 10 ** 6 * 100  # TODO 100MB

ARCHIVE_PATH = Path("../../archive")


@app.route("/")
def main():
    return Path("Klausurarchiv")


"""@app.route("/v1/item", provide_automatic_options=True)
def get_all_items():
    # get meta data of all items
    print("get meta data of all items")
    response = app.response_class(
        response=json.dumps(
            [{"name": item.meta.name,
              "uuid": item.uuid,
              "date": item.meta.date,
              "author": item.meta.author,
              "downloadable": item.meta.downloadable} for item in archive.items
             ],
            default=str),
        status=200,
        mimetype='application/json'
    )
    return response
"""


@app.route("/v1/item")
def get_all_items():
    # get meta data of all items
    archive = Archive(ARCHIVE_PATH)
    print("get meta data of all items")
    response = app.response_class(
        response=json.dumps(
            [{"name": item.name,
              "uuid": item.uuid,
              "date": item.date,
              "author": item.author.name,
              "downloadable": item.downloadable,
              "documents": [doc.name for doc in item.documents]} for item in archive.items
             ],
            default=str),
        status=200,
        mimetype='application/json'
    )
    del archive
    return response


@app.route("/v1/item", methods=["POST"])
def add_item():
    # add new item
    archive = Archive(ARCHIVE_PATH)
    print("add new item\n", request.__dict__)

    if request.is_json:
        data_transmitted_by_request = request.get_json()
    else:
        data_transmitted_by_request = request.form.to_dict()

    if not data_transmitted_by_request.get('name'):
        # abort(400, jsonify({"message":"A Item needs a <str:name> attribute"}))
        """return Response(jsonify(
            message="No ids provided.",
            category="error",
            status=404
        ), status=404)"""
        return make_response(jsonify(message="A Item needs a <str:name> attribute"), 400)

    if not data_transmitted_by_request.get('downloadable'):
        return make_response(jsonify(message="A Item needs a <int:downloadable> attribute"), 400)
    try:
        date_item = datetime.date.fromisoformat(data_transmitted_by_request.get('date'))
    except ValueError:
        return make_response(jsonify(message="The date of the item is not in the correct format YYYY-MM-DD"), 400)

    try:
        downloadable = bool(int(data_transmitted_by_request.get('downloadable')))
    except ValueError:
        return make_response(jsonify(message="The downloadable attribute of the item is not a integer between 0 and 1"),
                             400)

    item = archive.add_item(data_transmitted_by_request.get('name'))
    item.date = date_item
    item.downloadable = downloadable

    author = archive.get_author_by_name(request.form.get('author'))
    if author is None:
        author = archive.add_author(request.form.get('author'))
    item.author.name = author

    del archive
    return Response(status=201)


"""
@app.route("/v1/item/<uuid:ID>", methods=["POST"])
def get_all_items(self, ID):
    # change existing item
    return {}
"""


@app.route("/v1/item/<uuid:id>", methods=["DELETE"])
def delete_item(id):
    # delete existing item
    archive = Archive(ARCHIVE_PATH)

    item = archive.get_item_with_uuid(id)
    if item is None:
        abort(400, description="Given item uuid is not found")

    archive.remove_item(item)
    del archive
    return Response(status=200)


@app.route("/v1/item/<uuid:id>/document")
def get_all_documents_of_item(id):
    # get meta data of all documents from existing item
    archive = Archive(ARCHIVE_PATH)

    item = archive.get_item_with_uuid(id)
    if item is None:
        abort(400, description="Given item uuid is not found")

    response = app.response_class(
        response=json.dumps(
            [{"name": document.path.name} for document in item.documents],
            default=str),
        status=200,
        mimetype='application/json'
    )

    del archive
    return response


@app.route("/v1/item/<uuid:id>/document", methods=["POST"])
def upload_document_to_item(id):
    # Add document to item: <filename> needed
    archive = Archive(ARCHIVE_PATH)

    item = archive.get_item_with_uuid(id)
    if item is None:
        abort(400, description="Given item uuid is not found")

    # Check whether the key exists in the POST request
    if "filename" not in request.files:
        abort(400, description="File key in the POST request is missing")

    file_object = request.files["filename"]

    if file_object.filename == "":
        abort(400, description="No file uploaded")

    # Sanitize bad filename https://flask.palletsprojects.com/en/2.0.x/patterns/fileuploads/
    file_name = secure_filename(file_object.filename)

    if item.get_document_with_name(file_name) is not None:
        abort(400, description="Filename does already exists")

    # Store the uploaded file in a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / Path(file_name)
        file_object.save(file_path)

        try:
            item.add_document(file_path)
        except KeyError as e:
            abort(400, description=str(e))
        # finally the directory and the file is automatically removed
        # even in an event of an exception

    del archive
    return Response(status=201)


@app.route("/v1/item/<uuid:id>/document/<string:name>")
def download_document_of_item(id, name):
    # download document of item
    archive = Archive(ARCHIVE_PATH)
    item = archive.get_item_with_uuid(id)
    document = item.get_document_with_name(name)
    if not document:
        abort(400, description="Given document by item uuid and document name is not found")

    if not item.downloadable:
        abort(423, description="Given document does exists but is not accessible")

    return send_file(document.path, as_attachment=True)


@app.route("/v1/item/<uuid:id>/document/<string:name>", methods=["DELETE"])
def delete_document_of_item(id, name):
    # delete document of item
    archive = Archive(ARCHIVE_PATH)
    item = archive.get_item_with_uuid(id)
    document = item.get_document_with_name(name)

    if not item:
        abort(400, description="Given item uuid is not found")
    if not document:
        abort(400, description="Given document by item uuid and document name is not found")

    item.remove_document(document)
    return Response(status=200)


if __name__ == '__main__':
    app.run(port=5001, debug=True),  # host="0.0.0.0")
    # d = datetime.datetime.strptime("2019-09-06", "%Y-%m-%d")
