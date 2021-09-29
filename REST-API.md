# Classes

## Item

| Attribute     | Type      | Default   | Description                                               |
|---------------|-----------|-----------|-----------------------------------------------------------|
| `name`        | `str`     | `null`    | Display name of the item                                  |
| `date`        | `str`     | `null`    | Associated date of the item, in iso format: YYYY-MM-DD    |
| `documents`   | `[int]`   | `[]`      | List of associated document IDs.                          |
| `authors`     | `[int]`   | `[]`      | List of associated author IDs.                            |
| `courses`     | `[int]`   | `[]`      | List of associated course IDs.                            |
| `folders`     | `[int]`   | `[]`      | List of associated folder IDs.                            |
| `visible`     | `bool`    | `false`   | True iff the item is visible to unauthorized users.       |

## Document

| Attribute         | Type      | Default       | Description                                                   |
|-------------------|-----------|---------------|---------------------------------------------------------------|
| `filename`        | `str`     | `null`        | Filename of the document.                                     |
| `downloadable`    | `bool`    | `false`       | True iff the document is downloadable by unauthorized users.  |
| `content-type`    | `str`     | `text/plain`  | The [media type](https://en.wikipedia.org/wiki/Media_type) of the document. |

Only the following content types are allowed:

* `application/msword`
* `application/pdf`
* `application/x-latex`
* `image/png`
* `image/jpeg`
* `image/gif`
* `text/plain`

## Course

| Attribute     | Type  | Default   | Description                                               |
|---------------|-------|-----------|-----------------------------------------------------------|
| `long_name`   | `str` | `null`    | The long name of the course, i.e. "Rocket Programming"    |
| `short_name`  | `str` | `null`    | The short, abbreviated name of the course, i.e. "RS"      |

## Folder

| Attribute     | Type  | Default   | Description                                           |
|---------------|-------|-----------|-------------------------------------------------------|
| `name`        | `str` | `null`    | Display name of the folder as printed on the label.   |

## Author

| Attribute     | Type  | Default   | Description               |
|---------------|-------|-----------|---------------------------|
| `name`        | `str` | `null`    | Full name of the author.  |

# Login and Authorization

The Klausurarchiv server requires authorization for certain requests. This authorization is provided with the following endpoints and is stored in the `KLAUSURARCHIV` cookie. This cookie should be set in all requests since it is used to check the authorization of the user.

## `POST /v1/login`

Log into the server. The check may be performed with a local password database or with an external authentication service.

### Request

The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `username` | `str` | The username of the user. |
| `password` | `str` | The password of the user. |

### Response 200 "Ok"

The login was successful and the session information is stored in the `KLAUSURARCHIV` cookie. If the user was logged in before, they were first logged out and is now logged in with the new information. The body is an empty object.

### Response 400 "Bad Request"

The request body is malformed. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 401 "Unauthorized"

The provided username and/or password is wrong, or the user is not authorized to login. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 500 "Internal Server Error"

An internal error occurred. The body is an empty object. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

## `POST /v1/logout`

Log out of the server.

### Request

The body is an empty object.

### Response 200 "Ok"

The logout was successful and the session information is removed from the `KLAUSURARCHIV` cookie. This response will also be sent if the user wasn't logged in before as the resulting state is the same.

### Response 500 "Internal Server Error"

An internal error occurred. The body is an empty object. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

# Resources

The database queries all follow the same scheme: There is a request to get all resources of a certain class and there are requests to get, create, modify and delete a specific resource. The following resource classes are available under the following locations:

| Class | Location |
|-|-|
| Item | `/v1/items` |
| Document | `/v1/documents` |
| Course | `/v1/courses` |
| Folder | `/v1/folders` |
| Author | `/v1/authors` |

Access to certain resources may be restricted depending on the resource class and the client's authorization:

* Courses, Folders, and Authors are always retrievable by anyone.
* A document is retrievable iff the user is logged in and is authorized to retrieve all downloads, or the document belongs to a visible item.
* An item is retrievable iff the user is logged in and is authorized to retrieve all items, or the item is visible.

The creation, modification and deletion of resources is only possible by users that are logged in and are authorized to do so.

## `GET /v1/<resource>s`

Get all resources from the archive.

### Request

The body is an empty object.

### Response 200 "Ok"

The query was successful. The body is an object of type `{int:ResourceClass}`, where resource IDs are mapped to resources. Resources the user is not authorized to access are not included and therefore, the response may be different depending on the class and client's authorization.

### Response 500 "Internal Server Error"

An internal error occurred. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

## `GET /v1/<resource>s/<id:int>`

Get a specific resource from the archive.

### Request

The body is an empty object.

### Response 200 "Ok"

The query was successful. The body is a `ResourceClass` object.

### Response 404 "Not Found"

The requested resource does not exist. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 401 "Unauthorized"

The client lacks authorization to access the resource. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 500 "Internal Server Error"

An internal error occurred. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

## `POST /v1/<resource>s/`

Create a new resource.

### Request

The body is a `ResourceClass` object.

### Response 201 "Created"

The resource was created. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `id` | `int` | The ID of the newly created resource. The new resource will be available as `/v1/<resource>s/<id>`.

### Response 400 "Bad Request"

The request body is not a well-formed resource. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem, i.e. which attribute is missing or which reference is illegal. |

### Response 401 "Unauthorized"

The client lacks authorization to create an resource. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 500 "Internal Server Error"

An internal error occurred. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

## `PUT /v1/<resource>s/<id:int>`

Update a resource, create it if necessary.

### Request

The body is a `ResourceClass` object.

### Response 200 "Ok"

The resource existed before and it's contents were replaced. The body is an empty object.

### Response 201 "Created"

The resource didn't exist before and it was created. The body is an empty object.

### Response 400 "Bad Request"

The request body is not a well-formed resource. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem, i.e. which attribute is missing or which reference is illegal. |

### Response 401 "Unauthorized"

The client lacks authorization to create or update an resource. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 500 "Internal Server Error"

An internal error occurred. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

## `DELETE /v1/<resource>s/<id:int>`

Delete an resource from the archive.

### Request

The body is an empty object.

### Response 200 "Ok"

The query was successful. The body is a `ResourceClass` object.

### Response 404 "Not Found"

The requested resource does not exist. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 401 "Unauthorized"

The client lacks authorization to delete the resource, usually because the client is not logged in and the resource is invisible. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 500 "Internal Server Error"

An internal error occurred. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

# Document content up- and downloads

While documents are represented as the `/v1/documents` resource, it only provides metadata information. The actual contents are up- and downloaded at separate endpoints. Downloading documents is possible iff the user is logged in and is authorized to download all documents, or the document belongs to a downloadable document of a visible item. Uploading documents is only possible by authorized users.

## `POST /v1/upload`

Upload a document's content to the server.

### Request

| Query Parameter | Type | Description |
|-|-|-|
| `id` | `int` | The ID of the document to upload. If the document doesn't exist, it is created. |

The body of an upload request is exactly the document's content.

### Response 200 "Ok"

The file was successfully uploaded. The body is empty.

### Response 401 "Unauthorized"

The client lacks authorization to upload the document. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 500 "Internal Server Error"

An internal error occurred. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

## `GET /v1/download`

Download the requested document.

### Request

| Query Parameter | Type | Description |
|-|-|-|
| `id` | `int` | The ID of the document to download. |

The body may be empty.

### Response 200 "Ok"

The body of the response is the content of the requested document. The following headers will be set:

| Header | Description |
|-|-|
| `Content-Type` | The content type of the document. |
| `Content-Disposition` | Set to `attachment`, with the filename. |

### Response 401 "Unauthorized"

The client lacks the authorization to download the document.

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 404 "Not Found"

The requested document does not exist. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |

### Response 500 "Internal Server Error"

An internal error occurred. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem. |