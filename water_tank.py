from pico2d import *

# 보일러실 위쪽의 물통: 물 공격에 맞을 때마다 유리관 안에 물이 조금씩 차오름. 다 차면 받침대의 빨간 불이 초록으로 바뀜
# 물통 그림은 배경(boiler_bg.png)에 그려져 있고, 차오르는 물과 불빛만 덧그림
FILL_HITS = 5           # 다 차는 데 필요한 물 공격 횟수
FILL_SPEED = 0.8        # 물 높이가 목표 높이까지 올라가는 속도 (초당, 전체 높이에 대한 비율)
WATER_COLOR = (60, 150, 235, 130)
SURFACE_COLOR = (170, 220, 255, 220)
SURFACE_HEIGHT = 2      # 물 표면의 밝은 줄 두께 (이미지 픽셀)
GREEN = (60, 255, 120)


class WaterTank:
    def __init__(self, background, base_box, glass_box, light_boxes):
        # 모두 배경 이미지 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
        # base_box: 받침대 (지나갈 수 없고, 여기에 물 공격이 맞음), glass_box: 물이 차오르는 유리관 안쪽
        # light_boxes: 다 차면 초록으로 바뀌는 받침대의 불빛들
        self.bg = background
        self.bb = self.to_bb(base_box)
        self.glass_box = glass_box
        self.light_boxes = light_boxes
        self.hits = 0          # 맞은 물 공격 횟수
        self.level = 0.0       # 지금 그려지는 물 높이 (0~1)

    def to_bb(self, box):
        left, top, right, bottom = box
        return (self.bg.to_canvas_x(left), self.bg.to_canvas_y(bottom),
                self.bg.to_canvas_x(right), self.bg.to_canvas_y(top))

    def target_level(self):
        return min(1.0, self.hits / FILL_HITS)

    def is_full(self):
        # 물이 다 차오르는 연출까지 끝났는지
        return self.hits >= FILL_HITS and self.level >= 1.0

    def on_fire_hit(self, damage):
        return False  # 불 공격에는 반응 없음 (금속 받침대라 불도 붙지 않음)

    def on_water_hit(self, damage):
        if self.hits < FILL_HITS:
            self.hits += 1

    def update(self, frame_time):
        self.level = min(self.target_level(), self.level + FILL_SPEED * frame_time)

    def get_obstacle(self):
        return self.bb, False, self.on_fire_hit

    def draw(self):
        if self.level > 0:
            left, top, right, bottom = self.glass_box
            water_top = bottom - (bottom - top) * self.level
            draw_rectangle(*self.to_bb((left, water_top, right, bottom)), *WATER_COLOR, filled=True)
            draw_rectangle(*self.to_bb((left, water_top, right, water_top + SURFACE_HEIGHT)),
                           *SURFACE_COLOR, filled=True)
        if self.is_full():
            for box in self.light_boxes:
                draw_rectangle(*self.to_bb(box), *GREEN, 255, filled=True)
