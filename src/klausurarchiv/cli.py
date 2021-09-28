import datetime
import sys
from pathlib import Path

import click
from flask import Blueprint
from flask.cli import with_appcontext

from klausurarchiv import db

bp = Blueprint("cli", __name__)


@bp.cli.add_command
@click.command("init-archive")
@with_appcontext
def init_archive_command():
    db.Archive.get_singleton().init_archive()


@bp.cli.add_command
@click.command("legacy-import")
@click.argument("old_archive_path")
@with_appcontext
def legacy_import(old_archive_path: str):
    old_archive_path = Path(old_archive_path)
    complete_folders_path = old_archive_path / Path("50-fertig") / Path("alle-ordner")
    database_path = old_archive_path / Path("90-datenbank")
    if not complete_folders_path.is_dir():
        print(f"{old_archive_path} is not a valid Klausurarchiv archive!", file=sys.stderr)
        sys.exit(1)

    archive = db.Archive.get_singleton()

    author_aliases = dict()
    lectures_aliases_path = database_path / Path("examiners.aliases")
    if lectures_aliases_path.is_file():
        with open(lectures_aliases_path, mode="r") as file:
            for row in file.readlines():
                row = row.split("; ")
                if len(row) == 0:
                    continue
                author = archive.add_author(row[0])
                author_aliases.update(((name, author) for name in row))

    course_aliases = dict()
    lectures_aliases_path = database_path / Path("lectures.aliases")
    if lectures_aliases_path.is_file():
        with open(lectures_aliases_path, mode="r") as file:
            for row in file.readlines():
                row = row.split("; ")
                course = archive.add_course(row[0])
                for alias in row[1:]:
                    course.add_alias(alias)
                course_aliases.update((name, course) for name in row)

    for folder_path in complete_folders_path.iterdir():
        if not folder_path.is_dir():
            continue

        folder_meta = folder_path.name.split(" - ")
        folder_name = f"{folder_meta[0]} ({folder_meta[2]})"
        folder = archive.add_folder(folder_name)

        for file in folder_path.glob("*.pdf"):
            stem = file.name.partition(".pdf")[0]
            item_meta = stem.split(" - ")

            course_name = item_meta[0]
            item = archive.add_item(course_name)
            if course_name in course_aliases.keys():
                item.add_to_course(course_aliases[course_name])
            else:
                course = archive.add_course(course_name)
                course_aliases[course_name] = course
                item.add_to_course(course)

            date = datetime.date.fromisoformat(item_meta[1])
            if date == datetime.date(1907, 1, 1):
                item.date = None
            else:
                item.date = date

            author_name = item_meta[4]
            if author_name == "Unbekannt":
                item.author = None
            else:
                if author_name in author_aliases.keys():
                    item.author = author_aliases[author_name]
                else:
                    author = archive.add_author(author_name)
                    author_aliases[author_name] = author
                    item.author = author

            item.folder = folder

            document = item.add_document(file)
            document_type = item_meta[2]
            document.name = f"{document_type}.pdf"

    archive.commit()
