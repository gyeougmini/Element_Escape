from pico2d import *

from box import BODY_WIDTH, BODY_HEIGHT, BODY_BOTTOM_MARGIN

# melt_ice.png: 64x96 프레임 11개 (상자와 같은 크기와 배치: 위쪽은 빈 공간, 아래 6px는 그림자)
# 0: 얼음 블록 / 1~3: 금이 가며 녹음 / 4: 작은 조각 / 5~10: 물웅덩이와 김이 점점 사라짐
ICE_IMAGE = 'sprite_sheet/sprit_sheet_object/melt_ice.png'
FRAME_WIDTH, FRAME_HEIGHT = 64, 96
LAST_FRAME = 10
MELT_FPS = 6
PASSABLE_FRAME = 4  # 이 프레임부터는 작은 조각만 남아서 지나갈 수 있음


class IceBlock:
    """얼음 블록: 지나갈 수 없는 물체. 불 공격에 맞으면 녹아 없어짐"""
    image = None

    def __init__(self, background, image_x, image_body_bottom):
        if IceBlock.image is None:
            IceBlock.image = load_image(ICE_IMAGE)
        self.scale_x = background.to_canvas_x(1) - background.to_canvas_x(0)
        self.scale_y = background.to_canvas_y(0) - background.to_canvas_y(1)
        self.x = background.to_canvas_x(image_x)
        self.bottom = background.to_canvas_y(image_body_bottom)
        half_w = BODY_WIDTH / 2 * self.scale_x
        self.bb = (self.x - half_w, self.bottom,
                   self.x + half_w, self.bottom + BODY_HEIGHT * self.scale_y)
        self.melt_time = None  # 녹기 시작한 뒤 흐른 시간, None이면 멀쩡함
        self.alive = True      # False가 되면 목록에서 지움

    def on_fire_hit(self, damage):
        """파이어볼에 맞았을 때 호출. 얼음이 직접 녹으므로 True (불꽃 이펙트를 따로 남기지 않음)"""
        if self.melt_time is None:
            self.melt_time = 0.0
        return True

    def current_frame(self):
        if self.melt_time is None:
            return 0
        return 1 + int(self.melt_time * MELT_FPS)

    def update(self, frame_time):
        if self.melt_time is None:
            return
        self.melt_time += frame_time
        if self.current_frame() > LAST_FRAME:
            self.alive = False

    def foot_y(self):
        return self.bottom

    def get_obstacle(self):
        """(bb, burnable, on_hit), 녹아서 지나갈 수 있으면 None"""
        if self.current_frame() >= PASSABLE_FRAME:
            return None
        return self.bb, True, self.on_fire_hit

    def draw(self):
        frame = min(self.current_frame(), LAST_FRAME)
        w, h = FRAME_WIDTH * self.scale_x, FRAME_HEIGHT * self.scale_y
        frame_bottom = self.bottom - BODY_BOTTOM_MARGIN * self.scale_y
        IceBlock.image.clip_draw(frame * FRAME_WIDTH, 0, FRAME_WIDTH, FRAME_HEIGHT,
                                 self.x, frame_bottom + h / 2, w, h)
