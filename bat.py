import math
import random

from pico2d import *

from collision import collide, collide_any

# bat_animation_alpha.png: bat_animation.png의 단색 배경(90, 84, 77)을 투명하게 바꾼 시트
# 21열 x 8행(2688x1024), 프레임 128x128. 행(방향)은 카이 시트와 같은 순서
# 0~3열 날기 / 4열 경계 / 5~6열 돌진 / 7열 활공 / 8열 맞음 / 9~12열 물에 젖어 바닥에 떨어짐
# 13~16열 불타며 날기 / 17~20열 전기 (경계, 돌진, 활공, 전기는 아직 사용하지 않음)
BAT_IMAGE = 'sprite_sheet/sprite_sheet_bat/bat_animation_alpha.png'
FRAME_SIZE = 128
SHEET_HEIGHT = 1024
BAT_SCALE = 0.6      # 그림 크기 배율: 아래의 그림자/몸통 박스, 흔들림 폭도 이 배율에 맞춰 줄어듦
GROUND_MARGIN = 12   # 프레임 아래쪽 끝에서 그림자(바닥에 닿는 점)까지의 거리
FLY_COLS = (0, 1, 2, 3)
BURN_COLS = (13, 14, 15, 16)
WET_COLS = (9, 10, 11, 12)
HIT_COL = 8
FALLEN_COL = 9       # 쓰러졌을 때 (바닥에 떨어진 모습)
FLY_FPS = 10
WET_FPS = 5
BOB_AMPLITUDE = 3 * BAT_SCALE  # 날 때 몸이 위아래로 흔들리는 폭(px)
BOB_PERIOD = 0.8

# 그림자(바닥) 부분의 충돌 박스: 카이와 부딪히는 데, 바닥에 떨어졌을 때 벽에 막히는 데 사용
SHADOW_HALF_WIDTH = 18 * BAT_SCALE
SHADOW_HALF_HEIGHT = 6 * BAT_SCALE
# 공격에 맞는 몸통 박스: 그림자 가운데 기준 (날 때는 공중, 떨어지면 바닥 가까이)
HIT_HALF_WIDTH = 24 * BAT_SCALE
FLY_HIT_BOTTOM, FLY_HIT_TOP = 22 * BAT_SCALE, 70 * BAT_SCALE
WET_HIT_BOTTOM, WET_HIT_TOP = 2 * BAT_SCALE, 48 * BAT_SCALE

BAT_HP = 20
BAT_DAMAGE = 5       # 카이와 부딪혔을 때 카이에게 주는 피해
FLY_SPEED = 90       # 돌아다닐 때 (초당 픽셀)
CHASE_SPEED = 150    # 카이를 추적할 때
CHASE_RANGE = 200    # 박쥐의 그림자 가운데에서 이 거리(px) 안에 카이의 발이 있으면 추적
WANDER_TIME = (1.0, 2.5)  # 한 방향으로 날아가는 시간 범위(초)
# 물 공격에 맞으면 바닥으로 떨어져 '젖음' 상태: WET_TIME 동안 벽과 물체에 막히고 아주 느리게 기어감. 끝나면 다시 날아오름
WET_TIME = 4.0
WET_SPEED = 25
WET_CHASE_SPEED = 35
# 공격에 맞으면 밀려남 (쥐와 같음)
KNOCKBACK_SPEED = 320
KNOCKBACK_TIME = 0.25
# 불 공격에 맞으면 공중에서 '불타는' 상태: 쥐와 같은 방법으로 BURN_TIME 동안 합쳐서 BURN_DAMAGE만큼 지속 피해
BURN_TIME = 3.0
BURN_DAMAGE = 5
# HP가 0이 되면 바닥에 떨어진 모습으로 흐려지며 사라짐
DEATH_TIME = 1.0

# (dir_x, dir_y) -> 시트의 행 번호 (위에서부터), 카이와 같음
DIRECTION_ROWS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}
OCTANT_DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def bb_center(bb):
    left, bottom, right, top = bb
    return (left + right) / 2, (bottom + top) / 2


