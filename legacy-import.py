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

name_dict = dict()
course_dict = dict()
date_dict = dict()
author_dict = dict()
folder_dict = dict()

for folder_path in (OLD_ARCHIVE_FOLDER / Path("alle-ordner")).iterdir():
    if not folder_path.is_dir():
        continue

    folder_name = folder_path.name.split(" - ")
    folder_name = folder_name[0] + " - " + folder_name[1]
    for item_path in folder_path.glob("*.pdf"):
        stem = item_path.stem

        (courses, date, filename, _, authors) = stem.split(" - ")

        name_dict[stem] = courses
        course_dict[stem] = set(courses.split("; "))
        date_dict[stem] = date
        author_dict[stem] = set(authors.split("; "))
        folder_dict[stem] = folder_name

r = requests.post(f"{SERVER}/v1/login",
                  json={"username": USER, "password": PASSWORD})
assert r.status_code == 200
cookies = r.cookies


def create_resources(resource_dict, resource_name, to_json, multi_entries=False):
    if multi_entries:
        resources = chain(*resource_dict.values())
    else:
        resources = resource_dict.values()

    resource_ids = dict()

    for resource in tqdm(set(resources)):
        r = requests.post(f"{SERVER}/v1/{resource_name}",
                          json=to_json(resource), cookies=cookies)
        assert r.status_code == 201
        resource_ids[resource] = r.json()["id"]

    return resource_ids


print("Creating authors...")
author_ids = create_resources(author_dict, "authors", lambda name: {
                              "name": name}, multi_entries=True)

print("Creating courses...")
course_ids = create_resources(course_dict, "courses", lambda course: {
                              "long_name": course, "short_name": ""}, multi_entries=True)

print("Creating folders...")
folder_ids = create_resources(folder_dict, "folders", lambda name: {
                              "name": name}, multi_entries=False)

print("Creating items")
for item, name in tqdm(name_dict.items()):
    r = requests.post(
        f"{SERVER}/v1/items",
        json={
            "name": name,
            "date": date_dict[item],
            "documents": [],
            "authors": [author_ids[author] for author in author_dict[item]],
            "courses": [course_ids[course] for course in course_dict[item]],
            "folders": [folder_ids[folder_dict[item]]],
            "visible": True
        },
        cookies=cookies
    )
    if r.status_code != 201:
        print(r.json())
    assert r.status_code == 201

assert requests.post(f"{SERVER}/v1/logout", cookies=cookies).status_code == 200
