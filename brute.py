import math

from pico2d import *

import steam
from collision import collide, collide_any

# 하수 변이체(brute): 수로 건너편을 좌우로 순찰하다가 카이가 보이면 추적함. 절대 죽지 않음
# 증기 폭발로 생긴 증기가 시선을 가리면 카이를 놓치고("?") 다시 순찰로 돌아감
#
# brute_animation.png: 배경이 투명한 시트 (그림자와 빛 번짐은 반투명으로 남김)
# 49열 x 8행(6272x1024), 프레임 128x128. 행(방향)은 카이 시트와 같은 순서
# 0~5열 걷기 / 6~9열 달리기 / 10열 포효(카이 발견) / 11열 경계 / 12~13열 내려찍기 / 14열 맞음 / 15~18열 두리번("?")
# 19~28열 불타는 상태 / 29~38열 젖음 상태 / 39~48열 감전 상태(아직 사용하지 않음): 각각 걷기 6프레임 + 달리기 4프레임
BRUTE_IMAGE = 'sprite_sheet/sprite_sheet_brute/brute_animation.png'
FRAME_SIZE = 128
SHEET_HEIGHT = 1024
BRUTE_SCALE = 0.9
GROUND_MARGIN = 14    # 프레임 아래쪽 끝에서 발(바닥에 닿는 점)까지의 거리
WALK_COLS = (0, 1, 2, 3, 4, 5)
RUN_COLS = (6, 7, 8, 9)
ROAR_COL = 10
SLAM_COLS = (12, 13)
HIT_COL = 14
CONFUSED_COLS = (15, 16, 17, 18)
# 상태별 걷기/달리기 프레임: 기본 걷기(0~5), 달리기(6~9) 열에 이 값을 더함
BURN_OFFSET = 19
WET_OFFSET = 29
ELECTRIC_OFFSET = 39
# 두리번 프레임(15열)에서 "?"만 있는 부분: 프레임 안 (left, top, right, bottom), 위에서부터의 픽셀 좌표
QUESTION_BOX = (87, 2, 107, 26)
WALK_FPS = 8
RUN_FPS = 10
CONFUSED_FPS = 4

# 발 부분의 충돌 박스와 공격에 맞는 몸통 박스 (발 가운데 기준)
FOOT_HALF_WIDTH = 26 * BRUTE_SCALE
FOOT_HEIGHT = 16 * BRUTE_SCALE
HIT_HALF_WIDTH = 34 * BRUTE_SCALE
HIT_TOP = 92 * BRUTE_SCALE

PATROL_SPEED = 60     # 좌우로 순찰할 때 (초당 픽셀)
CHASE_SPEED = 150     # 카이를 추적할 때: 카이(200)보다 느려서 달아날 수 있음
RETURN_SPEED = 80     # 놓친 뒤 순찰하던 줄로 돌아갈 때
DETECT_RANGE = 215    # 이 거리(px) 안에서 카이가 보이면(증기에 가리지 않으면) 발견
LOSE_RANGE = 315      # 추적 중 카이가 이보다 멀어지거나 증기에 가리면 놓침
ROAR_TIME = 0.5       # 발견했을 때 포효하는 시간(초): 이 동안은 멈춰 있음
CONFUSED_TIME = 1.6   # 놓쳤을 때 두리번거리는 시간(초)

# 내려찍기: 가까이 오면 팔을 들었다가(첫 프레임) 내려찍음(둘째 프레임). 내려찍는 순간 범위 안이면 피해
ATTACK_RANGE = 70
ATTACK_WINDUP = 0.4
ATTACK_RECOVER = 0.35
ATTACK_DAMAGE = 25
ATTACK_COOLDOWN = 1.2
TOUCH_DAMAGE = 10     # 몸에 부딪혔을 때

# 죽지 않지만 쥐처럼 '불타는'/'젖음' 상태가 됨 (피해는 없음): 반대 속성에 맞으면 증기 폭발
BURN_TIME = 3.0
WET_TIME = 4.0
WET_SPEED_RATE = 0.6  # 젖으면 느려짐
FLASH_TIME = 0.15     # 공격에 맞았을 때 맞은 모습을 보여주는 시간

# (dir_x, dir_y) -> 시트의 행 번호 (위에서부터), 카이와 같음
DIRECTION_ROWS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}
OCTANT_DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def bb_center(bb):
    left, bottom, right, top = bb
    return (left + right) / 2, (bottom + top) / 2


