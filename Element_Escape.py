from pico2d import *

WIDTH, HEIGHT = 1280, 720

running = True
dir_x, dir_y = 0, 0


def handle_events():
    global running, dir_x, dir_y
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                running = False
            elif event.key == SDLK_d:
                dir_x += 1
            elif event.key == SDLK_a:
                dir_x -= 1
            elif event.key == SDLK_w:
                dir_y += 1
            elif event.key == SDLK_s:
                dir_y -= 1
        elif event.type == SDL_KEYUP:
            if event.key == SDLK_d:
                dir_x -= 1
            elif event.key == SDLK_a:
                dir_x += 1
            elif event.key == SDLK_w:
                dir_y -= 1
            elif event.key == SDLK_s:
                dir_y += 1


open_canvas(WIDTH, HEIGHT)

background = load_image('sprite_sheet/cell_bg.png')
kai_walk = load_image('sprite_sheet/kai_animation_sheet.png')
kai_idle = load_image('sprite_sheet/kai_idle.png')

# 두 시트 모두 프레임 64x64, 8행(방향)이며 높이 512
# kai_animation_sheet.png: 9열 (0~5열 걷기), kai_idle.png: 2열
FRAME_SIZE = 64
SHEET_HEIGHT = 512
WALK_FRAMES = 6
IDLE_FRAMES = 2
WALK_FPS = 10  # 걷기 애니메이션 초당 프레임 수
IDLE_FPS = 2   # idle 애니메이션 초당 프레임 수
KAI_SCALE = 1.5
KAI_SPEED = 100  # 초당 이동 픽셀

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

kai_x, kai_y = WIDTH // 2, HEIGHT // 2
kai_row = 0
anim_time = 0.0
last_time = get_time()

while running:
    handle_events()

    now = get_time()
    frame_time = now - last_time
    last_time = now
    anim_time += frame_time

    moving = (dir_x, dir_y) != (0, 0)
    if moving:
        kai_row = DIRECTION_ROWS[(dir_x, dir_y)]
        kai_x += dir_x * KAI_SPEED * frame_time
        kai_y += dir_y * KAI_SPEED * frame_time

    clear_canvas()
    background.draw(WIDTH // 2, HEIGHT // 2, WIDTH, HEIGHT)
    # pico2d는 좌하단이 원점이므로 위에서부터의 행 번호를 뒤집어서 계산
    if moving:
        sheet, col = kai_walk, int(anim_time * WALK_FPS) % WALK_FRAMES
    else:
        sheet, col = kai_idle, int(anim_time * IDLE_FPS) % IDLE_FRAMES
    sheet.clip_draw(col * FRAME_SIZE, SHEET_HEIGHT - (kai_row + 1) * FRAME_SIZE,
                    FRAME_SIZE, FRAME_SIZE,
                    kai_x, kai_y, FRAME_SIZE * KAI_SCALE, FRAME_SIZE * KAI_SCALE)
    update_canvas()
    delay(0.01)

close_canvas()
