#!/usr/bin/env python

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

    def sendServerData(self, gameMap: GameMap, gameObjs: GameObjs):
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
    gameObjs: GameObjs

    lock: Lock
    running: bool

    def __init__(self):
        self.config = Config(f"{SRC_DIR}/tanks.yaml")

        self.gameMap = GameMap()
        self.gameObjs = GameObjs()
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
        
        if client.gameControls.fire:
            self.shootMissle(client.tank)

    def findFreeSpawn(self) -> Vector:
        spawns = []
        for spawn in self.gameMap.spawns:
            rect = GameMap.getBlockRect(spawn)
            for tank in self.gameObjs.tanks:
                if tank.state == TankState.DEAD or not rect.intersects(tank.getRect()):
                    spawns.append(spawn)

        if not spawns:
            spawns = self.gameMap.spawns

        spawnIdx = randint(0, len(spawns) - 1)
        return spawns[spawnIdx]

    def moveObject(self, obj: DirectedObj, considerWater: bool, dir: Direction = None) -> tuple[int, int] | GameObj | None:
        if dir is not None and dir != obj.heading:
            obj.heading = dir
            return None

        pos = obj.pos
        match obj.heading:
            case Direction.LEFT:
                pos -= Vector(x=obj.VELOCITY)
            case Direction.RIGHT:
                pos += Vector(x=obj.VELOCITY)
            case Direction.UP:
                pos -= Vector(y=obj.VELOCITY)
            case Direction.DOWN:
                pos += Vector(y=obj.VELOCITY)

        match obj.heading:
            case Direction.LEFT:
                p1 = Vector(pos.x, pos.y)
                p2 = Vector(pos.x, pos.y + obj.SIZE.y - 1)
            case Direction.RIGHT:
                p1 = Vector(pos.x + obj.SIZE.x - 1, pos.y)
                p2 = Vector(pos.x + obj.SIZE.x - 1, pos.y + obj.SIZE.y - 1)
            case Direction.UP:
                p1 = Vector(pos.x, pos.y)
                p2 = Vector(pos.x + obj.SIZE.x - 1, pos.y)
            case Direction.DOWN:
                p1 = Vector(pos.x, pos.y + obj.SIZE.y - 1)
                p2 = Vector(pos.x + obj.SIZE.x - 1, pos.y + obj.SIZE.y - 1)

        collided = self.checkCollision(p1, considerWater)
        if collided is None:
            collided = self.checkCollision(p2, considerWater)
        if collided is not None:
            return collided
        
        obj.pos = pos
        return None

    def checkCollision(self, pos: Vector, considerWater: bool) -> Vector | GameObj:
        blockPos = pos // GameMap.BLOCK_SIZE
        block = self.gameMap.getBlock(blockPos)
        if block in GameMap.CONCRETE + GameMap.BRICKS + GameMap.TOWER or (considerWater and block in GameMap.WATER):
            return blockPos
        
        collided = self.getObjectAtPos(pos, self.gameObjs.tanks)
        if collided is not None and collided.state != TankState.DEAD:
            return collided
        
        return None

    def getObjectAtPos(self, pos: Vector, objs: ObjCollection[Obj.T]) -> Obj.T:
        for obj in objs:
            if pos in obj.getRect():
                return obj
        return None

    def getObjectInBox(self, o: GameObj, objs: ObjCollection[Obj.T]) -> Obj.T:
        rect = o.getRect()
        for obj in objs:
            if o.key != obj.key and rect.intersects(obj.getRect()):
                return obj

    def shootMissle(self, tank: Tank) -> Missle:
        if tank.state != TankState.DEAD and tank.missleTick > Tank.MISSLE_DELAY:
            self.gameObjs.missles.add(Missle(tank))
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
            self.animateObjects(self.gameObjs.punches, oneShot=True)
            self.animateObjects(self.gameObjs.booms, oneShot=True)
        finally:
            self.lock.release()

    def handleTanks(self):
        for tank in self.gameObjs.tanks:
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
        rect = GameMap.getBlockRect(spawn).centered(Tank.SIZE)
        tank.pos = rect.pos
        tank.heading = Direction.UP

        tank.state = TankState.START
        tank.stateTick = 0
        tank.missleTick = 0

        tank.health = Tank.INITIAL_HEALTH

    #TODO: refactor this ugly bloated code below
    def moveMissles(self):
        for missle in self.gameObjs.missles:
            collided = self.moveObject(missle, False)
            if collided is None:
                m = self.getObjectInBox(missle, self.gameObjs.missles)
                if m is not None:
                    rect = missle.getRect().union(m.getRect())
                    self.gameObjs.punches.add(Punch(centeredTo=rect))
                    self.gameObjs.missles.remove(missle, lazy=True)
                    self.gameObjs.missles.remove(m, lazy=True)

            else:
                self.gameObjs.punches.add(Punch(centeredTo=missle.getRect()))
                self.gameObjs.missles.remove(missle, lazy=True)

                if missle.lethal:
                    if isinstance(collided, Tank):
                        if collided.state == TankState.FIGHT:
                            collided.health -= 1
                            if collided.health == 0:
                                self.gameObjs.booms.add(Boom(centeredTo=collided.getRect()))
                                collided.state = TankState.DEAD
                                collided.stateTick = 0

                                collided.fails += 1
                                winner = self.gameObjs.tanks.get(missle.tankKey)
                                if winner is not None:
                                    winner.wins += 1

                    if isinstance(collided, Vector): # collided with GameMap block
                        block = self.gameMap.getBlock(collided)
                        if block in GameMap.BRICKS:
                            phase = GameMap.BRICKS.find(block) + 1
                            if phase >= len(GameMap.BRICKS):
                                block = GameMap.GROUND
                                self.gameObjs.booms.add(Boom(centeredTo=GameMap.getBlockRect(collided)))
                            else:
                                block = GameMap.BRICKS[phase]

                            self.gameMap.setBlock(collided, block)
                            self.gameMap.version += 1

        self.gameObjs.missles.purge()

    def animateObjects(self, objs: ObjCollection[GameObj], oneShot: bool = False):
        for obj in objs:
            obj.nextPhase()
            if oneShot and obj.phaseTick == 0:
                objs.remove(obj, lazy=True)
        objs.purge()

if __name__ == "__main__":
    server = Server()
    server.run()
