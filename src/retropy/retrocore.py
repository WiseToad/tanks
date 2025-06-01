from pygame import Surface, BufferProxy
import pygame

class RetroCore:
    surface: Surface
    __fps: int

    def __init__(self, size: tuple[int, int], fps: int):
        pygame.init()
        self.surface = None if size is None else Surface(size, depth=32)
        self.__fps = fps

    def __del__(self):
        pygame.quit()

    def reset(self):
        print("Reset not implemented")

    @property
    def width(self) -> int:
        return self.surface.get_width()

    @property
    def height(self) -> int:
        return self.surface.get_height()

    @property
    def fps(self) -> int:
        return self.__fps

    def nextFrame(self) -> BufferProxy:
        return self.surface.get_view()

    def joypadEvent(self, num: int, button: int, pressed: bool):
        pass

    def keyboardEvent(self, keycode: int, pressed: bool, character: int, modifiers: int):
        pass
