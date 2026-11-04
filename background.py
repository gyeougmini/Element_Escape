from pico2d import *

BG_IMAGE_HEIGHT = 768
GATE_BASE_IMAGE_Y = 500  # bars_gate.png에서 창살 아래쪽 끝의 y (위에서부터, 픽셀)


class Background:
    def __init__(self, width, height):
        self.image = load_image('sprite_sheet/cell_bg.png')
        # cell_bg.png와 같은 크기(1024x768)의 투명 이미지로, 창살이 감방 경계에 맞춰 그려져 있음
        self.gate_image = load_image('sprite_sheet/bars_gate.png')
        self.width, self.height = width, height
        # 창살 아래쪽 끝의 캔버스 y 좌표: 이보다 위에 발이 있으면 감방 안(창살 뒤)
        self.gate_base_y = (BG_IMAGE_HEIGHT - GATE_BASE_IMAGE_Y) * height / BG_IMAGE_HEIGHT

    def draw(self):
        self.image.draw(self.width // 2, self.height // 2, self.width, self.height)

    def draw_gate(self):
        self.gate_image.draw(self.width // 2, self.height // 2, self.width, self.height)
