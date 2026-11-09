import math
import random

from pico2d import *

from collision import collide_any

# rat_animation.png: 12열 x 8행, 프레임 64x64
# 행(방향)은 카이 시트와 같은 순서, 0~6열 걷기 / 7~8열 물기 / 9열 맞음 / 10~11열 기절
FRAME_SIZE = 64
SHEET_HEIGHT = 512
WALK_FRAMES = 7
WALK_FPS = 12
RAT_SCALE = 1.0
RAT_SPEED = 70  # 초당 이동 픽셀
# 발(그림자) 부분만 충돌 박스로 사용
FOOT_OFFSET = 24      # 그림 중심에서 발 아래쪽 끝까지의 거리
FOOT_HALF_WIDTH = 12
FOOT_HEIGHT = 10

IDLE_TIME = (0.5, 2.0)  # 멈춰 있는 시간 범위(초)
WALK_TIME = (1.0, 3.0)  # 한 방향으로 걷는 시간 범위(초)

# (dir_x, dir_y) -> 시트의 행 번호 (위에서부터), 카이와 같음
DIRECTION_ROWS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}


class Rat:
    """실험 쥐: 멈췄다가 무작위 방향으로 걷기를 반복하며 돌아다님"""
    image = None

    def __init__(self, x, y):
        if Rat.image is None:
            Rat.image = load_image('sprite_sheet_rat/rat_animation.png')
        self.x, self.y = x, y
        self.row = random.randint(0, 7)
        self.dir_x, self.dir_y = 0, 0
        self.anim_time = random.random()  # 쥐마다 걷는 박자가 어긋나도록
        self.start_idle()

    def foot_y(self):
        return self.y - FOOT_OFFSET * RAT_SCALE

    def get_bb(self):
        foot_y = self.foot_y()
        return (self.x - FOOT_HALF_WIDTH, foot_y,
                self.x + FOOT_HALF_WIDTH, foot_y + FOOT_HEIGHT)

    def start_idle(self):
        self.dir_x, self.dir_y = 0, 0
        self.state_time = random.uniform(*IDLE_TIME)

    def start_walk(self):
        self.dir_x, self.dir_y = random.choice(list(DIRECTION_ROWS))
        self.row = DIRECTION_ROWS[(self.dir_x, self.dir_y)]
        self.state_time = random.uniform(*WALK_TIME)

    def is_moving(self):
        return (self.dir_x, self.dir_y) != (0, 0)

    def update(self, frame_time, obstacles):
        self.anim_time += frame_time
        self.state_time -= frame_time
        if self.state_time <= 0:
            if self.is_moving():
                self.start_idle()
            else:
                self.start_walk()
        if not self.is_moving():
            return
        length = math.hypot(self.dir_x, self.dir_y)
        old_x, old_y = self.x, self.y
        self.x += self.dir_x / length * RAT_SPEED * frame_time
        self.y += self.dir_y / length * RAT_SPEED * frame_time
        if collide_any(self.get_bb(), obstacles):
            # 벽이나 물체에 부딪히면 제자리로 돌아가 다른 방향으로 걸음
            self.x, self.y = old_x, old_y
            self.start_walk()

    def draw(self):
        col = int(self.anim_time * WALK_FPS) % WALK_FRAMES if self.is_moving() else 0
        Rat.image.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                            FRAME_SIZE, FRAME_SIZE, self.x, self.y,
                            FRAME_SIZE * RAT_SCALE, FRAME_SIZE * RAT_SCALE)


def spawn_rats(count, areas, obstacles, min_distance=60, max_tries=200):
    """areas(캔버스 좌표 (left, bottom, right, top) 목록) 안의 무작위 위치에 쥐를 count마리 만듦.
    장애물과 겹치거나 다른 쥐와 너무 가까운 자리는 피함"""
    rats = []
    weights = [(r - l) * (t - b) for l, b, r, t in areas]  # 넓은 구역일수록 많이 나오게
    for _ in range(max_tries):
        if len(rats) >= count:
            break
        left, bottom, right, top = random.choices(areas, weights)[0]
        rat = Rat(0, 0)
        rat.x = random.uniform(left, right)
        rat.y = random.uniform(bottom, top) + FOOT_OFFSET * RAT_SCALE  # 발이 구역 안에 오도록
        if collide_any(rat.get_bb(), obstacles):
            continue
        if any(math.hypot(rat.x - other.x, rat.y - other.y) < min_distance for other in rats):
            continue
        rats.append(rat)
    return rats
