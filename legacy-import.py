#!/usr/bin/env python3
# This script reads a legacy database for https://git.cs.uni-paderborn.de/fsmi/fsmi-klausurarchiv
# and sends it's metadata to an instance of the new system.
# It does not send the actual documents, since we were not absolutely sure that the system as safe
# at the time of this writing.
from itertools import chain
from pathlib import Path

import requests
from tqdm import tqdm

SERVER = "https://my.domain/"
USER = "user"
PASSWORD = "topsecret"
OLD_ARCHIVE_FOLDER = Path("path/to/archive/50-fertig")

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

        (course, date, filename, _, authors) = stem.split(" - ")

        name_dict[stem] = course
        course_dict[stem] = course
        date_dict[stem] = date
        author_dict[stem] = set(authors.split("; "))

        if course not in folder_dict:
            folder_dict[stem] = set()
        folder_dict[stem].add(folder_name)

r = requests.post(f"{SERVER}/v1/login", json={"username": USER, "password": PASSWORD})
assert r.status_code == 200
cookies = r.cookies


def create_resources(resource_dict, resource_name, to_json, multi_entries=False):
    if multi_entries:
        resources = chain(*resource_dict.values())
    else:
        resources = resource_dict.values()

    for resource in tqdm(set(resources)):
        r = requests.post(f"{SERVER}/v1/{resource_name}", json=to_json(resource), cookies=cookies)
        assert r.status_code == 201
        resource_id = r.json()["id"]
        for item in resource_dict:
            if multi_entries:
                resource_dict[item] = [resource_id if prev_resource == resource else prev_resource for prev_resource in
                                       resource_dict[item]]
            elif resource_dict[item] == resource:
                resource_dict[item] = resource_id


print("Creating courses...")
create_resources(course_dict, "courses", lambda course: {"long_name": course, "short_name": ""})

print("Creating authors...")
create_resources(author_dict, "authors", lambda name: {"name": name}, multi_entries=True)

print("Creating folders...")
create_resources(folder_dict, "folders", lambda name: {"name": name}, multi_entries=True)

print("Creating items")
for item, name in tqdm(name_dict.items()):
    r = requests.post(
        f"{SERVER}/v1/items",
        json={
            "name": name,
            "date": date_dict[item],
            "documents": [],
            "authors": list(author_dict[item]),
            "courses": [course_dict[item]],
            "folders": list(folder_dict[item]) if item in folder_dict else [],
            "visible": True
        },
        cookies=cookies
    )
    assert r.status_code == 201

assert requests.post(f"{SERVER}/v1/logout", cookies=cookies).status_code == 200
