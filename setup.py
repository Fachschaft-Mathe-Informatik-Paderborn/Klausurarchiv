from setuptools import setup

setup(
    name="klausurarchiv",
    version="0.0.1",
    package_dir={
        "klausurarchiv": "src/klausurarchiv"
    },
    packages=["klausurarchiv"],
    python_requires=">=3.9",
    install_requires=["flask", "flask_cors"],
    package_data={
        "klausurarchiv": ["schema.sql"]
    }
)