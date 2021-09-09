from flask import Flask, send_file, request, render_template, jsonify
from pathlib import Path

from model import *

app = Flask(__name__, template_folder="../html")

app.config["UPLOAD_FOLDER"] = "../UPLOAD_FOLDER"
app.config["MAX_CONTENT_PATH"] = 10 ** 6 * 300  # TODO 300MB

from flask import jsonify, request

class InvalidAPIUsage(Exception):
    # https://flask.palletsprojects.com/en/2.0.x/errorhandling/
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidAPIUsage)
def invalid_api_usage(e):
    return jsonify(e.to_dict())


@app.route("/")
def main():
    return "Klausurarchiv"


@app.route("/download/<int:file_uuid>")
def download(file_uuid):
    return send_file("../../Plan.pdf", as_attachment=True)


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    file.save(Path(app.config["UPLOAD_FOLDER"]) / Path(file.filename))
    return render_template("upload_status.html", status="Erfolgreich hochgeladen!")


@app.route("/v1/item")
def get_all_items(self):
    # get meta data of all items
    return json.dumps([{"name": item.name,
             "uuid": item.meta.uuid,
             "date": item.meta.uuid,
             "author": item.meta.author,
             "downloadable": item.meta.downloadable} for item in archive.items])


@app.route("/v1/item", methods=["POST"])
def add_item(self):
    # add new item
    if not request.form.get('name'):
        return InvalidAPIUsage("A Item needs a <str:name>")
    

    item = archive.add_item()
    item.name = request.form.get('name')

    if request.form.get('author') or request.form.get('date')
    return {}


@app.route("/v1/item/<uuid:ID>", methods=["POST"])
def get_all_items(self, ID):
    # change existing item
    return {}


@app.route("/v1/item/<uuid:ID>", methods=["DELETE"])
def get_all_items(self, ID):
    # delete existing item
    return {}


@app.route("/v1/item/<uuid:ID>/document")
def get_all_items(self, ID):
    # get meta data of all documents from existing item
    return {}


@app.route("/v1/item/<uuid:ID>/document", methods=["POST"])
def add_document_to_item(self, ID):
    # add document to  item: <file> needed
    return {}


@app.route("/v1/item/<uuid:ID>/document/<str:name>")
def get_document_to_item(self, name):
    # download document of item
    return {}


@app.route("/v1/item/<uuid:ID>/document/<str:name>", methods=["DELETE"])
def delete_document_of_item(self, name):
    # delete document of item
    return {}


if __name__ == '__main__':
    archive = Archive("../UPLOAD_FOLDER")
    app.run(port=5001, debug=True)
