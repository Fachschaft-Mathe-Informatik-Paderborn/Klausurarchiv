BEGIN TRANSACTION;
DROP TABLE IF EXISTS "Items";
CREATE TABLE IF NOT EXISTS "Items"
(
    "ID"      INTEGER NOT NULL,
    "name"    TEXT    NOT NULL,
    "date"    TEXT,
    "visible" INTEGER NOT NULL DEFAULT 'false',
    PRIMARY KEY ("ID" AUTOINCREMENT)
);

DROP TABLE IF EXISTS "Folders";
CREATE TABLE IF NOT EXISTS "Folders"
(
    "ID"   INTEGER NOT NULL,
    "name" TEXT    NOT NULL,
    PRIMARY KEY ("ID" AUTOINCREMENT)
);

DROP TABLE IF EXISTS "Authors";
CREATE TABLE IF NOT EXISTS "Authors"
(
    "ID"   INTEGER NOT NULL,
    "name" TEXT    NOT NULL,
    PRIMARY KEY ("ID" AUTOINCREMENT)
);

DROP TABLE IF EXISTS "Courses";
CREATE TABLE IF NOT EXISTS "Courses"
(
    "ID"         INTEGER NOT NULL,
    "long_name"  TEXT    NOT NULL,
    "short_name" TEXT    NOT NULL,
    PRIMARY KEY ("ID" AUTOINCREMENT)
);

DROP TABLE IF EXISTS "Documents";
CREATE TABLE IF NOT EXISTS "Documents"
(
    "ID"           INTEGER NOT NULL,
    "filename"     TEXT    NOT NULL,
    "content_type" TEXT    NOT NULL,
    "downloadable" INTEGER NOT NULL DEFAULT false,
    PRIMARY KEY ("ID" AUTOINCREMENT)
);

DROP TABLE IF EXISTS "ItemCourseMap";
CREATE TABLE IF NOT EXISTS "ItemCourseMap"
(
    "ItemID"   INTEGER NOT NULL,
    "CourseID" INTEGER NOT NULL,
    FOREIGN KEY ("ItemID") REFERENCES "Items" ("ID") ON DELETE CASCADE,
    FOREIGN KEY ("CourseID") REFERENCES "Courses" ("ID") ON DELETE CASCADE,
    PRIMARY KEY ("ItemID", "CourseID")
);

DROP TABLE IF EXISTS "ItemAuthorMap";
CREATE TABLE IF NOT EXISTS "ItemAuthorMap"
(
    "ItemID"   INTEGER NOT NULL,
    "AuthorID" INTEGER NOT NULL,
    FOREIGN KEY ("AuthorID") REFERENCES "Authors" ("ID") ON DELETE CASCADE,
    FOREIGN KEY ("ItemID") REFERENCES "Items" ("ID") ON DELETE CASCADE,
    PRIMARY KEY ("ItemID", "AuthorID")
);

DROP TABLE IF EXISTS "ItemDocumentMap";
CREATE TABLE IF NOT EXISTS "ItemDocumentMap"
(
    "ItemID"     INTEGER NOT NULL,
    "DocumentID" INTEGER NOT NULL,
    FOREIGN KEY ("ItemID") REFERENCES "Items" ("ID") ON DELETE CASCADE,
    FOREIGN KEY ("DocumentID") REFERENCES "Documents" ("ID") ON DELETE CASCADE,
    PRIMARY KEY ("ItemID", "DocumentID")
);

DROP TABLE IF EXISTS "ItemFolderMap";
CREATE TABLE IF NOT EXISTS "ItemFolderMap"
(
    "ItemID"   INTEGER NOT NULL,
    "FolderID" INTEGER NOT NULL,
    FOREIGN KEY ("FolderID") REFERENCES "Folders" ("ID") ON DELETE CASCADE,
    FOREIGN KEY ("ItemID") REFERENCES "Items" ("ID") ON DELETE CASCADE,
    PRIMARY KEY ("ItemID", "FolderID")
);

CREATE VIEW IF NOT EXISTS VisibleItems as
select *
from Items
where visible = 1;

CREATE VIEW IF NOT EXISTS VisibleDocuments as
select *
from Documents
where ID in (
    select IDM.DocumentID
    from ItemDocumentMap as IDM
             inner join VisibleItems as Items
                        on IDM.ItemID == Items.ID
);

create view JoinedItemDocumentMap as
select Items.ID as ItemID, Map.DocumentID as DocumentID
from Items
         left join ItemDocumentMap as Map on Items.ID = Map.ItemID
order by ItemID;

create view JoinedItemAuthorMap as
select Items.ID as ItemID, Map.AuthorID as AuthorID
from Items
         left join ItemAuthorMap as Map on Items.ID = Map.ItemID
order by ItemID;

create view JoinedItemCourseMap as
select Items.ID as ItemID, Map.CourseID as CourseID
from Items
         left join ItemCourseMap as Map on Items.ID = Map.ItemID
order by ItemID;

create view JoinedItemFolderMap as
select Items.ID as ItemID, Map.FolderID as FolderID
from Items
         left join ItemFolderMap as Map on Items.ID = Map.ItemID
order by ItemID;

COMMIT;
