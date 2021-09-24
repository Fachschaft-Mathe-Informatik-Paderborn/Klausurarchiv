# Classes

## Item

| Attribute     | Type      | Description                                               |
|---------------|-----------|-----------------------------------------------------------|
| `item_id`     | `int`     | Identifier of the item                                    |
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
| `doc_id`          | `int`     | Identifier of the document.                                   |
| `name`            | `str`     | Display name of the document.                                 |
| `downloadable`    | `bool`    | True iff the document is downloadable by unauthorized users.  |

## Course

| Attribute     | Type  | Description                                               |
|---------------|-------|-----------------------------------------------------------|
| `course_id`   | `int` | Identifier of the course.                                 |
| `long_name`   | `str` | The long name of the course, i.e. "Rocket Programming"    |
| `short_name`  | `str` | The short, abbreviated name of the course, i.e. "RS"      |

## Folder

| Attribute     | Type  | Description                                           |
|---------------|-------|-------------------------------------------------------|
| `folder_id`   | `int` | Identifier of the folder.                             |
| `name`        | `str` | Display name of the folder as printed on the label.   |

## Author

| Attribute     | Type  | Description               |
|---------------|-------|---------------------------|
| `author_id`   | `int` | Identifier of the author. |
| `name`        | `str` | Full name of the author.  |

# Resources

## `GET /v1/items`

Get items from the archive. 

Without authorization, invisible items will automatically excluded. Also note that not all requested items may be delivered, for example because the client lacks authorization or because the item simply does not exist.

### Request format:

| Attribute     | Type      | Description                                                   |
|---------------|-----------|---------------------------------------------------------------|
| `item_ids`    | `[int]`   | List of item IDs to get. If empty, all items will be fetched. |

### Response format

| Attribute | Type      | Description                       |
|-----------|-----------|-----------------------------------|
| `items`   | `[Item]`  | List of requested items.|

## `GET /v1/items/<id:int>`

