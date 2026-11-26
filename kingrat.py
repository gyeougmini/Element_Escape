import math
import random

from pico2d import *

import game_world
import steam
from collision import collide, collide_any

# 킹 랫: 스테이지 2 보스, 하수 변이체의 우두머리 (HP 600, 크기 128x128, 약점: 증기 폭발 피해 2배)
#   패턴 A: 독 침을 3방향으로 발사 (한 발에 피해 10)
#   패턴 B: 가운데 저수조로 달려가 뛰어들어 잠수 (3초 동안 무적). 물속에서 카이 쪽 가장자리로 헤엄쳐 간 뒤
#           카이를 향해 뛰어올라 덮침 (착지 자리 근처면 피해 25). 착지한 뒤 1.5초 동안 '젖음' 상태
#   패턴 C: HP 50% 이하가 되면 방 가장자리에 화재 타일 4개 생성 (kingrat_mode에서 처리)
#   공략: 튀어나온 뒤 젖어 있을 때 불을 맞혀 증기 폭발을 일으킴. 화재 타일은 물로 꺼서 공간을 확보
#
# kingrat_sheet.png: 배경이 투명한 시트, 37열 x 8행(4736x1024), 프레임 128x128. 행(방향)은 카이 시트와 같은 순서
# 0~5열 걷기 / 6~7열 독 침 준비 / 8열 독 침 발사 / 9~11열 발사 뒤 / 12열 잠수 / 13열 물속(물결) / 14열 떠오름
# 15열 튀어나옴(물기둥) / 16열 물 털기 / 17열 착지 / 18열 맞음
# 19~24열 불타는 상태 / 25~30열 젖음 상태 / 31~36열 감전(이온화) 상태: 각각 걷기 6프레임
KINGRAT_IMAGE = 'sprite_sheet/sprite_sheet_boss/kingrat_sheet.png'
FRAME_SIZE = 128
SHEET_HEIGHT = 1024
KINGRAT_SCALE = 1.0
GROUND_MARGIN = 14   # 프레임 아래쪽 끝에서 발까지의 거리
WALK_COLS = (0, 1, 2, 3, 4, 5)
SPIT_READY_COLS = (6, 7)
SPIT_COL = 8
SPIT_RECOVER_COLS = (9, 10, 11)
DIVE_COL = 12
UNDER_COL = 13
RISE_COL = 14
BURST_COL = 15
SHAKE_COL = 16
LAND_COL = 17
HIT_COL = 18
BURN_OFFSET, WET_OFFSET, ION_OFFSET = 19, 25, 31  # 상태별 걷기 프레임: 걷기 열(0~5)에 더함
WALK_FPS = 8

# 발 부분의 충돌 박스와 공격에 맞는 몸통 박스 (발 가운데 기준)
FOOT_HALF_WIDTH = 30 * KINGRAT_SCALE
FOOT_HEIGHT = 16 * KINGRAT_SCALE
HIT_HALF_WIDTH = 36 * KINGRAT_SCALE
HIT_TOP = 84 * KINGRAT_SCALE

KINGRAT_HP = 600
WALK_SPEED = 65
TOUCH_DAMAGE = 10
PATTERN_INTERVAL = (1.4, 2.2)  # 패턴 사이에 카이 쪽으로 걸어오는 시간(초)

# 패턴 A: 독 침 3방향
SPIT_READY_TIME = 0.5
SPIT_TIME = 0.25
SPIT_RECOVER_TIME = 0.45
NEEDLE_COUNT = 3
NEEDLE_SPREAD = 20      # 독 침 사이 각도(도)
NEEDLE_SPEED = 300
NEEDLE_DAMAGE = 10
NEEDLE_LENGTH = 20
NEEDLE_HEIGHT = 44      # 독 침이 날아가는 높이 (바닥에서 입까지)
NEEDLE_COLORS = [(60, 120, 30), (140, 230, 60), (220, 255, 160)]  # 바깥부터 안쪽 색

