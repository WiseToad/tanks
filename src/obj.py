from typing import Any, Self, Iterator, TypeVar, Generic

from serde import Serde

class Obj(Serde):
    T = TypeVar("Obj.T", bound=Self)

    key: int
    
    __serde_fields__ = {"key"}

    def __init__(self):
        self.key = id(self)

class ObjCollection(Generic[Obj.T]):
    objs: dict[int, Obj.T]
    removed: set[int]

    def __init__(self):
        self.objs = {}
        self.removed = set()

    @classmethod
    def ofList(cls, data: list[Any], objType: type[Obj.T]) -> Self:
        self = cls.__new__(cls)
        self.objs = {obj.key: obj for obj in (objType.ofDict(datum) for datum in data)}
        self.removed = set()
        return self

    def toList(self) -> list[Any]:
        return list(iter(self))

    def get(self, key: int, default: Obj.T = None):
        return self.objs.get(key, default)

    def add(self, obj: Obj.T):
        self.objs[obj.key] = obj

    def remove(self, obj: Obj.T, lazy: bool = False):
        if not lazy:
            self.objs.pop(obj.key, None)
        else:
            self.removed.add(obj.key)

    def purge(self):
        for key in self.removed:
            self.objs.pop(key, None)
        self.removed.clear()

    def clear(self):
        self.objs.clear()

    def __iter__(self) -> Iterator[Obj.T]:
        return (obj for key, obj in self.objs.items() if key not in self.removed)
