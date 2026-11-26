import os

from pico2d import *

import game_world
import steam

# 수로 가운데 물길 위의 유리판: 처음에는 지나갈 수 없고, 불(용암구체) 공격에 맞으면 물에 급랭되어 돌로 변해
# 물길을 건너는 발판이 됨. 물 공격에는 반응 없음
# 돌 발판 그림(STONE_IMAGE)이 있으면 그것을 유리판 자리에 그리고, 없으면 회색 돌판을 직접 그려 대신함
STONE_IMAGE = 'sprite_sheet/sprit_sheet_object/stone_bridge.png'
COOL_TIME = 1.0  # 맞은 뒤 유리판이 돌로 바뀌어 가는 시간(초). 이 시간이 지나야 지나갈 수 있음

# 그림이 없을 때 그리는 돌판 색
STONE_COLOR = (118, 112, 104)
STONE_EDGE_COLOR = (78, 74, 70)
STONE_LIGHT_COLOR = (150, 144, 134)
STONE_BLOCKS = (2, 3)  # 돌판을 가로 x 세로 몇 장으로 나누어 그릴지


class GlassBridge:
    stone_image = None

    def __init__(self, background, glass_box, path_box):
        # glass_box: 유리판 그림의 자리, path_box: 유리판이 막고 있는 길 (둘 다 배경 이미지 기준 (left, top, right, bottom))
        if GlassBridge.stone_image is None and os.path.exists(STONE_IMAGE):
            GlassBridge.stone_image = load_image(STONE_IMAGE)
        self.glass_bb = self.to_canvas_box(background, glass_box)
        self.path_bb = self.to_canvas_box(background, path_box)
        self.cool_time = None  # 맞은 뒤 흐른 시간, None이면 아직 유리판

    @staticmethod
    def to_canvas_box(background, box):
        left, top, right, bottom = box
        return (background.to_canvas_x(left), background.to_canvas_y(bottom),
                background.to_canvas_x(right), background.to_canvas_y(top))

    def is_glass(self):
        return self.cool_time is None

    def is_stone(self):
        return self.cool_time is not None and self.cool_time >= COOL_TIME

    def on_fire_hit(self, damage):
        # 불(용암구체)에 맞으면 물에 급랭되어 굳기 시작함: 치익 하고 증기가 피어오름
        if self.is_glass():
            self.cool_time = 0.0
            left, bottom, right, top = self.glass_bb
            x, y = (left + right) / 2, (bottom + top) / 2
            game_world.add(steam.SteamExplosion(x, y, x, y))
        return True  # 불꽃 자국은 남기지 않음

    def update(self, frame_time):
        if self.cool_time is not None and not self.is_stone():
            self.cool_time = min(COOL_TIME, self.cool_time + frame_time)

    def get_obstacle(self):
        """(bb, burnable, on_hit), 돌로 다 굳으면 지나갈 수 있으므로 None"""
        if self.is_stone():
            return None
        return (self.path_bb, False, self.on_fire_hit)

    def draw(self):
        # 굳어 가는 동안 돌판이 점점 진해지며 유리판을 덮음
        if self.cool_time is None:
            return
        alpha = self.cool_time / COOL_TIME
        left, bottom, right, top = self.glass_bb
        if GlassBridge.stone_image:
            GlassBridge.stone_image.opacify(alpha)
            GlassBridge.stone_image.draw((left + right) / 2, (bottom + top) / 2, right - left, top - bottom)
            GlassBridge.stone_image.opacify(1)
            return
        a = int(255 * alpha)
        draw_rectangle(left, bottom, right, top, *STONE_EDGE_COLOR, a, filled=True)
        cols, rows = STONE_BLOCKS
        w, h = (right - left) / cols, (top - bottom) / rows
        for c in range(cols):
            for r in range(rows):
                l, b = left + c * w + 2, bottom + r * h + 2
                rr, t = l + w - 4, b + h - 4
                draw_rectangle(l, b, rr, t, *STONE_COLOR, a, filled=True)
                draw_rectangle(l, t - 3, rr, t, *STONE_LIGHT_COLOR, a, filled=True)  # 위쪽 모서리의 밝은 면
