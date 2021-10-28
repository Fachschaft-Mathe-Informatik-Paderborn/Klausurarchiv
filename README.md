# Klausurarchiv Server

Klausurarchiv is a simple document management system designed for maths and c.s. student council at the Paderborn University. It is implemented as a [flask](https://flask.palletsprojects.com/en/2.0.x/) web application, providing a RESTful API via HTTP.

"Klausurarchiv" is German and literally means "exam archive". In the student council, we've only talked about *the* exam archive and therefore, "Klausurarchiv" was a fitting name. However, it is not the first document system. It's precursor is [fsmi-klausurarchiv](https://git.cs.uni-paderborn.de/fsmi/fsmi-klausurarchiv), which had to be replaced since it's managment workflow was too inflexible and couldn't be transformed to an online managment interface.

## Interacting with a Klausurarchiv instance

The protocol of the Klausurarchiv service is defined in a [separate document](REST-API.md). In a nutshell, there are several resources, represented as JSON objects, that can be accessed and modified, assuming the user as proper authorization.

## Deploying Klausurarchiv

Klausurarchiv's deployment is still work in progress. Our current recommendation is to checkout the repository in `/opt`, install the requirements in [`requirements.txt`](requirements.txt) for your distribution along with [gunicorn](https://gunicorn.org) and create a systemd service for it.

Better deployment options and instructions are work in progress.

