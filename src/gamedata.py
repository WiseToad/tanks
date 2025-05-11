from enum import Enum
from typing import Any, Self

from const import Const
from serde import Serde
from obj import Obj, ObjCollection
from geometry import Direction, Vector, Rect
from gamemap import GameMap

class GameObj(Obj):
    SIZE: Vector
    PHASE_COUNT: int = 0
    PHASE_DURATION: int = 1

    pos: Vector
    phaseTick: int = 0

    __serde_fields__ = {"key", "pos", "phaseTick"}

    def __init__(self, pos: Vector = None, *, centeredTo: Rect = None):
        super().__init__()
        if pos is not None:
            self.pos = pos 
        elif centeredTo is not None:
            rect = centeredTo.centered(self.SIZE)
            self.pos = rect.pos
        else:
            self.pos = Vector()

    def getRect(self) -> Rect:
        return Rect(self.pos, self.SIZE)

    def nextPhase(self):
        self.phaseTick = (self.phaseTick + 1) % (self.PHASE_COUNT * self.PHASE_DURATION)

    def getPhase(self) -> int:
        return self.phaseTick // self.PHASE_DURATION % self.PHASE_COUNT if self.PHASE_COUNT else 0

class DirectedObj(GameObj):
    VELOCITY: int

    heading: Direction

    __serde_fields__ = {"key", "pos", "phaseTick", "heading"}

    def __init__(self, pos: Vector = None, *, centeredTo: Rect = None, heading = Direction.UP):
        super().__init__(pos, centeredTo=centeredTo)
        self.heading = heading

class TankState(Enum):
    START = 1
    FIGHT = 2
    DEAD = 3

class Tank(DirectedObj):
    SIZE = Vector(22, 22)
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

class Missle(DirectedObj):
    SIZE = Vector(8, 8)
    VELOCITY = 6

    tankKey: int
    lethal: bool

    def __init__(self, tank: Tank):
        super().__init__(centeredTo=tank.getRect(), heading=tank.heading)

        offset = (Tank.SIZE + Missle.SIZE) // 2
        match tank.heading:
            case Direction.LEFT:
                self.pos -= Vector(x=offset.x)
            case Direction.RIGHT:
                self.pos += Vector(x=offset.x)
            case Direction.UP:
                self.pos -= Vector(y=offset.y)
            case Direction.DOWN:
                self.pos += Vector(y=offset.y)

        self.tankKey = tank.key
        self.lethal = (tank.state == TankState.FIGHT)

class Punch(GameObj):
    SIZE = Vector(16, 16)
    PHASE_COUNT = 1
    PHASE_DURATION = 8

class Boom(GameObj):
    SIZE = Vector(32, 32)
    PHASE_COUNT = 4
    PHASE_DURATION = 8

class GameObjs(Serde):
    tanks: ObjCollection[Tank]
    missles: ObjCollection[Missle]
    punches: ObjCollection[Punch]
    booms: ObjCollection[Boom]

    __serde_fields__ = {"tanks", "missles", "punches", "booms"}

    def __init__(self):
        self.tanks = ObjCollection()
        self.missles = ObjCollection()
        self.punches = ObjCollection()
        self.booms = ObjCollection()

    @classmethod
    def ofDict(cls, data: dict[str, Any]) -> Self:
        self = cls.__new__(cls)
        self.tanks = ObjCollection.ofList(data["tanks"], Tank)
        self.missles = ObjCollection.ofList(data["missles"], Missle)
        self.punches = ObjCollection.ofList(data["punches"], Punch)
        self.booms = ObjCollection.ofList(data["booms"], Boom)
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
    gameObjs: GameObjs

    __serde_fields__ = {"gameObjs", "gameMap"}

    def __init__(self, *, gameObjs: ObjCollection):
        self.gameObjs = gameObjs

class ClientData(Serde):
    playerName: str = None
    gameControls: GameControls

    __serde_fields__ = {"playerName", "gameControls"}

    def __init__(self, *, gameControls: GameControls = None):
        self.gameControls = gameControls
