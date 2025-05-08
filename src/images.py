from enum import Enum
import pygame

from geometry import Direction

class Images:
    ground: pygame.Surface
    concrete: pygame.Surface
    bricks: list[pygame.Surface]
    tanks: dict[Direction, pygame.Surface]
    missles: dict[Direction, pygame.Surface]
    # punches: list[pygame.Surface]
    booms: list[pygame.Surface]

    def __init__(self, imageDir: str):
        self.ground = self.loadImage(imageDir, "ground")
        self.concrete = self.loadImage(imageDir, "concrete")
        self.bricks = self.loadImages(imageDir, "bricks-1", "bricks-2", "bricks-3", "bricks-4")
        self.waters = self.loadImages(imageDir, "water-1", "water-2")
        self.camo = self.loadImage(imageDir, "camo")
        self.tanks = self.loadForEnum(imageDir, "tank", Direction)
        self.missles = self.loadForEnum(imageDir, "missle", Direction)
        self.punches = self.loadImages(imageDir, "punch-1")
        self.booms = self.loadImages(imageDir, "boom-1", "boom-2", "boom-3", "boom-4")

    def loadImage(self, imageDir: str, imageName: str) -> pygame.Surface:
        return pygame.image.load(f"{imageDir}/{imageName}.png")

    def loadImages(self, imageDir: str, *imageNames: str) -> list[pygame.Surface]:
        return [self.loadImage(imageDir, name) for name in imageNames]

    def loadForEnum(self, imageDir: str, imageName: str, enum: Enum) -> dict[Enum, pygame.Surface]:
        return {item: self.loadImage(imageDir, f"{imageName}-{str.lower(item.name)}") for item in enum}
