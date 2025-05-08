from socket import socket, create_connection
import pygame
import os

from const import Const, Color
from config import Config
from geometry import Direction, Pos, Dims
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
    gameObjs: GameObjects
    gameControls: GameControls
    gameState: GameState

    images: Images

    conn: socket

    screen: pygame.Surface
    font: pygame.font.Font
    infoBarHeight: int

    nameInput: NameInput
    sendName: bool
    
    clock: pygame.time.Clock
    tick: int

    running: bool

    def __init__(self):
        self.config = Config(f"{SRC_DIR}/tanks.yaml")

        self.gameMap = GameMap()
        self.gameObjs = GameObjects()
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
        self.infoBarHeight = text.get_height() * 2 + 4

        screenSize = self.gameMap.size * GameMap.BLOCK_SIZE + Dims(0, self.infoBarHeight)
        self.screen = pygame.display.set_mode(screenSize, pygame.HWSURFACE | pygame.DOUBLEBUF, vsync=1)
        
        self.clock = pygame.time.Clock()

        pos = (self.gameMap.size - NameInput.SIZE_IN_BLOCKS) // 2 * GameMap.BLOCK_SIZE + Pos(0, self.infoBarHeight)
        self.nameInput = NameInput(self.screen, self.font, pos, self.config.get("playerName", "PLAYER"))
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

        for tank in self.gameObjs.tanks.values():
            self.drawTank(tank)

        for missle in self.gameObjs.missles.values():
            self.drawDirectedObj(missle, self.images.missles)

        for punch in self.gameObjs.punches.values():
            self.drawAnimatedObj(punch, self.images.punches)

        for boom in self.gameObjs.booms.values():
            self.drawAnimatedObj(boom, self.images.booms)

        self.drawGameMapCamo()
        self.drawNameEditor()

    def drawInfoBar(self):
        statsPos = Pos(0, 0)
        statsWidth = self.gameMap.size.x * GameMap.BLOCK_SIZE // 4
        for tank in self.gameObjs.tanks.values():
            self.drawTankStats(tank, statsPos)
            statsPos += Pos(statsWidth, 0)

    def drawTankStats(self, tank: Tank, pos: Pos):
        pos += Pos(2, 2)

        text = self.font.render(f"{tank.name.upper()}", True, Color.GRAY)
        self.screen.blit(text, pos)
        pos += Pos(0, text.get_height())

        text = self.font.render(f"WINS: {tank.wins}  ", True, Color.GREEN)
        self.screen.blit(text, pos)
        pos += Pos(text.get_width(), 0)

        text = self.font.render(f"FAILS: {tank.fails}", True, Color.RED)
        self.screen.blit(text, pos)

    def drawGameMap(self):
        for i in range(self.gameMap.size.x):
            for j in range(self.gameMap.size.y):
                block = self.gameMap.getBlock(i, j)
                if block in (" ", "x"):
                    self.drawMapBlock(i, j, self.images.ground)
                elif block == "#":
                    self.drawMapBlock(i, j, self.images.concrete)
                elif block == "~":
                    self.drawMapBlock(i, j, self.images.waters[self.tick // 16 % 2])
                elif block in ("1", "2", "3", "4"):
                    self.drawMapBlock(i, j, self.images.bricks[int(block) - 1])

    def drawGameMapCamo(self):
        for i in range(self.gameMap.size.x):
            for j in range(self.gameMap.size.y):
                block = self.gameMap.getBlock(i, j)
                if block == "x":
                    self.drawMapBlock(i, j, self.images.camo)

    def drawMapBlock(self, i: int, j: int, image: pygame.Surface):
        self.drawImage(Box(Pos(i, j) * GameMap.BLOCK_SIZE, GameMap.BLOCK_SIZE), image)

    def drawTank(self, tank: Tank):
        if tank.state == TankState.FIGHT or (tank.state == TankState.START and self.tick // 2 % 6 != 0):
            self.drawDirectedObj(tank, self.images.tanks)

    def drawDirectedObj(self, obj: DirectedObject, images: dict[Direction, pygame.Surface]):
        image = images[obj.heading]
        self.drawImage(obj.getBox(), image)

    def drawAnimatedObj(self, obj: GameObject, images: list[pygame.Surface]):
        image = images[int(obj.animTick / obj.ANIM_DELAY)]
        self.drawImage(obj.getBox(), image)

    def drawImage(self, centeredTo: Box, image: pygame.Surface):
        x = centeredTo.pos.x + (centeredTo.size - image.get_width()) // 2
        y = centeredTo.pos.y + (centeredTo.size - image.get_height()) // 2 + self.infoBarHeight
        rect = image.get_rect(topleft=(x, y))
        self.screen.blit(image, rect)

    def drawNameEditor(self):
        if self.gameState == GameState.NAME_INPUT:
            self.nameInput.draw()

if __name__ == "__main__":
    game = Game()
    game.run()
