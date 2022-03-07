from flask import Flask, request, make_response
from flask_login import UserMixin, LoginManager, login_user, logout_user
from hashlib import sha256

from marshmallow import Schema, fields
from marshmallow import ValidationError


class User(UserMixin):
    """
    A currently logged in user.

    Possesses an unique id and mainly implements the UserMixin.
    """
    def __init__(self, user_id: str):
        self.__user_id = user_id

    def get_id(self) -> str:
        return self.__user_id


def init_app(app: Flask):
    """
    Initializes the application by exposing login and logout endpoints for authorization.
    """
    login_manager = LoginManager()

    @login_manager.user_loader
    def load_user(user_id):
        return User(user_id)

    login_manager.init_app(app)

    @app.post("/v1/login")
    def login():
        data = request.get_json()

        class CredentialsSchema(Schema):
            username = fields.Str()
            password = fields.Str()

        try:
            credentials = CredentialsSchema().load(data)
        except ValidationError as err:
            return {"message": err.messages}, 400

        password_digest = sha256(bytes(credentials["password"], encoding="utf-8")).hexdigest()
        if credentials["username"] == app.config["USERNAME"] and password_digest == app.config["PASSWORD_SHA256"]:
            login_user(User(credentials["username"]))
            return make_response({}, 200)
        else:
            return make_response({"message": "Invalid username or password"}, 401)

    @app.post("/v1/logout")
    def logout():
        logout_user()
        return {}
