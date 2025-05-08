from typing import Any, Self, Callable
from typing import get_type_hints, get_origin
from enum import Enum
from json import JSONEncoder

class Serde:
    __serde_fields__: set[str]

    @classmethod
    def ofDict(cls, data: dict[str, Any]) -> Self:
        self = cls.__new__(cls)
        cvts = cls.getCvts()
        for field, value in data.items():
            if field in self.__serde_fields__:
                if value is not None:
                    cvt = cvts.get(field)
                    if cvt is not None:
                        value = cvt(value)
                setattr(self, field, value)
        return self

    @classmethod
    def getCvts(cls) -> dict[str, Callable[[Any], Any]]:
        try:
            return cls.__cvts
        except AttributeError:
            pass

        cls.__cvts = {}
        for field, typ in get_type_hints(cls).items():
            origin = get_origin(typ)
            if origin is not None:
                typ = origin
            if issubclass(typ, Enum):
                cls.__cvts[field] = typ.__getitem__
            else:
                ofDict = getattr(typ, "ofDict", None)
                if callable(ofDict):
                    cls.__cvts[field] = ofDict

        return cls.__cvts

    def toDict(self) -> dict[str, Any]:
        data = {}
        for field in self.__serde_fields__:
            try:
                value = getattr(self, field)
            except AttributeError:
                continue
            toDict = getattr(value, "toDict", None)
            if callable(toDict):
                value = toDict()
            data[field] = value
        return data

class JsonEncoderEx(JSONEncoder):
    def default(self, obj: Any) -> Any:
        toDict = getattr(obj, "toDict", None)
        if callable(toDict):
            return toDict()
        if isinstance(obj, Serde):
            return obj.toDict()
        if isinstance(obj, Enum):
            return obj.name
        return super().default(obj)
