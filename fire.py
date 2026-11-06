import math

from pico2d import *

import game_world
from collision import collide

FIREBALL_SPEED = 500     # 초당 이동 픽셀
FIREBALL_FPS = 12
FIREBALL_FRAMES = 4
FIREBALL_SIZE = 64       # fireball_sheet.png: 4열 x 8행, 프레임 64x64
FIREBALL_SHEET_HEIGHT = 512
# 바닥 기준 충돌 박스 크기 (벽/물체 충돌 박스가 바닥 면적이므로 같은 기준으로 판정)
FIREBALL_HALF_WIDTH = 8
FIREBALL_HALF_HEIGHT = 4

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

# (dir_x, dir_y) -> fireball_sheet.png 행 번호 (위에서부터)
FIREBALL_ROWS = {
    (1, 0): 0,    # 오른쪽
    (1, 1): 1,    # 오른쪽 위
    (0, 1): 2,    # 위
    (-1, 1): 3,   # 왼쪽 위
    (-1, 0): 4,   # 왼쪽
    (-1, -1): 5,  # 왼쪽 아래
    (0, -1): 6,   # 아래
    (1, -1): 7,   # 오른쪽 아래
}


class Fireball:
    image = None

    def __init__(self, ground_x, ground_y, height, dir_x, dir_y):
        if Fireball.image is None:
            Fireball.image = load_image('sprite_sheet/fireball_sheet.png')
        # 바닥 위치(ground)로 이동/충돌을 계산하고, height만큼 띄워서 그림
        self.x, self.y = ground_x, ground_y
        self.height = height
        self.row = FIREBALL_ROWS[(dir_x, dir_y)]
        length = math.hypot(dir_x, dir_y)
        self.vx = dir_x / length * FIREBALL_SPEED
        self.vy = dir_y / length * FIREBALL_SPEED
        self.anim_time = 0.0
        self.alive = True

    def get_bb(self):
        return (self.x - FIREBALL_HALF_WIDTH, self.y - FIREBALL_HALF_HEIGHT,
                self.x + FIREBALL_HALF_WIDTH, self.y + FIREBALL_HALF_HEIGHT)

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
        draw_y = self.y + self.height
        game_world.add(FireImpact(self.x, draw_y))
        if burnable:
            game_world.add(Burning(self.x, draw_y))

    def draw(self):
        col = int(self.anim_time * FIREBALL_FPS) % FIREBALL_FRAMES
        Fireball.image.clip_draw(col * FIREBALL_SIZE,
                                 FIREBALL_SHEET_HEIGHT - (self.row + 1) * FIREBALL_SIZE,
                                 FIREBALL_SIZE, FIREBALL_SIZE, self.x, self.y + self.height)


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
