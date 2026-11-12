import math
import random

from pico2d import *

from collision import collide, collide_any

# rat_animation.png: 30열 x 8행(1920x512), 프레임 64x64
# 행(방향)은 카이 시트와 같은 순서, 0~6열 걷기 / 7~8열 물기 / 9열 맞음 / 10~11열 기절
# 12~17열 불 / 18~23열 물 / 24~29열 전기 속성을 띤 걷기 (물/전기는 아직 사용하지 않음)
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

# 파이어볼에 맞는 몸통 박스: 그림 중심 기준. 파이어볼이 카이의 손 높이로 날아오므로 위쪽을 넉넉하게 잡음
HIT_HALF_WIDTH = 18
HIT_BOTTOM, HIT_TOP = -22, 22
# 파이어볼에 맞으면 날아온 방향으로 밀려남: 처음 속도에서 0까지 줄어들며 약 40px 이동
KNOCKBACK_SPEED = 320
KNOCKBACK_TIME = 0.25
HIT_COL = 9  # 맞았을 때 프레임

RAT_HP = 30
RAT_DAMAGE = 5  # 카이와 부딪혔을 때 카이에게 주는 피해
# HP가 0이 되면 밀려난 뒤 기절 프레임(10~11열)을 보여주다가 사라짐
DEATH_COLS = (10, 11)
DEATH_FPS = 4
DEATH_TIME = 1.2

# 파이어볼에 맞으면 '불타는' 상태: BURN_TIME 동안 HP가 조금씩 줄어 합쳐서 BURN_DAMAGE만큼 피해를 받고 빨간(불) 프레임으로 그림
# 불타는 중에 또 맞으면 파이어볼 피해만 받고, 남은 지속 피해는 버린 뒤 처음부터 다시 셈
BURN_TIME = 3.0
BURN_DAMAGE = 5
BURN_FIRST_COL = 12  # 불 걷기 프레임 12~17열
BURN_WALK_FRAMES = 6

IDLE_TIME = (0.5, 2.0)  # 멈춰 있는 시간 범위(초)
WALK_TIME = (1.0, 3.0)  # 한 방향으로 걷는 시간 범위(초)

# 쥐의 발 중심에서 이 거리(px) 안에 카이의 발이 있으면 추적
CHASE_RANGE = 150
CHASE_SPEED = 110  # 추적할 때는 돌아다닐 때보다 빠르게

# (dir_x, dir_y) -> 시트의 행 번호 (위에서부터), 카이와 같음
DIRECTION_ROWS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}
# 오른쪽부터 반시계 방향으로 45도씩의 8방향: 임의의 방향을 가장 가까운 8방향으로 맞출 때 사용
OCTANT_DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def bb_center(bb):
    left, bottom, right, top = bb
    return (left + right) / 2, (bottom + top) / 2


