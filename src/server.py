from threading import Thread, Lock
from socket import socket, create_server
from random import randint
import time
import os

from const import Const
from config import Config
from gamedata import *
from bytecodec import toBytes, ofBytes

SRC_DIR = os.path.normpath(os.path.dirname(__file__))
RESOURCE_DIR = os.path.normpath(f"{SRC_DIR}/../resource")

class Client:
    conn: socket
    tank: Tank
    mapVersion: int
    gameControls: GameControls
    disconnected: bool

    def __init__(self, conn: socket):
        self.conn = conn
        self.tank = Tank()
        self.mapVersion = None
        self.gameControls = GameControls()
        self.disconnected = False

    def sendGameMap(self, gameMap: GameMap):
        self.conn.send(toBytes(gameMap))
        self.mapVersion = gameMap.version

    def sendServerData(self, gameMap: GameMap, gameObjs: GameObjects):
        data = ServerData(gameObjs=gameObjs)
        if gameMap.version > self.mapVersion:
            data.gameMap = gameMap
            self.mapVersion = gameMap.version

        self.conn.send(toBytes(data))

    def recvClientData(self):
        data = ofBytes(self.conn.recv(Const.RECV_BUF_SIZE), ClientData)
        if data is None:
            self.disconnected = True
            return
        
        if data.playerName is not None:
            self.tank.name = data.playerName

        if data.gameControls is not None:
            self.gameControls = data.gameControls

