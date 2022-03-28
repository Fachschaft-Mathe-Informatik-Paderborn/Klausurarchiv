#!/usr/bin/env python3
# This script reads a legacy database for https://git.cs.uni-paderborn.de/fsmi/fsmi-klausurarchiv
# and sends it's metadata to an instance of the new system.
# It does not send the actual documents, since we were not absolutely sure that the system as safe
# at the time of this writing.
from itertools import chain
from pathlib import Path
import argparse

import requests
from tqdm import tqdm

parser = argparse.ArgumentParser(
    description="Transport item metadata from an old archive to a new one")
parser.add_argument("-s", "--server", type=str, nargs=1,
                    help="The URL via which the archive is available")
parser.add_argument("-u", "--user", type=str, nargs=1,
                    help="The username to use for authentication")
parser.add_argument("-p", "--password", type=str, nargs=1,
                    help="The password fo use for authentication")
parser.add_argument("-a", "--archive", type=Path, nargs=1,
                    help="The path to the old archive, ending in '50-fertig'")
args = parser.parse_args()

SERVER = args.server[0]
USER = args.user[0]
PASSWORD = args.password[0]
OLD_ARCHIVE_FOLDER = args.archive[0]

r = requests.post(f"{SERVER}/v1/login",
                  json={"username": USER, "password": PASSWORD})
assert r.status_code == 200
cookies = r.cookies

courses = {value["long_name"]: key for key, value in requests.get(
    f"{SERVER}/v1/courses", cookies=cookies).json().items()}
authors = {value["name"]: key for key, value in requests.get(
    f"{SERVER}/v1/authors", cookies=cookies).json().items()}
folders = {value["name"]: key for key, value in requests.get(
    f"{SERVER}/v1/authors", cookies=cookies).json().items()}

for folder_path in tqdm(list((OLD_ARCHIVE_FOLDER / Path("alle-ordner")).iterdir())):
    if not folder_path.is_dir():
        continue

    folder_name = folder_path.name.split(" - ")
    folder_name = folder_name[0] + " - " + folder_name[1]

    if folder_name not in folders:
        r = requests.post(f"{SERVER}/v1/folders",
                          json={"name": folder_name}, cookies=cookies)
        assert r.status_code == 201
        folders[folder_name] = r.json()["id"]
    folder_id = folders[folder_name]

    for item_path in folder_path.glob("*.pdf"):
        stem = item_path.stem

        (course_names, date, filename, _, author_names) = stem.split(" - ")

        name = course_names

        course_ids = list()
        for course_name in set(course_names.split("; ")):
            if course_name not in courses:
                r = requests.post(f"{SERVER}/v1/courses",
                                  json={"long_name": course_name, "short_name": ""}, cookies=cookies)
                assert r.status_code == 201
                courses[course_name] = r.json()["id"]
            course_ids.append(courses[course_name])

        author_ids = list()
        for author_name in set(author_names.split("; ")):
            if author_name not in authors:
                r = requests.post(f"{SERVER}/v1/authors",
                                  json={"name": author_name}, cookies=cookies)
                assert r.status_code == 201
                authors[author_name] = r.json()["id"]
            author_ids.append(authors[author_name])

        if item_path.exists():
            r = requests.post(f"{SERVER}/v1/documents",
                            json={"filename": "Klausur.pdf", "downloadable": False, "content_type": "application/pdf"}, cookies=cookies)
            assert r.status_code == 201
            document_id = r.json()["id"]

            r = requests.post(
                f"{SERVER}/v1/upload?id={document_id}",
                data=open(item_path, mode="rb"),
                headers={
                    "Content-type": "application/pdf"
                },
                cookies=cookies
            )
            assert r.status_code == 200
        else:
            document_id = None

        r = requests.post(
            f"{SERVER}/v1/items",
            json={
                "name": name,
                "date": date,
                "documents": [document_id] if document_id is not None else [],
                "authors": author_ids,
                "courses": course_ids,
                "folders": [folder_id],
                "visible": True
            },
            cookies=cookies
        )
        if r.status_code != 201:
            print(r.json())
        assert r.status_code == 201