BEGIN TRANSACTION;
DROP TABLE IF EXISTS "Items";
CREATE TABLE IF NOT EXISTS "Items" (
	"ID"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"date"	TEXT,
	"visible"	INTEGER NOT NULL DEFAULT 'false',
	PRIMARY KEY("ID" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "Folders";
CREATE TABLE IF NOT EXISTS "Folders" (
	"ID"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "Authors";
CREATE TABLE IF NOT EXISTS "Authors" (
	"ID"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "Courses";
CREATE TABLE IF NOT EXISTS "Courses" (
	"ID"	INTEGER NOT NULL,
	"long_name"	TEXT NOT NULL,
	"short_name"	TEXT NOT NULL,
	PRIMARY KEY("ID" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "Documents";
CREATE TABLE IF NOT EXISTS "Documents" (
	"ID"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"file_id"	TEXT NOT NULL,
	"downloadable"	INTEGER NOT NULL DEFAULT false,
	PRIMARY KEY("ID" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "ItemCourseMap";
CREATE TABLE IF NOT EXISTS "ItemCourseMap" (
	"ItemID"	INTEGER NOT NULL,
	"CourseID"	INTEGER NOT NULL,
	FOREIGN KEY("ItemID") REFERENCES "Items"("ID") ON DELETE CASCADE,
	FOREIGN KEY("CourseID") REFERENCES "Courses"("ID") ON DELETE CASCADE,
	PRIMARY KEY("ItemID","CourseID")
);
DROP TABLE IF EXISTS "ItemAuthorMap";
CREATE TABLE IF NOT EXISTS "ItemAuthorMap" (
	"ItemID"	INTEGER NOT NULL,
	"AuthorID"	INTEGER NOT NULL,
	FOREIGN KEY("AuthorID") REFERENCES "Authors"("ID") ON DELETE CASCADE,
	FOREIGN KEY("ItemID") REFERENCES "Items"("ID") ON DELETE CASCADE,
	PRIMARY KEY("ItemID","AuthorID")
);
DROP TABLE IF EXISTS "ItemDocumentMap";
CREATE TABLE IF NOT EXISTS "ItemDocumentMap" (
	"ItemID"	INTEGER NOT NULL,
	"DocumentID"	INTEGER NOT NULL,
	FOREIGN KEY("ItemID") REFERENCES "Items"("ID") ON DELETE CASCADE ,
	FOREIGN KEY("DocumentID") REFERENCES "Documents"("ID") ON DELETE CASCADE,
	PRIMARY KEY("ItemID","DocumentID")
);
DROP TABLE IF EXISTS "ItemFolderMap";
CREATE TABLE IF NOT EXISTS "ItemFolderMap" (
	"ItemID"	INTEGER NOT NULL,
	"FolderID"	INTEGER NOT NULL,
	FOREIGN KEY("FolderID") REFERENCES "Folders"("ID") ON DELETE CASCADE ,
	FOREIGN KEY("ItemID") REFERENCES "Items"("ID") ON DELETE CASCADE ,
	PRIMARY KEY("ItemID","FolderID")
);
COMMIT;
