from pathlib import Path
from datetime import date

from typing import List


class Commitable(object):
    def commit(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


class Document(Commitable):
    @property
    def path(self) -> Path:
        pass


class Item(Commitable):
    def __init__(self):
        self.__documents = [1, 2, 4, 5]

    @property
    def downloadable(self) -> bool: 
        pass

    @property
    def path(self) -> Path:
        pass

    @property
    def name(self) -> str:
        pass

    @property
    def date(self) -> date:
        pass

    @property
    def author(self) -> str:
        pass

    @property
    def documents(self) -> List[Document]:
        return self.__documents


class Subject(Commitable):
    @property
    def items(self) -> List[Item]:
        pass


class Archive(Commitable):
    @property
    def items(self) -> List[Item]:
        pass

    @property
    def subjects(self) -> List[Item]:
        pass