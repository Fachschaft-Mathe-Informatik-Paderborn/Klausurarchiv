import tempfile

from klausurarchiv.model import *


class TestDocument(object):
    def test_document(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            item = archive.add_item("itemA")

            doc_a_path = Path(tempdir) / Path("doc_a.txt")
            with open(doc_a_path, mode="w") as file:
                file.write("Hello World\n")
            doc_a = item.add_document(doc_a_path)

            doc_a.name = "Hello World.txt"
            assert doc_a.name == "Hello World.txt"
            with open(doc_a.path, mode="r") as file:
                assert file.readline() == "Hello World\n"


class TestCourse(object):
    def test_canonical_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            course = archive.add_course("Rocket Science")
            assert course.canonical_name == "Rocket Science"

            course.canonical_name = "Foundations of Rocket Science"
            assert course.canonical_name == "Foundations of Rocket Science"

    def test_aliases(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            course = archive.add_course("Rocket Science")
            assert course.aliases == []

            alias1 = "RS"
            alias2 = "FRS"
            course.add_alias(alias1)
            assert course.aliases == [alias1]
            course.add_alias(alias2)
            assert set(course.aliases) == {alias1, alias2}
            course.remove_alias(alias1)
            assert course.aliases == [alias2]
            course.remove_alias(alias2)
            assert course.aliases == []


class TestFolder(object):
    def test_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            folder = archive.add_folder("Rocket Science")
            assert folder.name == "Rocket Science"

            folder.name = "Foundations of Rocket Science"
            assert folder.name == "Foundations of Rocket Science"


class TestAuthor(object):
    def test_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            author = archive.add_author("Dr. Jane Doe")
            assert author.name == "Dr. Jane Doe"

            author.name = "Prof. Dr. Jane Doe"
            assert author.name == "Prof. Dr. Jane Doe"


class TestItem(object):
    def test_meta(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            item = archive.add_item("Rocket Science")
            folder = archive.add_folder("Rocket Science")
            author = archive.add_author("Prof. Dr. Jane Doe")

            assert not item.downloadable
            assert item.name == "Rocket Science"
            assert item.date is None
            assert item.folder is None
            assert item.author is None

            item.downloadable = True
            item.name = "Foundations of Rocket Science"
            item.date = datetime.date(2021, 9, 8)
            item.folder = folder
            item.author = author

            assert item.downloadable
            assert item.name == "Foundations of Rocket Science"
            assert item.date == datetime.date(2021, 9, 8)
            assert item.folder == folder
            assert item.author == author

    def test_uuid(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            item_a = archive.add_item("Item A")
            item_b = archive.add_item("Item B")
            assert item_a.uuid != item_b.uuid

    def test_documents(self):
        with tempfile.TemporaryDirectory() as tempdir:
            doc_a_path = Path(tempdir) / Path("doc_a.txt")
            with open(doc_a_path, mode="w") as file:
                file.write("Hello World\n")
            doc_b_path = Path(tempdir) / Path("doc_b.txt")
            with open(doc_b_path, mode="w") as file:
                file.write("Foo Bar\n")

            archive = Archive(tempdir)
            item = archive.add_item("item")
            assert item.documents == []

            doc_a = item.add_document(doc_a_path)
            assert not doc_a_path.exists()
            assert item.documents == [doc_a]
            with open(doc_a.path, mode="r") as file:
                assert file.readline() == "Hello World\n"

            doc_b = item.add_document(doc_b_path)
            assert not doc_b_path.exists()
            assert set(item.documents) == {doc_a, doc_b}
            with open(doc_b.path, mode="r") as file:
                assert file.readline() == "Foo Bar\n"

            item.remove_document(doc_a)
            assert item.documents == [doc_b]

            item.remove_document(doc_b)
            assert item.documents == []

    def test_courses(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            course1 = archive.add_course("Rocket Science")
            course2 = archive.add_course("Foundations of Rocket Science")

            item = archive.add_item("item")
            assert item.applicable_courses == []
            item.add_to_course(course1)
            assert item.applicable_courses == [course1]
            item.add_to_course(course2)
            assert set(item.applicable_courses) == {course1, course2}
            item.remove_from_course(course1)
            assert item.applicable_courses == [course2]
            item.remove_from_course(course2)
            assert item.applicable_courses == []


class TestArchive(object):
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

    def test_get_item_with_uuid(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            item = archive.add_item("Item")
            assert archive.get_item_with_uuid(item.uuid) == item
            assert archive.get_item_with_uuid(uuid4()) is None

    def test_reopen(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive_a = Archive(tempdir)
            archive_a.add_item("item")
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

    def test_items_for_course(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            item_frs = archive.add_item("Foundations of Rocket Science")
            item_rs = archive.add_item("Rocket Science")
            item_es = archive.add_item("Embedded Systems")
            course_rs = archive.add_course("Rocket Science")
            course_es = archive.add_course("Embedded Systems")

            item_frs.add_to_course(course_rs)
            item_rs.add_to_course(course_rs)
            item_es.add_to_course(course_es)

            assert set(archive.get_items_for_course(course_rs)) == {item_frs, item_rs}
            assert archive.get_items_for_course(course_es) == [item_es]

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

    def test_items_in_folder(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            item_frs = archive.add_item("Foundations of Rocket Science")
            item_rs = archive.add_item("Rocket Science")
            item_es = archive.add_item("Embedded Systems")
            folder_rs = archive.add_folder("Rocket Science")
            folder_es = archive.add_folder("Embedded Systems")

            item_frs.folder = folder_rs
            item_rs.folder = folder_rs
            item_es.folder = folder_es

            assert set(archive.get_items_in_folder(folder_rs)) == {item_frs, item_rs}
            assert archive.get_items_in_folder(folder_es) == [item_es]

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

    def test_items_by_author(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)

            item_frs = archive.add_item("Foundations of Rocket Science")
            item_rs = archive.add_item("Rocket Science")
            item_es = archive.add_item("Embedded Systems")
            author_mm = archive.add_author("Dr. Max Mustermann")
            author_jd = archive.add_author("Prof. Dr. Jane Doe")

            item_frs.author = author_mm
            item_rs.author = author_mm
            item_es.author = author_jd

            assert set(archive.get_items_by_author(author_mm)) == {item_frs, item_rs}
            assert archive.get_items_by_author(author_jd) == [item_es]
