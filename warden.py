import math

from pico2d import *

from collision import collide, collide_any

# warden_sheet.png: 21열 x 8행(2688x1024), 프레임 128x128
# 행(방향)은 카이 시트와 같은 순서, 0~5열 걷기 / 8~9열 돌진(속도선) / 10~13열 곤봉 공격 / 14~17열 기절
# 6~7열 과열(연기) / 18열 맞음(하얗게 번쩍) / 19~20열 경보 (곤봉 공격, 기절, 경보는 아직 사용하지 않음)
WARDEN_IMAGE = 'sprite_sheet/sprite_sheet_boss/warden_sheet.png'
# warden_death.png: 128x128 프레임 6개 (정면): 번쩍 -> 주저앉음 -> 폭발 -> 부서져 연기가 남
DEATH_IMAGE = 'sprite_sheet/sprite_sheet_boss/warden_death.png'
DEATH_FRAMES = 6
DEATH_FPS = 5
FRAME_SIZE = 128
SHEET_HEIGHT = 1024
WARDEN_SCALE = 1.0
WALK_FRAMES = 6
WALK_FPS = 8
DASH_COLS = (8, 9)
DASH_FPS = 10
# 발 아래쪽 끝이 프레임 아래쪽 끝에서 이만큼 위에 있음. 발(그림자) 부분만 충돌 박스로 사용
FOOT_BOTTOM_MARGIN = 4
FOOT_HALF_WIDTH = 26
FOOT_HEIGHT = 16

# 워든은 항상 카이를 추적함. 카이가 DASH_RANGE 안으로 들어오면 돌진하듯 더 빨리 움직임
WALK_SPEED = 70    # 초당 이동 픽셀 (카이는 200)
DASH_SPEED = 170
DASH_RANGE = 220   # 워든의 발 중심에서 카이의 발 중심까지의 거리(px)
WARDEN_DAMAGE = 15  # 카이와 부딪혔을 때 카이에게 주는 피해

WARDEN_HP = 200     # 파이어볼(10) 스무 발 (불타는 지속 피해까지 치면 더 적게)
# 파이어볼에 맞는 몸통 박스: 발 아래쪽 끝 기준 (프레임 안의 로봇 몸체 부분)
HIT_HALF_WIDTH = 36
HIT_HEIGHT = 96
HIT_COL = 18           # 맞았을 때 하얗게 번쩍이는 프레임
HIT_FLASH_TIME = 0.12
# 파이어볼에 맞으면 '불타는'(과열) 상태: BURN_TIME 동안 HP가 조금씩 줄어 합쳐서 BURN_DAMAGE만큼 피해를 받고,
# 걸을 때 연기가 나는 프레임(6~7열)으로 그림. 불타는 중에 또 맞으면 남은 지속 피해는 버리고 처음부터 다시 셈
BURN_TIME = 3.0
BURN_DAMAGE = 5
BURN_COLS = (6, 7)
BURN_FPS = 6
# 머리 위 HP 바
HP_BAR_WIDTH = 100
HP_BAR_HEIGHT = 8
HP_BAR_GAP = 6        # 로봇 머리 위쪽 끝에서 HP 바까지의 거리
FRAME_TOP_MARGIN = 24  # 프레임 위쪽 끝에서 로봇 머리 위쪽 끝까지의 빈 공간

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


