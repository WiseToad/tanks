from typing import Callable
import pygame
import re

from const import Color
from geometry import Pos, Dims
from gamemap import GameMap

class NameInput:
    SIZE_IN_BLOCKS = Dims(8, 1)
    MAX_NAME_LEN = 10

    screen: pygame.Surface
    font: pygame.font.Font

    pos: Pos
    size: Dims
    name: str
    finished: bool

    tick: int = 0

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, pos: Pos, name: str):
        self.screen = screen
        self.font = font

        self.pos = pos
        self.size = self.SIZE_IN_BLOCKS * GameMap.BLOCK_SIZE

        self.name = name
        self.finished = False

    def handleKeyDown(self, event):
        if re.fullmatch(r"[\w -]+", event.unicode) is not None:
            if len(self.name) < self.MAX_NAME_LEN:
                self.name += event.unicode.upper()
        else:
            match event.key:
                case pygame.K_BACKSPACE:
                    if len(self.name):
                        self.name = self.name[:-1]
                case pygame.K_RETURN:
                    self.finished = True

    def draw(self):
        rect = (self.pos.x, self.pos.y, self.size.x, self.size.y)
        pygame.draw.rect(self.screen, Color.BLACK, rect)
        pygame.draw.rect(self.screen, Color.GRAY, rect, 2)

        text = self.font.render("0", True, Color.GRAY)
        textSize = Dims(text.get_width(), text.get_height())

        text = self.font.render("YOUR NAME: ", True, Color.GRAY)
        textPos = Pos(self.pos.x + 4, self.pos.y + (self.size.y - textSize.y) // 2)
        self.screen.blit(text, textPos)
        textPos += Pos(text.get_width(), 0)

        text = self.font.render(self.name, True, Color.WHITE)
        self.screen.blit(text, textPos)
        textPos += Pos(text.get_width(), 0)

        if self.tick % 16 // 8 == 0:
            cursSize = Dims(textSize.x, textSize.y // 4)
            cursRect = (textPos.x, textPos.y + textSize.y - cursSize.y, cursSize.x, cursSize.y)
            pygame.draw.rect(self.screen, Color.WHITE, cursRect)

        self.tick += 1
