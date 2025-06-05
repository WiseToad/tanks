#!/usr/bin/env python3

from socket import socket, create_connection
import pygame
import os

from retropy.retrocore import RetroCore
from retropy.retrokey import RetroKey
from const import Const, Color
from config import Config
from geometry import Direction, Vector
from gamedata import *
from images import Images
from nameinput import NameInput
from bytecodec import toBytes, ofBytes

SRC_DIR = os.path.normpath(os.path.dirname(__file__))
PROJECT_DIR=os.path.normpath(f"{SRC_DIR}/..")
RESOURCE_DIR = os.path.normpath(f"{PROJECT_DIR}/resource")

def getCore():
    return GameCore()

class GameState(Enum):
    NAME_INPUT = 0
    PLAY = 1

class GameCore(RetroCore):
    config: Config

    gameMap: GameMap
    gameObjs: GameObjs
    gameControls: GameControls
    gameState: GameState
    mapTtl: int

    images: Images

    conn: socket

    font: pygame.font.Font

    infoBatHeight: int
    ttlInfoWidth: int
    gameMapPos: Vector

    nameInput: NameInput
    sendName: bool

    joypadState: set
    joypadPressed: set

    tick: int

    def __init__(self, standalone: bool = False):
        super().__init__(None, Const.FPS)

        self.config = Config(f"{PROJECT_DIR}/tanks.conf")

        self.gameMap = GameMap()
        self.gameObjs = GameObjs()
        self.gameControls = GameControls()

        self.images = Images(f"{RESOURCE_DIR}/image")

        host = self.config["server.host"]
        port = self.config["server.port"]
        self.conn = create_connection((host, port), timeout = 1)

        self.gameMap = ofBytes(self.conn.recv(Const.RECV_BUF_SIZE), GameMap)
        if self.gameMap is None:
            raise Exception("Failed to get initial data from server")

        self.font = pygame.font.SysFont(Const.FONT_NAME, GameMap.BLOCK_SIZE // 2, bold=True)

        text = self.font.render("00:00", True, Color.GRAY)
        self.infoBarHeight = GameMap.BLOCK_SIZE * 3 // 2
        self.ttlInfoWidth = text.get_width() + 4
        self.gameMapPos = Vector(0, self.infoBarHeight)

        if standalone:
            self.surface = pygame.display.set_mode(Const.SCREEN_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED | pygame.FULLSCREEN, vsync=1)
            pygame.display.set_caption("Multiplayer tanks")

            self.gameState = GameState.NAME_INPUT
            self.sendName = False
        else:
            self.surface = pygame.Surface(Const.SCREEN_SIZE, depth=32)

            self.gameState = GameState.PLAY
            self.sendName = True

        nameInputPos = self.gameMapPos + (GameMap.SIZE * GameMap.BLOCK_SIZE - NameInput.SIZE) // 2
        self.nameInput = NameInput(self.surface, self.font, nameInputPos, self.config["player.name"])

        self.joypadState = set()
        self.joypadStateBefore = set()

        self.tick = 0

    def nextFrame(self) -> pygame.BufferProxy:
        self.handleHidState()
        self.sendClientData()
        self.recvServerData()
        self.drawFrame()
        self.tick += 1

        return super().nextFrame()

    def joypadEvent(self, num: int, button: int, pressed: bool):
        if num != 0:
            return
        if pressed:
            self.joypadState.add(button)
        else:
            self.joypadState.discard(button)

    def keyboardEvent(self, keycode: int, pressed: bool, character: int, modifiers: int):
        if self.gameState == GameState.NAME_INPUT:
            self.nameInput.keyboardEvent(keycode, pressed, character, modifiers)

    def handleHidState(self):
        joypadPressed = self.joypadState - self.joypadStateBefore
        self.joypadStateBefore = self.joypadState.copy()

        match self.gameState:
            case GameState.NAME_INPUT:
                if self.nameInput.finished:
                    self.config["player.name"] = self.nameInput.name
                    self.config.write()
                    self.sendName = True

                    self.gameState = GameState.PLAY

            case GameState.PLAY:
                if RetroKey.JOYPAD_A in joypadPressed:
                    self.gameControls.fire = True

                self.gameControls.dir = None
                if RetroKey.JOYPAD_LEFT in self.joypadState:
                    self.gameControls.dir = Direction.LEFT
                elif RetroKey.JOYPAD_RIGHT in self.joypadState:
                    self.gameControls.dir = Direction.RIGHT
                elif RetroKey.JOYPAD_UP in self.joypadState:
                    self.gameControls.dir = Direction.UP
                elif RetroKey.JOYPAD_DOWN in self.joypadState:
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
        self.mapTtl = data.mapTtl

    def drawFrame(self):
        self.surface.fill(Color.BLACK)

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
        statsWidth = (Const.SCREEN_SIZE.x - self.ttlInfoWidth) // Const.MAX_PLAYERS
        for tank in self.gameObjs.tanks:
            self.drawTankStats(tank, statsPos)
            statsPos += Vector(statsWidth, 0)

        self.drawMapTtl()

    def drawTankStats(self, tank: Tank, pos: Vector):
        image = self.images.tanks[tank.color][Direction.UP]
        self.drawImage(image, Rect(pos, Vector(GameMap.BLOCK_SIZE, self.infoBarHeight)))
        pos += Vector(GameMap.BLOCK_SIZE, 0)

        rowHeight = GameMap.BLOCK_SIZE // 2

        text = self.font.render(tank.name.upper(), True, Color.WHITE)
        self.drawImage(text, Rect(pos, Vector(text.get_width(), rowHeight)))
        pos += Vector(0, rowHeight)

        text = self.font.render(f"score: {tank.score}", True, Color.GRAY)
        self.drawImage(text, Rect(pos, Vector(text.get_width(), rowHeight)))
        pos += Vector(0, rowHeight)

        text = self.font.render(f"health: {tank.health}", True, Color.GRAY)
        self.drawImage(text, Rect(pos, Vector(text.get_width(), rowHeight)))

    def drawMapTtl(self):
        mapTtlSec = self.mapTtl // Const.FPS
        text = self.font.render(f"{(mapTtlSec // 60):02d}:{(mapTtlSec % 60):02d}", True, Color.GRAY)
        pos = Vector(Const.SCREEN_SIZE.x - self.ttlInfoWidth + 2, (self.infoBarHeight - text.get_height()) // 2)
        self.surface.blit(text, pos)

    def drawGameMap(self):
        for i in range(GameMap.SIZE.x):
            for j in range(GameMap.SIZE.y):
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
                    phase = self.tick // 8 % 2
                    image = self.images.waters[phase]

                if image is not None:
                    self.drawImage(image, GameMap.getBlockRect(pos) + self.gameMapPos)

    def drawGameMapCamo(self):
        for i in range(GameMap.SIZE.x):
            for j in range(GameMap.SIZE.y):
                pos = Vector(i, j)
                block = self.gameMap.getBlock(pos)
                if block in GameMap.CAMO:
                    self.drawImage(self.images.camo, GameMap.getBlockRect(pos) + self.gameMapPos)

    def drawTank(self, tank: Tank):
        if tank.state == TankState.FIGHT or (tank.state == TankState.START and self.tick % 2 != 0):
            self.drawDirectedObj(tank, self.images.tanks[tank.color])

    def drawDirectedObj(self, obj: DirectedObj, images: dict[Direction, pygame.Surface]):
        image = images[obj.heading]
        self.drawImage(image, obj.getRect() + self.gameMapPos)

    def drawAnimatedObj(self, obj: GameObj, images: list[pygame.Surface]):
        image = images[obj.getPhase()]
        self.drawImage(image, obj.getRect() + self.gameMapPos)

    def drawImage(self, image: pygame.Surface, centeredTo: Rect):
        rect = centeredTo.centered(Vector.ofTuple(image.get_size()))
        self.surface.blit(image, rect.toTuple()) 

# Standalone mode

class Game(GameCore):
    joypadMap = {
        pygame.K_LEFT: RetroKey.JOYPAD_LEFT,
        pygame.K_RIGHT: RetroKey.JOYPAD_RIGHT,
        pygame.K_UP: RetroKey.JOYPAD_UP,
        pygame.K_DOWN: RetroKey.JOYPAD_DOWN,
        pygame.K_SPACE: RetroKey.JOYPAD_A
    }
    keyMap = {
        pygame.K_RETURN: RetroKey.RETROK_RETURN,
        pygame.K_BACKSPACE: RetroKey.RETROK_BACKSPACE
    }

    clock: pygame.time.Clock
    running: bool

    def __init__(self):
        super().__init__(True)
        self.clock = pygame.time.Clock()

    def run(self):
        self.running = True
        try:
            while self.running:
                self.handleEvents()
                self.nextFrame()
                pygame.display.flip()
                self.clock.tick(Const.FPS)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

    def handleEvents(self):
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    self.running = False
                case pygame.KEYDOWN:
                    self.handleKey(event, True)
                case pygame.KEYUP:
                    self.handleKey(event, False)

    def handleKey(self, event: pygame.event.Event, pressed: bool):
        if event.key == pygame.K_ESCAPE:
            self.running = False
            return
        
        button = self.joypadMap.get(event.key)
        if button is not None:
            self.joypadEvent(0, button, pressed)
            return

        key = self.keyMap.get(event.key)
        if key is not None or event.unicode:
            self.keyboardEvent(key, pressed, ord(event.unicode), 0)
            return

if __name__ == "__main__":
    game = Game()
    game.run()