class Rat:
    """실험 쥐: 멈췄다가 무작위 방향으로 걷기를 반복하며 돌아다니고, 카이가 가까이 오면 추적"""
    image = None

    def __init__(self, x, y):
        if Rat.image is None:
            Rat.image = load_image('sprite_sheet/sprite_sheet_rat/rat_animation.png')
        self.x, self.y = x, y
        self.row = random.randint(0, 7)
        self.dir_x, self.dir_y = 0, 0
        self.anim_time = random.random()  # 쥐마다 걷는 박자가 어긋나도록
        self.knockback_dir = (0, 0)
        self.knockback_time = 0.0
        self.hp = RAT_HP
        self.death_time = 0.0
        self.alive = True  # False가 되면 play_mode가 목록에서 지움
        self.chasing = False
        self.burn_time = 0.0  # 불타는 상태가 남은 시간(초), 0이면 불타지 않음
        self.burn_damage_left = 0.0  # 이번 불타는 상태에서 아직 받지 않은 지속 피해
        self.start_idle()

    def foot_y(self):
        return self.y - FOOT_OFFSET * RAT_SCALE

    def get_bb(self):
        foot_y = self.foot_y()
        return (self.x - FOOT_HALF_WIDTH, foot_y,
                self.x + FOOT_HALF_WIDTH, foot_y + FOOT_HEIGHT)

    def get_hit_bb(self):
        return (self.x - HIT_HALF_WIDTH, self.y + HIT_BOTTOM,
                self.x + HIT_HALF_WIDTH, self.y + HIT_TOP)

    def on_fireball_hit(self, dir_x, dir_y, damage):
        # dir: 파이어볼이 날아온 방향(길이 1). 맞은 반대편, 즉 파이어볼 진행 방향으로 밀려남
        self.hp = max(0, self.hp - damage)
        self.knockback_dir = (dir_x, dir_y)
        self.knockback_time = KNOCKBACK_TIME
        if not self.is_dead():
            self.ignite()

    def ignite(self):
        """'불타는' 상태로 만듦. 이미 불타는 중이어도 이전 지속 피해는 버리고 3초를 처음부터 다시 셈"""
        self.burn_time = BURN_TIME
        self.burn_damage_left = BURN_DAMAGE

    def place_feet_at(self, x, y):
        # 발 충돌 박스의 중심이 (x, y)에 오도록 위치를 맞춤
        self.x = x
        self.y = y + FOOT_OFFSET * RAT_SCALE - FOOT_HEIGHT / 2

    def is_dead(self):
        return self.hp <= 0

    def is_burning(self):
        return self.burn_time > 0

    def update_burn(self, frame_time):
        if not self.is_burning():
            return
        if self.is_dead():
            self.burn_time = 0.0
            return
        # 남은 시간 중 이번 프레임이 차지하는 비율만큼 남은 피해를 줌: 마지막 프레임에 남은 피해가 모두 들어가 합이 정확히 BURN_DAMAGE
        damage = self.burn_damage_left * min(frame_time, self.burn_time) / self.burn_time
        self.burn_damage_left -= damage
        self.burn_time -= frame_time
        self.hp -= damage
        if self.hp < 1e-6:  # 소수 계산 오차로 HP가 0에 아주 가깝게 남는 것을 막음
            self.hp = 0
        if self.burn_time <= 0 or self.is_dead():
            self.hp = round(self.hp, 6)  # 소수 오차 정리 (예: 14.9999999 -> 15)
            self.burn_time = 0.0

    def is_knocked_back(self):
        return self.knockback_time > 0

    def touch(self, target):
        """target(카이)과 발이 부딪혔으면 쥐 반대쪽으로 밀어내며 피해를 줌"""
        if self.is_dead() or self.is_knocked_back() or not collide(self.get_bb(), target.get_bb()):
            return
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        length = math.hypot(tx - x, ty - y)
        if length == 0:
            dir_x, dir_y = 0, -1  # 정확히 겹쳐 있으면 아래로 밀어냄
        else:
            dir_x, dir_y = (tx - x) / length, (ty - y) / length
        target.on_hit(dir_x, dir_y, RAT_DAMAGE)

    def start_idle(self):
        self.dir_x, self.dir_y = 0, 0
        self.state_time = random.uniform(*IDLE_TIME)

    def start_walk(self):
        self.dir_x, self.dir_y = random.choice(list(DIRECTION_ROWS))
        self.row = DIRECTION_ROWS[(self.dir_x, self.dir_y)]
        self.state_time = random.uniform(*WALK_TIME)

    def is_moving(self):
        return (self.dir_x, self.dir_y) != (0, 0)

    def update_knockback(self, frame_time, obstacles):
        # 남은 시간에 비례해 속도가 줄어듦. 벽에 막힌 축은 더 밀리지 않음
        speed = KNOCKBACK_SPEED * self.knockback_time / KNOCKBACK_TIME
        dx, dy = self.knockback_dir
        old_x = self.x
        self.x += dx * speed * frame_time
        if collide_any(self.get_bb(), obstacles):
            self.x = old_x
        old_y = self.y
        self.y += dy * speed * frame_time
        if collide_any(self.get_bb(), obstacles):
            self.y = old_y
        self.knockback_time -= frame_time
        if not self.is_knocked_back():
            self.start_idle()

    def distance_to(self, target):
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        return math.hypot(tx - x, ty - y)

    def chase(self, target, frame_time, obstacles):
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        dx, dy = tx - x, ty - y
        # 카이 쪽에 가장 가까운 8방향을 바라봄
        octant = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.dir_x, self.dir_y = OCTANT_DIRECTIONS[octant]
        self.row = DIRECTION_ROWS[(self.dir_x, self.dir_y)]
        if collide(self.get_bb(), target.get_bb()):
            return  # 이미 붙어 있으면 제자리에서 바라보기만 함
        length = math.hypot(dx, dy)
        old_x = self.x
        self.x += dx / length * CHASE_SPEED * frame_time
        if collide_any(self.get_bb(), obstacles):
            self.x = old_x
        old_y = self.y
        self.y += dy / length * CHASE_SPEED * frame_time
        if collide_any(self.get_bb(), obstacles):
            self.y = old_y

    def update(self, frame_time, obstacles, target=None):
        self.anim_time += frame_time
        self.update_burn(frame_time)
        if self.is_knocked_back():
            self.update_knockback(frame_time, obstacles)
            return
        if self.is_dead():
            self.death_time += frame_time
            if self.death_time >= DEATH_TIME:
                self.alive = False
            return
        if target and self.distance_to(target) <= CHASE_RANGE:
            self.chasing = True
            self.chase(target, frame_time, obstacles)
            return
        if self.chasing:
            # 놓치면 잠깐 멈췄다가 다시 돌아다님
            self.chasing = False
            self.start_idle()
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
        if self.is_knocked_back():
            col = HIT_COL
        elif self.is_dead():
            col = DEATH_COLS[int(self.death_time * DEATH_FPS) % len(DEATH_COLS)]
        elif self.is_burning():
            # 불타는 동안은 빨간 불 프레임: 멈춰 있으면 첫 프레임
            col = BURN_FIRST_COL
            if self.is_moving():
                col += int(self.anim_time * WALK_FPS) % BURN_WALK_FRAMES
        elif self.is_moving():
            col = int(self.anim_time * WALK_FPS) % WALK_FRAMES
        else:
            col = 0
        Rat.image.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                            FRAME_SIZE, FRAME_SIZE, self.x, self.y,
                            FRAME_SIZE * RAT_SCALE, FRAME_SIZE * RAT_SCALE)

    def draw_chase_range(self):
        # 디버그용: 추적 범위를 발 중심 기준 원으로 표시 (추적 중이면 빨강, 아니면 노랑)
        x, y = bb_center(self.get_bb())
        color = (255, 0, 0) if self.chasing else (255, 220, 0)
        draw_circle(x, y, int(CHASE_RANGE), *color)


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
