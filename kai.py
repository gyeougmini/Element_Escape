import math

from pico2d import *

import game_world
from collision import collide_any
from fire import Fireball, FireLaunch

# 두 시트 모두 프레임 64x64, 8행(방향)이며 높이 512
# kai_animation_sheet.png: 9열 (0~5열 걷기), kai_idle.png: 2열
FRAME_SIZE = 64
SHEET_HEIGHT = 512
WALK_FRAMES = 6
IDLE_FRAMES = 2
WALK_FPS = 10  # 걷기 애니메이션 초당 프레임 수
IDLE_FPS = 2   # idle 애니메이션 초당 프레임 수
KAI_SCALE = 1.5
KAI_SPEED = 200  # 초당 이동 픽셀
# 탑뷰이므로 몸 전체가 아니라 발 부분만 충돌 박스로 사용
FOOT_HALF_WIDTH = 15
FOOT_HEIGHT = 12

# fire_attack: kai_animation_sheet.png의 6~7열을 재생하고, 7열로 넘어갈 때 파이어볼 발사
ATTACK_COLS = (6, 7)
ATTACK_FRAME_TIME = 0.12  # 공격 프레임 하나의 시간(초)
ATTACK_DURATION = 0.3     # 공격 상태 전체 시간(초)
FIRE_HEIGHT = 36          # 발에서 손까지의 높이: 파이어볼이 손 높이에서 나감
FIRE_SPAWN_DISTANCE = 30  # 몸 중심에서 파이어볼이 생기는 거리
READY_GLOW_SIZE = 64      # fire_ready 표시: fire_launch.png 첫 프레임을 손에 띄움
READY_GLOW_DISTANCE = 20  # 몸 중심에서 표시가 떨어진 거리

KAI_HP = 100
KAI_ENERGY = 100
FIRE_ENERGY_COST = 5  # 파이어볼 한 발에 쓰는 에너지
ENERGY_REGEN = 3.5     # 초당 에너지 충전량
# 쥐에게 부딪히면 반대 방향으로 밀려남: 처음 속도에서 0까지 줄어들며 약 60px 이동
KNOCKBACK_SPEED = 480
KNOCKBACK_TIME = 0.25
# 맞은 뒤 이 시간(초) 동안은 다시 맞지 않음 (붙어 있는 동안 매 프레임 피해를 받지 않도록), 그동안 깜빡임
INVINCIBLE_TIME = 1.0
BLINK_FPS = 10

# (dir_x, dir_y) -> 시트의 행 번호 (위에서부터)
DIRECTION_ROWS = {
    (0, -1): 0,   # 정면
    (1, -1): 1,   # 오른쪽 아래
    (1, 0): 2,    # 오른쪽
    (1, 1): 3,    # 오른쪽 위
    (0, 1): 4,    # 뒤
    (-1, 1): 5,   # 왼쪽 위
    (-1, 0): 6,   # 왼쪽
    (-1, -1): 7,  # 왼쪽 아래
}
ROW_DIRECTIONS = {row: direction for direction, row in DIRECTION_ROWS.items()}
# 오른쪽부터 반시계 방향으로 45도씩의 8방향: 임의의 방향을 가장 가까운 8방향으로 맞출 때 사용
OCTANT_DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

# 키 -> (dir_x, dir_y) 변화량
KEY_DIRECTIONS = {
    SDLK_d: (1, 0),
    SDLK_a: (-1, 0),
    SDLK_w: (0, 1),
    SDLK_s: (0, -1),
}


