#!/usr/bin/env python3

from threading import Thread, Lock
from socket import socket, create_server
from random import randint
import time
import os

from const import Const
from config import Config
from gamedata import *
from geometry import movePos, reverseDir 
from bytecodec import toBytes, ofBytes

SRC_DIR = os.path.normpath(os.path.dirname(__file__))
PROJECT_DIR=os.path.normpath(f"{SRC_DIR}/..")
RESOURCE_DIR = os.path.normpath(f"{PROJECT_DIR}/resource")

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

    mapTtl: int

    lock: Lock
    running: bool

    TANK_OBSTACLES = GameMap.CONCRETE + GameMap.BRICKS + GameMap.TOWER + GameMap.WATER
    MISSLE_OBSTACLES = GameMap.CONCRETE + GameMap.BRICKS + GameMap.TOWER

    def __init__(self):
        self.config = Config(f"{PROJECT_DIR}/tanks.conf")

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
            host = self.config.get("server.host", "localhost")
            port = self.config.get("server.port", 5000)
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
            self.moveObject(client.tank, self.TANK_OBSTACLES, client.gameControls.dir)
        
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

    def moveObject(self, obj: DirectedObj, obstacles: str, dir: Direction = None) -> Vector | GameObj | None:
        if dir is not None and dir != obj.heading:
            obj.heading = dir
            return None

        newPos = movePos(obj.pos, obj.heading, obj.VELOCITY)

        checkCorner = newPos + obj.SIZE - Vector(1, 1)
        checkPts = newPos, Vector(checkCorner.x, newPos.y), checkCorner, Vector(newPos.x, checkCorner.y)

        rect = obj.getRect()
        for pt in checkPts:
            if pt not in rect:
                collided = self.checkCollision(pt, obstacles)
                if collided is not None:
                    return collided

        obj.pos = newPos
        return None

    def checkCollision(self, pos: Vector, obstacles: str) -> Vector | GameObj | None:
        blockPos = pos // GameMap.BLOCK_SIZE
        block = self.gameMap.getBlock(blockPos)
        if block in obstacles:
            return blockPos
        
        tank = self.getObjectAtPos(pos, self.gameObjs.tanks)
        if tank is not None and tank.state != TankState.DEAD:
            return tank
        
        return None

    def getObjectAtPos(self, pos: Vector, objs: ObjCollection[Obj.T]) -> Obj.T:
        return next((o for o in objs if pos in o.getRect()), None)

    def getOverlappedObj(self, obj: GameObj, objs: ObjCollection[Obj.T]) -> Obj.T:
        rect = obj.getRect()
        return next((o for o in objs if o.key != obj.key and rect.intersects(o.getRect())), None)

    def shootMissle(self, tank: Tank) -> Missle:
        if tank.state != TankState.DEAD and tank.missleTick > Tank.MISSLE_DELAY:
            self.gameObjs.missles.add(Missle(tank))
            tank.missleTick = 0

    def runGame(self):
        self.mapTtl = 0
        while self.running:
            self.nextFrame()
            time.sleep(1 / Const.FPS)

    def nextFrame(self):
        self.lock.acquire(timeout=1)
        try:
            self.mapTtl -= 1
            if self.mapTtl <= 0:
                self.reloadMap()

            self.handleTanks()
            self.moveMissles()
            self.animateObjects(self.gameObjs.punches, oneShot=True)
            self.animateObjects(self.gameObjs.booms, oneShot=True)
        finally:
            self.lock.release()

    def reloadMap(self):
        mapVersion = self.gameMap.version
        self.gameMap.load(f"{RESOURCE_DIR}/map/map.txt")
        self.gameMap.version = mapVersion + 1
        self.mapTtl = Const.MAP_TTL

        self.gameObjs.missles.clear()
        self.gameObjs.punches.clear()
        self.gameObjs.booms.clear()
        
        for tank in self.gameObjs.tanks:
            self.spawnTank(tank)

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
            collided = self.moveObject(missle, self.MISSLE_OBSTACLES)
            if collided is None:
                m = self.getOverlappedObj(missle, self.gameObjs.missles)
                if m is not None:
                    rect = missle.getRect().union(m.getRect())
                    self.gameObjs.punches.add(Punch(centeredTo=rect))
                    self.gameObjs.missles.remove(missle, lazy=True)
                    self.gameObjs.missles.remove(m, lazy=True)

            elif isinstance(collided, Vector) and self.gameMap.getBlock(collided) in GameMap.TOWER:
                missle.heading = reverseDir(missle.heading)

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
                                if missle.tankKey == collided.key:
                                    collided.wins -= 1
                                else:
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
