from setuptools import setup, find_packages

setup(
    name="klausurarchiv",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={'': 'src'},
    install_requires=[
        "flask~=2.3.2",
        "flask_cors~=3.0.0",
        "flask_login~=0.6.0",
        "requests~=2.30.0",
        "flask_caching~=2.0.0",
        "flask_SQLAlchemy~=3.0.0",
        "flask_marshmallow~=0.15.0",
        "marshmallow-sqlalchemy~=0.29.0",
        "psycopg2~=2.9.0"
    ]
)