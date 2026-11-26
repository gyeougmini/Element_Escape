from pico2d import *

import game_world
import steam

# 수로 가운데 물길 위의 유리판: 처음에는 지나갈 수 없고, 불(용암구체) 공격에 맞으면 물에 급랭되어 돌로 변해
# 물길을 건너는 발판이 됨. 물 공격에는 반응 없음
#
# deep_water_sheet.png: 64x64 칸 4열 x 4행 (256x256)
#   열(단계): 0 유리판 / 1 급랭되며 증기와 거품이 이는 유리판 / 2 막 굳어 아직 뜨거운 돌(주황 균열) / 3 식은 돌 발판
#   행(조각): 0 왼쪽 위 / 1 오른쪽 위 / 2 왼쪽 아래 / 3 오른쪽 아래 -> 네 조각을 2x2로 붙이면 한 장의 판(128x128)
DEEP_WATER_IMAGE = 'sprite_sheet/sprit_sheet_object/deep_water_sheet.png'
TILE_SIZE = 64
SHEET_HEIGHT = 256
GLASS, QUENCH, HOT_STONE, STONE = 0, 1, 2, 3
# (단계 열, 보여주는 시간(초)): 맞은 뒤 이 순서로 바뀌고, 마지막(식은 돌)에서 멈춤
TIMELINE = [(QUENCH, 0.6), (HOT_STONE, 0.9)]
COOL_TIME = sum(duration for _, duration in TIMELINE)  # 이 시간이 지나 식은 돌이 되어야 지나갈 수 있음
BLEND_TIME = 0.2  # 다음 단계로 넘어가기 전 이 시간 동안 다음 단계 그림이 서서히 겹쳐짐
# (조각 행, 판 안의 위치: 가로 0=왼쪽 1=오른쪽, 세로 0=아래 1=위)
PIECES = [(0, 0, 1), (1, 1, 1), (2, 0, 0), (3, 1, 0)]


class GlassBridge:
    image = None

    def __init__(self, background, glass_box, path_box):
        # glass_box: 유리판 그림의 자리, path_box: 유리판이 막고 있는 길 (둘 다 배경 이미지 기준 (left, top, right, bottom))
        if GlassBridge.image is None:
            GlassBridge.image = load_image(DEEP_WATER_IMAGE)
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

    def stages(self):
        """지금 그릴 (단계, 다음 단계, 다음 단계가 겹쳐지는 정도 0~1)"""
        if self.cool_time is None:
            return GLASS, None, 0.0
        t = self.cool_time
        for i, (stage, duration) in enumerate(TIMELINE):
            if t < duration:
                next_stage = TIMELINE[i + 1][0] if i + 1 < len(TIMELINE) else STONE
                blend = max(0.0, (t - (duration - BLEND_TIME)) / BLEND_TIME)
                return stage, next_stage, blend
            t -= duration
        return STONE, None, 0.0

    def draw_panel(self, stage, alpha):
        # 단계 열의 네 조각을 2x2로 붙여 유리판 자리에 맞춰 그림
        left, bottom, right, top = self.glass_bb
        half_w, half_h = (right - left) / 2, (top - bottom) / 2
        GlassBridge.image.opacify(alpha)
        for row, col_x, col_y in PIECES:
            GlassBridge.image.clip_draw(stage * TILE_SIZE, SHEET_HEIGHT - (row + 1) * TILE_SIZE, TILE_SIZE, TILE_SIZE,
                                        left + half_w * (col_x + 0.5), bottom + half_h * (col_y + 0.5),
                                        half_w, half_h)
        GlassBridge.image.opacify(1)

    def draw(self):
        stage, next_stage, blend = self.stages()
        self.draw_panel(stage, 1.0)
        if next_stage is not None and blend > 0:
            self.draw_panel(next_stage, blend)
