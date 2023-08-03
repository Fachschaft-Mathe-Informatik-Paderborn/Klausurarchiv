from setuptools import setup, find_packages

setup(
    name="klausurarchiv",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={'': 'src'},
    install_requires=[
        "flask",
        "flask_cors",
        "flask_login",
        "requests",
        "flask_caching",
        "flask_SQLAlchemy",
        "flask_marshmallow",
        "marshmallow-sqlalchemy",
        "psycopg2"
    ]
)