# Classes

## Item

| Attribute     | Type      | Description                                               |
|---------------|-----------|-----------------------------------------------------------|
| `name`        | `str`     | Display name of the item                                  |
| `date`        | `str`     | Associated date of the item, in iso format: YYYY-MM-DD    |
| `documents`   | `[int]`   | List of associated document IDs.                          |
| `authors`     | `[int]`   | List of associated author IDs.                            |
| `courses`     | `[int]`   | List of associated course IDs.                            |
| `folders`     | `[int]`   | List of associated folder IDs.                            |
| `visible`     | `bool`    | True iff the item is visible to unauthorized users.       |

## Document

| Attribute         | Type      | Description                                                   |
|-------------------|-----------|---------------------------------------------------------------|
| `name`            | `str`     | Display name of the document.                                 |
| `downloadable`    | `bool`    | True iff the document is downloadable by unauthorized users.  |
| `file_id`         | `str`     | Identifier of the document's file.                            |

## Course

| Attribute     | Type  | Description                                               |
|---------------|-------|-----------------------------------------------------------|
| `long_name`   | `str` | The long name of the course, i.e. "Rocket Programming"    |
| `short_name`  | `str` | The short, abbreviated name of the course, i.e. "RS"      |

## Folder

| Attribute     | Type  | Description                                           |
|---------------|-------|-------------------------------------------------------|
| `name`        | `str` | Display name of the folder as printed on the label.   |

## Author

| Attribute     | Type  | Description               |
|---------------|-------|---------------------------|
| `name`        | `str` | Full name of the author.  |

# Resources

The database queries all follow the same scheme: There is a request to get all resources of a certain class and there are requests to get, create, modify and delete a specific resource. The following resource classes are available under the following URLs:

| Class | URL |
|-|-|
| Item | `/v1/items` |
| Document | `/v1/documents` |
| Course | `/v1/courses` |
| Folder | `/v1/folders` |
| Author | `/v1/authors` |

## `GET /v1/<resource>s`

Get all resources from the archive.

### Request:

The body is an empty object.

### Response 200 "Ok":

The query was successful. The body is an object of type `{int:ResourceClass}`, where resource IDs are mapped to resources. Note that the selection of returned resources may be different depending on the client's authorization.

### Response 500 "Internal Server Error":

An internal error occurred. The body is an empty object.

## `GET /v1/<resource>s/<id:int>`

Get a specific resource from the archive.

### Request:

The body is an empty object.

### Response 200 "Ok":

The query was successful. The body is a `ResourceClass` object.

### Response 404 "Not Found":

The requested resource does not exist. The body is an empty object.

### Response 401 "Unauthorized":

The client lacks authorization to access the resource, usually because the client is not logged in and the resource is invisible.

### Response 500 "Internal Server Error":

An internal error occurred. The body is an empty object.

## `POST /v1/<resource>s/`

Create a new resource.

### Request:

The body is a `ResourceClass` object.

### Response 201 "Created":

The resource was created. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `id` | `int` | The ID of the newly created resource. The new resource will be available as `/v1/<resource>s/<id>`.

### Response 400 "Bad Request":

The request body is not a well-formed resource. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem, i.e. which attribute is missing or which reference is illegal. |

### Response 401 "Unauthorized":

The client lacks authorization to create an resource.

### Response 500 "Internal Server Error":

An internal error occurred. The body is an empty object. The body is an empty object.

## `PUT /v1/<resource>s/<id:int>`

Set the meta-data of an resource, create it if necessary.

### Request:

The body is a `ResourceClass` object.

### Response 200 "Ok":

The resource existed before and it's contents were replaced. The body is an empty object.

### Response 201 "Created":

The resource didn't exist before and it was created. The body is an empty object.

### Response 400 "Bad Request":

The request body is not a well-formed resource. The body is an object of the following schema:

| Attribute | Type | Description |
|-|-|-|
| `message` | `str` | A short description of the problem, i.e. which attribute is missing or which reference is illegal. |

### Response 401 "Unauthorized":

The client lacks authorization to create or update an resource. The body is an empty object.

### Response 500 "Internal Server Error":

An internal error occurred. The body is an empty object.

## `DELETE /v1/<resource>s/<id:int>`

Delete an resource from the archive.

### Request:

The body is an empty object.

### Response 200 "Ok":

The query was successful. The body is a `ResourceClass` object.

### Response 404 "Not Found":

The requested resource does not exist. The body is an empty object.

### Response 401 "Unauthorized":

The client lacks authorization to delete the resource, usually because the client is not logged in and the resource is invisible.

### Response 500 "Internal Server Error":

An internal error occurred. The body is an empty object.
