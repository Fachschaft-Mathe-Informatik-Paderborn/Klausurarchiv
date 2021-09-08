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
