import tempfile

from klausurarchiv.model import *


class TestDocument(object):
    def test_path(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / Path("test.txt")
            doc = Document(path)
            assert (doc.path == path)


class TestItem(object):
    def test_new_item(self):
        with tempfile.TemporaryDirectory() as tempdir:
            Item.new_item(tempdir)
            directory = Path(tempdir)
            dirs = list(directory.iterdir())
            assert (len(dirs) == 1)
            directory = dirs[0]
            assert (directory.is_dir())
            files = list(directory.iterdir())
            assert (len(files) == 1)
            assert (str(files[0].name) == str(META_FILENAME))
