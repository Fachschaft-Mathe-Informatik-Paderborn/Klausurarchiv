import tempfile

from klausurarchiv.db import *


class TestDocument(object):
    def test_document(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            assert archive.documents == []

            doc = archive.add_document(
                filename="doc_a.txt",
                downloadable=True,
                content_type="text/plain"
            )

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

            doc.downloadable = True
            assert doc.downloadable


class TestCourse(object):
    def test_course(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            course = archive.add_course(
                long_name="Rocket Science",
                short_name="RS"
            )

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
            folder = archive.add_folder(
                name="Rocket Science"
            )

            assert folder.name == "Rocket Science"

            folder.name = "Foundations of Rocket Science"
            assert folder.name == "Foundations of Rocket Science"


class TestAuthor(object):
    def test_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            author = archive.add_author(
                name="Dr. Jane Doe"
            )
            assert author.name == "Dr. Jane Doe"

            author.name = "Prof. Dr. Jane Doe"
            assert author.name == "Prof. Dr. Jane Doe"


class TestItem(object):
    def test_item(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            doc_a = archive.add_document(
                filename="exam.pdf",
                downloadable=True,
                content_type="application/pdf"
            )
            doc_b = archive.add_document(
                filename="solution.pdf",
                downloadable=True,
                content_type="application/pdf"
            )
            folder_a = archive.add_folder(
                name="Rocket Science"
            )
            folder_b = archive.add_folder(
                name="Foundations of Rocket Science"
            )
            author_a = archive.add_author(
                name="Prof. Dr. Jane Doe"
            )
            author_b = archive.add_author(
                name="Prof. Dr. Max Mustermann"
            )
            course_a = archive.add_course(
                long_name="Rocket Science",
                short_name="RS"
            )
            course_b = archive.add_course(
                long_name="Foundations of Rocket Science",
                short_name="FRS"
            )

            item = archive.add_item(
                name="Rocket Science WS 2020/21",
                date=None,
                documents=[],
                authors=[],
                courses=[],
                folders=[],
                visible=False
            )

            assert item.name == "Rocket Science WS 2020/21"
            assert item.date is None
            assert item.documents == []
            assert item.authors == []
            assert item.applicable_courses == []
            assert item.folders == []
            assert not item.visible

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

    def test_reopen(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive_a = Archive(tempdir)
            archive_a.commit()

            archive_b = Archive(tempdir)
            assert archive_a == archive_b
            assert not (archive_a != archive_b)

    def test_items(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert str(archive.path) == tempdir
            assert len(archive.items) == 0

            item_a = archive.add_item()
            assert archive.items == [item_a]
            assert archive.get_item(item_a.entry_id) == item_a

            item_b = archive.add_item()
            assert item_a != item_b
            assert set(archive.items) == {item_a, item_b}
            assert archive.get_item(item_b.entry_id) == item_b

            archive.remove_item(item_a)
            assert archive.items == [item_b]
            assert archive.get_item(item_a.entry_id) is None

            archive.remove_item(item_b)
            assert archive.items == []
            assert archive.get_item(item_b.entry_id) is None

    def test_documents(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert archive.documents == []

            doc_a = archive.add_document()
            assert archive.documents == [doc_a]
            assert archive.get_document(doc_a.entry_id) == doc_a

            doc_b = archive.add_document()
            assert doc_a != doc_b
            assert set(archive.documents) == {doc_a, doc_b}
            assert archive.get_document(doc_b.entry_id) == doc_b

            archive.remove_document(doc_a)
            assert archive.documents == [doc_b]
            assert archive.get_document(doc_a.entry_id) is None

            archive.remove_document(doc_b)
            assert archive.documents == []
            assert archive.get_document(doc_b.entry_id) is None

    def test_courses(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert archive.courses == []

            course1 = archive.add_course()
            assert archive.courses == [course1]
            assert archive.get_course(course1.entry_id) == course1

            course2 = archive.add_course()
            assert set(archive.courses) == {course1, course2}
            assert course1 != course2
            assert archive.get_course(course2.entry_id) == course2

            archive.remove_course(course1)
            assert archive.courses == [course2]
            assert archive.get_course(course1.entry_id) is None

            archive.remove_course(course2)
            assert archive.courses == []
            assert archive.get_course(course2.entry_id) is None

    def test_folders(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert archive.folders == []

            folder1 = archive.add_folder()
            assert archive.folders == [folder1]
            assert archive.get_folder(folder1.entry_id) == folder1

            folder2 = archive.add_folder()
            assert set(archive.folders) == {folder1, folder2}
            assert folder1 != folder2
            assert archive.get_folder(folder2.entry_id) == folder2

            archive.remove_folder(folder1)
            assert archive.folders == [folder2]
            assert archive.get_folder(folder1.entry_id) is None

            archive.remove_folder(folder2)
            assert archive.folders == []
            assert archive.get_folder(folder2.entry_id) is None

    def test_authors(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert archive.authors == []

            author1 = archive.add_author()
            assert archive.authors == [author1]
            assert archive.get_author(author1.entry_id) == author1

            author2 = archive.add_author()
            assert set(archive.authors) == {author1, author2}
            assert author1 != author2
            assert archive.get_author(author2.entry_id) == author2

            archive.remove_author(author1)
            assert archive.authors == [author2]
            assert archive.get_author(author1.entry_id) is None

            archive.remove_author(author2)
            assert archive.authors == []
            assert archive.get_author(author2.entry_id) is None
