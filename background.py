from pico2d import *


class Background:
    def __init__(self, width, height):
        self.image = load_image('sprite_sheet/cell_bg.png')
        self.width, self.height = width, height

    def draw(self):
        self.image.draw(self.width // 2, self.height // 2, self.width, self.height)
