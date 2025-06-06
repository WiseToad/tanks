from geometry import Vector

class Const:
    RECV_BUF_SIZE = 4096

    MAX_PLAYERS = 6
    FPS = 60

    SCREEN_SIZE = Vector(1920, 1080) // 2

    FONT_NAME = "Arial"

    MAP_TTL = FPS * 60 * 5
    FADE_OUT_TICKS = FPS // 2
    FADE_IN_TICKS = FPS // 8

class Color:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (192, 192, 192)
    RED = (192, 0, 0)
    GREEN = (0, 192, 0)
    YELLOW = (192, 192, 0)