class Bat:
    """박쥐: 날아다니는 적. 날 때는 벽과 물체 위로도 지나다니고, 가까이 온 카이를 추적함.
    물 공격에 맞으면 바닥에 떨어져 느려지고, 불 공격에 맞으면 공중에서 불타며 지속 피해를 받음"""
    image = None

    def __init__(self, x, y, bounds):
        # (x, y): 그림자(바닥에 닿는 점)의 가운데. bounds: 날아다닐 수 있는 범위 (left, bottom, right, top), 캔버스 좌표
        if Bat.image is None:
            Bat.image = load_image(BAT_IMAGE)
        self.x, self.y = x, y
        self.bounds = bounds
        self.row = random.randint(0, 7)
        self.dir_x, self.dir_y = 0.0, 0.0
        self.anim_time = random.random()  # 박쥐마다 날갯짓 박자가 어긋나도록
        self.hp = BAT_HP
        self.knockback_dir = (0, 0)
        self.knockback_time = 0.0
        self.burn_time = 0.0
        self.burn_damage_left = 0.0
        self.wet_time = 0.0
        self.death_time = 0.0
        self.alive = True  # False가 되면 목록에서 지움
        self.chasing = False
        self.start_wander()

    # ---- 상태 ----
    def is_dead(self):
        return self.hp <= 0

    def is_burning(self):
        return self.burn_time > 0

    def is_wet(self):
        # 젖어서 바닥에 떨어져 있는지
        return self.wet_time > 0

    def is_flying(self):
        return not self.is_wet() and not self.is_dead()

    def is_knocked_back(self):
        return self.knockback_time > 0

    # ---- 위치와 충돌 박스 ----
    def foot_y(self):
        return self.y - SHADOW_HALF_HEIGHT

    def get_bb(self):
        return (self.x - SHADOW_HALF_WIDTH, self.y - SHADOW_HALF_HEIGHT,
                self.x + SHADOW_HALF_WIDTH, self.y + SHADOW_HALF_HEIGHT)

    def get_hit_bb(self):
        bottom, top = (FLY_HIT_BOTTOM, FLY_HIT_TOP) if self.is_flying() else (WET_HIT_BOTTOM, WET_HIT_TOP)
        return (self.x - HIT_HALF_WIDTH, self.y + bottom, self.x + HIT_HALF_WIDTH, self.y + top)

    def distance_to(self, target):
        tx, ty = bb_center(target.get_bb())
        return math.hypot(tx - self.x, ty - self.y)

    # ---- 공격에 맞음 ----
    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp < 1e-6:
            self.hp = 0
        if self.is_dead():
            self.burn_time = 0.0
            self.wet_time = 0.0

    def knock_back(self, dir_x, dir_y):
        self.knockback_dir = (dir_x, dir_y)
        self.knockback_time = KNOCKBACK_TIME

    def on_fireball_hit(self, dir_x, dir_y, damage):
        # 불 공격: 밀려나며 피해를 받고 공중에서 불타는 상태가 됨. 바닥에 떨어져 있었으면 말라서 다시 날아오름
        self.take_damage(damage)
        self.knock_back(dir_x, dir_y)
        if not self.is_dead():
            self.ignite()

    def on_water_hit(self, dir_x, dir_y, damage):
        # 물 공격: 밀려나며 피해를 받고, 불이 꺼지며, 젖어서 바닥으로 떨어짐
        self.take_damage(damage)
        self.knock_back(dir_x, dir_y)
        self.burn_time = 0.0
        self.burn_damage_left = 0.0
        if not self.is_dead():
            self.wet_time = WET_TIME
            self.start_wander()

    def ignite(self):
        self.burn_time = BURN_TIME
        self.burn_damage_left = BURN_DAMAGE
        self.wet_time = 0.0  # 불이 붙으면 말라서 다시 날아오름

    def update_burn(self, frame_time):
        if not self.is_burning():
            return
        # 쥐와 같은 방법: 남은 시간 중 이번 프레임이 차지하는 비율만큼 남은 피해를 줌 (합이 정확히 BURN_DAMAGE)
        damage = self.burn_damage_left * min(frame_time, self.burn_time) / self.burn_time
        self.burn_damage_left -= damage
        self.burn_time -= frame_time
        self.take_damage(damage)
        if self.burn_time <= 0:
            self.hp = round(self.hp, 6)
            self.burn_time = 0.0

    # ---- 움직임 ----
    def start_wander(self):
        angle = random.uniform(0, 2 * math.pi)
        self.dir_x, self.dir_y = math.cos(angle), math.sin(angle)
        self.state_time = random.uniform(*WANDER_TIME)

    def face(self, dx, dy):
        if dx == 0 and dy == 0:
            return
        octant = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.row = DIRECTION_ROWS[OCTANT_DIRECTIONS[octant]]

    def move(self, dx, dy, obstacles):
        """(dx, dy)만큼 움직임. 날 때는 범위 안이면 어디든, 바닥에서는 벽과 물체에 막힘. 막혔으면 True"""
        left, bottom, right, top = self.bounds
        blocked = False
        old_x = self.x
        self.x += dx
        if not (left <= self.x <= right) or (not self.is_flying() and collide_any(self.get_bb(), obstacles)):
            self.x = old_x
            blocked = True
        old_y = self.y
        self.y += dy
        if not (bottom <= self.y <= top) or (not self.is_flying() and collide_any(self.get_bb(), obstacles)):
            self.y = old_y
            blocked = True
        return blocked

    def update(self, frame_time, obstacles, target):
        self.anim_time += frame_time
        if self.is_dead():
            self.death_time += frame_time
            if self.death_time >= DEATH_TIME:
                self.alive = False
            return
        self.update_burn(frame_time)
        if self.is_dead():
            return
        self.wet_time = max(0.0, self.wet_time - frame_time)
        if self.is_knocked_back():
            speed = KNOCKBACK_SPEED * self.knockback_time / KNOCKBACK_TIME
            dx, dy = self.knockback_dir
            self.move(dx * speed * frame_time, dy * speed * frame_time, obstacles)
            self.knockback_time -= frame_time
            return
        if self.distance_to(target) <= CHASE_RANGE:
            # 카이 쪽으로 곧장 다가감 (날 때는 벽 위로도)
            self.chasing = True
            tx, ty = bb_center(target.get_bb())
            dx, dy = tx - self.x, ty - self.y
            length = math.hypot(dx, dy)
            self.face(dx, dy)
            if length > 1 and not collide(self.get_bb(), target.get_bb()):
                speed = CHASE_SPEED if self.is_flying() else WET_CHASE_SPEED
                self.move(dx / length * speed * frame_time, dy / length * speed * frame_time, obstacles)
            return
        if self.chasing:
            self.chasing = False
            self.start_wander()
        self.state_time -= frame_time
        if self.state_time <= 0:
            self.start_wander()
        speed = FLY_SPEED if self.is_flying() else WET_SPEED
        self.face(self.dir_x, self.dir_y)
        if self.move(self.dir_x * speed * frame_time, self.dir_y * speed * frame_time, obstacles):
            self.start_wander()  # 범위 끝이나 (바닥에서는) 벽에 막히면 다른 방향으로

    def touch(self, target):
        """target(카이)과 그림자가 부딪혔으면 박쥐 반대쪽으로 밀어내며 피해를 줌"""
        if self.is_dead() or self.is_knocked_back() or not collide(self.get_bb(), target.get_bb()):
            return
        tx, ty = bb_center(target.get_bb())
        length = math.hypot(tx - self.x, ty - self.y)
        dir_x, dir_y = ((tx - self.x) / length, (ty - self.y) / length) if length else (0, -1)
        target.on_hit(dir_x, dir_y, BAT_DAMAGE)

    # ---- 그리기 ----
    def draw(self):
        size = FRAME_SIZE * BAT_SCALE
        center_y = self.y + (FRAME_SIZE / 2 - GROUND_MARGIN) * BAT_SCALE
        if self.is_dead():
            col = FALLEN_COL
            Bat.image.opacify(max(0.0, 1 - self.death_time / DEATH_TIME))
        elif self.is_knocked_back():
            col = HIT_COL
        elif self.is_wet():
            col = WET_COLS[int(self.anim_time * WET_FPS) % len(WET_COLS)]
        else:
            cols = BURN_COLS if self.is_burning() else FLY_COLS
            col = cols[int(self.anim_time * FLY_FPS) % len(cols)]
            # 날 때는 몸만 살짝 위아래로 흔들림 (그림자는 프레임에 같이 그려져 있어 함께 움직이지만 폭이 작음)
            center_y += math.sin(self.anim_time * 2 * math.pi / BOB_PERIOD) * BOB_AMPLITUDE
        Bat.image.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                            FRAME_SIZE, FRAME_SIZE, self.x, center_y, size, size)
        Bat.image.opacify(1)

    def draw_chase_range(self):
        color = (255, 0, 0) if self.chasing else (255, 220, 0)
        draw_circle(int(self.x), int(self.y), int(CHASE_RANGE), *color)


def spawn_bats(count, areas, bounds, avoid=None, min_distance=80, max_tries=200):
    """areas(캔버스 좌표 (left, bottom, right, top) 목록) 안의 무작위 위치에 박쥐를 count마리 만듦.
    날아다니므로 장애물 위도 괜찮음. avoid: 이 점 (x, y)에서 CHASE_RANGE 밖에만 놓음 (시작하자마자 추적하지 않도록)"""
    bats = []
    weights = [(r - l) * (t - b) for l, b, r, t in areas]
    for _ in range(max_tries):
        if len(bats) >= count:
            break
        left, bottom, right, top = random.choices(areas, weights)[0]
        x, y = random.uniform(left, right), random.uniform(bottom, top)
        if avoid and math.hypot(x - avoid[0], y - avoid[1]) <= CHASE_RANGE:
            continue
        if any(math.hypot(x - b.x, y - b.y) < min_distance for b in bats):
            continue
        bats.append(Bat(x, y, bounds))
    return bats
