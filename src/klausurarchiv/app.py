from flask import Flask, send_file

app = Flask(__name__)

@app.route("/")
def main():
    return "<p>Klausurarchiv</p>"

@app.route("/download/<int:file_uuid>")
def download(file_uuid):
    return send_file("../../Plan.pdf", as_attachment=True)




if __name__ == '__main__':
    app.run(port=5001,debug=True)