# 패턴 B: 저수조 가장자리로 달려감 -> 물속으로 뛰어듦 -> 물속(물결)에서 카이와 가까운 쪽으로 헤엄침
#         -> 물 위로 떠오름 -> 카이가 있던 자리로 뛰어올라 덮침. 뛰어들 때부터 떠오를 때까지(3초) 무적, 공중에서도 맞지 않음
RUN_SPEED = 130         # 저수조로 달려갈 때
RUN_TIMEOUT = 2.5       # 이 시간 안에 가장자리에 닿지 못하면(막혀 있으면) 그 자리에서 뛰어듦
DIVE_TIME = 0.4         # 물속으로 뛰어드는 시간 (포물선)
DIVE_HEIGHT = 40
DIVE_INSET = 50         # 가장자리에서 물 안쪽으로 이만큼 들어간 곳에 빠짐 (px)
UNDER_TIME = 2.0        # 물속에서 헤엄치는 시간
UNDER_SPEED = 260       # 저수조 반대편에서도 2초 안에 카이 쪽 물가에 닿을 만큼
WATER_MARGIN = 34       # 물결이 물 가장자리에서 이만큼 안쪽에서만 움직임 (px)
RISE_TIME = 0.6         # 물 위로 떠오르는 시간 (뛰어오를 예고)
LEAP_TIME = 0.65        # 카이 쪽으로 뛰어올라 착지하기까지의 시간
LEAP_HEIGHT = 90        # 뛰어오르는 높이 (px)
LEAP_RANGE = 360        # 이보다 먼 곳은 이 거리까지만 뜀
SHAKE_TIME = 0.25
LAND_TIME = 0.2
BURST_RADIUS = 80       # 착지할 때 이 거리 안에 카이의 발이 있으면 피해
BURST_DAMAGE = 25
WET_TIME = 1.5          # 착지한 뒤 젖어 있는 시간

# 불 공격: 불타는 상태로 BURN_TIME 동안 합쳐서 BURN_DAMAGE만큼 지속 피해
BURN_TIME = 3.0
BURN_DAMAGE = 15
# 증기 폭발: 젖은 채 불에 맞거나, 불타는 채 물에 맞으면 일어남. 약점이라 피해가 2배
STEAM_DAMAGE = 30
STEAM_WEAKNESS = 2
FLASH_TIME = 0.12
DEATH_TIME = 1.5

DIRECTION_ROWS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}
OCTANT_DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
INVULNERABLE_STATES = ('dive', 'under', 'rise', 'leap')
IN_WATER_STATES = ('dive', 'under', 'rise', 'leap')  # 벽과 저수조를 무시하고 움직이는 동안


def bb_center(bb):
    left, bottom, right, top = bb
    return (left + right) / 2, (bottom + top) / 2


class PoisonNeedle:
    """킹 랫의 독 침: 바닥 기준 (x, y)를 따라 날아가며 NEEDLE_HEIGHT 위에 그림. 방 밖으로 나가면 사라짐
    (저수조 위로는 날아감)"""

    def __init__(self, x, y, dir_x, dir_y, target, bounds):
        self.x, self.y = x, y
        self.dir_x, self.dir_y = dir_x, dir_y
        self.target = target
        self.bounds = bounds
        self.alive = True

    def get_bb(self):
        return (self.x - 6, self.y - 6, self.x + 6, self.y + 6)

    def update(self, frame_time):
        self.x += self.dir_x * NEEDLE_SPEED * frame_time
        self.y += self.dir_y * NEEDLE_SPEED * frame_time
        left, bottom, right, top = self.bounds
        if not (left <= self.x <= right and bottom <= self.y <= top):
            self.alive = False
            return
        # 카이의 발 박스를 조금 넓혀서 맞았는지 봄 (몸통 높이를 날아가므로)
        kl, kb, kr, kt = self.target.get_bb()
        if collide(self.get_bb(), (kl - 6, kb - 6, kr + 6, kt + 10)):
            self.target.on_hit(self.dir_x, self.dir_y, NEEDLE_DAMAGE)
            self.alive = False

    def draw(self):
        # 굵기가 있어 보이도록 여러 줄을 겹쳐 그림 (뒤쪽 끝에서 앞쪽 끝으로)
        x2, y2 = self.x, self.y + NEEDLE_HEIGHT
        x1, y1 = x2 - self.dir_x * NEEDLE_LENGTH, y2 - self.dir_y * NEEDLE_LENGTH
        nx, ny = -self.dir_y, self.dir_x
        for width, color in zip((2, 1, 0), NEEDLE_COLORS):
            for offset in range(-width, width + 1):
                draw_line(x1 + nx * offset, y1 + ny * offset, x2 + nx * offset, y2 + ny * offset, *color)


