from pico2d import *

from collision import draw_bb

BG_IMAGE_WIDTH, BG_IMAGE_HEIGHT = 1024, 768
GATE_BASE_IMAGE_Y = 500  # bars_gate.png에서 창살 아래쪽 끝의 y (위에서부터, 픽셀)

# 통과할 수 없는 벽과 물체: cell_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
OBSTACLES = [
    # 외벽
    (0, 0, 1024, 130),     # 위
    (0, 705, 1024, 768),   # 아래
    (0, 0, 64, 768),       # 왼쪽
    (960, 0, 1024, 768),   # 오른쪽
    # 감방 사이 벽
    (256, 0, 320, 500),    # No.12 | No.07
    (704, 0, 768, 510),    # No.07 | 복도
    # 창살 (아래쪽 끝 부분만)
    (64, 485, 256, 500),   # No.12
    (320, 485, 704, 500),  # No.07
    # No.12 감방
    (84, 130, 176, 295),   # 침대
    # No.07 감방
    (330, 132, 424, 298),  # 침대
    (440, 140, 494, 214),  # 모니터 테이블
    (430, 250, 460, 272),  # 링거 거치대 받침
    (580, 105, 626, 142),  # 세면대
    (640, 100, 690, 175),  # 변기
    (598, 450, 655, 480),  # 식판
    # 복도
    (78, 578, 188, 672),   # 시약 카트
]


class Background:
    def __init__(self, width, height):
        self.image = load_image('sprite_sheet/cell_bg.png')
        # cell_bg.png와 같은 크기(1024x768)의 투명 이미지로, 창살이 감방 경계에 맞춰 그려져 있음
        self.gate_image = load_image('sprite_sheet/bars_gate.png')
        self.width, self.height = width, height
        # 창살 아래쪽 끝의 캔버스 y 좌표: 이보다 위에 발이 있으면 감방 안(창살 뒤)
        self.gate_base_y = self.to_canvas_y(GATE_BASE_IMAGE_Y)
        self.bbs = [(self.to_canvas_x(left), self.to_canvas_y(bottom),
                     self.to_canvas_x(right), self.to_canvas_y(top))
                    for left, top, right, bottom in OBSTACLES]

    def to_canvas_x(self, image_x):
        return image_x * self.width / BG_IMAGE_WIDTH

    def to_canvas_y(self, image_y):
        # 이미지는 위에서부터, pico2d는 아래에서부터 y를 셈
        return (BG_IMAGE_HEIGHT - image_y) * self.height / BG_IMAGE_HEIGHT

    def get_bbs(self):
        return self.bbs

    def draw(self):
        self.image.draw(self.width // 2, self.height // 2, self.width, self.height)

    def draw_gate(self):
        self.gate_image.draw(self.width // 2, self.height // 2, self.width, self.height)

    def draw_bbs(self):
        for bb in self.bbs:
            draw_bb(bb)
