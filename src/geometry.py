from typing import Any, Self
from enum import Enum
from collections import namedtuple

class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

class Pos(namedtuple("Pos", ("x", "y"), defaults=(0, 0))):
    @classmethod
    def ofDict(cls, data: dict[str, Any]) -> Self:
        return cls(x=data["x"], y=data["y"])

    def toDict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y}

    def move(self, dir: Direction, offset: int) -> Self:
        match dir:
            case Direction.LEFT:
                return self - Pos(x=offset)
            case Direction.RIGHT:
                return self + Pos(x=offset)
            case Direction.UP:
                return self - Pos(y=offset)
            case Direction.DOWN:
                return self + Pos(y=offset)

    def __add__(self, other: Any) -> Self:
        if isinstance(other, Pos):
            return Pos(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __sub__(self, other: Any) -> Self:
        if isinstance(other, Pos):
            return Pos(self.x - other.x, self.y - other.y)
        return NotImplemented

    def __mul__(self, other: Any) -> Self:
        if isinstance(other, int):
            return Pos(self.x * other, self.y * other)
        return NotImplemented

    def __floordiv__(self, other: Any) -> Self:
        if isinstance(other, int):
            return Pos(self.x // other, self.y // other)
        return NotImplemented

Dims = Pos # dimensions, or 2D size

class Box(namedtuple("Box", ("pos", "size"), defaults=(Pos(), 0))):
    @classmethod
    def centeredTo(cls, other: Self, size: int) -> Self:
        margin = (other.size - size) // 2
        return cls(pos=Pos(other.pos.x + margin, other.pos.y + margin), size=size)

    def intersects(self, other: Self) -> bool:
        return (self.pos.x + self.size) > other.pos.x and self.pos.x < (other.pos.x + other.size) and \
            (self.pos.y + self.size) > other.pos.y and self.pos.y < (other.pos.y + other.size)
    
    def __contains__(self, other: Any) -> bool:
        if isinstance(other, Pos):
            return other.x >= self.pos.x and other.x < (self.pos.x + self.size) and \
                    other.y >= self.pos.y and other.y < (self.pos.y + self.size)
