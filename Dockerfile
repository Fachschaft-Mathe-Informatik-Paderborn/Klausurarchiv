FROM python:3.7.13-bullseye

WORKDIR /server
COPY . /server

RUN pip install -r requirements.txt
RUN pip install gunicorn

ENTRYPOINT ["gunicorn", "klausurarchiv:create_app()", "--pythonpath", "/server/src", "-b", "0.0.0.0:8000"]

