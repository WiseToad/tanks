from serde import Serde
from geometry import Vector, Rect

class GameMap(Serde):
    SIZE = Vector(30, 15)
    BLOCK_SIZE = 32

    blocks: list[str]
    spawns: list[Vector]
    version: int = 0

    __serde_fields__ = {"size", "blocks"}

    GROUND = " "
    CONCRETE = "#"
    BRICKS = "=123"
    TOWER = "+"
    WATER = "~"
    CAMO = "x"
    SPAWN = "*"

    def __init__(self):
        self.clear()

    def clear(self):
        self.blocks = []
        self.spawns = []
        self.version = 0

    def load(self, fileName):
        self.clear()
        with open(fileName, "r") as f:
            y = 0
            for line in f:
                line = line.rstrip("\n")

                p = 0
                while True:
                    i = line.find(self.SPAWN, p)
                    if i == -1:
                        break
                    self.spawns.append(Vector(i, y))
                    p = i + 1

                self.blocks.append(line)

                y += 1

    def getBlock(self, pos: Vector) -> str:
        return self.blocks[pos.y][pos.x]

    def setBlock(self, pos: Vector, block: str):
        row = self.blocks[pos.y]
        self.blocks[pos.y] = row[:pos.x] + block[0] + row[(pos.x + 1):]

    @staticmethod
    def getBlockRect(pos: Vector) -> Rect:
        return Rect(pos, Vector(1, 1)) * GameMap.BLOCK_SIZE