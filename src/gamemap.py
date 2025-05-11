from serde import Serde
from geometry import Vector, Rect

class GameMap(Serde):
    BLOCK_SIZE = 32

    size: Vector
    blocks: list[str]
    spawns: list[Vector]
    version: int = 0

    __serde_fields__ = {"size", "blocks"}

    def __init__(self):
        self.clear()

    def clear(self):
        self.size = Vector()
        self.blocks = []
        self.spawns = []
        self.version = 0

    def load(self, fileName):
        self.clear()
        with open(fileName, "r") as f:
            width, height = 0, 0
            for line in f:
                line = line.rstrip("\n")
                line = line.replace("=", "4")

                while True:
                    i = line.find("*")
                    if i ==-1:
                        break
                    self.spawns.append(Vector(x=i, y=height))
                    line = line[:i] + " " + line[(i + 1):]

                self.blocks.append(line)

                if len(line) > width:
                    width = len(line)
                height += 1
            
            self.size = Vector(width, height)

    def getBlock(self, pos: Vector) -> str:
        return self.blocks[pos.y][pos.x]

    def setBlock(self, pos: Vector, block: str):
        row = self.blocks[pos.y]
        self.blocks[pos.y] = row[:pos.x] + block[0] + row[(pos.x + 1):]

    @staticmethod
    def getBlockRect(pos: Vector) -> Rect:
        return Rect(pos * GameMap.BLOCK_SIZE, Vector(1, 1) * GameMap.BLOCK_SIZE)