# Klausurarchiv Server

Klausurarchiv is a simple document management system designed for maths and c.s. student council at the Paderborn
University. It is implemented as a [flask](https://flask.palletsprojects.com/en/2.0.x/) web application, providing
a RESTful API via HTTP.

"Klausurarchiv" is German and literally means "exam archive". In the student council, we've only talked about
*the* exam archive and therefore, "Klausurarchiv" was a fitting name. However, it is not the first document
system. It's precursor is [fsmi-klausurarchiv](https://git.cs.uni-paderborn.de/fsmi/fsmi-klausurarchiv), which had
to be replaced since it's managment workflow was too inflexible and couldn't be transformed to an online managment
interface.

## Interacting with a Klausurarchiv instance

The protocol of the Klausurarchiv service is defined in a [separate document](REST-API.md). In a nutshell, there
are several resources, represented as JSON objects, that can be accessed and modified, assuming the user has
proper authorization.

## Deployment

Our current recommendation for deployment is to checkout the repository in `/opt`, install the requirements in
[`requirements.txt`](requirements.txt) for your distribution along with [gunicorn](https://gunicorn.org) and
create a systemd service for it.

## Configuration

Klausurarchiv's configuration is stored in a JSON file. Its path is `/etc/klausurarchiv/config.json`, but its 
directory can be overridden via the `KLAUSURARCHIV_INSTANCE` environment variable. If it doesn't exist during 
launch, a reasonable default is created. Here are some of the configuration values that can be set. Note however 
that these will be directly set as the flask app configuration, so you can also configure the extensions used by 
Klausurarchiv.

### `USERNAME` and `PASSWORD_SHA256`

These are the username and the password that are required to login via the `/v1/login` resource. The password hash 
is supposed to be the sha256 hash of the password in hexadecimal notation.

This simple form of authentification is supposed to be replaced and/or improved soon, so don't rely on it to exist 
forever!

### `SQLALCHEMY_DATABASE_URI`

The URI of the database to use. The default is `sqlite:///:memory:`, which creates a simple database in memory, 
but you could also use `postgresql+psycopg2://klausurarchiv@localhost/klausurarchiv` to use a PostgreSQL database.

### `ACCESS`

These are the IP white- and blocklisting settings. The outer dict may provide rulesets for every `/v1/` resource, as well as for the wildcard resource `*`. These rulesets may either contain the key `allow` or `deny`, which map
to a list of IP networks encoded as strings. A full example:

``` json
{
    "*": {
        "allow": ["0.0.0.0/0", "::/0"],
    },
    "download": {
        "deny": ["10.0.0.1/32"],
    }
}
```

The matcher first tries to find a specialized ruleset for a resource. If it doesn't exist, it tries to find the wildcard ruleset, and if it doesn't exist too, it accepts the request. As said before, a ruleset may either contain the key `allow` or `deny`. If `allow` is used, only IPs from the given networks are accepted, and if `deny` is used, all IPs except those in the given networks are accepted.