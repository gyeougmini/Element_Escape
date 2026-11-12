from pico2d import *

# burn_box.png: 64x96 프레임 14개
# 0: 원래 상자 / 1: 불붙음 / 2~5: 활활 탐(반복) / 6: 숯이 된 상자 / 7~8: 무너짐 / 9~12: 재 / 13: 연기
BOX_IMAGE = 'sprite_sheet/sprit_sheet_object/burn_box.png'
FRAME_WIDTH, FRAME_HEIGHT = 64, 96
# 프레임 안에서 상자 몸체가 차지하는 부분 (위쪽은 불꽃이 들어갈 빈 공간, 아래 6px는 그림자)
BODY_WIDTH = 52          # x 6~57
BODY_HEIGHT = 60         # 위에서부터 y 30~89
BODY_BOTTOM_MARGIN = 6   # 몸체 아래쪽 끝에서 프레임 아래쪽 끝까지 (그림자)

# 불타는 순서: 불붙음 -> 활활 탐(2~5 반복) -> 6~13을 차례로 한 번 재생하고 사라짐
IGNITE_FRAME, IGNITE_TIME = 1, 0.3
BURN_FRAMES, BURN_FPS, BURN_LOOP_TIME = (2, 3, 4, 5), 8, 3.0
COLLAPSE_FIRST_FRAME, LAST_FRAME, COLLAPSE_FRAME_TIME = 6, 13, 0.25
PASSABLE_FRAME = 7       # 이 프레임부터는 상자 모양이 무너져서 지나갈 수 있음
# 불이 붙고 이 시간(초)이 지나면 8방향으로 맞닿은 상자에 불이 옮겨붙음
SPREAD_TIME = 3.0

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
# 상자 안에 든 것: BOX_POSITIONS의 순서(0부터) -> 'hp'/'ep' 물약, 'rat' 실험 쥐
# 상자가 다 타서 무너지면(PASSABLE_FRAME) 나옴. 쥐는 불에 탄 채로 나와서 '불타는' 상태로 돌아다님
BOX_CONTENTS = {
    1: 'hp',    # 아래쪽 복도 왼쪽 가운데
    4: 'ep',    # 아래쪽 복도 오른쪽 뒷줄 가운데
    2: 'rat',   # 아래쪽 복도 왼쪽 오른쪽 끝
    5: 'rat',   # 아래쪽 복도 오른쪽 뒷줄 오른쪽 끝
    6: 'rat',   # 아래쪽 복도 오른쪽 앞줄 왼쪽
    8: 'rat',   # 오른쪽 복도 뒷줄 왼쪽
}


class Box:
    """나무 상자: 지나갈 수 없는 물체. 불 공격에 맞으면 불타 없어지고, 맞닿은 상자에 불이 번짐"""
    image = None

    def __init__(self, background, image_x, image_body_bottom, content=None):
        if Box.image is None:
            Box.image = load_image(BOX_IMAGE)
        self.image_x, self.image_bottom = image_x, image_body_bottom
        self.scale_x = background.to_canvas_x(1) - background.to_canvas_x(0)
        self.scale_y = background.to_canvas_y(0) - background.to_canvas_y(1)
        self.x = background.to_canvas_x(image_x)
        self.bottom = background.to_canvas_y(image_body_bottom)
        # 충돌 박스는 그림자를 뺀 상자 몸체: 옆 상자의 박스와 딱 맞닿음
        half_w = BODY_WIDTH / 2 * self.scale_x
        self.bb = (self.x - half_w, self.bottom,
                   self.x + half_w, self.bottom + BODY_HEIGHT * self.scale_y)
        self.neighbors = []      # 8방향으로 맞닿은 상자들 (make_boxes가 채움)
        self.burn_time = None    # 불붙은 뒤 흐른 시간, None이면 멀쩡함
        self.spread = False      # 이웃에 불을 옮겼는지
        self.alive = True        # False가 되면 play_mode가 목록에서 지움
        self.content = content   # 안에 든 것 ('hp', 'ep', 'rat' 또는 None)

    def is_touching(self, other):
        # 가로/세로/대각선으로 바로 옆 칸에 있으면 맞닿은 것으로 봄
        return (other is not self
                and abs(self.image_x - other.image_x) <= BODY_WIDTH + 1
                and abs(self.image_bottom - other.image_bottom) <= BODY_HEIGHT + 1)

    def is_burning(self):
        return self.burn_time is not None

    def ignite(self):
        if not self.is_burning():
            self.burn_time = 0.0

    def on_fire_hit(self, damage):
        """파이어볼에 맞았을 때 호출. 상자가 직접 불타므로 True (불꽃 이펙트를 따로 남기지 않음)"""
        self.ignite()
        return True

    def current_frame(self):
        if not self.is_burning():
            return 0
        t = self.burn_time
        if t < IGNITE_TIME:
            return IGNITE_FRAME
        t -= IGNITE_TIME
        if t < BURN_LOOP_TIME:
            return BURN_FRAMES[int(t * BURN_FPS) % len(BURN_FRAMES)]
        t -= BURN_LOOP_TIME
        return COLLAPSE_FIRST_FRAME + int(t / COLLAPSE_FRAME_TIME)

    def update(self, frame_time):
        if not self.is_burning():
            return
        self.burn_time += frame_time
        if not self.spread and self.burn_time >= SPREAD_TIME:
            self.spread = True
            for box in self.neighbors:
                box.ignite()
        if self.current_frame() > LAST_FRAME:
            self.alive = False

    def take_content(self):
        """상자가 무너져 지나갈 수 있게 되면 안에 든 것을 한 번만 돌려줌, 아니면 None"""
        if self.content is None or self.current_frame() < PASSABLE_FRAME:
            return None
        content, self.content = self.content, None
        return content

    def content_pos(self):
        # 안에 든 것이 나올 자리: 상자 몸체 가운데의 (x, y)
        left, bottom, right, top = self.bb
        return (left + right) / 2, (bottom + top) / 2

    def foot_y(self):
        # 캐릭터와 같은 기준으로 앞뒤 순서를 정함
        return self.bottom

    def get_bb(self):
        return self.bb

    def get_obstacle(self):
        """(bb, burnable, on_hit), 무너져서 지나갈 수 있으면 None"""
        if self.current_frame() >= PASSABLE_FRAME:
            return None
        return self.bb, True, self.on_fire_hit

    def draw(self):
        frame = min(self.current_frame(), LAST_FRAME)
        w, h = FRAME_WIDTH * self.scale_x, FRAME_HEIGHT * self.scale_y
        frame_bottom = self.bottom - BODY_BOTTOM_MARGIN * self.scale_y
        Box.image.clip_draw(frame * FRAME_WIDTH, 0, FRAME_WIDTH, FRAME_HEIGHT,
                            self.x, frame_bottom + h / 2, w, h)


def make_boxes(background):
    boxes = [Box(background, x, bottom, BOX_CONTENTS.get(i))
             for i, (x, bottom) in enumerate(BOX_POSITIONS)]
    for box in boxes:
        box.neighbors = [other for other in boxes if box.is_touching(other)]
    return boxes
