#!/usr/bin/env python

from socket import socket, create_connection
import pygame
import os

from const import Const, Color
from config import Config
from geometry import Direction, Vector
from gamedata import *
from images import Images
from nameinput import NameInput
from bytecodec import toBytes, ofBytes

SRC_DIR = os.path.normpath(os.path.dirname(__file__))
RESOURCE_DIR = os.path.normpath(f"{SRC_DIR}/../resource")

class GameState(Enum):
    NAME_INPUT = 0
    PLAY = 1

class Game:
    config: Config

    gameMap: GameMap
    gameObjs: GameObjs
    gameControls: GameControls
    gameState: GameState

    images: Images

    conn: socket

    screen: pygame.Surface
    font: pygame.font.Font

    gameMapPos: Vector

    nameInput: NameInput
    sendName: bool
    
    clock: pygame.time.Clock
    tick: int

    running: bool

    def __init__(self):
        self.config = Config(f"{SRC_DIR}/tanks.yaml")

        self.gameMap = GameMap()
        self.gameObjs = GameObjs()
        self.gameControls = GameControls()

        self.images = Images(f"{RESOURCE_DIR}/image")

    def run(self):
        host = self.config.get("server", {}).get("host", "localhost")
        port = self.config.get("server", {}).get("port", 5000)
        self.conn = create_connection((host, port), timeout = 1)
        
        self.gameMap = ofBytes(self.conn.recv(Const.RECV_BUF_SIZE), GameMap)
        if self.gameMap is None:
            raise Exception("Failed to get initial data from server")

        pygame.init()
        pygame.display.set_caption("Multiplayer tanks")

        self.font = pygame.font.SysFont(Const.INFOBAR_FONT, Const.INFOBAR_FONT_SIZE, bold=True)

        text = self.font.render("0", True, Color.GRAY)
        infoBarHeight = text.get_height() * 2 + 4
        self.gameMapPos = Vector(0, infoBarHeight)

        screenSize = self.gameMapPos + self.gameMap.size * GameMap.BLOCK_SIZE
        self.screen = pygame.display.set_mode(screenSize, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED, vsync=1)
        
        self.clock = pygame.time.Clock()

        nameInputPos = self.gameMapPos + (self.gameMap.size * GameMap.BLOCK_SIZE - NameInput.SIZE) // 2
        self.nameInput = NameInput(self.screen, self.font, nameInputPos, self.config.get("playerName", "PLAYER"))
        self.sendName = False

        self.gameState = GameState.NAME_INPUT

        self.running = True
        try:
            self.runGame()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

    def runGame(self):
        self.tick = 0
        while self.running:
            self.nextFrame()
            self.tick += 1

            pygame.display.flip()
            self.clock.tick(Const.FPS * 2)
        
        pygame.quit()

    def nextFrame(self):
        if self.tick % 2 == 0:
            self.fetchEvents()
            self.pollKeyboard()
            self.sendClientData()
            self.recvServerData()
        else:
            self.drawFrame()

    def fetchEvents(self):
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    self.running = False
                case pygame.KEYDOWN:
                    self.handleKeyDown(event)

    def handleKeyDown(self, event):
        match self.gameState:
            case GameState.NAME_INPUT:
                self.nameInput.handleKeyDown(event)
                if self.nameInput.finished:
                    self.config.put("playerName", self.nameInput.name)
                    self.config.save(f"{SRC_DIR}/tanks.yaml")
                    self.sendName = True

                    self.gameState = GameState.PLAY

            case GameState.PLAY:
                match event.key:
                    case pygame.K_SPACE:
                        self.gameControls.fire = True

    def pollKeyboard(self):
        self.gameControls.dir = None
        if self.gameState == GameState.PLAY:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.gameControls.dir = Direction.LEFT
            elif keys[pygame.K_RIGHT]:
                self.gameControls.dir = Direction.RIGHT
            elif keys[pygame.K_UP]:
                self.gameControls.dir = Direction.UP
            elif keys[pygame.K_DOWN]:
                self.gameControls.dir = Direction.DOWN

    def sendClientData(self):
        data = ClientData(gameControls=self.gameControls)
        if self.sendName:
            data.playerName = self.nameInput.name

        self.conn.send(toBytes(data))

        self.sendName = False
        self.gameControls.fire = False

    def recvServerData(self):
        data = ofBytes(self.conn.recv(Const.RECV_BUF_SIZE), ServerData)
        if data is None:
            print("Server closed connection")
            self.running = False
            return

        self.gameObjs = data.gameObjs
        if data.gameMap is not None:
            self.gameMap = data.gameMap

    def drawFrame(self):
        self.screen.fill(Color.BLACK)

        self.drawInfoBar()
        self.drawGameMap()

        for tank in self.gameObjs.tanks:
            self.drawTank(tank)

        for missle in self.gameObjs.missles:
            self.drawDirectedObj(missle, self.images.missles)

        for punch in self.gameObjs.punches:
            self.drawAnimatedObj(punch, self.images.punches)

        for boom in self.gameObjs.booms:
            self.drawAnimatedObj(boom, self.images.booms)

        self.drawGameMapCamo()

        if self.gameState == GameState.NAME_INPUT:
            self.nameInput.draw()

    def drawInfoBar(self):
        statsPos = Vector(0, 0)
        statsWidth = self.gameMap.size.x * GameMap.BLOCK_SIZE // 4
        for tank in self.gameObjs.tanks:
            self.drawTankStats(tank, statsPos)
            statsPos += Vector(statsWidth, 0)

    def drawTankStats(self, tank: Tank, pos: Vector):
        pos += Vector(2, 2)

        text = self.font.render(f"{tank.name.upper()}", True, Color.GRAY)
        self.screen.blit(text, pos)
        pos += Vector(0, text.get_height())

        text = self.font.render(f"H: {tank.health}  ", True, Color.YELLOW)
        self.screen.blit(text, pos)
        pos += Vector(text.get_width(), 0)

        text = self.font.render(f"W: {tank.wins}  ", True, Color.GREEN)
        self.screen.blit(text, pos)
        pos += Vector(text.get_width(), 0)

        text = self.font.render(f"D: {tank.fails}", True, Color.RED)
        self.screen.blit(text, pos)

    def drawGameMap(self):
        for i in range(self.gameMap.size.x):
            for j in range(self.gameMap.size.y):
                pos = Vector(i, j)
                block = self.gameMap.getBlock(pos)

                image = None
                if block in GameMap.GROUND + GameMap.CAMO + GameMap.SPAWN:
                    image = self.images.ground
                elif block in GameMap.CONCRETE:
                    image = self.images.concrete
                elif block in GameMap.BRICKS:
                    phase = GameMap.BRICKS.find(block)
                    image = self.images.bricks[phase]
                elif block in GameMap.TOWER:
                    image = self.images.tower
                elif block in GameMap.WATER:
                    phase = self.tick // 16 % 2
                    image = self.images.waters[phase]

                if image is not None:
                    self.drawImage(GameMap.getBlockRect(pos), image)

    def drawGameMapCamo(self):
        for i in range(self.gameMap.size.x):
            for j in range(self.gameMap.size.y):
                pos = Vector(i, j)
                block = self.gameMap.getBlock(pos)
                if block in GameMap.CAMO:
                    self.drawImage(GameMap.getBlockRect(pos), self.images.camo)

    def drawTank(self, tank: Tank):
        if tank.state == TankState.FIGHT or (tank.state == TankState.START and self.tick // 2 % 6 != 0):
            self.drawDirectedObj(tank, self.images.tanks)

    def drawDirectedObj(self, obj: DirectedObj, images: dict[Direction, pygame.Surface]):
        image = images[obj.heading]
        self.drawImage(obj.getRect(), image)

    def drawAnimatedObj(self, obj: GameObj, images: list[pygame.Surface]):
        image = images[obj.getPhase()]
        self.drawImage(obj.getRect(), image)

    def drawImage(self, centeredTo: Rect, image: pygame.Surface):
        rect = self.gameMapPos + centeredTo.centered(Vector.ofTuple(image.get_size()))
        self.screen.blit(image, rect.toTuple()) 

if __name__ == "__main__":
    game = Game()
    game.run()
