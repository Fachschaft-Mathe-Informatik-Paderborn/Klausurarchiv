import tempfile

from klausurarchiv.model import *


class TestDocument(object):
    def test_path(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / Path("test.txt")
            doc = Document(path)
            assert (doc.path == path)

    def test_rename(self):
        with tempfile.TemporaryDirectory() as tempdir:
            old_path = Path(tempdir) / Path("a.txt")
            new_path = Path(tempdir) / Path("b.txt")

            with open(old_path, mode="w") as file:
                file.write("Hallo Welt\n")
            document = Document(old_path)
            document.rename(new_path.name)

            assert not old_path.exists()
            assert new_path.is_file()
            assert document.path == new_path

            with open(new_path, mode="r") as file:
                assert file.readline() == "Hallo Welt\n"


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

            assert item.documents == [doc_a]

            doc_b = item.add_document(path_b)
            assert doc_b.path.is_file()
            assert doc_b.path.parent == item.path
            assert str(doc_b.path.name) == "b.txt"
            with open(doc_b.path, mode="r") as fileB:
                assert fileB.readline() == "Foo Bar\n"

            assert set(item.documents) == {doc_a, doc_b}

            item.remove_document(doc_a)
            assert not doc_a.path.exists()
            assert doc_b.path.is_file()
            assert item.documents == [doc_b]

            item.remove_document(doc_b)
            assert not doc_b.path.exists()
            assert item.documents == []


class TestArchive(object):
    def test_items(self):
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Archive(tempdir)
            assert str(archive.path) == tempdir
            assert len(archive.items) == 0

            item_a = archive.add_item()
            assert item_a.path.is_dir()
            assert item_a.path.parent == archive.path
            assert archive.items == [item_a]

            item_b = archive.add_item()
            assert item_b.path.is_dir()
            assert item_b.path.parent == archive.path
            assert item_a != item_b
            assert set(archive.items) == {item_a, item_b}

            archive.remove_item(item_a)
            assert not item_a.path.exists()
            assert item_b.path.is_dir()
            assert archive.items == [item_b]

            archive.remove_item(item_b)
            assert not item_b.path.exists()
            assert archive.items == []
