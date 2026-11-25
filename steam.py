import math
import os

from pico2d import *

import game_world

# 증기 폭발: '불타는' 적이 물 공격에 맞거나 '젖은' 적이 불 공격에 맞으면 일어남
#   기존 상태(불타는/젖음)가 풀리고, 적은 공격이 날아온 방향(맞은 반대쪽)으로 보통보다 멀리 밀려남
#   폭발로 생긴 증기는 약 2초 동안 남아 있다가 흩어지고, 증기 안에 있는 적은 카이를 보지 못해 추적하지 못함
# steam_animation.png: 배경이 투명한 증기 시트 (128x128 프레임 8개)
#   0: 번쩍임 -> 1~3: 연기가 부풀어 오름 -> 4~7: 고리 모양으로 퍼지며 흐려짐
STEAM_IMAGE = 'sprite_sheet/sprite_sheet_steam/steam_animation.png'
OLD_STEAM_IMAGE = 'sprite_sheet/sprite_sheet_steam/steam_animation_alpha.png'  # 이름을 바꾸기 전 파일
FRAME_SIZE = 128
SCALE = 1.3
# 재생 순서: (프레임, 보여주는 시간(초)). 가장 짙은 3번 프레임에서 오래 머물러 증기가 남아 있는 것처럼 보이게 함
TIMELINE = [(0, 0.07), (1, 0.07), (2, 0.07), (3, 1.19), (4, 0.15), (5, 0.15), (6, 0.15), (7, 0.15)]
DURATION = sum(duration for _, duration in TIMELINE)  # 2.0초

# 증기 폭발로 밀려나는 정도: 처음 속도에서 0까지 줄어들며 약 (속도 x 시간 / 2)px 이동 (보통 넉백은 약 40px)
KNOCKBACK_SPEED = 600
KNOCKBACK_TIME = 0.4
KNOCKBACK_DISTANCE = KNOCKBACK_SPEED * KNOCKBACK_TIME / 2
# 증기는 밀려나는 길의 가운데에 생겨서, 밀려난 적이 증기 안에 들어가 있게 함
CLOUD_SHIFT = KNOCKBACK_DISTANCE / 2
# 적의 발이 증기 가운데(바닥 기준)에서 이 거리(px) 안에 있으면 증기 안에 있는 것으로 봄
CLOUD_RADIUS = 80
FADE_START = DURATION - 0.3  # 이때부터는 증기가 다 흩어져 가므로 시야를 가리지 않음

# 둥실둥실: 증기 그림이 위아래로 천천히 오르내림 (시야를 가리는 범위는 그대로)
BOB_AMPLITUDE = 6   # 위아래로 움직이는 폭(px)
BOB_PERIOD = 1.4    # 한 번 오르내리는 데 걸리는 시간(초)
BOB_START = 0.2     # 폭발이 터진 뒤 이때부터 서서히 떠오름


class SteamExplosion:
    """증기 폭발 연출: 약 2초 동안 증기가 남아 있다가 사라짐 (game_world에 넣어 다른 것들 위에 그림)"""
    image = None

    def __init__(self, x, y, ground_x, ground_y):
        if SteamExplosion.image is None:
            path = STEAM_IMAGE if os.path.exists(STEAM_IMAGE) else OLD_STEAM_IMAGE
            SteamExplosion.image = load_image(path)
        self.x, self.y = x, y  # 그림의 가운데 (적의 몸통 높이)
        self.ground_x, self.ground_y = ground_x, ground_y  # 증기가 덮은 바닥의 가운데 (적의 발 높이)
        self.time = 0.0
        self.alive = True

    def update(self, frame_time):
        self.time += frame_time
        if self.time >= DURATION:
            self.alive = False

    def current_frame(self):
        t = self.time
        for frame, duration in TIMELINE:
            if t < duration:
                return frame
            t -= duration
        return TIMELINE[-1][0]

    def covers(self, x, y):
        # 바닥의 (x, y)가 아직 짙은 증기에 덮여 있는지
        return self.time < FADE_START and math.hypot(x - self.ground_x, y - self.ground_y) <= CLOUD_RADIUS

    def bob_offset(self):
        # 터지는 순간에는 제자리, 이후 0.3초에 걸쳐 흔들림이 커지며 위아래로 둥실둥실 움직임
        t = self.time - BOB_START
        if t <= 0:
            return 0.0
        ease = min(1.0, t / 0.3)
        return BOB_AMPLITUDE * ease * math.sin(2 * math.pi * t / BOB_PERIOD)

    def draw(self):
        size = FRAME_SIZE * SCALE
        SteamExplosion.image.clip_draw(self.current_frame() * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE,
                                       self.x, self.y + self.bob_offset(), size, size)

    def draw_range(self):
        # 디버그용: 시야를 가리는 범위
        if self.time < FADE_START:
            draw_circle(int(self.ground_x), int(self.ground_y), CLOUD_RADIUS, 200, 200, 255)


def explode_at(enemy, dir_x, dir_y):
    """enemy 자리에서 증기 폭발을 일으킴. 증기는 밀려나는 방향(dir)으로 길의 가운데에 생김"""
    left, bottom, right, top = enemy.get_hit_bb()
    foot_left, foot_bottom, foot_right, foot_top = enemy.get_bb()
    shift_x, shift_y = dir_x * CLOUD_SHIFT, dir_y * CLOUD_SHIFT
    game_world.add(SteamExplosion((left + right) / 2 + shift_x, (bottom + top) / 2 + shift_y,
                                  (foot_left + foot_right) / 2 + shift_x, (foot_bottom + foot_top) / 2 + shift_y))


def in_steam(entity):
    """entity의 발이 짙은 증기 안에 있는지: 증기 안에서는 카이를 보지 못해 추적하지 못함"""
    left, bottom, right, top = entity.get_bb()
    x, y = (left + right) / 2, (bottom + top) / 2
    return any(isinstance(o, SteamExplosion) and o.covers(x, y) for o in game_world.objects)
