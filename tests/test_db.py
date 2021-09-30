import datetime
import tempfile

from klausurarchiv.db import *


class TestDocument(object):
    def test_document(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            assert archive.documents == []

            doc = archive.add_document({
                "filename": "doc_a.txt",
                "downloadable": True,
                "content-type": "text/plain"
            })

            with open(doc.path, mode="w") as f:
                f.write("Hello World\n")

            assert doc.filename == "doc_a.txt"
            assert doc.downloadable
            assert doc.content_type == "text/plain"

            with open(doc.path, mode="r") as f:
                assert "Hello World\n" == f.readline()

            doc.filename = "doc_b.tex"
            doc.downloadable = False
            doc.content_type = "application/x-latex"

            with open(doc.path, mode="w") as f:
                f.write("foobar\n")

            assert doc.filename == "doc_b.tex"
            assert not doc.downloadable
            assert doc.content_type == "application/x-latex"

            with open(doc.path, mode="r") as f:
                assert "foobar\n" == f.readline()


class TestCourse(object):
    def test_course(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            course = archive.add_course({
                "long_name": "Rocket Science",
                "short_name": "RS"
            })

            assert course.long_name == "Rocket Science"
            assert course.short_name == "RS"

            course.long_name = "Foundations of Rocket Science"
            course.short_name = "FRS"

            assert course.long_name == "Foundations of Rocket Science"
            assert course.short_name == "FRS"


class TestFolder(object):
    def test_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            folder = archive.add_folder({
                "name": "Rocket Science"
            })

            assert folder.name == "Rocket Science"

            folder.name = "Foundations of Rocket Science"
            assert folder.name == "Foundations of Rocket Science"


class TestAuthor(object):
    def test_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            author = archive.add_author({
                "name": "Dr. Jane Doe"
            })
            assert author.name == "Dr. Jane Doe"

            author.name = "Prof. Dr. Jane Doe"
            assert author.name == "Prof. Dr. Jane Doe"


class TestItem(object):
    def test_item(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            doc_a = archive.add_document({
                "filename": "exam.pdf",
                "downloadable": True,
                "content-type": "application/pdf"
            })
            doc_b = archive.add_document({
                "filename": "solution.pdf",
                "downloadable": True,
                "content-type": "application/pdf"
            })
            folder_a = archive.add_folder({
                "name": "Rocket Science"
            })
            folder_b = archive.add_folder({
                "name": "Foundations of Rocket Science"
            })
            author_a = archive.add_author({
                "name": "Prof. Dr. Jane Doe"
            })
            author_b = archive.add_author({
                "name": "Prof. Dr. Max Mustermann"
            })
            course_a = archive.add_course({
                "long_name": "Rocket Science",
                "short_name": "RS"
            })
            course_b = archive.add_course({
                "long_name": "Foundations of Rocket Science",
                "short_name": "FRS"
            })

            item = archive.add_item({
                "name": "Rocket Science WS 2020/21",
                "date": None,
                "documents": [],
                "authors": [],
                "courses": [],
                "folders": [],
                "visible": False
            })

            assert item.name == "Rocket Science WS 2020/21"
            assert item.date is None
            assert item.documents == []
            assert item.authors == []
            assert item.applicable_courses == []
            assert item.folders == []

            item.name = "Rocket Science WS 2021/22"
            item.date = datetime.date(2021, 12, 3)
            item.add_document(doc_a)
            item.add_author(author_a)
            item.add_to_course(course_a)
            item.add_folder(folder_a)
            item.visible = True

            assert item.name == "Rocket Science WS 2021/22"
            assert item.date == datetime.date(2021, 12, 3)
            assert item.documents == [doc_a]
            assert item.authors == [author_a]
            assert item.applicable_courses == [course_a]
            assert item.folders == [folder_a]
            assert item.visible

            item.add_document(doc_b)
            item.add_author(author_b)
            item.add_to_course(course_b)
            item.add_folder(folder_b)

            assert set(item.documents) == {doc_a, doc_b}
            assert set(item.authors) == {author_a, author_b}
            assert set(item.applicable_courses) == {course_a, course_b}
            assert set(item.folders) == {folder_a, folder_b}

            item.remove_document(doc_a)
            item.remove_author(author_a)
            item.remove_from_course(course_a)
            item.remove_folder(folder_a)

            assert item.documents == [doc_b]
            assert item.authors == [author_b]
            assert item.applicable_courses == [course_b]
            assert item.folders == [folder_b]

            item.remove_document(doc_b)
            item.remove_author(author_b)
            item.remove_from_course(course_b)
            item.remove_folder(folder_b)

            assert item.documents == []
            assert item.authors == []
            assert item.applicable_courses == []
            assert item.folders == []


class TestArchive(object):
    def test_init(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive_dir = Path(tempdir)
            archive = Archive(archive_dir)

            assert archive.db_path.is_file()
            assert archive.db_path.parent == archive_dir

            assert archive.docs_path.is_dir()
            assert archive.docs_path.parent == archive_dir

            assert archive.secret_path.is_file()
            assert archive.secret_path.parent == archive_dir

    def test_items(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert str(archive.path) == tempdir
            assert len(archive.items) == 0

            item_a = archive.add_item("item_a")
            assert archive.items == [item_a]

            item_b = archive.add_item("item_b")
            assert item_a != item_b
            assert set(archive.items) == {item_a, item_b}

            archive.remove_item(item_a)
            assert archive.items == [item_b]

            archive.remove_item(item_b)
            assert archive.items == []

    def test_reopen(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive_a = Archive(tempdir)
            archive_a.add_item("item")
            archive_a.commit()
            del archive_a

            archive_b = Archive(tempdir)
            assert len(archive_b.items) == 1

    def test_courses(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            assert archive.courses == []
            course1 = archive.add_course("Rocket Science")
            assert archive.courses == [course1]
            course2 = archive.add_course("Foundations of Rocket Science")
            assert set(archive.courses) == {course1, course2}
            archive.remove_course(course1)
            assert archive.courses == [course2]
            archive.remove_course(course2)
            assert archive.courses == []

    def test_folders(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            assert archive.folders == []
            folder1 = archive.add_folder("Rocket Science")
            assert archive.folders == [folder1]
            folder2 = archive.add_folder("Foundations of Rocket Science")
            assert set(archive.folders) == {folder1, folder2}
            archive.remove_folder(folder1)
            assert archive.folders == [folder2]
            archive.remove_folder(folder2)
            assert archive.folders == []

    def test_authors(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            assert archive.authors == []
            author1 = archive.add_author("Dr. Max Mustermann")
            assert archive.authors == [author1]
            author2 = archive.add_author("Prof. Dr. Jane Doe")
            assert set(archive.authors) == {author1, author2}
            archive.remove_author(author1)
            assert archive.authors == [author2]
            archive.remove_author(author2)
            assert archive.authors == []
