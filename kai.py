from pico2d import *

from collision import collide_any

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

# 키 -> (dir_x, dir_y) 변화량
KEY_DIRECTIONS = {
    SDLK_d: (1, 0),
    SDLK_a: (-1, 0),
    SDLK_w: (0, 1),
    SDLK_s: (0, -1),
}


class Kai:
    def __init__(self, x, y):
        self.walk_image = load_image('sprite_sheet/kai_animation_sheet.png')
        self.idle_image = load_image('sprite_sheet/kai_idle.png')
        self.x, self.y = x, y
        self.dir_x, self.dir_y = 0, 0
        self.row = 0
        self.anim_time = 0.0

    def foot_y(self):
        # 프레임 아래쪽 끝을 발 위치로 사용
        return self.y - FRAME_SIZE * KAI_SCALE / 2

    def get_bb(self):
        foot_y = self.foot_y()
        return (self.x - FOOT_HALF_WIDTH, foot_y,
                self.x + FOOT_HALF_WIDTH, foot_y + FOOT_HEIGHT)

    def is_moving(self):
        return (self.dir_x, self.dir_y) != (0, 0)

    def handle_event(self, event):
        if event.type not in (SDL_KEYDOWN, SDL_KEYUP) or event.key not in KEY_DIRECTIONS:
            return
        dx, dy = KEY_DIRECTIONS[event.key]
        sign = 1 if event.type == SDL_KEYDOWN else -1
        self.dir_x += dx * sign
        self.dir_y += dy * sign

    def update(self, frame_time, obstacles):
        self.anim_time += frame_time
        if self.is_moving():
            self.row = DIRECTION_ROWS[(self.dir_x, self.dir_y)]
            # x, y를 따로 움직이고 부딪힌 축만 되돌려서 벽을 따라 미끄러지듯 이동
            old_x = self.x
            self.x += self.dir_x * KAI_SPEED * frame_time
            if collide_any(self.get_bb(), obstacles):
                self.x = old_x
            old_y = self.y
            self.y += self.dir_y * KAI_SPEED * frame_time
            if collide_any(self.get_bb(), obstacles):
                self.y = old_y

    def draw(self):
        if self.is_moving():
            image, col = self.walk_image, int(self.anim_time * WALK_FPS) % WALK_FRAMES
        else:
            image, col = self.idle_image, int(self.anim_time * IDLE_FPS) % IDLE_FRAMES
        # pico2d는 좌하단이 원점이므로 위에서부터의 행 번호를 뒤집어서 계산
        image.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (self.row + 1) * FRAME_SIZE,
                        FRAME_SIZE, FRAME_SIZE,
                        self.x, self.y, FRAME_SIZE * KAI_SCALE, FRAME_SIZE * KAI_SCALE)
