import tempfile

from klausurarchiv.model import *


class TestDocument(object):
    def test_path(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / Path("test.txt")
            doc = Document(path)
            assert (doc.path == path)


class TestItemMeta(object):
    def test_load_store(self):
        with tempfile.TemporaryFile(mode="w+") as file:
            meta = ItemMeta()
            meta.downloadable = True
            meta.date = datetime.date(2021, 12, 9)
            meta.author = None
            meta.store(file)

            new_meta = ItemMeta()
            file.seek(0)
            new_meta.load(file)
            assert new_meta.downloadable
            assert new_meta.date == datetime.date(2021, 12, 9)
            assert meta.author is None


class TestItem(object):
    def test_meta(self):
        with tempfile.TemporaryDirectory() as tempdir:
            item = Item.new_item(tempdir)
            meta_path = item.meta_path
            assert meta_path.is_file()
            assert str(meta_path.name) == str(META_FILENAME)
            assert meta_path.parent == item.path

            meta = item.meta
            meta.date = datetime.date(2021, 9, 8)
            meta.downloadable = True
            item.meta = meta

            with open(meta_path, mode="r") as meta_file:
                meta = json.load(meta_file)

            assert meta["date"] == "2021-09-08"
            assert meta["downloadable"]

    def test_new_item(self):
        with tempfile.TemporaryDirectory() as tempdir:
            Item.new_item(tempdir)
            directory = Path(tempdir)
            dirs = list(directory.iterdir())
            assert len(dirs) == 1
            directory = dirs[0]
            assert directory.is_dir()
            files = list(directory.iterdir())
            assert len(files) == 1
            assert str(files[0].name) == str(META_FILENAME)

    def test_path(self):
        with tempfile.TemporaryDirectory() as tempdir:
            item = Item.new_item(tempdir)
            item_path = list(Path(tempdir).iterdir())[0]
            assert item.path == item_path

    def test_uuid_name(self):
        with tempfile.TemporaryDirectory() as tempdir:
            item = Item.new_item(tempdir)
            item_path = list(Path(tempdir).iterdir())[0]
            (uuid, _, name) = str(item_path.name).partition(" ")
            assert item.uuid == UUID(uuid)
            assert item.name == name

            item.name = "New Name"
            assert item.name == "New Name"
            item_path = list(Path(tempdir).iterdir())[0]
            name = str(item_path).partition(" ")[2]
            assert name == "New Name"

    def test_documents(self):
        with tempfile.TemporaryDirectory() as tempdir:
            item = Item.new_item(tempdir)
            assert len(item.documents) == 0

            path_a = Path(tempdir) / "a.txt"
            with open(path_a, mode="w") as fileA:
                fileA.write("Hello World\n")
            path_b = Path(tempdir) / "b.txt"
            with open(path_b, mode="w") as fileB:
                fileB.write("Foo Bar\n")

            doc_a = item.add_document(path_a)
            assert doc_a.path.is_file()
            assert doc_a.path.parent == item.path
            assert str(doc_a.path.name) == "a.txt"
            with open(doc_a.path, mode="r") as fileA:
                assert fileA.readline() == "Hello World\n"

            assert len(item.documents) == 1
            assert item.documents[0].path == doc_a.path

            doc_b = item.add_document(path_b)
            assert doc_b.path.is_file()
            assert doc_b.path.parent == item.path
            assert str(doc_b.path.name) == "b.txt"
            with open(doc_b.path, mode="r") as fileB:
                assert fileB.readline() == "Foo Bar\n"

            assert len(item.documents) == 2
            assert item.documents[0].path in [doc_a.path, doc_b.path]
            assert item.documents[1].path in [doc_a.path, doc_b.path]
            assert item.documents[0].path != item.documents[1].path

            item.remove_document(doc_a)
            assert len(item.documents) == 1
            assert item.documents[0].path == doc_b.path

            item.remove_document(doc_b)
            assert len(item.documents) == 0
