from typing import Any, TypeVar
import json

from serde import JsonEncoderEx

T = TypeVar("T")

def toBytes(obj: Any) -> bytes:
    return bytes(json.dumps(obj, cls=JsonEncoderEx), "utf-8")

def ofBytes(b: bytes, cls: type[T] | None = None) -> T | Any | None:
    if not b:
        return None

    result = json.loads(b.decode("utf-8"))
    if cls is not None:
        result = cls.ofDict(result)

    return result
