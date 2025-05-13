from typing import Any, Self
from enum import Enum
from collections import namedtuple

class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

class Vector(namedtuple("Vector", ("x", "y"), defaults=(0, 0))):
    @classmethod
    def ofDict(cls, data: dict[str, Any]) -> Self:
        return cls(x=data["x"], y=data["y"])

    def toDict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def ofTuple(cls, t: tuple[int, int]) -> Self:
        x, y = t
        return cls(x, y)

    def __add__(self, other: Any) -> Self:
        if isinstance(other, Vector):
            return Vector(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __sub__(self, other: Any) -> Self:
        if isinstance(other, Vector):
            return Vector(self.x - other.x, self.y - other.y)
        return NotImplemented

    def __mul__(self, other: Any) -> Self:
        if isinstance(other, int):
            return Vector(self.x * other, self.y * other)
        return NotImplemented

    def __floordiv__(self, other: Any) -> Self:
        if isinstance(other, int):
            return Vector(self.x // other, self.y // other)
        return NotImplemented

    def __min__(self, other: Any) -> Self:
        if isinstance(other, Vector):
            return Vector(min(self.x, other.x), min(self.y, other.y))
        return NotImplemented

    def __max__(self, other: Any) -> Self:
        if isinstance(other, Vector):
            return __class__(max(self.x, other.x), max(self.y, other.y))
        return NotImplemented

class Rect(namedtuple("Rect", ("pos", "size"), defaults=(Vector(), Vector()))):
    def centered(self, size: Vector) -> Self:
        margin = (self.size - size) // 2
        return Rect(self.pos + margin, size)

    def toTuple(self) -> tuple[int, int, int, int]:
        return self.pos.x, self.pos.y, self.size.x, self.size.y

    def intersects(self, other: Self) -> bool:
        corner = self.corner()
        otherCorner = other.corner()
        return corner.x > other.pos.x and self.pos.x < otherCorner.x and \
            corner.y > other.pos.y and self.pos.y < otherCorner.y

    def union(self, other: Self) -> Self:
        pos = min(self.pos, other.pos)
        corner = max(self.corner(), other.corner())
        return __class__(pos, size=(corner - pos))

    def corner(self) -> Vector:
        return self.pos + self.size

    def lt(self) -> Vector: # left-top
        return self.pos

    def rb(self) -> Vector: # right-bottom
        return self.corner()

    def rt(self) -> Vector: # right-top
        return Vector(self.pos.x + self.size.x, self.pos.y)

    def lb(self) -> Vector: # left-bottom
        return Vector(self.pos.x, self.pos.y + self.size.y)

    def __add__(self, other: Any) -> Self:
        if isinstance(other, Vector):
            return Rect(self.pos + other, self.size)
        return NotImplemented

    def __radd__(self, other: Any) -> Self:
        return self.__add__(other)

    def __mul__(self, other: Any) -> Self:
        if isinstance(other, int):
            return Rect(self.pos * other, self.size * other)
        return NotImplemented

    def __contains__(self, other: Any) -> bool:
        if isinstance(other, Vector):
            corner = self.corner()
            return other.x >= self.pos.x and other.x < corner.x and \
                    other.y >= self.pos.y and other.y < corner.y
        return NotImplemented

def reverseDir(dir: Direction) -> Direction:
    match dir:
        case Direction.LEFT:
            return Direction.RIGHT
        case Direction.RIGHT:
            return Direction.LEFT
        case Direction.UP:
            return Direction.DOWN
        case Direction.DOWN:
            return Direction.UP

def movePos(pos: Vector, dir: Direction, offset: int) -> Vector:
    match dir:
        case Direction.LEFT:
            return pos - Vector(x=offset)
        case Direction.RIGHT:
            return pos + Vector(x=offset)
        case Direction.UP:
            return pos - Vector(y=offset)
        case Direction.DOWN:
            return pos + Vector(y=offset)
