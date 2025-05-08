from serde import Serde
from geometry import Pos, Dims

class GameMap(Serde):
    BLOCK_SIZE = 32

    size: Dims
    blocks: list[str]
    spawns: list[Pos]
    version: int = 0

    __serde_fields__ = {"size", "blocks"}

    def __init__(self):
        self.size = Dims()
        self.blocks = []
        self.spawns = []

    def load(self, fileName):
        width, height = 0, 0
        self.size = Dims()
        self.blocks = []
        self.spawns = []
        self.version = 0
        with open(fileName, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                line = line.replace("=", "4")

                while True:
                    i = line.find("*")
                    if i ==-1:
                        break
                    self.spawns.append(Pos(x=i, y=height))
                    line = line[:i] + " " + line[(i + 1):]

                self.blocks.append(line)

                if len(line) > width:
                    width = len(line)
                height += 1
            
            self.size = Dims(width, height)

    def getBlock(self, i: int, j: int) -> str:
        return self.blocks[j][i]

    def setBlock(self, i: int, j: int, block: str):
        row = self.blocks[j]
        self.blocks[j] = row[:i] + block[0] + row[(i + 1):]
