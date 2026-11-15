from pico2d import *

import game_world
from fire import Fireball, FIREBALL_SIZE, FIREBALL_SHEET_HEIGHT

# water.png: fireball_sheet.png와 같은 배치 (4열 x 8행, 프레임 64x64, 행은 오른쪽부터 반시계 방향으로 45도씩)
WATER_IMAGE = 'sprite_sheet/sprite_sheet_water/water.png'
WATER_SPEED = 450        # 초당 이동 픽셀
WATER_DAMAGE = 8         # 한 발당 피해
WATER_FPS = 12

# 맞았을 때 물이 튀는 연출: 물방울 그림이 커지며 흐려지다 사라짐 (따로 시트가 없어서 물방울 프레임을 씀)
SPLASH_TIME = 0.3
SPLASH_START_SCALE, SPLASH_END_SCALE = 0.8, 1.8
SPLASH_ROW = 6           # 아래로 떨어지는 물방울 (꼬리가 위로 향한 행)
SPLASH_COUNT = 3         # 몇 갈래로 튀는지
SPLASH_SPREAD = 14       # 갈래끼리 벌어지는 거리(px)


class WaterBall(Fireball):
    """물 공격: 파이어볼처럼 날아가지만 불을 붙이지 않고, 맞은 대상의 불을 끄며 밀어냄.
    상자, 얼음, 자물쇠 같은 물체에는 반응 없이 물만 튐"""
    image = None
    IMAGE_PATH = WATER_IMAGE
    SPEED = WATER_SPEED
    DAMAGE = WATER_DAMAGE
    FPS = WATER_FPS

    def hit_target(self, target):
        self.alive = False
        game_world.add(WaterSplash(self.x, self.y))
        target.on_water_hit(self.dir_x, self.dir_y, self.DAMAGE)

    def hit(self, burnable, on_hit):
        # 물체에 맞으면 불 공격용 반응(on_hit: 불붙음, 녹음 등)은 부르지 않음
        self.alive = False
        game_world.add(WaterSplash(self.x, self.y))


class WaterSplash:
    image = None

    def __init__(self, x, y):
        if WaterSplash.image is None:
            WaterSplash.image = load_image(WATER_IMAGE)
        self.x, self.y = x, y
        self.time = 0.0
        self.alive = True

    def update(self, frame_time):
        self.time += frame_time
        if self.time >= SPLASH_TIME:
            self.alive = False

    def draw(self):
        t = min(1.0, self.time / SPLASH_TIME)
        scale = SPLASH_START_SCALE + (SPLASH_END_SCALE - SPLASH_START_SCALE) * t
        size = FIREBALL_SIZE * scale
        image = WaterSplash.image
        image.opacify(1 - t)  # 이미지 전체의 투명도라서 그린 뒤 원래대로 돌려 놓음
        for i in range(SPLASH_COUNT):
            offset = (i - (SPLASH_COUNT - 1) / 2) * SPLASH_SPREAD * scale
            col = i % 4
            image.clip_draw(col * FIREBALL_SIZE, FIREBALL_SHEET_HEIGHT - (SPLASH_ROW + 1) * FIREBALL_SIZE,
                            FIREBALL_SIZE, FIREBALL_SIZE,
                            self.x + offset, self.y + abs(offset) * 0.3 + 6 * scale * t, size * 0.6, size * 0.6)
        image.opacify(1)
