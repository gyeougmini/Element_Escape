import math

from pico2d import *

import game_world
from collision import collide

FIREBALL_SPEED = 500     # 초당 이동 픽셀
FIREBALL_FPS = 12
FIREBALL_FRAMES = 4
FIREBALL_SIZE = 64       # fireball_sheet.png: 4열 x 8행, 프레임 64x64
FIREBALL_SHEET_HEIGHT = 512
# 충돌 박스는 이미지의 불덩이(꼬리 제외) 부분: 지름 약 18px, 프레임 중심에서 진행 방향으로 약 3px 앞
FIREBALL_BB_HALF_SIZE = 9
FIREBALL_BB_FORWARD = 3

LAUNCH_SIZE = 64         # fire_launch.png: 3프레임, 64x64
LAUNCH_FRAMES = 3
LAUNCH_FPS = 20

IMPACT_SIZE = 96         # fire_impact.png: 6프레임, 96x96
IMPACT_FRAMES = 6
IMPACT_FPS = 15

BURNING_SIZE = 64        # burning.png: 4프레임, 64x64
BURNING_FRAMES = 4
BURNING_FPS = 8
BURNING_DURATION = 3.0   # 초

# fireball_sheet.png 행은 오른쪽(0행)부터 반시계 방향으로 45도씩:
# 오른쪽, 오른쪽 위, 위, 왼쪽 위, 왼쪽, 왼쪽 아래, 아래, 오른쪽 아래
FIREBALL_ROW_COUNT = 8


class Fireball:
    image = None

    def __init__(self, x, y, dir_x, dir_y):
        if Fireball.image is None:
            Fireball.image = load_image('sprite_sheet/fireball_sheet.png')
        # (x, y)는 이미지가 그려지는 중심
        self.x, self.y = x, y
        # 날아가는 각도에 가장 가까운 45도 방향의 행을 사용
        angle = math.degrees(math.atan2(dir_y, dir_x))
        self.row = round(angle / 45) % FIREBALL_ROW_COUNT
        length = math.hypot(dir_x, dir_y)
        self.dir_x, self.dir_y = dir_x / length, dir_y / length
        self.vx = self.dir_x * FIREBALL_SPEED
        self.vy = self.dir_y * FIREBALL_SPEED
        self.anim_time = 0.0
        self.alive = True

    def get_bb(self):
        cx = self.x + self.dir_x * FIREBALL_BB_FORWARD
        cy = self.y + self.dir_y * FIREBALL_BB_FORWARD
        return (cx - FIREBALL_BB_HALF_SIZE, cy - FIREBALL_BB_HALF_SIZE,
                cx + FIREBALL_BB_HALF_SIZE, cy + FIREBALL_BB_HALF_SIZE)

    def update(self, frame_time):
        self.anim_time += frame_time
        self.x += self.vx * frame_time
        self.y += self.vy * frame_time
        for bb, burnable in game_world.obstacles:
            if collide(self.get_bb(), bb):
                self.hit(burnable)
                return

    def hit(self, burnable):
        self.alive = False
        game_world.add(FireImpact(self.x, self.y))
        if burnable:
            game_world.add(Burning(self.x, self.y))

    def draw(self):
        col = int(self.anim_time * FIREBALL_FPS) % FIREBALL_FRAMES
        Fireball.image.clip_draw(col * FIREBALL_SIZE,
                                 FIREBALL_SHEET_HEIGHT - (self.row + 1) * FIREBALL_SIZE,
                                 FIREBALL_SIZE, FIREBALL_SIZE, self.x, self.y)


class OneShotEffect:
    """가로로 나열된 프레임을 한 번 재생하고 사라지는 이펙트"""
    images = {}  # 경로별로 한 번만 로드

    def __init__(self, image_path, x, y, size, frames, fps):
        if image_path not in OneShotEffect.images:
            OneShotEffect.images[image_path] = load_image(image_path)
        self.image = OneShotEffect.images[image_path]
        self.x, self.y = x, y
        self.size, self.frames, self.fps = size, frames, fps
        self.anim_time = 0.0
        self.alive = True

    def update(self, frame_time):
        self.anim_time += frame_time
        if self.anim_time * self.fps >= self.frames:
            self.alive = False

    def draw(self):
        col = min(int(self.anim_time * self.fps), self.frames - 1)
        self.image.clip_draw(col * self.size, 0, self.size, self.size, self.x, self.y)


class FireLaunch(OneShotEffect):
    def __init__(self, x, y):
        super().__init__('sprite_sheet/fire_launch.png', x, y,
                         LAUNCH_SIZE, LAUNCH_FRAMES, LAUNCH_FPS)


class FireImpact(OneShotEffect):
    def __init__(self, x, y):
        super().__init__('sprite_sheet/fire_impact.png', x, y,
                         IMPACT_SIZE, IMPACT_FRAMES, IMPACT_FPS)


class Burning:
    image = None

    def __init__(self, x, y):
        if Burning.image is None:
            Burning.image = load_image('sprite_sheet/burning.png')
        self.x, self.y = x, y
        self.time = 0.0
        self.alive = True

    def update(self, frame_time):
        self.time += frame_time
        if self.time >= BURNING_DURATION:
            self.alive = False

    def draw(self):
        col = int(self.time * BURNING_FPS) % BURNING_FRAMES
        Burning.image.clip_draw(col * BURNING_SIZE, 0, BURNING_SIZE, BURNING_SIZE, self.x, self.y)
