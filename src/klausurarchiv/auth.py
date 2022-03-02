from flask import Flask, request, make_response
from flask_login import UserMixin, LoginManager, login_user, logout_user
from hashlib import sha256


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
        # TODO: Marshmallow dat shit
        # validate_schema({
        #     "username": str,
            # "password": str
        # }, data)


        #TODO: Use werkzeug.generate_password_hash/check_password_hash
        password_digest = sha256(bytes(data["password"], encoding="utf-8")).hexdigest()
        # TODO: remove or True
        if data["username"] == app.config["USERNAME"] and password_digest == app.config["PASSWORD_SHA256"]: # or True:
            login_user(User(data["username"]))
            return make_response({}, 200)
        else:
            return make_response({"message": "Invalid username or password"}, 401)

    @app.post("/v1/logout")
    def logout():
        logout_user()
        return {}
