from flask import Flask, send_file, request, render_template, jsonify
from pathlib import Path

from model import *

app = Flask(__name__, template_folder="../html")

app.config["UPLOAD_FOLDER"] = "../UPLOAD_FOLDER"
app.config["MAX_CONTENT_PATH"] = 10**6 * 300 # TODO 300MB


@app.route("/")
def main():
    return "Klausurarchiv"


@app.route("/exams")
def list_items():
    return json.dumps({
        "name":"EK",
        "author": "Roland",
        "documents": [str(document.path.name) for document in demo_item.documents]
    })

@app.route("/download/<int:file_uuid>")
def download(file_uuid):
    return send_file("../../Plan.pdf", as_attachment=True)


@app.route("/upload")
def upload():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    file.save(Path(app.config["UPLOAD_FOLDER"]) / Path(file.filename))
    return render_template("upload_status.html", status="Erfolgreich hochgeladen!")


if __name__ == '__main__':
    demo_item = Item(Path("../UPLOAD_FOLDER"))
    app.run(port=5001, debug=True)
