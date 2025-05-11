from typing import Callable
import pygame
import re

from const import Color
from geometry import Vector, Rect
from gamemap import GameMap

class NameInput:
    SIZE = Vector(8, 1) * GameMap.BLOCK_SIZE
    MAX_NAME_LEN = 10

    screen: pygame.Surface
    font: pygame.font.Font
    pos: Vector

    name: str
    finished: bool

    tick: int = 0

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, pos: Vector, name: str):
        self.screen = screen
        self.font = font
        self.pos = pos

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
        rect = Rect(self.pos, self.SIZE).toTuple()
        pygame.draw.rect(self.screen, Color.BLACK, rect)
        pygame.draw.rect(self.screen, Color.GRAY, rect, 2)

        text = self.font.render("0", True, Color.GRAY)
        textSize = Vector(text.get_width(), text.get_height())

        text = self.font.render("YOUR NAME: ", True, Color.GRAY)
        textPos = Vector(self.pos.x + 4, self.pos.y + (self.SIZE.y - textSize.y) // 2)
        self.screen.blit(text, textPos)
        textPos += Vector(text.get_width(), 0)

        text = self.font.render(self.name, True, Color.WHITE)
        self.screen.blit(text, textPos)
        textPos += Vector(text.get_width(), 0)

        if self.tick % 16 // 8 == 0:
            cursSize = Vector(textSize.x, textSize.y // 4)
            cursRect = (textPos.x, textPos.y + textSize.y - cursSize.y, cursSize.x, cursSize.y)
            pygame.draw.rect(self.screen, Color.WHITE, cursRect)

        self.tick += 1
