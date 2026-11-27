import math

from pico2d import *

from collision import collide

# 워든 맵 오른쪽 위 캡슐 장치: 물의 초능력 알약이 유리관 안에 보관되어 있음
# water_capsule_glass.png: 배경의 유리관 패널(알약을 지운 것), water_pill.png: 알약 (둘 다 warden_bg.png에서 떼어냄)
GLASS_IMAGE = 'sprite_sheet/sprit_sheet_object/water_capsule_glass.png'
PILL_IMAGE = 'sprite_sheet/sprit_sheet_object/water_pill.png'
# 배경 이미지 기준 픽셀 좌표 (위에서부터)
GLASS_BOX = (611, 45, 669, 128)     # 유리 패널이 그려진 자리 (left, top, right, bottom)
INSIDE_BOX = (612, 46, 668, 127)    # 유리가 올라가면 드러나는 관 안쪽
INSIDE_COLOR = (22, 30, 40)
PILL_IN_TUBE = (639, 83)            # 관 안에 있을 때 알약의 가운데
HOVER_GROUND = (640, 262)           # 나온 뒤 떠 있는 자리의 바닥(그림자) 위치: 장치 받침대(아래쪽 끝 188) 앞

OPEN_DELAY = 0.5        # 워든의 쓰러지는 연출이 끝나고 유리관이 열리기까지 기다리는 시간(초)
OPEN_TIME = 1.0         # 유리 패널이 위로 올라가 열리는 시간
RELEASE_TIME = 1.2      # 알약이 관에서 나와 떠 있는 자리까지 날아가는 시간
FLOAT_SCALE = 2.0       # 떠 있을 때 알약 크기 (원래 그림의 배수, 관 안에서는 배경과 같은 크기)
HOVER_HEIGHT = 40       # 떠 있는 알약의 가운데가 그림자(바닥)에서 떨어진 높이(px)
BOB_AMPLITUDE = 6       # 위아래로 움직이는 폭(px)
BOB_PERIOD = 1.6        # 한 번 오르내리는 시간(초)
# 카이의 발이 이 박스(그림자 주변)에 닿으면 알약을 먹음
PICKUP_HALF_WIDTH = 26
PICKUP_HALF_HEIGHT = 14


def ease_in_out(t):
    return t * t * (3 - 2 * t)


