import tempfile

from model import *

from flask import Flask, send_file, request, render_template, jsonify, abort, Response
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder="../html")

app.config["UPLOAD_FOLDER"] = "../UPLOAD_FOLDER"
app.config["MAX_CONTENT_PATH"] = 10 ** 6 * 100  # TODO 100MB


def get_item(id: UUID):
    for item in archive.items:
        if item.uuid == id:
            return item
    return None


def get_document(item_id: UUID, document_name: str):
    item = get_item(item_id)
    if not item:
        return None

    for document in item.documents:
        if document.path.name == document_name:
            return document
    return None


@app.route("/")
def main():
    return "Klausurarchiv"


@app.route("/v1/item")
def get_all_items():
    # get meta data of all items
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


@app.route("/v1/item", methods=["POST"])
def add_item():
    # add new item
    if not request.form.get('name'):
        print(request.form.get('name'))
        abort(400, description="A Item needs a <str:name> attribute")

    if not request.form.get('downloadable'):
        abort(400, description="A Item needs a <int:downloadable> attribute")

    try:
        date_item = datetime.date.fromisoformat(request.form.get('date'))
    except ValueError:
        abort(400, description="The date of the item is not in the correct format YYYY-MM-DD")

    try:
        downloadable = bool(int(request.form.get('downloadable')))
    except ValueError:
        abort(400, description="The downloadable attribute of the item is not a integer between 0 and 1")

    item = archive.add_item()
    meta = ItemMeta()

    meta.name = request.form.get('name')
    meta.date = date_item
    meta.author = request.form.get('author')
    meta.downloadable = downloadable

    item.meta = meta

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
    item = get_item(id)
    if not item:
        abort(400, description="Given item uuid is not found")

    archive.remove_item(item)
    return Response(status=200)


@app.route("/v1/item/<uuid:ID>/document")
def get_all_documents_of_item(id):
    # get meta data of all documents from existing item
    item = get_item(id)
    if not item:
        abort(400, description="Given item uuid is not found")

    response = app.response_class(
        response=json.dumps(
            [{"name": document.path.name} for document in item.documents],
            default=str),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route("/v1/item/<uuid:id>/document", methods=["POST"])
def upload_document_to_item(id):
    # Add document to item: <filename> needed
    item = get_item(id)
    if not item:
        abort(400, description="Given item uuid is not found")

    # Check whether the key exists in the POST request
    if not "filename" in request.files:
        abort(400, description="File key in the POST request is missing")

    file_object = request.files["filename"]

    if file_object.filename == "":
        abort(400, description="No file uploaded")

    # Sanitize bad filename https://flask.palletsprojects.com/en/2.0.x/patterns/fileuploads/
    file_name = secure_filename(file_object.filename)

    if get_document(id, file_name) is not None:
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
    return Response(status=201)


@app.route("/v1/item/<uuid:id>/document/<string:name>")
def download_document_of_item(id, name):
    # download document of item
    item = get_item(id)
    document = get_document(id, name)
    if not document:
        abort(400, description="Given document by item uuid and document name is not found")

    if not item.meta.downloadable:
        abort(423, description="Given document does exists but is not accessible")

    return send_file(document.path, as_attachment=True)


@app.route("/v1/item/<uuid:id>/document/<string:name>", methods=["DELETE"])
def delete_document_of_item(id, name):
    # delete document of item
    item = get_item(id)
    document = get_document(id, name)

    if not item:
        abort(400, description="Given item uuid is not found")
    if not document:
        abort(400, description="Given document by item uuid and document name is not found")

    item.remove_document(document)
    return Response(status=200)


if __name__ == '__main__':
    archive = Archive("../../archive")
    app.run(port=5001, debug=True)
    # d = datetime.datetime.strptime("2019-09-06", "%Y-%m-%d")