class Server:
    config: Config

    gameMap: GameMap
    gameObjs: GameObjects

    lock: Lock
    running: bool

    def __init__(self):
        self.config = Config(f"{SRC_DIR}/tanks.yaml")

        self.gameMap = GameMap()
        self.gameObjs = GameObjects()
        self.lock = Lock()

    def run(self):
        self.running = True
        try:
            thread = Thread(target=self.waitConn)
            thread.start()

            self.runGame()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

    def waitConn(self):
        print("Waiting for connections")

        try:
            host = self.config.get("server", {}).get("host", "localhost")
            port = self.config.get("server", {}).get("port", 5000)
            sock = create_server((host, port), backlog=Const.MAX_PLAYERS)
            sock.settimeout(1)

            while self.running:
                try:
                    conn, addr = sock.accept()
                    thread = Thread(target=self.handleConn, args=(conn, addr))
                    thread.start()
                except TimeoutError:
                    pass
        except:
            self.running = False
            raise

    def handleConn(self, conn: socket, addr: tuple[str, int]):
        print(f"Connected: {addr}")

        try:
            conn.settimeout(10) # if client drags his window, all his threads hang and network exchange stopped completely for this period
            client = Client(conn)

            self.lock.acquire(timeout=1)
            try:
                client.sendGameMap(self.gameMap)
            finally:
                self.lock.release()

            inGame = False
            try:
                while self.running:
                    client.recvClientData()
                    if client.disconnected:
                        break
                    
                    if not inGame and client.tank.name is not None:
                        self.gameObjs.tanks.add(client.tank)
                        self.spawnTank(client.tank)
                        inGame = True

                    self.lock.acquire(timeout=1)
                    try:
                        self.handleGameControls(client)
                        client.sendServerData(self.gameMap, self.gameObjs)
                    finally:
                        self.lock.release()
            finally:
                self.gameObjs.tanks.remove(client.tank)

        finally:
            conn.close()
            print(f"Disconnected: {addr}")

    def handleGameControls(self, client: Client):
        if client.gameControls.dir is not None:
            self.moveObject(client.tank, True, client.gameControls.dir)
        
        if client.gameControls.fire and client.tank.missleTick > Tank.MISSLE_DELAY:
            self.shootMissle(client.tank)

    def findFreeSpawn(self) -> Pos:
        spawns = []
        for spawn in self.gameMap.spawns:
            spawnBox = Box(spawn * GameMap.BLOCK_SIZE, GameMap.BLOCK_SIZE)
            for tank in self.gameObjs.tanks.values():
                if tank.state == TankState.DEAD or not spawnBox.intersects(tank.getBox()):
                    spawns.append(spawn)

        if not spawns:
            spawns = self.gameMap.spawns

        spawnIdx = randint(0, len(spawns) - 1)
        return spawns[spawnIdx]

    def moveObject(self, obj: DirectedObject, considerWater: bool, dir: Direction = None) -> tuple[int, int] | GameObject | None:
        if dir is not None and dir != obj.heading:
            obj.heading = dir
            return None

        pos = obj.pos.move(obj.heading, obj.VELOCITY)
        match obj.heading:
            case Direction.LEFT:
                p1 = Pos(pos.x, pos.y)
                p2 = Pos(pos.x, pos.y + obj.BOX_SIZE - 1)
            case Direction.RIGHT:
                p1 = Pos(pos.x + obj.BOX_SIZE - 1, pos.y)
                p2 = Pos(pos.x + obj.BOX_SIZE - 1, pos.y + obj.BOX_SIZE - 1)
            case Direction.UP:
                p1 = Pos(pos.x, pos.y)
                p2 = Pos(pos.x + obj.BOX_SIZE - 1, pos.y)
            case Direction.DOWN:
                p1 = Pos(pos.x, pos.y + obj.BOX_SIZE - 1)
                p2 = Pos(pos.x + obj.BOX_SIZE - 1, pos.y + obj.BOX_SIZE - 1)

        collided = self.checkCollision(p1, considerWater)
        if collided is None:
            collided = self.checkCollision(p2, considerWater)
        if collided is not None:
            return collided
        
        obj.pos = pos
        return None

    def checkCollision(self, pos: Pos, considerWater: bool) -> Pos | GameObject:
        i = pos.x // GameMap.BLOCK_SIZE
        j = pos.y // GameMap.BLOCK_SIZE
        block = self.gameMap.getBlock(i, j)
        if block in ("#", "1", "2", "3", "4") or (considerWater and block == "~"):
            return Pos(i, j)
        
        collided = self.getObjectAt(pos, self.gameObjs.tanks)
        if collided is not None and collided.state != TankState.DEAD:
            return collided
        
        return None

    def getObjectAt(self, pos: Pos, objs: GameDict[GameObject.T]) -> GameObject.T:
        for obj in objs.values():
            if pos in obj.getBox():
                return obj
        return None

    def shootMissle(self, tank: Tank) -> Missle:
        missle = Missle.ofTank(tank)
        self.gameObjs.missles.add(missle)
        tank.missleTick = 0

    def runGame(self):
        self.gameMap.load(f"{RESOURCE_DIR}/map/map.txt")

        while self.running:
            self.nextFrame()
            time.sleep(1 / Const.FPS)

    def nextFrame(self):
        self.lock.acquire(timeout=1)
        try:
            self.handleTanks()
            self.moveMissles()
            self.animateObjects(self.gameObjs.punches)
            self.animateObjects(self.gameObjs.booms)
        finally:
            self.lock.release()

    def handleTanks(self):
        for tank in self.gameObjs.tanks.values():
            tank.stateTick += 1
            tank.missleTick += 1
            match tank.state:
                case TankState.DEAD:
                    if tank.stateTick > Tank.DEAD_DURATION:
                        self.spawnTank(tank)
                case TankState.START:
                    if tank.stateTick > Tank.START_DURATION:
                        tank.state = TankState.FIGHT
                        tank.stateTick = 0

    def spawnTank(self, tank: Tank):
        spawn = self.findFreeSpawn()
        tankBox = Box.centeredTo(Box(spawn * GameMap.BLOCK_SIZE, GameMap.BLOCK_SIZE), Tank.BOX_SIZE)
        tank.pos = tankBox.pos
        tank.heading = Direction.UP

        tank.state = TankState.START
        tank.stateTick = 0
        tank.missleTick = 0

        tank.health = Tank.INITIAL_HEALTH

    def moveMissles(self):
        removed = []
        for missle in self.gameObjs.missles.values():
            collided = self.moveObject(missle, False)
            if collided is not None:
                self.gameObjs.punches.add(Punch.centeredTo(missle))
                removed.append(missle)

                if missle.lethal:
                    if isinstance(collided, Tank):
                        if collided.state == TankState.FIGHT:
                            collided.health -= 1
                            if collided.health == 0:
                                self.gameObjs.booms.add(Boom.centeredTo(collided))
                                collided.state = TankState.DEAD
                                collided.stateTick = 0

                                collided.fails += 1
                                winner = self.gameObjs.tanks.get(missle.tankKey)
                                if winner is not None:
                                    winner.wins += 1

                    if isinstance(collided, tuple):
                        i, j = collided
                        block = self.gameMap.getBlock(i, j)
                        if block in ("1", "2", "3", "4"):
                            block = str(int(block) - 1)
                            if block == "0":
                                block = " "
                                self.gameObjs.booms.add(Boom.centeredToBox(Box(Pos(i, j) * GameMap.BLOCK_SIZE, GameMap.BLOCK_SIZE)))

                            self.gameMap.setBlock(i, j, block)
                            self.gameMap.version += 1

        self.gameObjs.missles.remove(*removed)

    def animateObjects(self, objs: GameDict[GameObject]):
        removed = []
        for obj in objs.values():
            obj.animTick += 1
            if obj.animTick >= obj.ANIM_COUNT * obj.ANIM_DELAY:
                removed.append(obj)
        objs.remove(*removed)

if __name__ == "__main__":
    server = Server()
    server.run()