class KingRat:
    image = None

    def __init__(self, x, y, room_bounds, pool_box):
        # (x, y): 발 가운데. room_bounds: 방 안쪽 (left, bottom, right, top), 독 침이 날아갈 수 있는 범위
        # pool_box: 저수조 물 부분 (left, bottom, right, top), 잠수 패턴에서 뛰어드는 곳
        if KingRat.image is None:
            KingRat.image = load_image(KINGRAT_IMAGE)
        self.x, self.y = x, y
        self.room_bounds = room_bounds
        self.pool_box = pool_box
        self.jump_from = self.jump_to = (x, y)  # 뛰어들기/뛰어오르기의 출발점과 도착점 (발 가운데)
        self.height = 0.0                       # 공중에 떠 있는 높이 (그릴 때만 씀)
        self.hp = self.max_hp = KINGRAT_HP
        self.row = 0
        self.state = 'walk'
        self.state_time = 0.0
        self.anim_time = 0.0
        self.next_pattern_time = random.uniform(*PATTERN_INTERVAL)
        self.last_patterns = []
        self.burn_time = 0.0
        self.burn_damage_left = 0.0
        self.wet_time = 0.0
        self.ion_time = 0.0     # '이온화' 상태 (전기 공격이 생기면 ionize로 켬)
        self.flash_time = 0.0
        self.knockback_dir = (0, 0)
        self.knockback_time = 0.0
        self.death_time = 0.0
        self.alive = True

    # ---- 상태 ----
    def is_dead(self):
        return self.hp <= 0

    def is_death_done(self):
        return self.is_dead() and self.death_time >= DEATH_TIME

    def is_invulnerable(self):
        return self.state in INVULNERABLE_STATES

    def ignores_obstacles(self):
        # 물속이나 공중에 있는 동안은 벽과 저수조에 밀려나지 않음
        return self.state in IN_WATER_STATES

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
        return not self.is_dead()

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

    # ---- 공격에 맞음 ----
    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp < 1e-6:
            self.hp = 0
        if self.is_dead():
            self.set_state('dead')

    def steam_explode(self, dir_x, dir_y):
        # 증기 폭발: 약점이라 큰 피해를 받고 멀리 밀려나며, 하던 패턴이 끊김
        self.take_damage(STEAM_DAMAGE * STEAM_WEAKNESS)
        self.knockback_dir = (dir_x, dir_y)
        self.knockback_time = steam.KNOCKBACK_TIME
        steam.explode_at(self, dir_x, dir_y)
        if not self.is_dead():
            self.set_state('walk')

    def on_fireball_hit(self, dir_x, dir_y, damage):
        if self.is_invulnerable() or self.is_dead():
            return
        self.take_damage(damage)
        self.flash_time = FLASH_TIME
        if self.is_dead():
            return
        if self.is_wet():
            self.wet_time = 0.0
            self.steam_explode(dir_x, dir_y)
            return
        self.burn_time = BURN_TIME
        self.burn_damage_left = BURN_DAMAGE

    def on_water_hit(self, dir_x, dir_y, damage):
        # 물에 사는 쥐라 물에 맞아도 젖지는 않음 (젖음은 잠수했다 튀어나올 때만). 불타고 있었으면 증기 폭발
        if self.is_invulnerable() or self.is_dead():
            return
        self.take_damage(damage)
        self.flash_time = FLASH_TIME
        if self.is_burning() and not self.is_dead():
            self.burn_time = self.burn_damage_left = 0.0
            self.steam_explode(dir_x, dir_y)

    def update_burn(self, frame_time):
        if not self.is_burning():
            return
        damage = self.burn_damage_left * min(frame_time, self.burn_time) / self.burn_time
        self.burn_damage_left -= damage
        self.burn_time -= frame_time
        self.take_damage(damage)
        if self.burn_time <= 0:
            self.hp = round(self.hp, 6)
            self.burn_time = 0.0

    # ---- 움직임 ----
    def set_state(self, state):
        self.state = state
        self.state_time = 0.0

    def face(self, dx, dy):
        if dx == 0 and dy == 0:
            return
        octant = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.row = DIRECTION_ROWS[OCTANT_DIRECTIONS[octant]]

    def face_target(self, target):
        tx, ty = bb_center(target.get_bb())
        x, y = bb_center(self.get_bb())
        self.face(tx - x, ty - y)
        return tx - x, ty - y

    def move(self, dx, dy, obstacles):
        old_x = self.x
        self.x += dx
        if collide_any(self.get_bb(), obstacles):
            self.x = old_x
        old_y = self.y
        self.y += dy
        if collide_any(self.get_bb(), obstacles):
            self.y = old_y

    def update(self, frame_time, obstacles, target):
        self.anim_time += frame_time
        self.state_time += frame_time
        if self.is_dead():
            self.death_time += frame_time
            return
        self.update_burn(frame_time)
        if self.is_dead():
            return
        for name in ('wet_time', 'ion_time', 'flash_time'):
            setattr(self, name, max(0.0, getattr(self, name) - frame_time))
        if self.is_knocked_back():
            speed = steam.KNOCKBACK_SPEED * self.knockback_time / steam.KNOCKBACK_TIME
            dx, dy = self.knockback_dir
            self.move(dx * speed * frame_time, dy * speed * frame_time, obstacles)
            self.knockback_time -= frame_time
            return
        getattr(self, 'update_' + self.state)(frame_time, obstacles, target)

    def sees(self, target):
        # 증기에 가리면 카이가 보이지 않음
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        return not steam.blocks_sight(x, y, tx, ty)

    def update_walk(self, frame_time, obstacles, target):
        if not self.sees(target):
            return  # 증기 속에서는 카이를 찾지 못해 멈춰 있고, 패턴도 쓰지 않음
        dx, dy = self.face_target(target)
        length = math.hypot(dx, dy)
        if length > 1 and not collide(self.get_bb(), target.get_bb()):
            speed = WALK_SPEED * (0.6 if self.is_wet() else 1.0)
            self.move(dx / length * speed * frame_time, dy / length * speed * frame_time, obstacles)
        self.next_pattern_time -= frame_time
        if self.next_pattern_time <= 0:
            self.start_pattern(target)

    def start_pattern(self, target):
        # 같은 패턴이 세 번 이어지지 않게, 멀리 있으면 잠수(B)를 더 자주 고름
        if len(self.last_patterns) >= 2 and self.last_patterns[-1] == self.last_patterns[-2]:
            pattern = 'B' if self.last_patterns[-1] == 'A' else 'A'
        else:
            chance_b = 0.65 if self.distance_to(target) > 260 else 0.4
            pattern = 'B' if random.random() < chance_b else 'A'
        self.last_patterns = (self.last_patterns + [pattern])[-2:]
        self.next_pattern_time = random.uniform(*PATTERN_INTERVAL)
        if pattern == 'A':
            self.set_state('spit_ready')
        else:
            self.set_state('to_pool')
            self.jump_from = self.pool_edge_point()

    # 패턴 A
    def update_spit_ready(self, frame_time, obstacles, target):
        self.face_target(target)
        if self.state_time >= SPIT_READY_TIME:
            self.set_state('spit')
            self.spit(target)

    def spit(self, target):
        # 카이 쪽을 가운데로 NEEDLE_SPREAD도씩 벌어진 3방향
        dx, dy = self.face_target(target)
        base = math.atan2(dy, dx)
        x, y = bb_center(self.get_bb())
        for i in range(NEEDLE_COUNT):
            angle = base + math.radians((i - (NEEDLE_COUNT - 1) / 2) * NEEDLE_SPREAD)
            dir_x, dir_y = math.cos(angle), math.sin(angle)
            game_world.add(PoisonNeedle(x + dir_x * 30, y + dir_y * 30, dir_x, dir_y, target, self.room_bounds))

    def update_spit(self, frame_time, obstacles, target):
        if self.state_time >= SPIT_TIME:
            self.set_state('spit_recover')

    def update_spit_recover(self, frame_time, obstacles, target):
        if self.state_time >= SPIT_RECOVER_TIME:
            self.set_state('walk')

    # 패턴 B
    def pool_edge_point(self):
        """저수조 둘레에서 지금 자리와 가장 가까운 곳 바로 바깥 (발 가운데가 설 자리)"""
        left, bottom, right, top = self.pool_box
        # 저수조 바깥에서 어느 쪽에 있는지: 가장 멀리 벗어난 쪽의 변으로 감
        outside = {'left': left - self.x, 'right': self.x - right,
                   'bottom': bottom - (self.y + FOOT_HEIGHT), 'top': self.y - top}
        side = max(outside, key=outside.get)
        x = min(max(self.x, left + FOOT_HALF_WIDTH), right - FOOT_HALF_WIDTH)
        y = min(max(self.y, bottom), top - FOOT_HEIGHT)
        if side == 'left':
            return left - FOOT_HALF_WIDTH - 4, y
        if side == 'right':
            return right + FOOT_HALF_WIDTH + 4, y
        if side == 'bottom':
            return x, bottom - FOOT_HEIGHT - 4
        return x, top + 4

    def water_point(self, x, y, margin=WATER_MARGIN):
        """(x, y)를 저수조 물 안쪽(가장자리에서 margin 안)으로 맞춘 자리"""
        left, bottom, right, top = self.pool_box
        return (min(max(x, left + margin), right - margin),
                min(max(y, bottom + margin), top - margin - FOOT_HEIGHT))

    def update_to_pool(self, frame_time, obstacles, target):
        # 저수조 가장자리로 달려감. 닿으면(또는 막혀서 시간이 지나면) 물속으로 뛰어듦
        ex, ey = self.jump_from
        dx, dy = ex - self.x, ey - self.y
        length = math.hypot(dx, dy)
        if length > 6 and self.state_time < RUN_TIMEOUT:
            self.face(dx, dy)
            step = min(length, RUN_SPEED * frame_time)
            old_x, old_y = self.x, self.y
            self.move(dx / length * step, dy / length * step, obstacles)
            # 저수조 난간에 막혀 더 다가가지 못하면 그 자리가 가장자리이므로 바로 뛰어듦
            if math.hypot(self.x - old_x, self.y - old_y) > step * 0.3:
                return
        self.jump_from = (self.x, self.y)
        self.jump_to = self.water_point(self.x, self.y, DIVE_INSET)
        self.face(self.jump_to[0] - self.x, self.jump_to[1] - self.y)
        self.set_state('dive')

    def update_dive(self, frame_time, obstacles, target):
        # 가장자리에서 물 안쪽으로 포물선을 그리며 뛰어듦
        t = min(1.0, self.state_time / DIVE_TIME)
        (x1, y1), (x2, y2) = self.jump_from, self.jump_to
        self.x, self.y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        self.height = math.sin(math.pi * t) * DIVE_HEIGHT
        if t >= 1.0:
            self.height = 0.0
            self.set_state('under')

    def update_under(self, frame_time, obstacles, target):
        # 물속(물결)에서 카이와 가장 가까운 물가 쪽으로 헤엄쳐 감
        tx, ty = bb_center(target.get_bb())
        wx, wy = self.water_point(tx, ty - FOOT_HEIGHT / 2)
        dx, dy = wx - self.x, wy - self.y
        length = math.hypot(dx, dy)
        if length > 1:
            self.face(dx, dy)
            step = min(length, UNDER_SPEED * frame_time)
            self.x += dx / length * step
            self.y += dy / length * step
        if self.state_time >= UNDER_TIME:
            self.face_target(target)
            self.set_state('rise')

    def update_rise(self, frame_time, obstacles, target):
        # 물 위로 떠올라 카이를 노려봄. 다 떠오르면 그 순간 카이가 있던 자리로 뛰어오름
        self.face_target(target)
        if self.state_time >= RISE_TIME:
            self.jump_from = (self.x, self.y)
            self.jump_to = self.find_landing_point(target, obstacles)
            self.set_state('leap')

    def find_landing_point(self, target, obstacles):
        # 카이의 발 자리(너무 멀면 LEAP_RANGE까지). 킹 랫의 발 박스가 장애물에 겹치면 가까운 빈 곳
        tx, ty = bb_center(target.get_bb())
        ty -= FOOT_HEIGHT / 2
        dx, dy = tx - self.x, ty - self.y
        length = math.hypot(dx, dy)
        if length > LEAP_RANGE:
            tx, ty = self.x + dx / length * LEAP_RANGE, self.y + dy / length * LEAP_RANGE
        back = math.atan2(-dy, -dx)  # 킹 랫 쪽(저수조 쪽)부터 찾음
        for radius in (0, 30, 60, 90, 120, 160):
            for i in range(12 if radius else 1):
                angle = back + math.radians(30 * ((i + 1) // 2) * (1 if i % 2 else -1))
                x, y = tx + math.cos(angle) * radius, ty + math.sin(angle) * radius
                bb = (x - FOOT_HALF_WIDTH, y, x + FOOT_HALF_WIDTH, y + FOOT_HEIGHT)
                if not collide_any(bb, obstacles) and self.in_room(x, y):
                    return x, y
        return self.pool_edge_point()

    def in_room(self, x, y):
        left, bottom, right, top = self.room_bounds
        return left + FOOT_HALF_WIDTH <= x <= right - FOOT_HALF_WIDTH and bottom <= y <= top - FOOT_HEIGHT

    def update_leap(self, frame_time, obstacles, target):
        # 포물선을 그리며 날아가 착지. 착지할 때 가까이 있는 카이에게 피해를 주고, 젖은 채로 1.5초
        t = min(1.0, self.state_time / LEAP_TIME)
        (x1, y1), (x2, y2) = self.jump_from, self.jump_to
        self.x, self.y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        self.height = math.sin(math.pi * t) * LEAP_HEIGHT
        if t < 1.0:
            return
        self.height = 0.0
        self.wet_time = WET_TIME
        self.set_state('shake')
        if self.distance_to(target) <= BURST_RADIUS:
            x, y = bb_center(self.get_bb())
            tx, ty = bb_center(target.get_bb())
            length = math.hypot(tx - x, ty - y)
            target.on_hit(*(((tx - x) / length, (ty - y) / length) if length else (0, -1)), BURST_DAMAGE)

    def update_shake(self, frame_time, obstacles, target):
        if self.state_time >= SHAKE_TIME:
            self.set_state('land')

    def update_land(self, frame_time, obstacles, target):
        if self.state_time >= LAND_TIME:
            self.set_state('walk')

    def update_dead(self, frame_time, obstacles, target):
        pass

    def touch(self, target):
        """걷는 중에 카이와 발이 부딪혔으면 밀어내며 피해를 줌"""
        if (self.is_dead() or self.is_invulnerable() or self.is_knocked_back()
                or not collide(self.get_bb(), target.get_bb())):
            return
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        length = math.hypot(tx - x, ty - y)
        target.on_hit(*(((tx - x) / length, (ty - y) / length) if length else (0, -1)), TOUCH_DAMAGE)

    # ---- 그리기 ----
    def status_offset(self):
        if self.is_burning():
            return BURN_OFFSET
        if self.is_wet():
            return WET_OFFSET
        if self.is_ionized():
            return ION_OFFSET
        return None

    def current_col(self):
        walk_col = WALK_COLS[int(self.anim_time * WALK_FPS) % len(WALK_COLS)]
        t = self.state_time
        if self.is_dead() or self.is_knocked_back():
            return HIT_COL
        # 잠수 패턴(뛰어듦, 물속, 떠오름, 뛰어오름, 물 털기)은 상태와 상관없이 그 모습을 보여줌
        if self.state == 'dive':
            # 공중에서는 몸을 날리는 모습, 물에 닿을 즈음부터 물보라
            return DIVE_COL if self.state_time >= DIVE_TIME * 0.6 else BURST_COL
        if self.state == 'under':
            return UNDER_COL
        if self.state == 'rise':
            return RISE_COL
        if self.state == 'leap':
            # 물을 박차고 오를 때는 물기둥, 공중에서는 물을 흩뿌리는 모습
            return BURST_COL if self.state_time < LEAP_TIME * 0.3 else SHAKE_COL
        if self.state == 'shake':
            return SHAKE_COL
        offset = self.status_offset()
        if offset is not None:
            # 상태별 구간에는 걷기만 있으므로 다른 동작 중에도 그 구간의 프레임으로 상태 모습을 유지
            return offset + (walk_col if self.state in ('walk', 'to_pool') else WALK_COLS[0])
        if self.flash_time > 0:
            return HIT_COL
        if self.state == 'spit_ready':
            return SPIT_READY_COLS[min(int(t / (SPIT_READY_TIME / 2)), 1)]
        if self.state == 'spit':
            return SPIT_COL
        if self.state == 'spit_recover':
            return SPIT_RECOVER_COLS[min(int(t / (SPIT_RECOVER_TIME / 3)), 2)]
        if self.state == 'land':
            return LAND_COL
        return walk_col  # 걷기, 저수조로 달려가기

    def draw(self):
        size = FRAME_SIZE * KINGRAT_SCALE
        center_y = self.y + (FRAME_SIZE / 2 - GROUND_MARGIN) * KINGRAT_SCALE + self.height
        if self.state == 'leap':
            self.draw_landing_mark()
        if self.is_dead():
            KingRat.image.opacify(max(0.0, 1 - self.death_time / DEATH_TIME))
        KingRat.image.clip_draw(self.current_col() * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                                FRAME_SIZE, FRAME_SIZE, self.x, center_y, size, size)
        KingRat.image.opacify(1)

    def draw_landing_mark(self):
        # 뛰어올라 착지할 자리를 붉은 원으로 미리 보여줌 (착지가 가까울수록 커지고 진해짐)
        x, y = self.jump_to
        t = min(1.0, self.state_time / LEAP_TIME)
        cy = y + FOOT_HEIGHT / 2
        for i in range(3):
            draw_circle(int(x), int(cy), int(BURST_RADIUS * (0.55 + 0.45 * t)) - i, 255, 60, 60, int(120 + 135 * t))

    def draw_range(self):
        # 디버그용: 튀어나올 때 피해를 주는 범위
        if self.state == 'to_pool':
            draw_circle(int(self.jump_from[0]), int(self.jump_from[1]), 6, 80, 200, 255)
        if self.state in ('under', 'rise'):
            left, bottom, right, top = self.pool_box
            draw_rectangle(left, bottom, right, top, 80, 200, 255)
