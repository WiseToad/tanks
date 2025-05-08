from enum import Enum
from typing import Any, Self, TypeVar

from const import Const
from serde import Serde
from geometry import Direction, Pos, Box
from gamemap import GameMap

class GameObject(Serde):
    BOX_SIZE: int
    ANIM_COUNT: int
    ANIM_DELAY: int

    key: int
    pos: Pos
    animTick: int = 0

    __serde_fields__ = {"key", "pos", "animTick"}

    T = TypeVar("T", bound=Self)

    @classmethod
    def centeredTo(cls, other: T, **kwArgs):
        return cls.centeredToBox(other.getBox(), **kwArgs)

    @classmethod
    def centeredToBox(cls, box: Box, **kwArgs):
        objBox = Box.centeredTo(box, cls.BOX_SIZE)
        return cls(pos=objBox.pos, **kwArgs)

    def __init__(self, *, pos: Pos = None):
        self.key = id(self)
        self.pos = pos if pos is not None else Pos()

    def getBox(self) -> Box:
        return Box(self.pos, self.BOX_SIZE)

class DirectedObject(GameObject):
    VELOCITY: int

    heading: Direction

    __serde_fields__ = {"key", "pos", "heading"}

    def __init__(self, *, pos: Pos = None, heading = Direction.UP):
        super().__init__(pos=pos)
        self.heading = heading

class TankState(Enum):
    START = 1
    FIGHT = 2
    DEAD = 3

class Tank(DirectedObject):
    BOX_SIZE = 22
    VELOCITY = 1

    INITIAL_HEALTH = 4
    START_DURATION = 2 * Const.FPS
    DEAD_DURATION = 3 * Const.FPS
    MISSLE_DELAY = 1 * Const.FPS // 2

    name: str = None
    
    state: TankState = TankState.START
    stateTick: int = 0

    missleTick: int = 0

    health: int = INITIAL_HEALTH
    fails: int = 0
    wins: int = 0

    __serde_fields__ = {"key", "pos", "heading", "name", "state", "health", "fails", "wins"}

class Missle(DirectedObject):
    BOX_SIZE = 8
    VELOCITY = 6

    tankKey: int
    lethal: bool

    @classmethod
    def ofTank(cls, tank: Tank) -> Self:
        self = Missle.centeredTo(tank, heading=tank.heading, tankKey=tank.key, lethal=(tank.state == TankState.FIGHT))

        offset = (Tank.BOX_SIZE + Missle.BOX_SIZE) // 2
        self.pos = self.pos.move(tank.heading, offset)

        return self
    
    def __init__(self, *, pos: Pos = None, heading = Direction.UP, tankKey: int, lethal: bool = True):
        super().__init__(pos=pos, heading=heading)
        self.tankKey = tankKey
        self.lethal = lethal

class Punch(GameObject):
    BOX_SIZE = 16
    ANIM_COUNT = 1
    ANIM_DELAY = 8

class Boom(GameObject):
    BOX_SIZE = 32
    ANIM_COUNT = 4
    ANIM_DELAY = 8

class GameDict(dict[int, GameObject.T]):
    @classmethod
    def ofList(cls, data: list[Any], objType: type[GameObject.T]) -> Self:
        self = cls()
        self.update({obj.key: obj for obj in (objType.ofDict(datum) for datum in data)})
        return self

    def toList(self) -> list[Any]:
        return list(self.values())

    def add(self, obj: GameObject.T):
        self[obj.key] = obj

    def remove(self, *objs: GameObject.T):
        for obj in objs:
            self.pop(obj.key, None)

class GameObjects(Serde):
    tanks: GameDict[Tank]
    missles: GameDict[Missle]
    punches: GameDict[Punch]
    booms: GameDict[Boom]

    __serde_fields__ = {"tanks", "missles", "punches", "booms"}

    def __init__(self):
        self.tanks = GameDict()
        self.missles = GameDict()
        self.punches = GameDict()
        self.booms = GameDict()

    @classmethod
    def ofDict(cls, data: dict[str, Any]) -> Self:
        self = cls.__new__(cls)
        self.tanks = GameDict.ofList(data["tanks"], Tank)
        self.missles = GameDict.ofList(data["missles"], Missle)
        self.punches = GameDict.ofList(data["punches"], Punch)
        self.booms = GameDict.ofList(data["booms"], Boom)
        return self

    def toDict(self) -> dict[str, Any]:
        return {
            "tanks": self.tanks.toList(),
            "missles": self.missles.toList(),
            "punches": self.punches.toList(),
            "booms": self.booms.toList()
        }

class GameControls(Serde):
    dir: Direction = None
    fire: bool = False

    __serde_fields__ = {"dir", "fire"}

class ServerData(Serde):
    gameMap: GameMap = None
    gameObjs: GameObjects

    __serde_fields__ = {"gameObjs", "gameMap"}

    def __init__(self, *, gameObjs: GameObjects):
        self.gameObjs = gameObjs

class ClientData(Serde):
    playerName: str = None
    gameControls: GameControls

    __serde_fields__ = {"playerName", "gameControls"}

    def __init__(self, *, gameControls: GameControls = None):
        self.gameControls = gameControls