class WaterCapsule:
    """워든이 쓰러지면 유리관이 열리고, 물의 초능력 알약이 나와 공중에서 위아래로 떠다님. 카이가 닿으면 먹음"""

    def __init__(self, background):
        self.glass_image = load_image(GLASS_IMAGE)
        self.pill_image = load_image(PILL_IMAGE)
        self.bg = background
        self.scale_x = background.to_canvas_x(1) - background.to_canvas_x(0)
        self.scale_y = background.to_canvas_y(0) - background.to_canvas_y(1)
        self.state = 'closed'  # 'closed' -> 'waiting' -> 'opening' -> 'releasing' -> 'floating' -> 'taken'
        self.time = 0.0        # 지금 상태가 된 뒤 흐른 시간
        self.float_time = 0.0  # 떠다니기 시작한 뒤 흐른 시간 (위아래 움직임에 사용)
        self.ground_x = background.to_canvas_x(HOVER_GROUND[0])
        self.ground_y = background.to_canvas_y(HOVER_GROUND[1])

    def to_bb(self, box):
        left, top, right, bottom = box
        return (self.bg.to_canvas_x(left), self.bg.to_canvas_y(bottom),
                self.bg.to_canvas_x(right), self.bg.to_canvas_y(top))

    def open(self):
        """워든이 쓰러지는 연출이 끝나면 호출: 잠깐 뒤에 유리관이 열림"""
        if self.state == 'closed':
            self.set_state('waiting')

    def set_state(self, state):
        self.state, self.time = state, 0.0

    def is_floating(self):
        return self.state == 'floating'

    def is_taken(self):
        return self.state == 'taken'

    def update(self, frame_time, kai):
        """알약을 먹었으면 True를 돌려줌 (먹은 그 프레임에만)"""
        self.time += frame_time
        if self.state == 'waiting' and self.time >= OPEN_DELAY:
            self.set_state('opening')
        elif self.state == 'opening' and self.time >= OPEN_TIME:
            self.set_state('releasing')
        elif self.state == 'releasing' and self.time >= RELEASE_TIME:
            self.set_state('floating')
        elif self.state == 'floating':
            self.float_time += frame_time
            if collide(self.get_bb(), kai.get_bb()):
                self.set_state('taken')
                return True
        return False

    def get_bb(self):
        # 알약을 먹는 범위: 떠 있는 자리 아래 그림자 주변
        return (self.ground_x - PICKUP_HALF_WIDTH, self.ground_y - PICKUP_HALF_HEIGHT,
                self.ground_x + PICKUP_HALF_WIDTH, self.ground_y + PICKUP_HALF_HEIGHT)

    def foot_y(self):
        # 다른 캐릭터와 앞뒤 순서를 정할 때 쓰는 바닥 위치
        return self.ground_y

    def hover_pos(self):
        bob = math.sin(self.float_time * 2 * math.pi / BOB_PERIOD) * BOB_AMPLITUDE
        return self.ground_x, self.ground_y + HOVER_HEIGHT + bob

    def pill_pos_and_scale(self):
        """(x, y, 원래 그림 대비 가로 배율, 세로 배율), 알약이 보이지 않으면 None"""
        tube_x, tube_y = self.bg.to_canvas_x(PILL_IN_TUBE[0]), self.bg.to_canvas_y(PILL_IN_TUBE[1])
        if self.state in ('waiting', 'opening'):
            return tube_x, tube_y, self.scale_x, self.scale_y
        if self.state == 'releasing':
            # 관에서 살짝 떠올랐다가 앞쪽(아래)의 떠 있는 자리로 내려오며 커짐
            t = ease_in_out(min(1.0, self.time / RELEASE_TIME))
            hover_x, hover_y = self.hover_pos()
            arc = math.sin(t * math.pi) * 30
            sx = self.scale_x + (FLOAT_SCALE - self.scale_x) * t
            sy = self.scale_y + (FLOAT_SCALE - self.scale_y) * t
            return (tube_x + (hover_x - tube_x) * t, tube_y + (hover_y - tube_y) * t + arc, sx, sy)
        if self.state == 'floating':
            x, y = self.hover_pos()
            return x, y, FLOAT_SCALE, FLOAT_SCALE
        return None

    def draw_machine(self):
        """배경 바로 위에 그림: 열리는 유리관과 관 안의 알약"""
        if self.state == 'closed':
            return  # 닫혀 있으면 배경 그림 그대로
        draw_rectangle(*self.to_bb(INSIDE_BOX), *INSIDE_COLOR, 255, filled=True)
        if self.state in ('waiting', 'opening'):
            self.draw_pill()  # 유리 뒤에 있는 알약
        # 유리 패널이 위쪽 덮개 속으로 올라감: 아래쪽부터 드러나도록 위쪽을 잘라서 그림
        rise = 0.0
        if self.state == 'opening':
            rise = ease_in_out(min(1.0, self.time / OPEN_TIME))
        elif self.state != 'waiting':
            rise = 1.0
        h = self.glass_image.h
        visible = int(round(h * (1 - rise)))
        if visible <= 0:
            return
        left, bottom, right, top = self.to_bb(GLASS_BOX)
        draw_h = visible * self.scale_y
        # pico2d는 아래쪽이 원점: 그림의 아래쪽 visible줄을 위쪽에 붙여 그림
        self.glass_image.clip_draw(0, 0, self.glass_image.w, visible,
                                   (left + right) / 2, top - draw_h / 2, right - left, draw_h)

    def draw(self):
        """다른 캐릭터들과 앞뒤 순서를 맞춰 그림: 관에서 나온 뒤의 알약과 그림자"""
        if self.state in ('releasing', 'floating'):
            self.draw_shadow()
            self.draw_pill()

    def draw_shadow(self):
        # 높이 떠오를수록 그림자가 작아짐
        _, y, _, _ = self.pill_pos_and_scale()
        height = max(0.0, y - self.ground_y)
        shrink = max(0.3, 1 - height / 150)
        w, h = 22 * shrink, 5 * shrink
        x, gy = self.ground_x, self.ground_y
        draw_rectangle(x - w, gy - h, x + w, gy + h, 0, 0, 0, 60, filled=True)
        draw_rectangle(x - w * 0.6, gy - h * 1.4, x + w * 0.6, gy + h * 1.4, 0, 0, 0, 50, filled=True)

    def draw_pill(self):
        pos = self.pill_pos_and_scale()
        if pos is None:
            return
        x, y, sx, sy = pos
        w, h = self.pill_image.w, self.pill_image.h
        self.pill_image.draw(x, y, w * sx, h * sy)
