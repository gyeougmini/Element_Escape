from pico2d import *

import game_world

# 증기 폭발: '불타는' 적이 물 공격에 맞거나 '젖은' 적이 불 공격에 맞으면 일어남
#   기존 상태(불타는/젖음)가 풀리고, 적은 공격이 날아온 방향(맞은 반대쪽)으로 보통보다 멀리 밀려남
# steam_animation_alpha.png: steam_animation.png의 체크무늬 배경을 투명하게 바꾼 시트 (128x128 프레임 8개)
#   0: 번쩍임 -> 1~3: 연기가 부풀어 오름 -> 4~7: 고리 모양으로 퍼지며 흐려짐
STEAM_IMAGE = 'sprite_sheet/sprite_sheet_steam/steam_animation_alpha.png'
FRAME_SIZE = 128
FRAMES = 8
FPS = 14
SCALE = 0.9

# 증기 폭발로 밀려나는 정도: 처음 속도에서 0까지 줄어들며 약 (속도 x 시간 / 2)px 이동 (보통 넉백은 약 40px)
KNOCKBACK_SPEED = 600
KNOCKBACK_TIME = 0.4


class SteamExplosion:
    """증기 폭발 연출: 한 번 재생하고 사라짐 (game_world에 넣어 다른 것들 위에 그림)"""
    image = None

    def __init__(self, x, y):
        if SteamExplosion.image is None:
            SteamExplosion.image = load_image(STEAM_IMAGE)
        self.x, self.y = x, y  # 폭발 가운데 (적의 몸통 가운데)
        self.time = 0.0
        self.alive = True

    def update(self, frame_time):
        self.time += frame_time
        if self.time * FPS >= FRAMES:
            self.alive = False

    def draw(self):
        col = min(int(self.time * FPS), FRAMES - 1)
        size = FRAME_SIZE * SCALE
        SteamExplosion.image.clip_draw(col * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE, self.x, self.y, size, size)


def explode_at(hit_bb):
    """적의 몸통 박스(hit_bb) 가운데에서 증기 폭발 연출을 시작"""
    left, bottom, right, top = hit_bb
    game_world.add(SteamExplosion((left + right) / 2, (bottom + top) / 2))
