import math
import random

from pico2d import *

import steam

# 전기 드론: 날아다니며(벽과 오수 물길 위로도) 돌아다니다가 카이가 가까이 오면 다가가서
# 붉은 전기 레이저를 충전했다가 쏨. 물에 맞으면 합선되어 잠깐 지직거린 뒤 젖은 상태가 되어 쏘지 못하고 느려짐
#
# drone_animation.png: 배경이 투명한 시트, 25열 x 8행(1600x512), 프레임 64x64. 행(방향)은 카이 시트와 같은 순서
# 0~3열 떠 있기 / 4열 레이저 충전 / 5열 레이저 발사 / 6열 발사 뒤 / 7열 맞음 / 8열 전기 공격에 맞음(피해 없음)
# 9~12열 물에 맞아 합선 / 13~16열 불타는 상태 / 17~20열 젖음 상태 / 21~24열 감전(이온화) 상태
DRONE_IMAGE = 'sprite_sheet/sprite_sheet_drone/drone_animation.png'
FRAME_SIZE = 64
SHEET_HEIGHT = 512
DRONE_SCALE = 1.0
GROUND_MARGIN = 4    # 프레임 아래쪽 끝에서 그림자 가운데까지의 거리
HOVER_COLS = (0, 1, 2, 3)
CHARGE_COL = 4
FIRE_COL = 5
RECOVER_COL = 6
HIT_COL = 7
SHIELD_COL = 8       # 전기 공격에 맞았지만 피해 없음
SHORT_COLS = (9, 10, 11, 12)
BURN_COLS = (13, 14, 15, 16)
WET_COLS = (17, 18, 19, 20)
ION_COLS = (21, 22, 23, 24)
HOVER_FPS = 10
STATUS_FPS = 8
BOB_AMPLITUDE = 2    # 몸이 위아래로 흔들리는 폭(px)
BOB_PERIOD = 0.9

# 그림자(바닥) 부분의 박스와 공격에 맞는 몸통 박스 (그림자 가운데 기준)
SHADOW_HALF_WIDTH = 14 * DRONE_SCALE
SHADOW_HALF_HEIGHT = 4 * DRONE_SCALE
HIT_HALF_WIDTH = 24 * DRONE_SCALE
HIT_BOTTOM, HIT_TOP = 16 * DRONE_SCALE, 48 * DRONE_SCALE

DRONE_HP = 30
FLY_SPEED = 70       # 돌아다닐 때 (초당 픽셀)
CHASE_SPEED = 110    # 카이에게 다가갈 때
WANDER_TIME = (1.0, 2.5)
CHASE_RANGE = 230    # 이 거리 안에 카이가 보이면(증기에 가리지 않으면) 다가감
ATTACK_RANGE = 170   # 이 거리 안이면 멈춰서 레이저를 쏨
# 레이저: 충전하는 동안 조준한 쪽(충전을 시작할 때의 카이 자리)으로 쏘므로, 충전 중에 비켜서면 피할 수 있음
CHARGE_TIME = 0.5
FIRE_TIME = 0.2
RECOVER_TIME = 0.25
ATTACK_COOLDOWN = 1.1
LASER_LENGTH = 260
LASER_HIT_WIDTH = 16  # 카이의 발 가운데가 레이저 선에서 이 거리 안이면 맞음
LASER_DAMAGE = 10
LASER_COLORS = [(255, 70, 90), (255, 140, 150), (255, 230, 230)]  # 바깥부터 안쪽 색

# 공격에 맞으면 밀려남 (쥐, 박쥐와 같음)
KNOCKBACK_SPEED = 320
KNOCKBACK_TIME = 0.25
FLASH_TIME = 0.12
# 불 공격: '불타는' 상태로 BURN_TIME 동안 합쳐서 BURN_DAMAGE만큼 지속 피해 (쥐와 같은 방법)
BURN_TIME = 3.0
BURN_DAMAGE = 6
# 물 공격: SHORT_TIME 동안 합선(지직거림)된 뒤 '젖음' 상태. 합선, 젖음 동안은 레이저를 쏘지 못하고 느려짐
SHORT_TIME = 0.6
WET_TIME = 4.0
WET_SPEED_RATE = 0.5
# 전기 공격: 피해 없이 방어막 모습만 잠깐 보여줌
SHIELD_TIME = 0.4
DEATH_TIME = 1.0