class Warden:
    """워든(보스 로봇): 카이를 계속 추적하고, 가까워지면 더 빨리 다가옴. 부딪히면 카이에게 피해를 줌"""
    image = None
    death_image = None

    def __init__(self, x, y):
        if Warden.image is None:
            Warden.image = load_image(WARDEN_IMAGE)
            Warden.death_image = load_image(DEATH_IMAGE)
        self.x, self.y = x, y  # 그림의 중심
        self.row = DIRECTION_ROWS[(0, -1)]
        self.anim_time = 0.0
        self.dashing = False  # 카이가 DASH_RANGE 안에 있어서 빨리 움직이는 중
        self.max_hp = self.hp = WARDEN_HP
        self.flash_time = 0.0
        self.burn_time = 0.0  # 불타는 상태가 남은 시간(초), 0이면 불타지 않음
        self.burn_damage_left = 0.0  # 이번 불타는 상태에서 아직 받지 않은 지속 피해
        self.death_time = None  # 쓰러진 뒤 흐른 시간, None이면 살아 있음

    def place_feet_at(self, x, y):
        # 발 충돌 박스의 중심이 (x, y)에 오도록 위치를 맞춤
        self.x = x
        self.y = y + (FRAME_SIZE / 2 - FOOT_BOTTOM_MARGIN) * WARDEN_SCALE - FOOT_HEIGHT / 2

    def foot_y(self):
        return self.y - (FRAME_SIZE / 2 - FOOT_BOTTOM_MARGIN) * WARDEN_SCALE

    def get_bb(self):
        foot_y = self.foot_y()
        return (self.x - FOOT_HALF_WIDTH, foot_y,
                self.x + FOOT_HALF_WIDTH, foot_y + FOOT_HEIGHT)

    def get_hit_bb(self):
        foot_y = self.foot_y()
        return (self.x - HIT_HALF_WIDTH, foot_y, self.x + HIT_HALF_WIDTH, foot_y + HIT_HEIGHT)

    def is_dead(self):
        return self.hp <= 0

    def is_burning(self):
        return self.burn_time > 0

    def on_fireball_hit(self, dir_x, dir_y, damage):
        # 보스라서 쥐처럼 밀려나지는 않고, 하얗게 번쩍이며 불타는 상태가 됨
        self.take_damage(damage)
        self.flash_time = HIT_FLASH_TIME
        if not self.is_dead():
            self.burn_time = BURN_TIME
            self.burn_damage_left = BURN_DAMAGE

    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp < 1e-6:  # 소수 계산 오차로 HP가 0에 아주 가깝게 남는 것을 막음
            self.hp = 0
        if self.is_dead() and self.death_time is None:
            self.death_time = 0.0
            self.burn_time = 0.0
            self.dashing = False

    def update_burn(self, frame_time):
        if not self.is_burning():
            return
        # 남은 시간 중 이번 프레임이 차지하는 비율만큼 남은 피해를 줌: 합이 정확히 BURN_DAMAGE
        damage = self.burn_damage_left * min(frame_time, self.burn_time) / self.burn_time
        self.burn_damage_left -= damage
        self.burn_time -= frame_time
        self.take_damage(damage)
        if self.burn_time <= 0:
            self.hp = round(self.hp, 6)  # 소수 오차 정리 (예: 184.9999999 -> 185)
            self.burn_time = 0.0

    def distance_to(self, target):
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        return math.hypot(tx - x, ty - y)

    def update(self, frame_time, obstacles, target):
        self.anim_time += frame_time
        self.flash_time = max(0.0, self.flash_time - frame_time)
        if self.is_dead():
            self.death_time += frame_time
            return
        self.update_burn(frame_time)
        if self.is_dead():
            return
        self.dashing = self.distance_to(target) <= DASH_RANGE
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        dx, dy = tx - x, ty - y
        length = math.hypot(dx, dy)
        if length == 0:
            return
        # 카이 쪽에 가장 가까운 8방향을 바라봄
        octant = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.row = DIRECTION_ROWS[OCTANT_DIRECTIONS[octant]]
        if collide(self.get_bb(), target.get_bb()):
            return  # 이미 붙어 있으면 제자리에서 바라보기만 함
        # x, y를 따로 움직이고 부딪힌 축만 되돌려서 장애물을 따라 미끄러지듯 이동
        speed = DASH_SPEED if self.dashing else WALK_SPEED
        old_x = self.x
        self.x += dx / length * speed * frame_time
        if collide_any(self.get_bb(), obstacles):
            self.x = old_x
        old_y = self.y
        self.y += dy / length * speed * frame_time
        if collide_any(self.get_bb(), obstacles):
            self.y = old_y

    def touch(self, target):
        """target(카이)과 발이 부딪혔으면 워든 반대쪽으로 밀어내며 피해를 줌"""
        if self.is_dead() or not collide(self.get_bb(), target.get_bb()):
            return
        x, y = bb_center(self.get_bb())
        tx, ty = bb_center(target.get_bb())
        length = math.hypot(tx - x, ty - y)
        if length == 0:
            dir_x, dir_y = 0, -1  # 정확히 겹쳐 있으면 아래로 밀어냄
        else:
            dir_x, dir_y = (tx - x) / length, (ty - y) / length
        target.on_hit(dir_x, dir_y, WARDEN_DAMAGE)

    def draw(self):
        size = FRAME_SIZE * WARDEN_SCALE
        if self.is_dead():
            # 쓰러지는 연출을 한 번 재생하고 마지막(부서진) 프레임으로 남음
            frame = min(int(self.death_time * DEATH_FPS), DEATH_FRAMES - 1)
            Warden.death_image.clip_draw(frame * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE,
                                         self.x, self.y, size, size)
            return
        if self.flash_time > 0:
            col = HIT_COL
        elif self.dashing:
            col = DASH_COLS[int(self.anim_time * DASH_FPS) % len(DASH_COLS)]
        elif self.is_burning():
            col = BURN_COLS[int(self.anim_time * BURN_FPS) % len(BURN_COLS)]
        else:
            col = int(self.anim_time * WALK_FPS) % WALK_FRAMES
        Warden.image.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                               FRAME_SIZE, FRAME_SIZE, self.x, self.y, size, size)
        self.draw_hp_bar()

    def draw_hp_bar(self):
        # 머리 위에 남은 HP를 빨간 바로 표시 (어두운 바탕 위에 채움)
        left = self.x - HP_BAR_WIDTH / 2
        bottom = self.y + (FRAME_SIZE / 2 - FRAME_TOP_MARGIN) * WARDEN_SCALE + HP_BAR_GAP
        draw_rectangle(left - 1, bottom - 1, left + HP_BAR_WIDTH + 1, bottom + HP_BAR_HEIGHT + 1,
                       20, 20, 25, 220, filled=True)
        ratio = self.hp / self.max_hp
        if ratio > 0:
            draw_rectangle(left, bottom, left + HP_BAR_WIDTH * ratio, bottom + HP_BAR_HEIGHT,
                           220, 40, 40, 255, filled=True)

    def draw_dash_range(self):
        # 디버그용: 돌진 범위를 발 중심 기준 원으로 표시 (돌진 중이면 빨강, 아니면 노랑)
        x, y = bb_center(self.get_bb())
        color = (255, 0, 0) if self.dashing else (255, 220, 0)
        draw_circle(x, y, int(DASH_RANGE), *color)