class Brute:
    image = None

    def __init__(self, x, y, left_x, right_x, start_dir=1, route=None, sight=None):
        # (x, y): 발 가운데. left_x ~ right_x 사이의 이 줄(y)을 좌우로 순찰함
        # route(x, y, tx, ty): 발 가운데 (x, y)에서 (tx, ty)로 가려면 먼저 향할 곳 (x, y), 갈 수 없으면 None
        #   (예: 물길 건너편은 다리로 돌아가야 하고, 다리가 없으면 갈 수 없음). 없으면 곧장 향함
        if Brute.image is None:
            Brute.image = load_image(BRUTE_IMAGE)
        self.x, self.y = x, y
        self.patrol_y = y
        self.left_x, self.right_x = left_x, right_x
        self.route = route or (lambda x, y, tx, ty: (tx, ty))
        # sight(x, y, tx, ty): 벽에 가리지 않고 볼 수 있는지 (예: 높은 벽돌 벽 너머는 보이지 않음). 없으면 언제나 보임
        self.sight = sight or (lambda x, y, tx, ty: True)
        self.patrol_dir = start_dir
        self.row = DIRECTION_ROWS[(start_dir, 0)]
        self.state = 'patrol'  # patrol, roar, chase, attack, confused, return
        self.state_time = 0.0
        self.anim_time = 0.0
        self.attack_cooldown = 0.0
        self.struck = False    # 이번 내려찍기에서 이미 피해를 주었는지
        self.burn_time = 0.0
        self.wet_time = 0.0
        self.ion_time = 0.0    # '이온화' 상태 남은 시간 (전기 공격이 생기면 ionize로 켬)
        self.flash_time = 0.0
        self.knockback_dir = (0, 0)
        self.knockback_time = 0.0
        self.alive = True      # 죽지 않으므로 항상 True

    # ---- 상태 ----
    def is_dead(self):
        return False  # 절대 죽지 않음

    def is_burning(self):
        return self.burn_time > 0

    def is_wet(self):
        return self.wet_time > 0

    def is_ionized(self):
        return self.ion_time > 0

    def ionize(self, duration):
        self.ion_time = duration

    def is_knocked_back(self):
        return self.knockback_time > 0

    def is_chasing(self):
        return self.state in ('roar', 'chase', 'attack')

    # ---- 위치와 충돌 박스 ----
    def foot_y(self):
        return self.y

    def get_bb(self):
        return (self.x - FOOT_HALF_WIDTH, self.y, self.x + FOOT_HALF_WIDTH, self.y + FOOT_HEIGHT)

    def get_hit_bb(self):
        return (self.x - HIT_HALF_WIDTH, self.y, self.x + HIT_HALF_WIDTH, self.y + HIT_TOP)

    def distance_to(self, target):
        tx, ty = bb_center(target.get_bb())
        x, y = bb_center(self.get_bb())
        return math.hypot(tx - x, ty - y)

    def can_see(self, target, max_range):
        # 거리 안에 있고, 둘 사이의 시선이 증기에 가리지 않으며, 갈 수 있는 곳에 있으면 추적 대상으로 봄
        # (물길 건너편처럼 갈 방법이 없는 곳의 카이는 보여도 쫓지 않음)
        if self.distance_to(target) > max_range:
            return False
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        return (not steam.blocks_sight(x, y, tx, ty) and self.sight(x, y, tx, ty)
                and self.route(x, y, tx, ty) is not None)

    def go_to(self, tx, ty, speed, frame_time, obstacles):
        """발 가운데를 (tx, ty)로 길을 따라 옮김. 다 왔으면 True, 갈 수 없으면 None"""
        x, y = bb_center(self.get_bb())
        waypoint = self.route(x, y, tx, ty)
        if waypoint is None:
            return None
        wx, wy = waypoint
        arrived = self.move_toward(wx, wy - FOOT_HEIGHT / 2, speed, frame_time, obstacles)
        return arrived and waypoint == (tx, ty)

    # ---- 공격에 맞음 (피해는 받지 않음) ----
    def steam_explode(self, dir_x, dir_y):
        # 증기 폭발: 멀리 밀려나고 그 자리에 증기가 피어올라 시선이 가려짐
        self.knockback_dir = (dir_x, dir_y)
        self.knockback_time = steam.KNOCKBACK_TIME
        steam.explode_at(self, dir_x, dir_y)
        if self.state == 'attack':
            self.set_state('chase')

    def on_fireball_hit(self, dir_x, dir_y, damage):
        self.flash_time = FLASH_TIME
        if self.is_wet():
            self.wet_time = 0.0
            self.steam_explode(dir_x, dir_y)
            return
        self.burn_time = BURN_TIME

    def on_water_hit(self, dir_x, dir_y, damage):
        self.flash_time = FLASH_TIME
        if self.is_burning():
            self.burn_time = 0.0
            self.steam_explode(dir_x, dir_y)
            return
        self.wet_time = WET_TIME

    # ---- 움직임 ----
    def set_state(self, state):
        self.state = state
        self.state_time = 0.0

    def face(self, dx, dy):
        if dx == 0 and dy == 0:
            return
        octant = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.row = DIRECTION_ROWS[OCTANT_DIRECTIONS[octant]]

    def move(self, dx, dy, obstacles):
        """x, y를 따로 움직이고 부딪힌 축은 되돌림. 하나라도 막혔으면 True"""
        blocked = False
        old_x = self.x
        self.x += dx
        if collide_any(self.get_bb(), obstacles):
            self.x = old_x
            blocked = dx != 0
        old_y = self.y
        self.y += dy
        if collide_any(self.get_bb(), obstacles):
            self.y = old_y
            blocked = blocked or dy != 0
        return blocked

    def move_toward(self, tx, ty, speed, frame_time, obstacles):
        dx, dy = tx - self.x, ty - self.y
        length = math.hypot(dx, dy)
        if length < 1:
            return True
        self.face(dx, dy)
        step = min(length, speed * frame_time)
        self.move(dx / length * step, dy / length * step, obstacles)
        return False

    def speed_rate(self):
        return WET_SPEED_RATE if self.is_wet() else 1.0

    def update(self, frame_time, obstacles, target):
        self.anim_time += frame_time
        self.state_time += frame_time
        self.attack_cooldown = max(0.0, self.attack_cooldown - frame_time)
        self.burn_time = max(0.0, self.burn_time - frame_time)
        self.wet_time = max(0.0, self.wet_time - frame_time)
        self.ion_time = max(0.0, self.ion_time - frame_time)
        self.flash_time = max(0.0, self.flash_time - frame_time)
        if self.is_knocked_back():
            speed = steam.KNOCKBACK_SPEED * self.knockback_time / steam.KNOCKBACK_TIME
            dx, dy = self.knockback_dir
            self.move(dx * speed * frame_time, dy * speed * frame_time, obstacles)
            self.knockback_time -= frame_time
            return

        # 추적 중에 카이가 멀어지거나 증기에 가리면 놓치고 두리번거림
        if self.state in ('roar', 'chase') and not self.can_see(target, LOSE_RANGE):
            self.set_state('confused')
            return
        # 순찰 중이거나 돌아가는 중에 카이가 보이면 포효하고 추적
        if self.state in ('patrol', 'return', 'confused') and self.can_see(target, DETECT_RANGE):
            tx, ty = bb_center(target.get_bb())
            self.face(tx - self.x, ty - self.y)
            self.set_state('roar')
            return

        if self.state == 'patrol':
            self.update_patrol(frame_time, obstacles)
        elif self.state == 'roar':
            if self.state_time >= ROAR_TIME:
                self.set_state('chase')
        elif self.state == 'chase':
            self.update_chase(frame_time, obstacles, target)
        elif self.state == 'attack':
            self.update_attack(target)
        elif self.state == 'confused':
            if self.state_time >= CONFUSED_TIME:
                self.set_state('return')
        elif self.state == 'return':
            # 순찰하던 줄에서 가장 가까운 곳으로 돌아감
            tx = min(max(self.x, self.left_x), self.right_x)
            arrived = self.go_to(tx, self.patrol_y + FOOT_HEIGHT / 2, RETURN_SPEED * self.speed_rate(), frame_time, obstacles)
            if arrived is not False:  # 도착했거나 (길이 막혀) 갈 수 없으면 그 자리에서 순찰
                self.patrol_y = self.y if arrived is None else self.patrol_y
                self.set_state('patrol')

    def update_patrol(self, frame_time, obstacles):
        self.face(self.patrol_dir, 0)
        blocked = self.move(self.patrol_dir * PATROL_SPEED * self.speed_rate() * frame_time, 0, obstacles)
        # 순찰 범위 끝에 닿거나 막히면 돌아섬
        if blocked or (self.patrol_dir > 0 and self.x >= self.right_x) or (self.patrol_dir < 0 and self.x <= self.left_x):
            self.patrol_dir = -self.patrol_dir

    def update_chase(self, frame_time, obstacles, target):
        tx, ty = bb_center(target.get_bb())
        if self.distance_to(target) <= ATTACK_RANGE and self.attack_cooldown == 0:
            self.face(tx - self.x, ty - self.y)
            self.struck = False
            self.set_state('attack')
            return
        if not collide(self.get_bb(), target.get_bb()):
            # 물길 건너편이면 다리를 거쳐 감
            self.go_to(tx, ty, CHASE_SPEED * self.speed_rate(), frame_time, obstacles)

    def update_attack(self, target):
        # 팔을 든 뒤 내려찍는 순간 카이가 범위 안에 있으면 피해를 주고 밀어냄
        if not self.struck and self.state_time >= ATTACK_WINDUP:
            self.struck = True
            if self.distance_to(target) <= ATTACK_RANGE + 10:
                self.push(target, ATTACK_DAMAGE)
        if self.state_time >= ATTACK_WINDUP + ATTACK_RECOVER:
            self.attack_cooldown = ATTACK_COOLDOWN
            self.set_state('chase')

    def push(self, target, damage):
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        length = math.hypot(tx - x, ty - y)
        dir_x, dir_y = ((tx - x) / length, (ty - y) / length) if length else (0, -1)
        target.on_hit(dir_x, dir_y, damage)

    def touch(self, target):
        """카이와 발이 부딪혔으면 밀어내며 피해를 줌"""
        if self.is_knocked_back() or not collide(self.get_bb(), target.get_bb()):
            return
        self.push(target, TOUCH_DAMAGE)

    # ---- 그리기 ----
    def status_offset(self):
        # 불타는/젖음/이온화 상태의 걷기, 달리기 프레임이 있는 구간 (상태가 없으면 0)
        if self.is_burning():
            return BURN_OFFSET
        if self.is_wet():
            return WET_OFFSET
        if self.is_ionized():
            return ELECTRIC_OFFSET
        return 0

    def current_col(self):
        """(열, 머리 위에 "?"를 덧그려야 하는지)"""
        walk_col = WALK_COLS[int(self.anim_time * WALK_FPS * self.speed_rate()) % len(WALK_COLS)]
        run_col = RUN_COLS[int(self.anim_time * RUN_FPS) % len(RUN_COLS)]
        offset = self.status_offset()
        if offset:
            # 상태가 있으면 시트의 상태별 구간에는 걷기/달리기만 있으므로, 포효, 내려찍기, 맞음, 두리번도
            # 그 구간의 프레임으로 대신해 상태 모습이 잠깐이라도 사라지지 않게 함
            if self.state == 'chase':
                return offset + run_col, False
            if self.state == 'patrol' or self.state == 'return':
                if not (self.is_knocked_back() or self.flash_time > 0):
                    return offset + walk_col, False
            if self.state == 'attack' and self.state_time >= ATTACK_WINDUP:
                return offset + RUN_COLS[2], False  # 내려찍는 순간: 앞으로 내딛는 달리기 프레임
            # 포효, 팔을 드는 중, 맞음, 두리번: 서 있는 프레임 (두리번은 "?"를 덧그림)
            return offset + WALK_COLS[0], self.state == 'confused'
        if self.is_knocked_back() or self.flash_time > 0:
            return HIT_COL, False
        if self.state == 'roar':
            return ROAR_COL, False
        if self.state == 'attack':
            return (SLAM_COLS[0] if self.state_time < ATTACK_WINDUP else SLAM_COLS[1]), False
        if self.state == 'confused':
            return CONFUSED_COLS[int(self.state_time * CONFUSED_FPS) % len(CONFUSED_COLS)], False
        if self.state == 'chase':
            return run_col, False
        return walk_col, False

    def draw(self):
        size = FRAME_SIZE * BRUTE_SCALE
        center_y = self.y + (FRAME_SIZE / 2 - GROUND_MARGIN) * BRUTE_SCALE
        col, question = self.current_col()
        Brute.image.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                              FRAME_SIZE, FRAME_SIZE, self.x, center_y, size, size)
        if question:
            # 두리번 프레임(15열, 0행)의 "?"만 잘라서 같은 자리에 그림. 두리번 프레임처럼 좌우로 살짝 흔들림
            left, top, right, bottom = QUESTION_BOX
            shake = 2 * (int(self.state_time * CONFUSED_FPS) % 2)
            src_bottom = SHEET_HEIGHT - FRAME_SIZE + (FRAME_SIZE - bottom)
            qx = self.x + ((left + right) / 2 + shake - FRAME_SIZE / 2) * BRUTE_SCALE
            qy = center_y + (FRAME_SIZE / 2 - (top + bottom) / 2) * BRUTE_SCALE
            Brute.image.clip_draw(CONFUSED_COLS[0] * FRAME_SIZE + left, src_bottom, right - left, bottom - top,
                                  qx, qy, (right - left) * BRUTE_SCALE, (bottom - top) * BRUTE_SCALE)

    def draw_chase_range(self):
        color = (255, 0, 0) if self.is_chasing() else (255, 220, 0)
        x, y = bb_center(self.get_bb())
        draw_circle(int(x), int(y), DETECT_RANGE, *color)
        if self.is_chasing():
            draw_circle(int(x), int(y), LOSE_RANGE, 255, 120, 120)
