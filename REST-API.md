# /v1/archive

## GET: Retrieve the complete archive metadata.

### Request body
``` json
```

### Response body
``` json
{
    "items": [
        {
            "item_id": "int",
            "name": "str",
            "date": "?str",
            "documents": [
                "int", "int"
            ],
            "courses": [
                "int", "int"
            ],
            "authors": [
                "int", "int"
            ],
            "folder": "?int"
        }
    ],
    "documents": [
        {
            "doc_id": "int",
            "name": "int",
            "downloadable": "bool"
        }
    ],
    "courses": [
        {
            "course_id": "int",
            "long_name": "str",
            "short_name": "str"
        }
    ],
    "folders": [
        {
            "folder_id": "int",
            "name": "str"
        }
    ],
    "authors": [
        {
            "author_id": "int",
            "name": "str"
        }
    ]
}
```