class Kai:
    def __init__(self, x, y):
        self.walk_image = load_image('sprite_sheet_kai/kai_animation_sheet.png')
        self.idle_image = load_image('sprite_sheet_kai/kai_idle.png')
        self.ready_image = load_image('sprite_sheet_fire/fire_launch.png')
        self.x, self.y = x, y
        self.dir_x, self.dir_y = 0, 0
        # 눌려 있는 방향키: 눌림을 못 받은 키의 뗌 신호가 와도 방향이 틀어지지 않도록 직접 기록
        self.pressed_keys = set()
        self.row = 0
        self.anim_time = 0.0
        self.state = 'idle'  # 'idle', 'walk', 'fire_attack'
        self.attack_time = 0.0
        self.fired = False
        # Q로 켜는 발사 준비 상태: 준비 중에도 걷거나 멈춰 있을 수 있으므로 state와 따로 관리
        self.fire_ready = False
        self.fire_dir = (0, -1)  # 파이어볼이 날아갈 방향 (길이 1)
        # E/R로 켜는 물/전기 준비 상태 (아직 공격은 없고 HUD 표시만)
        self.water_ready = False
        self.electric_ready = False
        self.max_hp = self.hp = KAI_HP
        self.max_energy = self.energy = KAI_ENERGY
        self.knockback_dir = (0, 0)
        self.knockback_time = 0.0
        self.invincible_time = 0.0

    def foot_y(self):
        # 프레임 아래쪽 끝을 발 위치로 사용
        return self.y - FRAME_SIZE * KAI_SCALE / 2

    def place_feet_at(self, x, y):
        # 발 충돌 박스의 중심이 (x, y)에 오도록 위치를 맞춤
        self.x = x
        self.y = y + FRAME_SIZE * KAI_SCALE / 2 - FOOT_HEIGHT / 2

    def get_bb(self):
        foot_y = self.foot_y()
        return (self.x - FOOT_HALF_WIDTH, foot_y,
                self.x + FOOT_HALF_WIDTH, foot_y + FOOT_HEIGHT)

    def hand_y(self):
        # 파이어볼이 나가는 손의 화면상 높이
        return self.foot_y() + FOOT_HEIGHT / 2 + FIRE_HEIGHT

    def stop(self):
        # 대화 등으로 조작을 막을 때: 눌려 있던 방향키를 잊고 멈춤
        self.pressed_keys.clear()
        self.dir_x, self.dir_y = 0, 0

    def is_moving(self):
        return (self.dir_x, self.dir_y) != (0, 0)

    def active_elements(self):
        # HUD에 켜서 보여줄 속성들
        ready = {'fire': self.fire_ready, 'water': self.water_ready, 'electric': self.electric_ready}
        return {name for name, on in ready.items() if on}

    def is_invincible(self):
        return self.invincible_time > 0

    def on_hit(self, dir_x, dir_y, damage):
        """부딪혀서 피해를 받음. dir: 밀려날 방향(길이 1). 무적 시간 중이면 무시하고 False"""
        if self.is_invincible():
            return False
        self.hp = max(0, self.hp - damage)
        self.knockback_dir = (dir_x, dir_y)
        self.knockback_time = KNOCKBACK_TIME
        self.invincible_time = INVINCIBLE_TIME
        return True

    def move(self, dx, dy, obstacles):
        # x, y를 따로 움직이고 부딪힌 축만 되돌려서 벽을 따라 미끄러지듯 이동
        old_x = self.x
        self.x += dx
        if collide_any(self.get_bb(), obstacles):
            self.x = old_x
        old_y = self.y
        self.y += dy
        if collide_any(self.get_bb(), obstacles):
            self.y = old_y

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN and event.key == SDLK_q:
            # 발사 준비 토글: 한 번 더 누르면 취소
            if self.state != 'fire_attack':
                self.fire_ready = not self.fire_ready
            return
        if event.type == SDL_KEYDOWN and event.key == SDLK_e:
            self.water_ready = not self.water_ready
            return
        if event.type == SDL_KEYDOWN and event.key == SDLK_r:
            self.electric_ready = not self.electric_ready
            return
        if event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            if self.fire_ready:
                # SDL 마우스 좌표는 위에서부터이므로 pico2d 좌표로 뒤집음
                self.aim_at(event.x, get_canvas_height() - 1 - event.y)
            return
        if event.type not in (SDL_KEYDOWN, SDL_KEYUP) or event.key not in KEY_DIRECTIONS:
            return
        if event.type == SDL_KEYDOWN:
            self.pressed_keys.add(event.key)
        else:
            self.pressed_keys.discard(event.key)
        self.dir_x = sum(KEY_DIRECTIONS[key][0] for key in self.pressed_keys)
        self.dir_y = sum(KEY_DIRECTIONS[key][1] for key in self.pressed_keys)

    def aim_at(self, target_x, target_y):
        # 공격 중이거나 에너지가 모자라면 쏘지 않음
        if self.state == 'fire_attack' or self.energy < FIRE_ENERGY_COST:
            return
        dx, dy = target_x - self.x, target_y - self.hand_y()
        length = math.hypot(dx, dy)
        if length == 0:
            return
        self.energy -= FIRE_ENERGY_COST
        self.fire_dir = (dx / length, dy / length)
        # 클릭한 쪽에 가장 가까운 8방향을 바라보게 함
        octant = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.row = DIRECTION_ROWS[OCTANT_DIRECTIONS[octant]]
        self.start_fire_attack()

    def start_fire_attack(self):
        self.state = 'fire_attack'
        self.attack_time = 0.0
        self.fired = False

    def launch_fireball(self):
        # 클릭한 방향(fire_dir)으로 발사
        dir_x, dir_y = self.fire_dir
        spawn_x = self.x + dir_x * FIRE_SPAWN_DISTANCE
        spawn_y = self.hand_y() + dir_y * FIRE_SPAWN_DISTANCE
        game_world.add(Fireball(spawn_x, spawn_y, dir_x, dir_y))
        game_world.add(FireLaunch(spawn_x, spawn_y))

    def update(self, frame_time, obstacles):
        self.anim_time += frame_time
        self.invincible_time = max(0.0, self.invincible_time - frame_time)
        self.energy = min(self.max_energy, self.energy + ENERGY_REGEN * frame_time)
        if self.state == 'fire_attack':
            self.attack_time += frame_time
            if not self.fired and self.attack_time >= ATTACK_FRAME_TIME:
                self.launch_fireball()
                self.fired = True
        if self.state != 'fire_attack' or self.attack_time >= ATTACK_DURATION:
            self.state = 'walk' if self.is_moving() else 'idle'
        if self.knockback_time > 0:
            # 밀려나는 동안은 키 입력으로 움직이지 않음. 남은 시간에 비례해 속도가 줄어듦
            speed = KNOCKBACK_SPEED * self.knockback_time / KNOCKBACK_TIME
            dx, dy = self.knockback_dir
            self.move(dx * speed * frame_time, dy * speed * frame_time, obstacles)
            self.knockback_time -= frame_time
        elif self.is_moving():
            # 공격 중에는 이동만 하고, 바라보는 방향은 공격 방향으로 유지
            if self.state != 'fire_attack':
                self.row = DIRECTION_ROWS[(self.dir_x, self.dir_y)]
            self.move(self.dir_x * KAI_SPEED * frame_time, self.dir_y * KAI_SPEED * frame_time, obstacles)

    def draw(self):
        if self.state == 'fire_attack':
            attack_frame = min(int(self.attack_time / ATTACK_FRAME_TIME), len(ATTACK_COLS) - 1)
            image, col = self.walk_image, ATTACK_COLS[attack_frame]
        elif self.state == 'walk':
            image, col = self.walk_image, int(self.anim_time * WALK_FPS) % WALK_FRAMES
        else:
            image, col = self.idle_image, int(self.anim_time * IDLE_FPS) % IDLE_FRAMES
        # 뒤쪽(위)을 보고 있으면 손이 몸에 가려지므로 준비 표시를 카이보다 먼저 그림
        facing_back = ROW_DIRECTIONS[self.row][1] > 0
        if self.fire_ready and facing_back:
            self.draw_ready_glow()
        # 무적 시간 중에는 깜빡임
        blink_off = self.is_invincible() and int(self.invincible_time * BLINK_FPS) % 2 == 1
        if not blink_off:
            # pico2d는 좌하단이 원점이므로 위에서부터의 행 번호를 뒤집어서 계산
            image.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                            FRAME_SIZE, FRAME_SIZE,
                            self.x, self.y, FRAME_SIZE * KAI_SCALE, FRAME_SIZE * KAI_SCALE)
        if self.fire_ready and not facing_back:
            self.draw_ready_glow()

    def draw_ready_glow(self):
        # 바라보는 쪽 손 위치에 불꽃을 띄워 발사 준비 중임을 표시
        dir_x, dir_y = ROW_DIRECTIONS[self.row]
        length = math.hypot(dir_x, dir_y)
        self.ready_image.clip_draw(0, 0, READY_GLOW_SIZE, READY_GLOW_SIZE,
                                   self.x + dir_x / length * READY_GLOW_DISTANCE,
                                   self.hand_y() + dir_y / length * READY_GLOW_DISTANCE)
