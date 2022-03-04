from datetime import datetime
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import inspect, SQLAlchemy
from marshmallow import validates, ValidationError
from werkzeug.utils import secure_filename

db = SQLAlchemy()
ma = Marshmallow()

# Links between objects
courses = db.Table('ItemCourseMap',
                   db.Column('item_id', db.Integer, db.ForeignKey('item.id'), primary_key=True),
                   db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
                   )

authors = db.Table('ItemAuthorMap',
                   db.Column('author_id', db.Integer, db.ForeignKey('author.id'), primary_key=True),
                   db.Column('item_id', db.Integer, db.ForeignKey('item.id'), primary_key=True)
                   )

documents = db.Table('ItemDocumentMap',
                     db.Column('item_id', db.Integer, db.ForeignKey('item.id'), primary_key=True),
                     db.Column('document_id', db.Integer, db.ForeignKey('document.id'), primary_key=True)
                     )

folders = db.Table('ItemFolderMap',
                   db.Column('folder_id', db.Integer, db.ForeignKey('folder.id'), primary_key=True),
                   db.Column('item_id', db.Integer, db.ForeignKey('item.id'), primary_key=True)
                   )


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    downloadable = db.Column(db.Boolean, nullable=False, default=False)
    content_type = db.Column(db.String(120), nullable=False)

    file = db.Column(db.LargeBinary, nullable=True)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    long_name = db.Column(db.String(120), nullable=False)
    short_name = db.Column(db.String(60), nullable=False)


class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=True)
    visible = db.Column(db.Boolean, nullable=False, default=False)

    courses = db.relationship('Course', secondary=courses, lazy='subquery',
                              backref=db.backref('items', lazy=True))
    authors = db.relationship('Author', secondary=authors, lazy='subquery',
                              backref=db.backref('items', lazy=True))
    documents = db.relationship('Document', secondary=documents, lazy='subquery',
                                backref=db.backref('items', lazy=True))
    folders = db.relationship('Folder', secondary=folders, lazy='subquery',
                              backref=db.backref('items', lazy=True))


class DocumentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Document
        # dump_only = ("id",)  # ids are given by database and cannot be controlled by user
        exclude = ("id", "file",)  # file supplied via separate endpoint, ids are exposed through mapping
        ordered = True

    @validates("filename")
    def filename_is_secure(self, filename):
        if secure_filename(filename) != filename or len(secure_filename(filename)) == 0:
            raise ValidationError("Insecure filename")

class CourseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Course
        # dump_only = ("id",)  # ids are given by database and cannot be controlled by user
        exclude = ("id", ) # ids are exposed via mapping
        ordered = True


class FolderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Folder
        # dump_only = ("id",)  # ids are given by database and cannot be controlled by user
        exclude = ("id", ) # ids are exposed via mapping
        ordered = True


class AuthorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Author
        # dump_only = ("id",)  # ids are given by database and cannot be controlled by user
        exclude = ("id", ) # ids are exposed via mapping
        ordered = True


class ItemSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Item
        # dump_only = ("id",)  # ids are given by database and cannot be controlled by user
        exclude = ("id", ) # ids are exposed via mapping
        include_relationships = True  # Item links between resources, so we want to include their primary keys each time
        ordered = True
        dateformat = "%Y-%m-%d"  # export time format consistently

    # requests may supply invalid (or later non-public) foreign keys - these will be read in as transient objects
    @validates("authors")
    def authors_exist(self, given_authors):
        for author in given_authors:
            if inspect(author).transient:
                raise ValidationError(f"Author with id {author.id} does not exist.")

    @validates("folders")
    def folders_exist(self, given_folders):
        for folder in given_folders:
            if inspect(folder).transient:
                raise ValidationError(f"Folder with id {folder.id} does not exist.")

    @validates("documents")
    def documents_exist(self, given_documents):
        for document in given_documents:
            if inspect(document).transient:
                raise ValidationError(f"Document with id {document.id} does not exist.")

    @validates("courses")
    def courses_exist(self, given_courses):
        for course in given_courses:
            if inspect(course).transient:
                raise ValidationError(f"Course with id {course.id} does not exist.")


# multiple schemas required to differentiate collections of an object versus single objects
document_schema = DocumentSchema()

course_schema = CourseSchema()

folder_schema = FolderSchema()

author_schema = AuthorSchema()

item_schema = ItemSchema()
