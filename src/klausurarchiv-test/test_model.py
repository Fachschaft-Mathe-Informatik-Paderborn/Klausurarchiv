import tempfile

from klausurarchiv.model import *


class TestDocument(object):
    def test_document(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            item = archive.add_item()

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


class TestItem(object):
    def test_meta(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            item = archive.add_item()

            item.downloadable = True
            item.name = "Rocket Science"
            item.date = datetime.date(2021, 9, 8)

            assert item.downloadable
            assert item.name == "Rocket Science"
            assert item.date == datetime.date(2021, 9, 8)

    def test_documents(self):
        with tempfile.TemporaryDirectory() as tempdir:
            doc_a_path = Path(tempdir) / Path("doc_a.txt")
            with open(doc_a_path, mode="w") as file:
                file.write("Hello World\n")
            doc_b_path = Path(tempdir) / Path("doc_b.txt")
            with open(doc_b_path, mode="w") as file:
                file.write("Foo Bar\n")

            archive = Archive(tempdir)
            item = archive.add_item()
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


class TestArchive(object):
    def test_items(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert str(archive.path) == tempdir
            assert len(archive.items) == 0

            item_a = archive.add_item()
            assert archive.items == [item_a]

            item_b = archive.add_item()
            assert item_a != item_b
            assert set(archive.items) == {item_a, item_b}

            archive.remove_item(item_a)
            assert archive.items == [item_b]

            archive.remove_item(item_b)
            assert archive.items == []

    def test_reopen(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive_a = Archive(tempdir)
            archive_a.add_item()
            del archive_a

            archive_b = Archive(tempdir)
            assert len(archive_b.items) == 1