DIRECTION_ROWS = {
    (0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
    (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7,
}
OCTANT_DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def bb_center(bb):
    left, bottom, right, top = bb
    return (left + right) / 2, (bottom + top) / 2


def segment_distance(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


class Drone:
    image = None

    def __init__(self, x, y, bounds):
        # (x, y): 그림자 가운데. bounds: 날아다닐 수 있는 범위 (left, bottom, right, top), 그림자 가운데 기준
        if Drone.image is None:
            Drone.image = load_image(DRONE_IMAGE)
        self.x, self.y = x, y
        self.bounds = bounds
        self.hp = DRONE_HP
        self.row = 0
        self.anim_time = random.uniform(0, 1)
        self.dir_x, self.dir_y = 0.0, 0.0
        self.state_time = 0.0
        self.chasing = False
        self.attack = None      # None, 'charge', 'fire', 'recover'
        self.attack_time = 0.0
        self.attack_cooldown = 0.0
        self.aim = (0.0, 0.0)   # 레이저 방향 (길이 1)
        self.burn_time = 0.0
        self.burn_damage_left = 0.0
        self.short_time = 0.0
        self.wet_time = 0.0
        self.ion_time = 0.0     # '이온화' 상태 (전기 공격이 생기면 ionize로 켬)
        self.flash_time = 0.0
        self.shield_time = 0.0
        self.knockback_dir = (0, 0)
        self.knockback_time = 0.0
        self.knockback_speed, self.knockback_duration = KNOCKBACK_SPEED, KNOCKBACK_TIME
        self.death_time = 0.0
        self.alive = True
        self.start_wander()

    # ---- 상태 ----
    def is_dead(self):
        return self.hp <= 0

    def is_burning(self):
        return self.burn_time > 0

    def is_shorted(self):
        return self.short_time > 0

    def is_wet(self):
        # 합선 중이거나 젖어 있으면 젖은 것으로 봄 (불에 맞으면 증기 폭발)
        return self.short_time > 0 or self.wet_time > 0

    def is_ionized(self):
        return self.ion_time > 0

    def ionize(self, duration):
        self.ion_time = duration

    def is_knocked_back(self):
        return self.knockback_time > 0

    def can_attack(self):
        return not self.is_wet()  # 젖으면 합선되어 레이저를 쏘지 못함

    def speed_rate(self):
        return WET_SPEED_RATE if self.is_wet() else 1.0

    # ---- 위치와 충돌 박스 ----
    def foot_y(self):
        return self.y - SHADOW_HALF_HEIGHT

    def get_bb(self):
        return (self.x - SHADOW_HALF_WIDTH, self.y - SHADOW_HALF_HEIGHT,
                self.x + SHADOW_HALF_WIDTH, self.y + SHADOW_HALF_HEIGHT)

    def get_hit_bb(self):
        return (self.x - HIT_HALF_WIDTH, self.y + HIT_BOTTOM, self.x + HIT_HALF_WIDTH, self.y + HIT_TOP)

    def distance_to(self, target):
        tx, ty = bb_center(target.get_bb())
        return math.hypot(tx - self.x, ty - self.y)

    def can_see(self, target, max_range):
        if self.distance_to(target) > max_range:
            return False
        tx, ty = bb_center(target.get_bb())
        return not steam.blocks_sight(self.x, self.y, tx, ty)

    # ---- 공격에 맞음 ----
    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp < 1e-6:
            self.hp = 0
        if self.is_dead():
            self.attack = None

    def knock_back(self, dir_x, dir_y, speed=KNOCKBACK_SPEED, duration=KNOCKBACK_TIME):
        self.knockback_dir = (dir_x, dir_y)
        self.knockback_speed, self.knockback_duration = speed, duration
        self.knockback_time = duration

    def steam_explode(self, dir_x, dir_y):
        self.knock_back(dir_x, dir_y, steam.KNOCKBACK_SPEED, steam.KNOCKBACK_TIME)
        steam.explode_at(self, dir_x, dir_y)

    def on_fireball_hit(self, dir_x, dir_y, damage):
        # 불 공격: 밀려나며 피해를 받고 불타는 상태가 됨. 젖어 있었으면 증기 폭발 (젖음만 풀리고 불은 붙지 않음)
        self.take_damage(damage)
        self.flash_time = FLASH_TIME
        self.attack = None
        if self.is_wet() and not self.is_dead():
            self.short_time = self.wet_time = 0.0
            self.steam_explode(dir_x, dir_y)
            return
        self.knock_back(dir_x, dir_y)
        if not self.is_dead():
            self.burn_time = BURN_TIME
            self.burn_damage_left = BURN_DAMAGE

    def on_water_hit(self, dir_x, dir_y, damage):
        # 물 공격: 밀려나며 피해를 받고 합선된 뒤 젖음. 불타고 있었으면 증기 폭발 (불만 꺼지고 젖지 않음)
        self.take_damage(damage)
        self.attack = None
        if self.is_burning() and not self.is_dead():
            self.burn_time = self.burn_damage_left = 0.0
            self.steam_explode(dir_x, dir_y)
            return
        self.knock_back(dir_x, dir_y)
        if not self.is_dead():
            self.short_time = SHORT_TIME
            self.wet_time = WET_TIME

    def on_electric_hit(self, dir_x, dir_y, damage):
        # 전기 드론이라 전기 공격에는 피해가 없음
        self.shield_time = SHIELD_TIME

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
    def start_wander(self):
        angle = random.uniform(0, 2 * math.pi)
        self.dir_x, self.dir_y = math.cos(angle), math.sin(angle)
        self.state_time = random.uniform(*WANDER_TIME)

    def face(self, dx, dy):
        if dx == 0 and dy == 0:
            return
        octant = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.row = DIRECTION_ROWS[OCTANT_DIRECTIONS[octant]]

    def move(self, dx, dy):
        """날아다니므로 벽은 무시하고 범위 끝에서만 멈춤. 범위 끝에 닿았으면 True"""
        left, bottom, right, top = self.bounds
        nx = min(max(self.x + dx, left), right)
        ny = min(max(self.y + dy, bottom), top)
        blocked = nx != self.x + dx or ny != self.y + dy
        self.x, self.y = nx, ny
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
        for name in ('short_time', 'wet_time', 'ion_time', 'flash_time', 'shield_time', 'attack_cooldown'):
            setattr(self, name, max(0.0, getattr(self, name) - frame_time))
        if self.is_knocked_back():
            speed = self.knockback_speed * self.knockback_time / self.knockback_duration
            dx, dy = self.knockback_dir
            self.move(dx * speed * frame_time, dy * speed * frame_time)
            self.knockback_time -= frame_time
            return
        if self.attack:
            self.update_attack(frame_time, target)
            return
        # 증기에 가려 보이지 않으면 추적하지 못하고 돌아다니기만 함
        if self.can_see(target, CHASE_RANGE):
            self.chasing = True
            tx, ty = bb_center(target.get_bb())
            dx, dy = tx - self.x, ty - self.y
            length = math.hypot(dx, dy)
            self.face(dx, dy)
            if self.can_attack() and length <= ATTACK_RANGE and self.attack_cooldown == 0:
                self.aim = (dx / length, dy / length) if length else (0, -1)  # 충전을 시작할 때 조준
                self.attack, self.attack_time = 'charge', 0.0
                return
            if length > ATTACK_RANGE * 0.8:
                speed = CHASE_SPEED * self.speed_rate()
                self.move(dx / length * speed * frame_time, dy / length * speed * frame_time)
            return
        if self.chasing:
            self.chasing = False
            self.start_wander()
        self.state_time -= frame_time
        if self.state_time <= 0:
            self.start_wander()
        speed = FLY_SPEED * self.speed_rate()
        self.face(self.dir_x, self.dir_y)
        if self.move(self.dir_x * speed * frame_time, self.dir_y * speed * frame_time):
            self.start_wander()

    def laser_line(self):
        # 몸통 가운데에서 조준한 방향으로 LASER_LENGTH만큼
        x, y = bb_center(self.get_hit_bb())
        ax, ay = self.aim
        return x, y, x + ax * LASER_LENGTH, y + ay * LASER_LENGTH

    def update_attack(self, frame_time, target):
        self.attack_time += frame_time
        if self.attack == 'charge' and self.attack_time >= CHARGE_TIME:
            self.attack, self.attack_time = 'fire', 0.0
            # 쏘는 순간 레이저 선 가까이에 카이의 발이 있으면 맞음 (증기에 가리면 막힘)
            x1, y1, x2, y2 = self.laser_line()
            tx, ty = bb_center(target.get_bb())
            if (segment_distance(tx, ty, x1, y1 - HIT_BOTTOM, x2, y2 - HIT_BOTTOM) <= LASER_HIT_WIDTH
                    and not steam.blocks_sight(self.x, self.y, tx, ty)):
                target.on_hit(self.aim[0], self.aim[1], LASER_DAMAGE)
        elif self.attack == 'fire' and self.attack_time >= FIRE_TIME:
            self.attack, self.attack_time = 'recover', 0.0
        elif self.attack == 'recover' and self.attack_time >= RECOVER_TIME:
            self.attack = None
            self.attack_cooldown = ATTACK_COOLDOWN

    def touch(self, target):
        pass  # 몸으로 부딪혀서는 피해를 주지 않음 (레이저로만 공격)

    # ---- 그리기 ----
    def current_col(self):
        t = self.anim_time
        if self.shield_time > 0:
            return SHIELD_COL
        if self.flash_time > 0 and not (self.is_burning() or self.is_wet()):
            return HIT_COL
        if self.is_shorted():
            return SHORT_COLS[int(t * STATUS_FPS) % len(SHORT_COLS)]
        if self.is_burning():
            return BURN_COLS[int(t * STATUS_FPS) % len(BURN_COLS)]
        if self.is_wet():
            return WET_COLS[int(t * STATUS_FPS) % len(WET_COLS)]
        if self.is_ionized():
            return ION_COLS[int(t * STATUS_FPS) % len(ION_COLS)]
        if self.is_dead() or self.is_knocked_back():
            return HIT_COL
        if self.attack == 'charge':
            return CHARGE_COL
        if self.attack == 'fire':
            return FIRE_COL
        if self.attack == 'recover':
            return RECOVER_COL
        return HOVER_COLS[int(t * HOVER_FPS) % len(HOVER_COLS)]

    def draw(self):
        size = FRAME_SIZE * DRONE_SCALE
        center_y = self.y + (FRAME_SIZE / 2 - GROUND_MARGIN) * DRONE_SCALE
        if not self.is_dead():
            center_y += math.sin(self.anim_time * 2 * math.pi / BOB_PERIOD) * BOB_AMPLITUDE
        if self.is_dead():
            Drone.image.opacify(max(0.0, 1 - self.death_time / DEATH_TIME))
        Drone.image.clip_draw(self.current_col() * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                              FRAME_SIZE, FRAME_SIZE, self.x, center_y, size, size)
        Drone.image.opacify(1)
        if self.attack == 'fire':
            self.draw_laser()

    def draw_laser(self):
        # 굵기가 있어 보이도록 여러 줄을 겹쳐 그림 (바깥쪽은 진한 빨강, 안쪽은 밝게)
        x1, y1, x2, y2 = self.laser_line()
        ax, ay = self.aim
        nx, ny = -ay, ax  # 레이저에 수직인 방향
        for width, color in zip((3, 2, 0), LASER_COLORS):
            for offset in range(-width, width + 1):
                draw_line(x1 + nx * offset, y1 + ny * offset, x2 + nx * offset, y2 + ny * offset, *color)

    def draw_chase_range(self):
        color = (255, 0, 0) if self.chasing else (255, 220, 0)
        draw_circle(int(self.x), int(self.y), CHASE_RANGE, *color)
        draw_circle(int(self.x), int(self.y), ATTACK_RANGE, 255, 120, 200)
