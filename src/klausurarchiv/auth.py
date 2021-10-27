from flask import Flask, request, make_response
from flask_login import UserMixin, LoginManager, login_user, logout_user
from hashlib import sha256

from klausurarchiv.db import validate_schema


class User(UserMixin):
    def __init__(self, user_id: str):
        self.__user_id = user_id

    def get_id(self) -> str:
        return self.__user_id


def init_app(app: Flask):
    login_manager = LoginManager()

    @login_manager.user_loader
    def load_user(user_id):
        return User(user_id)

    login_manager.init_app(app)

    @app.post("/v1/login")
    def login():
        data = request.get_json()
        validate_schema({
            "username": str,
            "password": str
        }, data)

        password_digest = sha256(bytes(data["password"], encoding="utf-8")).hexdigest()
        if data["username"] == app.config["USERNAME"] and password_digest == app.config["PASSWORD_SHA256"]:
            login_user(User(data["username"]))
            response = make_response({}, 200)
            # TODO: This might be dangerous, but otherwise our webapp doesn't work
            # and I don't know enough to properly evaluate the risk.
            response.access_control_allow_credentials = True
            return response
        else:
            return make_response({"message": "Invalid username or password"}, 401)

    @app.post("/v1/logout")
    def logout():
        logout_user()
        return {}
