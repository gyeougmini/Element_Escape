from pico2d import *

# burn_box.png: 64x96 프레임 14개 (0: 원래 상자, 1~12: 불타서 재가 됨, 13: 연기). 지금은 0번 프레임만 사용
BOX_IMAGE = 'sprit_sheet_object/burn_box.png'
FRAME_WIDTH, FRAME_HEIGHT = 64, 96
# 프레임 안에서 상자 몸체가 차지하는 부분 (위쪽은 불꽃이 들어갈 빈 공간, 아래 6px는 그림자)
BODY_WIDTH = 52          # x 6~57
BODY_HEIGHT = 60         # 위에서부터 y 30~89
BODY_BOTTOM_MARGIN = 6   # 몸체 아래쪽 끝에서 프레임 아래쪽 끝까지 (그림자)

# 상자 위치: cell_bg.png 기준 (몸체 가운데 x, 몸체 아래쪽 끝 y), 위에서부터의 픽셀 좌표
# 가로는 BODY_WIDTH, 세로는 BODY_HEIGHT 간격으로 놓아 상자끼리 맞닿게 함
BOX_POSITIONS = [
    # 아래쪽 복도 왼쪽
    (235, 566), (287, 566), (339, 566),
    # 아래쪽 복도 오른쪽 (뒷줄 3개, 앞줄 2개)
    (752, 573), (804, 573), (856, 573),
    (752, 633), (804, 633),
    # 오른쪽 복도 (EXIT 아래: 뒷줄 2개, 앞줄 1개)
    (870, 349), (922, 349),
    (870, 409),
]


class Box:
    """나무 상자: 지나갈 수 없는 물체. 배경과 같은 비율로 늘려 그림"""
    image = None

    def __init__(self, background, image_x, image_body_bottom):
        if Box.image is None:
            Box.image = load_image(BOX_IMAGE)
        self.scale_x = background.to_canvas_x(1) - background.to_canvas_x(0)
        self.scale_y = background.to_canvas_y(0) - background.to_canvas_y(1)
        self.x = background.to_canvas_x(image_x)
        self.bottom = background.to_canvas_y(image_body_bottom)
        # 충돌 박스는 그림자를 뺀 상자 몸체: 옆 상자의 박스와 딱 맞닿음
        half_w = BODY_WIDTH / 2 * self.scale_x
        self.bb = (self.x - half_w, self.bottom,
                   self.x + half_w, self.bottom + BODY_HEIGHT * self.scale_y)

    def foot_y(self):
        # 캐릭터와 같은 기준으로 앞뒤 순서를 정함
        return self.bottom

    def get_bb(self):
        return self.bb

    def get_obstacle(self):
        # (bb, burnable, on_hit): 파이어볼에 맞으면 불이 붙음
        return self.bb, True, None

    def draw(self):
        w, h = FRAME_WIDTH * self.scale_x, FRAME_HEIGHT * self.scale_y
        frame_bottom = self.bottom - BODY_BOTTOM_MARGIN * self.scale_y
        Box.image.clip_draw(0, 0, FRAME_WIDTH, FRAME_HEIGHT, self.x, frame_bottom + h / 2, w, h)


def make_boxes(background):
    return [Box(background, x, bottom) for x, bottom in BOX_POSITIONS]
